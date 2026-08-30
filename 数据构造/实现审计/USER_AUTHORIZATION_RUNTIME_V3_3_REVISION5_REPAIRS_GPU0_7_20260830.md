# runtime-v3_3 revision-5 非正式修复授权

依据用户在当前 Codex 线程中的明确指令：工程修复预算不设总次数上限，可以持续查因并建立 source-distinct revision；但每次真实 GPU scope 仍必须是有限、单次、无自动 retry，并完整保留失败证据。

本授权将当前机器可执行上限推进到 revision 5，允许：

- F2 revision-5：一次完整 same-current/fresh-scene 三分支 nonformal root；
- F3 revision-5：一次完整 same-current/fresh-scene 三分支 nonformal root；
- F4 revision-5：一次 common boundary + A 20 mm micro-lift nonformal diagnosis；不运行 B/C/ABC/ACB/BAC 或完整 root；
- 使用 physical fvl05 GPU0–7 中任一张启动前 independently fresh-idle 的卡；不同 family 仅在独立 GPU、lease、cache、PID/PGID、namespace 和 cleanup 条件下并行。

机器可执行 scope 白名单严格为：

```yaml
F2_diagnosis_root_per_revision: {family: F2, family_revision_index: 5}
F3_prefix_root_per_revision: {family: F3, family_revision_index: 5}
F4_micro_lift_diagnosis_per_revision: {family: F4, family_revision_index: 5}
```

F1、canonical-prefix smoke、F4 cube IK、F4 staged/full root 及 revision 1–4/6 均不在本轮授权内。

每项必须：

```yaml
automatic_retry: false
recovery_attempts: 0
maximum_execution_per_revision: 1
formal_data: false
stage0_data: false
stage0_authorized: false
```

本授权不允许 Stage 0、Stage 1、360 条正式数据、训练、H-reveal、compression 或 π0.5。若 revision 5 仍失败，可按用户的持续修复授权先做新的 CPU/source-distinct revision，但不得复用已消费授权或覆盖失败 namespace。
