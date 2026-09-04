#!/usr/bin/env python3
"""Pure-CPU tests for the exact successor-bound F2 auditor V1.1."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

import auditor_v1_1 as auditor


LEGACY_TEST_PATH = auditor.AUDIT_ROOT / (
    "f2_controlled_insertion_route_gate_postrun_auditor_v1/test_auditor.py"
)
LEGACY_TEST_SHA256 = (
    "a0cb73a8c37d3ebb8d80609a766164c180020d2419ec6e5a3fe5b9d9918fc2c6"
)


def load_legacy_tests():
    if auditor.file_sha(LEGACY_TEST_PATH) != LEGACY_TEST_SHA256:
        raise RuntimeError("hash-frozen V1 auditor tests changed")
    spec = importlib.util.spec_from_file_location(
        "cmf_f2_postrun_auditor_v1_tests_frozen", LEGACY_TEST_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen V1 auditor tests")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get("auditor")
    sys.modules["auditor"] = auditor
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop("auditor", None)
        else:
            sys.modules["auditor"] = previous
    return module


legacy = load_legacy_tests()


class SuccessorScientificAndGuardTests(legacy.PostrunAuditorTests):
    """Re-run every V1 positive/negative test against the successor binding."""


class SuccessorLineageTests(unittest.TestCase):
    def test_exact_disk_lineage_passes(self):
        manifest = json.loads(
            auditor.EXPECTED_MANIFEST_PATH.read_text(encoding="utf-8")
        )
        lineage = auditor.validate_successor_lineage_from_disk(manifest)
        self.assertTrue(lineage["parent_equivalent_after_four_path_normalizations"])
        self.assertEqual(lineage["dispatch_ordinal"], 2)
        self.assertEqual(lineage["scientific_attempt_ordinal"], 1)

    def test_lineage_tamper_fails_closed(self):
        fixture = legacy.valid_fixture()
        fixture["manifest"] = deepcopy(fixture["manifest"])
        fixture["manifest"]["dispatch_ordinal"] = 3
        payload = dict(fixture["manifest"])
        payload.pop("manifest_sha256")
        fixture["manifest"]["manifest_sha256"] = auditor.canonical_hash(payload)
        report = auditor.audit_documents(**fixture)
        self.assertFalse(report["pass"])
        self.assertEqual(report["failure"]["code"], "successor_lineage_contract")

    def test_pre_run_cli_boundary_is_read_only_and_fail_closed(self):
        self.assertFalse(auditor.EXPECTED_OUTPUT_NAMESPACE.exists())
        self.assertFalse(auditor.EXPECTED_GUARD_DIRECTORY.exists())
        report = auditor.run_audit()
        self.assertFalse(report["pass"])
        self.assertEqual(report["failure"]["code"], "job_start_missing")
        self.assertFalse(auditor.EXPECTED_OUTPUT_NAMESPACE.exists())
        self.assertFalse(auditor.EXPECTED_GUARD_DIRECTORY.exists())

    def test_frozen_base_auditor_identity(self):
        self.assertEqual(
            auditor.file_sha(auditor.BASE_AUDITOR_PATH),
            auditor.BASE_AUDITOR_SHA256,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
