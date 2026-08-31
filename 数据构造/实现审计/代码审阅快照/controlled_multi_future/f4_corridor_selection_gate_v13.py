"""Planner-only F4 frozen-canonical-neutral infrastructure Gate v13."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
import traceback

from .anchor import compare_anchors
from .canonical_prefix_artifact_v1 import (
    build_canonical_prefix_artifact,
    write_canonical_prefix_artifact,
)
from .canonical_prefix_replay_v1 import replay_canonical_prefix
from .current_hasher import hash_json, require_same_current
from .f4_exact_corridor_application_v11 import (
    audit_f4_exact_corridor_results_v11,
)
from .f4_frozen_canonical_neutral_binding_v13 import (
    IMPLEMENTATION_VERSION,
    bind_f4_canonical_prefix_artifact_v13,
    bind_f4_corridor_contract_to_canonical_neutral_v13,
    build_f4_frozen_canonical_neutral_binding_from_artifacts_v13,
    build_f4_realized_prefix_end_physical_equivalence_v13,
)
from .root_orchestrator_v1_1 import CleanupUncertain, _immutable_copy, _write_json
from .root_orchestrator_v1_2 import (
    RealSapienStrictPrefixRootOrchestratorV1_2,
    _validate_prefix_reference_result,
    _validate_suffix_planner_receipt,
)
from .schemas import validate_exactly_three_programs


SCHEMA_VERSION = "cmf_f4_corridor_selection_gate_v13"


class F4CorridorSelectionGateV13:
    """Freeze one canonical neutral, replay it, then reach a real query.

    A complete planner failure is valid pilot evidence.  Infrastructure pass
    therefore means that the immutable target specification survived fresh
    reconstruction, physical prefix replay passed its independent tolerance,
    and at least one real corridor query returned structured evidence.  It is
    deliberately not synonymous with corridor solvability.
    """

    def __init__(self, adapter):
        if adapter.family != "F4":
            raise ValueError("F4 v13 corridor selection requires F4 adapter")
        self.adapter = adapter
        self.helper = RealSapienStrictPrefixRootOrchestratorV1_2(
            adapter, implementation_version=IMPLEMENTATION_VERSION
        )

    @staticmethod
    def _public_candidate(candidate, suffix, cleanup_pass):
        evidence = suffix.get("evidence", {})
        segments = list(evidence.get("segment_receipts", []))
        previous = None
        chain = True
        for item in segments:
            start = item.get("start_qpos_sha256")
            if previous is not None and start != previous:
                chain = False
            previous = item.get("end_qpos_sha256")
        ids = [item.get("segment_id") for item in segments]
        preplanner = evidence.get("exact_candidate_preplanner_gate_v11", {})
        equivalence = evidence.get("fresh_scene_candidate_equivalence_v12", {})
        neutral_identity = evidence.get(
            "frozen_canonical_neutral_spec_identity_v13", {}
        )
        physical = evidence.get(
            "realized_prefix_end_physical_equivalence_v13", {}
        )
        return {
            "candidate_id": candidate["candidate_id"],
            "candidate_application_sha256": candidate[
                "candidate_application_sha256"
            ],
            "canonical_terminal_neutral_pose_sha256_v13": neutral_identity.get(
                "canonical_terminal_neutral_pose_sha256"
            ),
            "frozen_canonical_neutral_binding_sha256_v13": neutral_identity.get(
                "frozen_canonical_neutral_binding_sha256"
            ),
            "preplanner_contract_application_exact": preplanner.get("pass")
            is True,
            "fresh_scene_candidate_equivalence_v12": equivalence,
            "fresh_scene_candidate_equivalence_pass": equivalence.get("pass")
            is True,
            "frozen_canonical_neutral_spec_identity_v13": neutral_identity,
            "frozen_canonical_neutral_spec_identity_pass": neutral_identity.get(
                "pass"
            )
            is True,
            "realized_prefix_end_physical_equivalence_v13": physical,
            "realized_prefix_end_physical_equivalence_pass": physical.get(
                "pass"
            )
            is True,
            "qpos_chain_continuous": chain,
            "release_and_neutral_in_chain": (
                any(str(name).endswith("_release") for name in ids)
                and bool(ids)
                and str(ids[-1]).endswith("_neutral")
            ),
            "execution_attempt_count": 0,
            "fresh_scene": True,
            "cleanup_pass": cleanup_pass,
            "planner_query_count": int(suffix.get("planner_query_count", 0)),
            "planner_solvable": suffix.get("planner_solvable") is True,
            "segment_receipts": segments,
            "source_suffix_receipt_sha256": hash_json(suffix),
        }

    def run(self, *, output_dir: Path, planned_root_slot_spec) -> dict:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        planned = _immutable_copy(planned_root_slot_spec)
        planned_hash = hash_json(planned)
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "design_version": "controlled_multi_future_f1_f4_v1_2",
            "implementation_version": IMPLEMENTATION_VERSION,
            "formal_data": False,
            "stage0_data": False,
            "stage0_authorized": False,
            "status": "running",
            "pass": False,
            "planner_query_count": 0,
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
            "candidate_receipts": [],
            "cleanup_records": [],
        }
        self.helper._event_log_path = output_dir / "events.jsonl"
        _write_json(output_dir / "planned_root_slot_spec.json", planned)
        try:

            def pristine_callback(scene, _program):
                current = dict(self.adapter.capture_current(scene))
                anchor = dict(self.adapter.capture_anchor(scene))
                programs = _immutable_copy(list(self.adapter.build_programs(scene)))
                validate_exactly_three_programs(programs)
                prefix = _immutable_copy(
                    self.adapter.canonical_prefix_contract(programs)
                )
                # None is permitted only for this pristine freeze.  Every
                # fresh-scene reconstruction below receives the binding.
                contract = (
                    self.adapter.controller_v3_3.build_exact_a_corridor_contract_v13(
                        scene, canonical_neutral_binding=None
                    )
                )
                if contract.get("pass") is not True:
                    raise ValueError("F4 v13 pristine corridor contract failed")
                return current, anchor, programs, prefix, contract

            current, anchor, programs, prefix_contract, base_corridor_contract = (
                self.helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase="f4_frozen_neutral_pristine_v13",
                    program=None,
                    program_sha256=None,
                    callback=pristine_callback,
                )
            )
            _write_json(output_dir / "reference_current.json", current)
            _write_json(output_dir / "reference_anchor.json", anchor)
            _write_json(
                output_dir / "base_exact_corridor_contract.json",
                base_corridor_contract,
            )
            prefix_runtime = {"queries": 0}

            def prefix_callback(scene, _program):
                require_same_current(current, dict(self.adapter.capture_current(scene)))
                if not compare_anchors(
                    anchor, dict(self.adapter.capture_anchor(scene))
                )["equivalent"]:
                    raise ValueError("F4 v13 prefix reference anchor mismatch")
                before = int(getattr(scene, "planner_query_count", 0))
                try:
                    result = _validate_prefix_reference_result(
                        self.adapter.plan_and_execute_canonical_prefix(
                            scene, _immutable_copy(prefix_contract)
                        )
                    )
                finally:
                    prefix_runtime["queries"] = int(
                        getattr(scene, "planner_query_count", 0)
                    ) - before
                path = output_dir / "prefix_reference_trace.npz"
                trace = dict(scene.save_trace(path))
                result["trace_source"] = {
                    **trace,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                return result

            try:
                prefix_result = self.helper._scene_call(
                    receipt=receipt,
                    planned_spec=planned,
                    planned_spec_sha256=planned_hash,
                    phase="f4_frozen_neutral_prefix_reference_v13",
                    program=None,
                    program_sha256=None,
                    callback=prefix_callback,
                )
            finally:
                receipt["planner_query_count"] += prefix_runtime["queries"]
            manifest, arrays = build_canonical_prefix_artifact(
                root_slot_id=str(planned["slot_id"]),
                family="F4",
                reference_current_sha256=current["aggregate_sha256"],
                reference_anchor=anchor,
                prefix_contract=prefix_contract,
                planner_seed=int(prefix_result.get("planner_seed", 20260828)),
                planner_query_receipts=prefix_result["planner_query_receipts"],
                planner_source_hash=prefix_result["planner_source_hash"],
                arrays=prefix_result["arrays"],
                semantic_prefix_end_anchor=prefix_result[
                    "semantic_prefix_end_anchor"
                ],
                acceptance_prefix_end_anchor=prefix_result[
                    "acceptance_prefix_end_anchor"
                ],
                settling_step_count=int(prefix_result["settling_step_count"]),
                settling_policy=prefix_result["settling_policy"],
                prefix_physical_acceptance=prefix_result[
                    "prefix_physical_acceptance"
                ],
                reference_trace_source=prefix_result["trace_source"],
                reference_event_boundaries=prefix_result.get(
                    "reference_event_boundaries", {}
                ),
            )
            binding = build_f4_frozen_canonical_neutral_binding_from_artifacts_v13(
                canonical_prefix_artifact=manifest,
                corridor_contract=base_corridor_contract,
            )
            corridor_contract = bind_f4_corridor_contract_to_canonical_neutral_v13(
                base_corridor_contract, binding
            )
            manifest = bind_f4_canonical_prefix_artifact_v13(manifest, binding)
            _write_json(
                output_dir / "frozen_canonical_neutral_binding_v13.json",
                binding,
            )
            _write_json(
                output_dir / "exact_corridor_contract_v13.json",
                corridor_contract,
            )
            manifest = write_canonical_prefix_artifact(
                output_dir / "prefix_artifact", manifest, arrays
            )
            receipt["canonical_neutral_binding_v13"] = binding
            public = []
            for candidate in corridor_contract["candidates"]:
                candidate_dir = output_dir / f"candidate_{candidate['priority']}"
                candidate_dir.mkdir(parents=True, exist_ok=False)
                runtime = {"queries": 0}
                diagnostic_program = {
                    "program_id": "F4-DIAG-A-FROZEN-NEUTRAL-"
                    + candidate["candidate_id"],
                    "steps": [{"operation": "place", "object_role": "A"}],
                    "diagnostic_nonroot": True,
                }

                def candidate_callback(scene, _program):
                    require_same_current(
                        current, dict(self.adapter.capture_current(scene))
                    )
                    if not compare_anchors(
                        anchor, dict(self.adapter.capture_anchor(scene))
                    )["equivalent"]:
                        raise ValueError("F4 v13 candidate anchor mismatch")
                    self.adapter.initialize_prefix_replay_trace(scene)
                    replay = replay_canonical_prefix(
                        scene,
                        manifest=manifest,
                        arrays=arrays,
                        reference_current=current,
                        capture_current=self.adapter.capture_current,
                        capture_anchor=self.adapter.capture_anchor,
                    )
                    realized = build_f4_realized_prefix_end_physical_equivalence_v13(
                        replay=replay, binding=binding
                    )
                    scene._cmf_f4_realized_prefix_end_physical_equivalence_v13 = (
                        realized
                    )
                    _write_json(
                        candidate_dir
                        / "realized_prefix_end_physical_equivalence_v13.json",
                        realized,
                    )
                    if realized.get("pass") is not True:
                        raise ValueError(
                            "F4 v13 realized prefix-end physical equivalence failed"
                        )
                    physical = dict(
                        self.adapter.validate_replayed_prefix_physical(scene, replay)
                    )
                    if physical.get("pass") is not True:
                        raise ValueError("F4 v13 candidate prefix physical Gate failed")
                    before = int(getattr(scene, "planner_query_count", 0))
                    try:
                        suffix = _validate_suffix_planner_receipt(
                            self.adapter.controller_v3_3.plan_a_exact_corridor_candidate_v13(
                                scene,
                                replay,
                                candidate,
                                binding,
                            ),
                            diagnostic_program["program_id"],
                        )
                    except BaseException:
                        for attr, filename in (
                            (
                                "_cmf_f4_candidate_equivalence_v12",
                                "equivalence_receipt_v12.json",
                            ),
                            (
                                "_cmf_f4_frozen_canonical_neutral_spec_identity_v13",
                                "frozen_neutral_identity_receipt_v13.json",
                            ),
                        ):
                            value = getattr(scene, attr, None)
                            if isinstance(value, dict):
                                _write_json(candidate_dir / filename, value)
                        raise
                    finally:
                        runtime["queries"] = int(
                            getattr(scene, "planner_query_count", 0)
                        ) - before
                    suffix.pop("_execution_controls", None)
                    suffix.pop("_actual_prefix_end_qpos", None)
                    evidence = suffix.setdefault("evidence", {})
                    evidence[
                        "realized_prefix_end_physical_equivalence_v13"
                    ] = realized
                    for key, attr in (
                        (
                            "fresh_scene_candidate_equivalence_v12",
                            "_cmf_f4_candidate_equivalence_v12",
                        ),
                        (
                            "frozen_canonical_neutral_spec_identity_v13",
                            "_cmf_f4_frozen_canonical_neutral_spec_identity_v13",
                        ),
                    ):
                        if key not in evidence:
                            value = getattr(scene, attr, None)
                            if isinstance(value, dict):
                                evidence[key] = value
                    path = candidate_dir / "preflight_trace_source.npz"
                    trace = dict(scene.save_trace(path))
                    suffix["trace_source"] = {
                        **trace,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                    _write_json(candidate_dir / "preflight_receipt.json", suffix)
                    return suffix

                try:
                    suffix = self.helper._scene_call(
                        receipt=receipt,
                        planned_spec=planned,
                        planned_spec_sha256=planned_hash,
                        phase="f4_frozen_neutral_candidate:"
                        + candidate["candidate_id"],
                        program=diagnostic_program,
                        program_sha256=hash_json(diagnostic_program),
                        callback=candidate_callback,
                    )
                except BaseException as candidate_exc:
                    equivalence = self._optional_json(
                        candidate_dir / "equivalence_receipt_v12.json"
                    )
                    neutral_identity = self._optional_json(
                        candidate_dir / "frozen_neutral_identity_receipt_v13.json"
                    )
                    realized = self._optional_json(
                        candidate_dir
                        / "realized_prefix_end_physical_equivalence_v13.json"
                    )
                    infrastructure_identity_failure = (
                        isinstance(equivalence, dict)
                        and equivalence.get("pass") is False
                    ) or (
                        isinstance(neutral_identity, dict)
                        and neutral_identity.get("pass") is False
                    )
                    failure_type = (
                        "infrastructure_frozen_neutral_identity_failure"
                        if infrastructure_identity_failure
                        else "cleanup_uncertain"
                        if isinstance(candidate_exc, CleanupUncertain)
                        else "candidate_planner_exception"
                        if int(runtime["queries"]) > 0
                        else "candidate_scene_or_prefix_gate_failure"
                    )
                    failed_candidate = {
                        "candidate_id": candidate["candidate_id"],
                        "candidate_application_sha256": candidate[
                            "candidate_application_sha256"
                        ],
                        "planner_query_count": int(runtime["queries"]),
                        "execution_attempt_count": 0,
                        "failure_type": failure_type,
                        "error_type": type(candidate_exc).__name__,
                        "error": str(candidate_exc),
                        "fresh_scene_candidate_equivalence_v12": equivalence,
                        "frozen_canonical_neutral_spec_identity_v13": (
                            neutral_identity
                        ),
                        "realized_prefix_end_physical_equivalence_v13": realized,
                        "cleanup_pass": bool(receipt["cleanup_records"])
                        and receipt["cleanup_records"][-1].get(
                            "cleanup_safety_pass"
                        )
                        is True,
                        "formal_data": False,
                        "stage0_data": False,
                    }
                    failed_candidate["receipt_sha256"] = hash_json(
                        failed_candidate
                    )
                    receipt["candidate_receipts"].append(failed_candidate)
                    _write_json(
                        candidate_dir / "candidate_failure_receipt.json",
                        failed_candidate,
                    )
                    raise
                finally:
                    receipt["planner_query_count"] += int(runtime["queries"])
                item = self._public_candidate(
                    candidate,
                    suffix,
                    receipt["cleanup_records"][-1].get("cleanup_safety_pass")
                    is True,
                )
                public.append(item)
                receipt["candidate_receipts"].append(item)
                if any(
                    segment.get("joint_limit_evidence_complete") is not True
                    for segment in item["segment_receipts"]
                ):
                    break
                if suffix.get("planner_solvable") is True:
                    break
            audit = audit_f4_exact_corridor_results_v11(
                corridor_contract, public
            )
            receipt["corridor_planner_audit"] = audit
            hash_checks = {
                "canonical_neutral_binding_present_and_self_hashed": isinstance(
                    binding.get("binding_sha256"), str
                ),
                "at_least_one_candidate_reached_real_planner": bool(public)
                and sum(
                    int(item.get("planner_query_count", 0)) for item in public
                )
                > 0,
                "all_attempted_candidate_v12_equivalence_pass": bool(public)
                and all(
                    item.get("fresh_scene_candidate_equivalence_pass") is True
                    for item in public
                ),
                "all_attempted_frozen_neutral_identity_pass": bool(public)
                and all(
                    item.get("frozen_canonical_neutral_spec_identity_pass")
                    is True
                    for item in public
                ),
                "all_attempted_realized_prefix_physical_equivalence_pass": bool(
                    public
                )
                and all(
                    item.get("realized_prefix_end_physical_equivalence_pass")
                    is True
                    for item in public
                ),
                "all_attempted_preplanner_contracts_exact": bool(public)
                and all(
                    item.get("preplanner_contract_application_exact") is True
                    for item in public
                ),
                "planner_receipt_evidence_complete": audit.get(
                    "evidence_complete"
                )
                is True,
                "no_candidate_hash_infrastructure_failure": audit.get(
                    "failure_type"
                )
                != "infrastructure_schema_failure",
            }
            infrastructure_pass = all(hash_checks.values())
            receipt["hash_infrastructure_audit_v13"] = {
                "schema_version": "cmf_f4_hash_infrastructure_audit_v13",
                "checks": hash_checks,
                "pass": infrastructure_pass,
                "corridor_selection_pass": audit["pass"],
                "corridor_physical_failure_is_valid_stage0_evidence": True,
                "candidate_spec_position_atol_m": 1.0e-5,
                "candidate_spec_orientation_atol_rad": 1.0e-5,
                "realized_prefix_state_uses_candidate_spec_tolerance": False,
            }
            receipt["selected_corridor_candidate_v13"] = next(
                (
                    item
                    for item in corridor_contract["candidates"]
                    if item["candidate_id"] == audit["selected_candidate_id"]
                ),
                None,
            )
            receipt["status"] = (
                "passed_f4_hash_infrastructure_gate_v13"
                if infrastructure_pass
                else "failed_f4_hash_infrastructure_gate_v13"
            )
            receipt["pass"] = infrastructure_pass
        except CleanupUncertain as exc:
            receipt["status"] = "failed_cleanup_uncertain"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        except BaseException as exc:
            receipt["status"] = "failed_f4_hash_infrastructure_gate_v13"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)
            receipt["traceback"] = traceback.format_exc()
        receipt["budget_counts"] = {
            "planner_query_count": receipt["planner_query_count"],
            "execution_attempt_count": 0,
            "recovery_attempt_count": 0,
        }
        receipt.setdefault(
            "hash_infrastructure_audit_v13",
            {
                "schema_version": "cmf_f4_hash_infrastructure_audit_v13",
                "checks": {},
                "pass": False,
                "failure": receipt.get("error"),
            },
        )
        receipt["elapsed_seconds"] = time.time() - started
        payload = dict(receipt)
        payload.pop("receipt_sha256", None)
        receipt["receipt_sha256"] = hash_json(payload)
        _write_json(output_dir / "receipt.json", receipt)
        return receipt

    @staticmethod
    def _optional_json(path: Path):
        return (
            json.loads(path.read_text(encoding="utf-8"))
            if path.is_file()
            else None
        )


__all__ = ["F4CorridorSelectionGateV13"]
