# Stage 0 readiness — smoke v1

## READY_TO_RUN_STAGE0_SMOKE_AFTER_F4_INFRA_FIX

CPU实现已完成，active/snapshot tests均=`471/471 passed`，byte-equal=true。当前只剩一个Stage 0前Gate：在真实SAPIEN中证明F4 v12不再因raw-float hash失败，且至少进入一次corridor planner query。

该Gate通过后将直接生成12-attempt Stage 0 manifest，并在GPU0–7中任意独立fresh-idle卡上并行运行F1–F4。F2/F3不需要先修到成功；失败将作为`FAILED_WITH_EVIDENCE`保留。

Stage 1、360 formal trajectories、training、H-reveal、compression和π0.5仍未授权。
