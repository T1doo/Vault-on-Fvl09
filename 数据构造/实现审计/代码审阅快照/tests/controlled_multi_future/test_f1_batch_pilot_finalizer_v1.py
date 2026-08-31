import unittest

from controlled_multi_future.current_hasher import hash_json
from controlled_multi_future.f1_batch_generation_pilot_v1 import (
    build_f1_batch_pilot_plan_v1,
)
from controlled_multi_future.f1_batch_pilot_finalizer_v1 import (
    build_reserve_activation_receipt_v1,
    finalize_f1_batch_pilot_v1,
)


def _receipt(slot_id, passed):
    value = {
        "root_slot_id": slot_id,
        "accepted_development_root": passed,
        "pass": passed,
        "root_status": "accepted" if passed else "failed_planner",
        "trajectory_count": 3 if passed else 0,
        "elapsed_seconds": 10.0,
        "formal_data": False,
        "stage0_data": False,
        "stage1_authorized": False,
        "accepted_root_increment": 0,
    }
    value["receipt_sha256"] = hash_json(value)
    return value


class F1BatchPilotFinalizerV1Test(unittest.TestCase):
    def test_five_primary_pass(self):
        plan = build_f1_batch_pilot_plan_v1()
        receipts = {
            item["slot_id"]: _receipt(item["slot_id"], True)
            for item in plan["primary_slots"]
        }
        result = finalize_f1_batch_pilot_v1(
            plan=plan, root_receipts=receipts, reserve_activations=[]
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["accepted_trajectory_count"], 15)

    def test_first_failed_primary_activates_first_reserve(self):
        plan = build_f1_batch_pilot_plan_v1()
        failed = plan["primary_slots"][0]["slot_id"]
        activation = build_reserve_activation_receipt_v1(
            plan=plan, failed_slot_id=failed, prior_activations=[]
        )
        receipts = {
            item["slot_id"]: _receipt(item["slot_id"], item["slot_id"] != failed)
            for item in plan["primary_slots"]
        }
        receipts[activation["reserve_slot_id"]] = _receipt(
            activation["reserve_slot_id"], True
        )
        result = finalize_f1_batch_pilot_v1(
            plan=plan,
            root_receipts=receipts,
            reserve_activations=[activation],
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["accepted_root_count"], 5)

    def test_cannot_skip_first_reserve(self):
        plan = build_f1_batch_pilot_plan_v1()
        activation = build_reserve_activation_receipt_v1(
            plan=plan,
            failed_slot_id=plan["primary_slots"][0]["slot_id"],
            prior_activations=[],
        )
        activation["reserve_slot_id"] = plan["ordered_reserve_slots"][1]["slot_id"]
        result = finalize_f1_batch_pilot_v1(
            plan=plan,
            root_receipts={
                item["slot_id"]: _receipt(item["slot_id"], False)
                for item in plan["primary_slots"]
            },
            reserve_activations=[activation],
        )
        self.assertFalse(result["checks"]["activation_sequence"])


if __name__ == "__main__":
    unittest.main()
