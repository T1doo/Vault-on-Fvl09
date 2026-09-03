"""Disk-authoritative state machine for the V2.3.1a planner wiring smoke."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .canonical_artifact import (
    canonical_hash_json,
    canonical_jsonable,
    canonical_write_json,
)
from .planner_qualification_scene_bridges_v2_3_1 import (
    build_f3_stage_b_dependency_registry_v1_1,
    load_f3_stage_b_dependency_registry_v1_1,
)
from .planner_wiring_smoke_v2_3_1a import (
    build_updated_planner_wiring_smoke_v1_proposal_v2,
    validate_wave_approval_v2,
)


LEDGER_SCHEMA = "cmf_planner_wiring_smoke_wave_ledger_v1"
NORMALIZED_SCHEMA = "cmf_planner_wiring_smoke_normalized_terminal_v1"
BASE_SLOTS = ("S1", "S2", "S3", "S4", "S5")
CONDITIONAL_DEPENDENCIES = {
    "S6A": "S2",
    "S6B": "S5",
    "S7A": "S3",
    "S7B": "S7A",
}
ALL_SLOTS = BASE_SLOTS + tuple(CONDITIONAL_DEPENDENCIES)


def _workspace(path: Path, label: str, *, file=False) -> Path:
    value = Path(path).resolve()
    if not str(value).startswith("/nfs_share/lijunhui/"):
        raise ValueError(f"{label} is outside workspace")
    if file and not value.is_file():
        raise ValueError(f"{label} is not a file")
    return value


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path):
    return json.loads(_workspace(path, "ledger artifact", file=True).read_text(encoding="utf-8"))


def _self_hashed(value: Mapping[str, Any], key: str, label: str):
    result = canonical_jsonable(value)
    payload = dict(result)
    digest = payload.pop(key, None)
    if digest != canonical_hash_json(payload):
        raise ValueError(f"{label} hash mismatch")
    return result


def build_planner_wiring_smoke_wave_driver_v1_contract():
    proposal = build_updated_planner_wiring_smoke_v1_proposal_v2()
    value = {
        "schema_version": "cmf_planner_wiring_smoke_wave_driver_v1_contract",
        "ledger_schema": LEDGER_SCHEMA,
        "normalized_terminal_schema": NORMALIZED_SCHEMA,
        "ordered_slots": list(ALL_SLOTS),
        "base_slots": list(BASE_SLOTS),
        "conditional_dependencies": CONDITIONAL_DEPENDENCIES,
        "aggregate_budget": proposal["aggregate"],
        "prior_terminal_source": "validated immutable files only",
        "caller_supplied_prior_terminal_dict_allowed": False,
        "o_excl_per_slot_issuance": True,
        "o_excl_per_slot_terminal": True,
        "infrastructure_error_permanently_closes_wave": True,
        "f3_stage_b_registry_auto_built_from_stage_a_files": True,
        "operational_wave_approval_created": False,
        "planner_execution_authorized": False,
    }
    value["contract_sha256"] = canonical_hash_json(value)
    return value


def initialize_wave_ledger_v1(
    ledger_directory: Path,
    *,
    activation_contract: Mapping[str, Any],
    wave_approval: Mapping[str, Any],
):
    root = _workspace(ledger_directory, "wave ledger")
    if root.exists():
        raise FileExistsError("wave ledger must be new/O_EXCL")
    contract = _self_hashed(
        activation_contract, "contract_sha256", "activation contract"
    )
    approval = validate_wave_approval_v2(
        wave_approval, activation_contract=contract
    )
    root.mkdir(parents=True, exist_ok=False)
    for name in ("issued", "terminals", "skipped", "registries"):
        (root / name).mkdir()
    proposal = build_updated_planner_wiring_smoke_v1_proposal_v2()
    value = {
        "schema_version": LEDGER_SCHEMA,
        "wave_id": approval["wave_id"],
        "activation_contract": contract,
        "activation_contract_sha256": contract["contract_sha256"],
        "wave_approval": approval,
        "wave_approval_sha256": approval["wave_approval_sha256"],
        "proposal_sha256": proposal["proposal_sha256"],
        "manifest_bundle_sha256": proposal["manifest_bundle_sha256"],
        "ordered_job_slots": proposal["ordered_job_slots"],
        "aggregate_budget": proposal["aggregate"],
        "closed": False,
        "operational_execution_started": False,
    }
    value["ledger_sha256"] = canonical_hash_json(value)
    canonical_write_json(root / "meta.json", value, exclusive=True, mode=0o600)
    return value


def _load_meta(root: Path):
    value = _self_hashed(_load(root / "meta.json"), "ledger_sha256", "wave ledger")
    if value.get("schema_version") != LEDGER_SCHEMA:
        raise ValueError("wave ledger schema mismatch")
    validate_wave_approval_v2(
        value["wave_approval"], activation_contract=value["activation_contract"]
    )
    return value


def _load_dir(root: Path, name: str, key: str, *, wave_id: str):
    result = {}
    schemas = {
        "issued": "cmf_planner_wiring_smoke_slot_issuance_v1",
        "terminals": NORMALIZED_SCHEMA,
        "skipped": "cmf_planner_wiring_smoke_skipped_slot_v1",
    }
    for path in sorted((root / name).glob("*.json")):
        value = _self_hashed(_load(path), key, f"wave {name} entry")
        slot = value.get("slot")
        if (
            value.get("schema_version") != schemas[name]
            or value.get("wave_id") != wave_id
            or slot not in ALL_SLOTS
            or slot in result
            or path.stem != slot
        ):
            raise ValueError(f"wave {name} slot identity mismatch")
        if name == "issued":
            auth_path = _workspace(
                Path(value.get("authorization_receipt_path", "")),
                "issued authorization",
                file=True,
            )
            auth = _load(auth_path)
            if (
                _file_sha(auth_path)
                != value.get("authorization_receipt_file_sha256")
                or auth.get("receipt_sha256")
                != value.get("authorization_receipt_sha256")
                or auth.get("wave_id") != wave_id
                or auth.get("slot") != slot
            ):
                raise ValueError("issued authorization file binding mismatch")
        elif name == "terminals":
            required = {
                "authorization_receipt_path",
                "authorization_receipt_file_sha256",
                "authorization_receipt_sha256",
                "outer_terminal_path",
                "outer_terminal_file_sha256",
                "outer_terminal_receipt_sha256",
                "scene_instance_id",
                "scene_seed",
                "planner_query_count",
                "planner_pass",
                "failure_class",
                "failure_code",
                "scene_count",
                "elapsed_seconds",
                "guard_receipt_path",
                "guard_receipt_file_sha256",
                "guard_receipt_sha256",
                "cleanup_safety_pass",
                "orphan_process_count",
                "physical_execution_count",
                "trajectory_count",
            }
            if not required.issubset(value):
                raise ValueError("normalized terminal fields are incomplete")
            for path_key, sha_key, receipt_key in (
                (
                    "authorization_receipt_path",
                    "authorization_receipt_file_sha256",
                    "authorization_receipt_sha256",
                ),
                (
                    "outer_terminal_path",
                    "outer_terminal_file_sha256",
                    "outer_terminal_receipt_sha256",
                ),
                (
                    "guard_receipt_path",
                    "guard_receipt_file_sha256",
                    "guard_receipt_sha256",
                ),
            ):
                artifact = _workspace(
                    Path(value[path_key]), path_key, file=True
                )
                disk = _load(artifact)
                digest_key = (
                    "guard_receipt_sha256"
                    if path_key == "guard_receipt_path"
                    else "receipt_sha256"
                )
                disk_payload = dict(disk)
                disk_digest = disk_payload.pop(digest_key, None)
                if (
                    _file_sha(artifact) != value[sha_key]
                    or disk_digest != canonical_hash_json(disk_payload)
                    or disk_digest != value[receipt_key]
                ):
                    raise ValueError("normalized terminal artifact binding mismatch")
        result[slot] = value
    return result


def load_wave_ledger_state_v1(ledger_directory: Path):
    root = _workspace(ledger_directory, "wave ledger")
    meta = _load_meta(root)
    issued = _load_dir(
        root, "issued", "issuance_sha256", wave_id=meta["wave_id"]
    )
    terminals = _load_dir(
        root,
        "terminals",
        "normalized_terminal_sha256",
        wave_id=meta["wave_id"],
    )
    skipped = _load_dir(
        root, "skipped", "skip_sha256", wave_id=meta["wave_id"]
    )
    closed = _load(root / "closed.json") if (root / "closed.json").is_file() else None
    if closed is not None:
        closed = _self_hashed(closed, "closed_sha256", "wave closure")
    overlap = (set(terminals) & set(skipped)) | (set(issued) & set(skipped))
    if overlap:
        raise ValueError(f"wave ledger slot state overlaps: {sorted(overlap)}")
    aggregate = {
        "planner_query_count": sum(
            item["planner_query_count"] for item in terminals.values()
        ),
        "scene_count": sum(item["scene_count"] for item in terminals.values()),
        "elapsed_seconds": sum(
            item["elapsed_seconds"] for item in terminals.values()
        ),
        "physical_execution_count": sum(
            item["physical_execution_count"] for item in terminals.values()
        ),
        "trajectory_count": sum(
            item["trajectory_count"] for item in terminals.values()
        ),
    }
    budget = meta["aggregate_budget"]
    if (
        aggregate["planner_query_count"] > budget["planner_query_limit"]
        or aggregate["scene_count"] > budget["scene_limit"]
        or aggregate["elapsed_seconds"] > budget["wall_time_seconds"]
        or aggregate["physical_execution_count"]
        > budget["physical_execution_limit"]
        or aggregate["trajectory_count"] > budget["trajectory_limit"]
    ):
        raise RuntimeError("wave aggregate budget exceeded")
    return {
        "root": root,
        "meta": meta,
        "issued": issued,
        "terminals": terminals,
        "skipped": skipped,
        "closed": closed,
        "aggregate": aggregate,
    }


def validate_slot_issuance_from_ledger_v1(
    ledger_directory: Path, *, slot: str
):
    state = load_wave_ledger_state_v1(ledger_directory)
    if slot not in ALL_SLOTS:
        raise ValueError("unknown smoke slot")
    if state["closed"] is not None or (state["root"] / "wave_terminal.json").exists():
        raise PermissionError("wave is permanently closed")
    if slot in state["issued"] or slot in state["terminals"] or slot in state["skipped"]:
        raise FileExistsError("wave slot was already issued or resolved")
    if slot in BASE_SLOTS:
        index = BASE_SLOTS.index(slot)
        missing = [
            prior for prior in BASE_SLOTS[:index] if prior not in state["terminals"]
        ]
        if missing:
            raise PermissionError(f"base slot order incomplete: {missing}")
    else:
        missing_base = [item for item in BASE_SLOTS if item not in state["terminals"]]
        if missing_base:
            raise PermissionError("conditional slots require all S1-S5 terminals")
        dependency = CONDITIONAL_DEPENDENCIES[slot]
        prior = state["terminals"].get(dependency)
        if prior is None or prior.get("planner_pass") is not True:
            raise PermissionError("conditional planner-pass rule is not satisfied")
    return {
        "wave_id": state["meta"]["wave_id"],
        "slot": slot,
        "prior_normalized_terminal_sha256s": [
            state["terminals"][name]["normalized_terminal_sha256"]
            for name in ALL_SLOTS
            if name in state["terminals"]
        ],
        "aggregate_before_issuance": state["aggregate"],
    }


def record_slot_issuance_v1(
    ledger_directory: Path,
    *,
    slot: str,
    authorization_receipt_path: Path,
    authorization: Mapping[str, Any],
):
    decision = validate_slot_issuance_from_ledger_v1(
        ledger_directory, slot=slot
    )
    path = _workspace(authorization_receipt_path, "authorization", file=True)
    auth = canonical_jsonable(authorization)
    disk_auth = _load(path)
    if (
        disk_auth != auth
        or auth.get("wave_id") != decision["wave_id"]
        or auth.get("slot") != slot
        or auth.get("receipt_sha256") is None
        or auth.get("receipt_sha256")
        != canonical_hash_json(
            {key: item for key, item in auth.items() if key != "receipt_sha256"}
        )
    ):
        raise ValueError("issued authorization differs from wave slot")
    value = {
        "schema_version": "cmf_planner_wiring_smoke_slot_issuance_v1",
        **decision,
        "authorization_id": auth["authorization_id"],
        "authorization_receipt_path": str(path),
        "authorization_receipt_file_sha256": _file_sha(path),
        "authorization_receipt_sha256": auth["receipt_sha256"],
    }
    value["issuance_sha256"] = canonical_hash_json(value)
    canonical_write_json(
        state_root(ledger_directory) / "issued" / f"{slot}.json",
        value,
        exclusive=True,
        mode=0o600,
    )
    return value


def state_root(ledger_directory: Path):
    return _workspace(ledger_directory, "wave ledger")


def normalize_outer_terminal_from_disk_v1(
    *,
    authorization_receipt_path: Path,
    outer_terminal_path: Path,
    guard_receipt_path: Path,
):
    from .probes.planner_qualification_authorization_v2_3_1a import (
        SCOPE,
        validate as validate_authorization,
    )

    auth_path = _workspace(authorization_receipt_path, "authorization", file=True)
    outer_path = _workspace(outer_terminal_path, "outer terminal", file=True)
    guard_path = _workspace(guard_receipt_path, "guard receipt", file=True)
    auth = validate_authorization(
        _load(auth_path), requested_scope=SCOPE, allow_completed_paths=True
    )
    outer = _self_hashed(_load(outer_path), "receipt_sha256", "outer terminal")
    guard = _self_hashed(_load(guard_path), "guard_receipt_sha256", "guard receipt")
    expected_outer = Path(auth["output_namespace"]) / "receipt.json"
    binding = guard.get("binding", {})
    dispatch = outer.get("dispatch") if isinstance(outer.get("dispatch"), Mapping) else {}
    terminal = dispatch.get("job_terminal") if isinstance(dispatch.get("job_terminal"), Mapping) else {}
    cleanup = (
        dispatch.get("cleanup")
        if isinstance(dispatch.get("cleanup"), Mapping)
        else outer.get("cleanup")
        if isinstance(outer.get("cleanup"), Mapping)
        else {}
    )
    if dispatch:
        dispatch = _self_hashed(
            dispatch, "receipt_sha256", "dispatch terminal"
        )
        terminal = _self_hashed(
            terminal, "receipt_sha256", "family planner terminal"
        )
    if (
        outer.get("schema_version")
        != "cmf_planner_qualification_outer_terminal_v2_3_1a"
        or guard.get("schema_version") != "cmf_gpu_guard_v2_4_1"
        or outer_path != expected_outer.resolve()
        or guard_path != Path(auth["guard_receipt_path"]).resolve()
        or outer.get("wave_id") != auth["wave_id"]
        or outer.get("slot") != auth["slot"]
        or outer.get("job_kind") != auth["job_kind"]
        or outer.get("family") != auth["family"]
        or outer.get("authorization_id") != auth["authorization_id"]
        or outer.get("authorization_receipt_sha256") != auth["receipt_sha256"]
        or binding.get("authorization_id") != auth["authorization_id"]
        or binding.get("authorization_receipt_sha256") != auth["receipt_sha256"]
        or guard.get("purpose") != "planner_wiring_smoke_v1"
        or guard.get("status") not in {"completed", "completed_child_failed"}
        or outer.get("physical_execution_count") != 0
        or outer.get("trajectory_count") != 0
        or (
            dispatch
            and (
                dispatch.get("job_terminal_receipt_sha256")
                != terminal.get("receipt_sha256")
                or dispatch.get("planner_query_count")
                != outer.get("planner_query_count")
                or dispatch.get("planner_pass") != outer.get("planner_pass")
                or dispatch.get("failure_class")
                != outer.get("failure_class")
            )
        )
        or (
            outer.get("planner_pass") is True
            and not dispatch
        )
    ):
        raise ValueError("outer/auth/Guard binding mismatch")
    planner_pass = outer.get("planner_pass") is True
    failure_class = outer.get("failure_class")
    if planner_pass and failure_class is not None:
        raise ValueError("passing terminal cannot carry a failure class")
    if not planner_pass and failure_class not in {
        "PLANNER_CANDIDATE_FAIL",
        "INFRASTRUCTURE_ERROR",
    }:
        raise ValueError("failed terminal has invalid failure class")
    planner_count = outer.get("planner_query_count")
    scene_count = outer.get("scene_count")
    elapsed = outer.get("elapsed_seconds")
    if (
        not isinstance(planner_count, int)
        or not 0 <= planner_count <= auth["planner_query_limit"]
        or not isinstance(scene_count, int)
        or scene_count not in {0, 1}
        or not isinstance(elapsed, (int, float))
        or elapsed < 0
    ):
        raise ValueError("outer terminal accounting fields are invalid")
    cleanup_pass = bool(
        cleanup.get("cleanup_safety_pass") is True
        and guard.get("job_cache_cleanup", {}).get("succeeded") is True
        and guard.get("gpu_lease_release", {}).get("released") is True
        and guard.get("orphan_process_count") == 0
        and guard.get("postcheck_release", {}).get("verified") is True
    )
    value = {
        "schema_version": NORMALIZED_SCHEMA,
        "wave_id": auth["wave_id"],
        "slot": auth["slot"],
        "job_kind": auth["job_kind"],
        "family": auth["family"],
        "authorization_id": auth["authorization_id"],
        "authorization_receipt_path": str(auth_path),
        "authorization_receipt_file_sha256": _file_sha(auth_path),
        "authorization_receipt_sha256": auth["receipt_sha256"],
        "outer_terminal_path": str(outer_path),
        "outer_terminal_file_sha256": _file_sha(outer_path),
        "outer_terminal_receipt_sha256": outer["receipt_sha256"],
        "scene_instance_id": outer.get("scene_instance_id", terminal.get("scene_instance_id")),
        "scene_seed": auth["scene_seed"],
        "planner_query_count": planner_count,
        "planner_pass": planner_pass,
        "failure_class": failure_class,
        "failure_code": outer.get("failure_code"),
        "scene_count": scene_count,
        "elapsed_seconds": float(elapsed),
        "guard_receipt_path": str(guard_path),
        "guard_receipt_file_sha256": _file_sha(guard_path),
        "guard_receipt_sha256": guard["guard_receipt_sha256"],
        "cleanup_safety_pass": cleanup_pass,
        "orphan_process_count": int(guard.get("orphan_process_count", -1)),
        "physical_execution_count": 0,
        "trajectory_count": 0,
    }
    if not cleanup_pass:
        value["planner_pass"] = False
        value["failure_class"] = "INFRASTRUCTURE_ERROR"
        value["failure_code"] = "CLEANUP_OR_RELEASE_UNCERTAIN"
    value["normalized_terminal_sha256"] = canonical_hash_json(value)
    return value


def record_outer_terminal_v1(
    ledger_directory: Path,
    *,
    authorization_receipt_path: Path,
    outer_terminal_path: Path,
    guard_receipt_path: Path,
):
    normalized = normalize_outer_terminal_from_disk_v1(
        authorization_receipt_path=authorization_receipt_path,
        outer_terminal_path=outer_terminal_path,
        guard_receipt_path=guard_receipt_path,
    )
    state = load_wave_ledger_state_v1(ledger_directory)
    slot = normalized["slot"]
    if slot not in state["issued"]:
        raise PermissionError("terminal slot was not issued by this ledger")
    if state["issued"][slot]["authorization_receipt_sha256"] != normalized[
        "authorization_receipt_sha256"
    ]:
        raise ValueError("terminal authorization differs from issuance")
    prospective = dict(state["aggregate"])
    prospective["planner_query_count"] += normalized["planner_query_count"]
    prospective["scene_count"] += normalized["scene_count"]
    prospective["elapsed_seconds"] += normalized["elapsed_seconds"]
    budget = state["meta"]["aggregate_budget"]
    if (
        prospective["planner_query_count"] > budget["planner_query_limit"]
        or prospective["scene_count"] > budget["scene_limit"]
        or prospective["elapsed_seconds"] > budget["wall_time_seconds"]
    ):
        raise RuntimeError("normalized terminal would exceed wave budget")
    path = state["root"] / "terminals" / f"{slot}.json"
    canonical_write_json(path, normalized, exclusive=True, mode=0o600)
    if normalized["failure_class"] == "INFRASTRUCTURE_ERROR":
        closure = {
            "schema_version": "cmf_planner_wiring_smoke_wave_closure_v1",
            "wave_id": state["meta"]["wave_id"],
            "trigger_slot": slot,
            "failure_code": normalized["failure_code"],
            "permanently_closed": True,
        }
        closure["closed_sha256"] = canonical_hash_json(closure)
        canonical_write_json(
            state["root"] / "closed.json",
            closure,
            exclusive=True,
            mode=0o600,
        )
    return normalized


def record_guard_prevalidation_terminal_v1(
    ledger_directory: Path,
    *,
    authorization_receipt_path: Path,
    guard_receipt_path: Path,
    failure_code: str,
):
    """Fail-close a wave when Guard rejects a job before consumption/child."""

    state = load_wave_ledger_state_v1(ledger_directory)
    auth_path = _workspace(
        authorization_receipt_path, "authorization", file=True
    )
    guard_path = _workspace(guard_receipt_path, "Guard receipt", file=True)
    auth = _self_hashed(_load(auth_path), "receipt_sha256", "authorization")
    guard = _self_hashed(
        _load(guard_path), "guard_receipt_sha256", "Guard receipt"
    )
    slot = auth.get("slot")
    allowed_statuses = {
        "failed_authorization_binding",
        "failed_guard_authorization_mismatch",
        "failed_guard_budget_mismatch",
        "failed_guard_internal_prevalidation",
        "failed_runtime_source_lock",
    }
    consumption_path = (
        Path(auth.get("consumption_ledger_directory", ""))
        / f"{auth.get('authorization_id')}.json"
    )
    output_path = Path(auth.get("output_namespace", ""))
    if (
        state["closed"] is not None
        or slot not in state["issued"]
        or slot in state["terminals"]
        or slot in state["skipped"]
        or state["issued"][slot]["authorization_receipt_path"]
        != str(auth_path)
        or state["issued"][slot]["authorization_receipt_sha256"]
        != auth["receipt_sha256"]
        or Path(auth.get("guard_receipt_path", "")).resolve() != guard_path
        or guard.get("schema_version") != "cmf_gpu_guard_v2_4_1"
        or guard.get("purpose") != "planner_wiring_smoke_v1"
        or guard.get("status") not in allowed_statuses
        or not isinstance(guard.get("error"), Mapping)
        or "child_pid" in guard
        or "binding" in guard
        or consumption_path.exists()
        or output_path.exists()
        or not isinstance(failure_code, str)
        or not failure_code
    ):
        raise ValueError("Guard prevalidation terminal evidence is invalid")
    elapsed = guard.get("elapsed_seconds")
    if not isinstance(elapsed, (int, float)) or elapsed < 0:
        raise ValueError("Guard prevalidation elapsed time is invalid")

    outer = {
        "schema_version": (
            "cmf_planner_wiring_smoke_prevalidation_outer_terminal_v1"
        ),
        "wave_id": auth["wave_id"],
        "slot": slot,
        "job_kind": auth["job_kind"],
        "family": auth["family"],
        "authorization_id": auth["authorization_id"],
        "authorization_receipt_sha256": auth["receipt_sha256"],
        "guard_receipt_path": str(guard_path),
        "guard_receipt_file_sha256": _file_sha(guard_path),
        "guard_receipt_sha256": guard["guard_receipt_sha256"],
        "status": "failed_guard_prevalidation_before_consumption",
        "planner_pass": False,
        "failure_class": "INFRASTRUCTURE_ERROR",
        "failure_code": failure_code,
        "failure_message": str(guard["error"].get("message", "")),
        "child_started": False,
        "authorization_consumed": False,
        "lease_acquired": False,
        "job_cache_created": False,
        "output_namespace_created": False,
        "planner_query_count": 0,
        "scene_count": 0,
        "physical_execution_count": 0,
        "trajectory_count": 0,
        "elapsed_seconds": float(elapsed),
        "terminalization_kind": "guard_prevalidation_terminal_v1",
        "not_a_child_output": True,
    }
    outer["receipt_sha256"] = canonical_hash_json(outer)
    outer_path = state["root"] / "prevalidation" / f"{slot}_outer_terminal.json"
    canonical_write_json(outer_path, outer, exclusive=True, mode=0o600)

    normalized = {
        "schema_version": NORMALIZED_SCHEMA,
        "wave_id": auth["wave_id"],
        "slot": slot,
        "job_kind": auth["job_kind"],
        "family": auth["family"],
        "authorization_id": auth["authorization_id"],
        "authorization_receipt_path": str(auth_path),
        "authorization_receipt_file_sha256": _file_sha(auth_path),
        "authorization_receipt_sha256": auth["receipt_sha256"],
        "outer_terminal_path": str(outer_path),
        "outer_terminal_file_sha256": _file_sha(outer_path),
        "outer_terminal_receipt_sha256": outer["receipt_sha256"],
        "scene_instance_id": None,
        "scene_seed": auth["scene_seed"],
        "planner_query_count": 0,
        "planner_pass": False,
        "failure_class": "INFRASTRUCTURE_ERROR",
        "failure_code": failure_code,
        "scene_count": 0,
        "elapsed_seconds": float(elapsed),
        "guard_receipt_path": str(guard_path),
        "guard_receipt_file_sha256": _file_sha(guard_path),
        "guard_receipt_sha256": guard["guard_receipt_sha256"],
        "cleanup_safety_pass": True,
        "cleanup_semantics": (
            "Guard failed before consumption, lease, cache, child, or GPU precheck"
        ),
        "orphan_process_count": 0,
        "physical_execution_count": 0,
        "trajectory_count": 0,
        "normalizer_path": "guard_prevalidation_terminal_v1",
        "production_child_normalizer_applicable": False,
    }
    normalized["normalized_terminal_sha256"] = canonical_hash_json(normalized)
    canonical_write_json(
        state["root"] / "terminals" / f"{slot}.json",
        normalized,
        exclusive=True,
        mode=0o600,
    )
    closure = {
        "schema_version": "cmf_planner_wiring_smoke_wave_closure_v1",
        "wave_id": auth["wave_id"],
        "trigger_slot": slot,
        "failure_code": failure_code,
        "permanently_closed": True,
        "normalized_terminal_sha256": normalized[
            "normalized_terminal_sha256"
        ],
        "guard_receipt_sha256": guard["guard_receipt_sha256"],
        "authorization_consumed": False,
        "planner_query_count": 0,
        "scene_count": 0,
        "physical_execution_count": 0,
        "trajectory_count": 0,
        "closure_origin": "guard_prevalidation_terminal_v1",
        "retry_authorized": False,
    }
    closure["closed_sha256"] = canonical_hash_json(closure)
    canonical_write_json(
        state["root"] / "closed.json",
        closure,
        exclusive=True,
        mode=0o600,
    )
    return normalized


def build_f3_stage_b_registry_from_wave_v1(
    ledger_directory: Path, *, stage_b_slot: str
):
    source_slot = {"S6A": "S2", "S6B": "S5"}.get(stage_b_slot)
    if source_slot is None:
        raise ValueError("F3 Stage-B registry slot must be S6A or S6B")
    state = load_wave_ledger_state_v1(ledger_directory)
    normalized = state["terminals"].get(source_slot)
    if (
        normalized is None
        or normalized["job_kind"] != "F3_STAGE_A"
        or normalized["planner_pass"] is not True
    ):
        raise PermissionError("F3 Stage-A passing terminal is absent")
    auth = _load(Path(normalized["authorization_receipt_path"]))
    output = Path(auth["output_namespace"])
    outer = _load(Path(normalized["outer_terminal_path"]))
    stage_a_terminal = _load(output / "stage_a_terminal.json")
    if (
        auth.get("job_kind") != "F3_STAGE_A"
        or auth.get("slot") != source_slot
        or normalized.get("scene_seed") != auth.get("scene_seed")
        or outer.get("dispatch", {}).get("job_terminal_receipt_sha256")
        != stage_a_terminal.get("receipt_sha256")
    ):
        raise ValueError("F3 Stage-A output differs from normalized outer terminal")
    registry = build_f3_stage_b_dependency_registry_v1_1(
        stage_a_spec_path=output / "stage_a_spec.json",
        stage_a_terminal_path=output / "stage_a_terminal.json",
        actual_scene_seed=normalized["scene_seed"],
        stage_a_scene_instance_id=normalized["scene_instance_id"],
    )
    path = state["root"] / "registries" / f"{stage_b_slot}.json"
    if path.exists():
        existing = load_f3_stage_b_dependency_registry_v1_1(_load(path))["registry"]
        if existing != registry:
            raise ValueError("existing F3 Stage-B registry differs")
        return existing
    canonical_write_json(path, registry, exclusive=True, mode=0o600)
    return registry


def _record_skip(root: Path, *, wave_id: str, slot: str, reason: str):
    path = root / "skipped" / f"{slot}.json"
    if path.exists():
        return _self_hashed(_load(path), "skip_sha256", "wave skip")
    value = {
        "schema_version": "cmf_planner_wiring_smoke_skipped_slot_v1",
        "wave_id": wave_id,
        "slot": slot,
        "reason": reason,
    }
    value["skip_sha256"] = canonical_hash_json(value)
    canonical_write_json(path, value, exclusive=True, mode=0o600)
    return value


def reconcile_skipped_slots_v1(ledger_directory: Path):
    state = load_wave_ledger_state_v1(ledger_directory)
    if state["closed"] is not None:
        for slot in ALL_SLOTS:
            if slot not in state["terminals"] and slot not in state["skipped"]:
                _record_skip(
                    state["root"],
                    wave_id=state["meta"]["wave_id"],
                    slot=slot,
                    reason="wave_closed_after_infrastructure_error",
                )
        return load_wave_ledger_state_v1(ledger_directory)["skipped"]
    for slot, dependency in CONDITIONAL_DEPENDENCIES.items():
        if slot in state["terminals"] or slot in state["skipped"]:
            continue
        prior = state["terminals"].get(dependency)
        prior_skipped = state["skipped"].get(dependency)
        if prior is not None and prior["planner_pass"] is not True:
            _record_skip(
                state["root"],
                wave_id=state["meta"]["wave_id"],
                slot=slot,
                reason=f"{dependency}_planner_pass_condition_not_met",
            )
        elif prior_skipped is not None:
            _record_skip(
                state["root"],
                wave_id=state["meta"]["wave_id"],
                slot=slot,
                reason=f"{dependency}_was_skipped",
            )
        state = load_wave_ledger_state_v1(ledger_directory)
    return state["skipped"]


def finalize_wave_terminal_v1(ledger_directory: Path):
    reconcile_skipped_slots_v1(ledger_directory)
    state = load_wave_ledger_state_v1(ledger_directory)
    if state["closed"] is None:
        missing_base = [slot for slot in BASE_SLOTS if slot not in state["terminals"]]
        unresolved = [
            slot
            for slot in CONDITIONAL_DEPENDENCIES
            if slot not in state["terminals"] and slot not in state["skipped"]
        ]
        if missing_base or unresolved:
            raise PermissionError(
                f"wave is incomplete: base={missing_base}, conditional={unresolved}"
            )
    value = {
        "schema_version": "cmf_planner_wiring_smoke_wave_terminal_v1",
        "wave_id": state["meta"]["wave_id"],
        "status": (
            "INFRASTRUCTURE_ERROR_STOPPED"
            if state["closed"] is not None
            else "WAVE_TERMINAL_COMPLETE"
        ),
        "proposal_sha256": state["meta"]["proposal_sha256"],
        "normalized_terminal_sha256s_by_slot": {
            slot: state["terminals"][slot]["normalized_terminal_sha256"]
            for slot in ALL_SLOTS
            if slot in state["terminals"]
        },
        "skipped_slots": {
            slot: state["skipped"][slot]["reason"]
            for slot in ALL_SLOTS
            if slot in state["skipped"]
        },
        "aggregate": state["aggregate"],
        "aggregate_budget": state["meta"]["aggregate_budget"],
        "physical_execution_count": 0,
        "trajectory_count": 0,
        "stage1_authorized": False,
    }
    value["wave_terminal_sha256"] = canonical_hash_json(value)
    canonical_write_json(
        state["root"] / "wave_terminal.json",
        value,
        exclusive=True,
        mode=0o600,
    )
    return value


__all__ = [
    "ALL_SLOTS",
    "build_f3_stage_b_registry_from_wave_v1",
    "build_planner_wiring_smoke_wave_driver_v1_contract",
    "finalize_wave_terminal_v1",
    "initialize_wave_ledger_v1",
    "load_wave_ledger_state_v1",
    "normalize_outer_terminal_from_disk_v1",
    "record_guard_prevalidation_terminal_v1",
    "record_outer_terminal_v1",
    "record_slot_issuance_v1",
    "reconcile_skipped_slots_v1",
    "validate_slot_issuance_from_ledger_v1",
]
