# Stage 0 readiness：runtime-v3_3 revision-6 CPU current

## BLOCKED_WITH_REASONS

Revision-6 active/snapshot各359/359、byte-equal且独立P0审计通过，但尚未真实运行。F1仍是唯一accepted root，当前`1/4`。

下一步仅允许F2-r6完整root、F3-r6完整root、F4-r6 A-only micro。F4 micro即使通过也不是accepted root。Stage0继续禁止。

```yaml
revision6_cpu_ready: true
revision6_gpu_started: false
accepted_roots: 1/4
stage0_trajectories: 0
formal_trajectories: 0
```
