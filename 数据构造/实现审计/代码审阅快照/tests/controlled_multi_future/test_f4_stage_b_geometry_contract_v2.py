import unittest

from controlled_multi_future.f4_hierarchical_template_search_v1 import (
    build_f4_hierarchical_template_search_v1,
    build_f4_stage_b_candidates_v1,
    select_f4_stage_a_source_v1,
)
from controlled_multi_future.f4_stage_b_geometry_contract_v2 import (
    EXTRA_SAFETY_CLEARANCE_M,
    audit_obb_clearance_v2,
    audit_translation_sweep_v2,
    legacy_r01_invalidation_v2,
)


IDENTITY = [1.0, 0.0, 0.0, 0.0]


class F4StageBGeometryContractV2Tests(unittest.TestCase):
    @staticmethod
    def _stage_a_terminal():
        contract = build_f4_hierarchical_template_search_v1()
        gates = contract["stage_a_required_gates"]
        receipts = [
            {
                "candidate_id": item["candidate_id"],
                "candidate_sha256": item["candidate_sha256"],
                "checks": {
                    gate: item["rank"] == 1 for gate in gates
                },
                "cleanup_safety_pass": True,
                "orphan_process_count": 0,
            }
            for item in contract["stage_a_candidates"]
        ]
        return contract, select_f4_stage_a_source_v1(contract, receipts)

    def test_legacy_r01_is_invalid_before_planner(self):
        receipt = legacy_r01_invalidation_v2()
        self.assertEqual(
            receipt["status"],
            "INVALID_BY_CONSTRUCTION_TARGET_OVERLAPS_UNMOVED_OBJECT",
        )
        self.assertFalse(receipt["geometry_audit"]["construction_valid"])
        failures = receipt["geometry_audit"]["construction_failure_codes"]
        self.assertIn("ABC:A:TARGET_OVERLAPS_CURRENT_OTHER_OBJECT", failures)
        self.assertIn("ACB:A:TARGET_OVERLAPS_CURRENT_OTHER_OBJECT", failures)
        self.assertIn("BAC:B:TARGET_OVERLAPS_CURRENT_OTHER_OBJECT", failures)
        self.assertFalse(receipt["reexecution_required"])

    def test_exact_ten_millimeter_clearance_boundary(self):
        left = [0.0, 0.0, 0.8, *IDENTITY]
        just_below = [0.054 - 2e-9, 0.0, 0.8, *IDENTITY]
        exact = [0.054, 0.0, 0.8, *IDENTITY]
        self.assertFalse(audit_obb_clearance_v2(left, just_below)["pass"])
        self.assertTrue(audit_obb_clearance_v2(left, exact)["pass"])
        self.assertEqual(EXTRA_SAFETY_CLEARANCE_M, 0.010)

    def test_preplace_to_release_sweep_is_checked(self):
        start = [0.0, 0.0, 0.90, *IDENTITY]
        end = [0.0, 0.0, 0.764, *IDENTITY]
        obstacle = [0.0, 0.0, 0.82, *IDENTITY]
        self.assertFalse(
            audit_translation_sweep_v2(start, end, obstacle)["pass"]
        )

    def test_all_new_candidates_pass_all_programs_and_share_final_state(self):
        contract, terminal = self._stage_a_terminal()
        stage_b = build_f4_stage_b_candidates_v1(contract, terminal)
        self.assertEqual(len(stage_b["candidates"]), 8)
        for candidate in stage_b["candidates"]:
            with self.subTest(candidate=candidate["candidate_id"]):
                self.assertTrue(candidate["construction_valid"])
                self.assertEqual(candidate["construction_failure_codes"], [])
                self.assertGreaterEqual(
                    candidate["minimum_terminal_clearance_m"] + 1e-12,
                    EXTRA_SAFETY_CLEARANCE_M,
                )
                self.assertGreaterEqual(
                    candidate["minimum_swept_clearance_m"] + 1e-12,
                    EXTRA_SAFETY_CLEARANCE_M,
                )
                self.assertTrue(candidate["candidate_id"].startswith("f4-slot-corridor-hv2-"))
                audit = candidate["program_state_transition_audit"]
                self.assertEqual(set(audit["program_state_transition_audits"]), {"ABC", "ACB", "BAC"})
                self.assertTrue(audit["equal_final_world_state"])
                self.assertTrue(
                    all(
                        program["pass"]
                        for program in audit[
                            "program_state_transition_audits"
                        ].values()
                    )
                )
                for program in audit["program_state_transition_audits"].values():
                    for role in program["role_audits"]:
                        self.assertIn(
                            "preplace_to_release", role["sweep_clearance"]
                        )


if __name__ == "__main__":
    unittest.main()
