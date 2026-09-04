# 审阅结论

这轮 Codex 的推进是**实质性的**，不是继续堆文档：

- F2 保持原 11-query Gate 未修改、未消费；
- F3 把漏算的 physical planner 纳入，总上限修正为 58；
- F4 已经从旧 Run14 补丁链中独立出来，建立了新的四阶段 Runtime V2；
- F4 的 Guard→runner 路径状态矛盾已经真正修掉，13 个负例和 Run10–Run14 五项历史回归均通过；
- NVIDIA 驱动仍不可见，因此没有误启动 GPU，也没有消耗授权。当前 formal 仍为 `0 roots / 0 trajectories`。fileciteturn252file0L1-L12

但完整代码审阅后，我的决定不是“F4 直接开跑”，而是：

> **F4 已经成功救回，不再永久关闭；但还需要一次很小、很明确的 CPU 最终加固。**  
> **F3 V2 也还有两个 fail-closed 小问题，驱动恢复前正好一起修完。**  
> **F2 不改，仍然排第一执行。**

---

# 一、当前三族的准确状态

| Family | 当前状态 | 我的决定 |
|---|---|---|
| F2 | 11-query controlled-insertion/beside planner Gate 已签发、未消费 | **保持不动，驱动恢复后第一项执行** |
| F3 | 58-query 总预算已补齐，V2 未消费 | **升级为 V2.1 后执行** |
| F4 | 物理模板 3/3，Runtime V2 生命周期修复通过 | **不再关闭；补最终验收与授权绑定后，再批准一个 root** |

---

# 二、F4：最难的基础设施问题已经解决了

F4 Runtime V2 做对了几个关键事情。

## 1. Guard 和 runner 不再使用矛盾的路径状态

新合同已经区分：

- `PREPUBLICATION`
- `GUARD_ENTRY`
- `RUNNER_ENTRY`
- `POST_CHILD`

其中：

- Guard 进入时要求 output/guard/cache 不存在；
- runner 进入时要求 Guard 已创建 start receipt、stdout、stderr、cache 和 9 个 cache 子目录；
- runner 不再错误地要求 Guard 创建的路径仍然不存在。fileciteturn258file0L1-L6 fileciteturn259file0L1-L6

这已经正确修掉了 Run14 的根因。

## 2. 新 Guard 没有继续 monkey-patch 旧 Guard main

新 Guard 只复用了旧 Guard 的：

- `nvidia_snapshot`
- `idle`
- `selected`
- `child_environment`

然后自己负责 lease、start receipt、child 启动、post snapshot 和 cleanup。fileciteturn260file0L1-L6

## 3. 新 runner 不再调用旧 runner main

它只 hash-bound 调用：

```python
run_f4_development_r_pc_root(...)
```

然后自己进行最终验收，并且只有 root 真正 accepted 时才返回 exit code 0；这修掉了“root 失败但因为没有抛异常而被当成成功”的问题。fileciteturn262file0L1-L6 fileciteturn263file0L1-L6

## 4. 生命周期测试是真正的状态转换测试

它已经模拟：

```text
路径全部不存在
→ GUARD_ENTRY
→ 创建 guard/start/stdout/stderr/cache
→ 子进程执行 RUNNER_ENTRY
→ 解析 exact F4 dispatch
→ 在 GPU/scene/output 前停止
→ 清理临时路径
```

并拒绝了 13 个错误情况，包括缺目录、错误 start receipt、错误 candidate、错误 program、错误预算、错误 planner terminal 和旧 third-reopen 字段。fileciteturn264file0L1-L6 fileciteturn265file0L1-L6

因此，**F4 的启动链已经从“不可信”推进到了“基本可用”。**

---

# 三、F4 还剩下哪些问题？

现在剩下的不是物理任务，也不是 planner，而是**数据最终验收和授权绑定**。

## 问题 1：当前 Runtime 没有强绑定这一次新的 GPT 外审决定

当前 proposal 绑定了：

- 执行计划；
- Runtime 文件；
- Run2；
- Run9；
- Run10–Run14；
- planner terminals；
- active source；
- assets。

但是没有：

```yaml
external_review_decision_path:
external_review_decision_file_sha256:
external_review_decision_receipt_sha256:
```

当前 `manifest_contract.py` 也没有验证这些字段。fileciteturn255file0L1-L6 fileciteturn258file0L1-L6

这意味着，从当前 schema 本身看，一个 `approved=true` manifest 并没有被代码强制要求绑定“GPT 已经批准这一 root”的文件。

### 必须补齐

新 proposal/未来 approved manifest 必须绑定：

```yaml
external_review_decision_path:
external_review_decision_file_sha256:
external_review_decision_receipt_sha256:

source_proposal_manifest_path:
source_proposal_manifest_file_sha256:
source_proposal_manifest_sha256:

cpu_review_path:
cpu_review_file_sha256:
cpu_review_receipt_sha256:

lifecycle_receipt_path:
lifecycle_receipt_file_sha256:
lifecycle_receipt_sha256:
```

并且 `validate_bound_sources()` 必须真实读取、验证这些文件。

---

## 问题 2：RUNNER_ENTRY 对 GPU、lease 和 start receipt 的交叉绑定还不完整

当前 runner entry 只确认：

- start receipt 的 manifest SHA；
- job ID；
- run ID；
- 环境变量中有 UUID、GPU index 和 lease path。

但没有严格确认：

```text
start receipt family == F4
start receipt physical_gpu_index == 环境 GPU index
start receipt gpu_uuid == CUDA_VISIBLE_DEVICES
start receipt lease_path == CMF_GPU_LEASE_PATH
lease path 确实存在
CUDA_VISIBLE_DEVICES 只有一个 UUID
九个 cache 环境变量分别指向九个已建立目录
CUDA_HOME、PYTHONPATH、PYTHONDONTWRITEBYTECODE 精确符合合同
```

当前代码只是检查这些变量“存在”，没有全部交叉比对。fileciteturn259file0L1-L6

旧 Guard 的 `child_environment()` 已明确给出了九个环境变量和目录映射，可以直接冻结并验证：fileciteturn294file0L1-L6

```text
CONDA_PKGS_DIRS       → conda_pkgs
CUDA_CACHE_PATH       → cuda
HOME                  → home
MPLCONFIGDIR          → matplotlib
NUMBA_CACHE_DIR       → numba
TMPDIR                → tmp
TORCH_EXTENSIONS_DIR  → torch_extensions
TORCH_HOME            → torch
XDG_CACHE_HOME        → xdg
```

---

## 问题 3：POST_CHILD 只检查 job terminal 存在，没有验证它是否真的可信

目前 `POST_CHILD` 做的是：

- Guard terminal 存在且 self-hash 正确；
- manifest/job ID 一致；
- output 存在时 `job_terminal.json` 必须存在。

但它没有验证：

- job terminal 的 self-hash；
- job terminal 的 run/job/manifest 绑定；
- `job_terminal.pass` 与 child exit code 是否一致；
- root finalizer 是否 accepted；
- accepted root/trajectory 计数是否为 1/3；
- Guard cleanup 是否通过；
- GPU 是否返回 baseline。fileciteturn259file0L1-L6

应增加：

```text
child_exit_code == 0
⇔ job_terminal.pass == true
⇔ root_finalizer.accepted == true
```

任何一个不一致都必须让 Guard 最终失败。

---

## 问题 4：F4 finalizer 还没有独立重验磁盘上的 raw 和 MP4

当前 finalizer 的 raw 检查主要是：

```python
raw_manifest 是 dict
raw_streams_npz_sha256 是字符串
manifest_file_sha256 是字符串
manifest_integrity_sidecar_sha256 是字符串
```

视频检查则主要信任 branch receipt 中已经写好的：

```python
development_video_integrity.pass == true
```

它没有再次打开磁盘文件验证：

- raw NPZ 是否存在；
- manifest 和 sidecar 是否存在；
- 文件 hash 是否仍然匹配；
- MP4 是否存在；
- MP4 bytes/hash 是否仍匹配；
- MP4 是否包含首帧、末帧。

这部分在当前 finalizer 代码中确实没有调用独立的 raw/video validator。fileciteturn262file0L1-L6 fileciteturn263file0L1-L6

仓库已经有成熟的现成函数：

```python
verify_raw_artifact_integrity(...)
validate_development_trajectory_mp4_receipt_v1(...)
```

前者会重算 raw、manifest、sidecar 和 trace 的 hash；后者会重新检查 MP4 文件、hash、bytes、frames 以及首末帧。fileciteturn300file0L1-L6 fileciteturn301file0L1-L6

F1 batch finalizer 也已经采用独立 raw 验证，F4 应复用相同模式，而不是只检查 receipt 中有没有字符串字段。fileciteturn291file2L30-L42

---

## 问题 5：CPU review 声称测试过 finalizer，但没有绑定机器可复核的测试产物

实施审阅文档写了：

- nested NumPy `bool_` 可以序列化；
- synthetic `failed_verifier` 会被拒绝；
- synthetic successful finalizer 得到 11/7。

但当前提交里没有单独、机器可复核并绑定的 finalizer test receipt；这些结果目前主要存在于文字报告中。fileciteturn270file0L1-L6 fileciteturn271file0L1-L6

应补一份版本化测试：

```text
F4_DEVELOPMENT_ROOT_RUNTIME_V2_1_FINALIZER_TEST_V1.json
```

至少覆盖：

- accepted 3/3；
- root `failed_verifier` 但无异常；
- 缺 raw；
- raw NPZ 被篡改；
- 缺 MP4；
- MP4 被篡改；
- branch receipt 被篡改；
- suffix query 不是 42；
- planner total 不是 136；
- duplicate scene ID；
- phase 数量不是 1+3+1+3+3；
- branch execution planner delta 非 0；
- final-state equivalence false；
- NumPy bool/int/float/array 序列化。

---

# 四、F4 的最终决定

**不是 KEEP_CLOSED。**

但当前也不能直接 `APPROVE_ONE...`，因为上述缺口属于 accepted-data 可信性问题。

正式决定是：

```yaml
f4:
  decision: REVISE

  scientific_status: PHYSICALLY_QUALIFIED
  root_status: INFRASTRUCTURE_FINAL_HARDENING_REQUIRED

  old_closed_status:
    superseded_for_cpu_infrastructure_repair: true
    candidate_search_reopened: false
    physical_template_requalification_required: false

  exact_scope_if_revised:
    candidate: f4-slot-corridor-hv2-r01
    programs: [F4-ABC, F4-ACB, F4-BAC]

    fixed_arm_schedule:
      canonical_prefix: right
      program_suffix: left

    scientific_changes_allowed: false
    layout_changes_allowed: false
    verifier_threshold_changes_allowed: false
    planner_terminal_changes_allowed: false
    seed_retry_allowed: false
    fallback_allowed: false
    second_root_allowed: false
    automatic_retry: false

    required_cpu_changes:
      - Bind the new external review decision, the source proposal,
        CPU review receipt and final lifecycle receipt by exact path,
        file SHA-256 and receipt/manifest SHA-256.
      - Validate manifest_contract.py, guarded_launcher.py and
        job_runner.py executable identity against their exact
        manifest-bound paths and SHA-256 values.
      - Cross-bind RUNNER_ENTRY start receipt family, GPU index,
        GPU UUID and lease path to the child environment.
      - Validate all nine cache environment variables, CUDA_HOME,
        PYTHONPATH, PYTHONDONTWRITEBYTECODE and absence of
        LD_LIBRARY_PATH.
      - Extend POST_CHILD to verify the job-terminal self-hash,
        run/job/manifest binding, pass status, child exit code,
        root-finalizer status, accepted counts and Guard cleanup.
      - Independently reload and verify each on-disk branch receipt,
        raw artifact, development MP4 and root receipt.
      - Verify the three suffix receipts are in exact ABC/ACB/BAC
        order, each reports planner_solvable=true and exactly
        12+30=42 queries.
      - Verify all 11 cleanup scene IDs are unique and their exact
        phase multiset is pristine=1, task-feasibility=3,
        canonical-prefix=1, suffix-preflight=3,
        strict-prefix-branch=3.
      - Publish a machine-readable finalizer/post-child test receipt
        covering success, failed_verifier, artifact corruption,
        count corruption, duplicate scenes and NumPy serialization.

    frozen_caps:
      maximum_root_invocations: 1
      maximum_canonical_prefix_generations: 1
      maximum_suffix_prefix_replays: 3
      maximum_branch_prefix_replays: 3
      maximum_total_prefix_replays: 6
      maximum_suffix_preflights: 3
      maximum_branch_executions: 3
      maximum_planner_queries: 136
      maximum_fresh_scenes: 11
      maximum_robot_action_scenes: 7
      maximum_raw_trajectories: 3
      maximum_debug_videos: 3
      maximum_accepted_development_roots: 1
      maximum_accepted_development_trajectories: 3
      maximum_formal_trajectories: 0

    gpu_execution_authorized_now: false
    new_external_review_required_after_cpu_hardening: true
```

这次 revision **不允许再修改 F4 机器人动作代码**。它只是在已经正确的 Runtime V2 上补：

1. 权限绑定；
2. runner/Guard 环境交叉验证；
3. post-child 验证；
4. 磁盘产物独立验收。

完成后，F4 的下一次外审应该非常小，只需审：

```text
Runtime V2.1 hashes
finalizer test receipt
post-child lifecycle receipt
proposal V2
```

不需要重新研究 Run9–Run14，也不需要重新解释物理设计。

---

# 五、F3：58-query 修正是正确的，但还要升级成 V2.1

F3 V2 manifest 已明确写成：

```text
qualification planner ≤ 30
physical planner ≤ 7 / candidate
physical candidates ≤ 4
aggregate planner ≤ 58
planner scenes ≤ 6
physical scenes ≤ 4
aggregate scenes ≤ 10
no-suffix scenes = 0
```

这部分与代码结构一致。fileciteturn273file0L1-L6

但我发现两个问题。

## 1. F3 V2 无论 Gate 成败都返回 exit code 0

当前 main 最后固定为：

```python
return 0
```

即使：

```python
terminal["pass"] == False
```

child 仍返回 0，Guard 可能登记为 completed。fileciteturn275file0L1-L6

应改成：

```python
return 0 if terminal["pass"] else 1
```

## 2. physical executor 抛异常时，planner query 可能被漏记

V2 accounting 依赖：

```python
physical_rows[*].physical_planner_queries
```

但 V1 physical row 是从成功返回的 terminal 中读取 planner count。

而底层 `record_physical_scene()` 在 execute 抛异常时，只保存 error、trace、video 和 cleanup，没有始终保存：

```text
planner_query_count_before
planner_query_count_after
planner_query_delta
```

因此，如果某个 physical candidate 已经运行了若干 planner query，随后在动作或接触阶段抛异常，结果可能被记成 0 次 physical planner query。fileciteturn278file0L1-L6

虽然 `_plan_chain` 本身仍限制单场最多 7 次，不会真的无限超预算，但最终 accounting receipt 会不完整。

## F3 V2.1 精确修改

```yaml
f3:
  decision: REVISE_UNCONSUMED_V2_TO_V2_1

  reissue_ordinal: 1
  second_reissue: false
  tuples_changed: false
  overlay_changed: false
  physical_gate_changed: false

  exact_changes:
    - Make child exit code 0 if and only if job_terminal.pass is true.
    - For every physical scene, record planner_query_count_before,
      planner_query_count_after and planner_query_delta in a finally
      block, including exception paths.
    - Derive physical planner accounting from the physical-scene
      receipt, not only from the returned physical terminal.
    - Require one complete planner count for every attempted physical
      candidate.
    - Reject the job when a physical scene was attempted but its
      planner delta is missing or negative.
    - Preserve exact 30 + 4*7 = 58 aggregate cap.
    - Keep no-suffix execution at zero in this job.

  frozen_caps:
    replacement_qualification_planner_query_cap: 30
    physical_planner_query_cap_per_candidate: 7
    physical_candidate_cap: 4
    aggregate_planner_query_cap: 58
    planner_scene_cap: 6
    physical_scene_cap: 4
    aggregate_scene_cap: 10
    conditional_no_suffix_scene_cap_in_this_job: 0
    reserved_next_no_suffix_scene_cap: 3
    formal_trajectory_cap: 0

  required_cpu_tests:
    - successful gate returns exit 0
    - scientific gate failure without exception returns exit 1
    - exception after three physical planner queries records three
      and returns exit 1
    - exact worst case 30 plus 4 times 7 equals 58
    - 59 queries fail closed
    - no scene/GPU/output created by preflight

  external_review_after_exact_hotfix_required: false
```

因为 V2 尚未消费，这仍是**同一次 reissue 的未消费 V2.1 修正**，不是第二次 reissue。完成上述 exact CPU tests 后，可以按既定顺序执行，不需要再单独回来申请 F3。

---

# 六、F2 保持不变

F2 当前清单和 Runtime 不要修改。

它已经明确绑定：

- 5 段 controlled inside；
- 6 段 beside；
- gravity drop 关闭；
- physical/branch/raw/video/root 全为 0；
- CPU preflight 通过。fileciteturn228file0L1-L6

驱动恢复后第一项执行。

但 F2 的最终结论必须以：

```text
job_terminal.pass
result.both_chains_pass
inside 5/5
beside 6/6
planner total = 11
```

为准，不能只看 Guard 是否写了 `completed`。

F2 无论通过还是失败，都先完成：

- Guard terminal；
- cleanup；
- GPU baseline postcheck；
- terminal publication。

之后再进入 F3 V2.1。F2 科学结果失败不影响 F3 独立 Gate，但禁止 F2 自动进入 root。

---

# 七、Codex 现在应执行的完整顺序

下面这段可以原样交给 Codex：

```text
基于 Vault HEAD 861d48c1e62e837f51ea116240836633780a235f，
本轮CPU工作整体有效，但不要在driver恢复后原样启动F3 V2或F4。

一、F2
1. 保持现有F2 approved manifest、Guard、runner、hash和路径完全不动。
2. 驱动恢复后，F2仍是第一项。
3. 结果以job_terminal.pass和both_chains_pass为准，不只看Guard completed。
4. F2结束后必须完成clean GPU postcheck；不得自动进入root。

二、F3
1. 当前F3 V2尚未消费，将其无损supersede为V2.1，reissue ordinal仍为1。
2. 不改overlay、r0005、r1505/r2180/r3677、物理Gate或58-query预算。
3. 修正runner：
   - return 0 if terminal.pass else 1；
   - 每个physical scene在finally中记录planner before/after/delta；
   - 即使physical executor抛异常也必须保留真实planner delta；
   - aggregate accounting从scene receipt计算，不能只依赖返回terminal。
4. 增加success/fail-without-exception/exception-after-query/58/59测试。
5. CPU测试通过后可直接进入既定F2后串行执行，不需再次申请GPT批准。
6. 本job no-suffix仍严格为0。

三、F4
1. F4不得恢复为永久关闭；状态保持：
   F4_PHYSICALLY_QUALIFIED_ROOT_INFRASTRUCTURE_FINAL_HARDENING_REQUIRED。
2. 不改r01、ABC/ACB/BAC、layout、arm schedule、planner terminals、
   physical code、threshold或verifier。
3. 在新versioned路径创建Runtime V2.1，不覆盖Runtime V2。
4. 增加外审决定、source proposal、CPU review、lifecycle receipt的
   path/file-SHA/receipt-SHA强绑定。
5. Guard和runner都必须验证自身__file__路径与manifest绑定路径一致。
6. RUNNER_ENTRY交叉验证：
   - start family/run/job/manifest；
   - GPU index/UUID；
   - lease path；
   - CUDA_VISIBLE_DEVICES；
   - CUDA_HOME、PYTHONPATH、PYTHONDONTWRITEBYTECODE；
   - 九个cache环境变量；
   - LD_LIBRARY_PATH不存在。
7. POST_CHILD必须读取并验证job_terminal：
   - self-hash；
   - run/job/manifest；
   - pass；
   - child exit；
   - finalizer；
   - accepted 1/3；
   - cleanup与GPU baseline。
8. F4 finalizer必须从磁盘独立读取：
   - root receipt；
   - 三个branch receipt；
   - 三个raw目录并调用verify_raw_artifact_integrity；
   - 三个MP4并调用validate_development_trajectory_mp4_receipt_v1；
   - 三个suffix receipt各42 queries；
   - 11个唯一scene IDs和精确phase multiset。
9. 发布机器可复核的finalizer/post-child测试receipt，覆盖artifact篡改、
   failed_verifier、count错误、duplicate scene和NumPy serialization。
10. 只生成approved=false/GPU=false/physical=false的proposal V2和新GPT
    review request；不得启动F4 GPU。

四、驱动
1. nvidia-smi -L、8-card row、compute-app query任一失败都不启动Guard。
2. 连续两轮、间隔至少10秒通过后：
   F2 → clean postcheck → F3 V2.1 → clean postcheck。
3. F4继续等待Runtime V2.1最终外审。
4. Stage0 rerun、Stage1、formal360、training、H-reveal、
   compression、pi0.5继续全部false。
```

---

# 最终一句话

> **Codex 这轮已经把 F4 从“似乎修不动”推进到了“只剩最终数据验收加固”；F4 不要放弃。F2 已经排队待运行，F3 只需补一个 V2.1 fail-closed 修正。真正阻止 GPU 的仍然是服务器驱动，而不是三族任务本身。**

---

If you want, I can:

- 列出F4需要完成的四个残余风险详细步骤
- 说明F3 V2.1修复的关键变更和影响
- 梳理当前F2、F3、F4执行流程和依赖关系
