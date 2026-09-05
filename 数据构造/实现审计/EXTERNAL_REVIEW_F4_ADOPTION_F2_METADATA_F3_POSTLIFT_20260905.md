# 审阅结论：F4 这次可以只做 CPU 收据更正，不需要重跑机器人

我核对了提交 **`9ca36270a2acac52ce0a606b4de684907ee6cb64`** 下的交接文档、F4 原运行终端、收据修复脚本与验证报告，以及 F2 的目标计算代码、F3 的新 executor、runner 和测试。

**这轮最重要的变化是：F4 已经不是“动作可行、但还没采到数据”，而是三条完整数据已经采到了，只差依法追溯、明确记录的一次元数据更正。**原运行确实完成了三条分支、三个 raw、三个视频；物理、前缀、终态和文件完整性检查通过，外层唯一失败是磁盘分支收据与 root 内嵌收据不一致。fileciteturn413file0L2-L2

本次决定如下：

| 项目 | 决定 | 下一步 |
|---|---|---|
| **F4** | **批准仅 CPU、追加式收据更正与重新验收** | 不动原数据；复核通过后接收已有的 1 root / 3 trajectories |
| **F2** | **确认保留当前 live metadata 几何来源，纠正我上一轮的示例数值** | 完成专属入口后，按既有条件许可执行 beside-only 6 queries |
| **F3** | 新接线有效，但抬升验收还有一处实质缺口 | 只补 post-lift 验收及针对性测试，不重写 Guard、不换候选 |
| **Stage 1 / formal / 训练** | 仍不开放 | development 数据验收与这些阶段分开统计 |

本轮我审阅的是仓库代码和已封存机器证据，**没有在此重新解码服务器上的原始 NPZ**。因此，下面的 F4 采纳流程要求 Codex 再从原始文件重新计算，而不是直接把诊断报告中的 `pass=true` 当作最终验收。

---

# 一、F4：确实是一处收据发布顺序错误

## 1. 为什么机器人做对了，最后还是失败？

代码顺序已经确认：

```text
每条 branch 执行完成
        ↓
把 branch receipt 写入磁盘
        ↓
三条 branch 全部完成
        ↓
比较三条实际动作，计算真正的首次分歧
        ↓
更新内存中的三份 branch receipt
        ↓
写 root receipt
```

问题在于，**最后更新了内存，却没有同步发布更新后的分支收据**。

`root_orchestrator_v1_2.py` 先写 `branches/.../receipt.json`，随后才调用 `finalize_three_branch_root_v1_1()`；后者调用的 `resolve_first_post_prefix_divergence()` 会原地修改三条分支的分歧字段。最终 v1.2 只写 root receipt，没有发布对应的最终分支版本。fileciteturn407file0L2-L2 fileciteturn406file0L2-L2

于是出现：

| 字段 | 磁盘 branch receipt | root 内嵌 branch receipt |
|---|---:|---:|
| `canonical_prefix_end_step` | 2851 | 2851 |
| `first_post_prefix_divergence_step` | **2851** | **2926** |

**不是动作步数少了，也不是轨迹被截断了。是“首次分歧位置”这个派生字段，没有同步到分支文件。**

三条 raw 的实际动作数量分别为 **12018、12015、12049**，这些长度不需要修改。fileciteturn413file0L2-L2

## 2. 为什么 2851 和 2926 可以不同？

这里必须区分两个概念：

- **2851：预先冻结的 canonical prefix 结束位置。**
- **2926：比较实际动作流后，三条分支第一次出现差异的位置。**

冻结前缀结束以后，三个后缀又自然共享了 75 步动作，因此：

```text
2851 + 75 = 2926
```

现有诊断分别从原始动作流、原收据中的逐步哈希和 root finalization 重算，三种结果都得到 2926；canonical prefix 仍为 2851。fileciteturn418file0L2-L2

因此不能为了“统一数字”把 P 改成 2926，也不能删掉那 75 步。

另外，**2926 只是三条动作开始不完全相同的位置，不等于三种意图已经全部可辨识，更不等于 `H_reveal`。**这个区分要在更正记录里保留。

---

# 二、F4 正式批准：追加更正记录，然后接收原来的数据

正式决定：

```text
APPROVE_F4_ROOT1_CPU_ONLY_RECEIPT_RESOLUTION_V1
```

**批准的是对已有 root 的收据解析与采纳，不是第二次采集，不是放宽验收，更不是把原失败终端改成成功。**

## 1. 更正范围严格限定为三处同名字段

三个允许解析的分支：

```text
F4-ABC
F4-ACB
F4-BAC
```

每条仅允许：

```text
JSON pointer:
/executed_prefix/first_post_prefix_divergence_step

原值：2851
解析后值：2926
```

以下内容全部保持原样：

```text
canonical_prefix_end_step = 2851
动作数组、状态数组、时间戳、动作维度
raw NPZ、raw manifest、integrity sidecar
source trace、MP4
candidate、program、current、anchor
verifier、物理阈值、planner 计数
原 branch/root/job/Guard receipts 与事件日志
```

CPU 诊断已经证明：对每条原分支做这一处更正后，整份对象与 root 内对应分支完全一致；额外修改 status、canonical P 等情况会被拒绝。fileciteturn404file0L2-L2 fileciteturn418file0L2-L2

## 2. 正式采纳不能继续靠 `unittest.mock.patch`

当前诊断脚本使用：

```python
patch.object(module, "_read_mapping", ...)
```

给原 finalizer 提供派生视图。**作为诊断，这能够说明“只修该字段即可通过”；作为正式采纳入口，则需要显式的、可追溯的读取接口。**当前脚本本身也明确没有执行采纳。fileciteturn404file0L2-L2

最小实现即可，不需要再造一套 Guard：

```python
load_original_branch(...)
validate_resolution(...)
load_resolved_branch(...)
audit_f4_root_with_resolution(...)
```

其中 `load_resolved_branch()` 必须执行：

```text
读取原 branch 文件并验证其原 SHA
        ↓
验证本次 resolution 的授权与自身哈希
        ↓
验证 old_value 确实是 2851
        ↓
从 immutable raw 重新计算 divergence
        ↓
仅在计算结果为 2926 时生成派生视图
        ↓
验证除指定 pointer 外，其他字段没有变化
        ↓
验证派生视图与原 root 内对应 branch 完全一致
```

原 finalizer 的科学检查、文件完整性检查和计数规则继续保留。只显式增加“原收据 + 获批 resolution”的读取能力。

## 3. 正式采纳流程

**第一步：验证全部原始依赖。**

以 `F4_ROOT1_DIVERGENCE_RECEIPT_RESOLUTION_CPU_V1.json` 中的原始文件清单为基线，重新校验三条 branch、raw、manifest、sidecar、视频、root 和 job terminal。同时把实际参与复核的 source traces、prefix/suffix artifacts、Guard terminal 和事件日志纳入本次依赖清单。

任何原文件与已封存 SHA 不一致，都不能按这次单字段修复继续采纳。

**第二步：独立重算分歧。**

沿用当前动作布局、数据类型和 `_step_hashes` 口径，验证：

```text
三条 canonical prefix 一致
canonical P = 2851
raw-derived first divergence = 2926
receipt-step-hash-derived divergence = 2926
root-finalization divergence = 2926
```

不加浮点容差，不重采样，不改变下标口径。

**第三步：写入新版本派生文件。**

建议在原采集目录之外新增：

```text
f4_root1_receipt_resolution_v1/
  resolution.json
  branches/F4-ABC.resolved.json
  branches/F4-ACB.resolved.json
  branches/F4-BAC.resolved.json
  acceptance.json
```

每份派生文件明确记录原文件路径、原 SHA、resolution SHA 和派生内容 SHA。**不要覆盖原 `receipt.json`。**

**第四步：重新跑完整 CPU 验收。**

至少重新核对：

- 三条 raw 和 MP4 的磁盘完整性；
- 三个 resolved branch 与原 root 的一致性；
- same-current、anchor、prefix 和 final-state evidence；
- 每条 suffix 的 `12+30=42`、总数 136；
- 11 个独立场景、7 个动作场景、6 次前缀重放；
- 原运行的 cleanup、lease、GPU postcheck 证据。

注意：这一步是**复核原有物理证据**，不是重新执行物理仿真。

**第五步：发布新的接收记录。**

新 acceptance receipt 应同时保留：

```yaml
original_job_pass: false
original_child_exit_code: 1
original_terminal_modified: false

receipt_resolution_pass: true
post_resolution_acceptance: true
accepted_via: APPEND_ONLY_RECEIPT_RESOLUTION
```

不要修改原来的 POST_CHILD 结果。原运行的退出码 1 是历史事实；新的 CPU 验收通过是另一件事。

## 4. 通过后怎么计数？

通过后可以把**原来这一个 F4 root**登记为：

```text
F4 development accepted：1 root / 3 trajectories
```

在其他数据不变的前提下，全项目 development accepted 从：

```text
5 roots / 15 trajectories
```

更新为：

```text
6 roots / 18 trajectories
```

但：

```text
新增物理运行：0
新增轨迹采集：0
Stage-1-authorized：仍为 0/48
formal：仍为 0/360
```

接收索引必须按原 root 身份去重。重复运行 CPU 审计不能重复增加计数。

**上述条件满足后，不需要再回来申请一次 F4 采纳批准。**

---

# 三、F4 后续代码修复：修发布顺序，不再修机器人

当前 root 的更正，与未来 collector 的修复分开做。

未来版本应将流程改为：

```text
三条分支执行完成，保存 provisional receipts
        ↓
计算三条分支的实际 divergence
        ↓
构造 finalized branch receipts
        ↓
发布 finalized branch receipts
        ↓
发布引用这些最终分支版本的 root receipt
        ↓
最后登记 accepted root
```

这里最好避免继续原地修改已发布对象。历史事件日志可以保留 provisional 记录，再追加 finalized 事件。

增加一个针对性回归就能抓住这次错误：

```text
canonical P = 10
三条 suffix 的前 2 步仍相同
第 12 步首次不同

预期：
P 始终为 10
最终三份 branch 的 divergence 均为 12
root 内嵌分支与最终磁盘分支完全相同
```

再覆盖“发布中途中断，不能登记 accepted”的情况即可。**不需要重新审议 ABC/ACB/BAC、场景、候选或 verifier。**

这项修改放在独立 CPU 开发分支，不立即改动 F2/F3 当前绑定的 active source。

---

# 四、F2：保留 live metadata 来源，纠正我之前的数值要求

这部分 Codex 的暂停是正确的。

**我上一轮关于“actor origin 与 geometry centre 混用”的判断成立，但引用 collision inventory 得到的微米补偿，不应直接约束当前读取 model_data 的 live helper。这是我之前数值要求的问题。**

当前修复代码使用被冻结的 `model_data0.json`，按原 scale 计算中心与半尺寸，并用历史 candidate 0 → candidate 2 的整体平移做独立交叉检查。fileciteturn408file0L2-L2

我重新计算了报告中的 metadata 数值，结果一致：

```text
actor-origin XY 补偿：
(-9.4041217866, +10.7975129598) μm

旧 XY 覆盖错误的大小：
14.318651916 μm
```

正确 actor pose 为：

```text
[
  0.07999059587821346,
  0.07001079751295976,
  0.7404792624087959,
  0.5, 0.5, 0.5, 0.5
]
```

对应的 geometry-centre XY 仍严格落在：

```text
[0.08000000000000002, 0.07]
```

这些值与仓库的 discrepancy receipt 一致。fileciteturn414file0L2-L2

## F2 的明确决定

**允许保留 live metadata 来源；撤销上一轮示例中的 `(+3.619492,+2.966821) μm` 数值约束。**

这不意味着 collision inventory 作废。两种资料的用途要分开：

- 本次 beside actor target：沿用当前 live helper 的 metadata 口径；
- 碰撞、安全间隙、真实接触：仍按对应 collision/physical 证据判断；
- 不借这次修复修改 inside certificate 或其他 family 的几何来源。

## 执行前只需完成必要的入口收口

原来的 **beside-only 6 queries / 1 scene** 条件许可继续有效，不需要重新申请目标选择。

保留：

```text
candidate index 2
原 can、box、arm、orientation
原 planner seed
原六段顺序与 neutral
原 annulus 与目标比较容差
inside Run3 receipt 不变
```

补齐两处代码检查：

**其一，支撑高度要独立核对。**  
当前 `semantic_target.py` 从历史 template 反推出桌面高度，再用于重算，这是有用的交叉检查，但还应与冻结布局的 `table_plane_z_m` 和 live 的 `0.74 + table_z_bias` 比较，不能只用 template 验证自己。当前记录应仍得到 `0.74`，不产生新目标。fileciteturn408file0L2-L2

**其二，缺失 planner counter 不能回退成“没有消耗”。**  
`scene_attempt.py` 目前使用：

```python
getattr(scene, "planner_query_count", before)
```

如果进入场景后 counter 丢失，这会把未知消耗写成 0。改成明确记录 `unknown/accounting_complete=false`，保留 finally cleanup，不允许把未知计数当作成功证据。fileciteturn419file0L2-L2

然后完成专属 manifest/runner/Guard 预检与发布，执行一次 beside-only。

成功时可以合并：

```text
原 Run3 inside 5/5
+
新 beside 6/6
=
route qualification 11/11
```

但它仍不是物理 root 成功，下一步才是 controlled-insertion root proposal。

---

# 五、F3：接线已经完成，但目前不能把“最后一帧离桌”当作稳定微抬升成功

## 已经修好的部分，不再重做

新 executor 确实已经按以下顺序接入：

```text
pregrasp → 完整窗口 Gate
grasp → 完整窗口 Gate
两段通过后才 close
hold 250
micro lift
```

pregrasp 失败不会继续 grasp，grasp 失败不会 close。runner 也按冻结次序处理候选，使用 live counter 的 finally 记录，并保留 scene cleanup。fileciteturn409file0L2-L2 fileciteturn410file0L2-L2

四个候选、52-query/12-scene/4-attempt 预算和独立授权绑定都已进入 proposal。fileciteturn416file0L2-L2

## 还需要修的，是 `verify()` 这一小段

当前抬升后的关键检查是：

```python
"off_support": bool(off) and off[-1]
```

相对抓持变换也只比较抬升前后两个端点；`lift_action()` 丢弃了 `_execute_planned_segment()` 的返回收据，并没有直接检查瓶子实际升高多少。fileciteturn409file0L2-L2

这意味着以下情况可能被判通过：

```text
瓶子大部分时间仍在支撑面上
最后一帧短暂失去支撑接触
相对抓持变换端点变化很小
→ 当前条件可能 pass
```

我按当前布尔条件验证了这个反例：`off=[False, True]`，其他条件为真时，确实会通过。**这只是代码条件的反例，不是声称真实运行已经发生了该情况。**

目前 23 项测试主要覆盖顺序、计数、异常与 Guard；其中成功顺序测试把 `verify()` 直接 mock 成 `pass=true`，没有实际覆盖这段 post-lift 判定。fileciteturn412file0L2-L2

## F3 最小修正范围

只修改 post-lift 验收，不改 pre-close Gate，不换候选，不再增加通用审批框架。

建议抽出一个可单测的：

```python
audit_micro_lift_trace(...)
```

本轮 CPU 修订按以下合同实现：

| 检查 | 要求 |
|---|---|
| 抬升执行收据 | 保存并检查实际 lift execution receipt，不丢弃 |
| 实际抬升量 | 从 hold 后的瓶子位置计算；本次微门预设最小 **20 mm** |
| 抬升后确认 | 保持夹持再记录 **50 帧**，不追加 planner |
| 离开支撑面 | 50 帧均无 bottle–table/pad 物理接触 |
| 抓持连续性 | lift 窗口与确认窗口均保持有效 selected-gripper 接触 |
| 抓持变换 | 检查窗口内最大漂移，保持既有 **5 mm / 0.05 rad** 界限 |
| 禁止碰撞 | 继续使用现有 classifier 检查执行臂自碰、撞支撑物 |
| 信号完整性 | 缺帧、缺字段或不完整接触证据不能判成功 |

这里的 **20 mm** 是针对 25 mm 指令预先设定的微门验收值，留下 5 mm 跟踪余量；**这是新增诊断合同，不用于重新判定旧四条失败轨迹，也不能在新结果出来后调整。**

新增针对性反例即可：

```text
仅最后一帧离桌
瓶子没有实际升高
中途滑动、末端又回到原相对姿态
确认窗口缺少一帧
抬升后出现自碰或支撑碰撞
完整有效微抬升
```

所有修改仍保持：

```text
最多 52 planner queries
最多 12 scenes
最多 4 physical attempts
两个合格 micro pass 后停止
shared-V / no-suffix / root / raw / formal = 0
```

**F3 本轮仍只批准这一小段 CPU 修订。**完成后提交新的 source hashes、post-lift 测试和 proposal 做窄复审；不用重新阅读全部历史，不用再改 Guard。

还要注意：pre-close Gate 是检测与阻断措施，**不是 CuRobo 碰撞模型已经修好的证明**。新四个候选能否抓住，仍需真实微门验证。

---

# 六、给 Codex 的执行顺序

**优先完成 F4 的 CPU 采纳。**这是把已有真实数据变成正式 development 验收结果，不占用 GPU，也不需要新的物理实验。

同时可以完成 F2 入口收口与 F3 post-lift CPU 修订。GPU 队列中只有 F2 的既有条件许可可继续；F3 等窄复审，F4 不再运行。

完成 F4 采纳后更新统一状态：

```text
F1：5 development roots / 15 r_pc
F4：1 development root / 3 r_pc，accepted via receipt resolution
F2：inside pass，beside completion 待运行或记录新结果
F3：新 micro runtime 待 post-lift 修订及窄复审
Stage 1：0/48
formal：0/360
```

F4 是否完成采纳、F2 是否规划成功，不构成 F3 的科学依赖。只有清理、GPU 身份、残留进程或证据完整性问题需要阻断后续 GPU 队列。

---

# 可直接交给 Codex 的本次决定

```yaml
review_base:
  vault_head: 9ca36270a2acac52ce0a606b4de684907ee6cb64
  stage0_rerun: false
  stage1_authorized: false
  formal_360_authorized: false
  training_authorized: false
  h_reveal_authorized: false
  compression_authorized: false
  pi05_authorized: false

f4:
  decision: APPROVE_F4_ROOT1_CPU_ONLY_RECEIPT_RESOLUTION_V1
  authorized: true
  scope: EXISTING_ROOT_APPEND_ONLY_METADATA_RESOLUTION_AND_ACCEPTANCE

  source_run_id: f4-v22-authorized-root1-20260905
  source_manifest_sha256: 13ca428e61a81c6cff36fd77ee6aae3e9e6c6d9f1d70358512827d9582b9d1a8
  cpu_resolution_proposal_receipt_sha256: bd2a313764f0cae98340e93c54d3fc784a7a7bc1061eee9655e43af46ba7ecbf

  programs: [F4-ABC, F4-ACB, F4-BAC]
  canonical_prefix_end_step: 2851
  permitted_patch:
    json_pointer: /executed_prefix/first_post_prefix_divergence_step
    original_value: 2851
    resolved_value: 2926
    branch_count: 3

  original_branch_file_sha256:
    F4-ABC: ca7af3efa5e702ab51eb67f2298b96eb176b6a4d21860abfed90eabb9e3064d6
    F4-ACB: 044283d5ac6f3eefe775fae4d63994700db061a4c5c2d63b2068efca02c328f6
    F4-BAC: 67872e6935c500bf87dacd6debffe4c661b3db5b5c76de329d69b48172863908

  requirements:
    - Rehash original dependencies before and after adoption.
    - Recompute divergence from original raw actions and receipt step hashes.
    - Keep canonical P, action arrays, timestamps and all physical evidence unchanged.
    - Publish explicit resolution receipts and derived branch views.
    - Do not use unittest.mock as the production acceptance mechanism.
    - Preserve all original branch/root/job/Guard receipts and event logs.
    - Revalidate raw/video/current/anchor/prefix/final-state/accounting/cleanup evidence.
    - Keep original job pass=false and original child exit=1.
    - Publish a distinct post-resolution acceptance receipt.
    - Register the original root exactly once; do not double-count re-audits.

  maximum_gpu_executions: 0
  maximum_scene_creations: 0
  maximum_planner_queries: 0
  maximum_physical_executions: 0
  maximum_new_trajectories: 0
  maximum_existing_roots_adopted: 1
  maximum_existing_trajectories_adopted: 3
  maximum_formal_trajectories: 0

  further_review_required_if_all_conditions_pass: false
  second_physical_root_authorized: false
  active_collector_modification_authorized: false

f2:
  decision: CONFIRM_LIVE_METADATA_GEOMETRY_AND_EXISTING_BESIDE_ONLY_PERMISSION
  previous_collision_inventory_numeric_example_superseded: true

  geometry_source:
    file: assets/objects/071_can/model_data0.json
    file_sha256: 78eb137b42da2d6fa0b9208717964838e01cf6c65c5c6b14ad7c988d6ff2acfb
    scale: 0.05

  target_artifact_receipt_sha256: 7bd3593bccffbb6b83e83fc033467c2be803ec1faaa42fed1fb6e8111c6415e5
  corrected_beside_targets_sha256: 39e04cb57afeb64236a6f549e37a1dc1b9f9f09a3861908ce9eb7173e2ae51ae

  before_execution:
    - Independently check support plane against frozen layout and live table bias.
    - Do not replace unknown post-entry planner counts with zero.
    - Complete beside-only runner/Guard/manifest and CPU preflight.
    - Bind this clarification and the corrected target artifact.
    - Publish source and use a fresh output/Guard/cache namespace.

  inside_rerun: false
  full_11_query_rerun: false
  beside_queries_cap: 6
  fresh_scene_cap: 1
  physical_execution_cap: 0
  raw_trajectory_cap: 0
  accepted_root_cap: 0
  formal_trajectory_cap: 0
  automatic_retry: false
  automatic_root_transition: false
  additional_review_for_geometry_clarification_required: false

f3:
  decision: REVISE_MICRO_LIFT_ACCEPTANCE_ONLY_CPU
  gpu_execution_authorized_now: false

  retain:
    - exact four candidate recipes and order
    - existing V1.1 full-window pre-close Gate
    - current Guard lifecycle and authorization structure
    - current planner seeds and qualification order

  post_lift_revision:
    save_lift_execution_receipt: true
    minimum_actual_bottle_rise_m: 0.020
    post_lift_confirmation_frames: 50
    continuous_selected_contact_required: true
    continuous_off_support_during_confirmation: true
    maximum_relative_translation_drift_m: 0.005
    maximum_relative_orientation_drift_rad: 0.05
    evaluate_transform_over_full_window: true
    reject_forbidden_arm_collisions: true
    reject_incomplete_evidence: true

  unchanged_caps:
    planner_queries: 52
    scenes: 12
    physical_attempts: 4
    stop_after_qualified_micro_passes: 2
    shared_v: 0
    no_suffix: 0
    root: 0
    raw: 0
    formal: 0

  next_review_scope:
    - post-lift audit function and its targeted tests
    - updated exact source hashes and proposal
    - unchanged candidate and budget bindings

execution_priority:
  - F4 append-only CPU resolution and acceptance
  - F2 beside-only completion after existing prerequisites pass
  - F3 CPU post-lift revision and narrow review

gpu_jobs_serial: true
```

**这次可以真正把 F4 从“已采到但未接收”推进到“已有 1 组合格开发数据”；不要再为它重跑机器人。F2 保留正确的 live 几何口径继续补 beside，F3 只修抬升验收，不再扩展整套基础设施。**

---

If you want, I can:

- 继续详细描述F4的更正代码实现细节
- 解释F3阶段post-lift验收的修订计划
- 梳理F2阶段的数值修正影响与后续执行步骤
