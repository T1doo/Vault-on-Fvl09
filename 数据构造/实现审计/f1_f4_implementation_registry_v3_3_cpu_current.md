# F1–F4 implementation registry：runtime-v3_3 CPU current

当前实现版本为 `controlled_multi_future_runtime_v3_3`，科学设计仍为 `controlled_multi_future_f1_f4_v1_2`。本文件只更新 current implementation status；runtime-v3_2 历史失败证据保持不变。

| Family | 固定对象／执行臂 | runtime-v3_3 修复 | CPU 状态 | 真实 Gate |
|---|---|---|---|---|
| F1 | RGB red/green/blue + plasticbox/base3；left | r1红/绿planner通过、蓝在role-local `safe_vertical`失败；r2三色统一回公共hub后升至不变1.02 m；完整batch planner计数 | r1 failed；r2 CPU/tested | 仅剩一次r2；3/3 suffix planner后才执行三fresh branches |
| F2 | 071_can/base1 + box/base2 + scale/base0 + stand/base3；left | 互斥layout v2、staged inside、release dynamics、beside support z | implemented/tested | same-can 3/3 inside/on/beside verifier |
| F3 | bottle/base13 + original pad；left | grasp/lift/central/shared-first-V exact artifact；reference/replay motion/contact/grasp Gate | implemented/tested | VVHH/VHVH/VHHV 3/3 + return/final equivalence |
| F4 | common-X、A/B/C、tray/base0、visible slots；right | explicit cube grasp；A/B/C/AB staged Gate；连续稳定completion与noninterference | final-layout no-action IK 3/3 passed | A→B→C→AB→ABC/ACB/BAC |

公共实现已经包含：

- canonical prefix 单次生成、exact bytes/requested/mask replay；
- semantic P 与物理 settling 分账；
- replay-end physical acceptance；
- suffix 从 actual replay-end qpos 规划并封存 controls；
- 三个 suffix planner 全部通过前零 suffix execution；
- one-shot authorization、canonical revision ledger、clean published Vault HEAD、source/code/budget/command/output绑定；
- GPU Guard v2_4.1允许physical GPU0–7：每卡原子lease、每job独立HOME/cache/TMP、source-lock后双fresh snapshot、PID/PGID/信号清理、post source-lock与release；
- official grasp chooser的batch API calls与内部10-pose candidates分账；root runtime count必须等于receipt并不超过source-bound envelope；
- raw 26-D/250 Hz/N+1、actual per-role pose/velocity/contact、失败与cleanup receipts。

Active与byte-equal snapshot各`256/256 tests passed`，source SHA=`40e2ef20…`。真实canonical-prefix smoke已通过；F4 final-layout A/B/C no-action IK 3/3通过。F1 revision-1已受控失败：显式26次planner，posthoc补见12次未入账batch calls（完整38/64），branch execution=0、cleanup/release安全；该缺口已在新source中fail-closed修复。Accepted roots仍为0，Stage 0未授权。
