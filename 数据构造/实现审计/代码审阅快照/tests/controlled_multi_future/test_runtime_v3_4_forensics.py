import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from controlled_multi_future.runtime_v3_4_forensics import (
    _array_comparison,
    _seal_payload,
    validate_sealed_payload,
    write_forensic_pair,
)


class RuntimeV34ForensicsTest(unittest.TestCase):
    def test_payload_hash_detects_mutation(self):
        value = _seal_payload(
            {
                "design_version": "controlled_multi_future_f1_f4_v1_2",
                "implementation_version": "controlled_multi_future_runtime_v3_4",
                "formal_data": False,
                "stage0_data": False,
                "selected_row_indices": [0, 1],
            }
        )
        self.assertEqual(validate_sealed_payload(value), value)
        changed = dict(value)
        changed["stage0_data"] = True
        with self.assertRaises(ValueError):
            validate_sealed_payload(changed)

    def test_array_comparison_reports_first_byte_level_row(self):
        first = np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
        second = first.copy()
        second[1, 0] += 0.25
        result = _array_comparison(first, second)
        self.assertFalse(result["byte_equal"])
        self.assertEqual(result["first_different_row"], 1)
        self.assertEqual(result["maximum_absolute_difference_at_first_row"], 0.25)

    def test_write_pair_is_exclusive_and_machine_readable(self):
        root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        root.mkdir(parents=True, exist_ok=True)
        value = _seal_payload(
            {
                "design_version": "controlled_multi_future_f1_f4_v1_2",
                "implementation_version": "controlled_multi_future_runtime_v3_4",
                "formal_data": False,
                "stage0_data": False,
            }
        )
        with tempfile.TemporaryDirectory(dir=root) as directory:
            directory = Path(directory)
            json_path = directory / "artifact.json"
            md_path = directory / "artifact.md"
            receipt = write_forensic_pair(value, json_path, md_path, "test")
            self.assertEqual(json.loads(json_path.read_text()), value)
            self.assertIn(value["output_sha256"], md_path.read_text())
            self.assertEqual(receipt["output_sha256"], value["output_sha256"])
            with self.assertRaises(FileExistsError):
                write_forensic_pair(value, json_path, md_path, "test")


if __name__ == "__main__":
    unittest.main()
