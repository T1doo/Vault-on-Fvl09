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
        self.assertAlmostEqual(a["f2"]["beside_target_xy"][0], 0.24)
        self.assertAlmostEqual(a["f2"]["beside_table_z"], 0.740)

    def test_beside_is_not_stand_top(self):
        checks = synthetic_boundary_checks()
        self.assertTrue(all(checks.values()))
        spec = scene_spec("F2-A-v2")
        result = verify_expected_relation(program_id="beside", pose=[0.08, -0.18, 0.825], spec=spec, contact={"stand_top_contact": True})
        self.assertFalse(result["pass"])
        legal = verify_expected_relation(program_id="beside", pose=[0.24, -0.18, 0.740], spec=spec)
        self.assertTrue(legal["pass"])
        self.assertTrue(legal["separated_from_stand"])

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
            camera_images = {name: image.copy() for name in ("front_camera", "head_camera", "left_camera", "right_camera")}
            np.savez_compressed(path / "rgb.npz", **{f"{name}__rgb": value for name, value in camera_images.items()})
            state = {"joint_qpos": [0.0] * 38, "joint_qvel": [0.0] * 38, "joint_qf": [0.0] * 38, "eef_pose": [0.0] * 7, "gripper_command": [0.0, 0.0], "left_gripper_drive_target": [0.0], "right_gripper_drive_target": [0.0], "left_gripper_drive_velocity_target": [0.0], "right_gripper_drive_velocity_target": [0.0], "role_object_pose": {"obj": [0.0] * 7}, "role_object_linear_velocity": {"obj": None}, "role_object_angular_velocity": {"obj": None}, "role_velocity_available": {"obj": {"linear": False, "angular": False}}}
            state["state76_sha256"] = _sha_bytes(np.asarray(state["joint_qpos"] + state["joint_qvel"], dtype=np.float64).tobytes())
            (path / "state.json").write_text(__import__("json").dumps(state, sort_keys=True))
            anchor = {"schema_version": "cmf_f2_f3_anchor_bundle_v2", "state": state}; (path / "anchor.json").write_text(__import__("json").dumps(anchor, sort_keys=True))
            metadata = {"schema_version": "cmf_f2_f3_t0_capture_metadata_v2", "required_camera_names": ["front_camera", "head_camera", "left_camera", "right_camera"], "camera_names": ["front_camera", "head_camera", "left_camera", "right_camera"], "camera_images": {name: {"shape": [2, 2, 3], "dtype": "uint8", "sha256": _sha_bytes(image.tobytes())} for name in camera_images}, "state_sha256": state["state76_sha256"], "rgb_npz_sha256": _sha_bytes((path / "rgb.npz").read_bytes()), "state_json_sha256": _sha_bytes((path / "state.json").read_bytes()), "anchor_json_sha256": _sha_bytes((path / "anchor.json").read_bytes()), "rest_target": None}
            metadata["capture_metadata_sha256"] = canonical_sha256(metadata); (path / "capture_metadata.json").write_text(__import__("json").dumps(metadata, sort_keys=True))
            self.assertTrue(read_bundle(path)["checks"]["pass"])
            state["joint_qpos"][0] = 1.0; (path / "state.json").write_text(__import__("json").dumps(state, sort_keys=True))
            self.assertFalse(read_bundle(path)["checks"]["pass"])

    def test_readback_requires_model_camera_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory); image = np.zeros((2, 2, 3), dtype=np.uint8)
            np.savez_compressed(path / "rgb.npz", head_camera__rgb=image)
            state = {"joint_qpos": [0.0] * 38, "joint_qvel": [0.0] * 38, "joint_qf": [0.0] * 38, "eef_pose": [0.0] * 7, "gripper_command": [0.0, 0.0], "left_gripper_drive_target": [0.0], "right_gripper_drive_target": [0.0], "left_gripper_drive_velocity_target": [0.0], "right_gripper_drive_velocity_target": [0.0], "role_object_pose": {"bottle": [0.0] * 7}, "role_object_linear_velocity": {"bottle": None}, "role_object_angular_velocity": {"bottle": None}, "role_velocity_available": {"bottle": {"linear": False, "angular": False}}}
            from controlled_multi_future.redesign_f2_f3_v2.observations import _sha_bytes
            state["state76_sha256"] = _sha_bytes(np.asarray(state["joint_qpos"] + state["joint_qvel"], dtype=np.float64).tobytes())
            (path / "state.json").write_text(__import__("json").dumps(state, sort_keys=True)); (path / "anchor.json").write_text(__import__("json").dumps({"schema_version": "cmf_f2_f3_anchor_bundle_v2", "state": state}, sort_keys=True))
            metadata = {"schema_version": "cmf_f2_f3_t0_capture_metadata_v2", "required_camera_names": ["front_camera", "head_camera", "left_camera", "right_camera"], "camera_names": ["head_camera"], "camera_images": {"head_camera": {"shape": [2, 2, 3], "dtype": "uint8", "sha256": _sha_bytes(image.tobytes())}}, "state_sha256": state["state76_sha256"], "rgb_npz_sha256": _sha_bytes((path / "rgb.npz").read_bytes()), "state_json_sha256": _sha_bytes((path / "state.json").read_bytes()), "anchor_json_sha256": _sha_bytes((path / "anchor.json").read_bytes()), "rest_target": None}
            metadata["capture_metadata_sha256"] = canonical_sha256(metadata); (path / "capture_metadata.json").write_text(__import__("json").dumps(metadata, sort_keys=True))
            self.assertFalse(read_bundle(path)["checks"]["pass"])

    def test_trace_row0_is_bound_to_saved_state(self):
        from controlled_multi_future.redesign_f2_f3_v2.finalizer import _trace_row0_check
        state = {"joint_qpos": [0.0] * 38, "joint_qvel": [0.0] * 38, "joint_qf": [0.0] * 38, "eef_pose": [0.0] * 7, "gripper_command": [0.0, 0.0], "left_gripper_drive_target": [0.0], "right_gripper_drive_target": [0.0], "left_gripper_drive_velocity_target": [0.0], "right_gripper_drive_velocity_target": [0.0], "role_object_pose": {"bottle": [0.0] * 7}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.npz"
            fields = {"step_index": np.asarray([0], dtype=np.int64), "joint_qpos": np.asarray([state["joint_qpos"]]), "joint_qvel": np.asarray([state["joint_qvel"]]), "joint_qf": np.asarray([state["joint_qf"]]), "eef_pose": np.asarray([state["eef_pose"]]), "gripper_command": np.asarray([state["gripper_command"]]), "left_gripper_joint_drive_target": np.asarray([[0.0]]), "right_gripper_joint_drive_target": np.asarray([[0.0]]), "left_gripper_joint_drive_velocity_target": np.asarray([[0.0]]), "right_gripper_joint_drive_velocity_target": np.asarray([[0.0]]), "object_pose": np.asarray([[0.0] * 7]), "role_object_pose__bottle": np.asarray([[0.0] * 7])}
            np.savez_compressed(path, **fields)
            bundle = {"state": state}
            self.assertTrue(_trace_row0_check(path, bundle)["pass"])
            fields["joint_qpos"][0, 0] = 1.0; np.savez_compressed(path, **fields)
            self.assertFalse(_trace_row0_check(path, bundle)["pass"])

    def test_v2_execution_ledger_is_independent_and_idempotent(self):
        from controlled_multi_future.redesign_f2_f3_v2.execution_ledger_v2 import ExecutionLedgerV2, ExecutionLedgerError
        with tempfile.TemporaryDirectory() as directory:
            caps = {"fresh_scenes": 2, "action_scenes": 2, "collection_attempts": 2, "solver_problems": 10, "gpu_lease_seconds": 20}
            ledger = ExecutionLedgerV2(Path(directory) / "ledger.jsonl", contract_sha256="contract-v2", task_id="task-v2", caps=caps)
            reservation = {"fresh_scenes": 1, "action_scenes": 1, "collection_attempts": 1, "solver_problems": 4, "gpu_lease_seconds": 10}
            first = ledger.reserve("job-1", reservation, idempotency_key="reserve-job-1")
            self.assertEqual(ledger.reserve("job-1", reservation, idempotency_key="reserve-job-1")["event_id"], first["event_id"])
            settled = ledger.settle("job-1", reservation, reservation, idempotency_key="settle-job-1")
            self.assertEqual(settled["event_type"], "JOB_SETTLED")
            with self.assertRaises(ExecutionLedgerError):
                ledger.reserve("job-2", {"fresh_scenes": 2, "action_scenes": 2, "collection_attempts": 2, "solver_problems": 10, "gpu_lease_seconds": 20}, idempotency_key="reserve-job-2")

    def test_anchor_signature_excludes_run_identity_but_keeps_physics(self):
        from controlled_multi_future.redesign_f2_f3_v2.finalizer import _anchor_signature
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"; second = Path(directory) / "second"; first.mkdir(); second.mkdir()
            anchor = {"schema_version": "cmf_f2_f3_anchor_bundle_v2", "root_id": "F2-A-v2", "cell_key": "inside:r_pc", "state": {"joint_qpos": [0.0]}, "scene_spec": {"layout": "A"}}
            (first / "anchor.json").write_text(__import__("json").dumps(anchor, sort_keys=True)); changed = {**anchor, "root_id": "F2-A-v2", "cell_key": "on:r_inv_path", "path": "/tmp/other"}; (second / "anchor.json").write_text(__import__("json").dumps(changed, sort_keys=True))
            self.assertEqual(_anchor_signature(first), _anchor_signature(second))
            changed["state"] = {"joint_qpos": [1.0]}; (second / "anchor.json").write_text(__import__("json").dumps(changed, sort_keys=True))
            self.assertNotEqual(_anchor_signature(first), _anchor_signature(second))

    def test_finalizer_rejects_missing_f3_events_and_f2_support(self):
        from controlled_multi_future.redesign_f2_f3_v2.finalizer import _f2_trace_check, _f3_trace_check

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.npz"
            self.assertFalse(_f3_trace_check(path, {}, scene_spec("F3-A-v2"))["pass"])
            self.assertFalse(_f2_trace_check(path, {}, scene_spec("F2-A-v2"), "beside")["pass"])

    def test_f3_event_layout_is_derived_from_program_and_trace(self):
        from controlled_multi_future.redesign_f2_f3_v2.finalizer import _f3_event_layout_check

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.npz"
            np.savez_compressed(path, step_index=np.arange(40, dtype=np.int64))
            receipt = {
                "program_id": "VHVH",
                "prefix_event_evidence": {"start_row": 1, "end_row": 5},
                "expected_suffix_event_order": ["H", "V", "H"],
                "event_segments": [
                    {"event_index": 1, "axis": "H", "start_row": 7, "end_row": 12},
                    {"event_index": 2, "axis": "V", "start_row": 14, "end_row": 19},
                    {"event_index": 3, "axis": "H", "start_row": 21, "end_row": 26},
                ],
            }
            self.assertTrue(_f3_event_layout_check(path, receipt, scene_spec("F3-A-v2"))["pass"])
            reordered = {**receipt, "event_segments": [receipt["event_segments"][1], receipt["event_segments"][0], receipt["event_segments"][2]]}
            self.assertFalse(_f3_event_layout_check(path, reordered, scene_spec("F3-A-v2"))["pass"])
            self.assertFalse(_f3_event_layout_check(path, {**receipt, "expected_suffix_event_order": []}, scene_spec("F3-A-v2"))["pass"])
            self.assertFalse(_f3_event_layout_check(path, {**receipt, "program_id": "VVHH", "expected_suffix_event_order": ["H", "V", "H"]}, scene_spec("F3-A-v2"))["pass"])

    def test_f3_object_return_is_a_terminal_gate(self):
        from controlled_multi_future.redesign_f2_f3_v2.finalizer import _f3_trace_check

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / "trace.npz"; current = root / "current"; current.mkdir()
            n = 70; eef = np.zeros((n, 7), dtype=float); obj = np.zeros((n, 7), dtype=float)
            eef[:, 3] = 1.0; obj[:, 3] = 1.0; eef[:, 2] = 0.75; obj[:, 2] = 0.75
            intervals = [(1, 8, "V"), (10, 17, "H"), (19, 26, "V"), (28, 35, "H")]
            for start, end, axis in intervals:
                axis_index = 2 if axis == "V" else 0
                values = (-0.05, 0.05, 0.0, -0.05, 0.05, 0.0, 0.0, 0.0)
                for offset, value in enumerate(values):
                    eef[start + offset, axis_index] = value
                    obj[start + offset, axis_index] = value
            obj[-1, 0] = 0.10
            zeros3 = np.zeros((n, 3), dtype=float); zeros4 = np.zeros((n, 4), dtype=float); zeros4[:, 3] = 1.0
            contacts = np.asarray(["[]"] * n, dtype="U160")
            for i in range(n - 10, n): contacts[i] = '[{"body_a":"f3_redesign_bottle","body_b":"f3_redesign_support_pad"}]'
            selected = np.zeros(n, dtype=bool); selected[1:36] = True
            np.savez_compressed(path, step_index=np.arange(n), eef_pose=eef, object_pose=obj, selected_gripper_contact=selected, object_linear_velocity=zeros3, eef_linear_velocity=zeros3, eef_angular_velocity=zeros3, gripper_command=np.ones((n, 2)), contact_pairs_json=contacts)
            (current / "capture_metadata.json").write_text('{"rest_target":[0.0,0.0,0.75,1.0,0.0,0.0,0.0]}')
            receipt = {"program_id": "VHVH", "rest_target": [0.0, 0.0, 0.75, 1.0, 0.0, 0.0, 0.0], "prefix_event_evidence": {"start_row": 1, "end_row": 8}, "expected_suffix_event_order": ["H", "V", "H"], "event_segments": [{"event_index": 1, "axis": "H", "start_row": 10, "end_row": 17}, {"event_index": 2, "axis": "V", "start_row": 19, "end_row": 26}, {"event_index": 3, "axis": "H", "start_row": 28, "end_row": 35}]}
            result = _f3_trace_check(path, receipt, scene_spec("F3-A-v2"))
            self.assertFalse(result["pass"])
            self.assertFalse(result["terminal"]["checks"]["object_return"])

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

    def test_cell_finalizer_exception_is_persisted_and_stops_root(self):
        from controlled_multi_future.redesign_f2_f3_v2 import collector_v2, finalizer

        def fake_cell(*, output, root_id, program_id, realization_id, artifact, collection):
            output.mkdir(parents=True, exist_ok=False)
            return {"schema_version": "fake", "root_id": root_id, "family": "F2", "program_id": program_id, "realization_id": realization_id, "status": "cell_pass", "collection": collection, "current": [0.0] * 7, "anchor": [0.0] * 7, "prefix_sha256": "prefix-v2", "prefix_end_trace_row": 0, "prefix_anchor_contact_stable": True, "trace_path": str(output / "trace.npz")}

        def fake_prefix(root_output, receipt):
            path = root_output / "prefix_artifact.npz"; path.write_bytes(b"prefix"); return path

        with tempfile.TemporaryDirectory() as directory, mock.patch.object(collector_v2, "_f2_cell", side_effect=fake_cell), mock.patch.object(collector_v2, "_save_prefix", side_effect=fake_prefix), mock.patch.object(finalizer, "finalize_cell", side_effect=RuntimeError("synthetic finalizer crash")):
            result = collector_v2.run_root(output=Path(directory) / "root", root_id="F2-A-v2", cell_keys=["beside:r_pc"])
            self.assertFalse(result["accepted"])
            self.assertEqual(result["stop_reason"], "independent_cell_finalizer_failed:beside:r_pc")
            self.assertTrue((Path(directory) / "root" / "beside_r_pc" / "independent_finalizer_v2.json").is_file())
            self.assertTrue((Path(directory) / "root" / "root_checkpoint.json").is_file())


if __name__ == "__main__":
    unittest.main()
