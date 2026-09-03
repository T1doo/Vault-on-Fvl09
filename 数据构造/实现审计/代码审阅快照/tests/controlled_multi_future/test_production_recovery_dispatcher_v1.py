import unittest
from unittest.mock import patch

from controlled_multi_future.production_recovery_dispatcher_v1 import (
    RUNNER_SYMBOLS,
    build_production_recovery_adapter_v1,
    dispatch_production_recovery_v1,
)


class ProductionRecoveryDispatcherV1Test(unittest.TestCase):
    def test_each_exact_job_kind_routes_once(self):
        cases = (
            (
                "F2_CONTROLLED_INSERTION_PHYSICAL",
                "run_f2_controlled_insertion_physical_v2",
                None,
            ),
            ("F3_SHARED_V_PHYSICAL", "run_f3_shared_v_physical_v1", None),
            (
                "F4_BOUNDED_PHYSICAL_MICRO",
                "run_f4_bounded_physical_micro_v1",
                lambda _: {},
            ),
        )
        for job_kind, function, callback in cases:
            with self.subTest(job_kind=job_kind), patch(
                f"controlled_multi_future.production_recovery_dispatcher_v1.{function}",
                return_value={"job_kind": job_kind},
            ) as runner:
                result = dispatch_production_recovery_v1(
                    object(),
                    job_kind=job_kind,
                    runner_symbol=RUNNER_SYMBOLS[job_kind],
                    spec={"family": job_kind[:2]},
                    capture_anchor_callback=callback,
                )
                self.assertEqual(result["job_kind"], job_kind)
                self.assertEqual(runner.call_count, 1)

    def test_wrong_symbol_and_missing_f4_callback_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "symbol mismatch"):
            dispatch_production_recovery_v1(
                object(),
                job_kind="F2_CONTROLLED_INSERTION_PHYSICAL",
                runner_symbol="wrong",
                spec={},
            )

    def test_adapter_factory_uses_only_validated_embedded_scene_spec(self):
        checked = {"legacy_scene_spec": {"family": "F2"}}

        class Adapter:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        with patch(
            "controlled_multi_future.production_recovery_dispatcher_v1."
            "validate_f2_controlled_insertion_physical_spec_v2",
            return_value=checked,
        ), patch(
            "controlled_multi_future.production_recovery_dispatcher_v1."
            "RoboTwinRealSapienF2HierarchicalStageAV1Adapter",
            Adapter,
        ):
            adapter = build_production_recovery_adapter_v1(
                job_kind="F2_CONTROLLED_INSERTION_PHYSICAL",
                spec={"untrusted": True},
                output_root=__import__("pathlib").Path(
                    "/nfs_share/lijunhui/Robotwin2/tmp/not-created"
                ),
                expected_implementation_source_sha256="a" * 64,
            )
        self.assertEqual(adapter.kwargs["planned_spec"], checked["legacy_scene_spec"])
        with self.assertRaisesRegex(ValueError, "anchor callback"):
            dispatch_production_recovery_v1(
                object(),
                job_kind="F4_BOUNDED_PHYSICAL_MICRO",
                runner_symbol=RUNNER_SYMBOLS["F4_BOUNDED_PHYSICAL_MICRO"],
                spec={},
            )


if __name__ == "__main__":
    unittest.main()
