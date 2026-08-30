import inspect
import unittest

from controlled_multi_future.f3_three_context_diagnostic_runner_v11 import (
    F3ThreeContextDiagnosticRunnerV11,
    PROGRAM_IDS,
)
from controlled_multi_future.f4_bc_preflight_gate_v11 import F4BCPreflightGateV11
from controlled_multi_future.f4_exact_corridor_a_gate_v11 import (
    F4ExactCorridorAExecutionGateV11,
)
from controlled_multi_future.f4_staged_block_gate_v1 import (
    F4StagedBlockExecutionGateV1,
)
from controlled_multi_future.probes import gpu_guard_v2_4
from controlled_multi_future.probes import runtime_v3_4_1_scope_runner
from controlled_multi_future.probes.runtime_v3_4_1_authorization_v1 import (
    current_source_bindings_v3_4_1,
)
from controlled_multi_future.real_sapien_adapter_v1_5 import (
    RoboTwinRealSapienStrictPrefixAdapterV1_5,
)
from controlled_multi_future.runtime_v3_4_1_budget_v1 import SUPPORTED_SCOPES


class FakeAdapter:
    family = "F4"


class RuntimeV341EntrypointsStaticTest(unittest.TestCase):
    def test_real_adapter_is_lazy_v1_5_identity(self):
        source = inspect.getsource(RoboTwinRealSapienStrictPrefixAdapterV1_5)
        self.assertNotIn("import sapien", source)
        self.assertIn("controlled_multi_future_runtime_v3_4_1", source)

    def test_f3_uses_canonical_ids_without_alias(self):
        source = inspect.getsource(F3ThreeContextDiagnosticRunnerV11)
        self.assertEqual(
            PROGRAM_IDS, ("F3-VVHH", "F3-VHVH", "F3-VHHV")
        )
        self.assertNotIn('item["program_id"] = "D3-"', source)
        self.assertIn("diagnostic_nonroot", source)
        self.assertIn("release_executed", source)

    def test_f4_planner_only_mode_is_explicit(self):
        gate = F4StagedBlockExecutionGateV1(
            FakeAdapter(),
            gate_sequence=(("B",), ("C",)),
            implementation_version="controlled_multi_future_runtime_v3_4_1",
            planner_only=True,
        )
        self.assertTrue(gate.planner_only)
        self.assertEqual(gate.gate_sequence, (("B",), ("C",)))
        self.assertIn(
            "planner_only=True", inspect.getsource(F4BCPreflightGateV11)
        )
        self.assertIn(
            "F4ExactCorridorSelectionGateV11",
            inspect.getsource(F4ExactCorridorAExecutionGateV11),
        )

    def test_runner_guard_and_source_bindings_cover_v3_4_1(self):
        runner_source = inspect.getsource(runtime_v3_4_1_scope_runner)
        guard_source = inspect.getsource(gpu_guard_v2_4)
        for scope in (
            "F2_inside_targeted_v11",
            "F3_three_context_targeted_v11",
            "F4_exact_corridor_A_v11",
            "F4_BC_preflight_v11",
        ):
            self.assertIn(scope, runner_source)
        self.assertIn("scope in FULL_ROOT_SCOPES", runner_source)
        self.assertEqual(len(SUPPORTED_SCOPES), 8)
        self.assertIn("load_authorization_v3_4_1", guard_source)
        self.assertIn("consume_authorization_once_v3_4_1", guard_source)
        bindings = current_source_bindings_v3_4_1()
        for key in (
            "scope_runner_sha256",
            "gpu_guard_sha256",
            "common_counter_schema_sha256",
            "f2_preload_entry_gate_sha256",
            "f3_three_context_runner_sha256",
            "f4_exact_selection_sha256",
            "f4_exact_A_gate_sha256",
            "joint_limit_audit_sha256",
        ):
            self.assertEqual(len(bindings[key]), 64)


if __name__ == "__main__":
    unittest.main()
