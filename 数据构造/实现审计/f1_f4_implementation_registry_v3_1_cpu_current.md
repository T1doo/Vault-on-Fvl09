# F1–F4 implementation registry — runtime-v3_1 CPU current

> [!warning] Superseded
> 本文件是GPU运行前的v5 CPU registry，已由`f1_f4_implementation_registry_v3_1_v5_1_current.md/json`取代。不要把下方“real GPU not run”当作当前事实；当前真实A0已执行两次并terminal blocked。

当前状态：`cpu_static_hardened_v5_a0_approval_ready_real_gpu_unverified`；Stage-0 readiness=`BLOCKED_WITH_REASONS`；A0 approval readiness=`READY_FOR_USER_REVIEW_BEFORE_A0`。

| Component | Current version | CPU status | Real GPU status |
| --- | --- | --- | --- |
| Root | `real_sapien_pilot_root_orchestrator_v1_1` | 4 P0 repairs + raw-derived prefix/suffix/divergence tests passed | not run |
| Raw | `cmf_raw_attempt_v2_1_1` / action layout v2_1 | integrity/timing/planner audit passed synthetic | not run |
| Current | `current_context_hash_v2` | model-visible/reconstruction exact + hidden-anchor semantic split tests passed | not run |
| Anchor | `physical_anchor_v2` | quaternion/velocity/sleep contracts passed | not run |
| Adapter | `RoboTwinRealSapienPilotRootAdapterV1_2` / `RoboTwinSceneContextV1_2` | post-setup monitor、timestep/camera/procedural asset/physics source 加固 | not run |
| A0 activity | `cmf_a0_activity_audit_v2` | 独立 wrapper/physics proxy、scene/phase/hash binding、install/restore fail-closed | real SAPIEN not run |
| A0 | `A0CurrentAnchorOrchestratorV1_2` | 1 pristine + 3 fresh、per-scene artifacts/hash、component diagnostics、terminal Gate | real SAPIEN not run |
| Authorization | `cmf_runtime_v3_1_gpu_authorization_v1_1` | family/seed/spec/source/budget/output/command/expiry/one-shot replay tests passed | no approved receipt |
| Guard | `cmf_gpu_guard_v2_1` | authorization/consumption/budget/GPU/PID/command binding tests passed | not run |
| F1 | `f1_three_branch_coverage_v3_1` | actual-prefix/root contracts passed synthetic | not run |
| F2 | `f2_workspace_reachability_v4_1` | fresh candidates + chained qpos contracts passed | not run |
| F3 | `f3_release_dynamics_diagnosis_v3_1` | slip/transient/final contracts passed | not run; full programs incomplete |
| F4 | `f4_segmented_common_carry_v3_1` | fresh route/cleanup/carry envelope contracts passed | not run; full programs incomplete |

代码、call-graph registry、审批请求、证据和 hashes 见同名 JSON及 `a0_post_setup_activity_entrypoint_registry_v2.*`。Active/snapshot 131/131 tests，current synthetic root 为 cpu10。A0请求仍 `approved=false`；GPU/A0/Stage 0 均未运行，Stage 0未授权。
