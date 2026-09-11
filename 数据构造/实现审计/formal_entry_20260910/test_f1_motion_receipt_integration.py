"""CPU integration checks for the timing-only F1 motion receipt boundary."""
import copy
import json
from pathlib import Path
import unittest

import numpy as np

from native_f1 import (
    _load_motion_baseline_controls,
    apply_motion_hold,
    audit_motion_start_qpos,
    build_motion_baseline_planner_source,
    validate_motion_baseline_planner_source,
)


ROOT = Path('/nfs_share/lijunhui')
ENTRY = ROOT / 'Vault-on-Fvl09/数据构造/实现审计/formal_entry_20260910'
PACKAGE = ENTRY / 'F1_FULL_PRODUCTION/F1_MOTION_RECOVERY_20260911'
OUTPUT = ROOT / 'Robotwin2/datasets/f1_motion_recovery_20260911/F1_000013'
ATTEMPT4 = OUTPUT / 'r_inv_motion/recovery_4/root'


class MotionReceiptIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((PACKAGE / 'specs/F1_000013.spec.json').read_text(encoding='utf-8'))
        cls.auth = json.loads((PACKAGE / 'specs/F1_000013.authorization.json').read_text(encoding='utf-8'))
        cls.binding = cls.auth['motion_baseline_binding']
        cls.old_receipt = json.loads((ATTEMPT4 / 'root_receipt.json').read_text(encoding='utf-8'))

    def _source(self, program_id):
        baseline, _, _ = _load_motion_baseline_controls(
            binding=self.binding, spec=self.spec, program_id=program_id
        )
        return build_motion_baseline_planner_source(
            binding=self.binding,
            spec=self.spec,
            program_id=program_id,
            baseline_manifest=baseline,
        )

    def _complete_receipts(self):
        values = copy.deepcopy(self.old_receipt['suffix_planner_receipts'])
        for item in values:
            source = self._source(item['program_id'])
            item.setdefault('evidence', {})['planner_collision_source'] = source
            item['evidence']['planner_collision_check_source'] = source['description']
        return values

    def test_attempt4_missing_source_still_fails_gate(self):
        from controlled_multi_future.family_runners_v3_3 import F1ControllerV3_3

        gate = F1ControllerV3_3().validate_family_suffix_gate(
            self.old_receipt['suffix_planner_receipts']
        )
        self.assertFalse(gate['evidence_complete'])
        self.assertFalse(gate['checks']['planner_collision_source_available'])

    def test_real_source_envelope_roundtrip_and_gate_pass(self):
        from controlled_multi_future.family_runners_v3_3 import F1ControllerV3_3

        values = self._complete_receipts()
        encoded = json.loads(json.dumps(values, ensure_ascii=False))
        for item in encoded:
            baseline, _, _ = _load_motion_baseline_controls(
                binding=self.binding, spec=self.spec, program_id=item['program_id']
            )
            self.assertTrue(
                validate_motion_baseline_planner_source(
                    item['evidence']['planner_collision_source'],
                    binding=self.binding,
                    spec=self.spec,
                    program_id=item['program_id'],
                    baseline_manifest=baseline,
                )
            )
            self.assertEqual(item['planner_query_count'], 0)
            self.assertFalse(item['evidence']['planner_invoked'])
        gate = F1ControllerV3_3().validate_family_suffix_gate(encoded)
        self.assertTrue(gate['evidence_complete'], gate)
        self.assertTrue(gate['pass'], gate)

    def test_unbound_or_wrong_program_source_is_rejected(self):
        item = self._complete_receipts()[0]
        source = copy.deepcopy(item['evidence']['planner_collision_source'])
        source['description'] = 'official planner pass'
        baseline, _, _ = _load_motion_baseline_controls(
            binding=self.binding, spec=self.spec, program_id=item['program_id']
        )
        with self.assertRaises(ValueError):
            validate_motion_baseline_planner_source(
                source,
                binding=self.binding,
                spec=self.spec,
                program_id=item['program_id'],
                baseline_manifest=baseline,
            )
        source = copy.deepcopy(item['evidence']['planner_collision_source'])
        source['baseline_program_id'] = 'F1-green'
        with self.assertRaises(ValueError):
            validate_motion_baseline_planner_source(
                source,
                binding=self.binding,
                spec=self.spec,
                program_id=item['program_id'],
                baseline_manifest=baseline,
            )

    def test_native_adapter_rejects_free_form_source_at_receiver(self):
        from file_source_pin import native_implementation_hash
        from native_f1 import native_adapter

        values = self._complete_receipts()
        for item in values:
            item['evidence']['planner_collision_source'] = 'official planner pass'
        with __import__('tempfile').TemporaryDirectory(dir=ROOT / 'Robotwin2/tmp') as td:
            adapter = native_adapter(
                spec=self.spec,
                realization='r_inv_motion',
                output_root=Path(td),
                source_sha=native_implementation_hash(),
                recovery_context=self.auth['recovery_context'],
            )
            gate = adapter.validate_family_suffix_gate(
                json.loads(json.dumps(values, ensure_ascii=False))
            )
        self.assertFalse(gate['pass'])
        self.assertFalse(gate['checks']['motion_baseline_source_binding'])

    def test_attempt4_hold_state_fails_strict_selected_arm_start_rule(self):
        baseline, _, _ = _load_motion_baseline_controls(
            binding=self.binding, spec=self.spec, program_id='F1-red'
        )
        segment_start = baseline['execution_spec']['segment_receipts'][0]['start_qpos']
        prefix = np.load(
            ATTEMPT4 / 'canonical_prefix_replay_reference_trace.npz', allow_pickle=False
        )['joint_qpos'][-1]
        suffix = np.load(
            ATTEMPT4 / 'suffix_preflight/F1-red/trace_source.npz', allow_pickle=False
        )['joint_qpos'][878]
        self.assertTrue(np.array_equal(prefix, np.asarray(segment_start, dtype=np.float64)))
        audit = audit_motion_start_qpos(
            baseline_start_qpos=segment_start,
            actual_qpos=suffix,
            arm_qpos_indices=[6, 14, 18, 22, 26, 30],
            tolerance_rad=1e-5,
        )
        self.assertFalse(audit['pass'])
        self.assertGreater(audit['selected_arm_max_error_rad'], 1e-5)
        self.assertAlmostEqual(audit['selected_arm_max_error_rad'], 0.0006772279739379883, places=9)

    def test_constant_actual_qpos_hold_emits_fixed_setpoint_without_planner(self):
        class Joint:
            def __init__(self, name):
                self.name = name

            def get_name(self):
                return self.name

        class Entity:
            def __init__(self):
                self.joints = [Joint(name) for name in ('base', 'fl_joint1', 'fl_joint2')]

            def get_active_joints(self):
                return self.joints

            def get_qpos(self):
                return np.asarray([0.0, 0.12, -0.34])

        class Robot:
            def __init__(self):
                self.left_entity = Entity()
                self.left_arm_joints = self.left_entity.joints[1:]

        class Scene:
            def __init__(self):
                self.robot = Robot()
                self.calls = []

            def take_dense_action(self, control):
                self.calls.append(control)

        scene = Scene()
        audit = apply_motion_hold(scene, 35)
        self.assertTrue(audit['constant_setpoint'])
        self.assertFalse(audit['planner_invoked'])
        self.assertEqual(audit['arm_qpos_indices'], [1, 2])
        control = scene.calls[0]['left_arm']
        self.assertEqual(control['position'].shape, (35, 2))
        self.assertTrue(np.array_equal(control['position'][0], control['position'][-1]))
        self.assertTrue(np.array_equal(control['velocity'], np.zeros((35, 2), dtype=np.float32)))


if __name__ == '__main__':
    unittest.main()
