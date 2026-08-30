# Stage 0 readiness：runtime-v3_3 revision-5 terminal current

## BLOCKED_WITH_REASONS

F1是唯一accepted nonformal pre-Stage-0 root。F2 r5只有on/beside accepted、inside失败；F3 r5三程序一致失败于release clearance；F4 r5 micro在close前grasp boundary失败。局部成功不能拼成root，accepted仍`1/4`。

```yaml
accepted_nonformal_pre_stage0_roots: 1/4
revision5_gpu_scopes_terminal: true
revision6_cpu_repairs_in_progress: true
stage0_trajectories: 0
stage1_trajectories: 0
formal_f1_f4_trajectories: 0
h_reveal: null
```

下一安全动作是完成F2/F3/F4 source-distinct r6、CPU/P0/byte-equal/publication，再签新的single-use scopes。仍不得启动Stage0。
