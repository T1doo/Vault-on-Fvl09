# External review decision after Post-Gate V2 execution V1

日期：2026-09-04

来源：用户提供的 ChatGPT shared review：`https://chatgpt.com/s/t_6a99be65e8688191b469cb9cb06f907b`

绑定输入：

- Vault HEAD before decision receipt: `0faba46e33fd4e59c5da2563e9a3dcfcde74466c`
- Review request SHA-256: `594907dd064bc7411c33b0c30291ad3e6981c39a27327d45f77e6659d6a14fdc`
- Machine review packet SHA-256: `fc0e3c255e2ff17b47c7420eccab60e90762fd207947194e88e923f020e4be9c`
- F3 wiring overlay SHA-256: `586384db1676c3a4ec1cfa78f90f5de624059640da34e2c4707c6681dd9b9347`

## Authoritative decision transcription

```yaml
f2:
  decision: REVISE
  exact_scope_if_revised:
    gate_name: F2_PLANNER_ONLY_CONTROLLED_INSERTION_ROUTE_GATE_V1

    rationale: >-
      The proposed Gate retains inside_drop_release_10cm and the gravity-drop
      inside route. Replace it with a top-contact adaptation of controlled
      insertion V2 before any further F2 root execution.

    immutable_inputs:
      reuse_sealed_actual_prefix_end_qpos: true
      reuse_sealed_prefix_end_eef_pose: true
      reuse_sealed_prefix_end_actor_pose: true
      reuse_sealed_actual_eef_to_actor_transform: true

      selected_candidate:
        main_object_model_id: 0
        plastic_box_model_id: 2
        arm: left
        official_contact_point_id: 8
        official_rotation_candidate_index: 0
        recipe_id: f2-final-grasp-v2-r000725

      same_current_anchor_prefix_binding_unchanged: true
      scene_layout_asset_threshold_verifier_changes_allowed: false

    inside:
      semantics: controlled_insertion_v2_top_contact_adaptation
      primary_10cm_gravity_drop: false
      open_gripper_during_planner_gate: false

      target_derivation:
        target_actor_pose: frozen_strict_cavity_target_from_selected_binding
        supported_eef_pose: >-
          actor_target_to_eef_pose(
            sealed_prefix_end_eef_pose,
            sealed_prefix_end_actor_pose,
            target_actor_pose
          )
        preinsert_eef_pose: >-
          supported_eef_pose translated 0.030 m outward along the frozen
          runtime opening_normal_world
        high_carry_eef_pose: >-
          same x, y and orientation as preinsert_eef_pose, with world-z equal
          to max(sealed_prefix_end_eef_pose.z, preinsert_eef_pose.z)

      ordered_targets:
        - inside_controlled_high_carry
        - f2_v2_preinsert_30mm
        - f2_v2_controlled_descend_to_support
        - f2_v2_retreat_to_preinsert
        - f2_v2_neutral

      planner_query_cap: 5

      future_physical_contract_not_authorized_by_this_gate:
        support_stability_before_open_frames: 50
        slow_release_normalized_targets: [0.2, 0.4, 0.6, 0.8, 1.0]
        post_release_settle_frames: 250
        final_strict_inside_required: true

    beside:
      frozen_layout_candidate_index: 2
      target_xy_m: [0.08000000000000002, 0.07]
      unchanged_six_segment_route: true
      planner_query_cap: 6

    aggregate_caps:
      planner_query_cap: 11
      fresh_planner_scene_cap: 2
      physical_execution_cap: 0
      branch_execution_cap: 0
      raw_trajectory_cap: 0
      video_cap: 0
      accepted_root_cap: 0
      formal_trajectory_cap: 0

    execution_rule: >-
      Run the inside five-target chain once and the beside six-target chain
      once from the sealed actual prefix-end qpos. No fallback, target search,
      physical action, root retry, or automatic continuation.

    stop_condition: >-
      Seal both one-pass planner results. Any implementation, binding,
      accounting or planner failure terminates this Gate. Even if both chains
      pass, a separate external review is required before root execution.

f3:
  decision: REISSUE_ZERO_SCENE_WIRING_ONCE
  exact_scope_if_revised: null

f4: CLOSED_NO_REOPEN_REQUESTED

stage0_rerun: false
stage1: false
formal_360: false
training: false
h_reveal: false
compression: false
pi_0_5: false
```

F3 reissue additional binding transcribed from the review:

- keep the existing `r0005` qualification without replanning it;
- new tuples remain only `r1505 / r2180 / r3677`;
- caps remain `30 planner queries / 6 planner scenes / 4 physical candidates / conditional 3 fresh no-suffix scenes / 0 formal`;
- exactly one reissue; no fallback tuple and no second reissue;
- the reissue is bound to overlay SHA-256 `586384db1676c3a4ec1cfa78f90f5de624059640da34e2c4707c6681dd9b9347`.

## Scope interpretation

- F2 authorizes only the revised 11-query planner-only Gate. It does not authorize physical execution, a root retry, raw/video generation, or automatic continuation after a pass.
- F3 authorizes exactly one hash-bound reissue of the zero-scene-failed job under the old bounded budgets and stop rules.
- F4 remains permanently closed. No third reopen is requested or permitted.
- Stage 0 rerun, Stage 1, formal 360, training, H-reveal, compression, and pi0.5 remain prohibited.
