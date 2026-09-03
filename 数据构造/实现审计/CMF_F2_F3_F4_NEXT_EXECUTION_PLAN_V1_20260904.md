# F2/F3/F4 后续修复与数据构造执行计划 V1

- 日期：2026-09-04
- 当前证据 Vault HEAD：`ee4b530791d02a4fafabf459a0c7ca34901f0efe`
- 当前外部阻塞：fvl05 NVIDIA 驱动不可见，`nvidia-smi` 无法返回 GPU0–7 实时状态
- 当前正式数据：`0 roots / 0 trajectories`
- 本计划不授权：Stage 0 重跑、Stage 1、formal 360、训练、H-reveal、compression、π0.5
- 本计划对 F4 的处理：**重新纳入 CPU 修复计划，但不立即授权 GPU 重跑**

---

## 0. 总体裁决

### F2

保留当前已经签发且未消耗的 11-query planner-only Gate，不修改它的 manifest、Guard、runner 或任何绑定文件。驱动恢复后，F2 是第一个执行的 GPU planner-only job。

若 inside 5 段与 beside 6 段全部通过，不得直接复用旧 `F2TopContactRootControllerV1` 重跑 root。旧 root 的 inside execution 仍继承历史 gravity-drop 语义。必须另建一个真正使用 controlled insertion V2 的 strict-prefix root V2。

### F3

当前 wiring 修复方向正确，但现有 V1 approved manifest 存在 planner 预算表达不完整的问题：

- replacement Stage A/B planner 最多 30 queries；
- 最多 4 个 physical candidate，每个 `execute_f3_level2_physical_v1` 又会调用 7-query planner；
- 真实 aggregate planner 上限因此可能达到 `30 + 4 × 7 = 58`；
- 当前 runner 即使触发 `conditional_no_suffix`，也固定写 `conditional_no_suffix_executed=false`。

因此，当前未消耗的 F3 V1 manifest **不得直接启动**。应在不改变 tuple、overlay、物理 Gate 和“一次 reissue”序号的前提下，发布 V2 manifest/runner contract，明确：

- qualification planner cap = 30；
- physical planner cap = 7 per candidate；
- aggregate planner cap = 58；
- planner scenes = 6；
- physical scenes = 4；
- 本 job 的 no-suffix scenes = 0；
- 3-scene no-suffix diagnostic 留给后续独立 Gate。

V1 未消费，所以 V2 是对同一次 reissue 的未消费替换，不是第二次 reissue。

### F4

F4 不应按“任务失败”永久放弃。正确状态应改为：

`F4_PHYSICALLY_QUALIFIED_ROOT_INFRASTRUCTURE_BLOCKED`

F4 已有 `ABC / ACB / BAC = 3/3` 真实物理成功、same-current、same-anchor 和 final-state equivalence 证据。Run10–Run14 没有一次在真实 branch 动作上失败；最后失败是 Guard 与 runner 对目录生命周期的相互矛盾。

现在立即允许的范围是：

`REOPEN_F4_FOR_CPU_INFRASTRUCTURE_REPAIR_ONLY`

禁止范围仍是：

- F4 GPU execution = false
- F4 scene/planner/physical/root execution = false
- 需要完成 Runtime V2 和生命周期回归测试后，再提交一次新的外审请求，取得一个精确 root 授权。

---

# 1. 当前冻结原则

在 F2/F3 现有授权被消费或明确 supersede 前：

1. 不得修改 RoboTwin active `controlled_multi_future` 源码树。
2. 不得修改以下已签发文件：
   - `F2_CONTROLLED_INSERTION_ROUTE_GATE_APPROVED_RUN1_MANIFEST_V1.json`
   - `f2_controlled_insertion_route_gate_run1_runtime_v1/guarded_launcher.py`
   - `f2_controlled_insertion_route_gate_run1_runtime_v1/job_runner.py`
   - `F3_ZERO_SCENE_WIRING_REISSUE_APPROVED_RUN1_MANIFEST_V1.json`
   - `f3_replacement_reissue_run1_runtime_v1/guarded_launcher.py`
   - `f3_replacement_reissue_run1_runtime_v1/job_runner.py`
   - `f3_replacement_reissue_proposal_v1/job_runner_overlay.py`
3. 所有未来实现放在新的 versioned 路径、独立 scratch checkout 或 proposal-only review snapshot 中。
4. 不得通过修改已绑定文件后重新计算 hash 来“延续”旧授权。
5. F2 和 F3 不并行启动。驱动刚恢复时先运行低风险的 F2 planner-only Gate，再完成 GPU postcheck，之后才运行 F3。

---

# 2. 驱动恢复 Gate

Codex 不负责修改共享服务器驱动，不执行重启、重装或内核模块操作。服务器管理员恢复后，执行以下只读 Gate。

## 2.1 必须全部通过

连续两轮、间隔至少 10 秒：

1. `nvidia-smi -L` 成功；
2. GPU row query 成功返回恰好 8 张卡；
3. compute-app query 成功；
4. 两轮 GPU index→UUID 映射完全相同；
5. 要使用的卡满足：
   - 无 compute process；
   - memory 在既有 fresh-idle 阈值内；
   - utilization=0；
   - P-state 满足 Guard 的 idle 规则；
6. F2/F3 lease 文件可独占；
7. 两个 job 的 output namespace、guard directory、cache/job namespace 仍不存在；
8. active RoboTwin HEAD、tracked worktree、controlled source SHA、runner/Guard/manifest SHA 全部与清单一致。

## 2.2 未通过时

- 不启动 Guard；
- 不把 `nvidia-smi` 失败记作 F2/F3 job consumption；
- 只发布新的 driver blocker receipt；
- 不尝试使用“看起来空闲但无法读取状态”的 GPU。

---

# 3. Phase A：F2 当前 11-query planner-only Gate

## 3.1 执行顺序

驱动恢复后首先执行当前已签发的 F2 job：

- inside：5 targets；
- beside：6 targets；
- aggregate planner cap：11；
- fresh planner scenes：2；
- physical/branch/raw/video/root/formal：全部 0。

两条 chain 均从 sealed actual prefix-end qpos 开始，各执行一次，无 fallback、无搜索、无自动 continuation。

## 3.2 终端判定

不能只看 child exit code。当前 runner 会正常写 terminal，即使路线 planner fail 也可能以进程成功退出。

必须读取并发布：

- `job_terminal.pass`
- `result.both_chains_pass`
- inside 每个 segment receipt
- beside 每个 segment receipt
- live planner query count
- cleanup/post-GPU snapshot
- output/guard/cache/lease 状态

通过条件必须同时满足：

```text
inside 5/5 planner pass
beside 6/6 planner pass
aggregate planner queries = 11
physical execution = 0
branch execution = 0
raw/video/root/formal = 0
cleanup pass
GPU returned to baseline
```

## 3.3 F2 Gate 失败后的处理

### inside 失败

按首个失败 segment 分类：

- `inside_controlled_high_carry`：
  - 说明高位水平转移本身不可达；
  - 不进入 physical；
  - 只允许发布 reachability evidence，不允许在当前 Gate 换姿态或换目标。

- `f2_v2_preinsert_30mm`：
  - 检查 opening normal、preinsert orientation、实际 EEF→actor transform 和腕部关节余量；
  - 不改 cavity/verifier；
  - 后续若修，必须是新的 route proposal。

- `f2_v2_controlled_descend_to_support`：
  - 检查目标 orientation、support pose、末端关节极限；
  - 同时做 carried-can full-OBB/rim swept-envelope CPU audit；
  - 不允许退回 gravity drop。

- retreat/neutral 失败：
  - 只修回撤/回中路径，不改 inside 目标和 release/verifier。

### beside 失败

- 固定 candidate index 2，不自动尝试其他 candidate；
- 记录失败 segment、终端 qpos、关节余量；
- 后续变更必须是新的 exact route proposal。

## 3.4 F2 Gate 全部通过后的下一步

不得直接重跑旧 root。先实现以下 proposal-only 组件。

### 新实现

`F2TopContactControlledInsertionRootV2`

必须：

1. 复用已成功的 top-contact8/rotation0/can0+box2/left candidate；
2. canonical prefix 仍为 exact pregrasp→grasp→close→12cm lift；
3. inside planner targets 必须与通过的 5-target Gate 字节级一致；
4. beside planner targets 必须与通过的 index2 六段 Gate 字节级一致；
5. on 继续使用已通过的 4-target route；
6. branch execution 只消费 frozen controls，planner delta 必须为 0；
7. inside 禁止调用 standalone executor 重新执行 approach/grasp/lift；
8. inside 必须实现一个 post-prefix controlled insertion executor：
   - execute high carry；
   - execute preinsert；
   - execute controlled descend；
   - 50-frame continuous box support/stability/opening-projection Gate；
   - 五级慢释放 `0.2/0.4/0.6/0.8/1.0`，每级 10 frames；
   - 250-frame post-release settle；
   - retreat；
   - neutral；
   - final strict true-cavity OBB；
   - inside/on/beside 互斥；
   - gripper full open；
   - arm rest/stationary；
   - no table contact where forbidden；
9. 为 carried can 加 CPU 几何必要条件：
   - high-carry endpoint OBB；
   - preinsert endpoint OBB；
   - descend swept opening projection；
   - facility clearance；
   - 明确这只是必要条件，不能替代真实 contact Gate。

### F2 root 精确预算

根据当前 root orchestrator 和已运行证据，源结构应为：

```yaml
canonical_prefix_planner_queries: 3
inside_suffix_queries: 5
on_suffix_queries: 4
beside_suffix_queries: 6
aggregate_planner_queries: 18

fresh_scenes: 11
robot_action_scenes: 7
branch_executions: 3
raw_trajectories: 3
debug_videos: 3
accepted_development_roots: 1
accepted_development_trajectories: 3
formal_trajectories: 0
```

场景数必须包括：

- pristine 1；
- task-feasibility 3；
- canonical-prefix reference 1；
- suffix preflight 3；
- branch execution 3。

CPU tests 必须从实际 target 数和 orchestrator 阶段推导预算，禁止手写一个与源码脱节的上限。

### F2 root 停止条件

- 任一 manifest/Guard/source/binding/scene/current/anchor/prefix/planner/accounting error：立即停止；
- 任一 branch physical/verifier 失败：root 不接收；
- 不 fallback、不第二 root、不自动调参；
- 只有 3/3 branch、raw、MP4、verifier、cleanup 和 atomic finalizer 全过，才接收 1 development root。

完成 proposal 和 CPU lifecycle regression 后，提交新的 GPT review request；不得自动执行。

---

# 4. Phase B：F3 未消费 V1 的预算修正

## 4.1 为什么必须先修清单

当前 F3 runner 的真实代码路径是：

1. 三个 replacement candidate 各做 Stage A（最多 3）；
2. Stage A survivor 再做 Stage B（最多 7）；
3. replacement qualification 总上限 30；
4. 若有新 survivor，则 retained r0005 + new survivors 最多执行 4 个 physical candidates；
5. 每个 physical candidate 的 `execute_f3_level2_physical_v1` 又会运行一个 7-query planner chain。

因此最坏情况是：

```text
qualification planner = 30
physical planner = 4 × 7 = 28
aggregate planner = 58
```

当前 manifest 只有一个 `planner_query_cap=30`，而 wrapper 只检查 qualification count，没有检查 aggregate。这是授权计数歧义，不能在 GPU 恢复后直接运行。

## 4.2 创建 F3 V2 未消费替换

创建：

- `F3_ZERO_SCENE_WIRING_REISSUE_APPROVED_RUN1_MANIFEST_V2.json`
- `f3_replacement_reissue_run1_runtime_v2/guarded_launcher.py`
- `f3_replacement_reissue_run1_runtime_v2/job_runner.py`

保持不变：

- overlay SHA；
- retained r0005；
- replacements 仅 r1505/r2180/r3677；
- tuple 顺序；
- scene binding；
- physical Gate；
- verifier；
- one reissue ordinal；
- no fallback；
- no second reissue。

新增明确字段：

```yaml
replacement_qualification_planner_query_cap: 30
physical_planner_query_cap_per_candidate: 7
physical_candidate_cap: 4
aggregate_planner_query_cap: 58
planner_scene_cap: 6
physical_scene_cap: 4
aggregate_scene_cap: 10
conditional_no_suffix_executed_in_this_job: false
conditional_no_suffix_scene_cap_in_this_job: 0
reserved_next_no_suffix_scene_cap: 3
formal_trajectory_cap: 0
```

V2 wrapper terminal必须重新计算：

```text
aggregate =
replacement_planner_queries
+ sum(physical_rows[*].physical_planner_queries)
```

并校验：

- qualification ≤30；
- each physical planner ≤7；
- physical count ≤4；
- aggregate ≤58；
- total scenes ≤10；
- no-suffix scenes =0。

V1 manifest 标记 `SUPERSEDED_UNCONSUMED_BY_F3_REISSUE_V2_BUDGET_CLARIFICATION`。这不算第二次 reissue。

---

# 5. Phase C：执行 F3 V2 Gate

F2 postcheck 完整通过且 GPU 再次 fresh-idle 后，执行 F3 V2。

## 5.1 planner阶段

新 tuple 仍严格为：

1. `bottle5/right/lower/contact2/rotation1/r1505`
2. `bottle4/left/upper/contact0/rotation6/r2180`
3. `bottle13/right/upper/contact2/rotation5/r3677`

retained `bottle15/left/lower/contact0/rotation1/r0005` 的既有 Stage A/B qualification 只读复用，不重新规划。

每个 replacement：

- Stage A 3-query；
- Stage B 7-query lift-anchored；
- 无 fallback；
- 保存每段 receipt、qpos、target hash、cleanup。

## 5.2 physical阶段

只有至少一个 new planner survivor 时，才构成：

`retained r0005 + new survivors`

最多 4 个 physical candidates。

每个 candidate 只执行一次：

- pregrasp；
- grasp；
- close；
- settle；
- lift；
- lift-anchored center；
- hold；
- V+；
- V−；
- return；
- hold。

必须报告十个 frozen Gate：

- planner success；
- selected gripper contact continuity；
- bottle off support；
- grasp transform translation stability；
- grasp transform orientation stability；
- bottle linear stability；
- bottle angular stability；
- EEF tracking；
- shared-V realized amplitude；
- shared-V closed-loop return。

## 5.3 F3 终端分支

### A. 没有 new planner survivor

- physical=0；
- F3 停止；
- 按每个 tuple 的 Stage A/Stage B 首个失败分类；
- 不扩候选、不换 seed。

### B. 有 survivor，但 physical successes <2

- Gate 失败；
- 不执行 no-suffix；
- 优先检查：
  - 是否 precontact EEF tracking miss；
  - 是否抓取后接触不连续；
  - 是否未离桌；
  - 是否 V 中滑动；
  - 是否 return 后不稳定。
- 若最早失败是 precontact tracking，下一版应仿照 F2，在 close 前增加 position/orientation hard Gate；不能直接调 V/H 阈值。
- 若物理失败集中在右臂或特定资产，只报告 evidence，不按结果临时改 winner rule。

### C. physical successes ≥2

- 当前 Gate 通过；
- 仍然不能声称 no-suffix 已完成；
- 当前 runner 的 `conditional_no_suffix_executed` 是 false；
- 发布通过的 exact candidate 列表；
- 按预先冻结的候选顺序选择第一个 physical pass 作为 root winner，禁止为了实现方便临时挑左臂候选；
- 然后进入独立 no-suffix Gate。

---

# 6. Phase D：F3 candidate-bound no-suffix 与 root

## 6.1 为什么不能直接复用旧 diagnostic/root

现有 full F3 controller：

- 程序语义正确：shared first V 在 canonical prefix，suffix 执行剩余三个 V/H event；
- 但大量代码硬编码 left arm；
- `f3_selected_stable_grasp_contract_v1` 属于旧 asset13/left candidate universe；
- 现有 no-suffix diagnostic 只识别旧 `common_grasp_prefix_v2` 或 `contact_preserving_prefix_v11`；
- 新 physical winner 可能是 bottle15/5/4/13，且可能是 right arm。

因此必须新建 candidate-bound、arm-parametric 版本，不能把新 recipe 强塞入旧 contract。

## 6.2 新组件

建议：

- `F3SelectedRecipePrefixContractV1`
- `F3SelectedRecipeRootControllerV1`
- `F3SelectedRecipeSharedPrefixNoSuffixDiagnosticV1`
- `RoboTwinRealSapienF3SelectedRecipeRootV1Adapter`

必须绑定：

- exact recipe id/SHA；
- asset model；
- arm；
- grasp region；
- official contact；
- rotation；
- close target；
- scene binding；
- Stage A/B terminal receipts；
- physical success receipt；
- lift-anchored center；
- V/H amplitudes和现有 verifier thresholds。

所有 arm 访问均使用参数化 helper，不得写死 left。

## 6.3 no-suffix Gate

恰好 3 fresh scenes：

1. reference canonical prefix generation；
2. exact replay 1；
3. exact replay 2。

canonical prefix 必须包含：

- exact selected grasp；
- close/settle；
- lift；
- center；
- hold；
- shared first V；
- return center；
- acceptance settle。

不得：

- suffix planner；
- suffix execution；
- release；
- raw accepted root；
- formal data。

通过条件：

- 三场 current/anchor 等价；
- one reference + two exact replays；
- prefix action bytes/hash 完全相同；
- selected contact identity/continuity；
- bottle off support；
- grasp transform stable；
- shared first V realized；
- return and stability；
- cleanup 3/3。

## 6.4 F3 full root

程序保持：

- `VVHH`
- `VHVH`
- `VHHV`

prefix 已包含第一个 V。每条 suffix 由：

- 剩余 3 个 events；
- 每个 event 7 targets；
- return preplace/release/retreat/rest 4 targets；

构成 25-target suffix。

必须使用 frozen controls；branch execution planner delta=0。

不要预先手写 canonical-prefix planner 总数。先用 source-derived counter test 得到：

```text
root planner total =
canonical-prefix planner count
+ 3 × 25
```

然后冻结 exact budget。

场景预算仍应由 root orchestrator 推导为：

```text
fresh scenes = 11
robot-action scenes = 7
branch executions = 3
raw = 3
videos = 3
development root = 1
development trajectories = 3
formal = 0
```

只有 no-suffix 3/3 和完整 root CPU lifecycle tests 通过后，提交外审。不得自动执行。

---

# 7. Phase E：F4 重新纳入 CPU 修复

## 7.1 状态变更

新审计文件应写：

```yaml
family: F4
scientific_status: PHYSICALLY_QUALIFIED
template_evidence:
  isolation: 5/5
  full_programs: 3/3
root_status: INFRASTRUCTURE_BLOCKED_BEFORE_BRANCH
cpu_repair_authorized: true
gpu_execution_authorized: false
third_candidate_search_authorized: false
stage1_authorized: false
formal_data: false
```

不得写成：

- task failed；
- physical infeasible；
- candidate exhausted；
- abandoned。

## 7.2 已知 F4 失败链必须写入回归测试

- Run10：旧 0.10m slot-center check 与 r01 正表面间隙不一致；
- Run11：12 target-construction +30 chain 被错误报告为 30；
- Run12：`total_before` NameError；
- Run13：manifest 缺 `asset_hashes_by_family`；
- Run14：Guard 已创建 guard/cache，runner 共用 validator 又要求其不存在。

所有回归必须 fail before GPU if重新出现。

## 7.3 新 Runtime V2

创建全新目录：

```text
数据构造/实现审计/f4_development_root_runtime_v2/
  manifest_contract.py
  guarded_launcher.py
  job_runner.py
  lifecycle_preflight.py
```

禁止修改或继续叠补丁于：

`f4_reopen2_runtime_v1/`

### manifest_contract.py

拆分：

```python
validate_manifest_semantics(...)
validate_runtime_paths(..., phase)
validate_bound_sources(...)
validate_job_budget(...)
```

phase 至少包括：

```yaml
PREPUBLICATION:
  output: absent
  guard_directory: absent
  cache_job: absent

GUARD_ENTRY:
  output: absent
  guard_directory: absent
  cache_job: absent

RUNNER_ENTRY:
  output: absent
  guard_directory: present
  guard_start_receipt: present_and_bound
  stdout_log: present
  stderr_log: present
  cache_job: present
  lease_and_uuid_environment: present

POST_CHILD:
  output: present_or_terminally_absent_with_error
  job_terminal: required_if_output_started
  guard_terminal: written_by_guard
```

不得再使用一个无 phase 的 `file=False` 检查同时服务 Guard 与 runner。

### guarded_launcher.py

可以复用现有基础 Guard 的 GPU snapshot/lease/cleanup primitives，但必须做到：

1. Guard 入口用 `phase=GUARD_ENTRY`；
2. Guard 创建目录/start receipt/cache；
3. child runner 用 `phase=RUNNER_ENTRY`；
4. 不 monkey-patch 一个会再次使用 GUARD_ENTRY 规则的 shared loader；
5. postcheck/cleanup/lease release 保持 fail-closed。

### job_runner.py

不要再调用旧 base runner 的 `main()` 并 monkey-patch loader。

推荐：

1. runner 自己执行 `RUNNER_ENTRY` validation；
2. 直接调用 hash-bound 的 `run_f4_development_r_pc_root` 函数，或将该函数复制为新的审计绑定实现；
3. 明确写 start/terminal；
4. terminal 分开报告：
   - contract；
   - task feasibility；
   - prefix；
   - suffix preflight；
   - branches；
   - raw/video；
   - verifier；
   - accepted root。

## 7.4 F4 生命周期 CPU 集成测试

测试必须真正模拟：

```text
all runtime paths absent
→ GUARD_ENTRY pass
→ create guard directory
→ write bound start receipt
→ create stdout/stderr
→ create cache/job and expected cache subdirs
→ launch runner --preflight-runner-entry as a subprocess
→ RUNNER_ENTRY pass
→ exact F4 dispatch selected
→ exact candidate/program/source/planner terminals resolved
→ stop before scene/GPU/output creation
→ cleanup temporary paths
```

必须有负例：

- guard dir missing at runner entry；
- cache missing；
- start receipt manifest hash错误；
- start receipt job id错误；
- existing output；
- wrong asset map；
- wrong candidate/program；
- wrong budget；
- wrong source hash；
- wrong planner terminal；
- unknown third reopen flag；
- runner preflight意外创建 scene/GPU/output。

旧 Run14 prepublication test 只测试“前后目录都不存在”，不能作为这个生命周期测试的替代。

## 7.5 F4 精确预算

恢复 Run12 的正确结构预算：

```yaml
maximum_root_invocations: 1
maximum_canonical_prefix_generations: 1
maximum_exact_prefix_replays: 3
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
```

planner 计数必须固定为：

```text
canonical prefix = 10
每条 suffix = 12 target construction + 30 control chain = 42
总计 = 10 + 3 × 42 = 136
```

branch execution 必须 planner delta=0。

## 7.6 F4 科学内容全部保持

禁止改变：

- candidate `f4-slot-corridor-hv2-r01`；
- `ABC / ACB / BAC`；
- object-slot mapping；
- same current/anchor；
- common-X prefix；
- fixed arm schedule：prefix right / suffix left；
- scene/layout；
- threshold；
- verifier；
- final-state equivalence；
- candidate search/seed retry。

## 7.7 F4 CPU 完成定义

以下全部通过后，发布：

- `F4_DEVELOPMENT_ROOT_RUNTIME_V2_CPU_REVIEW.md/json`
- `F4_DEVELOPMENT_ROOT_RUNTIME_V2_LIFECYCLE_PREFLIGHT.json`
- `PROPOSED_F4_INFRASTRUCTURE_CORRECTED_ROOT_MANIFEST_V1.json`
- `GPT_REVIEW_REQUEST_F4_INFRASTRUCTURE_CORRECTED_ROOT_V1_20260904.md`

proposal 必须：

- `approved=false`
- `gpu_execution_authorized=false`
- `physical_execution_authorized=false`

等待新的外审明确 supersede 旧 `CLOSED_NO_REOPEN_REQUESTED`。

---

# 8. F4 获批后的唯一 root 执行

只有新外审绑定 Runtime V2、manifest、lifecycle preflight 和源码 SHA 后执行。

执行一次：

- 1 canonical prefix；
- 3 suffix preflights；
- 3 branch executions；
- 3 raw；
- 3 MP4；
- 1 atomic development root。

接受条件：

- task feasibility 3/3；
- same-current/anchor；
- prefix exact replay 3/3；
- suffix planner exact counts；
- frozen execution planner delta 0；
- ABC/ACB/BAC physical 3/3；
- selected contact identity/continuity；
- prior slots preserved；
- untouched roles preserved；
- common-X preserved；
- all final slots pass；
- final-state equivalence across three branches；
- raw/video integrity；
- cleanup/orphan 3/3；
- root finalizer accepted。

无 fallback、无 candidate/seed search、无第二 root、无自动 retry。

---

# 9. 三族 root 完成后的后续数据构造

在 F2/F3/F4 各有至少 1 个 accepted development r_pc root 前：

- 不启动 Stage 1；
- 不启动 formal 360；
- 不训练 π0.5；
- 不做 H-reveal/compression。

随后依次：

## 9.1 real r_inv

每个 root 构造：

- 3 条 `r_pc`：same current，不同 intent；
- 3 条 `r_inv_path`：同 intent，不同空间路径；
- 3 条 `r_inv_motion`：同 intent，不同速度/动作实现但语义不变。

形成 root-atomic `9/9`。

禁止：

- 同一个 batch 放 same current；
- 用 planner ID、轨迹长度或 padding 泄漏标签；
- 只对成功 seed 做 post-hoc 选择。

## 9.2 Stage 1 pilot

先发布统一 readiness：

- F1 roots；
- F2 root；
- F3 root；
- F4 root；
- r_inv 完成度；
- root-atomic 9/9；
- raw/video/verifier integrity；
- denominator；
- failure inventory。

取得新授权后再做冻结 Stage 1 pilot。

## 9.3 Formal 与训练

Stage 1 通过后才分别申请：

1. formal data collection；
2. 数据转换/π0.5 输入格式；
3. baseline；
4. future-action conditioning；
5. H-reveal；
6. K/compression；
7. 训练和评测。

---

# 10. Codex 每轮必须返回的统一终端矩阵

```yaml
source_and_authorization:
  vault_head:
  robotwin_head:
  active_source_sha256:
  manifest_sha256:
  guard_sha256:
  runner_sha256:
  authorization_consumed:

driver_and_gpu:
  nvidia_smi_pass:
  gpu_index_uuid_map:
  selected_gpu:
  fresh_idle_pass:
  lease_released:
  returned_to_baseline:

counts:
  planner_qualification:
  planner_physical:
  planner_aggregate:
  fresh_scenes:
  robot_action_scenes:
  physical_candidates:
  suffix_preflights:
  branch_executions:
  raw_trajectories:
  videos:
  accepted_development_roots:
  accepted_development_trajectories:
  formal_roots:
  formal_trajectories:

family_result:
  F2:
  F3:
  F4:

failure:
  earliest_stage:
  category:
  exact_segment:
  consumed_before_failure:
  retry_authorized: false

later_stages:
  stage0_rerun: false
  stage1: false
  formal360: false
  training: false
  h_reveal: false
  compression: false
  pi05: false
```

---

# 11. 当前可立即开展的工作顺序

在 NVIDIA 驱动仍不可见时：

1. 保持 F2 manifest/runtime 完全不动；
2. 标记 F3 V1 为“未消费待预算澄清”，实现并签发 V2，但不启动；
3. 新建 F4 Runtime V2，完成 phase-aware lifecycle validator 和 CPU transition test；
4. 可以在 proposal-only 隔离目录预写 F2 controlled-insertion root V2，但不得修改 active source；
5. 可以预写 F3 candidate-bound/arm-parametric interface，但 winner-dependent hash 和 manifest 必须等 physical 结果；
6. 发布上述 CPU 产物并 push；
7. 驱动恢复后，按 `F2 → clean postcheck → F3 V2` 顺序执行；
8. F4 继续等待新的外审 GPU 授权，不与 F2/F3 偷跑。
