import unittest

from controlled_multi_future.canonical_artifact import canonical_hash_json
from controlled_multi_future.f4_collision_capability_audit_v1 import (
    build_f4_collision_capability_audit_v1,
)


class F4CollisionCapabilityAuditV1Test(unittest.TestCase):
    def test_table_only_planner_forces_physical_micro_gate(self):
        value = build_f4_collision_capability_audit_v1()
        self.assertTrue(value["pass"])
        self.assertFalse(
            value["table_only_planner_can_qualify_physical_noninterference"]
        )
        self.assertFalse(
            value["full_1696_query_panel_recommended_before_physical_micro_gate"]
        )
        self.assertEqual(
            value["selected_recovery_route"],
            "bounded_staged_physical_noninterference",
        )
        payload = dict(value)
        digest = payload.pop("receipt_sha256")
        self.assertEqual(digest, canonical_hash_json(payload))


if __name__ == "__main__":
    unittest.main()
