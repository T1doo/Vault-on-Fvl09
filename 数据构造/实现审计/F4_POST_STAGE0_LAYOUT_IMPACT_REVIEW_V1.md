# F4 post-Stage-0 layout impact review v1

## 结论

Stage 0 v13已经排除hash/neutral/重建基础设施问题：四条完整candidate chain均能通过prefix、pregrasp、grasp、lift与各自carry waypoint，最终统一在旧slot侧的`A_preplace`或`A_lower_preplace`以`MotionGenStatus.IK_FAIL`终止。因此下一步修复layout的slot positions，而不是继续给旧layout增加corridor。

冻结新layout `f4_post_stage0_slot_row_v1`：objects、common-X、tray、right arm、branch-neutral、object-slot mapping、ABC/ACB/BAC和verifier全部不变，只将slots改为共享row：A=`(0.100,0.080)`、B=`(0.205,0.080)`、C=`(0.355,0.080)`，layout SHA=`09d2ef2d8051cdfab31463fd04c0c944cd7db0f65a0fbdfc2825f0fb0003e557`。

CPU搜索使用5 mm网格、有序共享y-row、105 mm slot-pair margin和75 mm slot-object/common margin；共检查1,371,720个候选，13,051个可行，以预先固定的六级词典序目标选出唯一候选。现有完整geometry audit通过：最小slot-pair=105 mm、slot-object=75 mm、slot-common=77.6 mm。

第一版搜索因内层重复读取资产而被主动中止；旧62 mm硬边界最优点仅多0.65 mm余量而被拒绝；75 mm版本的首个点因浮点值`0.09999999999999999 m`未通过既有严格pairwise Gate而被拒绝。三项都保留为失败/拒绝记录，没有进入SAPIEN或planner。

后续只允许一个endpoint-IK + planner-only scope：固定复用v13已有candidate 3 `lower_carry_height`，不新增corridor；执行一次common-X→tray canonical reference prefix，再在三个fresh program scenes中exact replay prefix并分别规划ABC/ACB/BAC完整链。所有endpoint IK、collision、joint margin与qpos continuity必须通过；suffix execution/release均为0。只有三条完整program chain全部通过，才允许最多一个post-Stage-0 F4 development root。

本review只支持`CPU geometry verified`；IK、planner-only、development-root与Stage 1 readiness当前均未通过。
