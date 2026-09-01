# Stage 0 v1.2 seal 与统一 Stage 1 readiness

## STAGE0_COMPLETED_WITH_FAILURE_EVIDENCE

Stage 0 authoritative seal保持不变，禁止重跑或覆盖。Development pipeline consolidation V1已终端为`COMPLETED_WITH_BOUNDED_SEARCH_EXHAUSTION`。

```yaml
F1:
  stage0_status: PASS
  development_status: PASS
  stage1_candidate_ready: true
  evidence: 5/5 roots, 15/15 trajectories, 15 raw, 15 MP4, 15 verifier pass
  template_redesign: false

F2:
  stage0_replacement:
    inside: FAILED_EXECUTION_WITH_EVIDENCE
    on: PASSED
    beside: PASSED
  development_status: ALL_12_DYNAMIC_CANDIDATES_EXHAUSTED
  evaluated_ranks: 50-61
  selected_binding: null
  passing_three_branch_root: false
  stage1_candidate_ready: false
  next_design_state: higher_level_asset_layout_redesign_required

F3:
  stage0_status: FAILED_EXECUTION_WITH_EVIDENCE
  planner_screen: 12/12 pass
  physical_candidates: r01-r04 evaluated
  stable_grasp: null
  three_scene_confirmation_run: false
  vvhh_vhvh_vhhv_root_formed: false
  development_status: BOUNDED_GRASP_SEARCH_EXHAUSTED_REQUIRES_ASSET_REDESIGN
  stage1_candidate_ready: false

F4:
  stage0_status: FAILED_PLANNER_WITH_EVIDENCE
  evaluated_layouts: c01-c06
  observed_rendered_visibility: pass
  common_failure: ABC/A_pregrasp chained planner failure
  selected_template: null
  a_only_run: false
  abc_acb_bac_root_formed: false
  development_status: BOUNDED_LAYOUT_SEARCH_EXHAUSTED_REQUIRES_HIGHER_LEVEL_LAYOUT_REDESIGN
  stage1_candidate_ready: false

canonical_stage1_authorized: false
formal_360_authorized: false
training_authorized: false
h_reveal_authorized: false
compression_authorized: false
pi05_authorized: false
formal_root_increment: 0
formal_trajectory_increment: 0
```

只有F1达到family-level Stage 1 candidate readiness；四family统一Stage 1不ready且未授权。Machine readiness=`STAGE1_READINESS_AFTER_DEVELOPMENT_CONSOLIDATION_V1.json`，最终集中报告=`DEVELOPMENT_PIPELINE_CONSOLIDATION_AND_TEMPLATE_CONVERGENCE_V1_REPORT.md/json`。
