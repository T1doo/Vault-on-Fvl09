from pathlib import Path
import json
import tempfile
import unittest

import numpy as np

from controlled_multi_future.canonical_artifact import (
    CanonicalArtifactError,
    build_self_hashed_receipt,
    canonical_hash_json,
    canonical_json_bytes,
    canonical_jsonable,
    canonical_write_json,
    validate_self_hashed_receipt,
)
from controlled_multi_future.f2_asset_bound_runtime_v3 import (
    _hash_json as f2_runtime_hash_json,
)
from controlled_multi_future.f1_batch_generation_pilot_v1 import (
    build_f1_batch_pilot_plan_v1,
)
from controlled_multi_future.f3_common_grasp_prefix_v2 import (
    build_f3_common_grasp_prefix_v2,
)
from controlled_multi_future.f4_layout_candidate_search_v2 import (
    build_f4_layout_candidate_search_v2,
)


class CanonicalArtifactV1Test(unittest.TestCase):
    def test_nested_numpy_bool(self):
        self.assertEqual(
            canonical_jsonable({"outer": [{"passed": np.bool_(True)}]}),
            {"outer": [{"passed": True}]},
        )

    def test_numpy_scalars(self):
        value = canonical_jsonable(
            {"integer": np.int64(7), "floating": np.float32(1.25), "boolean": np.bool_(False)}
        )
        self.assertEqual(value, {"integer": 7, "floating": 1.25, "boolean": False})

    def test_ndarray_and_nested_tuple_list_dict(self):
        value = {"array": np.asarray([[1, 2], [3, 4]]), "nested": (1, [2, {"x": (3,)}])}
        self.assertEqual(
            canonical_jsonable(value),
            {"array": [[1, 2], [3, 4]], "nested": [1, [2, {"x": [3]}]]},
        )

    def test_nan_inf_and_unsupported_rejected(self):
        for value in (float("nan"), float("inf"), np.float64("-inf")):
            with self.assertRaises(CanonicalArtifactError):
                canonical_jsonable({"value": value})
        with self.assertRaises(CanonicalArtifactError):
            canonical_jsonable({"path": Path("unsupported")})
        with self.assertRaises(CanonicalArtifactError):
            canonical_jsonable({1: "non-string-key"})

    def test_hash_is_deterministic(self):
        left = {"b": np.int32(2), "a": [np.bool_(True), np.float64(1.5)]}
        right = {"a": [True, 1.5], "b": 2}
        self.assertEqual(canonical_hash_json(left), canonical_hash_json(right))
        self.assertEqual(canonical_json_bytes(left), canonical_json_bytes(right))

    def test_write_read_rehash_equality(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            value = {"array": np.asarray([1, 2]), "passed": np.bool_(True)}
            descriptor = canonical_write_json(path, value)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(canonical_hash_json(value), canonical_hash_json(loaded))
            self.assertEqual(descriptor["canonical_payload_sha256"], canonical_hash_json(value))

    def test_self_hashed_receipt_round_trip(self):
        receipt = build_self_hashed_receipt({"value": np.int64(3)})
        self.assertEqual(validate_self_hashed_receipt(receipt), receipt)
        receipt["value"] = 4
        with self.assertRaises(CanonicalArtifactError):
            validate_self_hashed_receipt(receipt)

    def test_f2_passive_on_real_schema_fixture(self):
        fixture = {
            "schema_version": "cmf_f2_asset_bound_passive_on_audit_v3",
            "candidate_key_sha256": "a" * 64,
            "passive_250hz_settle_verified": np.bool_(True),
            "continuous_scale_support": np.bool_(True),
            "stable_window_pass": np.bool_(False),
            "last50": {
                "linear_speed_mps": np.asarray([0.0, 0.001]),
                "angular_speed_rps": np.asarray([0.0, 0.002]),
            },
            "formal_data": False,
            "stage0_data": False,
        }
        receipt = build_self_hashed_receipt(fixture)
        self.assertTrue(validate_self_hashed_receipt(receipt)["passive_250hz_settle_verified"])
        self.assertEqual(
            f2_runtime_hash_json(fixture),
            canonical_hash_json(fixture),
        )

    def test_f1_f3_hashes_and_intentionally_repaired_f4_hash_are_frozen(self):
        expected = {
            "f1": "60d303df5392b139eac29ed189e287e77988c08b6ee7554e1e4b1941451a78e7",
            "f3": "570520bb3d6799a1667177256c5ce9ead5d732ae9ce13ca2922c7a371981d4a5",
            "f4": "25ddeb4596d405ea2f9cc49f4c0225fff04f4b66aeb7362c0cb715c1cb5af8d3",
        }
        actual = {
            "f1": canonical_hash_json(build_f1_batch_pilot_plan_v1()),
            "f3": canonical_hash_json(build_f3_common_grasp_prefix_v2()),
            "f4": canonical_hash_json(build_f4_layout_candidate_search_v2()),
        }
        self.assertEqual(actual, expected)
        self.assertNotEqual(
            actual["f4"],
            "91393164e99d9f04deeea08987ba6284c33a29556b016606f90f94bb2b4a29d2",
        )


if __name__ == "__main__":
    unittest.main()
