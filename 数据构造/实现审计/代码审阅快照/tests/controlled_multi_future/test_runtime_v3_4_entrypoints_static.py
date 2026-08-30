import inspect
import unittest

from controlled_multi_future.f3_grasp_three_context_gate_v10 import (
    F3GraspDiagnosticAdapterV10,
    F3GraspThreeContextGateV10,
)
from controlled_multi_future.f4_carry_corridor_v10 import (
    apply_f4_corridor_candidate_v10,
    build_f4_fixed_order_corridors_v10,
)
from controlled_multi_future.f4_staged_block_gate_v1 import (
    F4StagedBlockExecutionGateV1,
)
from controlled_multi_future.probes import gpu_guard_v2_4
from controlled_multi_future.probes import runtime_v3_4_scope_runner
from controlled_multi_future.probes.runtime_v3_4_authorization_v1 import (
    current_source_bindings_v3_4,
)
from controlled_multi_future.real_sapien_adapter_v1_4 import (
    RoboTwinRealSapienStrictPrefixAdapterV1_4,
)


def targets(role):
    q = [1.0, 0.0, 0.0, 0.0]
    values = {
        "pregrasp": [0.16, 0.00, 0.98, *q],
        "grasp": [0.16, 0.01, 0.90, *q],
        "lift": [0.16, 0.01, 0.92, *q],
        "carry_mid": [0.155, 0.08, 1.00, *q],
        "preplace": [0.15, 0.15, 1.00, *q],
        "release": [0.15, 0.15, 0.90, *q],
        "neutral": [0.20, -0.12, 1.01, *q],
    }
    if role == "B":
        for value in values.values():
            value[0] += 0.12
    return [
        {"segment_id": f"{role}_{name}", "pose": pose}
        for name, pose in values.items()
    ]


class FakeAdapter:
    family = "F4"


class RuntimeV34EntrypointsStaticTest(unittest.TestCase):
    def test_real_adapter_is_lazy_v1_4_identity(self):
        source = inspect.getsource(RoboTwinRealSapienStrictPrefixAdapterV1_4)
        self.assertNotIn("import sapien", source)
        self.assertIn("controlled_multi_future_runtime_v3_4", source)

    def test_f3_diagnostic_uses_aliases_and_preopen_controller(self):
        adapter_source = inspect.getsource(F3GraspDiagnosticAdapterV10)
        gate_source = inspect.getsource(F3GraspThreeContextGateV10)
        self.assertIn('item["program_id"] = "D3-"', adapter_source)
        self.assertIn("execute_grasp_robustness_diagnostic_v10", adapter_source)
        self.assertIn("diagnostic_nonroot", gate_source)
        self.assertIn("accepted_root_increment", gate_source)

    def test_f4_staged_gate_accepts_exact_subset_sequence(self):
        gate = F4StagedBlockExecutionGateV1(
            FakeAdapter(),
            gate_sequence=(("B",), ("C",), ("A", "B")),
            implementation_version="controlled_multi_future_runtime_v3_4",
        )
        self.assertEqual(gate.gate_sequence, (("B",), ("C",), ("A", "B")))
        with self.assertRaises(ValueError):
            F4StagedBlockExecutionGateV1(FakeAdapter(), gate_sequence=(("D",),))

    def test_selected_A_corridor_is_applied_uniformly_to_B(self):
        a = targets("A")
        b = targets("B")
        contract = build_f4_fixed_order_corridors_v10(a)
        candidate = contract["candidates"][2]["candidate_id"]
        output = apply_f4_corridor_candidate_v10(
            b,
            selected_candidate_id=candidate,
            reference_A_base_targets=a,
        )
        self.assertEqual(len(output), 7)
        self.assertEqual(output[3]["segment_id"], "B_carry_mid")
        self.assertEqual(output[-2], b[-2])

    def test_runner_guard_and_source_bindings_cover_v3_4(self):
        runner_source = inspect.getsource(runtime_v3_4_scope_runner)
        guard_source = inspect.getsource(gpu_guard_v2_4)
        self.assertIn("F2_inside_targeted_v10", runner_source)
        self.assertIn("F3_grasp_three_context_v10", runner_source)
        self.assertIn("F4_corridor_A_v10", runner_source)
        self.assertIn("_load_runtime_authorization", guard_source)
        bindings = current_source_bindings_v3_4()
        for key in (
            "scope_runner_sha256",
            "gpu_guard_sha256",
            "f2_release_gates_sha256",
            "f3_three_context_gate_sha256",
            "f4_corridor_selection_sha256",
        ):
            self.assertEqual(len(bindings[key]), 64)


if __name__ == "__main__":
    unittest.main()
