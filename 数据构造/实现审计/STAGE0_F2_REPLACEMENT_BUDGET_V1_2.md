# Stage 0 F2 replacement budget v1.2

```yaml
scope: Stage0_v1_2_F2_root_A_scene_layout_replacement
programs: [F2-inside, F2-on, F2-beside]
attempts: 3
attempts_per_program: 1
planner_query_limit: 64
execution_limit: 3
recovery_attempts: 0
automatic_retry: false
timeout_seconds: 7200
allowed_physical_gpu_indices: [0, 1, 2, 3, 4, 5, 6, 7]
formal_data: false
stage0_data: true
stage1_authorized: false
```

任一物理/planner/verifier failure均保留为有效Stage 0 smoke evidence，不为成功现场热修。Cleanup/source/GPU/current-anchor lineage不确定则fail closed并停止。
