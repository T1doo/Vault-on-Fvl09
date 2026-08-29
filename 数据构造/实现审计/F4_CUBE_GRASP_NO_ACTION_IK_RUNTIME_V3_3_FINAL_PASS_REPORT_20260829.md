# F4 A/B/C no-action IK final pass

Final layout `f4_right_arm_workspace_base0_v4_final`在真实GPU0/SAPIEN中通过：A/B/C各自fresh scene的pregrasp与grasp均2/2 planner Success，execution=0。

| Role | Planner | Minimum joint margin |
|---|---:|---:|
| A | 2/2 | 7.6727 rad |
| B | 2/2 | 7.7604 rad |
| C | 2/2 | 7.7264 rad |

四scene current/anchor一致、cleanup安全、orphan=0；总planner=6、budget通过。Guard无timeout、post-release verified；独立GPU0 postcheck=P8/14 MiB/0%。

该证据只证明共同right-arm cube grasp endpoints可规划，放行`A-only→B-only→C-only→A+B` staged execution Gate。它不证明staged blocks、ABC/ACB/BAC、noninterference或F4 accepted root。
