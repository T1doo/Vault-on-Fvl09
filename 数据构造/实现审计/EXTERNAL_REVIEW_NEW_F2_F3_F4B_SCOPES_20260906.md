# 来源

https://chatgpt.com/s/t_6a9d282120f881918863d7bf69035323

完整提取正文；原文中的filecite为分享对话自身引用，未当作本地独立校验。

# 这轮的判断：应该批准验证新方案，不再继续修旧目标

我以 **`9ed6a353b59c39d050a6a5b0cbfdaf4c9cdff2ad`** 为基线，检查了交接文档、F2 诊断与布局生成代码、F3 新抓取姿态生成器、实际几何与模型重放代码、坐标转换兼容层，以及 F4-B 的布局和预算提案。

**这次已经具备改变实现方案的依据：**

- **F2：接受“reference 与 beside 目标一起向内移动 10 cm”的单一布局，进入有限规划验证。**
- **F3：接受“从上方接近、横向夹持”的设计方向，但先补闭合几何和坐标映射，再验证 IK 与真实抓取。**
- **F4-B：允许同步完成执行接线，并在严格前置条件满足后采集一个新根的六条开发轨迹。**
- **已成功的 F1/F4 数据保持不动，不再重复审批、重跑或重复登记。**

最重要的变化是：

> **现在不是继续给原来的失败动作加补丁，而是保留研究任务的语义，换掉已经证实不合适的场景位置和抓取姿态。**

以下是可直接转给 Codex 的计划。本次没有在你的服务器上重跑求解器；判断来自实际源码和封存证据，后面的条件验证不能省略。

---

# 一、先把当前结论固定下来

| 部分 | 已经证明的事情 | 仍未证明的事情 |
|---|---|---|
| **F2 旧目标** | 当前姿态能解；原 U/D 与有限 yaw 在固定求解预算下没有合格解 | 不能把数值求解失败写成数学不可达 |
| **F2 新布局** | reference 与目标一起移动，相对 beside 关系保留；与已检查的 box/scale/wall 无网格交叠 | 桌面完整支撑、全臂可达性、路径及三分支物理成功 |
| **F3 旧抓取** | 原终点存在手掌/手指与 table/pad 的实际几何交叠 | 不值得继续执行原终点 |
| **F3 新抓取** | 新开爪姿态没有已检查到的确定穿插 | 手指能否闭合夹住、IK、全臂路径和物理抓持 |
| **F1/F4** | 开发数据仍为 **6 roots / 27 raw**；18 个 pilot 候选格复核通过 | 完整 48 条 pilot 和正式 360 尚未完成 |

这些边界与本轮交接、诊断结果一致。尤其是 F2，报告没有把“有限预算内未找到解”夸大成任务不可能；F3 则已经有足够几何证据否决旧抓取终点。fileciteturn461file0L2-L2 fileciteturn463file0L2-L2

**旧 15 个 IK 问题、旧 yaw、旧 hub、旧两个抓取终点，到此停止。**剩余旧预算不能自动转用于新布局或新 recipe。

---

# 二、F2：接受单一内移布局，但先验证新端点，不直接采完整 root

## 1. 为什么这次布局修改是合理的？

新提案将 stand 和 beside 目标一起移动：

```text
平移向量：
[-0.09966188119296109, -0.008216412664910758] m

平移长度：
0.10 m

目标 geometry-centre XY：
[0.08, 0.07]
→
[-0.01966188119296107, 0.06178358733508925]
```

同时保留罐子的目标朝向、抓持关系和相对 beside 几何。这个方案是根据已有可达持物位置推导的，而不是再任意增加中转点。fileciteturn463file0L2-L2

但需要保留报告中的限定：

> **10 cm 是一个有依据的设计选择，不是从 4 cm IK 残差推导出来的可达性定理。**

我接受它作为**唯一待验证布局**。不允许在同一次作业里失败后继续改成 12 cm、15 cm 或换方向。

## 2. 执行前，补齐现有 CPU 几何检查漏掉的项目

我检查了 `endpoint_proposal_geometry_followup_v1.py`。它目前主要比较移动后的 stand、目标罐子与 box/scale/wall，并记录高度范围；**没有完整认证桌面 footprint，也没有检查所有 moving 对象之间的配对。**源码和输出对此已有明确说明。fileciteturn468file0L2-L2

因此只补下面这些针对性检查，不再重做整个几何系统：

### A. 桌面支撑

验证移动后的 stand 和最终罐子：

- footprint 位于真实桌面有效区域内；
- 底面高度与支撑面一致；
- 不悬空、不越界；
- 使用实际 collision geometry，而不是只看 actor origin。

### B. 移动物体之间，以及初始状态

补查：

```text
移动后的 stand ↔ 最终罐子
移动后的 stand ↔ 初始罐子
移动后的 stand ↔ 机器人初始/诊断持物状态
```

不需要把所有动态路径在 CPU 上证明一遍，但不能漏掉明显的起点或终点交叠。

### C. 三关系语义

验证新目标仍满足：

```text
beside = true
inside = false
on = false
```

reference 和目标同步移动，不能只改变执行目标，却让 verifier 继续读旧 reference。

凡是在新 binding 中保留的 beside 候选坐标，也要明确同步或标记未使用，不能留下互相矛盾的旧坐标。

### D. 新根身份

新布局必须使用：

```text
新 planned root / layout version
新 current / anchor / candidate lineage
```

**不能沿用旧 current hash。**

原 inside 5/5 继续保留为历史证据，但不能因为 box 没移动，就直接宣布它在新场景中也完成资格验证。stand 的移动可能影响其他动作的碰撞与可见性。

## 3. 下一次只做一个新布局的端点与路线作业

本轮给予以下**条件式执行许可**：上述 CPU 检查和实际入口预检通过后，不必再为这一个规划作业回来申请。

### 第一阶段：三个完整约束 IK 问题

在一个新布局的 planner-only scene 中检查：

```text
C：诊断用持物起点
U_new：新目标上方
D_new：新放置终点
```

全部使用审计后的完整模型，不再重复 K0/K1/K2 九宫格，也不再测试其他 yaw。

沿用已经验证的：

```text
32 个固定 seed
100 次迭代
原目标转换链
原位置与旋转判据
实际夹爪状态
实际环境与手持罐子模型
```

这里仍要区分旋转指标：IK 的 `sin(angle/2)` 判据不能被改写成同数值的弧度阈值。当前诊断代码已经分开报告这两个量，应继续保留。fileciteturn472file0L2-L2

### 第二阶段：端点通过后，规划一条路线

仅当 C、U_new、D_new 都通过，才继续：

```text
U_new → D_new → U_new → N
```

最多四次轨迹规划。

这里还要明确放置前后模型状态：

- 到 D_new 前，罐子是随夹爪运动的物体；
- 到达支撑位置时，允许的是正确的罐子—桌面支撑，不是手指—桌面碰撞；
- 放置后的回撤，要按“罐子已留在目标处”的状态检查。

**不能把罐子一路附着到 neutral，也不能为了使 D_new 通过而整体关闭桌面碰撞。**

### 本作业上限

```text
3 个 IK 问题
4 次轨迹规划
1 个 fresh planner-only scene
0 次机械臂执行
0 条训练 raw
0 个 accepted root
```

规划用的持物状态重建只证明“从这个状态出发可规划”，**不证明新场景中已经真实完成抓取前缀**。

## 4. 结果之后，Codex 应继续推进到什么程度？

### 新端点和路线通过

立即完成 F2 新 root 的 CPU 接线：

```text
新场景
→ 新 current/anchor
→ 真实公共抓取前缀
→ inside / on / beside 三分支
→ frozen controls
→ 真实执行与独立 verifier
→ 两阶段收据发布
```

仍使用 controlled insertion，不回到 gravity drop。

完整 root 的预算从新执行链推导，**不能机械继承旧 16 或 18 queries**。模型更新、真实前缀、新场景资格与附着状态切换需要多少调用，都要进入账本。

本轮允许把实现、预检、精确预算和下一份 root 执行包做完；**完整物理 root 另按该执行包批准**。

### 新端点仍未解出

停止这个布局，不再现场平移第二次。

下一份提案应回答“是末端方向/抓持偏移，还是位置工作区仍不合适”，而不是再次提交一个随意位移。也不必因此放弃 F2 的关系意图任务。

---

# 三、F3：新抓取方向值得保留，但还需要三个实质检查

我检查了 `f3_geometry_topdown_proposal_v1.py`。它当前做的是：

```text
取原开爪手部几何
→ 改成从 -Z 接近、沿 X 闭合
→ 保留瓶体纵向抓取站点
→ 向上平移到距 pad 至少 8 mm
→ 检查开爪网格没有确定穿插
```

它**没有**执行闭合过程检查，没有 IK，也没有完整机械臂路径检查。代码对此没有冒充成功。fileciteturn467file0L2-L2

所以我的决定是：**接受这两个新 recipe 的方向，允许完成必要检查后进入有限 IK/物理微门；不允许直接把“开爪没穿模”视为抓取已合格。**

## 1. 第一项：闭合时，手指到底能不能碰到瓶体？

目前为避开支撑面，两个姿态分别额外抬高约：

```text
17.31 mm
10.89 mm
```

抬高能解决穿垫子，但可能把夹持区域抬得过高。必须检查：

> 手指闭合扫过的是瓶体两侧，还是从瓶子上面合拢，根本没有形成夹持？

先做 CPU 关节几何检查：

- 用实际“open → close 0.50”的关节映射，不假设归一化 command 等于关节位置；
- 固定少量闭合采样，记录两侧手指的实际包络；
- 检查两侧内表面是否能够与同一瓶体截面接触；
- 检查掌部、手指与 table/pad 是否发生禁止交叠；
- 接近阶段保持开爪，不能通过提前闭合避开垫子。

这只是**夹持几何必要条件**，不是力闭合或稳定抓持证明。离散采样也要明确标为离散检查，不宣称证明整个连续闭合过程。

如果闭合几何不成立，停止该 proposal，给出是哪一侧手指、哪个行程范围接触不到；不能直接扩大 close command 或改变瓶子高度。

## 2. 第二项：8 mm 无穿插，不代表不会产生仿真接触

提案里 finger–pad 的最小几何距离是 **8 mm**，相关 shape 的 `contact_offset` 合计约 **20 mm**。fileciteturn464file0L2-L2

PhysX 在两物体距离进入 contact offset 之和时就可能生成接触点；但“生成接触点”也不等于立即产生足以推开物体的强冲量。因此：

- 不能因为距离为正就宣称一定安全；
- 也不能仅因为 8 mm 小于 20 mm，就宣布一定失败。citeturn904116search0

正确处理是：

```text
CPU：记录真实 distance / contact offset / rest offset。
物理：继续用原 physical classifier、瓶位移和 tracking Gate。
```

**本轮不允许降低 contact offset、提高瓶位移阈值或放宽 Gate 来保住新姿态。**

也不建议不经抓取几何检查就把它继续抬高到 20 mm——抬得更高可能反而夹不到瓶体。

## 3. 第三项：新 proposal 是 actual flange pose，不能直接塞进旧 reported-goal 接口

这是最可能再次浪费一次 GPU 的接口问题。

你们的新提案明确标注：

```text
desired_actual_flange_world_pose
pose_is_NOT_legacy_reported_goal = true
```

当前转换代码又保留了完整的工具转换、base/frame bias 和 Aloha 经验旋转；环境几何则使用实际 configured base。两者不能混用。fileciteturn467file0L2-L2 fileciteturn470file0L2-L2

建议实现两个明确函数：

```python
actual_flange_goal_to_reported_command(...)
reported_command_to_actual_solver_goal(...)
```

验收时做真正的往返检查：

```text
期望 actual flange pose
→ 转成 reported command
→ 走锁定版本的完整原始目标转换
→ solver goal
→ 与期望 actual flange 在 solver base 下的位姿比较
```

不要用两个新函数互相验证、却不对照真实旧入口；也不要只比较 quaternion 分量而忽略 q 与 -q 的等价性。

执行后的 tracking 同样要在明确一致的坐标口径下比较：

```text
预先冻结的期望 actual pose
↔ 实际 link FK / 测得 pose
```

不能将测得终点反过来当成目标，造成假通过。

## 4. 保留这轮已经修好的模型，不再回退

下列修复应直接进入新运行配置：

- body 内唯一 collision-shape 名称；
- 真实 mesh、pose 与 planner cache 的核对；
- 实际开爪/闭爪 locked-joint 状态同步；
- 当前安装版本的局部兼容层；
- actual base 与 legacy goal 转换的分离。

`lock_compat.py` 已明确在所有相关 rollout 中同步命名关节位置，而不是只更新一份表面配置。这部分应复用，不改安装库、不再重写另一套。fileciteturn475file0L2-L2

---

# 四、F3 新方案的有限执行范围

上述三个检查完成、来源和目标冻结后，可以按本轮条件许可连续推进，不需要每完成一个 helper 就回来复审。

## 阶段 A：两个新 recipe 的 IK/全臂约束验证

每个 recipe 固定检查：

```text
当前姿态正对照
上方 pregrasp
新 grasp
```

共最多：

```text
6 个 IK 问题
2 个非动作场景
```

pregrasp 使用该新 grasp 上方的固定接近距离；可沿用父 recipe 的 **0.12 m**，但必须写入新 recipe，不能在 GPU 运行时临时改变。

检查的是**全臂与实际开爪状态**，不是只看三个手部 link 不穿模。对侧机械臂和场景障碍也要进入审计后的模型。

## 阶段 B：仅对阶段 A 通过的 recipe，真实执行一次微门

每个候选一个 fresh physical scene：

```text
规划并执行 pregrasp
→ 原 full-window Gate
→ 规划并执行 grasp
→ 原 full-window Gate
→ close 0.50
→ hold 250
→ 读取实际闭爪状态与抓持变换
→ 从实际状态规划向上 25 mm
→ 原 post-lift 验收
→ 停止
```

每个候选最多三次轨迹规划，两候选共最多六次。

保持：

```text
实际升高至少 20 mm
50 帧确认
相对平移漂移 ≤ 5 mm
相对旋转漂移 ≤ 0.05 rad
原接触连续性与禁止碰撞规则
```

本轮总上限：

```text
6 个 IK 问题
6 次轨迹规划
4 个 fresh scenes
2 个物理尝试
0 shared-V
0 no-suffix
0 accepted root
0 training raw
```

诊断 trace 可以保留，但不能记为训练轨迹。

## 结果分支

**两个都通过：**按冻结次序选择第一个成功 recipe，立即完成 shared-V、prefix replay 和完整 F3 root 的 CPU 执行包。

**一个通过：**保留这个真实正结果，不作废，也不临时降低当前“两候选确认”的规则；提交剩余风险和下一项最小确认方案。

**都没通过：**按最早失败阶段处理，不再随机选择第五个瓶子：

```text
IK失败 → 姿态/工作空间
接近失败 → 全臂路径/模型覆盖
进入抓取失败 → 接触与目标位置
闭爪后失败 → 夹持几何、控制与物理参数
抬升失败 → 实际抓持稳定性
```

shared-V 和 full root 还没有获得本轮物理执行许可，但其 CPU 实现、预算与待执行 manifest 可以继续完成。

---

# 五、F4-B：这条成熟数据线可以同步推进

F4-B 方案将 A/B/C 源物体和目标槽一起沿 table-X 负方向移动 **10 mm**，common-X tray 保持不变，使用新 seed 和新 root，目标是：

```text
3 条 r_pc
+
3 条 r_inv_motion
=
6 条开发轨迹
```

这是当前 proposal 的明确内容。fileciteturn469file0L2-L2 fileciteturn477file0L2-L2

我接受这个方案作为**pilot-B 开发验证根**，并给予条件式的一次采集范围，但要强调：

> 它是一个新的场景根，不是与 A 统计独立的泛化测试。布局只差 10 mm，必须保留 A/B 的派生关系，不能以后一个放 train、另一个冒充未见过的 test。

## 执行前完成的工作

1. 新场景真实构建使用这组新坐标和 seed。
2. 重新生成 B 的 current、anchor、candidate binding 和 prefix。
3. 三个程序重新完成该 root 内的资格与规划。
4. 使用已经修正的收据发布顺序。
5. `r_inv_motion` 只重定时 **B 自己刚通过的控制序列**，不使用 A 的控制或 raw。
6. 冻结统一的运动变体规则，沿用已验证的 `1.10` 时长规则及实际控制一致性检查。
7. 原 family verifier、终态等价、raw/video 和 cleanup 全保留。

新布局会影响 common prefix 周边环境，所以“tray 没动”不等于可以直接复用 A 的前缀证据。

## 预算及条件

当前预算提案是：

```text
r_pc：11 scenes / 136 queries
motion：3 scenes / 0 新 queries
合计：14 scenes / 136 queries / 6 raw
```

预算文件同时明确：它只是推导，实际 runner 尚需绑定；额外前置探针不能偷偷塞进零消耗。fileciteturn476file0L2-L2

本轮允许 Codex在实际调用链验证符合该上限后签发一次新作业：

```text
1 个新 root
最多 14 scenes
最多 10 个 robot-action scenes
最多 136 planner queries
3 条 r_pc + 3 条 motion
最多接收 6 条开发 raw
无自动重试
```

先验收 B 的三条 `r_pc`，再执行三条 motion。前半段失败，不继续消费后半段。

若实际所需预算高于上限，保留提案并报告差额，不能漏计或临时扩预算。

**这不授权 Stage 1 promotion，也不开放 formal 360。**但无需让 F4-B 的准备工作一直等待 F2/F3 修完。

---

# 六、从这里怎样走到真正批量造数

建议把后续目标固定成四个，不再增加无关阶段。

## 目标 1：本轮拿到新方案的真实答案

```text
F2：新内移布局的端点和路线是否通过？
F3：新 top-down recipe 能否真正夹住并微抬升？
F4-B：一个新根的六条开发数据能否完整生成？
```

不要再只提交“CPU 测试又增加了多少项”。

## 目标 2：F2/F3 各完成一个完整三分支 root

F2：

```text
新布局规划通过
→ 新公共抓取前缀
→ inside / on / beside 全部真实执行
→ root 验收
```

F3：

```text
新抓取微门通过
→ 持物 shared-V
→ 共同前缀重放
→ VVHH / VHVH / VHHV
→ root 验收
```

F2 的新布局、F3 的新抓取都要有自己的版本，不能把旧资格直接移植成新成功。

## 目标 3：补齐 48 个 pilot 格子并检查机制

当前 18 个候选格保持只读复用；若 F4-B 六条全部成功，候选输入结构将达到 **24 格**，剩余是 F2-A/B 和 F3-A/B 共 24 格。

这只是数据输入齐备程度，不是机制检查已完成。

仍需验证：

- 同意图不同路径/时长保持语义；
- 错误对象、关系和顺序会被 verifier 拒绝；
- current、anchor、event 对齐正确；
- 路径名、planner ID、长度、padding 不成为确定标签的捷径；
- F3/F4 的终态不能替代过程顺序。

pilot A/B 每根要求相应六条，**不提前强迫每个 pilot root 做 formal 9/9**。

## 目标 4：用真实 pilot 统计冻结正式生产预算

正式开始批量采集之前，至少要知道：

```text
每族完整 root 的成功率与失败类别
实际 query / scene / action-scene 消耗
每条数据与视频大小
写盘、验收、恢复是否稳定
有限重试与 reserve 规则
```

然后冻结正式 split、场景生成器、verifier、变体规则与预算，才进入 360 条。

**一个 root 成功说明模板可用；跨 root、跨 realization 的重复成功，才说明适合批量生产。**不要再用“CPU 全通过”或“某条轨迹成功”替代这一步。

---

# 七、本轮可以直接交给 Codex 的决定

下面是本轮新范围，**不是重复使用旧作业剩余额度**。执行前必须把新 proposal、目标、源码、预算和本条决定绑定，完成已有 Guard 预检及发布；不需要为每个局部 helper 再往返审批。

```yaml
review_base:
  vault_head: 9ed6a353b59c39d050a6a5b0cbfdaf4c9cdff2ad

global:
  old_consumed_jobs_reissued: false
  automatic_retry: false
  candidate_search_expansion: false
  gpu_jobs_serial: true

  preserve:
    - existing_F1_F4_accepted_data
    - existing_18_pilot_candidate_evidence
    - original_failed_attempts
    - separate_successful_F1_and_F4_source_profiles

  stage0_rerun: false
  stage1_promotion_authorized: false
  formal_360_authorized: false
  training_authorized: false
  h_reveal_authorized: false
  compression_authorized: false
  pi05_authorized: false

F2:
  decision: CONDITIONALLY_APPROVE_ONE_INWARD_LAYOUT_PLANNER_GATE
  authorized_scope: NEW_LAYOUT_PLANNER_ONLY
  source_proposal_receipt_sha256: 11f151ca27222f1ed0c974ea7dbaaa27a03233cf1451ee864441a7127486d859

  layout:
    id: f2-beside-inward-layout-v1
    translation_world_xy_m:
      - -0.09966188119296109
      - -0.008216412664910758
    new_target_geometry_xy_m:
      - -0.01966188119296107
      - 0.06178358733508925
    move_reference_and_target_together: true
    new_root_current_anchor_lineage_required: true
    inherit_old_inside_qualification_as_new_success: false

  prerequisites:
    - actual_table_footprint_and_support_check
    - moving_pair_and_initial_state_geometry_check
    - inside_on_beside_mutual_exclusivity
    - consistent_reference_and_target_binding
    - exact_goal_transform_and_grasp_transform_binding
    - correct_carried_and_released_object_planning_semantics
    - source_targets_budget_and_manifest_frozen
    - existing_guard_preflight_and_publication

  execution:
    full_constraint_ik_goals: [C, U_new, D_new]
    ik_problem_cap: 3
    route_after_all_endpoints_pass: [U_new, D_new, U_new, N]
    trajectory_query_cap: 4
    fresh_planner_only_scene_cap: 1
    physical_execution_cap: 0
    accepted_raw_cap: 0
    accepted_root_cap: 0

  no_additional_yaw_or_translation_search: true
  no_inside_old_gate_rerun: true
  after_pass_cpu_followup:
    - new_layout_controlled_insertion_root_implementation
    - complete_three_relation_qualification_scope
    - source_derived_full_root_budget
  full_physical_root_authorized_now: false

F3:
  decision: CONDITIONALLY_APPROVE_TWO_TOPDOWN_RECIPE_QUALIFICATION_AND_MICRO
  approved_direction: TOP_APPROACH_TRANSVERSE_GRASP
  source_proposal: F3_GEOMETRY_TOPDOWN_PROPOSAL_V1_20260906.json

  proposals:
    - f3-final-pose-v3-r3063-topdown-geometry-v1
    - f3-final-pose-v3-r1401-topdown-geometry-v1

  prerequisites:
    - actual_open_to_close_joint_mapping
    - sampled_closure_geometry_and_bottle_contact_reach
    - no_forbidden_palm_finger_support_intersection
    - actual_flange_to_reported_goal_roundtrip_against_real_entry
    - actual_locked_gripper_state_and_world_cache_conformance
    - full_arm_endpoint_and_path_constraints
    - exact_new_recipe_and_source_freeze

  contact_policy:
    retain_proposed_geometry_margin_m: 0.008
    positive_mesh_gap_is_not_physical_success: true
    contact_offset_band_is_not_automatic_physical_failure: true
    contact_offset_or_rest_offset_changes_allowed: false
    retain_existing_physical_classifier_and_thresholds: true
    physical_weld_allowed: false

  qualification:
    goals_per_recipe: [current_control, pregrasp, grasp]
    pregrasp_world_z_offset_m: 0.12
    ik_problem_cap: 6
    non_action_scene_cap: 2

  conditional_micro:
    physical_attempt_cap: 2
    physical_scene_cap: 2
    trajectory_query_cap: 6
    close_target: 0.50
    post_close_hold_frames: 250
    lift_from_actual_post_close_state_m: 0.025
    minimum_actual_bottle_rise_m: 0.020
    confirmation_frames: 50
    maximum_relative_translation_drift_m: 0.005
    maximum_relative_orientation_drift_rad: 0.05

  aggregate_fresh_scene_cap: 4
  shared_v: 0
  no_suffix: 0
  accepted_root: 0
  training_raw: 0

  invalid_closure_or_endpoint:
    physical_execution: false
    silently_change_recipe: false
    relax_gate: false

  after_results_cpu_followup:
    - preserve_all_stage_specific_positive_and_negative_evidence
    - prepare_selected_recipe_shared_V_and_prefix_replay_scope
    - prepare_full_F3_root_interface_and_exact_budget

F4_B:
  decision: CONDITIONALLY_APPROVE_ONE_NEW_DEVELOPMENT_B_ROOT_SIX_TRAJECTORIES
  source_proposal_receipt_sha256: 39c1f6238014b0959f43d4d4748391dd79b7c1528703c5609f0039a428984e0f

  layout:
    root_slot: f4-pilot-B-layout-v1-20260906
    seed: 2026090604
    source_and_slot_table_x_translation_m: -0.010
    common_X_tray_unchanged: true
    programs: [ABC, ACB, BAC]

  prerequisites:
    - new_scene_layout_and_seed_actually_bound
    - new_current_anchor_and_prefix_generated
    - all_original_root_prerequisite_checks_retained
    - corrected_collector_publication_path_used
    - actual_runner_budget_proven_within_caps
    - source_and_manifest_published
    - existing_GPU_Guard_checks_pass

  sequence:
    - collect_and_accept_three_B_r_pc
    - derive_motion_commands_from_B_own_frozen_controls
    - execute_three_new_B_r_inv_motion_rollouts
    - audit_six_cell_development_cohort

  motion_duration_scale: 1.10
  reuse_A_current_anchor_prefix_controls_or_raw: false

  caps:
    root_attempts: 1
    fresh_scenes: 14
    robot_action_scenes: 10
    planner_queries: 136
    r_pc: 3
    r_inv_motion: 3
    accepted_raw_trajectories: 6
    new_development_roots: 1
    formal_trajectories: 0

  extra_unbudgeted_prerequisite_probe: false
  automatic_retry: false
  automatic_stage1_promotion: false
  preserve_A_B_related_root_lineage: true
  claim_independent_test_generalization: false

budget_rules:
  fixed_seed_bank_and_iteration_caps_required: true
  batch_of_N_IK_targets_counts_as_N_problems: true
  constraint_FK_and_geometry_checks_recorded_separately: true
  solver_calls_cannot_be_disguised_as_geometry_checks: true
  setup_failures_and_consumed_scenes_recorded: true
  unknown_counter_is_not_zero: true
  failed_job_cannot_be_reissued_under_same_consumed_authority: true

scheduling:
  CPU_work_may_run_in_isolated_parallel_tracks: true
  GPU_jobs_must_be_serial: true
  run_first_the_job_whose_prerequisites_are_complete: true
  F4_B_does_not_wait_for_F2_F3_scientific_success: true
  scientific_failure_with_clean_cleanup_does_not_block_other_family: true

stop_entire_GPU_queue_on:
  - unknown_resource_accounting
  - source_or_asset_binding_mismatch
  - task_owned_orphan_process
  - cleanup_failure
  - selected_GPU_identity_or_baseline_failure
  - evidence_integrity_failure
```

## 你可以最简单地理解为

**F2：把太难够到的目标，按一个固定方案移近，再验证，不继续折腾旧路线。**

**F3：旧抓法确实会穿桌子，改成从上方夹；先确认“既不撞、又夹得到”，再真跑。**

**F4：已经成功的数据不动，另做一个新场景的六条数据，继续验证可重复生产。**

这三条线同时推进，比继续要求所有开发版本都守住最早的坐标和抓取姿态，更有可能尽快形成稳定的数据生产流程。

---

If you want, I can:

- 制定F2新端点验证详细任务清单
- 拟定F3新抓取姿态闭合及物理测试方案
- 规划F4-B开发轨迹数据采集和预算控制流程
