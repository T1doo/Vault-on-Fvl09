import json
import unittest
from pathlib import Path

from controlled_multi_future.canonical_artifact import canonical_hash_json
from controlled_multi_future.production_recovery_v1 import (
    build_production_recovery_contract_v1,
    build_unconsumed_wave_supersession_receipt_v1,
    validate_unconsumed_wave_for_supersession_v1,
)


WORKSPACE = Path("/nfs_share/lijunhui")


class ProductionRecoveryV1Test(unittest.TestCase):
    def test_contract_points_to_physical_evidence_not_broad_panel(self):
        value = build_production_recovery_contract_v1()
        self.assertFalse(value["f4"]["full_1696_query_panel_next"])
        self.assertTrue(value["f2"]["legacy_dispatcher_disabled"])
        self.assertFalse(value["f3"]["planner_stage_b_proves_physical_grasp"])
        self.assertEqual(value["phase_a_budget"]["gpu"], 0)
        payload = dict(value)
        digest = payload.pop("contract_sha256")
        self.assertEqual(digest, canonical_hash_json(payload))

    def test_source_lock_covers_current_f2_and_f3_asset_universe(self):
        value = build_production_recovery_contract_v1()
        f2 = set(value["runtime_source_lock_assets"]["F2"])
        f3 = set(value["runtime_source_lock_assets"]["F3"])
        for relative in (
            "assets/objects/071_can/model_data0.json",
            "assets/objects/071_can/model_data5.json",
            "assets/objects/062_plasticbox/model_data2.json",
            "assets/objects/062_plasticbox/model_data8.json",
            "assets/objects/074_displaystand/model_data0.json",
        ):
            self.assertIn(relative, f2)
        for model_id in (15, 5, 4, 13):
            self.assertIn(
                f"assets/objects/001_bottle/model_data{model_id}.json", f3
            )

    def test_current_replacement_wave_is_eligible_only_for_supersession(self):
        path = WORKSPACE / (
            "Vault-on-Fvl09/数据构造/实现审计/"
            "planner_wiring_smoke_v1_replacement_wave_20260903_run2/meta.json"
        )
        meta = json.loads(path.read_text(encoding="utf-8"))
        checked = validate_unconsumed_wave_for_supersession_v1(
            meta,
            expected_wave_id="planner-wiring-smoke-v1-replacement-20260903-run2",
        )
        self.assertFalse(checked["operational_execution_started"])
        root = path.parent
        for directory in ("issued", "terminals", "skipped", "closures"):
            target = root / directory
            self.assertTrue(not target.exists() or not any(target.iterdir()))
        f2 = json.loads((root / "source_lock_f2.json").read_text(encoding="utf-8"))
        f3 = json.loads((root / "source_lock_f3.json").read_text(encoding="utf-8"))
        receipt = build_unconsumed_wave_supersession_receipt_v1(
            meta,
            f2_source_lock=f2,
            f3_source_lock=f3,
            ledger_entry_counts={
                "issued": 0,
                "terminals": 0,
                "skipped": 0,
                "closures": 0,
            },
            superseding_plan_path="数据构造/实现审计/plan.md",
        )
        self.assertEqual(
            receipt["status"],
            "SUPERSEDED_UNCONSUMED_BY_PRODUCTION_RECOVERY_V1",
        )
        self.assertIn(
            "assets/objects/071_can/model_data0.json",
            receipt["source_lock_missing_current_assets"]["F2"],
        )
        self.assertIn(
            "assets/objects/001_bottle/model_data15.json",
            receipt["source_lock_missing_current_assets"]["F3"],
        )


if __name__ == "__main__":
    unittest.main()
