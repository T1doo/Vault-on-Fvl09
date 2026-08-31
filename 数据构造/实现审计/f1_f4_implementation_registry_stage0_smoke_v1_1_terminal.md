# F1–F4 implementation registry — Stage 0 smoke v1.1 terminal

Base asset/physics/verifier registry继续引用`f1_f4_implementation_registry_v3_1_cpu_current.md/json`。本轮不修改科学设计、资产、物体ID、arm、program或verifier。

| Family | Terminal outcome | 真实根因 | 下一审阅方向 |
|---|---|---|---|
| F1 | 3/3 PASSED；3 raw + 3 MP4 | 无Stage 0 blocker | 是否批准作为Stage 1候选 |
| F2 | 3×infrastructure failure | root spec漏带冻结scene layout | 只修manifest/layout wiring，不将其解释为物理失败 |
| F3 | 3×execution failure | shared pre-V grasp/stationarity/support Gate | physical impact review |
| F4 | 3×planner failure | v13 neutral已修，但4条corridor均不可解 | layout/task implementation impact review |

12/12 terminal receipts存在，3 success/9 failure，canonical finalizer因F2 pipeline错误报告`stage0_completed=false`。每条generated trajectory均有独立MP4。
