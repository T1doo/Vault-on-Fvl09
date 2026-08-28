# F1–F4 implementation registry — runtime-v3_1 CPU current

当前状态：`cpu_static_hardened_v3_real_gpu_unverified`；readiness=`BLOCKED_WITH_REASONS`。

| Component | Current version | CPU status | Real GPU status |
| --- | --- | --- | --- |
| Root | `real_sapien_pilot_root_orchestrator_v1_1` | 4 P0 repairs + raw-derived prefix/suffix/divergence tests passed | not run |
| Raw | `cmf_raw_attempt_v2_1_1` / action layout v2_1 | integrity/timing/planner audit passed synthetic | not run |
| Current | `current_context_hash_v2` | model-visible/reconstruction exact + hidden-anchor semantic split tests passed | not run |
| Anchor | `physical_anchor_v2` | quaternion/velocity/sleep contracts passed | not run |
| Adapter | `RoboTwinRealSapienPilotRootAdapterV1_1` | concrete lazy-import implementation | not run |
| F1 | `f1_three_branch_coverage_v3_1` | actual-prefix/root contracts passed synthetic | not run |
| F2 | `f2_workspace_reachability_v4_1` | fresh candidates + chained qpos contracts passed | not run |
| F3 | `f3_release_dynamics_diagnosis_v3_1` | slip/transient/final contracts passed | not run; full programs incomplete |
| F4 | `f4_segmented_common_carry_v3_1` | fresh route/cleanup/carry envelope contracts passed | not run; full programs incomplete |

代码、证据和 hashes 见同名 JSON。GPU/Stage 0 均未授权。
