from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

import numpy as np

from controlled_multi_future.anchor import capture_anchor
from controlled_multi_future.canonical_prefix_artifact_v1 import (
    build_canonical_prefix_artifact,
    validate_canonical_prefix_artifact,
)
from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f4_candidate_equivalence_v12 import (
    audit_f4_candidate_equivalence_v12,
)
from controlled_multi_future.f4_exact_corridor_application_v11 import (
    build_f4_exact_A_corridors_v11,
)
from controlled_multi_future.f4_frozen_canonical_neutral_binding_v13 import (
    CANONICAL_SOURCE,
    audit_f4_frozen_canonical_neutral_spec_identity_v13,
    bind_f4_canonical_prefix_artifact_v13,
    bind_f4_corridor_contract_to_canonical_neutral_v13,
    build_f4_frozen_canonical_neutral_binding_from_artifacts_v13,
    build_f4_frozen_canonical_neutral_binding_v13,
    build_f4_realized_prefix_end_physical_equivalence_v13,
    validate_f4_frozen_canonical_neutral_binding_v13,
)
from controlled_multi_future.f4_right_workspace_layout_v4 import LAYOUT as F4_LAYOUT
from controlled_multi_future.family_runners_v3_3 import F4ControllerV3_3


CANONICAL_NEUTRAL = [-0.11, 0.02, 0.95, 1.0, 0.0, 0.0, 0.0]
LAYOUT_NEUTRAL = [0.02, -0.08, 0.88, 1.0, 0.0, 0.0, 0.0]


def _pose(x, y, z):
    return [x, y, z, 1.0, 0.0, 0.0, 0.0]


def _base_targets(neutral=CANONICAL_NEUTRAL):
    return [
        {"segment_id": "A_pregrasp", "pose": _pose(-0.20, 0.10, 0.91)},
        {"segment_id": "A_grasp", "pose": _pose(-0.20, 0.10, 0.86)},
        {"segment_id": "A_lift", "pose": _pose(-0.20, 0.10, 0.96)},
        {"segment_id": "A_carry_mid", "pose": _pose(0.02, 0.04, 0.96)},
        {"segment_id": "A_preplace", "pose": _pose(0.18, 0.02, 0.91)},
        {"segment_id": "A_release", "pose": _pose(0.18, 0.02, 0.86)},
        {"segment_id": "A_neutral", "pose": list(neutral)},
    ]


def _v12_contract(neutral=CANONICAL_NEUTRAL, *, base_targets=None):
    base = build_f4_exact_A_corridors_v11(
        _base_targets(neutral) if base_targets is None else base_targets
    )
    context = {
        "arm": "right",
        "scene_layout_sha256": "1" * 64,
        "layout_version": "f4_right_workspace_layout_v4",
        "release_target_semantics": "same_role_visible_slot_unchanged",
    }
    candidates = []
    for source in base["candidates"]:
        item = copy.deepcopy(source)
        item["base_v11_candidate_application_sha256"] = item[
            "candidate_application_sha256"
        ]
        item["stage0_context_binding_v12"] = context
        item["stage0_bound_candidate_sha256_v12"] = hash_json(item)
        candidates.append(item)
    contract = {
        key: copy.deepcopy(value)
        for key, value in base.items()
        if key not in ("candidates", "receipt_sha256")
    }
    contract.update(
        {
            "base_v11_receipt_sha256": base["receipt_sha256"],
            "stage0_context_binding_v12": context,
            "candidates": candidates,
            "schema_version": "cmf_f4_exact_corridor_contract_v12",
            "implementation_version": "controlled_multi_future_stage0_smoke_v1",
        }
    )
    contract["receipt_sha256"] = hash_json(contract)
    return contract


def _artifact(neutral=CANONICAL_NEUTRAL):
    prefix_contract = {
        "prefix_id": "f4_common_x_tray_withdraw_high_neutral_v5",
        "family": "F4",
        "arm": "right",
    }
    artifact = {
        "schema_version": "cmf_canonical_prefix_artifact_v1",
        "implementation_version": "controlled_multi_future_runtime_v3_3",
        "family": "F4",
        "prefix_contract": prefix_contract,
        "prefix_contract_sha256": hash_json(prefix_contract),
        "prefix_action_sha256": "2" * 64,
        "semantic_prefix_end_anchor_sha256": "3" * 64,
        "acceptance_prefix_end_anchor_sha256": "4" * 64,
        "prefix_end_tolerance_version": "cmf_prefix_end_tolerance_v1_provisional",
        "prefix_physical_acceptance": {
            "pass": True,
            "actual_open_contact_boundary_v5": {
                "target_neutral_pose": list(neutral),
                "pass": True,
            },
        },
    }
    artifact["artifact_sha256"] = hash_json(artifact)
    return artifact


def _binding_and_contract():
    contract = _v12_contract()
    artifact = _artifact()
    binding = build_f4_frozen_canonical_neutral_binding_from_artifacts_v13(
        canonical_prefix_artifact=artifact,
        corridor_contract=contract,
    )
    return (
        binding,
        bind_f4_corridor_contract_to_canonical_neutral_v13(contract, binding),
        artifact,
    )


def _real_artifact_and_arrays():
    actions = np.zeros((1, 26), dtype=np.float64)
    arrays = {
        "effective_setpoint_actions": actions,
        "requested_commands": actions.copy(),
        "component_masks": np.ones((1, 26), dtype=bool),
        "action_interval_start_timestamps": np.asarray([0.0]),
        "action_interval_end_timestamps": np.asarray([0.004]),
        "left_gripper_joint_drive_targets": np.zeros((1, 1)),
        "right_gripper_joint_drive_targets": np.zeros((1, 1)),
        "left_gripper_joint_drive_velocity_targets": np.zeros((1, 1)),
        "right_gripper_joint_drive_velocity_targets": np.zeros((1, 1)),
    }

    def anchor(value):
        return capture_anchor(
            robot_qpos=np.full(14, value, dtype=np.float64),
            robot_qvel=np.zeros(14),
            actor_poses={"common_x": [value, 0, 0, 1, 0, 0, 0]},
            gripper_state=[1, 1],
            metadata={"seed": 20260829},
        )

    artifact, normalized = build_canonical_prefix_artifact(
        root_slot_id="F4-stage0-root-A",
        family="F4",
        reference_current_sha256="a" * 64,
        reference_anchor=anchor(0),
        prefix_contract={
            "prefix_id": "f4_common_x_tray_withdraw_high_neutral_v5",
            "family": "F4",
            "arm": "right",
            "ops": ["common_X_to_tray", "branch_neutral"],
        },
        planner_seed=20260828,
        planner_query_receipts=[{"query_id": 1, "status": "Success"}],
        planner_source_hash="b" * 64,
        arrays=arrays,
        semantic_prefix_end_anchor=anchor(1),
        acceptance_prefix_end_anchor=anchor(2),
        settling_step_count=1,
        settling_policy={
            "mode": "hold_last_effective_setpoint",
            "semantic": False,
            "component_mask_policy": "all_false_no_new_control_command",
            "transition_operator": "replay_effective_setpoint_step_v1_1",
        },
        prefix_physical_acceptance={
            "pass": True,
            "actual_open_contact_boundary_v5": {
                "target_neutral_pose": list(CANONICAL_NEUTRAL),
                "pass": True,
            },
        },
        reference_trace_source={"sha256": "c" * 64, "path": "trace.npz"},
    )
    return artifact, normalized


def _case_binding_is_exact_self_hashed_and_rejects_layout_or_postprefix_source():
    binding, _, _ = _binding_and_contract()
    assert validate_f4_frozen_canonical_neutral_binding_v13(binding) == binding
    assert binding["canonical_terminal_neutral_pose"] == CANONICAL_NEUTRAL
    assert binding["canonical_terminal_neutral_source"] == CANONICAL_SOURCE
    assert binding["canonical_terminal_neutral_pose"] != LAYOUT_NEUTRAL

    kwargs = {
        "canonical_terminal_neutral_pose": CANONICAL_NEUTRAL,
        "canonical_prefix_id": "prefix",
        "canonical_prefix_contract_sha256": "1" * 64,
        "canonical_prefix_action_sha256": "2" * 64,
        "semantic_prefix_end_anchor_sha256": "3" * 64,
        "acceptance_prefix_end_anchor_sha256": "4" * 64,
        "prefix_end_tolerance_version": "physical_tolerance_v1",
    }
    for forbidden in (
        "post_prefix_common_x_pose",
        "recomputed_common_center_high",
        "layout_branch_neutral_pose",
    ):
        with unittest.TestCase().assertRaisesRegex(
            ValueError, "canonical-prefix target"
        ):
            build_f4_frozen_canonical_neutral_binding_v13(
                **kwargs, canonical_terminal_neutral_source=forbidden
            )


def _case_missing_or_mutated_binding_fails_closed():
    with unittest.TestCase().assertRaisesRegex(ValueError, "binding is missing"):
        validate_f4_frozen_canonical_neutral_binding_v13(None)
    binding, _, _ = _binding_and_contract()
    mutated = copy.deepcopy(binding)
    mutated["canonical_terminal_neutral_pose"][0] += 0.001
    with unittest.TestCase().assertRaisesRegex(ValueError, "pose hash mismatch"):
        validate_f4_frozen_canonical_neutral_binding_v13(mutated)


def _case_pristine_candidate_must_equal_prefix_physical_target_exactly():
    contract = _v12_contract()
    artifact = _artifact()
    artifact["prefix_physical_acceptance"]["actual_open_contact_boundary_v5"][
        "target_neutral_pose"
    ][0] += 1.0e-9
    artifact.pop("artifact_sha256")
    artifact["artifact_sha256"] = hash_json(artifact)
    with unittest.TestCase().assertRaisesRegex(
        ValueError, "differs from canonical-prefix target"
    ):
        build_f4_frozen_canonical_neutral_binding_from_artifacts_v13(
            canonical_prefix_artifact=artifact,
            corridor_contract=contract,
        )


def _case_common_x_postprefix_motion_cannot_change_bound_candidate_hash():
    binding, frozen_contract, _ = _binding_and_contract()
    # The binding API intentionally has no common-X actor/world-pose input.
    common_x_postprefix_pose_a = [-0.25, 0.0, 0.80]
    common_x_postprefix_pose_b = [0.23, 0.0, 0.80]
    assert common_x_postprefix_pose_a != common_x_postprefix_pose_b
    fresh_a = bind_f4_corridor_contract_to_canonical_neutral_v13(
        _v12_contract(), binding
    )
    fresh_b = bind_f4_corridor_contract_to_canonical_neutral_v13(
        _v12_contract(), binding
    )
    assert fresh_a["receipt_sha256"] == fresh_b["receipt_sha256"]
    assert [
        item["candidate_application_sha256"] for item in fresh_a["candidates"]
    ] == [
        item["candidate_application_sha256"] for item in frozen_contract["candidates"]
    ]


def _case_old_117mm_drift_reproduces_and_v13_refuses_late_repair():
    binding, frozen_contract, _ = _binding_and_contract()
    drifted = list(CANONICAL_NEUTRAL)
    drifted[0] += 0.11746700969074096
    drifted_contract = _v12_contract(drifted)
    old_audit = audit_f4_candidate_equivalence_v12(
        frozen_contract["candidates"][0], drifted_contract["candidates"][0]
    )
    assert old_audit["pass"] is False
    unittest.TestCase().assertAlmostEqual(
        old_audit["maximum_position_error_m"], 0.11746700969074096
    )
    with unittest.TestCase().assertRaisesRegex(
        ValueError, "late planner-boundary replacement"
    ):
        bind_f4_corridor_contract_to_canonical_neutral_v13(
            drifted_contract, binding
        )


def _case_first_seven_targets_unchanged_and_all_eight_match_after_reconstruction():
    binding, frozen_contract, _ = _binding_and_contract()
    reconstructed = bind_f4_corridor_contract_to_canonical_neutral_v13(
        _v12_contract(), binding
    )
    frozen = frozen_contract["candidates"][0]
    fresh = reconstructed["candidates"][0]
    assert len(frozen["applied_planner_targets"]) == 8
    assert frozen["applied_planner_targets"][:7] == fresh[
        "applied_planner_targets"
    ][:7]
    assert frozen["applied_planner_segment_ids"] == fresh[
        "applied_planner_segment_ids"
    ]
    assert frozen["applied_planner_targets"] == fresh["applied_planner_targets"]

    audit = audit_f4_frozen_canonical_neutral_spec_identity_v13(
        frozen_candidate=frozen,
        reconstructed_candidate=fresh,
        binding=binding,
    )
    assert audit["pass"] is True
    assert audit["retained_candidate_equivalence_v12"]["position_atol_m"] == 1e-5
    assert (
        audit["retained_candidate_equivalence_v12"]["orientation_atol_rad"]
        == 1e-5
    )


def _case_candidate_receipts_reference_canonical_neutral_pose_and_binding_hash():
    binding, contract, _ = _binding_and_contract()
    base = _v12_contract()
    for original, candidate in zip(base["candidates"], contract["candidates"]):
        # Preserve the truthful immutable v11/v12 candidate hashes; binding
        # references belong to the candidate audit receipt.
        assert candidate == original
        assert audit_f4_candidate_equivalence_v12(candidate, candidate)["pass"]
        receipt = audit_f4_frozen_canonical_neutral_spec_identity_v13(
            frozen_candidate=candidate,
            reconstructed_candidate=candidate,
            binding=binding,
        )
        assert receipt["canonical_terminal_neutral_pose_sha256"] == binding[
            "canonical_terminal_neutral_pose_sha256"
        ]
        assert receipt["frozen_canonical_neutral_binding_sha256"] == binding[
            "binding_sha256"
        ]


def _case_binding_is_written_into_contract_and_canonical_artifact_with_new_hashes():
    binding, contract, artifact = _binding_and_contract()
    bound_artifact = bind_f4_canonical_prefix_artifact_v13(artifact, binding)
    assert contract["schema_version"] == "cmf_f4_exact_corridor_contract_v13"
    assert contract["frozen_canonical_neutral_binding_v13"] == binding
    assert contract["canonical_terminal_neutral_pose"] == CANONICAL_NEUTRAL
    assert (
        contract["canonical_terminal_neutral_source"]
        == "canonical_prefix_target_neutral_pose"
    )
    assert contract["base_v12_receipt_sha256"] == _v12_contract()[
        "receipt_sha256"
    ]
    assert bound_artifact["f4_frozen_canonical_neutral_binding_v13"] == binding
    assert bound_artifact["canonical_terminal_neutral_pose"] == CANONICAL_NEUTRAL
    assert (
        bound_artifact["canonical_terminal_neutral_pose_sha256"]
        == binding["canonical_terminal_neutral_pose_sha256"]
    )
    assert bound_artifact["artifact_sha256"] != artifact["artifact_sha256"]


def _case_bound_real_canonical_artifact_remains_validator_clean():
    artifact, arrays = _real_artifact_and_arrays()
    contract = _v12_contract()
    binding = build_f4_frozen_canonical_neutral_binding_from_artifacts_v13(
        canonical_prefix_artifact=artifact,
        corridor_contract=contract,
    )
    bound = bind_f4_canonical_prefix_artifact_v13(artifact, binding)
    validated, normalized = validate_canonical_prefix_artifact(bound, arrays)
    assert validated["artifact_sha256"] == bound["artifact_sha256"]
    np.testing.assert_array_equal(
        normalized["effective_setpoint_actions"],
        arrays["effective_setpoint_actions"],
    )


def _case_realized_prefix_end_uses_anchor_tolerance_not_candidate_1e5_tolerance():
    binding, _, _ = _binding_and_contract()
    replay = {
        "prefix_end_equivalent": True,
        "semantic_prefix_end_equivalence": {
            "equivalent": True,
            "reference_sha256": binding["semantic_prefix_end_anchor_sha256"],
            "candidate_sha256": "5" * 64,
        },
        "acceptance_prefix_end_equivalence": {
            "equivalent": True,
            "reference_sha256": binding[
                "acceptance_prefix_end_anchor_sha256"
            ],
            "candidate_sha256": "6" * 64,
        },
    }
    receipt = build_f4_realized_prefix_end_physical_equivalence_v13(
        replay=replay, binding=binding
    )
    assert receipt["pass"] is True
    assert receipt["candidate_spec_position_atol_m"] is None
    assert receipt["candidate_spec_orientation_atol_rad"] is None
    assert receipt["prefix_end_tolerance_version"] == binding[
        "prefix_end_tolerance_version"
    ]

    failed = copy.deepcopy(replay)
    failed["semantic_prefix_end_equivalence"]["equivalent"] = False
    failed["prefix_end_equivalent"] = False
    assert (
        build_f4_realized_prefix_end_physical_equivalence_v13(
            replay=failed, binding=binding
        )["pass"]
        is False
    )


class TestF4FrozenCanonicalNeutralV13(unittest.TestCase):
    def test_binding_is_exact_self_hashed_and_rejects_fallback(self):
        _case_binding_is_exact_self_hashed_and_rejects_layout_or_postprefix_source()

    def test_missing_or_mutated_binding_fails_closed(self):
        _case_missing_or_mutated_binding_fails_closed()

    def test_pristine_candidate_equals_prefix_target_exactly(self):
        _case_pristine_candidate_must_equal_prefix_physical_target_exactly()

    def test_postprefix_common_x_motion_does_not_change_hash(self):
        _case_common_x_postprefix_motion_cannot_change_bound_candidate_hash()

    def test_old_drift_reproduces_and_late_repair_is_refused(self):
        _case_old_117mm_drift_reproduces_and_v13_refuses_late_repair()

    def test_first_seven_unchanged_and_all_eight_match(self):
        _case_first_seven_targets_unchanged_and_all_eight_match_after_reconstruction()

    def test_sub_tolerance_non_neutral_spec_drift_still_fails_exact_identity(self):
        binding, frozen_contract, _ = _binding_and_contract()
        frozen = frozen_contract["candidates"][0]
        changed_base = _base_targets()
        changed_base[0]["pose"][0] += 1.0e-6
        changed = bind_f4_corridor_contract_to_canonical_neutral_v13(
            _v12_contract(base_targets=changed_base), binding
        )["candidates"][0]
        retained = audit_f4_candidate_equivalence_v12(frozen, changed)
        self.assertTrue(retained["pass"])
        identity = audit_f4_frozen_canonical_neutral_spec_identity_v13(
            frozen_candidate=frozen,
            reconstructed_candidate=changed,
            binding=binding,
        )
        self.assertFalse(identity["checks"]["all_applied_target_specs_exact"])
        self.assertFalse(identity["pass"])

    def test_candidate_receipts_reference_binding(self):
        _case_candidate_receipts_reference_canonical_neutral_pose_and_binding_hash()

    def test_binding_written_into_contract_and_artifact(self):
        _case_binding_is_written_into_contract_and_canonical_artifact_with_new_hashes()

    def test_bound_real_artifact_remains_validator_clean(self):
        _case_bound_real_canonical_artifact_remains_validator_clean()

    def test_realized_prefix_uses_physical_anchor_tolerance(self):
        _case_realized_prefix_end_uses_anchor_tolerance_not_candidate_1e5_tolerance()

    def test_controller_overrides_neutral_before_v11_hash_construction(self):
        binding, _bound_contract, _artifact_value = _binding_and_contract()
        drifted = [0.21, -0.13, 1.01, 1.0, 0.0, 0.0, 0.0]
        common = [
            {"segment_id": f"common_{index}", "pose": _pose(0.0, 0.0, 0.9)}
            for index in range(F4ControllerV3_3.COMMON_SEGMENT_COUNT)
        ]
        a_targets = _base_targets(drifted)
        extra = {
            "object_target_groups": [
                {
                    "role": "A",
                    "target_start_index": 0,
                    "targets": copy.deepcopy(a_targets),
                }
            ]
        }

        class Scene:
            _cmf_planned_root_slot_spec = {
                "arm": "right",
                "scope": "F4_candidate_hash_infra_v13",
                "generator": "controlled_multi_future_stage0_smoke_v1_1_adapter_v1_7",
                "scene_layout": copy.deepcopy(F4_LAYOUT),
                "scene_layout_sha256": hash_json(F4_LAYOUT),
            }

        controller = F4ControllerV3_3()
        with patch.object(
            controller,
            "_top_down_full_targets_v8",
            return_value=(common + a_targets, extra),
        ):
            reconstructed = controller.build_exact_a_corridor_contract_v13(
                Scene(), binding
            )
        frozen = bind_f4_corridor_contract_to_canonical_neutral_v13(
            controller._wrap_exact_a_corridor_contract_v12(
                build_f4_exact_A_corridors_v11(_base_targets()),
                Scene._cmf_planned_root_slot_spec,
            ),
            binding,
        )
        self.assertEqual(
            [item["candidate_application_sha256"] for item in reconstructed["candidates"]],
            [item["candidate_application_sha256"] for item in frozen["candidates"]],
        )
        for candidate in reconstructed["candidates"]:
            self.assertEqual(
                candidate["applied_planner_targets"][-1]["pose"],
                CANONICAL_NEUTRAL,
            )


if __name__ == "__main__":
    unittest.main()
