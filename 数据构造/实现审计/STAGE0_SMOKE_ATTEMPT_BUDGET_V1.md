# Stage 0 Smoke Attempt Budget V1

Implementation：`controlled_multi_future_stage0_smoke_v1_1`
Budget SHA：`8aab303dfdf0f33d9558b8e67fe8c59564d8881d73ccf96301a6f676ea72bf1a`

| Scope | Planner | Execution | Recovery | Timeout | Data role |
|---|---:|---:|---:|---:|---|
| F4 v13 infrastructure | 48 | 0 | 0 | 7200s | nonformal pre-Stage0 |
| F1 Stage 0 root A | 64 | 3 | 0 | 7200s | Stage 0 smoke |
| F2 Stage 0 root A | 64 | 3 | 0 | 7200s | Stage 0 smoke |
| F3 Stage 0 root A | 96 | 3 | 0 | 10800s | Stage 0 smoke |
| F4 Stage 0 root A | 96 | 3 | 0 | 20400s | Stage 0 smoke |

每个scope仅一次调用、无自动retry。GPU0–7中任一独立fresh-idle卡可用，一卡一个project job、一个family root不拆分。Stage 0固定12个`r_pc` attempts；成功与失败均保留。

每条真正生成的Stage 0 trajectory必须同时生成独立head-camera MP4：25fps、每10个250Hz control steps采样，并包含initial/final frames。无trajectory的planner/prefix失败明确记录`video_not_applicable_no_trajectory`，不得伪造空视频。

本预算不授权Stage 1、360条formal、训练、H-reveal、compression或π0.5。
