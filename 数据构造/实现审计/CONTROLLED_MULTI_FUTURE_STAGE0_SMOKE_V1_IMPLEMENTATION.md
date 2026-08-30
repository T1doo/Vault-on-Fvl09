# controlled_multi_future_stage0_smoke_v1

当前状态：`CPU_READY_F4_INFRA_VALIDATION_PENDING`。

本轻量后续不是`v3_4_2`重试链。它只做两步：

1. 修复F4 fresh-scene candidate raw-float hash障碍，并在真实SAPIEN中证明至少进入一次corridor planner query；
2. 直接运行`4 families × 3 r_pc = 12`个Stage 0 smoke attempts。

Stage 0可以得到`PASS`或`FAILED_WITH_EVIDENCE`。F2/F3已知物理失败不在Stage 0前修正；shared Gate若在branch前失败，仍为三个planned attempts写终止回执，但不伪造raw trajectory。

保留的硬要求：same-current/anchor、candidate/label/arm不漂移、真实verifier、26-D 250Hz N/N+1、有限预算、失败保留、fresh scene、source/UUID/Guard/cleanup/orphan审计。

CPU source SHA=`6f09da13d447b11b89940b8142f7f49152d77937e1cd9a6893bad9f8e2098cad`，tests SHA=`1ac4cfd9afe68f3313987f3b7bb3f2392094e4432d83300dc7d36ca246d986c3`，budget SHA=`4ca7471888af9282351a1455bf96965fd565001b43f0806ec1d40e2b67913783`。Active/snapshot CPU tests均=`471/471 passed`，byte-equal=true。

本实现只授权Stage 0，不授权Stage 1、360条formal、training、H-reveal、compression或π0.5。
