# Stage 0 readiness：runtime-v3_3 revision-5 CPU current

## BLOCKED_WITH_REASONS

F1仍是唯一accepted nonformal pre-Stage-0 root。F2/F3/F4 revision-4真实失败证据已不可变封存；revision-5 active与byte-equal snapshot各`339/339`通过，三组独立P0审计未发现剩余确定性GPU前代码blocker，但revision-5尚未真实运行，因此Stage 0继续禁止。

下一轮只允许三个scope：F2-r5完整root、F3-r5完整root、F4-r5 common boundary + A 20mm micro-lift。F4 micro通过也不能算F4 accepted root，更不能在同一revision继续full root；后续必须建立source-distinct r6和新授权。

```yaml
accepted_nonformal_pre_stage0_roots: 1/4
revision5_cpu_ready: true
revision5_gpu_run_started: false
stage0_trajectories: 0
stage1_trajectories: 0
formal_f1_f4_trajectories: 0
h_reveal: null
training_started: false
compression_started: false
pi0_5_started: false
```

下一顺序：发布clean revision-5 byte-equal baseline→从published HEAD签三份single-use bundle→在三张fresh-idle GPU并行运行→审计receipts/traces/verifiers/cleanup→继续source-distinct修复直到4/4 accepted→只生成Stage 0审批包并等待用户另行批准。不得自行启动Stage 0。
