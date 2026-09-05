# 正式外审结论

我已经按 Vault HEAD `3e1bab4d51ad43ceb10b4b06f49a9551a0879c12` 检查了合并审阅材料、最新 readiness、F2 Run2 失败证据与 Run3 proposal、F3 的实际 0/4 trace 和 pre-close Gate、F4 Runtime V2.1 的 manifest contract、Guard、runner、finalizer 及测试矩阵。该 HEAD 与你给出的状态一致。当前确实已有 F1 的 5 个 development roots、15 条 `r_pc`，但 Stage-1-authorized 仍为 `0/48`，formal 仍为 `0/360`。fileciteturn283file0L2-L7 fileciteturn285file0L1-L7

我的正式裁决是：

| Family | 裁决 | 当前可否执行 GPU |
|---|---|---:|
| F1 | 保留 5 roots / 15 `r_pc`；转入 `r_inv_path/r_inv_motion` 设计 | 否 |
| F2 | **有条件批准唯一一次短 TMPDIR Run3** | 满足下面前置条件后可以 |
| F3 | **批准 CPU-only Gate V1.1 与精确候选冻结；暂不批准 GPU** | 否，需一次窄范围复审 |
| F4 | **REVISE：finalizer 已通过，但授权解析和 GPU 冷却仍有缺口** | 否，需 Runtime V2.2 后复审 |
| Stage 1 | 未就绪 | 否 |
| Formal 360 | 未授权 | 否 |
| Training / H-reveal / compression / π0.5 | 未授权 | 否 |

---

# 一、F2：批准唯一一次短路径基础设施恢复 Run3

## 1. Run2 不是路线失败

F2 Run2 的证据已经足够清楚：

- child 确实启动；
- CUDA context 初始化过；
- scene setup 尝试了 1 次；
- planner query 为 **0**；
- inside/beside planner receipt 均未产生；
- Warp/NVRTC 在 CuRobo planner 构造阶段报 `NVRTC_ERROR_COMPILATION`；
- 失败 TMPDIR 长度为 137；
- 没有 physical、branch、raw、video 或 root；
- cache、lease、进程和 GPU baseline 均清理成功。fileciteturn349file0L1-L7

因此这不能计为 F2 科学路线失败，也不能解释成 inside 或 beside 不可达。

短路径 proposal 将 cache root 改为：

```text
/nfs_share/lijunhui/Robotwin2/cache/f2
```

派生 TMPDIR 为 82 字节，全部 9 个 cache 路径最长 95 字节；科学合同仍严格保持 inside 5、beside 6、总计 11 queries、2 scenes、0 physical/root/raw/formal。fileciteturn335file0L1-L7

## 2. F2 正式批准 token

```text
APPROVE_ONE_F2_SHORT_TMPDIR_INFRASTRUCTURE_RECOVERY_RUN3
```

这是**有条件、单次、基础设施恢复授权**，不是无条件允许直接拿现有 Guard 开跑。

精确含义：

```yaml
f2:
  decision: APPROVE_ONE_F2_SHORT_TMPDIR_INFRASTRUCTURE_RECOVERY_RUN3

  dispatch_ordinal: 3
  scientific_attempt_ordinal: 1
  maximum_dispatches_authorized_by_this_decision: 1

  scientific_contract:
    inside_planner_queries: 5
    beside_planner_queries: 6
    aggregate_planner_queries: 11
    fresh_planner_scenes: 2
    physical_executions: 0
    branch_executions: 0
    raw_trajectories: 0
    videos: 0
    accepted_roots: 0
    formal_trajectories: 0

  target_search: false
  target_change: false
  seed_retry: false
  automatic_retry: false
  automatic_root_transition: false
  further_dispatch_after_run3: false
```

## 3. 但必须先补一个很薄的 admission 层

当前 F2 runner 仍只强制绑定较早的原始外审文件 SHA，并不知道这一次 Run3 的新批准；F2 Guard 又直接复用该 runner 的 `load_manifest()`。因此，仅在新 manifest 里增加一个审批字段，并不能证明执行入口真的验证了本次 Run3 批准。fileciteturn347file0L1-L5 fileciteturn348file0L1-L7

Codex 必须先增加一个**不修改科学 runner 的薄 wrapper**：

```text
f2_short_tmpdir_recovery_run3_admission_v1/
  authorized_launcher.py
  admission_contract.py
```

它必须在调用原 F2 Guard 前完成：

1. 读取本次外审回复对应的 self-hashed JSON decision receipt；
2. 对 decision 枚举做**精确相等**检查，不使用字符串包含关系；
3. 绑定：
   - 本次外审 Markdown 的 file SHA；
   - decision receipt 的 file SHA 和 receipt SHA；
   - Run3 proposal 的 file SHA 和 manifest SHA；
   - Run2 terminal publication 的 file SHA 和 receipt SHA；
4. 要求：
   - `dispatch_ordinal == 3`；
   - `scientific_attempt_ordinal == 1`；
   - `third_dispatch_authorized == true`；
   - GPU/planner/scene 为 true；
   - physical/root/formal/Stage 1/training 为 false；
5. 验证科学 runner、Guard、targets、candidate、query caps 完全未变；
6. 重新计算 9 个派生 cache 路径的 UTF-8 字节数，全部不得超过 100；
7. 验证 output、guard、cache-job 在启动前均不存在；
8. 再调用原 F2 Guard。

运行后 wrapper 必须自动调用只读 auditor V1.2，不得只信任 base Guard 的 exit code。Run2 已经证明，base Guard 可以在 `job_pass=false`、`job_error!=null` 时仍报告 transport `completed`。fileciteturn349file0L1-L7

Auditor V1.2 必须分别输出：

```yaml
evidence_integrity_pass:
scientific_gate_pass:
infrastructure_failure:
cleanup_pass:
```

其中科学成功只有一种：

```text
error == null
inside 5/5
beside 6/6
both_chains_pass == true
aggregate planner queries == 11
cleanup/baseline == true
```

完成 admission wrapper、auditor V1.2 和 CPU 负例后，**不需要再次回来申请 F2 外审**，可以执行唯一一次 Run3。

需要注意：82 字节短路径是高可信的修复假设，但仍没有经过 GPU 实测，所以 Run3 的性质是“验证基础设施修复并取得首次科学结果”，不能预先写成“F2 已修好”。

---

# 二、F3：根因判断正确，但现有 pre-close Gate 还漏看了“运动途中”

## 1. 当前进度判断成立

F3 目前已经证明：

- r1505、r2180、r3677 的 Stage A/B planner 均通过；
- 加上 retained r0005，共进行 4 次 physical；
- 每次 physical 都真实执行了 7 次 planner query；
- planner 4/4 可解；
- physical 0/4；
- 全部在 lift 后 selected contact fraction 为 0；
- 全部没有把瓶子抬离支撑面；
- 所有 scene、GPU、cache、lease 清理干净。fileciteturn331file0L1-L2 fileciteturn338file0L1-L7

四条 trace 的复查也支持 Codex 的根因判断：不是 26-D action layout、夹爪映射或后端 verifier 错误，而是 CuRobo 认为路径可行，但 SAPIEN 中出现了真实机械臂自碰、支撑物碰撞和瓶子提前位移。fileciteturn320file0L1-L7

## 2. 现有 Gate 的关键缺口

当前 `evaluate_preclose_stage()` 接收的是每个阶段的**单个 snapshot**，只在这个 snapshot 上检查：

- qpos error；
- EEF error；
- bottle displacement；
- contact pairs。fileciteturn336file0L1-L7

而 replay 代码对每段只读取：

```text
pregrasp 的结束行
grasp 的结束行
```

也就是说，它没有检查整段运动中的所有 contact rows。fileciteturn342file0L1-L7

这会留下一个直接针对当前根因的漏洞：

```text
机械臂在 pregrasp 运动中途撞到了自己
→ 随后脱离碰撞
→ 结束点看起来正常
→ 现有 Gate 可能放行 close
```

或者：

```text
中途碰了瓶子并将其推开
→ 瓶子又部分回到原处
→ 结束点位移小于 10 mm
→ 现有 Gate 可能漏报
```

因此，20/20 单元测试和 4/4 旧 trace 端点拒绝说明 Gate 的基本逻辑正确，但还不足以批准新的 GPU physical job。

## 3. 批准实现 F3 Gate V1.1

批准范围仅为 CPU 实现和测试：

```yaml
f3:
  decision: APPROVE_CPU_ONLY_F3_FULL_WINDOW_PRECLOSE_GATE_AND_CANDIDATE_FREEZE

  gpu_execution_authorized: false
  planner_execution_authorized: false
  scene_execution_authorized: false
  physical_execution_authorized: false
  shared_v_authorized: false
  root_authorized: false
  raw_authorized: false
  formal_authorized: false
```

Gate V1.1 必须：

1. 对 pregrasp 和 grasp 两个 segment 的 `start+1 ... end` **所有 trace rows** 做检查；
2. 任意一帧出现执行臂 self collision，立即失败；
3. 任意一帧出现执行臂与 table/pad 的 physical hit，立即失败；
4. pregrasp 阶段任何 arm–bottle physical contact 均失败；
5. grasp 阶段只允许 selected gripper links 与 bottle 接触，其他 arm link 接触仍失败；
6. 任意相关 contact pair 缺少完整 physical-contact signal，fail closed；
7. 检查整段的**最大 bottle displacement**，而不是只检查结束点；
8. 保留 segment 结束点的 qpos 和 EEF tracking 检查；
9. 保存：
   - first failure row；
   - first failure pair；
   - maximum bottle displacement；
   - maximum relevant impulse；
   - minimum signed separation；
10. Gate 失败时必须在 close 之前停止。

新增至少四个测试：

```text
transient_mid_segment_self_collision
transient_mid_segment_support_collision
bottle_bump_then_return
incomplete_contact_signal_in_middle_row
```

四条旧 trace 也必须重新按完整 segment window 回放。

---

# 三、F3 的精确候选冻结规则

当前 3840 条 universe 的代码枚举顺序是固定的：

```text
selected assets
→ left/right
→ lower/upper
→ contact 0..7
→ rotation 0..9
→ pregrasp 0.06/0.09/0.12
```

每条 recipe 均按 canonical JSON 生成 SHA。fileciteturn337file0L1-L7

我按该代码和当前 selected asset 顺序重新计算，批准下面这条冻结规则。

## 1. 规则

排除已消耗：

```text
r0005
r1505
r2180
r3677
```

候选生成变换：

```text
arm'             = opposite(old.arm)
region'          = opposite(old.region)
contact'         = (old.contact + 4) mod 8
rotation'        = (old.rotation + 5) mod 10
pregrasp_distance = 0.12 m
```

候选顺序：

1. 先放 base13 + left 的历史 audit lead 对应新候选；
2. 再按剩余原资产顺序 base15、base5、base4；
3. 每个 asset 恰好一个候选；
4. 不根据本轮 GPU 成败替换 recipe；
5. 不在线搜索、不 fallback、不换 seed。

把 base13 放第一只是固定的预注册优先级，不代表它已经通过当前协议。旧 trace 的 contact fraction 1.0、zero breaks 只能作为线索，其完整 semantic probe 当时并未通过。fileciteturn321file0L1-L7

## 2. 精确候选

| 顺序 | recipe | asset | arm / region | contact / rotation / pregrasp | recipe SHA-256 |
|---:|---|---:|---|---|---|
| 1 | `f3-final-pose-v3-r3063` | 13 | left / lower | 6 / 0 / 0.12 | `e612c0a829559966bae718bd3a995fe4d87b731de2680c38a56f325cedf2fb79` |
| 2 | `f3-final-pose-v3-r0861` | 15 | right / upper | 4 / 6 / 0.12 | `546859c30a0d068f1ca8103e5def09a450a84016980d766d479949d908ceadbd` |
| 3 | `f3-final-pose-v3-r1401` | 5 | left / upper | 6 / 6 / 0.12 | `599934ea0592589f4daa7b9daffc72c42a5a527ce2bd50911fd3b85a80ee883d` |
| 4 | `f3-final-pose-v3-r2526` | 4 | right / lower | 4 / 1 / 0.12 | `2b9c30ea466d6350b04add4102eda9aa004f22f9589224284ed5851dd681b5ae` |

按下面 payload 计算的 candidate-freeze rule SHA 为：

```text
e2d7956374b660708ebdc090c9b4208435f9ff31933c7bf18017107323144579
```

必须绑定的 universe SHA：

```text
4bc99d0957dcd2dd955e6060cbe2a077cec1a2cd71ef7eecf1eca9375b16de46
```

这四个候选是**确定性多样化候选**，不是 CPU 已证明无碰撞的候选。当前 proposal 中的：

```text
pending_cpu_collision_screen
```

建议改名为：

```text
pending_deterministic_candidate_freeze
```

避免把静态 recipe 变换误写成“已经完成真实碰撞筛选”。

## 3. 第二次外审仍然需要

F3 的 GPU 物理执行暂不批准。Codex 完成以下材料后，做一次窄范围复审：

```text
1. F3_CANDIDATE_FREEZE_RULE_V1.json
2. 四条完整 recipe + exact SHA 的 candidate-frozen manifest
3. Gate V1.1 source
4. Gate V1.1 test receipt
5. 四条旧 trace 的 full-window replay receipt
6. candidate-frozen runtime/Guard CPU preflight
```

复审不再研究旧 0/4 根因，也不重新选候选，只检查：

- 候选是否与上表完全一致；
- full-window Gate 是否正确接入；
- 预算是否仍为 52 queries / 12 scenes / 4 attempts；
- shared-V、suffix、root、raw、formal 是否仍为 0；
- Gate 失败是否确实在 close 前停止。

通过后才可批准最多 4 个候选的 bounded micro：

```text
plan pregrasp/grasp/25mm lift
→ execute pregrasp
→ full-window Gate
→ execute grasp
→ full-window Gate
→ conditional close 0.50
→ hold 250
→ conditional 25mm lift
→ contact/off-support/transform Gate
→ stop
```

达到 2 个 pass 后立即停止。第一条按冻结顺序通过的 candidate 作为后续 selected candidate，第二条只作为独立可行性确认；不得自动进入 shared-V 或 no-suffix。

---

# 四、F4：此前要求的 finalizer 加固已经完成

这一部分 Codex 做得很好。

当前 V2.1 已经真实实现：

- 磁盘 root receipt 与内存结果一致性；
- 三条 branch receipt 重读和 exact program order；
- 三个 raw artifact 重算完整性；
- 三个 MP4 重验；
- 每个 suffix 分别验证 `12 + 30 = 42`；
- aggregate 126 和总 planner 136；
- 11 个唯一 scene IDs；
- 精确 phase multiset `1+3+1+3+3`；
- 3 条 branch planner delta 为 0；
- final-state equivalence；
- POST_CHILD 的 exit/job/finalizer/1-root+3-trajectories/cleanup 等价性。fileciteturn354file0L1-L7

测试矩阵也确实覆盖了 finalizer 18/18、环境 21/21、lineage 5/5、executable identity 3/3、POST_CHILD 11/11 以及 NumPy serialization。fileciteturn311file0L1-L2 fileciteturn312file0L1-L7

所以：

> **F4 的物理代码和 root finalizer 不需要再改。**

---

# 五、F4 当前仍不能批准 GPU 的四个精确原因

## 1. Approved schema 没有要求完整执行权限

当前 `validate_manifest_semantics()` 在 execution-authorized 模式下只强制：

```text
approved
gpu_execution_authorized
physical_execution_authorized
```

但实际 root 还会创建 scene、调用 planner、执行 root。当前合同没有要求：

```text
planner_execution_authorized
scene_execution_authorized
root_execution_authorized
```

全部显式为 true。fileciteturn351file0L1-L7

Proposal 和 approved manifest 都应该显式包含六层权限：

```yaml
approved:
gpu_execution_authorized:
planner_execution_authorized:
scene_execution_authorized:
physical_execution_authorized:
root_execution_authorized:
```

Proposal 六项全部 false；approved 六项全部 true。

---

## 2. 当前审批解析使用字符串包含，而不是结构化精确决定

当前 contract 会读取外审 Markdown，然后判断“申请字符串是否出现在文本里”。这意味着，一个明确的拒绝文档只要引用了申请字符串，也可能被错误解释为批准。fileciteturn352file0L1-L7

因此，本轮我没有在回复中复写当前 F4 申请中的旧批准字符串。

Runtime V2.2 必须改成只读取 self-hashed JSON decision receipt，例如：

```yaml
schema_version: cmf_external_execution_decision_v1
decision: F4_ONE_ROOT_AUTHORIZED_RUNTIME_V2_2
authorized: true

candidate: f4-slot-corridor-hv2-r01
programs:
  - F4-ABC
  - F4-ACB
  - F4-BAC

maximum_root_invocations: 1
maximum_accepted_development_roots: 1
maximum_accepted_development_trajectories: 3
maximum_formal_trajectories: 0
```

所有字段必须 exact equality；Markdown 仅供人阅读，不再作为可执行 authority parser 的事实源。

还必须增加负例：

```text
一份 denial 文档引用了旧 V2 申请文字
→ 必须拒绝
```

---

## 3. Runner 只证明 lease 文件存在，没有证明 Guard 正持有锁

当前 runner-entry 验证了：

- lease 路径一致；
- lease 文件存在；
- GPU index/UUID 等环境一致。

但没有证明 Guard 此时仍持有该文件的 exclusive flock。fileciteturn353file0L1-L7

而 CPU lifecycle fixture 明确使用的是一个“存在但未 flock”的 synthetic marker，因此现有测试也没有覆盖真正的锁持有关系。fileciteturn316file0L1-L7

V2.2 runner 应：

```python
打开 lease 文件
尝试 LOCK_EX | LOCK_NB
```

预期结果必须是 `BlockingIOError`，证明 Guard 正在持锁。

若 runner 反而成功取得锁，说明 Guard 没有持锁，必须 fail closed。

CPU fixture 中由 parent process 真实 flock；另加 unlocked lease 负例。

---

## 4. Guard 只做一次即时 GPU post-snapshot

当前 F4 Guard 在 child 结束后只调用一次 `nvidia_snapshot()`，若这一瞬间 GPU 还处于 P0 或短暂 utilization 非零，就会把正常 CUDA teardown 误判为 cleanup failure，随后才删除 cache 和释放 lease。fileciteturn350file0L1-L7

这不是理论问题。F3 的真实 clean postcheck 已经出现：

```text
第一次：P0 / utilization 91%
第二次：P8 / utilization 0%
```

最终 GPU 实际是干净的。fileciteturn338file0L1-L7

对于 F4 这种只允许一次 root 的授权，一次瞬时误判会浪费唯一机会。

V2.2 Guard 必须：

1. child 结束并确保 process group 退出；
2. 删除本 job cache；
3. **继续持有 lease**；
4. 最多进行 13 次 GPU snapshot，间隔 5 秒；
5. 每次都绑定相同 physical index 和 UUID；
6. 一旦达到 fresh-idle baseline 即通过；
7. 只有全部轮询仍不干净才失败；
8. 最后才释放 lease；
9. 保存所有 poll snapshots、最终选中 GPU、poll count。

应增加测试：

```text
P0/91% → P8/0%         PASS
始终非 idle             FAIL
中途 UUID/index 变化     FAIL
snapshot 命令报错        FAIL
```

---

# 六、F4 正式裁决

```yaml
f4:
  decision: REVISE_TO_RUNTIME_V2_2_AUTHORITY_AND_GPU_COOLDOWN

  scientific_status: PHYSICALLY_QUALIFIED
  finalizer_status: PASS_RETAIN_UNCHANGED
  gpu_execution_authorized_now: false

  immutable_scope:
    candidate: f4-slot-corridor-hv2-r01
    programs: [F4-ABC, F4-ACB, F4-BAC]
    canonical_prefix_arm: right
    suffix_arm: left

    planner_queries: 136
    fresh_scenes: 11
    robot_action_scenes: 7
    branch_executions: 3
    raw_trajectories: 3
    debug_videos: 3
    accepted_development_roots: 1
    accepted_development_trajectories: 3
    formal_trajectories: 0

    candidate_search: false
    seed_retry: false
    fallback: false
    second_root: false
    automatic_retry: false

  exact_v2_2_changes:
    - structured exact JSON approval receipt; no Markdown substring authority
    - explicit planner/scene/root authorization flags
    - proposal and approved root_status separation
    - proof that Guard still holds lease flock
    - bounded GPU teardown polling before lease release
    - preserve the V2.1 finalizer logic and its 18/18 matrix

  new_external_review_required: true
```

建议状态名称改为：

```text
Proposal:
CPU_HARDENING_COMPLETE_AWAITING_EXTERNAL_APPROVAL

Approved:
ONE_DEVELOPMENT_ROOT_AUTHORIZED
```

不要继续让已完成 CPU hardening 的 proposal 声称：

```text
INFRASTRUCTURE_FINAL_HARDENING_REQUIRED
```

V2.2 完成后，下一轮外审只需要检查：

```text
manifest contract
Guard
lease test
cooldown test
structured decision schema
proposal/preflight hashes
```

不再复查 F4 finalizer 18/18，也不重新研究 Run9–Run14 或机器人动作。

---

# 七、接下来的最高效工作顺序

## CPU 阶段可以同时推进

### A. F2

完成：

```text
Run3 admission wrapper
structured decision receipt binding
auditor V1.2
CPU negative tests
approved manifest
```

F2 已获得本轮有条件授权，不需要下一次外审。

### B. F3

完成：

```text
full-window Gate V1.1
四条旧 trace 全窗口 replay
精确四候选 freeze
candidate-frozen proposal
runtime/Guard CPU preflight
```

然后做一次窄范围外审。

### C. F4

完成：

```text
Runtime V2.2 authority schema
real held-lease validation
GPU teardown bounded polling
对应 CPU tests
new proposal
```

然后做一次窄范围外审。

这三项均可在没有 GPU job 时并行做纯 CPU 工作。

---

## GPU 执行阶段

第一项固定为：

```text
两轮完整 fresh-idle snapshot
→ F2 Run3
→ auditor V1.2
→ clean postcheck
```

F2 后，不必人为等待 F3。F3 与 F4 没有科学依赖：

```text
谁先完成 CPU 修复并取得精确外审批准
→ 谁在 F2 clean postcheck 后先串行执行
```

但 F2、F3、F4 之间仍禁止并行 GPU job，也不能共享 lease。

只有以下情况阻塞整个队列：

```text
cleanup failure
orphan process
GPU 未回 baseline
UUID/index 不一致
artifact/terminal 无法封存
```

单个 family 的科学 Gate 失败，但清理完整，不应阻塞其他 family。

---

# 八、每个结果之后怎么走

## F2 Run3

### 两条 route 都通过

进入：

```text
F2 controlled-insertion development root V2
```

仍需单独设计/外审，不自动启动。

### planner 正常执行但路线失败

这是首次有效科学结果。停止 F2，不再批准第四次 dispatch；根据首个失败 segment 决定是否保留 F2 family。

### NVRTC 或其他基础设施仍失败

封存失败证据。当前决定不授权继续换路径和第四次 dispatch。

---

## F3 micro-Gate

### 2 个候选通过

冻结：

- 第一条按预注册顺序通过的 candidate 为 selected；
- 第二条为独立确认。

然后设计独立 3-scene no-suffix Gate，不自动进入 shared-V/root。

### 只有 1 个通过

不继续。先审查 pass 和三个 fail 的差异，不能直接把唯一 pass 当 root candidate。

### 0/4

停止当前 bottle family 搜索，进入 object-family 或 scene-layout redesign，不继续从 3840 universe 临时挑候选。

---

## F4 one-root

### 成功

增加：

```text
1 development root
3 development r_pc trajectories
```

随后进入 F4 的 `r_inv_path/r_inv_motion` 设计，仍不进入 Stage 1。

### 失败

保留 exact failure evidence，不自动执行第二个 root、不换 seed、不换 candidate。

---

# 九、F1 的下一步

F1 当前已经有 5 个 development roots 和 15 条 `r_pc`，继续追加同类 `r_pc` 的边际价值很低。

可以同步进行纯 CPU 设计：

```text
F1 r_inv_path schema
F1 r_inv_motion schema
r_pc ↔ r_inv pairing contract
event-start alignment
same-intent / different-realization validation
root-atomic 9/9 finalizer
```

但在这些 schema、verifier 和预算外审完成前，不授权新 F1 GPU 数据。

---

# 可直接转交 Codex 的机器可读回复

```yaml
review_base:
  vault_head: 3e1bab4d51ad43ceb10b4b06f49a9551a0879c12
  stage0_rerun: false
  stage1: false
  formal360: false
  training: false
  h_reveal: false
  compression: false
  pi05: false

f1:
  decision: KEEP_5_DEVELOPMENT_ROOTS_AND_15_RPC
  next: DESIGN_R_INV_PATH_AND_R_INV_MOTION_CPU_ONLY
  new_gpu_authority: false

f2:
  decision: APPROVE_ONE_F2_SHORT_TMPDIR_INFRASTRUCTURE_RECOVERY_RUN3
  approval_type: CONDITIONAL_EXACT_ONE_DISPATCH
  dispatch_ordinal: 3
  scientific_attempt_ordinal: 1

  required_before_execution:
    - exact self-hashed structured decision receipt
    - new admission wrapper binding this review and Run3 proposal
    - exact short-cache path validation, every derived path <=100 UTF-8 bytes
    - approved manifest with third_dispatch_authorized=true
    - read-only auditor V1.2
    - CPU manifest/Guard/admission/auditor negative tests
    - output, guard and cache-job absent
    - commit and push

  scientific_scope:
    inside_queries: 5
    beside_queries: 6
    total_queries: 11
    planner_scenes: 2
    physical: 0
    branch: 0
    raw: 0
    video: 0
    root: 0
    formal: 0

  unchanged:
    - scientific runner
    - Guard
    - targets
    - candidate
    - planner seeds
    - thresholds

  no_fourth_dispatch: true
  no_auto_root: true
  no_retry: true
  second_review_required: false

f3:
  decision: APPROVE_CPU_ONLY_F3_FULL_WINDOW_PRECLOSE_GATE_AND_CANDIDATE_FREEZE
  gpu_authorized: false

  required_gate_revision:
    version: V1.1
    audit_scope: every trace/contact row in pregrasp and grasp segments
    max_bottle_displacement_over_full_segment: true
    transient_self_collision_rejected: true
    transient_support_collision_rejected: true
    transient_bottle_bump_rejected: true
    incomplete_mid_segment_signal_rejected: true
    stop_before_close_on_failure: true

  candidate_freeze:
    universe_sha256: 4bc99d0957dcd2dd955e6060cbe2a077cec1a2cd71ef7eecf1eca9375b16de46
    rule_sha256: e2d7956374b660708ebdc090c9b4208435f9ff31933c7bf18017107323144579
    excluded:
      - f3-final-pose-v3-r0005
      - f3-final-pose-v3-r1505
      - f3-final-pose-v3-r2180
      - f3-final-pose-v3-r3677
    ordered_candidates:
      - id: f3-final-pose-v3-r3063
        sha256: e612c0a829559966bae718bd3a995fe4d87b731de2680c38a56f325cedf2fb79
      - id: f3-final-pose-v3-r0861
        sha256: 546859c30a0d068f1ca8103e5def09a450a84016980d766d479949d908ceadbd
      - id: f3-final-pose-v3-r1401
        sha256: 599934ea0592589f4daa7b9daffc72c42a5a527ce2bd50911fd3b85a80ee883d
      - id: f3-final-pose-v3-r2526
        sha256: 2b9c30ea466d6350b04add4102eda9aa004f22f9589224284ed5851dd681b5ae
    online_search: false
    fallback: false
    success_conditioned_substitution: false

  second_review_required_before_gpu: true

f4:
  decision: REVISE_TO_RUNTIME_V2_2_AUTHORITY_AND_GPU_COOLDOWN
  gpu_authorized: false

  accepted_without_rework:
    - Runtime V2.1 disk finalizer
    - finalizer 18/18 tests
    - raw and MP4 independent integrity verification
    - exact per-suffix 12+30=42 accounting
    - exact 11-scene unique phase validation
    - POST_CHILD result/finalizer/count equivalence

  required_v2_2_changes:
    - replace Markdown substring approval with exact self-hashed JSON decision receipt
    - require approved/gpu/planner/scene/physical/root authority flags explicitly
    - use proposal root_status CPU_HARDENING_COMPLETE_AWAITING_EXTERNAL_APPROVAL
    - use approved root_status ONE_DEVELOPMENT_ROOT_AUTHORIZED
    - prove Guard still holds exclusive lease flock at runner entry
    - make CPU lifecycle fixture hold a real flock
    - add unlocked-lease negative test
    - poll GPU baseline up to 13 times at 5-second intervals while lease remains held
    - persist every cooldown snapshot and exact UUID/index binding
    - add transient-busy, never-idle, UUID-change and snapshot-error tests
    - preserve finalizer implementation unchanged

  future_structured_decision_enum: F4_ONE_ROOT_AUTHORIZED_RUNTIME_V2_2
  new_external_review_required: true

execution_order:
  - complete all CPU work in parallel
  - two complete stable GPU snapshots
  - F2 Run3
  - F2 auditor and clean postcheck
  - run whichever of F3 or F4 next receives exact approval
  - never run F2/F3/F4 GPU jobs concurrently

global_stop_conditions:
  - cleanup failure
  - orphan process
  - GPU baseline not restored
  - GPU UUID/index mismatch
  - incomplete terminal or artifact sealing

scientific_failure_with_clean_cleanup_blocks_other_families: false
```

这条回复本身就是对合并审阅文档的正式外审结果。

---

If you want, I can:

- 继续讲解F4后的关键缺口内容
- 具体说明F2短路径基础设施恢复Run3的实施步骤
- 解释F3全窗口Preclose Gate V1.1的设计与测试要点
