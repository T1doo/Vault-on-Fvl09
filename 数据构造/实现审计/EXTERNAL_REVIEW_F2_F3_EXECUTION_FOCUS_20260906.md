# 结论：这轮已经验证了“小批量真实造变体”，下一步应把精力集中到 F2/F3

我按最新 **`47b29383e59636d452357e72e0349289c3e95b50`** 核对了交接、统一状态、9 条变体的独立验收脚本，以及实际运行的 `catalog.py`、`pipeline.py`；同时重新检查了你们锁定版本的 RoboTwin 目标转换和 planner 代码。

**本轮结果可以保留，不需要重新验收或重跑。**更重要的是，F1/F4 已不只是“单次任务能完成”，而是已经证明：在保留意图的情况下，更换路径或运动时长，新的真实轨迹仍能成功。独立审计确实重新检查了原始数据、视频、变体效果和三个六格配对矩阵，而不是只检查文件是否存在。fileciteturn470file0L2-L2

但要注意一个区别：

> **这轮主要完成的是 F1/F4 的九条变体。F2/F3 上轮获准的“约束辨析与模型修复”仍待实施，并不是它们又失败了一轮。**  
> 因此，不需要再换一套修复方案或重新申请同一许可，而应该把已经明确的两条工作线做到底。fileciteturn461file0L2-L2

下面的计划可以直接转给 Codex。

---

# 一、目前哪些已经完成，哪些才是真正阻塞

| 部分 | 当前已完成 | 下一步 |
|---|---|---|
| **F1** | 5 个根、21 条 raw：15 条 `r_pc`、3 条 path、3 条 motion | 冻结成功实现，准备 pilot 输入复用 |
| **F4** | 1 个根、6 条 raw：3 条 `r_pc`、3 条 path | 保留现有结果，准备第二个 pilot 根 B |
| **F2** | 抓持、inside 规划有正结果；固定 beside 目标及路线仍未解出 | 分离运动学、自碰、环境碰撞约束 |
| **F3** | 两候选接近动作通过；抓取段碰垫子/推动瓶子，被正确阻断 | 修复规划世界、夹爪状态和抓取终点 |
| **整套数据** | **6 个独立根、27 条开发 raw** | 不再重复补已完成的九条 |
| **Stage 1** | 18 个格子已有完整候选证据，但阶段接收仍为 0/48 | 做输入资格映射，并补剩余结构 |
| **Formal** | 0/360 | 等四族 pilot 和正式协议冻结 |

这些数字与最新 readiness 一致。**27 条开发 raw 不能直接写成“正式数据完成 27/360”，也不能写成“pilot 已完成 27/48”。**fileciteturn463file0L2-L2

---

# 二、先冻结已经成功的部分，避免再把 F1/F4 修坏

## 步骤 1：把这九条任务标记为完成，不再扩展原批次

保留：

```text
F1-A：3 r_pc + 3 r_inv_path
F1-B：3 r_pc + 3 r_inv_motion
F4-A：3 r_pc + 3 r_inv_path
```

这轮新增的是原有三个根的 realization，并没有新增独立根。路径变体有实际 EEF 变化，运动变体有实际执行时长变化；F1-B 的零新增 solver query，是复用控制后重新执行，不是没有进行物理 rollout。fileciteturn461file0L2-L2

**不要为了让日志更整齐重跑首条恢复数据，也不要重新申请 F4 采纳。**

## 步骤 2：保留分族源码配置，不要强行统一成一个 active 版本

这轮实际暴露过：旧 F1 reference 绑定的源码与当前 F4 使用的源码不同。现在 `catalog.py` 已经为 F1 使用父版本适配器，为 F4 使用当前适配器。这个做法应保留。fileciteturn468file0L2-L2

下一轮应建立一个简短的运行配置表：

```text
F1 已验收数据 → 对应父源码、adapter、reference
F4 已验收数据 → 对应当前源码、adapter、resolution
F2/F3 修复实验 → 独立版本化模型与运行入口
```

不要通过修改旧 reference hash，让它“兼容”新代码；也不要为了修 F3 的碰撞模型，直接改变 F1/F4 已验证的执行环境。

## 步骤 3：冻结现有 current 解码，后面 loader 直接复用

本轮 current 存储存在共享 articulation 的重复副本，但独立审计已经给出无损解码，并与原始 `state[0]`、三视角 RGB、夹爪状态核对通过。当前 getter 口径是 **38 个 qpos + 38 个 qvel = 76 维**，没有使用未来状态。fileciteturn474file0L2-L2

这里不需要再改原数据。后续 loader 应读取这份显式 layout 规则，不能看到数组长度就自行猜测机器人状态维度。

---

# 三、F2：先回答“为什么目标解不出来”，不要再跑中转点

上轮已经给出的 **最多 15 个 IK 问题 + 4 次轨迹查询、最多 2 个 planner-only scene** 的条件范围仍然适用。相关许可已经在仓库落库；这轮不重新扩大预算。fileciteturn469file0L2-L2

## 步骤 4：先完成一个正确的 IK 诊断适配器

这里有一个我这次从源码中确认的关键细节：

原路径不是直接把 EEF pose 传进 CuRobo，而是：

```text
用户侧目标 pose
→ Robot._trans_from_gripper_to_endlink()
→ world-to-base
→ frame_bias
→ Aloha 专用小角度旋转
→ CuRobo goal
```

如果新的 IK 诊断绕过 `Robot.left_plan_path()`，却漏掉前面的工具坐标转换，就会在**诊断一个不同的目标**。这会得到非常误导性的“不可达”结论。fileciteturn472file0L2-L2 fileciteturn473file0L2-L2 fileciteturn475file0L2-L2

因此先写两个小接口：

```python
reported_eef_goal_to_solver_goal(...)
full_joint_state_to_solver_joint_state(...)
```

要求：

- 复用锁定版本的转换规则，不重新手算另一套；
- 按 joint name 排序，不能只截取 qpos 前六项；
- 在 CPU 上对 C/U/D 比较“原调用链最终目标”和“新诊断目标”；
- 使用真实配置中的阈值、seed bank 和迭代设置；
- 不顺便升级 cuRobo。

**这个检查通过后再启动 GPU 诊断，而不是先跑九次求解才发现坐标口径不一样。**

## 步骤 5：按三个约束层级做九个 IK 问题

定义：

```text
C：已成功的当前 EEF 姿态
U：beside preplace 姿态
D：beside release 姿态
```

| 配置 | 内容 | 用途 |
|---|---|---|
| **K0** | 关节限制；关闭自碰和环境碰撞相关项 | 检查纯位置/方向约束 |
| **K1** | 关节限制 + 自碰 | 检查自碰约束的影响 |
| **K2** | 关节限制 + 自碰 + 审计后的环境 | 检查真实环境约束 |

这里的 K0/K1/K2 只是诊断配置名，**与研究里的压缩 token 数 K 无关**。

实现时，K0 不能只关掉“最终自碰检查”，却继续保留自碰优化成本。cuRobo 的配置区分 `self_collision_check` 与 `self_collision_opt`，必须核对两者，且环境相关成本也要按配置一致处理。citeturn782379view0

每个问题保存：

```text
原目标与 solver-frame 目标
seed bank、迭代上限
返回 qpos
FK 重算误差
关节余量
自碰与环境碰撞结果
实际求解消耗
```

**不要只保存一个 success 布尔值。**

## 步骤 6：用“解的交叉检查”判断原因，不只比较三个成功率

三个独立数值求解器可能因为优化过程不同，出现 K0 失败、K1 反而成功的情况。因此不能机械地认为成功结果一定随约束增加而递减。

正确做法是：

> 对任何找到的 qpos，在同一组 FK、关节限制、自碰和环境检查器下重新评估。

然后按下面的决策表继续：

| 结果 | 下一步 |
|---|---|
| C 在新诊断里也无法复现 | 先查适配器、配置或状态，不改任务 |
| U/D 找到了运动学解，但自碰检查失败 | 看具体碰撞 link 和姿态，不继续加 hub |
| U/D 通过自碰，但环境检查失败 | 看具体障碍、坐标和物体状态 |
| U/D 在 K2 都通过 | 才进入一次完整路径规划 |
| U/D 在固定数值预算内始终无解 | 保留“未找到解”结论，准备有限朝向或布局调整 |

这仍不是数学不可达证明，但足以决定工程上下一步该改什么。

## 步骤 7：K2 必须正确处理“罐子已被拿在手里”

这是必须提前避免的诊断陷阱。

F2 的起点已经是持物状态。如果把这个罐子同时作为普通静态障碍物放进 world，夹爪与罐子的正常抓持接触就可能把起点判成碰撞。

应当明确：

```text
桌子、reference、其他物体：环境障碍
手持罐子：随执行夹爪运动的碰撞几何
选定手指—罐子：正常抓持接触
手持罐子—其他环境：仍须检查
```

具体 attach 接口按安装版本验证；不得把罐子从全部检查中删除，也不得在物理引擎里添加固定约束制造抓持。cuRobo 提供附着物体与机器人几何更新能力，但使用者仍要正确提供关节状态和附着坐标。citeturn866448search1

**这只是防止新诊断误判，不表示已证实旧 F2 失败就是这一原因。**

## 步骤 8：按既有条件许可检查有限 yaw，然后停止旧目标搜索

若 F2 科学语义不要求固定 yaw，可以继续上轮已规定的：

```text
原 yaw
+90°
-90°
+180°
```

保持目标 geometry centre、直立与 beside 关系不变，重新通过实际抓持变换计算 actor/EEF 目标。

最多再做六个 U/D IK 问题。第一个在完整约束下 U/D 都通过的朝向，才规划：

```text
U → D → U → N
```

最多四次轨迹查询，仍不执行机器人。

如果这些都失败，**停止旧终点的路线搜索**，直接完成一个版本化的局部布局或抓取修订提案。不要再提交“建议换一个 hub 试试”。

新布局可以把 reference 与 beside 区域移到更合适的位置，但必须：

- 重新生成该 root 的 current、anchor 和绑定；
- 同组 inside/on/beside 仍共享同一 current；
- 旧 inside 成功保留为历史证据，不自动冒充新布局资格；
- 新终点的物理执行另列精确范围。

---

# 四、F3：把模型修复真正接进求解器，再判断两个抓取终点能否保留

这条工作线的既有条件范围仍是：

```text
原 r3063、r1401
最多 6 次轨迹规划
最多 2 个物理场景
另最多 2 个非动作模型核对场景
无 shared-V、无 no-suffix、无 root
```

不是再次执行旧四候选面板。fileciteturn469file0L2-L2

## 步骤 9：优先核对“张开夹爪”的真实几何

不要只验证六个机械臂关节一致。

需要导出：

```text
SAPIEN 全部相关 joint names / qpos
CuRobo active / locked joints
张开状态下手指和掌部的位姿
对应 collision spheres / meshes
```

尤其检查：

```text
SAPIEN 手指张开
CuRobo 手指是否仍处于默认锁定位置？
```

原 planner 创建 `JointState` 时只从 `active_joints_name` 中取值，因此不能仅凭“机械臂关节名称匹配”就认为夹爪几何也匹配。fileciteturn475file0L2-L2

若两边手指开度不一致，先修这个映射。不要继续增加瓶子候选。

## 步骤 10：补 table/pad/bottle，但要证明真正进入了执行中的 planner

建议只实现一个小的 scene-model bridge，供 F2/F3 使用：

```python
capture_scene_collision_geometry(...)
world_obstacle_to_solver_frame(...)
apply_world_and_robot_state(...)
```

注意两种转换不同：

```text
EEF 目标：
需要 gripper-to-endlink 转换。

环境障碍：
使用世界到 planner 的刚体变换，
不使用 gripper-to-endlink 的工具偏移。
```

**不能把同一个“目标转换函数”直接用来变换垫子和瓶子。**

原 planner 初始化有 `motion_gen`、`motion_gen_batch` 两个实例；实际机器人还可能使用 worker。需要确认当前任务真正调用哪个实例，并核对它收到的物体集合、几何 hash、pose 和夹爪状态。fileciteturn475file0L2-L2 fileciteturn473file0L2-L2

原 `update_world_pcd()` 还会捕获异常后只打印信息，因此**调用过函数不能作为更新成功证据**。不要复用这种静默失败方式。fileciteturn473file0L2-L2

## 步骤 11：用旧失败 trace 做正负对照，而不是只检查“模型对象有三个名字”

至少检查：

```text
初始明确无碰撞状态
已成功的 pregrasp 终点
首次 finger-pad 接触状态
瓶子开始被推动前的状态
原 grasp 目标对应的关节状态
```

输出：

```text
旧模型判断
新模型判断
碰撞 link/shape 对
距离或接触判据
是否涉及模型覆盖缺失
是否涉及终点本身碰撞
```

完成标准不是“所有旧失败都能被拒绝”，还要保证明确无碰撞的状态没有被全部误拒绝。

世界模型可以使用 cuboid 或 mesh，但选择必须与实际碰撞几何相符；cuRobo 对不同表示有不同的检查器，不应把所有物体一律用粗大包围盒后，再把所有拒绝解释成真实不可行。citeturn866448search2

## 步骤 12：先裁决抓取终点，再运行物理

这一步必须有两个明确出口。

### 出口 A：原 grasp 终点在正确模型下合法

允许按既有条件范围执行：

```text
pregrasp → full-window Gate
grasp → full-window Gate
close → hold
从实际闭爪状态规划 25 mm lift
原 post-lift Gate
停止
```

保留现有 20 mm 最小升高、50 帧确认、5 mm / 0.05 rad 最大相对漂移，不因结果不好调整。

### 出口 B：原 grasp 终点本身就碰垫子或穿入瓶子

**不要运行，也不要放宽 Gate。**

直接生成新版本的几何驱动抓取提案：

```text
同一 asset、同一 arm
根据实际张开夹爪包络和垫子 clearance
选择可接近的抓取截面
先计算最终目标
再冻结 recipe 与资格输入
```

如果改变了目标，新 recipe 必须关联旧 recipe，不能覆盖旧 hash。它不属于“原两个候选直接重跑”的许可。

这不是推倒研究 Idea，而是在修正不合适的抓取实现。

## 步骤 13：模型修复后若仍失败，按失败阶段继续，而不是重新扩候选

| 失败位置 | 应继续处理 |
|---|---|
| 正确模型下 grasp endpoint 无解/碰撞 | 新抓取目标或局部场景设计 |
| endpoint 合法，中间路径碰撞 | 路径与碰撞包络 |
| pre-close 通过，闭爪后滑动 | 接触、闭合量、物体质量/摩擦与夹爪控制 |
| 微抬升通过，之后 shared-V 才失败 | 持物动作与中心/速度设计 |
| 工程或计数异常 | 修局部实现，不把它记成物理失败 |

**当前最重要的是先拿到“正确模型下合法抓取 + 稳定微抬升”，不是重新写一次完整 VVHH/VHVH/VHHV root。**

---

# 五、F1/F4 后续可以继续准备，但不要再往已经完成的三个 cohort 里盲目加数据

## 步骤 14：把已有 18 格登记为可复用输入，而不是重采

这三个六格结构已经有完整证据：

```text
F1-A：6
F1-B：6
F4-A：6
合计：18
```

下一步只做只读 eligibility 清单：

```text
原 root 身份
程序语义
r_pc / variant 配对
source profile
raw/video/acceptance 引用
是否含明确标注的收据恢复
用于 development/pilot 的范围
```

没有新缺陷证据，不再重审或重跑这些物理轨迹。

但**输入证据齐全不等于 Stage 1 机制检查通过**。当前状态仍应保留这两个字段：

```text
pilot_input_evidence_complete = 18
stage1_accepted = 0
```

这是最新 readiness 的口径。fileciteturn463file0L2-L2

## 步骤 15：准备 F4-B，而不是给 F4-A 改个 ID

后续 F4 还需要：

```text
F4-B：
3 r_pc + 3 r_inv_motion = 6 条
```

B 应是另一个按协议生成的 root。不能把 A 的相同 current 和旧动作复制后改名，就算新根。

现在可以完成其 CPU proposal：

- 新 root/scene seed 与布局规则；
- 三种程序仍为 ABC/ACB/BAC；
- 固定程序语义与 family verifier；
- 新根自己的 current、anchor、prefix；
- 统一 motion variation 规则；
- 从实际调用链推导预算。

**本轮不凭空批准这六条 GPU 采集。**待具体 root 与运行入口确定后，与 F2/F3 下一阶段一起提交窄范围执行包，避免每个 helper 单独往返。

## 步骤 16：把离正式批量采集的剩余工作写成固定矩阵

当前已有 18 个候选 pilot 格子后，结构上还剩：

```text
F2-A/B：12 条
F3-A/B：12 条
F4-B：6 条
合计：30 条
```

但不能把这 30 条全部当作“现在已经能采”——F2/F3 需要先通过各自模板资格。

正式推进顺序应是：

```text
F2/F3 模型与目标修复
        ↓
各获得一个三分支 development root
        ↓
补齐 A/B pilot 结构与真实 realization
        ↓
48 条 pilot 的数据和机制检查
        ↓
Stage 2 冻结正式协议、预算与 split
        ↓
明确批准 formal 360
        ↓
小波次采集，按同一封存协议继续
```

**不要要求 pilot 每个 root 提前做正式 9/9；也不要因为 F1/F4 成功，就直接放量替代缺失的 F2/F3。**

---

# 六、这一轮应当怎样安排，才能避免继续“做了很多但没有推进关键问题”

建议 Codex 本轮只保留两个主交付和一个辅助交付。

### 主交付 A：F2 端点约束结论

不是“已实现诊断器”，而是条件满足后真正完成既有许可内的诊断，并回答：

> U/D 是目标转换问题、固定方向问题、自碰限制，还是环境约束？是否有一组完整约束下有效的端点和路径？

结果后自动继续完成对应的 CPU root/布局提案。

### 主交付 B：F3 模型一致性与抓取终点结论

不是“添加了 pad/bottle”，而是回答：

> 当前执行中的 planner 是否使用了正确几何和夹爪状态？原两个 grasp 终点是否合法？合法者是否能真实抓起？

原终点不合法就停止物理重跑，直接给出几何修订提案。

### 辅助交付 C：pilot 输入与 F4-B 准备

只读固定已有 18 格来源，准备 F4-B 的精确 CPU proposal。不要继续改成功的 realization runtime。

**GPU 谁先满足前置条件就先串行执行；F2 的科学失败不阻塞 F3，反之亦然。清理、计数或 GPU 身份失败才停止整个队列。**

---

# 七、可以直接转发给 Codex 的执行指令

```yaml
review_base:
  vault_head: 47b29383e59636d452357e72e0349289c3e95b50

completed:
  nine_realizations: RETAIN_ACCEPTED_NO_RERUN
  development_roots: 6
  development_raw_trajectories: 27
  repeat_F4_adoption: false
  reopen_completed_nine_cell_batch: false

source_policy:
  retain_F1_parent_source_profile: true
  retain_F4_successful_source_profile: true
  preserve_existing_references_and_artifacts: true
  isolate_F2_F3_model_changes: true
  do_not_rewrite_hashes_to_force_compatibility: true

F2:
  decision: CONTINUE_EXISTING_CONDITIONAL_ENDPOINT_DIAGNOSIS
  parent_decision_receipt_sha256: 46c42f0470fcf5be8bb34c619606c7a4d4d5b4f72827eaae13a899eec10ac09d

  implementation_priorities:
    - reproduce the complete original gripper-to-endlink and world-to-planner transform
    - map solver joints by name
    - verify K0 disables both collision optimization and collision acceptance checks
    - use one fixed seed bank and iteration budget
    - cross-validate returned solutions with FK and all constraint checkers
    - distinguish carried-can geometry from ordinary static obstacles
    - preserve unknown accounting as unknown

  existing_caps:
    ik_problems: 15
    trajectory_queries: 4
    total_solver_problems: 19
    fresh_planner_only_scenes: 2
    physical_executions: 0
    new_roots: 0
    training_raw: 0

  execution:
    - C_U_D_under_K0_K1_K2
    - conditional_registered_yaw_tests
    - one_route_for_first_fully_valid_endpoint_pair
    - stop_without_new_hub_or_seed_search

  automatic_cpu_followup:
    on_success: prepare_versioned_controlled_insertion_root_scope
    on_failure: prepare_one_evidence_based_target_or_layout_revision
  physical_root_authorized_by_this_reply: false

F3:
  decision: CONTINUE_EXISTING_MODEL_REPAIR_AND_CONDITIONAL_TWO_CANDIDATE_MICRO
  candidates:
    - f3-final-pose-v3-r3063
    - f3-final-pose-v3-r1401

  prerequisites:
    - actual_open_gripper_joint_and_geometry_conformance
    - table_pad_bottle_world_geometry_conformance
    - correct_object_world_to_planner_transform
    - actual_solver_or_worker_update_verified
    - known_clear_and_known_failure_state_checks
    - grasp_endpoint_validity_separate_from_path_validity
    - explicit_approach_close_lift_contact_semantics

  existing_caps:
    trajectory_queries: 6
    physical_scenes: 2
    additional_non_action_conformance_scenes: 2
    aggregate_fresh_scenes: 4
    physical_attempts: 2
    shared_v: 0
    no_suffix: 0
    new_roots: 0
    training_raw: 0

  invalid_endpoint_action:
    execute: false
    relax_gate: false
    overwrite_old_recipe: false
    next: geometry_derived_versioned_grasp_proposal

  valid_endpoint_action:
    - pregrasp_and_existing_full_window_gate
    - grasp_and_existing_full_window_gate
    - close_and_hold
    - plan_lift_from_actual_post_close_state
    - existing_post_lift_audit
    - stop

  candidate_search_expansion: false
  automatic_job_retry: false
  automatic_shared_v_or_root: false

pilot_preparation:
  read_only_eligibility_for_existing_18_cells: true
  recapture_existing_18_cells: false
  prepare_F4_B_exact_CPU_proposal: true
  new_F4_B_GPU_collection_authorized: false
  automatic_stage1_promotion: false

next_handoff:
  include:
    - F2 constraint matrix and exact next decision
    - F3 model conformance and endpoint/micro results
    - actual source and solver versions
    - executed and unconsumed budgets
    - first failure evidence rather than repeated historical summaries
    - pilot input mapping and F4_B proposal
  do_not_stop_after_only_helper_or_unit_test_completion: true

global:
  stage0_rerun: false
  stage1_collection_authorized: false
  formal_360_authorized: false
  training_authorized: false
  h_reveal_authorized: false
  compression_authorized: false
  pi05_authorized: false
  gpu_jobs_serial: true

  stop_entire_queue_on:
    - unknown_resource_accounting
    - source_or_asset_binding_mismatch
    - task_owned_orphan_process
    - cleanup_failure
    - selected_GPU_identity_or_baseline_failure
    - evidence_integrity_failure

  scientific_failure_with_clean_cleanup_blocks_other_family: false
```

**最重要的一句话：F1/F4 的这九条已经完成，不要再绕回去修它们。下一轮要交出的应当是 F2 的“固定目标为什么不成立”与 F3 的“正确模型下抓取终点是否合法”的实际结论；这两个结论出来，才有依据把剩余两族改成稳定可批量生成的模板。**

---

If you want, I can:

- 制定F2/F3问题诊断详细计划
- 设计F3抓取终点合法性验证流程
- 规划F4-B数据采集和开发方案
