import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.family_runners_v3_3 import F3ControllerV3_3


PROGRAM_AXES = ("VVHH", "VHVH", "VHHV")
ACTOR_POSE = [0.0, 0.0, 0.80, 1.0, 0.0, 0.0, 0.0]
EEF_POSE = [0.0, 0.0, 1.00, 1.0, 0.0, 0.0, 0.0]
PAD_POSE = [0.0, 0.0, 0.745, 1.0, 0.0, 0.0, 0.0]
ASSEMBLY_LINK_POSES = {
    "fl_link6": [0.0, 0.0, 0.90, 1.0, 0.0, 0.0, 0.0],
    "fl_link7": [0.03, 0.0, 0.92, 1.0, 0.0, 0.0, 0.0],
    "fl_link8": [-0.03, 0.0, 0.92, 1.0, 0.0, 0.0, 0.0],
}


def program(axes):
    return {
        "program_id": f"F3-{axes}",
        "steps": [
            {"op": "oscillate", "axis": axis} for axis in axes
        ],
    }


class F3Revision7SuffixWiringTest(unittest.TestCase):
    def test_all_programs_wire_projection_to_clearance_before_planner(self):
        controller = F3ControllerV3_3()
        bottle = object()
        pad = object()
        scene = SimpleNamespace(
            bottle=bottle,
            pad=pad,
            table_z_bias=0.0,
            robot=SimpleNamespace(
                left_original_pose=np.asarray(EEF_POSE, dtype=np.float64)
            ),
        )
        replay = {
            "start_anchor": {
                "actor_states": {"bottle": {"pose": ACTOR_POSE}}
            }
        }
        captured = []

        def pose(actor):
            if actor is bottle:
                return np.asarray(ACTOR_POSE, dtype=np.float64)
            if actor is pad:
                return np.asarray(PAD_POSE, dtype=np.float64)
            raise AssertionError("unexpected actor")

        def cache_stub(_scene, **kwargs):
            captured.append(kwargs)
            return {"program_id": kwargs["program_id"], "sentinel": True}

        with patch(
            "controlled_multi_future.family_runners_v3_3._arm_eef_pose",
            return_value=np.asarray(EEF_POSE, dtype=np.float64),
        ), patch(
            "controlled_multi_future.family_runners_v3_3._pose",
            side_effect=pose,
        ), patch(
            "controlled_multi_future.family_runners_v3_3._f3_full_assembly_link_poses",
            return_value=ASSEMBLY_LINK_POSES,
        ), patch(
            "controlled_multi_future.family_runners_v3_3._cache_suffix_controls",
            side_effect=cache_stub,
        ):
            for axes in PROGRAM_AXES:
                result = controller.plan_suffix_from_actual_prefix_end_state(
                    scene, program(axes), replay
                )
                self.assertTrue(result["sentinel"])

        self.assertEqual(len(captured), 3)
        clearance_hashes = set()
        for axes, call in zip(PROGRAM_AXES, captured):
            self.assertEqual(call["program_id"], f"F3-{axes}")
            self.assertEqual(call["arm"], "left")
            self.assertEqual(call["query_limit"], 42)
            self.assertEqual(
                [item["segment_id"] for item in call["targets"][-4:]],
                [
                    "f3_return_preplace",
                    "f3_return_release",
                    "f3_return_retreat",
                    "f3_rest",
                ],
            )
            projection = call["extra"][
                "release_full_assembly_projection_v6"
            ]
            clearance = call["extra"]["release_geometry_clearance_v6"]
            self.assertEqual(
                projection["gripper_assembly_below_eef_m"],
                clearance["gripper_assembly_below_eef_m"],
            )
            self.assertNotIn("gripper_below_eef_envelope_m", projection)
            self.assertEqual(
                clearance["scientific_invariants"]["programs"],
                list(PROGRAM_AXES),
            )
            self.assertFalse(
                clearance["scientific_invariants"]["v_h_targets_changed"]
            )
            clearance_hashes.add(clearance["receipt_sha256"])
        self.assertEqual(len(clearance_hashes), 1)

        partial = scene._cmf_suffix_preflight_partial_receipt
        digest = partial["receipt_sha256"]
        unsigned = dict(partial)
        unsigned.pop("receipt_sha256")
        self.assertEqual(digest, hash_json(unsigned))
        self.assertEqual(partial["phase"], "f3_release_planner_input_frozen")
        self.assertEqual(partial["query_limit"], 42)
        self.assertEqual(
            partial["assembly_below_eef_m"],
            partial["release_full_assembly_projection_v6"][
                "gripper_assembly_below_eef_m"
            ],
        )

    def test_f3_release_projection_consumer_does_not_use_the_old_key(self):
        source = inspect.getsource(
            F3ControllerV3_3.plan_suffix_from_actual_prefix_end_state
        )
        self.assertNotIn(
            'release_full_assembly_projection[\n                "gripper_below_eef_envelope_m"',
            source,
        )
        self.assertIn(
            'release_full_assembly_projection[\n                "gripper_assembly_below_eef_m"',
            source,
        )


if __name__ == "__main__":
    unittest.main()
