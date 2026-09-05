# 结论：现在应该做一次针对性的模型与任务实现调整，而不是继续修补旧路线

我核对了最新提交 **`ef5cdfc8cd13fb99c73252351b2ee07276902f9b`** 的交接、两次运行结果、同一失败证据审计，以及隔离分支里的 collector、realization 生成器、执行器和分级验收代码；还对照了你们锁定版本的 RoboTwin planner 源码。

**接下来的工作应分成三条线，并行推进 CPU 实现、串行执行 GPU 验证：**

| 工作线 | 核心任务 | 不再做什么 |
|---|---|---|
| **F2** | 判断固定目标受哪一种约束限制，再决定是否调整放置姿态或局部布局 | 不再增加第四、第五种中转点 |
| **F3** | 补齐真实碰撞世界、夹爪状态与抓取接触阶段 | 不再把“新增检测器”当作“规划已经修好” |
| **F1/F4 与批量流水线** | 修正 pilot 配对、补齐实际 family 接口，先做小批量真实变体 | 不必等 F2/F3 全部完成才推进 |

需要明确纠正我之前偏乐观的描述：

> **F2、F3 现在不是仅剩几处基础设施小错误，而是已经进入任务约束与规划模型的局部重设计。研究 Idea 不需要推倒，但不能再把旧坐标、旧抓取 recipe 当作必须永远保留的科学要求。**

以下计划可以直接转给 Codex。前半部分解释原因，后半部分明确连续推进范围与停止条件。

---

# 一、这轮证据究竟说明了什么

## 1. F2：已经排除了“只是中转点不好”的解释

最新结果是：

```text
当前姿态 C：通过
直接到 preplace U：IK_FAIL
直接到 release D：IK_FAIL
三条路线：均在第一个目标处 IK_FAIL
```

而且每次起点恢复、坐标绑定、计数、清理都正常。因此，继续改变 hub 没有足够依据；应该直接研究固定 U/D 的**位置、方向、抓持偏移、关节限制与碰撞约束**。fileciteturn443file0L2-L2

但“求解失败”仍然不等于“数学上没有解”。当前审计也明确没有证明几何不可达；简单比较目标距离和机械臂各段长度之和，无法回答有方向约束的可达性。fileciteturn446file0L2-L2

## 2. F3：新的接近动作已经改善，剩下的问题发生在真正进入抓取位置时

本轮实际进入物理阶段的是两个候选，不是四个：

- `r3063`：pregrasp 通过，grasp 时手指碰垫子。
- `r1401`：pregrasp 通过，grasp 时瓶子位移超过限制。
- 另外两个候选在规划阶段失败，没有执行物理动作。

两个物理候选都没有闭爪，因此本轮并没有测试到新的 25 mm 抬升与 post-lift 验收。fileciteturn443file0L2-L2

尤其重要的是：两个抓取段的最大关节跟踪误差约为 **0.017 / 0.013 rad**，瓶子最大位移却约为 **20 / 46 mm**。这说明这次不能简单继续归咎于“机械臂没跟上指令”。fileciteturn445file0L2-L2

## 3. 规划世界缺少真实物体，是已经找到的具体实现缺口

我核对了锁定版本 `envs/robot/planner.py`：`CuroboPlanner` 初始化的 `world_config` 确实只有一个 `table`。它创建了 `motion_gen` 和 `motion_gen_batch` 两个实例，不能只修其中一个就认为全部入口已修好。fileciteturn451file0L2-L2

不过还要区分：

> **“加入垫子和瓶子”能够阻止错误路径被放行，不保证原来的抓取目标因此变得可行。**

如果目标姿态本身就让张开的手指穿过垫子，正确的规划器应当拒绝这个目标，而不是设法执行它。

---

# 二、F3：修复“规划器看到的世界”，同时检查原抓取终点是否成立

## 步骤 1：只用本轮两个失败候选，完成一次同证据对照

先固定：

```text
r3063
r1401
```

复用它们的原始场景、资产、目标、起点、规划结果和失败 trace。

第一轮模型修复不增加新瓶子、不再运行另外两个已经规划失败的候选，也不重跑整套 40-query Stage A/B 筛选。

需要分别回答：

| 检查 | 要回答的问题 |
|---|---|
| 抓取终点 | 张开夹爪到达这个姿态时，几何上是否已经碰垫子或穿进瓶子？ |
| 抓取路径 | 终点可行，但中间轨迹是否碰撞？ |
| 夹爪开度 | planner 使用的手指位置，是否与 SAPIEN 实际张开状态一致？ |
| 模型覆盖 | planner 的碰撞球/网格，是否覆盖发生接触的手指和掌部？ |

**先区分“终点本身错误”和“通往终点的路径错误”，再改代码。**否则会再次陷入“补模型之后全部 IK_FAIL，却不知道为什么”。

## 步骤 2：重点检查夹爪关节，而不只核对六个机械臂关节

这是本次源码复核发现的一个值得优先验证的点：

- planner 配置列有六个机械臂关节和两个夹爪关节；
- `plan_path()` 构造 `JointState` 时，只传入 `active_joints_name` 对应的机械臂关节；
- 因此必须核对其余夹爪关节实际使用了什么：锁定值、retract 值，还是实时状态。fileciteturn446file0L2-L2 fileciteturn451file0L2-L2

这还不是已证实的根因，但它与“手指碰垫子”的现象直接相关。

Codex 应导出一份简明对照：

```text
SAPIEN joint name → 实际 qpos
CuRobo joint name → 当前模型 qpos/locked value
open gripper 时左右手指的世界位姿
两侧模型手指包络的差异
```

**如果 planner 用的是偏闭合的手指，而真实执行时夹爪张开，就必须修正规划状态；不能通过增大接触容差掩盖。**

## 步骤 3：新增统一的 scene→planner world 转换，不再手写另一套桌面坐标

建议新增一个小模块，例如：

```text
planner_scene_bridge_v1.py
```

职责只有三个：

```python
capture_collision_scene(...)
convert_world_to_planner_frame(...)
apply_and_verify_planner_world(...)
```

至少包含：

- 实际桌面碰撞几何；
- F3 垫子；
- F3 瓶子；
- 执行臂与夹爪；
- 位于运动区域的对侧机械臂或其他固定障碍。

必须使用实际 actor pose、collision-shape local pose、scale 和正确的坐标转换。**不能将 model metadata 的中心、collision mesh 中心和 actor origin 混为一谈。**

你们的 planner 对 Aloha 目标还额外应用了 `frame_bias` 与小角度旋转。因此，障碍物转换也必须使用同一套世界到 planner 坐标关系，不能直接把世界坐标填进 CuRobo。fileciteturn451file0L2-L2

cuRobo 本身提供世界更新接口，但更新后的障碍物数量受初始化 collision cache 容量约束。应按当前安装版本预留容量，并验证实际实例收到的对象列表与位姿；不要为了这次修复顺便升级整个 cuRobo。citeturn618803view3

### 必须产生的模型验证结果

不是一句 `update_world_called=true`，而是：

```text
导出的障碍物集合
实际 planner 中的障碍物集合
每个对象的 pose、geometry hash、frame
夹爪状态
应用到哪个 MotionGen 实例/worker
```

如果使用 worker 模式，必须真正通过该 worker 的入口更新，并收到确认；不能只修改主进程中的同名 Python 对象。

## 步骤 4：用旧失败位置检验模型是否真的看到了问题

从已封存 trace 中选：

```text
初始无碰撞状态
pregrasp 成功终点
首次手指碰垫子的状态
瓶子开始被推动前的状态
抓取目标对应的规划关节状态
```

比较旧模型与新模型的距离/碰撞判断。

注意，SAPIEN 可能在有小正间距时就产生接触冲量。你们本轮手指—垫子记录就是如此。因此不能只用“距离小于零”判断模型是否覆盖物理接触，还要对照实际 contact offset、碰撞球 buffer 和既有 physical classifier。fileciteturn445file0L2-L2

这一步的完成标准是：

> **新模型能够解释旧路径为何不应通过，同时不会把明确无碰撞的 pregrasp 状态全部误判为碰撞。**

只验证“旧失败都被拒绝”，还不够；否则把整个空间都标成障碍也能通过测试。

## 步骤 5：明确“接近、闭爪、抬升”三个阶段的允许接触

不能简单做：

```text
把瓶子加入障碍物
→ 抓取到不了
→ 再把瓶子整体删除
```

应区分：

| 阶段 | 规则 |
|---|---|
| 接近与进入抓取位 | 机械臂、掌部、张开手指不能穿过瓶子或垫子；目标应是可闭合的抓取位置 |
| 闭爪 | 允许选定手指与瓶子形成抓持接触；仍禁止手指碰垫子、掌部推瓶子 |
| 抬升 | 瓶子随夹爪运动；保留持物碰撞包络，验证与原支撑面的分离 |

原抓取姿态如果存在不可接受的几何穿插，应先判为 **目标不成立**。不能降低 pre-close Gate 的瓶位移限制来保住它。

后续持物规划可利用 cuRobo 的 attached-object 能力，但绑定变换必须来自实际抓持状态。**在 planner 中 attach 只是碰撞建模，不允许在 SAPIEN 中偷偷把瓶子焊到手上来制造抓取成功。**citeturn618803view2

刚开始抬升时，瓶子与原支撑面接触是正常起始条件。对此需要明确的分离阶段处理，不能因此全局关闭垫子碰撞，更不能同时放开手指—垫子接触。

## 步骤 6：模型验证通过后，只做两个候选的最小物理重验

**本轮给予条件执行范围：最多两个候选，各一次，不再重跑旧 52-query 面板。**

建议实际流程：

```text
新世界模型下规划 pregrasp、grasp
→ 执行 pregrasp + 原 full-window Gate
→ 执行 grasp + 原 full-window Gate
→ 通过后 close + hold
→ 从实际闭爪后的状态规划 25 mm lift
→ 原 20 mm / 50 帧 / 5 mm / 0.05 rad 验收
→ 停止
```

把 lift 放到实际闭爪后再规划，是为了使用真实夹爪开度和抓持变换；前后仍最多三次路径查询，不需要扩大为长动作测试。

上限：

```text
r3063、r1401 各一次
最多 6 次轨迹规划查询
最多 2 个物理场景
若模型对照必须新建只读场景，额外最多 2 个
最多 4 个 fresh scenes
shared-V / no-suffix / root / training raw = 0
```

前置条件包括新模型已通过上述正负对照、原抓取终点可行、接触阶段语义已实现和 source/manifest 已冻结。**任何一项没实现，就不能将这份条件许可当作“先跑再说”。**

### 如果原抓取终点仍不可行

不要继续对相同目标重试。

允许 Codex 继续完成一个**几何约束驱动的 CPU 抓取修订提案**：在同一 asset、同一 arm 下，依据夹爪张开包络、垫子距离、可接近表面重新计算抓取位。

这时必须：

- 使用新 recipe/version，关联原 recipe；
- 先算新目标，再做资格验证；
- 不覆盖旧 hash；
- 不以“原 recipe 已冻结”为由拒绝必要修改；
- 不把新目标悄悄塞回旧许可。

如果两个旧终点都不成立，本轮物理重验可以是零次，直接提交这份有几何证据的修订，不浪费 GPU。

---

# 三、F2：先拆开约束，再决定保留目标还是调整实现

## 步骤 7：停止运行旧 U/D 的路径搜索，改做一次端点约束辨析

下一轮不要再调用完整 `plan_single()` 去反复寻找通向同一失败端点的路线。

使用同一套关节限制、目标变换、容差、固定 seed bank，对 **C、U、D** 做三种 IK 配置：

| 配置 | 包含什么 | 要判断什么 |
|---|---|---|
| K0 | 关节限制，关闭碰撞成本与碰撞判定 | 单纯的位置与方向约束是否有可找到的解 |
| K1 | 关节限制 + 自碰 | 是否主要受自碰限制 |
| K2 | 关节限制 + 自碰 + 当前审计后的规划世界 | 是否主要受环境碰撞限制 |

共 **3 个目标 × 3 个配置 = 最多 9 个 IK 问题**。

cuRobo 的 IK 配置本身区分世界模型、自碰检查和自碰优化，并支持返回关节解、位置误差、旋转误差；适合做这类分解诊断。citeturn250790view0

**K0/K1 只是诊断。它们得到的解永远不能直接交给机械臂执行。**

每个结果必须保留：

```text
目标与 frame
seed bank 与迭代上限
返回 qpos
FK 重算的位置/方向误差
关节余量
自碰距离
环境碰撞距离/相关对象
实际求解调用数
```

不能只记录一个 `success`。

固定数值求解没有找到解，仍不能写成数学不可达证明；但已经足够判断下一步该改哪个层面。

## 步骤 8：先核对“放 beside”到底需不需要固定这个朝向

我建议把两类约束分开：

```text
科学语义：
同一罐子放在指定 reference 旁边，满足 beside 区域与互斥关系。

实现选择：
当前某个精确放置 quaternion、某种腕部朝向。
```

如果 F2 的标签和 verifier 并不要求罐子保持某个特定 yaw，那么把 yaw 永久锁死可能是不必要的困难。

允许准备一个**保持目标中心、直立和 relation 不变**的有限朝向集合：

```text
原 yaw
原 yaw + 90°
原 yaw - 90°
原 yaw + 180°
```

这里不是假设罐子几何完全旋转对称。每个朝向都必须重新计算：

- actor origin 与 geometry centre 补偿；
- 支撑高度；
- 罐体和夹爪包络；
- preplace/release EEF 目标；
- relation 与碰撞检查。

必须使用实际抓持变换：

\[
T_{\text{world,EEF目标}}
=
T_{\text{world,物体目标}}
\left(T_{\text{EEF,物体}}\right)^{-1}
\]

**不能保持物体目标不动，却任意旋转 wrist 来假装抓持关系仍一致。**

若预先审查确认 yaw 变化不改变任务语义与冻结的非朝向约束，可在 K2 下对三个新增 yaw 的 U/D 各求解一次，最多再增加 **6 个 IK 问题**。

## 步骤 9：只对第一个同时通过 U/D 的朝向规划一条完整路线

固定朝向顺序后，选第一个 U、D 都通过完整约束检查的朝向，规划：

```text
U → D → U → N
```

最多四次轨迹查询，不再增加 hub 扫描。

本轮 F2 条件许可总上限：

```text
IK 问题最多 15 个
轨迹规划最多 4 次
合计最多 19 个计费求解问题
fresh planner-only scenes 最多 2 个
physical / root / training raw = 0
```

批处理一次求八个目标，仍按八个 IK 问题计数；内部 seed 数和迭代也要冻结，不能把隐藏的大搜索包装成“一次调用”。

如果有限朝向集合仍无解，停止该集合。

## 步骤 10：若固定位置确实不适合，就调整局部布局，不必推倒 F2

**我的优先备选是：把 beside reference 与其目标区域作为一组，移到执行臂更合适的工作区，而不是继续挑战跨工作区的旧目标。**

但不要现在凭空指定一个“肯定能成功”的新坐标。Codex 应用模型和冻结规则确定一个修订布局，满足：

```text
reference 与 beside 目标相对关系保留
inside / on / beside 三种意图区分保留
对象、障碍、桌面之间几何合法
三种分支仍共享同一 current
整个 root 使用同一执行臂
可见性与标签泄漏检查保留
```

移动 reference 会改变 current，因此必须新建 root/spec，重新做当前状态与公共前缀验证。

这并不违反你们的 Idea：

> **same-current 要求的是“同一组里的三条分支具有相同 current”，不是要求所有开发版本永远使用第一次设计的桌面坐标。**

旧 inside 5/5 仍保留为历史证据；如果新布局影响场景绑定，它不能自动成为新 root 的资格证明。

---

# 四、公共采集代码：已有主体，下一步补实际接线，不再重造框架

## 步骤 11：接受隔离 collector 的修复方向，进入一次集成发布

隔离代码已经改为：

```text
provisional branch
→ 最终分歧计算
→ finalized branch receipts
→ root receipt
→ publication index
```

而且 publication index 明确只表示发布完整，不授予阶段验收。这种区分是正确的。fileciteturn456file0L2-L2

下一步只做：

1. 将这一修复与实际 F1/F4 adapter 集成到一个新的候选运行目录。
2. 使用真实 disk reader、prefix loader、raw/video writer 和 family verifier。
3. 校验最终执行的就是该版本，不是隔离测试通过、生产入口仍调用旧代码。
4. 保留 F4 旧数据与 resolution，不重采、不重登记。

**不再新建另一套 Guard、另一套收据体系。**

## 步骤 12：修正 F1 pilot A/B 的变体来源错配

这是本轮实际代码中一个明确的问题：

`build_reuse_candidates()` 收集了 F1 的前两个 root，分别作为 pilot A/B；但是返回给 `operation_proposals()` 的只有 `f1_roots[0]`，随后在这个 A root 上生成 path 和 motion 两类变体。fileciteturn452file0L2-L2

所以必须改成：

```text
F1-A：生成 3 条 r_inv_path
F1-B：生成 3 条 r_inv_motion
F4-A：生成 3 条 r_inv_path
```

每条变体都从对应 root 的：

```text
candidate_frozen spec
reference current / anchor
canonical prefix
suffix targets
验收来源
```

生成。

**不能从 A root 生成一条 motion 轨迹，再改标签说它属于 B。**

## 步骤 13：补齐 operation executor 与原 family 执行器的等价关系

当前 `generate.py` 主要根据 segment 名字插入 move、close、open、hold、verify；实际 `SapienOperationAdapter` 的 scene、anchor 和 program verifier 仍通过待绑定 hook 提供。fileciteturn450file0L2-L2 fileciteturn452file0L2-L2

因此，26 项测试不能直接推出“已经可以真实采集”。

需要一次性完成以下具体绑定：

```text
F1 scene factory
F1 current/anchor/prefix replay
F1 正确对象与非目标不动 verifier

F4 scene factory
F4 right-prefix / left-suffix 调度
F4 每子任务接触、已完成槽位保持、未操作物体保持
F4 common-X 与终态等价 verifier

两族实际 raw/video/cleanup 入口
```

尽量复用已经成功的 family 实现。变体只替换明确标记的非关键运输目标或时间参数，不用通用操作列表重新发明一遍物理逻辑。

## 步骤 14：把失败计数和 retiming 的边角问题一起收口

这两项放在同一次集成里，不另开审批循环：

**失败计数。**  
当前 `execute_to_artifacts()` 的异常记录保存了 error 和 cleanup，但没有保存完整的实际 planner 消耗。复用已有 `before / finally / after` 机制，失败也记录真实 query delta，缺失则写 unknown，不能按零处理。fileciteturn450file0L2-L2

**时间缩放。**  
当前 retiming 先把采样点数取整，再按名义 `1.10` 缩放速度。应同时记录取整后的实际 duration scale，核对 position、velocity、dt/长度字段一致，以及拼接段的边界连续性。

这不是禁止重定时。允许改变**下一次真实执行的控制指令**；禁止重采样旧 raw 后冒充新的真实 realization。

另外，验收时要确认变化真的发生了：路径变体有实际路径差异，运动变体有实际阶段时长变化，不能只因为两个文件 SHA 不同就算不同 realization。

---

# 五、先让 F1/F4 进入真实小批量，不让整个项目被 F2/F3 拖住

## 步骤 15：准备一个九条轨迹的 development realization 小批次

在上述具体 family 绑定和 CPU 预检通过后，按以下范围推进：

| 对象 | 新采集内容 | 条数 | 当前代码推导的 planner 上限 |
|---|---|---:|---:|
| F1-A | 三个 intent 的 `r_inv_path` | 3 | 33 |
| F1-B | 三个 intent 的 `r_inv_motion` | 3 | 33 |
| F4-A | 三个 program 的 `r_inv_path` | 3 | 90 |
| 合计 | 新的真实 rollout | **9** | **156** |

`F1=11 / F4=30` 来自当前操作链中 move 的计数，不是已证明完整入口没有额外查询。**发布前必须用最终 family 绑定重新验证；如果实际入口超出 156，就停止签发并报告差异，不得漏记额外查询。**当前代码也明确这些预算尚未完成实际 family 集成。fileciteturn443file0L2-L2 fileciteturn450file0L2-L2

本轮对这九条给予**条件式 development 采集许可**：

- 原始 root 和程序不变；
- path 只用已提出的非关键运输 `z+15 mm`；
- motion 只用同一规则的 `duration×1.10`；
- 每个 cell 一次真实尝试，无自动重试；
- 新 namespace，不覆盖已有数据；
- 同 cohort 三种 intent 使用同一变体规则；
- 原物理/verifier 阈值不变；
- 全部经过已有 Guard、source lock、raw/video 和 cleanup。

它们不是正式 360，也不因为文件生成就自动计入 Stage 1。

每个三轨迹 cohort 可以先执行第一条作为该 cohort 的入口检查。若第一条暴露接线、计数或 artifact 错误，停止该 cohort，避免另外两条重复消费；不是重新挑一条更容易成功的 intent 来替代。

## 步骤 16：修正后的九条完成后，最多有 18 个 pilot 可用格子

已有待审复用：

```text
F1-A 的 3 条 r_pc
F1-B 的 3 条 r_pc
F4-A 的 3 条 r_pc
= 9 条
```

补采上述九条后：

```text
F1 两个 pilot roots：12 条
F4 pilot A：6 条
合计 18 条候选 pilot 数据
```

仍需要按统一协议验证来源、配对与阶段 eligibility，才能更新 Stage 1 接收计数。不能只按 `9+9` 自动写成 `18/48 accepted`。

后续剩下的结构很明确：

```text
F2 A/B：12 条
F3 A/B：12 条
F4 B：6 条
合计 30 条
```

这样做的价值是：**在修 F2/F3 的同时，批量采集接口已经开始接受真实压力测试，而不是四族都修完后才第一次测试批量流程。**

---

# 六、从开发验证走到正式 360：按这个顺序，不再增加无关前置条件

## 步骤 17：F2/F3 分别拿到一个完整三分支 root

### F2

```text
目标约束辨析
→ 选定可行放置姿态或新布局
→ 三关系完整规划
→ 真实 inside/on/beside
→ 一个 development r_pc root 验收
```

inside 仍必须是受控插入、支撑后慢释放；不能回到 gravity drop。

### F3

```text
准确碰撞模型 + 合法抓取终点
→ 稳定 micro-lift
→ 持物 shared-V
→ canonical prefix + 精确重放
→ VVHH / VHVH / VHHV
→ 一个 development r_pc root 验收
```

后续 shared-V 应以实际持物中心展开，不恢复固定全局中心跳转的旧错误。

这两条不应都用“大批筛选”解决。先得到物理和语义都可信的一个模板，再扩展。

## 步骤 18：完成 48 条 pilot，做机制检查

保持主方案：

```text
每 family：
A = 3 intents ×（r_pc + r_inv_path）
B = 3 intents ×（r_pc + r_inv_motion）

四 family 合计 48 条
```

不要重新要求 pilot 每个 root 都先做正式 9/9。

重点验证：

```text
同意图不同路径/速度仍通过 family verifier
错误对象、错误关系、错误顺序会被拒绝
同 root 数据不能跨 split
路径名、planner ID、长度和 padding 不直接泄漏标签
F3/F4 的终态不能替代过程顺序
current / anchor / event 对齐正确
```

未完成完整阶段授权前，可以先运行不训练模型的 structural/data audits；不要把 CPU 检查混成模型实验已经完成。

## 步骤 19：用 pilot 的真实运行统计冻结正式预算

正式预算应由本轮真实日志回答：

- 每个 family 一条轨迹实际消耗多少规划查询；
- 一组完成率；
- 哪些失败属于任务不可行，哪些属于运行错误；
- 数据量、视频开销、写盘与清理是否稳定；
- 每 root 有限重试和 reserve 的使用规则。

不要继续凭“理论 target 数”直接写整个正式运行预算，也不要把大量内部 solver seeds 隐藏在一次 query 后面。

## 步骤 20：封存正式协议，再以小波次启动正式采集

Stage 2 保留：

```text
40 primary roots
16 ordered reserves
每 family 5 train / 2 validation / 3 test
正式每 root 9 条
```

未激活或未通过 feasibility 的条目保持 pending，不伪造 current/candidate hash。

正式采集获批后，建议先执行**每 family 一个预先指定的 train root，共四个 root、36 条**。这 36 条属于原 360 的一部分，不再额外制造一个无限增长的 smoke 数据集。

通过流水线、文件完整性和计数验收后，再按同一封存规则继续剩余 roots。普通单条规划失败按冻结规则处理，不要求每次都来回外审；碰到源码变动、计数未知、数据污染或新模型级错误才暂停。

---

# 七、必须调整的研发原则

这部分比再增加十个测试更能提高效率。

### 1. 科学约束和实现参数分开管理

必须严格保留：

```text
同组 same-current
真实成功多分支
对象/目标/程序语义
独立 verifier
防泄漏与数据来源
```

允许版本化修改：

```text
中转点
不影响语义的放置 yaw
抓取位
局部场景布局
碰撞世界表示
```

不能因为某个实现参数曾写进 manifest，就把它提升成不可改变的研究目标。

### 2. 检测器通过不等于系统修复

F3 新 Gate 正确阻止了错误闭爪，是好事；但它只是指出哪里错了。接下来必须改变导致碰撞的模型或目标，否则再增加测试只会更稳定地得到失败。

### 3. 不再反复审批已经完成的工作

F4 采纳不再重审。Guard、短 TMPDIR、原收据修复不再重做。新审阅只关注本轮实际改变的模型、目标和采集接口。

### 4. 报告必须同时给出“成功证据”和“缺口”

不要再用：

```text
CPU 26/26，所以可以批量造
```

应使用：

```text
CPU 接口通过
实际 family 接线通过
真实 rollout 通过
cohort 完整
阶段验收通过
```

每层有各自的证据和状态。

---

# 八、给 Codex 的本轮执行范围

下面是本轮连续推进的边界。新运行必须先完成实现、测试、实际调用链预算和版本化 manifest，再执行；不是让旧清单直接重试。

```yaml
review_base:
  vault_head: ef5cdfc8cd13fb99c73252351b2ee07276902f9b

global:
  stage0_rerun: false
  formal_360_authorized: false
  training_authorized: false
  h_reveal_authorized: false
  compression_authorized: false
  pi05_authorized: false
  gpu_jobs_serial: true
  automatic_job_retry: false

F4_existing:
  status: ACCEPTED_RETAIN_UNCHANGED
  reapproval_required: false
  original_root_rerun: false
  duplicate_registration: false

F2:
  decision: CONDITIONAL_ENDPOINT_CONSTRAINT_DIAGNOSIS_V1
  old_transit_panel_reissue: false

  preserve:
    - original C/U/D and grasp-transform evidence
    - metadata geometry source
    - joint limits and configured solver tolerances
    - inside historical evidence
    - original failure records

  phase_1:
    goals: [C, U, D]
    configurations:
      - K0_joint_limits_only
      - K1_joint_limits_and_self_collision
      - K2_joint_limits_self_collision_and_audited_world
    ik_problem_cap: 9
    execution_of_collision_disabled_solutions: false

  conditional_phase_2:
    prerequisite: yaw_is_not_part_of_required_task_semantics
    additional_object_yaws_degrees: [90, -90, 180]
    goals_per_yaw: [U, D]
    additional_ik_problem_cap: 6
    recompute_actor_origin_and_eef_from_grasp_transform: true
    preserve_geometry_center_and_relation: true

  conditional_phase_3:
    prerequisite: one_yaw_has_both_U_and_D_valid_under_full_constraints
    selection: first_in_preregistered_order
    trajectory_targets: [U, D, U, N]
    trajectory_query_cap: 4

  aggregate_caps:
    ik_problems: 15
    trajectory_queries: 4
    total_solver_problems: 19
    fresh_planner_only_scenes: 2
    physical_executions: 0
    roots: 0
    training_raw: 0
    formal: 0

  after_failure_cpu_work:
    - fixed_target_and_constraint_failure_matrix
    - one_versioned_local_layout_or_grasp_pose_revision_proposal
    - no_additional_hub_scan
    - no_unapproved_target_execution

F3:
  decision: REPAIR_SCENE_AND_GRIPPER_MODEL_WITH_CONDITIONAL_TWO_CANDIDATE_MICRO

  reference_candidates:
    - f3-final-pose-v3-r3063
    - f3-final-pose-v3-r1401

  required_before_physical:
    - verify_actual_open_gripper_joint_state_in_planner
    - export_table_pad_bottle_and_relevant_robot_geometry
    - use_one_verified_world_to_planner_transform
    - apply_world_to_the_actual_solver_or_worker
    - validate_known_clear_and_known_failure_states
    - classify_endpoint_collision_separately_from_path_collision
    - implement_explicit_approach_close_lift_contact_semantics
    - reject_invalid_original_grasp_endpoint
    - freeze_source_world_targets_and_budget_before_launch

  conditional_micro_caps:
    trajectory_queries: 6
    physical_scenes: 2
    additional_non_action_conformance_scenes: 2
    aggregate_fresh_scenes: 4
    physical_attempts: 2
    shared_v: 0
    no_suffix: 0
    roots: 0
    training_raw: 0
    formal: 0

  micro_order:
    - plan_and_execute_pregrasp_with_existing_gate
    - plan_and_execute_grasp_with_existing_gate
    - close_and_hold_only_after_gates_pass
    - plan_lift_from_actual_post_close_state
    - retain_existing_post_lift_contract
    - stop

  invalid_endpoint_response:
    - do_not_execute_it
    - retain_original_candidate_evidence
    - build_new_geometry_derived_recipe_proposal
    - do_not_overwrite_original_recipe_hash

downstream:
  cpu_integration_authorized: true
  retain_existing_guard_and_acceptance_framework: true

  required:
    - integrate_isolated_collector_publication_fix
    - bind_actual_F1_and_F4_scene_anchor_and_verifier
    - generate_F1_A_path_from_root_A
    - generate_F1_B_motion_from_root_B
    - generate_F4_A_path_from_root_A
    - retain_live_query_accounting_on_failure
    - verify_actual_retiming_duration_and_control_consistency
    - validate_realized_not_just_declared_variation
    - preserve_stage_specific_3_6_6_9_acceptance_profiles

  conditional_development_realization_batch:
    cells:
      F1_A_r_inv_path: 3
      F1_B_r_inv_motion: 3
      F4_A_r_inv_path: 3
    rollout_cap: 9
    fresh_scene_cap: 9
    planner_query_cap: 156
    max_attempts_per_cell: 1
    source_derived_budget_must_fit_cap: true
    automatic_retry: false
    new_formal_data: 0
    automatic_stage1_promotion: false

    prerequisites:
      - exact_family_bindings_complete
      - correct_pilot_root_pairing
      - real_disk_writer_loader_verifier_preflight
      - frozen_variation_specs
      - full_runtime_budget_verified
      - source_and_manifest_published
      - existing_GPU_Guard_checks_pass

later:
  F2_full_root_requires_new_exact_execution_scope: true
  F3_shared_v_and_full_root_require_new_exact_execution_scope: true
  stage1_reuse_requires_explicit_eligibility_records: true
  formal_collection_requires_protocol_freeze_and_explicit_authority: true

global_stop:
  - resource_accounting_unknown
  - source_or_asset_binding_mismatch
  - task_owned_orphan_process
  - cleanup_failure
  - GPU_identity_or_baseline_failure
  - raw_receipt_or_video_integrity_failure
```

**我最建议你们改变的是推进重心：不要再追求“把第一次冻结的 F2/F3 实现硬修成功”，而要保住科学语义，允许把不合适的目标和抓取实现改成可稳定生成的版本。同时让 F1/F4 的真实变体小批量先跑起来，这样才能尽快从“单点修复”转入“可重复的数据生产”。**

---

If you want, I can:

- 细化F3模型验证步骤的具体实现细节
- 制定F2不同IK配置的执行计划
- 规划公共采集代码集成的具体路线图
