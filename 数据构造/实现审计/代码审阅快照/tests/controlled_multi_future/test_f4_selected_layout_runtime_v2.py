import inspect
import unittest
from unittest.mock import Mock

import numpy as np

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f4_derivation_interface_v2 import (
    validate_f4_derivation_interface_v2,
)
from controlled_multi_future.f4_exact_corridor_application_v11 import (
    build_f4_exact_A_corridors_v11,
    derive_role_corridor_v11,
)
from controlled_multi_future.f4_layout_candidate_search_v2 import (
    IMPLEMENTATION_VERSION,
    SELECTED_EXISTING_CORRIDOR_ID,
    build_selected_layout_base_targets_v2,
    validate_selected_layout_runtime_binding_v2,
)
from controlled_multi_future.f4_post_stage0_planner_only_v1 import (
    F4PostStage0PlannerOnlyV1,
)
from controlled_multi_future.f4_selected_layout_scope_v2 import budget, spec
from controlled_multi_future.family_runners_v3_3 import F4ControllerV3_3
from controlled_multi_future.probes.f4_selected_layout_authorization_v2 import (
    AUTH_ID,
    CONSUMPTION_SCHEMA,
    consumption_sha,
    validate as validate_authorization,
    validate_consumption,
)
from controlled_multi_future.probes.f4_selected_layout_scope_runner_v2 import (
    _budget as validate_budget,
)
from controlled_multi_future.probes.runtime_v3_3_authorization_v1 import (
    AuthorizationBindingError,
)
from controlled_multi_future.real_sapien_adapter_f4_selected_layout_v2 import (
    RoboTwinRealSapienF4SelectedLayoutV2Adapter,
)
from controlled_multi_future.real_sapien_adapter_post_stage0_f4_v1 import (
    IMPLEMENTATION_VERSION as OLD_IMPLEMENTATION_VERSION,
)


class _Entity:
    def __init__(self, name, identifier):
        self.name = name
        self.identifier = identifier

    def get_name(self):
        return self.name

    def get_per_scene_id(self):
        return self.identifier


class _Camera:
    def __init__(self, actor_plane):
        self.labels = np.zeros((*actor_plane.shape, 4), dtype=np.uint32)
        self.labels[..., 1] = actor_plane

    def get_picture(self, name):
        if name != "Segmentation":
            raise AssertionError(name)
        return self.labels


class _Cameras:
    collect_wrist_camera = True
    collect_head_camera = True

    def __init__(self, actor_plane):
        self.left_camera = _Camera(actor_plane)
        self.right_camera = _Camera(actor_plane)
        self.static_camera_list = [_Camera(actor_plane)]
        self.static_camera_name = ["head_camera"]


class _Scene:
    def __init__(self, include_all=True):
        roles = ("common_x", "A", "B", "C", "common_tray", "slot_A", "slot_B", "slot_C")
        self.role_actors = {
            role: _Entity(role, index + 1) for index, role in enumerate(roles)
        }
        plane = np.zeros((4, 4), dtype=np.uint32)
        visible = list(self.role_actors.values()) if include_all else list(self.role_actors.values())[:-1]
        for index, entity in enumerate(visible):
            plane[index // 4, index % 4] = entity.identifier
        self.cameras = _Cameras(plane)


class F4SelectedLayoutRuntimeV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = spec()
        cls.binding = validate_selected_layout_runtime_binding_v2(cls.spec)
        cls.candidate = cls.binding["candidate"]

    def test_scope_binds_search_dispatch_layout_and_budget(self):
        self.assertTrue(self.binding["pass"])
        self.assertEqual(self.binding["candidate_id"], "f4-layout-v2-c01")
        self.assertEqual(
            self.binding["selected_existing_corridor_id"], "lower_carry_height"
        )
        self.assertFalse(self.spec["automatic_fallback"])
        self.assertFalse(self.spec["temporary_waypoint_allowed"])
        frozen_budget = budget()
        self.assertEqual(frozen_budget["allowed_physical_gpu_indices"], list(range(8)))
        self.assertEqual(frozen_budget["maximum_layout_dispatch_count"], 1)
        self.assertEqual(frozen_budget["suffix_execution_limit"], 0)
        self.assertEqual(frozen_budget["release_execution_limit"], 0)

    def test_selected_base_targets_change_only_uniform_preplace_quaternion(self):
        layout = self.candidate["layout"]
        result = build_selected_layout_base_targets_v2(
            candidate=self.candidate,
            object_poses=layout["object_poses"],
            slot_poses=layout["slot_poses"],
            neutral_pose=layout["branch_neutral_pose"],
            object_order=("A", "B", "C"),
        )
        self.assertTrue(result["pass"])
        self.assertFalse(result["temporary_waypoint_added"])
        self.assertEqual(len(result["flattened_targets"]), 21)
        for group in result["object_target_groups"]:
            role = group["role"]
            self.assertEqual(len(group["targets"]), 7)
            preplace = next(
                item
                for item in group["targets"]
                if item["segment_id"] == f"{role}_preplace"
            )
            self.assertEqual(
                preplace["pose"][3:],
                self.candidate["preplace_approach_orientation_wxyz"],
            )
            self.assertTrue(group["preplace_orientation_audit_v2"]["pass"])

    def test_existing_lower_corridor_preserves_uniform_orientation_and_hashes(self):
        layout = self.candidate["layout"]
        base = build_selected_layout_base_targets_v2(
            candidate=self.candidate,
            object_poses=layout["object_poses"],
            slot_poses=layout["slot_poses"],
            neutral_pose=layout["branch_neutral_pose"],
            object_order=("A", "B", "C"),
        )
        by_role = {item["role"]: item["targets"] for item in base["object_target_groups"]}
        contract = build_f4_exact_A_corridors_v11(by_role["A"])
        selected = next(
            item
            for item in contract["candidates"]
            if item["candidate_id"] == SELECTED_EXISTING_CORRIDOR_ID
        )
        hashes = []
        for role in ("A", "B", "C"):
            derived = derive_role_corridor_v11(
                selected_A_candidate=selected,
                base_A_targets=by_role["A"],
                role=role,
                base_role_targets=by_role[role],
            )
            checked = validate_f4_derivation_interface_v2(
                derived, role=role, selected_candidate=selected
            )
            self.assertTrue(checked["pass"])
            preplace = next(
                item for item in checked["targets"] if "preplace" in item["segment_id"]
            )
            self.assertEqual(
                preplace["pose"][3:],
                self.candidate["preplace_approach_orientation_wxyz"],
            )
            self.assertEqual(len(checked["targets"]), 7)
            hashes.append(checked["target_pose_sha256"])
        self.assertEqual(len(set(hashes)), 3)
        self.assertEqual(len(hash_json(hashes)), 64)

    def test_rendered_actor_visibility_requires_every_scene_role(self):
        adapter = RoboTwinRealSapienF4SelectedLayoutV2Adapter.__new__(
            RoboTwinRealSapienF4SelectedLayoutV2Adapter
        )
        passed = adapter.audit_current_rendered_visibility(_Scene(), phase="current")
        self.assertTrue(passed["pass"])
        self.assertEqual(set(passed["camera_buffers"]), {"head_camera", "left_camera", "right_camera"})
        failed = adapter.audit_current_rendered_visibility(
            _Scene(include_all=False), phase="current"
        )
        self.assertFalse(failed["pass"])

    def test_planner_runner_identity_is_additive_and_old_default_is_unchanged(self):
        adapter = Mock()
        adapter.family = "F4"
        new = F4PostStage0PlannerOnlyV1(
            adapter, implementation_version=IMPLEMENTATION_VERSION
        )
        old = F4PostStage0PlannerOnlyV1(adapter)
        self.assertEqual(new.implementation_version, IMPLEMENTATION_VERSION)
        self.assertEqual(old.implementation_version, OLD_IMPLEMENTATION_VERSION)
        source = inspect.getsource(F4ControllerV3_3._top_down_full_targets_v8)
        self.assertIn("F4_new_layout_endpoint_IK_and_three_program_planner_only_v1", source)
        self.assertIn("F4_SELECTED_LAYOUT_SCOPE_V2", source)

    def test_budget_requires_zero_suffix_execution_release_recovery(self):
        result = {
            "budget_counts": {
                "planner_query_count": 96,
                "canonical_prefix_reference_execution_count": 1,
                "suffix_execution_attempt_count": 0,
                "release_execution_count": 0,
                "recovery_attempt_count": 0,
            },
            "cleanup_records": [{}, {}, {}, {}],
            "rendered_visibility_receipts": [{"pass": True}] * 4,
        }
        self.assertTrue(validate_budget(result)["pass"])
        result["budget_counts"]["suffix_execution_attempt_count"] = 1
        with self.assertRaises(RuntimeError):
            validate_budget(result)

    def test_authorization_and_consumption_fail_closed_before_any_gpu_work(self):
        with self.assertRaises(AuthorizationBindingError):
            validate_authorization({}, requested_scope="wrong")
        authorization = {"receipt_sha256": "a" * 64}
        value = {
            "schema_version": CONSUMPTION_SCHEMA,
            "implementation_version": IMPLEMENTATION_VERSION,
            "authorization_id": AUTH_ID,
            "authorization_receipt_sha256": authorization["receipt_sha256"],
            "approved_scope": self.spec["scope"],
            "family": "F4",
            "scene_seed": 20260829,
            "selected_layout_candidate_id": "f4-layout-v2-c01",
            "consumed_at": "2026-08-31T00:00:00+00:00",
            "max_invocations": 1,
            "maximum_layout_dispatch_count": 1,
        }
        value["consumption_receipt_sha256"] = consumption_sha(value)
        self.assertEqual(validate_consumption(value, authorization), value)
        tampered = dict(value)
        tampered["selected_layout_candidate_id"] = "f4-layout-v2-c02"
        with self.assertRaises(AuthorizationBindingError):
            validate_consumption(tampered, authorization)


if __name__ == "__main__":
    unittest.main()
