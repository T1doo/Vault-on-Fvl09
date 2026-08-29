import json
from pathlib import Path
import tempfile
import unittest

from controlled_multi_future.evidence_manifest_v1 import (
    build_evidence_manifest,
    write_evidence_manifest,
)


class EvidenceManifestV1Test(unittest.TestCase):
    def test_manifest_is_sorted_byte_bound_and_write_once(self):
        root = Path("/nfs_share/lijunhui/Robotwin2/tmp")
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            directory = Path(directory)
            namespace = directory / "namespace"
            namespace.mkdir()
            (namespace / "b.bin").write_bytes(b"b")
            (namespace / "a.json").write_text('{"a":1}\n', encoding="utf-8")
            value = build_evidence_manifest(namespace)
            self.assertEqual(
                [item["relative_path"] for item in value["files"]],
                ["a.json", "b.bin"],
            )
            output = directory / "manifest.json"
            written = write_evidence_manifest(namespace, output)
            self.assertEqual(json.loads(output.read_text()), written)
            with self.assertRaises(FileExistsError):
                write_evidence_manifest(namespace, output)


if __name__ == "__main__":
    unittest.main()
