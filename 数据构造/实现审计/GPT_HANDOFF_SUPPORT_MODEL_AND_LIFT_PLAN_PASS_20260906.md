# 支撑接触模型已通过真实GPU验证，25mm lift规划成功

本轮用户授权：“允许，你一直修就好了”，对应保存的闭爪状态模型验证与最多一次lift规划。普通代码修复/检查继续自主推进；本轮没有新建仿真scene，也没有执行物理动作。

## 结论

导致上一轮停止的规划器支撑接触问题，已在该保存状态上修复并验证：

| 检查 | 原完整模型 | 新pair-aware模型 |
|---|---|---|
| single起点 | INVALID_START_STATE_WORLD_COLLISION | valid |
| batch起点 | INVALID_START_STATE_WORLD_COLLISION | valid |

随后只调用一次lift规划，成功。109个插值控制点的native几何检查全部通过：

- 计划actor上升 **24.99949mm**。
- native最低点由0.74994908m升至0.77494706m；最低点序列不下降，不进一步进入垫子。
- 原20mm计划升高、最终离开支撑等筛查均通过。

这是**真实GPU模型和规划成功**，不是物理抬升成功。没有执行109点控制，不计作训练raw/root；尚未证明离台承重抓稳，也没有通过完整micro/postlift。

## 修复不是关闭整张桌面

single/batch各包含125个附着瓶子球。完整world为14个mesh，附着瓶子视图为13个mesh，只少`pad__0`；所有机器人球仍查完整world，table、对臂和其他障碍没有关闭。

两路actual Warp缓存均核对通过，各94项优化器缓存callback绑定检查通过。原PrimitiveCollisionCost在构造时保存callback，所以本次在MotionGen构造前注入checker，而不是只改一份表面配置。

成功规划过程中，single-pair checker从构造到规划结束记录7次collision、323次distance、1500次swept-distance方法入口，swept-collision0。它们是方法调用实测值，**不是精确CUDA kernel launch总量**；CUDA launch总量没有profiler记录，应记unknown而非0。预算计数是明确的4个高层起点检查与1个trajectory问题，未把模型检查伪装成额外IK/轨迹。

原factory输出中的“PROPOSAL”静态字符串是此前实现标签，本次job terminal与GPU审计证明它已在当前冻结输入上验证。不能据此反推所有其他scene/model均已验证。

## 输入/来源边界

使用上一轮真实postclose qpos、actor/EEF pose、抓持变换、native瓶体几何和同布局静态capture，重新投影对臂world pose。CPU核对trace末行、FK及原actual EEF+25mm目标；不导入专家未来数据到训练，也没有建立新物理锚点。

在整理来源时发现prepare保留了捕获时的actor pose/per-shape hash字段，而solver_pose已是postclose重投影值。`SUPPORT_MODEL_PROJECTION_METADATA_OVERLAY_V1_20260906.json`将这些历史元数据显式放入source_capture_metadata，补出投影actor pose/self-hash；验证name/vertices/faces/solver_pose逐值不变。原输入、GPU输出和hash不覆盖，模型数值及本次结果不变，不重跑GPU。

## 资源与账本

GPU2 UUID `GPU-4306d28e-0eeb-2e26-bda4-b1b44058f63e`，由live wave自动选择并经Guard原子重查。Guard2952209/child2952249，总37.39s，单次规划约10.43s；exit0、完整计数与cleanup通过。独立host确认GPU2恢复14MiB/0%/P8/no compute，两PID退出。

本次新增：0scene、0physical、0IK、4高层constraint检查、1trajectory规划、0raw/root。此前真实micro/失败/替换账本不改；跨新批准范围累计为4scene、6IK、5trajectory、2physical-attempt slots、1实际arm执行scene。

输出：`/nfs_share/lijunhui/Robotwin2/datasets/f3_support_model_replay_v1`。

## 已继续完成的CPU后续接线

`f3_support_aware_physical_proposal_v1/micro.py`接入已验证模型，`support_pair_collision_v1/live_witness.py`与`escape.py`要求：

1. 新物理场景重新通过原pregrasp/grasp Gate，真实close/hold。
2. 从当次实际250帧保持、当前qpos和当前world重新生成支撑证据；不能直接继承上一轮“稳定=true”。
3. 构造实际pair-aware single/batch checker。
4. 从当次actual postclose状态规划lift，先通过native-escape Gate，才允许执行。
5. 保留原20mm/50帧/5mm/.05rad与接触/禁止碰撞验收。

新接口在保存的真实250帧hold上复核通过，并复现109点计划的native gate通过；AST/命名空间检查通过。**新物理接口尚未在live scene执行，不算端到端物理验证。** `F3_SUPPORT_AWARE_PHYSICAL_VALIDATION_PROPOSAL_V1_20260906.json`仅是一次新physical验证的有限提案（1scene/3trajectory/1attempt，0新IK/raw/root），approved=false，未签发执行manifest。

不再请求重复批准已经完成的模型检查或普通CPU代码修复。下一项真正新增物理验证须作为新范围单独列账；当前无新物理执行授权。r1401的pregrasp未合格状态保持，不能降低“两候选确认”，也不进入sharedV/full root。

F2持物/释放模型接线、F4-B预算差额仍待解决；开发接受仍6root/27raw，pilot候选18格，Stage1=0/48、formal=0/360。没有训练、H-reveal、compression或π0.5。

统一状态：`STAGE1_READINESS_SUPPORT_MODEL_LIFT_PLAN_PASS_20260906.json`。
