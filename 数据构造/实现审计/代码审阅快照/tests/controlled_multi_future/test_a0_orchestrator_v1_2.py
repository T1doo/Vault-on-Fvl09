import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from controlled_multi_future.a0_activity_monitor_v2 import (
    ActivityMonitorInstallationError,
    ActivityMonitorRestorationError,
    activity_entry_point_registry_artifact,
    canonical_json_sha256,
)
from controlled_multi_future.a0_orchestrator_v1_2 import (
    A0CurrentAnchorOrchestratorV1_2,
    A0_PHASES_V1_2,
)
from controlled_multi_future.anchor import capture_anchor
from controlled_multi_future.current_hasher import build_current_hashes
from controlled_multi_future.root_orchestrator_v1_1 import SceneHandleV1_1


def activity_receipt(scene_id, phase, *, violation=False):
    count = 1 if violation else 0
    registry = activity_entry_point_registry_artifact()
    entries = sorted(f"{item['owner']}.{item['attribute']}" for item in registry["entries"])
    payload = {
        "schema_version": "cmf_a0_activity_audit_v2",
        "scene_instance_id": scene_id,
        "phase": phase,
        "monitor_boundary": {
            "monitor_started": True,
            "monitor_stopped": True,
            "monitor_start_step": 0,
            "monitor_end_step": 0,
            "monitor_start_monotonic_time": 1.0,
            "monitor_end_monotonic_time": 2.0,
        },
        "setup_activity": {
            "setup_demo_completed": True,
            "setup_activity_source": "synthetic",
            "setup_take_action_count_if_available": 0,
            "setup_planner_query_count_if_available": None,
            "canonical_settle_steps": 60,
            "canonical_settle_is_control_action": False,
            "simulator_timestep_seconds": 0.004,
            "control_steps_per_action": 1,
            "effective_action_interval_seconds": 0.004,
            "timestep_source": "synthetic",
        },
        "post_setup_activity": {
            "planner_query_delta": count,
            "planner_query_record_delta": count,
            "controlled_action_delta": 0,
            "instrumented_control_call_delta": 0,
            "instrumented_planner_wrapper_delta": 0,
            "take_action_count_delta": 0,
            "trace_row_delta": None,
            "trace_counter_available": False,
            "physics_step_delta": 0,
            "renderer_update_delta": 2,
            "native_planner_query_count_delta_if_available": None,
            "native_planner_record_delta_if_available": None,
        },
        "instrumentation": {
            "entry_point_registry_schema": "cmf_a0_post_setup_entry_point_registry_v2",
            "entry_point_registry_sha256": registry["registry_sha256"],
            "wrapped_entry_points": entries,
            "all_registry_entry_points": entries,
            "missing_expected_entry_points": [],
            "wrapper_installation_pass": True,
            "wrapper_restoration_pass": True,
            "installation_errors": [],
            "restoration_errors": [],
            "per_entry_call_counts": {},
            "planner_query_records": [],
            "controlled_action_records": [],
            "counter_sources": {"synthetic": True},
        },
        "limits": {"planner_query_limit": 0, "controlled_action_limit": 0},
    }
    payload["activity_receipt_sha256"] = canonical_json_sha256(payload)
    return payload


class SyntheticScene:
    def __init__(self, phase, scene_id):
        self.phase = phase
        self._cmf_scene_instance_id = scene_id


class SyntheticContext:
    def __init__(self, adapter, planned, phase):
        adapter.counter += 1
        self.adapter = adapter
        self.planned = planned
        self.phase = phase
        self.scene_id = f"v1-2-scene-{adapter.counter}"
        self.handle = SceneHandleV1_1(scene_instance_id=self.scene_id, scene=SyntheticScene(phase, self.scene_id))
        self.cleanup_receipt = None

    def __enter__(self):
        self.adapter.opened.append(self.phase)
        if self.phase == self.adapter.mutate_phase:
            self.planned["seed"] = 123
        return self.handle

    def __exit__(self, exc_type, exc, tb):
        safe = self.phase != self.adapter.cleanup_uncertain_phase
        self.cleanup_receipt = {
            "scene_instance_id": self.scene_id,
            "scene_created": True,
            "scene_cleanup_attempted": True,
            "scene_cleanup_succeeded": safe,
            "cleanup_safety_pass": safe,
            "orphan_process_count": 0 if safe else None,
            "cleanup_error": None if safe else "synthetic cleanup uncertainty",
        }
        self.handle.cleanup_receipt = dict(self.cleanup_receipt)
        return False


class SyntheticAdapter:
    def __init__(
        self,
        *,
        current_mismatch_phase=None,
        anchor_mismatch_phase=None,
        cleanup_uncertain_phase=None,
        mutate_phase=None,
        unbound_phase=None,
        violation_phase=None,
        monitor_error_phase=None,
        monitor_error_type=None,
    ):
        self.current_mismatch_phase = current_mismatch_phase
        self.anchor_mismatch_phase = anchor_mismatch_phase
        self.cleanup_uncertain_phase = cleanup_uncertain_phase
        self.mutate_phase = mutate_phase
        self.unbound_phase = unbound_phase
        self.violation_phase = violation_phase
        self.monitor_error_phase = monitor_error_phase
        self.monitor_error_type = monitor_error_type
        self.counter = 0
        self.opened = []

    def scene(self, planned_root_slot_spec, *, phase, program=None):
        self.last_context = SyntheticContext(self, planned_root_slot_spec, phase)
        return self.last_context

    def capture_current(self, scene):
        mismatch = scene.phase == self.current_mismatch_phase
        return build_current_hashes(
            head_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            wrist_rgb={"left": np.zeros((1, 1, 3), dtype=np.uint8), "right": np.zeros((1, 1, 3), dtype=np.uint8)},
            robot_state=np.asarray([1.0 if mismatch else 0.0]),
            gripper_actual_state=np.zeros(2),
            object_role_layout={"object": [0, 0, 0]},
            camera_config_version="synthetic-v1",
            scene_seed=20260829,
            generator_version="synthetic-a0-v1-2",
        )

    def capture_anchor(self, scene):
        mismatch = scene.phase == self.anchor_mismatch_phase
        return capture_anchor(
            robot_qpos=[0.01 if mismatch else 0.0],
            robot_qvel=[0.0],
            actor_poses={"object": [0, 0, 0, 1, 0, 0, 0]},
            gripper_state=[1, 1],
            metadata={"seed": 20260829},
        )

    def finish_a0_activity_monitor(self, scene, *, phase, scene_instance_id):
        receipt = activity_receipt(scene_instance_id, phase, violation=phase == self.violation_phase)
        if phase == self.unbound_phase:
            receipt["scene_instance_id"] = "wrong-scene"
            receipt.pop("activity_receipt_sha256")
            receipt["activity_receipt_sha256"] = canonical_json_sha256(receipt)
        if phase == self.monitor_error_phase:
            error_type = self.monitor_error_type or ActivityMonitorInstallationError
            raise error_type("synthetic monitor error", receipt=receipt)
        self.last_context.activity_receipt = receipt
        self.last_context.handle.activity_receipt = receipt
        return receipt


class A0OrchestratorV1_2Test(unittest.TestCase):
    def run_a0(self, adapter):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name) / "a0"
        receipt = A0CurrentAnchorOrchestratorV1_2(adapter).run(
            output_dir=output,
            planned_root_slot_spec={"slot_id": "a0-v1-2", "family": "F1", "seed": 20260829},
            receipt_metadata={"test_only": True},
        )
        return receipt, output

    def test_four_scenes_and_all_artifact_hashes_pass(self):
        adapter = SyntheticAdapter()
        receipt, output = self.run_a0(adapter)
        self.assertEqual(receipt["status"], "passed_nonformal_A0")
        self.assertEqual(adapter.opened, list(A0_PHASES_V1_2))
        self.assertEqual(len(receipt["scenes"]), 4)
        for item in receipt["scenes"]:
            phase_dir = output / item["artifact_directory"]
            artifact = json.loads((phase_dir / "artifact_hashes.json").read_text())
            for metadata in artifact["files"].values():
                path = phase_dir / metadata["path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), metadata["sha256"])
            self.assertEqual(
                hashlib.sha256((phase_dir / "artifact_hashes.json").read_bytes()).hexdigest(),
                item["artifact_hashes"]["artifact_hashes_sha256"],
            )

    def test_current_mismatch_fresh1_stops_and_saves_component_diff(self):
        adapter = SyntheticAdapter(current_mismatch_phase="A0_fresh_1")
        receipt, output = self.run_a0(adapter)
        self.assertEqual(receipt["status"], "failed_current_hash")
        self.assertEqual(adapter.opened, list(A0_PHASES_V1_2[:2]))
        diff = output / "scenes/01_A0_fresh_1/component_diff.json"
        self.assertTrue(diff.is_file())
        value = json.loads(diff.read_text())
        self.assertTrue(value["current_component_diff"]["components_changed"]["robot_state"])
        self.assertTrue(value["diagnostic_only_does_not_relax_gate"])

    def test_anchor_mismatch_fresh2_stops_and_saves_diagnostic(self):
        adapter = SyntheticAdapter(anchor_mismatch_phase="A0_fresh_2")
        receipt, output = self.run_a0(adapter)
        self.assertEqual(receipt["status"], "failed_anchor_equivalence")
        self.assertEqual(adapter.opened, list(A0_PHASES_V1_2[:3]))
        value = json.loads((output / "scenes/02_A0_fresh_2/component_diff.json").read_text())
        self.assertTrue(value["anchor_component_diff"]["components_changed"]["robot_qpos"])

    def test_cleanup_uncertainty_is_terminal_at_pristine_and_fresh1(self):
        for phase, expected in (("A0_pristine", 1), ("A0_fresh_1", 2)):
            with self.subTest(phase=phase):
                adapter = SyntheticAdapter(cleanup_uncertain_phase=phase)
                receipt, _ = self.run_a0(adapter)
                self.assertEqual(receipt["status"], "failed_cleanup_uncertain")
                self.assertEqual(len(adapter.opened), expected)

    def test_planned_spec_mutation_activity_unbound_and_violation_fail(self):
        receipt, _ = self.run_a0(SyntheticAdapter(mutate_phase="A0_pristine"))
        self.assertEqual(receipt["status"], "failed_candidate_mutation")
        receipt, _ = self.run_a0(SyntheticAdapter(unbound_phase="A0_pristine"))
        self.assertEqual(receipt["status"], "failed_activity_audit_unbound")
        receipt, _ = self.run_a0(SyntheticAdapter(violation_phase="A0_pristine"))
        self.assertEqual(receipt["status"], "failed_zero_post_setup_activity")

    def test_monitor_installation_and_restoration_statuses_are_distinct(self):
        receipt, _ = self.run_a0(
            SyntheticAdapter(
                monitor_error_phase="A0_pristine",
                monitor_error_type=ActivityMonitorInstallationError,
            )
        )
        self.assertEqual(receipt["status"], "failed_activity_monitor_installation")
        receipt, _ = self.run_a0(
            SyntheticAdapter(
                monitor_error_phase="A0_pristine",
                monitor_error_type=ActivityMonitorRestorationError,
            )
        )
        self.assertEqual(receipt["status"], "failed_activity_monitor_restoration")

    def test_reused_activity_hash_is_terminal_even_if_validator_is_compromised(self):
        adapter = SyntheticAdapter()
        shared = "f" * 64

        def fake_validate(value, **kwargs):
            result = copy.deepcopy(value)
            result["activity_receipt_sha256"] = shared
            return result

        with mock.patch(
            "controlled_multi_future.a0_orchestrator_v1_2.validate_activity_receipt_v2",
            side_effect=fake_validate,
        ):
            receipt, _ = self.run_a0(adapter)
        self.assertEqual(receipt["status"], "failed_activity_receipt_reuse")
        self.assertEqual(adapter.opened, list(A0_PHASES_V1_2[:2]))


if __name__ == "__main__":
    unittest.main()
