# F4 right-workspace layout impact review v7

状态：`cpu_geometry_pass_real_three_role_ik_pending`。

## 触发证据

Runtime-v3_3 no-action IK中，A/B/C在同一right-arm grasp orientation下全部首段pregrasp失败；它们的world x为`0.07/-0.08/-0.23`。历史common-X在同一orientation、world x≈`0.28`成功，因此优先修复共同layout，不写role-specific姿态。

## 唯一共同修复

保持以下内容不变：

```text
right arm
project_cube_grasp_pose_v1
common-X pose
008_tray/base0 pose
branch-neutral pose/orientation
ABC / ACB / BAC
object-slot mapping
verifier thresholds
```

三对象统一移入right-workspace band，slots同步使用一套可见排列：

| Role | Object xy | Slot xy |
|---|---|---|
| A | (0.18, 0.175) | (0.15, 0.032) |
| B | (0.29, 0.175) | (0.30, 0.032) |
| C | (0.40, 0.175) | (0.41, 0.032) |

Layout version=`f4_right_arm_workspace_base0_v3`，SHA=`c0378c073e435f8a0772ce03890bb872150c228aee29067a2a0686f4153f9925`。

CPU checks全部通过：tray/objects/slots在桌面内；tray不与objects/slots重叠；objects和slots最小pairwise separation均约0.11 m；common-X与objects/slots保持安全间距；三个object x均在同一`[0.18,0.40]`候选band。

这只是layout impact review，不证明IK可达。下一步重新运行一次A/B/C no-action IK；三者2/2 planner和joint margin全部通过前，继续禁止staged/full F4执行。
