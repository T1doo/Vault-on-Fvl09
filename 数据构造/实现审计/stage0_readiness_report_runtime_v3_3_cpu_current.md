# Stage 0 readiness：runtime-v3_3 revision-6 terminal current

## BLOCKED_WITH_REASONS

F1仍是唯一accepted nonformal root，当前`1/4`。F2的`on/beside`局部成功不能拼成root；F3尚未真正测试r6 release clearance；F4 A-only micro的raw支持物理微抬，但运行时verifier接线错误且Guard保持fail-closed，不能retroactive accept。

```yaml
revision6_gpu_scopes_terminal: true
revision7_cpu_repairs_required: true
new_gpu_launch_authorized: false
accepted_roots: 1/4
stage0_trajectories: 0
formal_trajectories: 0
```

下一安全动作是先发布r6 immutable evidence，再完成r7 CPU/source-distinct修复、全测试、byte-equal快照和新预算/授权。Stage0继续禁止。
