# Stage 0 readiness：runtime-v3_3 revision-4 CPU current

## BLOCKED_WITH_REASONS

F1是唯一accepted nonformal pre-Stage-0 root。F2/F3/F4 revision-3均安全终止并已封存；revision-4 active与byte-equal snapshot各309/309通过，多代理P0 sweep无剩余确定性GPU前blocker，但r4尚未真实运行，因此Stage0继续禁止。

仍缺：F2 accepted root；F3证据完备diagnosis后完整VVHH/VHVH/VHHV+return root；F4 staged A/B/C/AB与ABC/ACB/BAC accepted root；四family后的真实SAPIEN pipeline总复核。

```yaml
accepted_nonformal_pre_stage0_roots: 1/4
stage0_trajectories: 0
stage1_trajectories: 0
formal_f1_f4_trajectories: 0
h_reveal: null
training_started: false
compression_started: false
pi0_5_started: false
```

下一顺序：发布r4 byte-equal baseline和r3失败证据→从clean published HEAD签三个r4 one-shot bundles→在三张fresh-idle GPU并行运行→审计receipts/traces/verifiers/cleanup→只有4/4 accepted且pipeline通过才可写`READY_FOR_USER_REVIEW_BEFORE_STAGE_0`，仍不得自行启动Stage0。
