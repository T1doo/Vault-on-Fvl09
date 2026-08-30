# Stage 0 readiness：runtime-v3_3 revision-7 CPU current

## BLOCKED_WITH_REASONS

Revision-7 active/snapshot各382/382、byte-equal且独立P0审计通过，但尚未真实运行。F1仍是唯一accepted root，当前`1/4`。

下一步只允许F2-r7完整root、F3-r7完整root、F4-r7 A-only micro。发布与精确single-use bundle完成后，可在physical GPU0–7中为每个job选择一张独立fresh-idle卡；F4 micro即使通过也不是完整accepted root。Stage0继续禁止。

```yaml
revision7_cpu_ready: true
revision7_gpu_started: false
accepted_roots: 1/4
stage0_trajectories: 0
formal_trajectories: 0
```
