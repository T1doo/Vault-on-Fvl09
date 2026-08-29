# F4 revision-1 failure and revision-2 repair report

Revision-1在staged common-X prefix的target construction阶段停止，planner/execution receipt写0。源码与traceback表明官方`choose_grasp_pose`实际对4个contact points各做1次right/left-selection batch（每批10 candidates），均无可用common grasp；随后legacy代码未先检查`None`，才触发reshape异常。诚实posthoc口径为planner4/256、execution0。GPU6、2 scenes cleanup、cache/lease/post-source-lock全部安全。

Revision-2不改最终layout、common-X/tray、right arm、common-X-first、ABC/ACB/BAC、slot/verifier。Common-X改用现有`project_cube_grasp_pose_v1`显式right-arm contract；该contract源自历史成功common-X grasp/transport，且同一contract已让A/B/C final-layout IK 3/3通过。Planned spec现在显式`arm=right`；common9段、每block6段、role/order/flattened targets均runtime assert；未知grasp mode直接失败。Planner envelope回到102、execution7。

R1 evidence tree=`c0b20491…563e`。F4只剩一次revision-2，失败即terminal。
