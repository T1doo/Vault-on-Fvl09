import ast
import inspect
from pathlib import Path
import unittest

from controlled_multi_future.probes import (
    a0_real_sapien_adapter_smoke,
    gpu_guard_v2_1,
    runtime_v3_1_family_repair_runner,
    runtime_v3_1_root_runner,
)


class V5CurrentEntrypointsStaticTest(unittest.TestCase):
    def test_a0_cli_uses_only_bound_v1_2_components_and_no_free_run_parameters(self):
        source = inspect.getsource(a0_real_sapien_adapter_smoke)
        self.assertIn("A0CurrentAnchorOrchestratorV1_2", source)
        self.assertIn("RoboTwinRealSapienPilotRootAdapterV1_2", source)
        self.assertIn("load_authorization_v1_1", source)
        self.assertIn("require_atomic_gpu_guard_v2_1", source)
        self.assertNotIn("a0_orchestrator_v1_1 import", source)
        self.assertNotIn('add_argument("--family"', source)
        self.assertNotIn('add_argument("--output"', source)
        self.assertNotIn('add_argument("--seed"', source)
        self.assertNotIn('add_argument("--timeout"', source)

    def test_future_family_entrypoints_use_v1_1_authorization_guard_and_v1_2_adapter(self):
        for module in (runtime_v3_1_root_runner, runtime_v3_1_family_repair_runner):
            source = inspect.getsource(module)
            self.assertIn("RoboTwinRealSapienPilotRootAdapterV1_2", source)
            self.assertIn("load_authorization_v1_1", source)
            self.assertIn("load_consumption_receipt", source)
            self.assertIn("require_atomic_gpu_guard_v2_1", source)
            self.assertIn("validate_runtime_receipt_against_budget", source)
            self.assertNotIn("runtime_v3_1_authorization import", source)

    def test_guard_has_no_import_time_gpu_or_subprocess_call(self):
        source = inspect.getsource(gpu_guard_v2_1)
        tree = ast.parse(source)
        top_level_calls = [node for node in tree.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)]
        self.assertEqual(top_level_calls, [])
        main_source = inspect.getsource(gpu_guard_v2_1.main)
        self.assertLess(main_source.index("load_authorization_v1_1"), main_source.index("snapshot("))
        self.assertLess(main_source.index("consume_authorization_once"), main_source.index("subprocess.Popen"))

    def test_current_entrypoints_keep_stage0_and_formal_flags_false(self):
        sources = "\n".join(
            inspect.getsource(module)
            for module in (
                a0_real_sapien_adapter_smoke,
                runtime_v3_1_root_runner,
                runtime_v3_1_family_repair_runner,
                gpu_guard_v2_1,
            )
        )
        self.assertNotIn('"stage0_authorized": True', sources)
        self.assertNotIn('"formal_data": True', sources)
        self.assertNotIn('"stage0_data": True', sources)

    def test_historical_gpu_clis_are_explicitly_disabled(self):
        probe_root = Path(__file__).resolve().parents[2] / "controlled_multi_future" / "probes"
        self.assertIn("superseded and disabled", (probe_root / "gpu_guard.py").read_text())
        self.assertIn("probe budget is exhausted", (probe_root / "action_feasibility_v2.py").read_text())
        self.assertIn("historical scene-inspection CLI is disabled", (probe_root / "scene_inspection.py").read_text())
        self.assertIn("historical GPU environment-certification CLI is disabled", (probe_root / "environment_certification.py").read_text())


if __name__ == "__main__":
    unittest.main()
