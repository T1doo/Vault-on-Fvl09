# 新条件范围推进：CPU前置结果、资源阻塞与F4-B预算差额

完整读取来源：<https://chatgpt.com/s/t_6a9d282120f881918863d7bf69035323>，正文16583字符、包含结尾YAML，无Markdown附件链接。原文及决定已保存为`EXTERNAL_REVIEW_NEW_F2_F3_F4B_SCOPES_20260906.md`、`EXTERNAL_NEW_F2_F3_F4B_DECISION_20260906.yaml`，基线和F2/F4-B proposal receipt均匹配。

## 目前真实状态

| 工作线 | 本轮完成 | 尚未完成/阻塞 |
|---|---|---|
| F2新内移布局 | 真实桌面footprint/底面、moving pairs、初始/持物双臂几何、三关系互斥；新binding和放置状态合同 | 选择性can-table支撑与released-can/open-gripper切换尚未接入真实IK/route checker；无GPU manifest |
| F3两top-down recipe | 实际close映射、5样本闭合、同一Y截面的双内表面可接触、原入口坐标往返；阶段A执行包/preflight | 所有GPU忙，尚未运行6IK/2scene资格；尚未进入physical micro |
| F4-B新根六条 | 原入口资格依赖及预算审计 | 直接保留现有检查至少17scene/262query，超14/136；不启动 |

本轮GPU runner实际启动次数0，新scene/IK/trajectory/physical/raw/root均0。开发仍6root/27raw；18个pilot候选格保留，Stage1=0/48、formal=0/360。不要将CPU必要条件写成物理成功。

## F2具体前置证据

`F2_INWARD_COMPLETE_CPU_PREREQUISITES_V1_20260906.json`：

- stand/final-can的全部实际native collision footprint均位于真实桌面top polygon内。
- 底面间隙分别约10.20µm与49.62µm，在原0.1mm几何数值核对精度内；不是悬空，也不以actor origin代替底面。
- stand↔最终can、初始can、诊断持物can无native交叠。
- stand↔双臂初始/持物状态无native交叠；左右link1–8碰撞XML逐一相同，使用实际捕获局部shape和URDF FK重投影，而非只检查手部。
- 保持beside=true、inside=false、on=false，radial=0.156205m；这是几何/语义必要条件，不是动态稳定性和新前缀成功。

`F2_INWARD_NEW_BINDING_ROUTE_STATE_CONTRACT_V1_20260906.json`同步stand和所有保留的三个beside坐标，只有index2启用。新layout、slot、seed与hash通过原binding validator；父asset/recipe和旧inside资格仅作历史来源，新layout动态资格pending。禁止旧current/anchor hash复用。

放置状态明确为：C/U/D前attached；在D取得支撑后，罐子成为留在D的障碍，回撤U/N用开爪状态。不能在D关闭整个table碰撞，也不能把can附着到N。**该状态合同已实现，真实碰撞checker/规划调用切换尚未完成，execution_ready=false。** 不应为凑一次GPU进度而启动旧attached-to-neutral路线。

## F3已就绪的阶段A

`F3_TOPDOWN_CLOSURE_AND_GOAL_MAPPING_V1_20260906.json`使用实际scale[-.01,.045]和mimic映射：close0.50→两个finger joint drive target0.0175m。从原实测open到目标固定五样本，不改变close、height、contact/rest offset或任何物理Gate。

`F3_TOPDOWN_INNER_SURFACE_SAME_SECTION_V1_20260906.json`进一步检查两指向内三角面在同一table-Y截面上的交点和中点，而非“任意hand mesh碰同一piece”。两个proposal均有双侧内表面接触该截面的样本，support/palm禁止穿入检查仍通过。离散几何不证明连续过程、力闭合或稳定抓持。

`new_recipe_prereqs_v1/goal_mapping.py`提供actual flange→reported command和完整原始目标链。通过AST提取的真实`Robot.left_plan_path`作外部参考，四个pregrasp/grasp目标及q/-q比较通过；没有用两个新函数互相作假对照。pregrasp固定grasp上方0.12m，actual target事先冻结。

当前阶段A入口：

```text
F3_NEW_TOPDOWN_QUALIFICATION_READY_IDLE_WAVE1_20260906.json
f3_topdown_qualification_runtime_v1_1/guarded_launcher.py
endpoint_idle_wave_scheduler_v1.py
```

两recipe各current_control/pregrasp/grasp，最多6IK/2非动作scene/0trajectory/0physical、3600s；32固定seed/100iterations、原5mm与sin(angle/2)判据。阶段B仍须以真实阶段A结果决定，不能把CPU过了当成资格过了。

## 全卡忙和零消耗调度记录

实时snapshot显示GPU0–7都有他人compute任务，显存约21–43GiB、P2/活跃利用率。一次外层编排在snapshot后缺少分支短路，仍调用了Guard；Guard2640173自己拒绝忙卡，**child_pid=null、launch_snapshot=null、output不存在**，没有GPU工作进程或场景启动。

旧Guard对“从未启动child”的路径仍等待他人卡回idle，63.01s后报CooldownExhausted。这是资源归属判定不适用，不是本项目泄漏或驱动坏了：cache_removed=true、lease_released=true，host确认Guard退出。原terminal/post-validation保留在`Robotwin2/datasets/f3_new_topdown_qualification_v1_guard`，不覆盖。

已修复：外层wave scheduler在全忙时不调用Guard，CPU实录fixture验证零dispatch；GPU7单卡idle fixture亦可正确选择7。新V1.1 Guard只对实际启动过child的路径要求卡回baseline；无child路径明确baseline restoration不适用，仍验证cache/lease，不宣称他人卡已经空闲。

新ready manifest记录原blocked Guard hash，并保留未消费6IK/2scene额度。依据工作区GPU规则，“调度不消费one-shot”；这不是重发已经执行失败的旧作业。下次先完整实时snapshot，再atomic Guard/UUID/lease；不共享忙卡。

## F4-B为什么暂不能签执行包

见`F4_B_ACTUAL_ENTRY_BUDGET_GAP_REVIEW_20260906.md`。现有root入口需要新candidate的三个精确passing source planner terminal，再从root实际prefix末态重新规划。A的terminal绑定旧candidate/spec，不能复制改hash给B。

因此直接复用当前入口并保留检查，至少在14scene/136query之外增加3scene/126query，即**至少17/262，比上限至少多3/126**；尚未包含可能新增的template/isolation资格成本，不能把这个下界直接当完整新预算。

下一项具体审查应选择：完整核算扩展预算，或版本化合并新B资格与root内部规划，在相同真实prefix状态和物体状态下安全复用controls。后者不能靠删除旧terminal检查、冒用A资格或隐瞒query来达标。没有F4-B GPU manifest、没有新增probe。

## 下一步

1. GPU空闲后，先运行已就绪F3阶段A，按真实结果推进条件micro，旧终点绝不重跑。
2. 完成F2真实持物/支撑/释放模型切换，验证实际入口后按既有新许可执行3IK+4route/1scene，不需要重复审批单个helper。
3. F4-B只解决上述预算/接口问题后再签发作业；其六条目标、1.10motion、与A的相关scene-family lineage保持。
4. 不开放Stage1 promotion、formal360、训练、H-reveal、compression或π0.5。
