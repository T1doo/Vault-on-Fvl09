# Stage 0 readiness：runtime-v3_3 revision-7 CPU current

## BLOCKED_WITH_REASONS

Revision-7 active/snapshot各382/382、byte-equal且独立P0审计通过，但尚未真实运行。F1仍是唯一accepted root，当前`1/4`。

下一步只允许已经发布的F2-r7完整root、F3-r7完整root、F4-r7 A-only micro single-use bundles。可在physical GPU0–7中为每个job选择一张独立fresh-idle卡；不同卡并行必须完整隔离，F4 micro即使通过也不是完整accepted root。Stage0继续禁止。

```yaml
revision7_cpu_ready: true
revision7_gpu_started: false
new_gpu_launch_authorized: true
accepted_roots: 1/4
stage0_trajectories: 0
formal_trajectories: 0
```
