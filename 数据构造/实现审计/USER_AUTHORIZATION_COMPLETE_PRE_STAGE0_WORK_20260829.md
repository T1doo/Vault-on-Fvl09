# 完成 Controlled Multi-Future 的全部 Stage 0 前置工作

本消息是用户对 **Stage 0 前全部非正式准备工作**的明确授权。

请不要再完成一个小步骤就停止汇报。请连续完成下面 A–N 的工作，直到：

```text
READY_FOR_USER_REVIEW_BEFORE_STAGE_0
```

或遇到真正无法在当前授权范围内解决的 hard blocker。

普通代码错误、测试失败、路径错误、Schema 问题、planner 参数问题、有限的场景布局调整和版本化实现修复，都不属于提前停止理由；请自行诊断、修复、重新测试并继续。

---

# 0. 本次用户授权范围

用户明确授权以下 **nonformal / pre-Stage-0** 工作：

```text
CPU/static 代码修改与测试
真实 RoboTwin2 / SAPIEN scene 运行
真实 GPU A0 current/anchor smoke
F1–F4 有限的非正式 repair probes
F1–F4 完整三分支 nonformal integration probes
真实 fresh-scene root pipeline integration
GPU guard、cleanup、orphan、raw、receipt、verifier 验证
Stage 0 attempt budget 冻结
Stage 0 4-root / 12-trajectory manifest 与审批包准备
Vault commit 和 push
```

允许使用：

```text
物理 GPU0–7 中，由 atomic guard 证明 independently fresh-idle 的任意一张卡
```

但必须同时遵守：

- 不抢占其他用户任务；
- 不杀非本任务进程；
- 一张卡同一时刻一个本项目 job；
- 每次运行前重新检查 GPU；
- 必须绑定实际 UUID；
- cleanup/orphan 不确定时立即停止该卡后续工作。

## 本次明确不授权

```text
正式执行 Stage 0 的 12 条 smoke trajectories
Stage 1 的 48 条 pilot
Stage 2 formal manifest seal
360 条正式轨迹采集
机制模型训练
H_reveal 裁决
K/compression
π0.5 或 policy-transfer
```

最终即使全部准备通过，也只能写：

```text
READY_FOR_USER_REVIEW_BEFORE_STAGE_0
stage0_authorized = false
```

不得自行启动正式 Stage 0。

---

# 1. 保存本次用户授权证据

将本消息完整保存为：

```text
数据构造/实现审计/
USER_AUTHORIZATION_COMPLETE_PRE_STAGE0_WORK_20260829.md
```

同时生成：

```text
USER_AUTHORIZATION_COMPLETE_PRE_STAGE0_WORK_20260829.json
```

至少包含：

```yaml
schema_version: cmf_pre_stage0_user_authorization_v1
approved: true

approved_scopes:
  - CPU_static_hardening
  - A0_current_anchor_smoke
  - F1_three_branch_nonformal_probe
  - F2_beside_and_three_branch_nonformal_probe
  - F3_release_and_full_program_nonformal_probe
  - F4_common_carry_and_full_program_nonformal_probe
  - real_sapien_root_integration_nonformal_probe
  - stage0_manifest_and_budget_preparation

formal_stage0_authorized: false
stage1_authorized: false
formal_collection_authorized: false
training_authorized: false

maximum_implementation_repair_rounds_per_family: 2
automatic_unbounded_retry: false
```

保存 Markdown 文件 SHA、JSON SHA、当前 Vault commit 和时间。

之后每一个具体 GPU run 仍然必须生成：

```text
独立 scope request
独立 one-shot authorization
独立 authorization consumption receipt
独立 guard receipt
独立 output namespace
```

但这些 run 可以由本次总授权派生，不需要每完成一个小步骤再次询问用户。

每个子授权必须引用：

```yaml
parent_user_authorization_sha256:
scope_request_sha256:
```

---

# 2. 锁定当前代码与规范

当前 Vault：

```text
repository:
https://github.com/T1doo/Vault-on-Fvl09

branch:
main

starting HEAD:
e274bce5993c514f4f8d17c6ea110528fb3cf5da

V5 content commit:
3e7cba9e1dc798f9e18a1c23e4811c80f664bf1a
```

当前 RoboTwin baseline：

```text
c3ddfa8b97d5519efa828b075999bd0006778e5e
```

必须先完整阅读：

```text
Idea/项目核心Idea.md
数据构造/数据构造方案.md

数据构造/实现审计/
GPT_REVIEW_HANDOFF_RUNTIME_V3_1_CPU_V5_20260829.md

数据构造/实现审计/
A0_USER_APPROVAL_REQUEST_RUNTIME_V3_1_V5.md

数据构造/实现审计/
A0_USER_APPROVAL_REQUEST_RUNTIME_V3_1_V5.json

数据构造/实现审计/
stage0_readiness_report_runtime_v3_1_current.md

数据构造/实现审计/
stage0_readiness_report_runtime_v3_1_current.json

数据构造/实现审计/
pilot_attempt_budget_runtime_v3_1_proposal.md

数据构造/实现审计/
pilot_attempt_budget_runtime_v3_1_proposal.json

数据构造/实现审计/
代码审阅快照/
```

科学设计保持：

```yaml
design_version: controlled_multi_future_f1_f4_v1_2

families: 4
formal_roots: 40
formal_raw_trajectories: 360
intents_per_root: 3
realizations_per_intent: 3

F3:
  - VVHH
  - VHVH
  - VHHV

F4:
  - common-X + ABC
  - common-X + ACB
  - common-X + BAC
```

禁止更改这些科学定义。

---

# A. 一次性修完剩余 CPU P0

建立：

```text
implementation_revision:
runtime_v3_1_cpu_hardening_v5_1
```

## A1. Native planner counter 必须进入 A0 hard Gate

修改：

```text
controlled_multi_future/a0_activity_monitor_v2.py
```

当前独立 wrapper counter 已经检查为 0，但必须同时要求：

```yaml
native_planner_query_count_delta_if_available: 0
native_planner_record_delta_if_available: 0
```

行为要求：

- 真实 RoboTwin task 中 native planner counter 应存在；
- 真实 adapter 中 native counter 意外为 `None` 时 fail closed；
- synthetic dummy 可以按测试 Schema 显式声明 unavailable；
- wrapper count=0、native count=1 时必须失败；
- native query count 和 native record count 不一致时必须失败。

新增测试：

```text
test_native_planner_delta_nonzero_fails
test_native_planner_record_delta_nonzero_fails
test_real_adapter_requires_native_planner_counters
```

## A2. Physics step 成为显式预算字段

所有 A0 相关结构增加：

```yaml
post_setup_physics_step_limit: 0
```

同步到：

```text
scope budget
approval request
authorization
guard binding
A0 receipt
budget validator
readiness
```

不得只在 activity validator 中隐式检查。

## A3. Authorization 必须绑定用户审阅的请求

升级为：

```text
cmf_runtime_v3_1_gpu_authorization_v1_2
```

每份子授权必须绑定：

```yaml
parent_user_authorization_sha256:
approval_request_schema_version:
approval_request_sha256:
approval_request_file_sha256:
reviewed_content_commit:
source_lock_receipt_sha256:
```

生成方式必须是：

```text
读取已经冻结的 scope approval request
→ 验证其 hash
→ 只填写 approved、issued_at、expires_at、receipt_sha256
→ 其余字段禁止修改
```

有效时间建议：

```text
expires_at - issued_at <= 1 hour
```

## A4. 真实 launch-time source lock

新增：

```text
controlled_multi_future/runtime_source_lock_v1.py
```

在每次 GPU authorization consumption 前重新验证：

```text
RoboTwin repo HEAD
RoboTwin tracked worktree clean
官方关键文件 hash
官方 camera/task config hash
当前 family 使用的官方 asset/model_data hash
controlled_multi_future active source hash
环境 activation hash
Python / CUDA / SAPIEN / CuRobo version
dependency commits/worktree
```

至少检查：

```text
envs/_base_task.py
envs/robot/robot.py
envs/robot/planner.py
envs/camera/camera.py
envs/utils/create_actor.py
使用中的 family env / asset / model_data / config
```

生成：

```yaml
schema_version: cmf_runtime_source_lock_v1
official_repo_commit:
official_worktree_clean:
critical_source_hashes:
asset_hashes:
config_hashes:
implementation_source_sha256:
environment_lock:
source_lock_pass:
source_lock_receipt_sha256:
```

行为要求：

- source lock 在 authorization consumption 前运行；
- source lock 失败时不得消费授权；
- source lock hash 进入 authorization、guard 和 child receipt；
- 不允许只写固定 commit 字符串而不验证实际磁盘内容。

## A5. 失败证据补取

若：

```text
capture_current
capture_anchor
activity validation
```

中途异常，orchestrator 必须尽量从：

```text
handle.activity_receipt
context.activity_receipt
monitor.last_receipt
```

补取 activity receipt 并保存。

这只能提高失败证据完整度，不能把 failure 变成 pass。

---

# B. 完成 V5.1 全部 CPU 测试

保留现有全部测试，并增加：

```text
native planner query delta 非零 → fail
native planner record delta 非零 → fail
native counter unavailable in real adapter → fail
physics limit 不匹配 → fail
approval request SHA 不匹配 → fail
parent user authorization SHA 不匹配 → fail
authorization 有效期超过上限 → fail
source lock commit 不匹配 → fail
source lock dirty worktree → fail
source lock critical file hash 不匹配 → fail
source lock asset/config hash 不匹配 → fail
source lock implementation hash 不匹配 → fail
source lock 失败时 authorization 不得被消费
失败 capture 后 activity receipt 仍被保留
```

完成：

```text
active source 全测试
Vault snapshot 全测试
Python compile
import-side-effect audit
source-hash registry
active/snapshot byte-equal
```

在完成 A、B 前禁止运行 GPU。

---

# C. 生成新的统一 pre-Stage-0 授权包

生成新的版本化文件：

```text
PRE_STAGE0_GPU_SCOPE_BUDGET_V1.md/json
PRE_STAGE0_GPU_SCOPE_REQUESTS_V1.md/json
```

每个 scope 使用独立 request hash 和 one-shot authorization。

允许的 scope：

```text
A0_current_anchor_smoke

F1_three_branch_nonformal_probe

F2_workspace_and_three_branch_nonformal_probe

F3_release_and_full_program_nonformal_probe

F4_common_carry_and_full_program_nonformal_probe

real_sapien_root_integration_nonformal_probe
```

所有 scope 保持：

```yaml
formal_data: false
stage0_data: false
stage0_authorized: false
```

本轮允许 Codex 根据本次用户总授权，生成这些 scope 的：

```text
approved=true
```

one-shot authorization receipts。

但每个 receipt 必须：

- 有唯一 authorization ID；
- 有唯一 output namespace；
- 有明确 issued/expires；
- 绑定 exact source/request/budget/command hash；
- `max_invocations=1`；
- 被消费后不可再次使用。

---

# D. 执行真实 A0

A0 固定：

```yaml
family: F1
scene_seed: 20260829

scene_pattern:
  - A0_pristine
  - A0_fresh_1
  - A0_fresh_2
  - A0_fresh_3

post_setup_planner_query_limit: 0
post_setup_controlled_action_limit: 0
post_setup_physics_step_limit: 0

timeout_seconds: 600
automatic_retry: false
```

## D1. A0 成功条件

必须全部满足：

```text
4 个唯一 scene 均创建
4 个 scene 均 cleanup 成功
fresh1/2/3 current 与 pristine 严格一致
fresh1/2/3 physical anchor 等价
每个 activity receipt 与 handle/cleanup scene ID 一致
每个 activity receipt 唯一
planner wrapper/native count 全为 0
controlled action count 为 0
physics step delta 为 0
artifact hash 可重算
task-owned orphan = 0
GPU 回到运行前 baseline
```

## D2. A0 失败处理

本次总授权最多允许：

```text
A0 初始运行 1 次
+ 明确修复后的版本化 A0 再运行 1 次
```

第二次只能在以下条件下使用：

- 第一次失败有明确代码／Schema／metadata／monitor／cleanup 根因；
- 已形成 versioned repair；
- CPU tests 已新增并通过；
- 新建 request、authorization、namespace；
- 不得原地重跑相同代码。

若失败原因是无法解释的 same-current 或 anchor nondeterminism：

- 允许 CPU/日志诊断；
- 允许定位具体 component；
- 禁止通过放宽 hash/tolerance 强行通过；
- 两次耗尽仍失败则标记 hard blocker。

A0 通过后自动继续后续工作，不要先停下来问用户。

---

# E. Family probe 公共要求

每个 family probe 都必须：

```text
真实 SAPIEN
fresh scene
独立 one-shot authorization
atomic GPU guard
固定 budget
旧失败证据保留
新 namespace
raw/receipt/verifier/cleanup 完整
```

所有 targeted repair 先运行 CPU：

```text
geometry
IK/reachability
actor→EEF mapping
collision/swept-volume
program contract
verifier contract
```

只有 CPU Gate 通过的预注册 candidate 才能执行。

每个 family 最多允许：

```text
2 个新的 implementation repair revisions
```

禁止：

- 无限更换 target pose；
- 多试几十个方案后只保留成功者；
- 静默换 main object；
- branch-specific 换 arm；
- 删除失败记录；
- 放宽 verifier 来制造成功。

允许的 implementation impact：

```text
修正 actor→EEF transform
调整 pre-place/release approach
增加安全 waypoint
分段 planner path
移动 target facility 到合理工作区
选择 pot 或 stand 中一个作为 F2 BESIDE 的统一实现
调整 project scaffold 的可见性、尺寸、位置或物理参数
选择 family/root 全局统一执行臂
```

但每一项必须：

- 新 scene/layout/implementation version；
- impact review；
- 保持 family 科学语义；
- 不制造明显位置捷径；
- 同 root 三个 branch 使用统一规则。

---

# F. F1：完成真实三分支

目标：

```text
red
green
blue
```

固定顺序执行，每个 branch 使用 fresh scene。

必须共同使用：

```text
相同 current
相同 anchor
相同公共盒子
相同执行臂
相同 target actor-pose rule
相同 canonical target-neutral prefix
相同 verifier
```

## F1 budget

```yaml
branches:
  - red
  - green
  - blue

execution_limit_per_branch: 1
planner_query_limit_per_branch: 12
timeout_per_branch_seconds: 1200
automatic_retry: false
recovery: 0
```

若一个 branch 失败，仍应运行后续预注册 branch，除非发生 cleanup/GPU 安全失败。

必须验证：

```text
3/3 target object 正确
3/3 true cavity inside
3/3 stable + box contact/support evidence
3/3 gripper open
3/3 arm rest
3/3 non-target RGB blocks 稳定
3 条实际 executed prefix action hash 相同
suffix first-divergence 合理
```

只有 3/3 全通过，F1 才算 Stage 0 前可用。

---

# G. F2：先解决 BESIDE，再完整跑三分支

固定：

```text
main object = 071_can/base1
同一执行臂
inside / on / beside
```

不得为不同 relation 换 main object。

## G1. BESIDE workspace preflight

最多预注册：

```text
6 个 actor-pose / EEF-pose candidates
```

每个 candidate 检查：

```text
actor upright orientation
actor→EEF transform
release pose reachability
pre-place pose reachability
pre-place→release chained qpos continuity
joint limit margin
carried-object sweep
robot/link collision
facility collision
table boundary
```

公平性要求：

- 固定 candidate 顺序；
- 每个 candidate planner seed/state 真正 reset；
- 不能先跑多个 scene 再挑最容易的；
- 选择固定顺序中第一个通过全部 Gate 的 candidate。

预算：

```yaml
pose_candidate_limit: 6
planner_query_limit_total: 16
execution_limit: 1
timeout_seconds: 1200
```

## G2. 若当前 display stand 仍全部失败

允许一个且仅一个 impact revision：

```text
F2 layout/reference implementation v2
```

Codex应根据 CPU reachability 证据在以下两项中选择一个：

```text
A. 移动 display stand 到同一左臂合理工作区
B. 使用官方 kitchen pot 作为统一 BESIDE reference
```

不能两个都连续试到成功。

选择后必须固定为当前 F2 implementation，更新 registry 和 scene version。

仍保持：

```text
同一个 071_can/base1
同一执行臂
同一个 beside 语义
```

## G3. BESIDE 成功后

通过真实 root pipeline 完整运行：

```text
inside plastic box
on electronic scale
beside chosen reference
```

三分支必须：

- same current；
- same anchor；
- same can/model ID；
- same arm；
- shared canonical prefix；
- mutually exclusive predicates；
- 3/3 semantic verifier。

只有 3/3 全通过，F2 才算 Stage 0 前可用。

---

# H. F3：归因释放失败并跑完整三个程序

固定：

```text
001_bottle/base13
同一执行臂
V = table-z
H = table-x

VVHH
VHVH
VHHV
```

禁止改变 V/H 轴和三个 program。

## H1. Release diagnosis

一次诊断运行必须记录：

```text
before release
after 1 frame
after 5 frames
after 10 frames
after 25 frames
after 50 frames
after 125 frames
after 250 frames
after arm rest
```

每个时间点保存：

```text
bottle position/orientation error
EEF position/orientation tracking error
T_eef_actor
grasp transform drift
bottle linear/angular velocity
pad footprint
bottle-pad contact point/normal/impulse
selected gripper contact
actual gripper qpos
```

## H2. 条件式 repair

### 情况 1：释放前已经偏移

且满足：

```text
grasp transform 稳定
EEF tracking 正常
actor target 存在系统性偏差
```

允许：

```text
一次 deterministic actor→EEF correction
```

### 情况 2：释放前正确，释放后滚动／弹跳

允许一个版本化 support/release impact repair，例如：

```text
降低 release height
调整冻结 release orientation
调整 project original pad 尺寸或 pose
修正 pad friction/material source
增加稳定等待但不得放宽终态
```

只能选择一个预注册 repair 版本，不能逐项试到成功。

### 情况 3：抓取过程发生 slip

进入：

```text
grasp_slip impact repair
```

允许修正：

```text
grasp pose
gripper closing target
central pose transport
```

不得用 final EEF correction 掩盖 grasp slip。

## H3. Primitive repair budget

```yaml
diagnosis_execution_limit: 1
conditional_repair_execution_limit: 1
planner_query_limit_per_run: 16
timeout_per_run_seconds: 1800
automatic_retry: false
```

## H4. Return 成功后跑完整 programs

分别 fresh-scene 执行：

```text
VVHH
VHVH
VHHV
```

必须验证：

```text
V/H realized event 顺序
V/H 各两次
主轴/偏轴/central return
selected-gripper contact continuity
bottle final position/orientation
pad footprint与稳定性
arm rest
gripper state
三个 branch final-state equivalence
三个 r_pc 的 shared-first-V prefix hash
```

只有三个程序全通过，F3 才算 Stage 0 前可用。

---

# I. F4：修复 common-X，并跑完整三个程序

固定：

```text
common-X
tray
A/B/C
slot A/B/C

common-X + ABC
common-X + ACB
common-X + BAC
```

## I1. Common-X route 预算

Route 1：

```text
source
→ 根据障碍物 envelope 算出的最低安全高度
→ central carry waypoint
→ above tray
→ pre-place
→ release
→ neutral
```

Route 2：

```text
source
→ carry-neutral orientation
→ central carry waypoint
→ above tray
→ pre-place
→ release
→ neutral
```

固定顺序：

```text
Route 1 先运行
Route 1 terminal non-cleanup failure 后才允许 Route 2
```

每个 route 使用 fresh scene。

预算：

```yaml
route_limit: 2
planner_query_limit_per_route: 16
execution_limit_per_route: 1
timeout_per_route_seconds: 1800
automatic_retry: false
```

## I2. 两条 route 都失败

允许一个且仅一个：

```text
tray layout impact revision
```

可以移动 tray 到选定执行臂合理工作区，但必须：

- common-X 仍然是完整公共子任务；
- current 中 tray 可见；
- 不遮挡 A/B/C；
- 不制造 candidate label shortcut；
- 更新 layout version 和 impact report。

新 layout 下仍只允许 Route 1 / Route 2 各一次。

## I3. Common-X 成功后

按顺序运行：

```text
A-only
B-only
C-only
common-X + A + B noninterference
common-X + ABC
common-X + ACB
common-X + BAC
```

每个 block 必须：

```text
neutral → grasp → place → release → neutral
```

必须验证：

```text
neutral pose/velocity/gripper equivalence
每个 block 只改变自己的 predicate
已完成 slot 不被后续动作破坏
A/B/C 非目标对象 displacement
completion stability
completion tie
最终 world equivalence
```

现阶段只需要真实自然 programs。

未经 block contract 全部通过，不执行 strict array-splice reorder，也不声称 strict block intervention。

只有三个完整 programs 全通过，F4 才算 Stage 0 前可用。

---

# J. 所有完整 Family probe 必须走真实 root pipeline

F1–F4 最终的三分支证据不能只是零散脚本。

必须通过：

```text
RealSapienPilotRootOrchestrator
```

完成：

```text
pristine scene/current/anchor
→ disposable task/physical feasibility scenes
→ candidate universe freeze once
→ task tree freeze
→ canonical prefix freeze
→ 3 个 fresh rollout scenes
→ raw writer
→ family verifier
→ root finalizer
```

## J1. Root 级硬要求

```text
candidate universe freeze call count = 1
task/physical feasibility 与 planner solvability 分账
planned spec/program 不可被 adapter 修改
3 个 branch current hash 与 reference 一致
3 个 branch anchor 等价
3 个 branch executed prefix hash 满足 family contract
3 个 raw manifest 完整
3 个 receipt terminal
3 个 scene cleanup
root finalizer 3/3
```

## J2. Raw contract

继续保持：

```text
controller_effective_setpoint_v1_layout_v2_1
250 Hz
26 dimensions
N actions / N+1 states
```

保存并验证：

```text
action interval start/end timestamps
state timestamps
effective setpoint
requested command
planner_goal_eef_pose
planner query ID/active range
双臂 qpos/qvel
双 EEF pose/velocity
actual gripper joint qpos
drive-target readback
object/contact/verifier audit
raw NPZ/file SHA
```

禁止 placeholder 冒充真实数据。

---

# K. Stage 0 前集成验收

当 A0 和 F1–F4 全部成功后，执行一次完整 audit：

## K1. Family 状态

必须满足：

```yaml
F1:
  three_branch_pass: true

F2:
  three_branch_pass: true
  same_object: true
  same_arm: true

F3:
  three_full_program_pass: true
  return_equivalence_pass: true

F4:
  three_full_program_pass: true
  common_prefix_pass: true
  noninterference_pass: true
```

## K2. Pipeline 状态

```yaml
real_A0_pass: true
real_current_hash_pass: true
real_anchor_pass: true
real_candidate_freeze_pass: true
real_fresh_scene_pass: true
real_raw_contract_pass: true
real_verifier_pass: true
real_finalizer_pass: true
cleanup_orphan_pass: true
```

## K3. 不允许用来宣称的内容

即使全部通过，也不能说：

```text
Temporal Identifiability passed
H_reveal 已得到
formal dataset generated
generalization 已证明
compression 已开始
policy transfer 已开始
```

这些只是：

```text
Stage 0 前的工程可执行性与数据管线准备
```

---

# L. 冻结 Stage 0 执行包，但不要运行

生成正式 Stage 0 审批包：

```text
STAGE0_EXECUTION_MANIFEST_V1.md
STAGE0_EXECUTION_MANIFEST_V1.json

STAGE0_ATTEMPT_BUDGET_V1.md
STAGE0_ATTEMPT_BUDGET_V1.json

STAGE0_USER_APPROVAL_REQUEST_V1.md
STAGE0_USER_APPROVAL_REQUEST_V1.json
```

Stage 0 固定：

```text
4 families
× 1 root/family
× 3 intents/root
× only r_pc
= 12 trajectories
```

## L1. Manifest 必须冻结

```text
4 个 Stage 0 root slot
family
seed
scene/layout version
selected assets
selected execution arm
3 candidate programs
candidate display order
prefix contract
verifier version
collector version
raw schema
source lock
GPU policy
```

## L2. Budget 必须基于真实 probe

根据真实成功和失败耗时冻结：

```text
per-candidate planner query limit
per-trajectory execution limit
per-root timeout
GPU hour range
retryable failures
non-retryable failures
cleanup stop line
root atomicity rule
```

不能再只保留模糊 proposal。

## L3. Stage 0 请求保持

```yaml
approved: false
stage0_authorized: false
formal_data: false
```

不要运行 Stage 0。

---

# M. Readiness 最终裁决

只有全部满足时写：

```text
READY_FOR_USER_REVIEW_BEFORE_STAGE_0
```

条件：

```text
A0 真实通过
F1 3/3 完整通过
F2 3/3 完整通过
F3 三个完整程序通过
F4 三个完整程序通过
真实 root pipeline 通过
raw/verifier/finalizer 通过
cleanup/orphan/GPU release 通过
Stage 0 manifest 已冻结
Stage 0 attempt budget 已冻结
Stage 0 用户审批请求已生成
```

否则保持：

```text
BLOCKED_WITH_REASONS
```

并准确列出剩余 blocker。

无论结果如何：

```text
stage0_authorized = false
stage0_trajectory_count = 0
formal_f1_f4_trajectory_count = 0
```

---

# N. 测试、文档、快照与发布

## N1. 测试

最终运行：

```text
active source 全测试
Vault snapshot 全测试
Python compile
import-side-effect audit
source-lock tests
authorization replay tests
GPU guard binding tests
activity monitor tests
family contract tests
root orchestrator tests
raw writer tests
verifier tests
finalizer tests
```

## N2. 文档

更新：

```text
controlled_multi_future implementation proposal
runtime registry
stage0 readiness
attempt budget
数据构造方案 implementation status
正式数据构造日志
代码审阅快照 README
```

新增：

```text
COMPLETE_PRE_STAGE0_EXECUTION_REPORT_20260829.md
COMPLETE_PRE_STAGE0_EXECUTION_REPORT_20260829.json

GPT_REVIEW_HANDOFF_COMPLETE_PRE_STAGE0_20260829.md
```

## N3. Evidence

所有 probe 保存：

```yaml
formal_data: false
stage0_data: false
purpose: pre_stage0_nonformal_validation
```

失败证据不得删除或覆盖。

## N4. 同步和提交

- 修改 active additive source；
- 不修改 RoboTwin 官方 tracked baseline；
- 同步 byte-equal Vault snapshot；
- 提交并 push Vault `main`；
- 不 commit/push RoboTwin 官方仓库。

---

# 最终反馈格式

完成全部工作后，用通俗中文先给一页总结，再附机器细节。

必须回答：

## 1. 当前进度

```text
READY_FOR_USER_REVIEW_BEFORE_STAGE_0
```

或：

```text
BLOCKED_WITH_REASONS
```

## 2. A0

```text
是否真实运行
是否通过
运行次数
失败/修复过程
same-current
anchor
zero planner/action/physics
cleanup/orphan
```

## 3. F1–F4

| Family | 最终实现版本 | 三分支/三程序是否全部通过 | 最终 blocker |
|---|---|---|---|

## 4. 数据管线

逐项回答：

```text
real current hash
real anchor
candidate freeze
task/physical vs planner 分账
canonical prefix
fresh scene
26-D / 250 Hz
N/N+1
receipt
verifier
finalizer
cleanup
```

## 5. Stage 0 包

说明：

```text
4 个 root 是否已冻结
12 条任务 manifest 是否生成
attempt budget 是否冻结
approval request SHA
stage0_authorized 是否仍为 false
```

## 6. 实际运行统计

```text
GPU runs
planner queries
executions
timeouts
cleanup failures
orphan count
失败分布
总 GPU 时间
```

## 7. Git 与文件

```text
新增/修改文件
active source hashes
Vault snapshot hashes
测试结果
commit
最终远端 HEAD
git status
```

## 8. 明确确认没有执行

```text
没有正式 Stage 0 轨迹
没有 Stage 1
没有 360 条正式数据
没有模型训练
没有 H_reveal 裁决
没有 compression
没有 π0.5
```

不要在完成 A0 或某一个 family 后停下来。依次完成 A–N，直到所有 Stage 0 前置工作完成或明确耗尽上述有限 repair budgets。

