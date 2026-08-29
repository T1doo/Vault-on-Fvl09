# F4 procedural-cube no-action IK：runtime-v3_3 run1

状态：`FAILED_NO_ACTION_IK_ALL_THREE_PREGRASP`。

固定同一个right-arm local grasp contract，分别在A/B/C fresh scene中只规划pregrasp/grasp，不执行动作。结果三者都在第一段pregrasp失败：

| Role | World x | Planner queries | 结果 |
|---|---:|---:|---|
| A | 0.07 | 1 | `A_pregrasp=Fail` |
| B | -0.08 | 1 | `B_pregrasp=Fail` |
| C | -0.23 | 1 | `C_pregrasp=Fail` |

对照历史成功common-X：同一orientation在world x≈0.28的pregrasp/grasp成功。当前证据优先指向A/B/C联合布局位于right-arm工作区左侧，而不是role-specific几何或scalar helper问题。

四个scene cleanup全部安全、orphan=0；execution=0、planner=3、budget通过。Guard无timeout、post-release verified，独立GPU0 postcheck=P8/14 MiB/0%。

按停止线不进入A/B/C staged execution或ABC/ACB/BAC。下一步只能做一个三角色共同的right-workspace layout impact review；不得给A/B/C分别写特殊姿态、换物体或偷偷换臂。
