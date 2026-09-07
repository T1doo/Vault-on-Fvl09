"""Locked original F3 post-8cm tail, private-global bound by controller.py."""
def original_tail(scene,start,post_close,post_close_transform,qualified,frozen_grasp,target_construction_audit,prefix_planner_reset):
    post_lift = len(scene.trace) - 1 - start
    post_lift_transform = relative_pose(
        _arm_eef_pose(scene, "left"), _pose(scene.bottle)
    )
    post_lift_eef = _arm_eef_pose(scene, "left")
    bottle_corners = obb_corners(
        _actor_geometry_center_pose(scene.bottle),
        _actor_half_extents(scene.bottle),
    )
    gripper_evidence = _gripper_below_eef_envelope(scene, arm="left")
    clearance_audit = build_f3_clearance_height_audit(
        table_top_z_m=0.74 + float(scene.table_z_bias),
        pad_top_z_m=float(
            _pose(scene.pad)[2] + F3_PAD_HALF_EXTENTS_M[2]
        ),
        post_lift_eef_z_m=float(post_lift_eef[2]),
        bottle_below_eef_m=float(
            post_lift_eef[2] - np.min(bottle_corners[:, 2])
        ),
        gripper_below_eef_m=gripper_evidence[
            "gripper_below_eef_envelope_m"
        ],
    )
    if clearance_audit["pass"] is not True:
        raise RuntimeError("F3 held-envelope clearance audit failed")
    grasp_contract_sha256 = (
        qualified["contract_sha256"]
        if qualified is not None
        else frozen_grasp["contract_sha256"]
    )
    carry_route = build_f3_clearance_route_targets(
        post_lift_eef,
        clearance_audit,
        grasp_contract_sha256=grasp_contract_sha256,
    )
    if carry_route["pass"] is not True:
        raise RuntimeError("F3 clearance carry route audit failed")
    carry_planned = _plan_chain(
        scene, carry_route["segments"], query_limit=32, arm="left"
    )
    if carry_planned["pass"] is not True or len(carry_planned["controls"]) != 2:
        raise RuntimeError("F3 clearance carry planner failed")
    _execute_control(
        scene,
        carry_planned["controls"][0],
        carry_route["segments"][0]["segment_id"],
        arm="left",
    )
    post_clearance_raise = len(scene.trace) - 1 - start
    post_clearance_transform = relative_pose(
        _arm_eef_pose(scene, "left"), _pose(scene.bottle)
    )
    dilated_center_control = time_dilate_f3_carry_control_2x(
        carry_planned["controls"][1]
    )
    _execute_control(
        scene,
        dilated_center_control,
        carry_route["segments"][1]["segment_id"],
        arm="left",
    )
    post_center_high = len(scene.trace) - 1 - start
    post_center_transform = relative_pose(
        _arm_eef_pose(scene, "left"), _pose(scene.bottle)
    )
    _wait_and_record(scene, F3_CENTRAL_HOLD_STEPS)
    pre_shared_v = len(scene.trace) - 1 - start
    pre_shared_v_transform = relative_pose(
        _arm_eef_pose(scene, "left"), _pose(scene.bottle)
    )
    pre_v_rows = scene.trace[-F3_CENTRAL_HOLD_STEPS:]
    pre_v_transforms = {
        "post_close": post_close_transform,
        "post_lift": post_lift_transform,
        "post_clearance_raise": post_clearance_transform,
        "post_center_high": post_center_transform,
        "pre_shared_V": pre_shared_v_transform,
    }
    pre_v_gate = build_f3_pre_v_evidence_v4(
        hold_rows=pre_v_rows,
        boundary_transforms=pre_v_transforms,
        thresholds={
            "eef_linear_speed_mps": PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_linear_speed_mps"
            ],
            "eef_angular_speed_rps": PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ],
            "bottle_linear_speed_mps": PROVISIONAL_RUNTIME_THRESHOLDS[
                "stable_linear_speed_mps"
            ],
            "bottle_angular_speed_rps": PROVISIONAL_RUNTIME_THRESHOLDS[
                "eef_stationary_angular_speed_rps"
            ],
            "grasp_translation_drift_m": 0.005,
            "grasp_orientation_drift_rad": 0.05,
        },
        expected_actor_name=_entity(scene.bottle).get_name(),
        selected_gripper_link_names=gripper_evidence[
            "selected_gripper_links"
        ],
        support_actor_names=("table", _entity(scene.pad).get_name()),
        planner_metadata={
            "planner_query_count_at_pre_v": int(
                getattr(scene, "planner_query_count", 0)
            ),
            "target_construction_planner_audit": target_construction_audit,
            "prefix_planner_reset_receipt": prefix_planner_reset,
            "clearance_carry_segment_receipts": carry_planned[
                "segment_receipts"
            ],
        },
        route_metadata={
            "clearance_height_audit": clearance_audit,
            "clearance_carry_route": carry_route,
            "center_carry_time_dilation": dilated_center_control[
                "_cmf_time_dilation"
            ],
        },
    )
    try:
        pre_v_gate = require_f3_pre_v_gate(pre_v_gate)
    except F3PreVBoundaryGateFailure as exc:
        scene._cmf_prefix_failure_receipt = exc.to_receipt()
        raise
    central = np.asarray(carry_route["segments"][1]["pose"], dtype=np.float64)
    v_start = len(scene.trace) - 1 - start
    shared_v_targets = _time_dilated_closed_loop_event_targets(
        central,
        axis="V",
        amplitude_m=F3_V_NOMINAL_AMPLITUDE_M_V3_3,
        segment_prefix="f3_shared_V",
    )
    scene.mark("event_0_V_start")
    for target in shared_v_targets:
        _move_left(scene, target["pose"], target["segment_id"])
        _wait_and_record(
            scene, F3_EVENT_ENDPOINT_HOLD_STEPS_V3_3_REV2
        )
    scene.mark("event_0_V_end")
    v_end = len(scene.trace) - 1 - start
    post_shared = v_end
    post_shared_transform = relative_pose(
        _arm_eef_pose(scene, "left"), _pose(scene.bottle)
    )
    event_rows = scene.trace[start + v_start : start + 1 + v_end]
    first_v_metrics = _realized_event_metrics(event_rows, axis="V")
    semantic_end = len(scene.trace) - 1
    semantic_anchor = capture_anchor(scene)
    settling = int(PROVISIONAL_RUNTIME_THRESHOLDS["stable_window_frames"])
    _settle_prefix_with_replay_operator(scene, settling)
    acceptance_anchor = capture_anchor(scene)
    acceptance_transform = relative_pose(
        _arm_eef_pose(scene, "left"), _pose(scene.bottle)
    )
    boundary_transforms = {
        "post_close": post_close_transform,
        "post_lift": post_lift_transform,
        "post_clearance_raise": post_clearance_transform,
        "post_center_high": post_center_transform,
        "pre_shared_V": pre_shared_v_transform,
        "post_shared_V": post_shared_transform,
        "acceptance_end": acceptance_transform,
    }
    boundary_audit = audit_f3_grasp_boundary_stability(boundary_transforms)
    grasp_translation_drift = boundary_audit["maximum_translation_drift_m"]
    grasp_orientation_drift = boundary_audit[
        "maximum_orientation_drift_rad"
    ]
    shared_v_gate = verify_realized_motion_metrics(
        {"event_0_V": first_v_metrics}, PROVISIONAL_RUNTIME_THRESHOLDS
    )
    shared_v_contact_audit = audit_f3_free_space_event_contacts(
        [row["contact_pairs"] for row in event_rows],
        bottle_actor_name=_entity(scene.bottle).get_name(),
        selected_gripper_link_names=gripper_evidence[
            "selected_gripper_links"
        ],
        support_actor_names=("table", _entity(scene.pad).get_name()),
    )
    prefix_acceptance = _prefix_physical_acceptance(
        scene,
        roles=("bottle",),
        require_selected_contact=True,
        expected_contact_actor_name=_entity(scene.bottle).get_name(),
        extra_checks={
            "shared_first_v_realized_motion": shared_v_gate["pass"],
            "grasp_transform_translation_stable": boundary_audit["checks"]
            ["all_translation_boundaries_stable"],
            "grasp_transform_orientation_stable": boundary_audit["checks"]
            ["all_orientation_boundaries_stable"],
            "shared_v_free_space_support_contact": shared_v_contact_audit[
                "pass"
            ],
            "pre_shared_v_boundary_gate": pre_v_gate["pass"],
        },
    )
    prefix_acceptance.update(
        {
            "shared_first_v_metrics": first_v_metrics,
            "shared_first_v_gate": shared_v_gate,
            "grasp_transform_translation_drift_m": grasp_translation_drift,
            "grasp_transform_orientation_drift_rad": grasp_orientation_drift,
            "grasp_boundary_stability_audit": boundary_audit,
            "shared_v_free_space_contact_audit": shared_v_contact_audit,
            "clearance_height_audit": clearance_audit,
            "clearance_carry_route": carry_route,
            "pre_shared_v_boundary_gate": pre_v_gate,
            "selected_gripper_envelope_evidence": gripper_evidence,
            "boundary_grasp_transforms": {
                name: value.tolist()
                for name, value in boundary_transforms.items()
            },
        }
    )
    return _prefix_reference_result(
        scene,
        start_action=start,
        semantic_end_action=semantic_end,
        semantic_end_anchor=semantic_anchor,
        acceptance_end_anchor=acceptance_anchor,
        settling_steps=settling,
        extra={
            "reference_event_boundaries": {
                "post_close": post_close,
                "post_lift": post_lift,
                "post_clearance_raise": post_clearance_raise,
                "post_center_high": post_center_high,
                "pre_shared_V": pre_shared_v,
                "shared_first_v_start": v_start,
                "shared_first_v_end": v_end,
                "post_shared_V": post_shared,
            },
            "reference_shared_first_v_metrics": first_v_metrics,
            "closed_loop_primitive_version": F3_CLOSED_LOOP_PRIMITIVE_VERSION,
            "event_endpoint_hold_steps": F3_EVENT_ENDPOINT_HOLD_STEPS_V3_3_REV2,
            "central_hold_steps": F3_CENTRAL_HOLD_STEPS,
            "clearance_height_audit": clearance_audit,
            "clearance_carry_route": carry_route,
            "pre_shared_v_boundary_gate": pre_v_gate,
            "clearance_carry_segment_receipts": carry_planned[
                "segment_receipts"
            ],
            "center_carry_time_dilation": dilated_center_control[
                "_cmf_time_dilation"
            ],
            "shared_v_target_count": len(shared_v_targets),
            "target_construction_planner_audit": target_construction_audit,
            "prefix_planner_reset_receipt": prefix_planner_reset,
            "prefix_physical_acceptance": prefix_acceptance,
        },
    )
