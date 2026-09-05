# 本轮结论：F4 已经收工；F3 可以执行；F2 应改成有限的路线比较，而不是继续补同一条路径

我以 **`8f24ad4371858edea531822dde61eecad1d11165`** 为基线，核对了交接文档、F4 接收记录、F2 真实失败终端和执行器、F3 新的 post-lift 函数及调用链、测试与 manifest，也重新对照了主数据构造方案。

**这次不需要再让 Codex把整个基础设施翻修一遍。我的决定是：**

| 部分 | 本轮决定 |
|---|---|
| **F4** | 已验收，保留现有 1 root / 3 条轨迹。**不重复审批、不重跑、不重复入账。** |
| **F3** | **通过本次窄范围审阅，批准现有 V1.1 执行一次候选微门。** |
| **F2** | 批准一个有明确前置条件的 **最多 19 次 query、2 个 planner-only scene** 的有限路线诊断与比较；不执行机械臂。 |
| **后续 CPU 工作** | 同时推进 F2/F3 下一阶段接口、采集器发布顺序修复、F1/F4 的真实 realization 采集实现和 Stage 1 清单。 |
| **Stage 1 / formal / 训练** | 本轮仍不启动；但不再把不必要的前置条件叠到 Stage 1 前面。 |

本次是**源码审阅、证据核对和执行规划**。35 项 CPU 测试的运行结果来自仓库中 Codex 封存的报告，不是我在你的服务器上重新执行了一遍；新候选能否抓取、F2 新路线能否通过，仍要由下面获准的真实运行回答。

---

# 一、现在到底完成了什么

## 1. F4 已经是验收数据，不再是“待修复数据”

正式接收记录已经确认：

- 61 个原始依赖重新校验；
- 原始数据没有修改；
- 29 项最终检查通过；
- 追加式收据更正后接收 **1 个 development root、3 条 `r_pc`**；
- 重复审计不会重复登记；
- 全项目 development 合计 **6 roots / 18 trajectories**。fileciteturn441file0L2-L2

因此，下一轮不要再讨论“是否允许采纳 F4”。只需要在读取已有 F4 数据时，正确使用它的 resolution/acceptance 索引。

## 2. F2 已经完成工程排障，现在暴露的是实际规划问题

最新 F2 已经通过：

```text
短路径环境
→ 正确 metadata 几何
→ candidate 2 坐标补偿
→ sealed qpos / EEF / actor 恢复
→ live target 校验
→ 实际 planner 调用
```

失败发生在第一段：

```text
beside_asset_bound_carry_hub
```

侧信道记录为：

```text
status = MotionGenStatus.IK_FAIL
valid_query = true
used_graph = false
external planner queries = 1
```

内部 `attempts=10` 是这一次求解内部的尝试，不能算成十次外部 query。fileciteturn442file0L2-L2

这次不能再归因于目录、收据、坐标或 GPU 驱动。**但也不能从一次 `IK_FAIL` 推断整个 beside 任务物理不可行。**

## 3. F3 本次要求的 post-lift 修订已经落实

我检查了实际调用链，确认不是只增加了一个没被调用的函数：

```text
执行 pregrasp
→ 审计整个 pregrasp 窗口
→ 执行 grasp
→ 审计整个 grasp 窗口
→ close 0.50
→ hold 250
→ 保存 lift execution receipt
→ 执行 25 mm micro-lift
→ 再记录 50 帧
→ audit_micro_lift_trace
```

新函数检查实际升高、连续接触、确认窗口离开支撑面、全窗口抓持变换以及禁止碰撞。对应的 12 项专项测试和 23 项保留回归均通过，且新的源文件与 post-lift contract 已纳入 manifest。fileciteturn422file0L2-L2 fileciteturn423file0L2-L2 fileciteturn437file0L2-L2

**我的判断：这轮应该让 F3 跑，不再追加一轮泛化的 CPU 加固。**

---

# 二、先纠正一处之前计划里的过度前置条件

这点直接关系到效率。

**我之前把“每个 root 必须先做到 9/9”混入了 Stage 1 前置要求，这不符合仓库主方案的分阶段定义。这里明确纠正。**

主方案规定：

### Stage 1：48 条 mechanism pilot

每个 family：

```text
Pilot root A：
3 intents ×（r_pc + r_inv_path）= 6 条

Pilot root B：
3 intents ×（r_pc + r_inv_motion）= 6 条

每 family 12 条
四个 family 合计 48 条
```

### 正式数据：每个 root 才要求 9/9

```text
3 intents ×（r_pc + r_inv_path + r_inv_motion）
= 9 条 / formal root
```

主方案 D17.2 和 D12.4 对这两者有明确区分。fileciteturn436file0L2-L2 fileciteturn435file0L2-L2

因此：

> **要提前实现和测试 9/9 finalizer，但不应为了启动 48 条 pilot，先强迫每个 pilot root 都采满 9 条。**

已有 18 条 development 数据也不能自动计入 Stage 1。需要建立一份明确的 eligibility/mapping 清单，判断哪些可作为 pilot 证据、哪些仅保留为开发结果；Stage 0 历史仍然封存，不重写、不重跑。

---

# 三、F3：批准现有微门，先获得真实结果

## 步骤 1：冻结当前 V1.1，不再改 executor、Gate 或 Guard

本次批准绑定：

```text
PROPOSED_F3_POST_LIFT_MICRO_MANIFEST_V1_1_20260905.json

proposal manifest SHA:
37d9a4ea7009c04ff73fb6f8f7b470e082ec8f0833bb7afc2d5ffb409f494f8a

CPU review receipt:
e764485818de8cfe48010dd860e070bec02f5e3cf2f630529becbdbadbd2cb72

candidate freeze:
67d608c88860c3b5f9843e0ba5c3d23e0c8f2389c25b014ec94971b47fe304c6
```

以上值与当前 proposal、CPU review 一致。fileciteturn425file0L2-L2 fileciteturn437file0L2-L2

四个候选顺序保持：

```text
r3063 → r0861 → r1401 → r2526
```

不换 candidate，不换 seed，不改 20 mm、50 帧、5 mm、0.05 rad 等诊断阈值。

## 步骤 2：签发新的执行 manifest，沿用现有审批接口

正式决定使用代码已支持的枚举：

```text
F3_PRECLOSE_CANDIDATE_MICRO_EXECUTION_V1
```

不是再设计新的审批协议。

生成结构化 decision receipt 时，把后文决定里的 `candidate_freeze_sha256`、`caps`、`source_files` 原样写入，并绑定本条回复的实际归档文件。当前 validator 已经检查这些字段与 manifest 一致。fileciteturn431file0L2-L2

执行前完成：

```text
执行版 manifest 校验
→ 原有 CPU preflight
→ 源文件/资产/目录检查
→ commit + push
→ 两次完整 GPU 快照
→ 选择一张实际空闲卡
→ Guard 启动
```

**读取全卡状态，不等于要求八张卡全部空闲。**只要求选中的卡满足规则，不干预其他用户任务。最新 F2 运行时其他卡已有任务，所选 GPU2 仍然完成了独立清理。fileciteturn442file0L2-L2

## 步骤 3：执行一次，预算保持不变

```yaml
qualification_query_cap: 40
physical_query_cap: 12
planner_query_cap: 52

planner_scene_cap: 8
physical_scene_cap: 4
scene_cap: 12
physical_attempt_cap: 4

stop_after_qualified_micro_passes: 2
```

这只是**抓持与 25 mm 抬升微门**：

```text
shared-V = 0
no-suffix = 0
accepted root = 0
training raw = 0
formal = 0
```

允许保留诊断 trace；它不是验收训练轨迹。

另外，当前 full-window Gate 是**每段执行完成后审查整段，再决定是否允许下一段/闭爪**，不是已经实现逐物理步实时急停。报告里不要把这两种能力混写。实际源码是在 `_execute_planned_segment()` 返回后调用 `online_window()`。fileciteturn423file0L2-L2

## 步骤 4：结果出来后，自动进入对应 CPU 分支

| F3 结果 | 接下来做什么 |
|---|---|
| **至少两个 micro pass** | 按冻结顺序选第一个成功 candidate；立即构建 candidate-bound prefix、shared-V/no-suffix 和 full-root 的 CPU 实现与提案 |
| **只有一个 micro pass** | 保留为单例物理正证据，不临时降低“两例确认”规则；输出成功与失败候选的阶段差异 |
| **0 个 micro pass，主要还是 pre-close 碰撞** | 停止翻候选；进入 planner/SAPIEN 碰撞模型一致性排查 |
| **0 个 micro pass，但已成功抓住，主要在 lift 窗口失败** | 聚焦抓持滑移、实际升高、抬升跟踪与确认窗口，不重写 pre-close Gate |
| **运行、计数、cleanup 失败** | 停止该作业，保留证据；不能把它当成候选物理失败 |

**当前这份批准不允许自动执行 shared-V，但允许立即把下一阶段 CPU 工作做完，而不是只回一句“等待下一步”。**

## 步骤 5：成功时，把后续三段接起来实现

新 candidate-bound prefix 应复用这次通过的抓持入口和 Gate，不重新调用旧的“执行两段后立即闭爪”函数。

后续结构：

```text
已通过的抓取/微抬升
        ↓
到达后续程序需要的实际持物高度与中心
        ↓
真实 shared first V
        ↓
回到共同中心并稳定
        ↓
冻结 canonical prefix
        ↓
fresh scene 精确重放
```

这里有一个重要边界：

> **25 mm micro-lift 成功，不代表旧 Stage-A 较长抬升或 shared-V 已成功。**

因此，后续 prefix 的高度、中心与动作参数必须来自选定 recipe 和既有程序合同，明确记录与微门的差别，不能直接用微门的成功盖章替代。

接着实现：

```text
1 reference prefix + 2 exact replays
= 3-scene no-suffix qualification
```

通过后的 full root 才是：

```text
VVHH
VHVH
VHHV
```

这些后续作业的 planner/scene 预算，**从最终实际调用链生成**，不要现在凭记忆写死。完成 CPU 实现、实际 dispatch 预检和精确预算后，统一提交一个后续执行包。

## 步骤 6：失败时，不再通过任意变换 recipe 来“碰运气”

旧失败证据支持的是：CuRobo 的规划结果没有排除 SAPIEN 执行中的自碰、桌面/垫子碰撞；新 Gate 负责发现并阻断，并没有修复 planner 模型。fileciteturn440file1L24-L32

若这轮仍集中失败，CPU 排查按固定顺序进行：

```text
joint-name / qpos 排列
→ robot base 与 world frame
→ EEF frame 与工具偏移
→ collision spheres/meshes 覆盖
→ self-collision ignore pairs
→ table/pad 的位姿与尺寸
→ 对侧机械臂是否进入规划世界
→ commanded 与 realized qpos 从何时开始偏离
```

用**已经失败的同一组 qpos、目标和接触证据**做对照，不换四个新物体后重新开始同一套故事。

CPU 几何比较只能给出模型不一致证据；真正的修复验证若需要新 planner/SAPIEN 执行，另列精确预算，不混入本轮 52 queries。

---

# 四、F2：采用一个最多 19-query 的有限诊断，不继续死守原 carry-hub

## 步骤 7：把已解决的问题正式移出待办

以下内容不再重做：

```text
TMPDIR
metadata 几何来源
candidate 2 的 actor-origin 补偿
table plane
原 inside 5/5
异常计数与 cleanup 记录
```

最新执行器确实完成 live target 恢复后才调用 `_plan_chain()`，最新终端也保留了目标、起止 qpos 和 MotionGen 状态。fileciteturn439file0L2-L2 fileciteturn442file0L2-L2

## 步骤 8：先把失败含义解释清楚

原 hub 是人为构造的中转姿态，不是任务终点。

当前代码构造方式近似为：

```text
hub.xy = 当前 EEF 与 preplace EEF 的 XY 中点
hub.z  = 两者较高的 Z
hub.orientation = preplace.orientation
```

这同时施加了“向中间移动、维持高位、到达目标姿态”三个要求。代码并没有证明这个中转姿态本身好解。fileciteturn408file0L2-L2

cuRobo 的 `plan_single` 在笛卡尔目标下先做 IK，再进入轨迹优化；所以本次 `IK_FAIL` 与后续“绕障路径搜索失败”不是一个阶段。不能只增加图搜索次数就认为能解决，更不能把 `used_graph=false` 单独当作配置故障。citeturn512288search2

**下一步应区分：终点是否能解，还是只有人为 hub 不好解。**

## 步骤 9：冻结诊断输入，只允许改变中转策略

定义以下符号，全部从当前封存输入读取，不手抄浮点值：

```text
C：sealed_prefix_end_eef_pose
U：已修正 beside 的 preplace pose
D：已修正 beside 的 release pose
N：冻结 neutral pose
H：本次失败的 carry-hub pose
```

固定不变：

```text
candidate index 2
目标 geometry-centre XY
最终 actor pose / release pose
metadata 来源
执行臂
抓持变换
原始起点 qpos
planner backend/config
现有碰撞检查设置
```

**本次新增允许改变的是 transit waypoint 结构，不是 beside 的任务定义或最终目标。**

## 步骤 10：先运行三个独立诊断，各最多 1 query

在第一个 planner-only scene 中，从相同 sealed qpos 分别检查：

| 编号 | 目标 | 用途 |
|---|---|---|
| D0 | `C` | 同一当前姿态的正对照，检查基本 frame/状态/接口 |
| D1 | `U` | 不经过旧 hub，检查 preplace |
| D2 | `D` | 不经过旧 hub，检查 release 终点 |

每次都恢复并核对同一 qpos、EEF、actor 状态，使用固定 reset 规则。

D0 失败时，停止后续路线比较，优先查接口、状态或当前配置有效性；**不能直接推断物理不可行。**

D1/D2 的失败仍只是当前配置下的诊断结果，不作为全局不存在 IK 解的证明。

## 步骤 11：比较三个预注册完整路线，第一条通过即停止

第二个 planner-only scene 中，按固定顺序测试：

| 顺序 | 路线 | 最多 queries |
|---|---|---:|
| **R0：直接路线** | `U → D → U → N` | 4 |
| **R1：降低 hub 高度** | `H_low → U → D → U → H_low → N` | 6 |
| **R2：hub 保持当前姿态** | `H_current_orientation → U → D → U → H_current_orientation → N` | 6 |

精确定义：

```text
H_low：
XY 和 quaternion 与 H 相同；
Z = U.z。

H_current_orientation：
XYZ 与 H 相同；
quaternion = C.quaternion。
```

R1 只是让 hub 从当前约 `1.04986 m` 降到 preplace 约 `1.00951 m`，减少约 **40.34 mm** 的高度要求；这个数值应由冻结输入计算，不作为手写新常数。

R2 则将“高位中转”与“到达目标姿态”分开。**这两条是待验证的路线假设，不是已证明安全或可行的路线。**

总预算：

```text
3 个独立诊断
+ R0 最多 4
+ R1 最多 6
+ R2 最多 6
= 最多 19 queries
```

每条路线首个失败段后即停止该路线；第一条完整成功后，不再试后面的路线。不进行在线加点、随机扫高度或换 seed。

## 步骤 12：特别处理现有 `_plan_chain` 的累计计数语义

这是新实现最容易再次踩坑的地方。

当前 `_plan_chain()`：

- 每次从实际 scene qpos 读取起点；
- 返回的 `planner_query_count` 是**场景累计值**；
- `query_limit` 会写入场景级 limit；
- 路线内部才把上一段 terminal qpos 传到下一段。fileciteturn430file0L2-L2

因此新诊断必须：

```python
before = scene.planner_query_count

# limit 是场景累计上限，不是本小段独立预算。
absolute_limit = before + len(targets)

planned = _plan_chain(
    scene,
    targets,
    query_limit=absolute_limit,
    arm="left",
)

delta = scene.planner_query_count - before
```

再由外层 ledger 检查：

```text
每个诊断 delta ≤ 1
R0 delta ≤ 4
R1/R2 delta ≤ 6
全部场景累计 delta ≤ 19
```

**不能把每次返回的累计 count 相加，也不能为了方便把总计数清零。**

不同路线起步前要恢复 sealed qpos；一条路线内部则保留真正的链式 qpos。规划产生的 controls 只保存，不执行。

## 步骤 13：本轮给 F2 条件执行许可，不要求实现完再往返一次审批

正式决定：

```text
APPROVE_BOUNDED_F2_BESIDE_TRANSIT_DIAGNOSTIC_V1
```

执行前必须完成：

```text
冻结 C/U/D/N/H 与 R0/R1/R2 targets
→ 固定 route order 和 target hashes
→ 验证 D/U/最终 actor 目标未变
→ 验证 before/after 累计计数
→ 验证每路线起点恢复
→ 验证没有物理执行入口
→ 原有 Guard/runner 生命周期预检
→ 新 manifest、新输出目录、commit/push
```

这是对上一条已消费 beside-only 作业之外的**新有限诊断许可**。不允许重发旧作业，不允许重跑 inside，也不允许把它包装成同一个未消费授权。

执行范围：

```yaml
planner_queries_cap: 19
fresh_planner_scenes_cap: 2
physical_executions: 0
branch_executions: 0
accepted_raw_trajectories: 0
accepted_roots: 0
formal_trajectories: 0
```

不需要为此再新造一整套审批框架。复用已经跑通过的短路径、Guard、清理和终端模式，只新增诊断/路线编排逻辑。

## 步骤 14：诊断后继续推进 CPU 实现，不停在一份结果摘要上

### 有完整路线通过

立即冻结首个成功路线，并构建 F2 controlled-insertion root 的 CPU 实现。

这里要更新以前的预算说法：

```text
prefix 3
+ inside 5
+ on 4
+ beside B
= 12 + B
```

所以，**若最终代码仍采用这些调用数**：

```text
R0：B=4，完整 root planner 预计 16
R1/R2：B=6，完整 root planner 预计 18
```

最终以实际 collector 调用链和计数测试为准，不能无论选择哪条路线都继续写 18。

同时注意：旧的“inside 5 + beside 6 = 11/11”统计只适用于原六段 beside。若采用 R0，应发布新的**路线版本资格记录**，不能凑成旧 11/11。

新 root 中：

```text
inside 必须使用 post-prefix controlled insertion
不重复 pregrasp / grasp / lift
不回退 gravity drop
执行阶段只消费 frozen controls
```

inside 5/5 目前仍只是规划结果，所以完整 root 必须真实验证支撑、慢释放、settle 和 strict-inside。不能因为规划通过就跳过物理验收。

### 三条路线都失败

自动生成一份小型故障矩阵：

```text
D0 / D1 / D2
R0 / R1 / R2 首失败段
目标 pose
起始 qpos
MotionGen status
内部 attempts
query delta
cleanup
```

之后不临时增加 R3/R4。

再根据矩阵决定下一方案：

- 主要是 hub 失败：研究中转姿态；
- 目标 U/D 一直失败：研究固定放置姿态、抓持变换和工作空间；
- 所有路径进入 TRAJOPT/碰撞阶段才失败：研究路径与碰撞模型；
- 正对照失败：先查系统配置，不改任务。

这一轮结果不足以直接宣布放弃 F2，也不构成无限重试的理由。

---

# 五、F1/F4 不要闲着：现在就推进后续 CPU 实现

## 步骤 15：修复未来 collector 的最终发布顺序

已有 F4 不动。新 collector 在隔离开发目录修复：

```text
branch provisional receipts
→ 三条分支完成
→ 计算 divergence
→ finalized branch receipts
→ root receipt
→ acceptance index
```

将“写出分支后又原地修改”改成明确的 provisional/final 两阶段。

至少使用真实 publisher/finalizer 接口跑这些 CPU 场景：

```text
suffix 立即分歧
suffix 额外共享若干步后分歧
分支尚未完成
finalization 中断
重复登记
磁盘 final branch 与 root 不一致
```

不能只手造一份必然通过的最终 receipt，然后宣称采集器已修复。

**这一项的价值是让后续 F2/F3/F1/F4 都不再重复 F4 的收据不同步问题。**但在当前 F3 和 F2 作业执行前，不要修改它们绑定的 active source。

## 步骤 16：把 F1/F4 realization 设计落成实现，而不只写文档

仓库已有 F1 realization 设计，明确要求 `r_inv_path`、`r_inv_motion` 必须是**新的真实 rollout**；复制动作数组、重采样视图不能充数。fileciteturn432file0L2-L2

现在可以实现：

```text
realization spec builder
candidate/program 绑定
variation executor 接口
pairing receipt
same-intent verifier
raw/video writer 对接
pilot/formal 分级 finalizer
```

CPU proposal 中分别给出：

- **路径变化**：只改变非关键运输路径，目标、对象、执行臂、操作顺序不变；
- **运动变化**：只改变预注册的速度/持续时间安排，操作顺序与意图不变；
- 变化值、允许修改的字段、禁止修改的字段；
- 失败记录与有限预算；
- 对不同 program 使用同一种变体规则，避免变体参数泄漏标签。

F4 的路径变体不能偷偷把 `ABC` 改成 `ACB`；运动变体不能通过不同 pause 模式直接编码程序类别。

这些实现可以继续推进到 CPU 预检、精确预算和待审 manifest，**本轮不批准新增 realization 的 GPU 采集**。

## 步骤 17：实现正确的 pilot/formal 分级验收

不要只做一个“任何 root 都必须 9/9”的 finalizer。

应明确：

```text
development r_pc root：
3 intents × r_pc = 3

Stage 1 pilot root A：
3 intents ×（r_pc + r_inv_path）= 6

Stage 1 pilot root B：
3 intents ×（r_pc + r_inv_motion）= 6

formal root：
3 intents × 3 realizations = 9
```

同一条轨迹通过哪个阶段的验收，必须记录对应 protocol/version，不能靠目录改名完成 promotion。

同时实现负例：

```text
用同一 raw ID 填两个格子
用 resampled view 充当新 realization
root A 错放 motion variant
root B 缺 r_pc
program/intent 对不上
不同 root 的轨迹混入同一矩阵
```

## 步骤 18：建立 Stage 1 的 48 条显式清单

生成：

```text
4 families
× 2 pilot roots
× 3 intents
× 每 root 的 2 个 realization
= 48 cells
```

每个 cell 列出：

```text
family
pilot root A/B
intent
realization
是否已有符合条件的原始数据
来源与验收 receipt
是否需要新采集
当前缺失原因
是否已获阶段授权
```

已有 development 轨迹只能标记为 `candidate_for_pilot_reuse` 或类似待审状态，不自动扣减 `0/48`。

之前查看过、用于调试的 roots 不应再伪装成未见过的 validation/test。主方案也明确限制 pilot promotion 的用途。fileciteturn436file0L2-L2

## 步骤 19：提前准备 Stage 2，但不要伪造冻结结果

可以做 CPU 清单与接口：

```text
formal 40 primary slots
16 ordered reserve slots
每 family 的 5/2/3 split
difficulty 配额
attempt budget schema
train-only normalization procedure
root/super-root 隔离检查
```

但尚未完成 feasibility/current/candidate freeze 的 slot 必须保持 pending。不能为了让 manifest “完整”，填入不存在的 current、candidate 或物理成功 hash。主方案对两层 spec 和 inactive reserve 有明确要求。fileciteturn436file0L2-L2

这一步只准备协议，不启动 formal 360。

---

# 六、提高效率：这轮应改变工作方式，而不是继续增加层数

## 步骤 20：只保留三条工作线和一个汇总入口

建议 Codex 这轮这样组织：

### 工作线 A：F3 微门

```text
签发批准 → preflight → 执行一次 → 终端/清理
→ 自动生成下一阶段 CPU 产物
```

### 工作线 B：F2 有限路线诊断

```text
冻结 3 个诊断与 3 条路线 → CPU 测试
→ 执行一次 bounded panel → 终端/清理
→ 成功则实现 root proposal；失败则生成模型/目标差异矩阵
```

### 工作线 C：公共 CPU 后续

```text
collector publication-order 修复
→ F1/F4 realization 实现
→ pilot/formal 分级 finalizer
→ 48-cell Stage 1 清单
```

**GPU 串行，CPU 可在互不修改绑定源文件的隔离目录推进。**

不再要求每写完一个 helper 就停下来外审。只有以下边界需要新的决定：

```text
扩大候选或 planner/scene 预算
改变终点、物体、执行臂或科学定义
放宽物理/verifier 阈值
从微门进入 shared-V/no-suffix/full root
启动新的 realization、Stage 1 或 formal
```

最后只提交一个汇总交接文档，指向真实 machine receipts。不要在每个阶段复制整段历史，也不要把巨大 raw/trace JSON 一遍遍塞进上下文。**源代码差异、首失败证据、当前决定和下一执行入口应足够让下个会话继续。**

---

# 七、本轮正式执行决定

下面这份决定供 Codex落库。F3 的 `source_files` 与当前 proposal 完全一致；F2 是对上述精确有限方案的条件许可。

```yaml
review_base:
  vault_head: 8f24ad4371858edea531822dde61eecad1d11165
  review_scope:
    - F3 post-lift narrow review and one micro execution
    - F2 bounded beside transit diagnosis
    - downstream CPU implementation
  stage0_rerun: false
  stage1_authorized: false
  formal_360_authorized: false
  training_authorized: false
  h_reveal_authorized: false
  compression_authorized: false
  pi05_authorized: false

F4:
  decision: ACKNOWLEDGE_ALREADY_ADOPTED_DO_NOT_REAPPROVE
  accepted_development_roots: 1
  accepted_development_trajectories: 3
  acceptance_receipt_sha256: 5416dc9e94cf8c534eb91e7b35fd9e9661c1f7bc142f96d6fcc6bf3f1b817723
  new_gpu_execution_authorized: false
  repeated_registration_allowed: false
  original_artifact_modification_allowed: false

F3:
  decision: F3_PRECLOSE_CANDIDATE_MICRO_EXECUTION_V1
  authorized: true
  maximum_job_executions: 1

  reviewed_proposal_manifest_sha256: 37d9a4ea7009c04ff73fb6f8f7b470e082ec8f0833bb7afc2d5ffb409f494f8a
  cpu_review_receipt_sha256: e764485818de8cfe48010dd860e070bec02f5e3cf2f630529becbdbadbd2cb72
  candidate_freeze_sha256: 67d608c88860c3b5f9843e0ba5c3d23e0c8f2389c25b014ec94971b47fe304c6

  ordered_candidates:
    - f3-final-pose-v3-r3063
    - f3-final-pose-v3-r0861
    - f3-final-pose-v3-r1401
    - f3-final-pose-v3-r2526

  caps:
    candidate_cap: 4
    formal: 0
    no_suffix: 0
    physical_attempt_cap: 4
    physical_query_cap: 12
    physical_scene_cap: 4
    planner_query_cap: 52
    planner_scene_cap: 8
    qualification_query_cap: 40
    raw: 0
    root: 0
    scene_cap: 12
    shared_v: 0

  post_lift_contract:
    maximum_relative_orientation_drift_rad: 0.05
    maximum_relative_translation_drift_m: 0.005
    minimum_actual_bottle_rise_m: 0.020
    post_lift_confirmation_frames: 50

  source_files:
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/f3_preclose_candidate_micro_runtime_v1_1/candidate_executor.py": "40df6332a8fc796417b315ba7d8a385017e9a8af74f0a2d5cccb7922d62333b2"
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/f3_preclose_candidate_micro_runtime_v1_1/guarded_launcher.py": "e0cbadab4814e7705c66bdadc1ffa53a5fd790ffaa5960823151a48a708c0572"
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/f3_preclose_candidate_micro_runtime_v1_1/job_runner.py": "fa1ad7649d387d31a07f55981834422d08e10da57b8b94f065768925472d1238"
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/f3_preclose_candidate_micro_runtime_v1_1/manifest_contract.py": "0b12aa59d51342865fb033f127693b583a4024dbc43647e476c61b328313aefb"
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/f3_preclose_candidate_micro_runtime_v1_1/post_lift_audit.py": "096509b41491ddf0d6a97b144e2801e8e6279f2b29b1ba18ddfeac364ca09e7c"
    "/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/f3_preclose_physical_consistency_gate_v1_1/gate.py": "ca9a7bcf4c2e03d74716d67342457fe19b82c0fe1f089cd8f16591580b1973ad"

  stop_after_qualified_micro_passes: 2
  candidate_substitution_allowed: false
  seed_retry_allowed: false
  threshold_change_allowed: false
  automatic_job_retry: false
  automatic_shared_v_execution: false
  automatic_root_execution: false
  second_review_before_this_micro: false

  after_result_cpu_work_authorized:
    - classify failures by earliest stage
    - freeze first successful candidate in registered order if gate passes
    - implement candidate-bound prefix and no-suffix proposal
    - implement full-root interfaces and derive actual budgets
    - prepare collision-model discrepancy report if gate fails

F2:
  decision: APPROVE_BOUNDED_F2_BESIDE_TRANSIT_DIAGNOSTIC_V1
  authorized: true
  approval_type: CONDITIONAL_AFTER_EXACT_CPU_IMPLEMENTATION
  maximum_job_executions: 1

  preserve:
    - Run3 inside 5-of-5 evidence
    - selected assets and left execution arm
    - sealed prefix-end qpos and grasp transform
    - metadata geometry source
    - candidate-index-2 final actor pose
    - corrected preplace and release targets
    - neutral target
    - planner backend and collision configuration

  pose_definitions:
    C: sealed_prefix_end_eef_pose
    U: corrected_beside_preplace_pose
    D: corrected_beside_release_pose
    N: frozen_neutral_pose
    H: previously_failed_carry_hub_pose
    H_low: H_with_z_equal_to_U_z
    H_current_orientation: H_with_quaternion_equal_to_C_quaternion

  diagnostic_order:
    - D0_current_pose_positive_control
    - D1_direct_preplace
    - D2_direct_release
  diagnostic_query_cap: 3

  route_order:
    - R0
    - R1
    - R2

  routes:
    R0:
      targets: [U, D, U, N]
      query_cap: 4
    R1:
      targets: [H_low, U, D, U, H_low, N]
      query_cap: 6
    R2:
      targets: [H_current_orientation, U, D, U, H_current_orientation, N]
      query_cap: 6

  aggregate_caps:
    planner_queries: 19
    fresh_planner_scenes: 2
    physical_executions: 0
    branch_executions: 0
    accepted_raw_trajectories: 0
    accepted_roots: 0
    formal_trajectories: 0

  rules:
    - stop route comparison if D0 fails
    - restore and verify the sealed start state before each independent test
    - retain chained qpos within each route
    - measure query deltas with before-and-after live counters
    - treat scene query_limit as an absolute cumulative limit
    - stop each route at its first failed segment
    - stop the panel at the first complete route pass
    - freeze all target hashes before GPU execution
    - no physical control execution
    - no new route beyond R0/R1/R2
    - no seed search or hidden planner retry configuration changes

  prerequisites:
    - exact route and target CPU tests
    - cumulative-counter and state-reset regression
    - no-physical-dispatch regression
    - existing Guard lifecycle preflight
    - fresh versioned manifest and output namespace
    - commit and push before execution
    - live GPU admission and complete cleanup

  inside_rerun: false
  old_job_reissue: false
  automatic_job_retry: false
  automatic_root_execution: false
  second_review_after_exact_implementation: false

  after_result_cpu_work_authorized:
    - publish endpoint-and-route failure matrix
    - freeze first complete route pass
    - implement post-prefix controlled-insertion root proposal
    - derive root budget from selected route and actual source calls

downstream_cpu:
  authorized: true
  tasks:
    - collector late-finalization publication-order fix in isolated checkout
    - real publisher-to-finalizer CPU integration tests
    - F1 and F4 realization spec/executor/pairing implementation
    - separate development, pilot-A, pilot-B and formal acceptance matrices
    - 48-cell Stage1 eligibility and acquisition manifest
    - pending Stage2 slot and protocol schemas

  active_source_changes_before_current_jobs_finish: false
  new_realization_gpu_collection_authorized: false
  future_root_gpu_execution_authorized: false

protocol_clarification:
  development_rpc_root_trajectory_count: 3
  stage1_pilot_A_trajectory_count: 6
  stage1_pilot_B_trajectory_count: 6
  stage1_total_trajectory_count: 48
  formal_root_trajectory_count: 9
  require_formal_9_of_9_before_stage1: false
  automatic_promotion_of_existing_development_data: false

scheduling:
  gpu_jobs_serial: true
  preferred_first_job: F3_micro
  next_job: F2_bounded_transit_diagnostic
  scientific_failure_with_clean_cleanup_blocks_other_family: false
  stop_global_queue_on:
    - unknown resource accounting
    - cleanup failure
    - task-owned orphan process
    - selected GPU identity mismatch
    - selected GPU baseline not restored
    - evidence integrity failure
```

**这轮应该争取完成的，不只是再多几份“CPU 通过”报告，而是：F3 得到新候选的真实微门结果，F2 得到终点与三条有限路线的明确结论，同时把后续采集器、realization 和 48 条 pilot 清单真正实现起来。F4 已经完成，不再让它回到修复循环里。**

---

If you want, I can:

- 继续详细说明F3阶段后续步骤
- 展开F2有限路线诊断方法
- 说明F4数据验收后的应用示例
