#!/usr/bin/env python3
"""F4 reopen2 runner with side-effect-free dispatch preflight."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys


RUNTIME_DIR = Path(__file__).resolve().parent
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from manifest_contract import (  # noqa: E402
    canonical_hash,
    file_sha,
    load_and_validate_manifest_job,
)


BASE_RUNNER = Path("/nfs_share/lijunhui/Robotwin2/production_micro_gate_v1/job_runner.py")
BASE_RUNNER_SHA256 = "376ddfbe07b1c9ae3e6e3b2d1975344a8605c6e81e49f27e92241c88a851a1d4"


def _load_base_runner():
    if file_sha(BASE_RUNNER) != BASE_RUNNER_SHA256:
        raise RuntimeError("sealed base F4 runner changed")
    spec = importlib.util.spec_from_file_location("cmf_f4_reopen2_base_runner", BASE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load sealed base F4 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def select_f4_dispatch_pre_gpu(manifest_path: Path, job_id: str) -> dict:
    """Validate the exact runtime dispatch without creating a scene or output."""

    validated = load_and_validate_manifest_job(manifest_path, job_id)
    manifest = validated["manifest"]
    job = validated["job"]
    base = _load_base_runner()
    dispatch = getattr(base, "run_f4_development_r_pc_root", None)
    if not callable(dispatch):
        raise RuntimeError("bound runner lacks F4 development-root dispatch")
    template_path = Path(job["template_gate_terminal_path"])
    if file_sha(template_path) != job["template_gate_terminal_file_sha256"]:
        raise RuntimeError("F4 template terminal file changed")
    template = json.loads(template_path.read_text(encoding="utf-8"))
    template_payload = dict(template)
    template_digest = template_payload.pop("receipt_sha256", None)
    if (
        template_digest != canonical_hash(template_payload)
        or template_digest != job["template_gate_receipt_sha256"]
        or template.get("status") != "F4_FULL_PROGRAM_TEMPLATE_QUALIFICATION_PASS"
        or template.get("terminal_matrix", {}).get("full_program_pass") is not True
    ):
        raise RuntimeError("F4 template terminal is not the exact Run9 qualification")
    from controlled_multi_future.f4_full_program_physical_v1 import (
        PROGRAM_IDS,
        build_f4_full_program_physical_spec_v1,
    )
    from controlled_multi_future.planner_qualification_manifests_v2_3 import (
        build_f4_program_panel_manifest_v1_1,
    )

    panel = build_f4_program_panel_manifest_v1_1()
    source = panel["source_candidate"]
    candidate = panel["candidates"][0]
    if (
        candidate["candidate_id"] != job["candidate_id"]
        or candidate["candidate_sha256"] != job["candidate_sha256"]
        or list(PROGRAM_IDS) != job["program_order"]
    ):
        raise RuntimeError("F4 panel candidate or program order changed")
    full_specs = {}
    planner_receipts = {}
    for program_id in PROGRAM_IDS:
        record = job["source_planner_terminals"][program_id]
        source_path = Path(record["path"])
        if file_sha(source_path) != record["file_sha256"]:
            raise RuntimeError(f"F4 {program_id} planner source file changed")
        envelope = json.loads(source_path.read_text(encoding="utf-8"))
        prior_spec = envelope.get("spec")
        terminal = envelope.get("terminal")
        if not isinstance(prior_spec, dict) or not isinstance(terminal, dict):
            raise RuntimeError(f"F4 {program_id} planner source is incomplete")
        terminal_payload = dict(terminal)
        terminal_digest = terminal_payload.pop("receipt_sha256", None)
        if terminal_digest != canonical_hash(terminal_payload):
            raise RuntimeError(f"F4 {program_id} planner terminal hash mismatch")
        full_specs[program_id] = build_f4_full_program_physical_spec_v1(
            source,
            candidate,
            terminal,
            program_id=program_id,
            slot_id=prior_spec["slot_id"],
            planner_reset_nonce=prior_spec["planner_reset_nonce"],
            isolation_gate_receipt_sha256=job["isolation_gate_receipt_sha256"],
        )
        planner_receipts[program_id] = terminal_digest
    planned_hashes = {
        spec["legacy_scene_spec_sha256"] for spec in full_specs.values()
    }
    if planned_hashes != {job["planned_scene_spec_sha256"]}:
        raise RuntimeError("F4 full-program specs do not share the frozen scene")
    if Path(validated["output_namespace"]).exists():
        raise RuntimeError("F4 preflight unexpectedly created output namespace")
    result = {
        "schema_version": "cmf_f4_reopen2_runner_dispatch_preflight_v1",
        "manifest_sha256": manifest["manifest_sha256"],
        "job_id": job_id,
        "dispatch_function": "run_f4_development_r_pc_root",
        "dispatch_callable": True,
        "program_order": list(PROGRAM_IDS),
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": candidate["candidate_sha256"],
        "planned_scene_spec_sha256": next(iter(planned_hashes)),
        "full_program_spec_sha256s": {
            key: value["spec_sha256"] for key, value in full_specs.items()
        },
        "planner_terminal_receipt_sha256s": planner_receipts,
        "scene_created": False,
        "output_created": False,
        "lease_acquired": False,
        "nvidia_smi_called": False,
        "gpu_context_created": False,
        "authorization_consumed": False,
        "pass": True,
    }
    result["receipt_sha256"] = canonical_hash(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight_only:
        print(
            json.dumps(
                select_f4_dispatch_pre_gpu(args.manifest, args.job_id),
                sort_keys=True,
                ensure_ascii=False,
            )
        )
        return 0
    base = _load_base_runner()

    def shared_loader(path):
        return load_and_validate_manifest_job(Path(path), args.job_id)["manifest"]

    base.load_manifest = shared_loader
    return base.main(["--manifest", str(args.manifest), "--job-id", args.job_id])


if __name__ == "__main__":
    raise SystemExit(main())
