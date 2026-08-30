import copy
import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f2_inside_tracking_compensation_v7 import (
    R6_DESIRED_PRE_RELEASE_ACTOR_POSE,
    R6_ORIGINAL_TARGETS,
)
from controlled_multi_future.family_runners_v3_3 import (
    F2ControllerV3_3,
    F4ControllerV3_3,
)
from controlled_multi_future.pre_stage0_authorization_v3 import (
    APPROVED_SCOPE_REVISION_MAP,
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
            "cavity_lower": [
                -0.07824613475799559,
                0.02176539531350136,
                -0.07823097729682921,
            ],
            "cavity_upper": [
                0.07775386524200455,
                0.10476539531350136,
                0.07776902270317093,
            ],
            "local_corner_max": [
                0.04803894845225601,
                0.09580738142474032,
                0.03240838237479299,
            ],
            "local_corner_min": [
                -0.048531217968247026,
                0.030723409202262464,
                -0.032870336968451264,
            ],
            "pass_true_cavity_obb": True,
        },
        "targets": copy.deepcopy(list(R6_ORIGINAL_TARGETS)),
        "audit": {"pass": True},
    }


class Revision7IntegrationTest(unittest.TestCase):
    def test_f2_controller_changes_only_inside_first_command(self):
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
                left_original_pose=np.asarray(
                    original[2]["pose"], dtype=np.float64
                )
            ),
        )
        program = {
            "program_id": "F2-inside",
            "steps": [{"op": "grasp"}, {"relation": "inside"}],
        }
        with patch.object(controller, "_require_layout_v2"), patch(
            "controlled_multi_future.family_runners_v3_3._arm_eef_pose",
            return_value=np.asarray(original[0]["pose"], dtype=np.float64),
        ), patch(
            "controlled_multi_future.family_runners_v3_3._pose",
            return_value=np.asarray([0, 0, 0, 1, 0, 0, 0], dtype=np.float64),
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
        self.assertEqual(targets[1], original[1])
        self.assertEqual(targets[2], original[2])
        self.assertEqual(captured["query_limit"], 24)
        receipt = captured["extra"]["inside_tracking_compensation_v7"]
        self.assertEqual(receipt["changed_target_indices"], [0])
        self.assertFalse(receipt["hard_alignment_gate_added"])
        self.assertFalse(receipt["verifier_threshold_changed"])
        self.assertEqual(
            captured["extra"]["inside_gravity_drop_route"], route
        )

    def test_f4_runner_uses_role_pose_wrapper_not_primary_actor_pose(self):
        source = inspect.getsource(
            F4ControllerV3_3.execute_a_micro_lift_diagnostic
        )
        self.assertIn(
            "build_a_role_pose_micro_lift_gate_receipt_v7", source
        )
        self.assertIn(
            "build_a_role_pose_micro_lift_rows_v7", source
        )
        self.assertIn("_cmf_f4_micro_lift_role_input_v7", source)
        self.assertIn("trace_rows=micro_trace_rows", source)
        self.assertIn("source_trace_indices=source_indices.tolist()", source)
        self.assertIn("micro_lift_role_pose_gate_v7", source)
        self.assertNotIn(
            '"actor_pose": np.asarray(\n                        row["actor_pose"]',
            source,
        )

    def test_revision7_scope_map_and_budget_remain_finite(self):
        self.assertEqual(
            APPROVED_SCOPE_REVISION_MAP,
            {
                "F2_diagnosis_root_per_revision": {
                    "family": "F2",
                    "family_revision_index": 7,
                },
                "F3_prefix_root_per_revision": {
                    "family": "F3",
                    "family_revision_index": 7,
                },
                "F4_micro_lift_diagnosis_per_revision": {
                    "family": "F4",
                    "family_revision_index": 7,
                },
            },
        )
        budget = budget_artifact()
        self.assertEqual(
            budget["maximum_new_implementation_revisions_per_family"], 7
        )
        self.assertFalse(budget["automatic_retry"])
        self.assertEqual(budget["recovery_attempts"], 0)
        for scope in APPROVED_SCOPE_REVISION_MAP:
            spec = planned_scope_spec(scope, revision_index=7)
            self.assertEqual(spec["implementation_revision_index"], 7)
            self.assertEqual(
                spec["maximum_full_root_execution_per_revision"], 1
            )


if __name__ == "__main__":
    unittest.main()
