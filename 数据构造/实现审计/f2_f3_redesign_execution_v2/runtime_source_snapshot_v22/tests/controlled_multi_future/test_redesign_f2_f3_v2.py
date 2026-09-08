from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from controlled_multi_future.redesign_f2_f3_v2.eligibility import empty_index, load_for_research, set_cell, write_index
from controlled_multi_future.redesign_f2_f3_v2.f2_geometry_v2 import synthetic_boundary_checks, verify_expected_relation
from controlled_multi_future.redesign_f2_f3_v2.observations import model_envelopes, read_bundle
from controlled_multi_future.redesign_f2_f3_v2.pilot_contract import expected_cells, planned_root_contract
from controlled_multi_future.redesign_f2_f3_v2.scene_spec import candidate_set_for, scene_spec
from controlled_multi_future.redesign_f2_f3_v2.strict_exit import StrictExitError, strict_negative_tests, validate_inputs_supervision_audit, validate_observable_inputs
from controlled_multi_future.redesign_f2_f3_v2.canonical import canonical_sha256


class V2ContractTests(unittest.TestCase):
    def test_ab_specs_are_real_layout_variants(self):
        a = scene_spec("F2-A-v2"); b = scene_spec("F2-B-v2")
        self.assertNotEqual(a["spec_sha256"], b["spec_sha256"])
        self.assertNotEqual(a["f2"]["box_center_xyz"], b["f2"]["box_center_xyz"])
        self.assertEqual(a["f2"]["support_identity_by_relation"]["beside"], "table")
        self.assertAlmostEqual(a["f2"]["beside_target_xy"][0], 0.20)
        self.assertAlmostEqual(a["f2"]["beside_table_z"], 0.740)

    def test_beside_is_not_stand_top(self):
        checks = synthetic_boundary_checks()
        self.assertTrue(all(checks.values()))
        spec = scene_spec("F2-A-v2")
        result = verify_expected_relation(program_id="beside", pose=[0.08, -0.18, 0.825], spec=spec, contact={"stand_top_contact": True})
        self.assertFalse(result["pass"])

    def test_f2_geometry_uses_asset_transform_and_extents(self):
        from controlled_multi_future.redesign_f2_f3_v2.f2_geometry_v2 import _world_geometry
        spec = scene_spec("F2-A-v2")
        origin = _world_geometry([0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0], spec["f2"])
        rotated = _world_geometry([0.0, 0.0, 0.0, 0.70710678, 0.70710678, 0.0, 0.0], spec["f2"])
        self.assertNotEqual(origin[1].tolist(), rotated[1].tolist())
        self.assertNotEqual(origin[2].tolist(), rotated[2].tolist())

    def test_execution_order_supports_new_first_cells(self):
        f2 = planned_root_contract("F2-A-v2"); f3 = planned_root_contract("F3-A-v2")
        self.assertEqual(f2["execution_order"][0], "beside:r_pc")
        self.assertEqual(f3["execution_order"][0], "VHVH:r_pc")
        self.assertEqual(len(expected_cells("F2-A-v2")), 6)

    def test_strict_inputs_have_no_target(self):
        self.assertTrue(strict_negative_tests()["pass"])
        candidates = candidate_set_for(scene_spec("F2-A-v2"))
        value = {"rgb": [[[0, 1, 2]]], "state": [0.0] * 76, "future": [[0.0] * 26], "candidate_set": candidates}
        validate_observable_inputs(value)
        with self.assertRaises(StrictExitError):
            validate_observable_inputs({**value, "target": candidates[0]})

    def test_f3_candidate_schema_is_ordered(self):
        value = {"rgb": [[[0, 1, 2]]], "state": [0.0] * 76, "future": [[0.0] * 26], "candidate_set": candidate_set_for(scene_spec("F3-A-v2"))}
        self.assertEqual({c["event_sequence"] for c in value["candidate_set"]}, {"VVHH", "VHVH", "VHHV"})
        validate_observable_inputs(value)

    def test_envelopes_keep_target_out_of_inputs(self):
        bundle = {"images": {"head_camera": np.zeros((2, 2, 3), dtype=np.uint8)}, "state": {"joint_qpos": [0.0] * 38, "joint_qvel": [0.0] * 38}, "metadata": {"source": "test"}, "checks": {"pass": True}}
        candidates = candidate_set_for(scene_spec("F3-A-v2")); value = model_envelopes(bundle=bundle, future=np.zeros((3, 26)), candidates=candidates, target=candidates[0])
        self.assertNotIn("target", value["inputs"]); self.assertIn("target", value["supervision"]); self.assertIn("audit", value)
        validate_inputs_supervision_audit(inputs=value["inputs"], supervision=value["supervision"], audit=value["audit"])
        validate_inputs_supervision_audit(inputs={"rgb": [[[0, 1, 2]]], "state": [0.0] * 76, "future": [[0.0] * 26], "candidate_set": candidates}, supervision=value["supervision"], audit=value["audit"])

    def test_eligibility_blocks_legacy_cell(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eligibility.json"; index = empty_index(); set_cell(index, cell_key="F2-A-v2:beside:r_pc", historical="ACCEPTED_IN_V1_HISTORY", current="BLOCKED", reasons=["legacy"]); write_index(path, index)
            with self.assertRaises(PermissionError): load_for_research(path, "F2-A-v2:beside:r_pc")

    def test_new_root_can_start_one_cell_then_resume(self):
        from controlled_multi_future.redesign_f2_f3_v2 import collector_v2

        def fake_cell(*, output, root_id, program_id, realization_id, artifact, collection):
            output.mkdir(parents=True, exist_ok=False)
            return {"schema_version": "fake", "root_id": root_id, "family": "F2", "program_id": program_id, "realization_id": realization_id, "status": "cell_pass", "collection": collection, "current": [0.0] * 7, "anchor": [0.0] * 7, "prefix_sha256": "prefix-v2", "prefix_end_trace_row": 0, "trace_path": str(output / "trace.npz")}

        def fake_prefix(root_output, receipt):
            path = root_output / "prefix_artifact.npz"
            path.write_bytes(b"immutable-prefix")
            return path

        def fake_finalizer(*, cell_dir, spec, expected_relation=None):
            return {"pass": True, "cell_dir": str(cell_dir), "schema_version": "fake-finalizer"}

        from controlled_multi_future.redesign_f2_f3_v2 import finalizer
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(collector_v2, "_f2_cell", side_effect=fake_cell), mock.patch.object(collector_v2, "_save_prefix", side_effect=fake_prefix), mock.patch.object(finalizer, "finalize_cell", side_effect=fake_finalizer), mock.patch.object(finalizer, "finalize_root", return_value={"pass": True, "schema_version": "fake-root-finalizer"}):
            first_dir = Path(directory) / "first"
            first = collector_v2.run_root(output=first_dir, root_id="F2-A-v2", cell_keys=["beside:r_pc"])
            self.assertEqual(first["status"], "INCOMPLETE")
            self.assertEqual(first["completed_cell_keys"], ["beside:r_pc"])
            remaining = [f"{program}:{realization}" for program in ("inside", "on", "beside") for realization in ("r_pc", "r_inv_path") if f"{program}:{realization}" != "beside:r_pc"]
            resumed = collector_v2.run_root(output=Path(directory) / "resumed", root_id="F2-A-v2", cell_keys=remaining, existing_root=first_dir)
            self.assertTrue(resumed["accepted"])
            self.assertEqual(len(resumed["completed_cell_keys"]), 6)

    def test_capture_is_before_planner_and_target_is_supervision_only(self):
        source = Path(__file__).parents[2] / "controlled_multi_future" / "redesign_f2_f3_v2" / "collector_v2.py"
        text = source.read_text(encoding="utf-8")
        self.assertLess(text.index('capture_t0(scene=scene'), text.index('_planner_reset(scene'))
        self.assertIn('"support_identity": support_name', text)
        self.assertIn('def model_envelopes', (source.parent / "observations.py").read_text(encoding="utf-8"))

    def test_object_return_does_not_imply_arm_rest(self):
        from controlled_multi_future.redesign_f2_f3_v2.finalizer import _f3_rest_check

        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.npz"
            (Path(directory) / "current").mkdir()
            (Path(directory) / "current" / "capture_metadata.json").write_text('{"rest_target": [0.0, 0.0, 0.75, 1.0, 0.0, 0.0, 0.0]}')
            object_pose = np.asarray([[0.0, 0.0, 0.75, 1.0, 0.0, 0.0, 0.0]] * 2)
            eef_pose = np.asarray([[0.0, 0.0, 0.75, 1.0, 0.0, 0.0, 0.0], [0.40, 0.0, 0.75, 1.0, 0.0, 0.0, 0.0]])
            np.savez_compressed(trace, object_pose=object_pose, eef_pose=eef_pose)
            result = _f3_rest_check(trace, {"rest_target": [0.0, 0.0, 0.75, 1.0, 0.0, 0.0, 0.0]}, scene_spec("F3-A-v2"))
            self.assertFalse(result["pass"])
            self.assertGreater(result["eef_rest_position_m"], 0.30)

    def test_readback_recomputes_content_hashes(self):
        from controlled_multi_future.redesign_f2_f3_v2.observations import _sha_bytes

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory); image = np.zeros((2, 2, 3), dtype=np.uint8)
            np.savez_compressed(path / "rgb.npz", head_camera__rgb=image)
            state = {"joint_qpos": [0.0] * 38, "joint_qvel": [0.0] * 38, "joint_qf": [0.0] * 38, "eef_pose": [0.0] * 7, "gripper_command": [0.0, 0.0], "left_gripper_drive_target": [0.0], "right_gripper_drive_target": [0.0], "left_gripper_drive_velocity_target": [0.0], "right_gripper_drive_velocity_target": [0.0], "role_object_pose": {"obj": [0.0] * 7}, "role_object_linear_velocity": {"obj": None}, "role_object_angular_velocity": {"obj": None}, "role_velocity_available": {"obj": {"linear": False, "angular": False}}}
            state["state76_sha256"] = _sha_bytes(np.asarray(state["joint_qpos"] + state["joint_qvel"], dtype=np.float64).tobytes())
            (path / "state.json").write_text(__import__("json").dumps(state, sort_keys=True))
            anchor = {"schema_version": "cmf_f2_f3_anchor_bundle_v2", "state": state}; (path / "anchor.json").write_text(__import__("json").dumps(anchor, sort_keys=True))
            metadata = {"schema_version": "cmf_f2_f3_t0_capture_metadata_v2", "camera_names": ["head_camera"], "camera_images": {"head_camera": {"shape": [2, 2, 3], "dtype": "uint8", "sha256": _sha_bytes(image.tobytes())}}, "state_sha256": state["state76_sha256"], "rgb_npz_sha256": _sha_bytes((path / "rgb.npz").read_bytes()), "state_json_sha256": _sha_bytes((path / "state.json").read_bytes()), "anchor_json_sha256": _sha_bytes((path / "anchor.json").read_bytes()), "rest_target": None}
            metadata["capture_metadata_sha256"] = canonical_sha256(metadata); (path / "capture_metadata.json").write_text(__import__("json").dumps(metadata, sort_keys=True))
            self.assertTrue(read_bundle(path)["checks"]["pass"])
            state["joint_qpos"][0] = 1.0; (path / "state.json").write_text(__import__("json").dumps(state, sort_keys=True))
            self.assertFalse(read_bundle(path)["checks"]["pass"])

    def test_finalizer_rejects_missing_f3_events_and_f2_support(self):
        from controlled_multi_future.redesign_f2_f3_v2.finalizer import _f2_trace_check, _f3_trace_check

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.npz"
            self.assertFalse(_f3_trace_check(path, {}, scene_spec("F3-A-v2"))["pass"])
            self.assertFalse(_f2_trace_check(path, {}, scene_spec("F2-A-v2"), "beside")["pass"])

    def test_failed_cell_stops_dispatch_and_cannot_be_accepted(self):
        from controlled_multi_future.redesign_f2_f3_v2 import collector_v2
        calls = []

        def failed_cell(*, output, root_id, program_id, realization_id, artifact, collection):
            calls.append(f"{program_id}:{realization_id}"); output.mkdir(parents=True, exist_ok=False)
            return {"schema_version": "fake", "root_id": root_id, "family": "F2", "program_id": program_id, "realization_id": realization_id, "status": "cell_failed_execution", "collection": collection}

        with tempfile.TemporaryDirectory() as directory, mock.patch.object(collector_v2, "_f2_cell", side_effect=failed_cell):
            result = collector_v2.run_root(output=Path(directory) / "failed", root_id="F2-A-v2", cell_keys=["beside:r_pc", "inside:r_pc", "inside:r_inv_path"])
            self.assertFalse(result["accepted"]); self.assertEqual(len(calls), 1); self.assertEqual(result["status"], "INCOMPLETE")

    def test_root_pass_requires_independent_root_finalizer(self):
        from controlled_multi_future.redesign_f2_f3_v2 import collector_v2, finalizer

        def fake_cell(*, output, root_id, program_id, realization_id, artifact, collection):
            output.mkdir(parents=True, exist_ok=False)
            return {"schema_version": "fake", "root_id": root_id, "family": "F2", "program_id": program_id, "realization_id": realization_id, "status": "cell_pass", "cell_local_verified": True, "collection": collection, "current": [0.0] * 7, "anchor": [0.0] * 7, "prefix_sha256": "prefix-v2", "prefix_end_trace_row": 0, "trace_path": str(output / "trace.npz")}

        def fake_prefix(root_output, receipt):
            path = root_output / "prefix_artifact.npz"; path.write_bytes(b"prefix"); return path

        with tempfile.TemporaryDirectory() as directory, mock.patch.object(collector_v2, "_f2_cell", side_effect=fake_cell), mock.patch.object(collector_v2, "_save_prefix", side_effect=fake_prefix), mock.patch.object(finalizer, "finalize_cell", return_value={"pass": True}), mock.patch.object(finalizer, "finalize_root", return_value={"pass": False, "reason": "synthetic root mismatch"}):
            result = collector_v2.run_root(output=Path(directory) / "root", root_id="F2-B-v2")
            self.assertFalse(result["accepted"]); self.assertEqual(result["status"], "INCOMPLETE_INDEPENDENT_FINALIZER"); self.assertFalse(result["root_independent_verified"])


if __name__ == "__main__":
    unittest.main()
