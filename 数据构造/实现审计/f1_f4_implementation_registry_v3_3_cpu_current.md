# F1–F4 implementation registry：runtime-v3_3 CPU current

当前实现版本为 `controlled_multi_future_runtime_v3_3`，科学设计仍为 `controlled_multi_future_f1_f4_v1_2`。本文件只更新 current implementation status；runtime-v3_2 历史失败证据保持不变。

| Family | 固定对象／执行臂 | runtime-v3_3 修复 | CPU 状态 | 真实 Gate |
|---|---|---|---|---|
| F1 | RGB red/green/blue + plasticbox/base3；left | 三色同一 top-down 与 4 cm+4 cm lift；terminal qpos、joint margin、waypoint clearance | implemented/tested | 3/3 suffix planner 后才执行三fresh branches |
| F2 | 071_can/base1 + box/base2 + scale/base0 + stand/base3；left | 互斥layout v2、staged inside、release dynamics、beside support z | implemented/tested | same-can 3/3 inside/on/beside verifier |
| F3 | bottle/base13 + original pad；left | grasp/lift/central/shared-first-V exact artifact；reference/replay motion/contact/grasp Gate | implemented/tested | VVHH/VHVH/VHHV 3/3 + return/final equivalence |
| F4 | common-X、A/B/C、tray/base0、visible slots；right | explicit cube grasp；A/B/C/AB staged Gate；连续稳定completion与noninterference | implemented/tested | no-action IK→A→B→C→AB→ABC/ACB/BAC |

公共实现已经包含：

- canonical prefix 单次生成、exact bytes/requested/mask replay；
- semantic P 与物理 settling 分账；
- replay-end physical acceptance；
- suffix 从 actual replay-end qpos 规划并封存 controls；
- 三个 suffix planner 全部通过前零 suffix execution；
- one-shot authorization、canonical revision ledger、source/code/budget/command/output绑定；
- GPU Guard v2_4 source-lock 后二次 fresh snapshot；
- raw 26-D/250 Hz/N+1、actual per-role pose/velocity/contact、失败与cleanup receipts。

Active与byte-equal snapshot各`245/245 tests passed`。真实canonical-prefix smoke已通过；F4共同right-workspace layout修复已通过CPU geometry、等待real IK；accepted roots仍为0，Stage 0未授权。
