# Stage 0 readiness：runtime-v3_3 revision-7 terminal current

## BLOCKED_WITH_REASONS

F4 A-only micro已经通过，但不是完整F4 root。F1仍是唯一accepted root，当前`1/4`；F2 inside未执行，F3未开夹/验证final equivalence，F4 B/C与完整三程序未运行。

```yaml
F4_A_only_micro: accepted
revision7_gpu_scopes_terminal: true
revision8_cpu_work_required: true
new_gpu_launch_authorized: false
accepted_roots: 1/4
stage0_trajectories: 0
formal_trajectories: 0
```

下一安全动作是封存r7证据，再完成F2 planner-false/XY-only、F3 separation/contact signal mapping和F4 full-scope CPU审计。Stage0继续禁止。
