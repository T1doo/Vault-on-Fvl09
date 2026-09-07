# F3下一独立设计决策：竖直瓶体的上部侧夹

**提案，未授权执行。** 现有稳定recipe三次修订上限及全部失败保持，不能把下面方案暗记成旧Goal中的第四次微调。本材料仅用于新的impact review/明确决策，未改代码、资产或预算。

## 为什么需要改变抓持机制

现有三次修改都在“横放瓶体、从上方夹圆柱横截面”的框架内移动station/深度。最终真实lift结束尚在门内，但确认窗继续滚转，达到6.065mm/0.05758rad；两指持续接触不等于能抗转矩。接触从瓶体COM上下反复迁移，说明静态“内表面可以碰到瓶子”不是稳定夹持证明。

本提案不再寻找横放时另一个毫米级位置，而把瓶轴从table Y改为table Z，让物体重心落在夹持位置**下方**，并优先寻找能承托轴向负载的瓶口凸缘。它改变重力/接触支撑关系，而不是给旧失败补一点高度余量。

## 首选A：同一13号瓶竖直摆放，夹瓶颈并利用上方凸缘承托

保留001_bottle/model13、scale0.132、原native七凸包、质量0.01kg、实测惯量、摩擦、机器人/夹指碰撞形状。拟将瓶体local +Y（其长轴）转为world +Z；几何旋转候选为Rx(+90°)，actor高度按native最低点与原pad顶面对齐，**不是照抄原actor z=0.785**。source XY可先保留原位置，候选场景/seed/姿态应另建planned spec。

拟侧向接近瓶颈（机器人前方向+Y接近，夹爪沿world X闭合），固定几何站点候选为bottle-local y≈0.220m。实际gripper pose仍需CPU从原生手形状/URDF/原入口转换推导，不能把此坐标当已合格执行pose。

原生截面证据（不是visual外观猜测）：

- y=0.220m：横向宽约36.230mm/34.346mm。
- y=0.225m：上方凸缘宽约40.394mm/36.789mm。
- 两轴上的单侧凸出量约2.082mm/1.222mm；属于小凸缘，尚未证明完整环向或手指承托可达。
- 实际local COM y=0.110451m，竖直后COM约低于该站点109.549mm，而不是旧横夹中几毫米的不稳定上下差。

预期机制：手指闭合在较窄处，上方凸缘有机会压在指面上承担向下负载；重心在夹持点下可对横向滚转产生恢复趋势。因此对当前“绕横向接触线滚转”的失败，机制上比继续横夹调高度更直接。**这只是有证据的候选，不是已实现形封闭或力封闭**：凸缘很薄、native网格有分片，指面可能够不到；圆形颈部绕自身轴的扭转仍要靠真实接触约束，不允许因瓶子近似旋转对称就免除0.05rad门。

## 备选B：同一竖直13号瓶，上段直壁侧夹

若A在CPU审查中不能形成真实可达凸缘承托，可考虑固定local-y≈0.170m的上段直壁侧夹，不加任何结构。这里native宽约67.838mm/67.088mm，COM在夹点下约59.549mm。

与A不同，B不主张凸缘承托，主要依赖较宽直壁上的摩擦夹持及COM下置带来的恢复趋势。它仍可能扭转/滑移，证据强度弱于A；不应在A物理失败后自动拿B再试。**A/B只能在CPU审查后择一冻结，新预算总额不因备选翻倍**。若两个都不能证明必要几何条件，本轮结论应是“尚无充分方案”，而不是继续搜更多点。

## 一个必须先解决的资产边界：竖直站立未证明

旧代码 `probes/scene_inspection.py::F3Scene.load_actors` 明确用[0,0,1,0]横放瓶体；model_data13的stable=true不能替代新朝向的真实资格。native最底层在1µm/10µm层只有1个顶点，0.1mm层2个，1mm层才有23个，后者投影包围COM但不是实际共面支撑。一次精确最底层ConvexHull诊断因点不足退出，未生成任何假稳定结果。

所以竖直方案可能在canonical settle后微倾或不稳。必须在首次资格scene、任何抓取动作前以新冻结姿态/原稳定门检查实际支撑和稳定性；失败就停止。不能临时磨平碰撞底面、加托架、改变质量/惯量、延长等待直到挑中稳定或重采scene。该风险同时影响A/B。

## 影响边界

| 项目 | A/B提案是否改变 |
|---|---|
| asset ID/scale、native碰撞体、夹爪/机器人形状 | 不改变 |
| 质量、惯量、摩擦、驱动/close0.50 | 不改变；新场景实测并核对，不能静默重算惯量 |
| 初始瓶朝向/actor高度、场景current/anchor、抓取朝向与站点 | **改变，必须新scene/grasp design版本和hash** |
| F3程序VVHH/VHVH/VHHV、table-frame V/H、V=.055、七点/hold50/250Hz | 不改变 |
| 原20mm/5mm/.05rad/50帧微门、preV/event/postV/final-state等价 | 不改变 |
| prefix物理轨迹、P/hash、clearance/return/release几何 | 必须重新构造/审查，不继承旧成功或旧前缀 |
| raw/action schema、split/root原子性、R、formal分母 | 不改变，不产生accepted root或formal授权 |

竖直后V相对瓶轴的方向关系改变，但科学定义仍为table坐标闭环事件，不应把V改为瓶坐标、改动标签或缩小幅度。需要新observable-task-tree/prefix实现影响记录，不能混用旧current/prefix或把旧失败替换成新成功。release/最终状态也须针对新朝向重审，三程序最终等价要求不减；不在下面两次资格预算里偷偷做suffix/root数据。

## 提交用户的新授权边界（尚未获得）

申请的应是“同资产竖直抓持设计的新有限资格轮次”，明确允许新场景/抓取朝向与spec版本，同时保留旧三次稳定修订失败；不是重新解释旧remaining budget。先CPU审查A，必要时仅CPU审查B，然后**唯一选定一个**设计/pose/seed/停点；任何物理执行之前冻结目标和完整版本。若用户不批准新边界，只继续CPU审查和F2/F4。

CPU前置必须包括：native支撑几何/初始姿态、实际COM/惯量绑定、所选颈部/直壁与两指真实可达接触、原工具→world/base→bias/Aloha转换往返，以及新侧抓姿态的原生全臂非邻接自碰/world审查（至少不能遗漏已知link3/link5）。没有实际规划controls时只能称端点必要条件；GPU产生每段controls后还要native逐点pre-execution筛查，不能拿手掌几何代替全臂。

## 最多一次资格 + 一次条件确认：预算草案

这是新的待批准上限，未reserve。A/B共用下表总额，不各拿一份。

| 作业 | 条件/内容 | Solver上限 | Scene/物理尝试 | Child/lease |
|---|---|---:|---:|---:|
| 资格一次 | 新固定场景settle先过原稳定/支撑门；C/pregrasp/grasp三个full-constraint单目标IK；一次pregrasp、grasp、25mm lift，原hold/postlift门 | 3 IK + 3轨迹 = 6 | 1 fresh / 1 action / 1 attempt | 900s /1080s |
| 确认一次 | 仅资格全部通过；第二fresh同一冻结spec，重复3 IK +3微门轨迹；第二微门与full恢复先通过后，同scene条件接15/40mm两段、carry两段、原V七点 | 3 IK +14轨迹 =17 | 1 fresh / 1 action / 1 attempt | 1800s /1980s |
| 总计 | 失败即停止，不换B补跑，不改参数续试 | **23 solver** | **2 fresh /2 action /2 attempts** | **3060 lease秒** |

正常微门model状态检查每scene至多6次（full2/pair2/restore2），单列非solver；GPU kernel次数未知不得写0。原生检查都是CPU几何检查，不偷偷调用IK。拟物理step总上限为资格6000、确认12000（含setup/hold/全部真实步，实施前绑定计数器）；若实际生成控制超余量，应在执行前停止，不截断轨迹凑成功。

0 collection、0训练raw、0 accepted root、0 formal；只保存完整诊断trace/receipt及必要inspection视频。第一资格失败不进确认；第二微门失败不进shared V；shared V失败也不追加后缀/第三scene。预算不足、侧抓路径需要额外中继、姿态初始不稳等都属于需停下重审的结果，不自动加query。

GPU仍只用当时fresh-idle的0–7之一，串行、一卡一job、单root不shard，独立Guard/UUID/lease/pre-post/owned cleanup。通过这两次也仅证明新抓持+sharedV资格，不自动授权F3完整root、Stage1科学实验、formal360或训练。

## 本材料的证据等级

已有：真实承重后接触迁移/滚转失败、同资产native截面/COM和现有横放代码。
推断：竖直上部侧夹可能改善横向滚转；A凸缘可能提供轴向承托。
未证明：竖直站立、完整手指承托、侧向IK/native路径、抗自身轴扭转、任何新物理成功。

`geometry_profile.json`为14个固定几何截面的只读调查，不是14个试跑候选；receipt `7c51eb7349853f99dae247fa064d813a04c4f0769949435a3a3ace80b96c50f7`。只有新报告/几何统计脚本，执行代码和资产未修改。
