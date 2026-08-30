import copy
import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f2_inside_xy_tracking_compensation_v8 import (
    R6_DESIRED_PRE_RELEASE_ACTOR_POSE,
)
from controlled_multi_future.f2_inside_tracking_compensation_v7 import (
    R6_ORIGINAL_TARGETS,
)
from controlled_multi_future.family_runners_v3_3 import (
    F2ControllerV3_3,
    F3ControllerV3_3,
    F4ControllerV3_3,
    _cache_preplanned_suffix_controls,
)
from controlled_multi_future.pre_stage0_authorization_v3 import (
    APPROVED_SCOPE_REVISION_MAP,
)
from controlled_multi_future.f4_right_workspace_layout_v4 import LAYOUT
from controlled_multi_future.f4_top_down_block_carry_v8 import (
    build_f4_top_down_block_carry_v8,
)
from controlled_multi_future.f4_uniform_block_carry_midpoint_v3 import (
    F4_SEGMENTED_BLOCK_SUFFIXES,
)
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    current_source_bindings_v3_3,
)
from controlled_multi_future.runtime_v3_3_budget_v1 import budget_artifact
from controlled_multi_future.runtime_v3_3_scope_specs_v1 import (
    planned_scope_spec,
)


def _frozen_inside_route():
    return {
        "relation": "inside",
        "release_target_index": 0,
        "target_actor_pose": [
            -0.2901713007200062,
            -0.15267864896059247,
            0.8432698593315743,
            7.850462293418875e-17,
            -0.7071067811865476,
            7.850462293418875e-17,
            -0.7071067811865475,
        ],
        "pre_release_actor_pose": list(
            R6_DESIRED_PRE_RELEASE_ACTOR_POSE
        ),
        "final_target_fit": {
            "cavity_lower": [-0.07824613475799559, 0.02176539531350136, -0.07823097729682921],
            "cavity_upper": [0.07775386524200455, 0.10476539531350136, 0.07776902270317093],
            "local_corner_max": [0.04803894845225601, 0.09580738142474032, 0.03240838237479299],
            "local_corner_min": [-0.048531217968247026, 0.030723409202262464, -0.032870336968451264],
            "pass_true_cavity_obb": True,
        },
        "targets": copy.deepcopy(list(R6_ORIGINAL_TARGETS)),
        "audit": {"pass": True},
    }


class Revision8IntegrationTest(unittest.TestCase):
    def test_f2_controller_uses_one_xy_only_inside_target(self):
        controller = F2ControllerV3_3()
        route = _frozen_inside_route()
        original = copy.deepcopy(route["targets"])
        captured = {}

        def cache(_scene, **kwargs):
            captured.update(kwargs)
            return {"planner_solvable": True}

        scene = SimpleNamespace(
            can=object(),
            box=object(),
            robot=SimpleNamespace(
                left_original_pose=np.asarray(original[2]["pose"])
            ),
        )
        program = {
            "program_id": "F2-inside",
            "steps": [{"op": "grasp"}, {"relation": "inside"}],
        }
        with patch.object(controller, "_require_layout_v2"), patch(
            "controlled_multi_future.family_runners_v3_3._arm_eef_pose",
            return_value=np.asarray(original[0]["pose"]),
        ), patch(
            "controlled_multi_future.family_runners_v3_3._pose",
            return_value=np.asarray([0, 0, 0, 1, 0, 0, 0]),
        ), patch(
            "controlled_multi_future.family_runners_v3_3._actor_local_geometry_bounds",
            return_value=(np.zeros(3), np.ones(3) * 0.01),
        ), patch(
            "controlled_multi_future.family_runners_v3_3.build_inside_gravity_drop_route",
            return_value=route,
        ), patch(
            "controlled_multi_future.family_runners_v3_3._cache_suffix_controls",
            side_effect=cache,
        ):
            controller.plan_suffix_from_actual_prefix_end_state(
                scene, program, {}
            )

        targets = captured["targets"]
        self.assertNotEqual(hash_json(targets[0]), hash_json(original[0]))
        self.assertEqual(targets[1:], original[1:])
        self.assertEqual(captured["query_limit"], 24)
        receipt = captured["extra"][
            "inside_xy_tracking_compensation_v8"
        ]
        self.assertEqual(receipt["changed_target_indices"], [0])
        self.assertFalse(receipt["candidate_search"])
        self.assertFalse(receipt["fallback"])
        self.assertTrue(receipt["r7_full_se3_endpoint_abandoned"])
        self.assertEqual(
            scene._cmf_suffix_preflight_partial_receipt[
                "inside_xy_tracking_compensation_v8"
            ]["receipt_sha256"],
            receipt["receipt_sha256"],
        )

    def test_f3_open_and_recontact_use_physical_pair_classifier(self):
        source = inspect.getsource(
            F3ControllerV3_3.execute_frozen_suffix_spec
        )
        self.assertIn("classify_contact_pair_physical_hit_v8", source)
        self.assertIn("selected_finger_contact", source)
        self.assertIn(
            "no_selected_finger_physical_recontact_through_after_release_250",
            source,
        )
        self.assertIn(
            "selected_pair_presence_false_at_physical_release_audit_only",
            source,
        )

    def test_f4_full_and_staged_targets_use_top_down_v8(self):
        builder = inspect.getsource(F4ControllerV3_3._top_down_full_targets_v8)
        full = inspect.getsource(
            F4ControllerV3_3.plan_suffix_from_actual_prefix_end_state
        )
        staged = inspect.getsource(
            F4ControllerV3_3.plan_diagnostic_blocks_from_actual_prefix_end_state
        )
        self.assertIn("build_f4_top_down_block_carry_v8", builder)
        self.assertNotIn("build_uniform_tilted_f4_block_groups", builder)
        self.assertIn("_top_down_full_targets_v8", full)
        self.assertIn("_top_down_full_targets_v8", staged)

    def test_f4_staged_B_C_and_AB_slice_exact_seven_target_groups(self):
        neutral = [
            0.24287901030859585,
            -0.018903042090389933,
            0.981401726222435,
            0.5243493205275805,
            -0.4743960933174202,
            0.47440145961494534,
            0.5243561688610553,
        ]
        receipt = build_f4_top_down_block_carry_v8(
            object_poses=LAYOUT["object_poses"],
            slot_poses=LAYOUT["slot_poses"],
            neutral_pose=neutral,
            object_order=("A", "B", "C"),
            arm="right",
            layout_version=LAYOUT["layout_version"],
        )
        groups = {
            item["role"]: item
            for item in receipt["object_target_groups"]
        }
        flattened = receipt["flattened_targets"]
        for roles in (("B",), ("C",), ("A", "B")):
            selected = []
            for role in roles:
                start = groups[role]["target_start_index"]
                selected.extend(
                    flattened[
                        start : start + len(F4_SEGMENTED_BLOCK_SUFFIXES)
                    ]
                )
            self.assertEqual(
                [item["segment_id"] for item in selected],
                [
                    f"{role}_{suffix}"
                    for role in roles
                    for suffix in F4_SEGMENTED_BLOCK_SUFFIXES
                ],
            )

    def test_revision8_scope_map_budget_and_source_bindings(self):
        self.assertEqual(
            APPROVED_SCOPE_REVISION_MAP,
            {
                "F2_diagnosis_root_per_revision": {"family": "F2", "family_revision_index": 8},
                "F3_prefix_root_per_revision": {"family": "F3", "family_revision_index": 8},
                "F4_block_root_per_revision": {"family": "F4", "family_revision_index": 8},
            },
        )
        budget = budget_artifact()
        self.assertEqual(
            budget["maximum_new_implementation_revisions_per_family"], 8
        )
        self.assertFalse(budget["automatic_retry"])
        self.assertEqual(budget["recovery_attempts"], 0)
        for scope in APPROVED_SCOPE_REVISION_MAP:
            spec = planned_scope_spec(scope, revision_index=8)
            self.assertEqual(spec["implementation_revision_index"], 8)
        bindings = current_source_bindings_v3_3()
        for key in (
            "f2_inside_xy_tracking_compensation_sha256",
            "f3_physical_contact_signal_sha256",
            "f4_top_down_block_carry_sha256",
        ):
            self.assertEqual(len(bindings[key]), 64)

    def test_normal_planner_false_preserves_preflight_input_evidence(self):
        class Joint:
            def get_limits(self):
                return np.asarray([[-1.0, 1.0]], dtype=np.float64)

        extra = {
            "uniform_top_down_block_carry_contract_v8": {
                "receipt_sha256": "a" * 64,
                "pass": True,
            }
        }
        scene = SimpleNamespace(
            robot=SimpleNamespace(
                right_entity=SimpleNamespace(
                    get_active_joints=lambda: [Joint(), Joint()]
                )
            ),
            planner_queries=[{"query_id": 1, "status": "IK_FAIL"}],
        )
        result = _cache_preplanned_suffix_controls(
            scene,
            program_id="F4-DIAG-B",
            arm="right",
            targets=[
                {
                    "segment_id": "B_pregrasp",
                    "pose": [0, 0, 1, 1, 0, 0, 0],
                }
            ],
            raw_actual_qpos=np.zeros(2, dtype=np.float64),
            planner_input_qpos=np.zeros(2, dtype=np.float32),
            reset={"planner_seed": 1},
            planned={
                "pass": False,
                "terminal_qpos": [0.0, 0.0],
                "segment_receipts": [
                    {"segment_id": "B_pregrasp", "planner_status": "Fail"}
                ],
                "controls": [],
            },
            planner_query_count=1,
            extra=extra,
        )
        self.assertFalse(result["planner_solvable"])
        self.assertIsNone(result["execution_spec"])
        evidence = result["evidence"]["preflight_input_evidence"]
        self.assertEqual(evidence["extra"], extra)
        self.assertEqual(
            evidence,
            scene._cmf_suffix_preflight_partial_receipt,
        )
        digest = evidence["receipt_sha256"]
        unsigned = dict(evidence)
        unsigned.pop("receipt_sha256")
        self.assertEqual(digest, hash_json(unsigned))


if __name__ == "__main__":
    unittest.main()
