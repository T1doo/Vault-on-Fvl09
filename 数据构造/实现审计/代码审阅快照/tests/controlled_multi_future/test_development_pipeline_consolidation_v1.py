import json
from pathlib import Path
import unittest

from controlled_multi_future.canonical_artifact import canonical_hash_json
from controlled_multi_future.development_pipeline_consolidation_v1 import (
    build_cpu_registry_v1,
    build_parent_authorization_v1,
)


AUDIT = Path("/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计")


class DevelopmentPipelineConsolidationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = json.loads(
            (AUDIT / "F2_OFFICIAL_ASSET_COMPATIBILITY_MATRIX_V3.json").read_text(
                encoding="utf-8"
            )
        )
        cls.screening = json.loads(
            (AUDIT / "F2_CPU_STATIC_SCREENING_V3.json").read_text(encoding="utf-8")
        )

    def test_parent_keeps_stage1_and_formal_disabled(self):
        parent = build_parent_authorization_v1()
        payload = dict(parent)
        digest = payload.pop("parent_user_authorization_sha256")
        self.assertEqual(canonical_hash_json(payload), digest)
        self.assertFalse(parent["stage1_authorized"])
        self.assertFalse(parent["formal_collection_authorized"])
        self.assertEqual(parent["allowed_physical_gpu_indices"], list(range(8)))

    def test_registry_contains_exact_f2_f3_f4_bounded_sets(self):
        registry = build_cpu_registry_v1(self.matrix, self.screening)
        self.assertEqual(registry["f2"]["candidate_ranks"], list(range(50, 62)))
        self.assertEqual(registry["f3"]["candidate_count"], 12)
        self.assertEqual(registry["f3"]["maximum_physical_candidate_count"], 4)
        self.assertEqual(registry["f4"]["candidate_count"], 6)
        self.assertLessEqual(registry["f4"]["candidate_count"], 12)
        payload = dict(registry)
        digest = payload.pop("registry_sha256")
        self.assertEqual(canonical_hash_json(payload), digest)


if __name__ == "__main__":
    unittest.main()
