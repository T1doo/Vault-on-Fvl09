"""Real A-block execution Gate after an F4 template passes planner qualification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
import traceback
from typing import Any, Mapping

from .anchor import compare_anchors
from .canonical_artifact import canonical_hash_json, canonical_write_json
from .canonical_prefix_artifact_v1 import load_canonical_prefix_artifact
from .canonical_prefix_replay_v1 import replay_canonical_prefix
from .current_hasher import require_same_current
from .family_runners_v3_3 import _cache_suffix_controls
from .f4_template_qualification_v1 import (
    IMPLEMENTATION_VERSION,
    validate_f4_template_candidate_spec_v1,
)
from .root_orchestrator_v1_1 import _immutable_copy
from .root_orchestrator_v1_2 import RealSapienStrictPrefixRootOrchestratorV1_2


class F4AOnlyExecutionQualificationV1:
    def __init__(self, adapter):
        if adapter.family != "F4":
            raise ValueError("F4 A-only qualification requires F4 adapter")
        self.adapter = adapter
        self.helper = RealSapienStrictPrefixRootOrchestratorV1_2(
            adapter, implementation_version=IMPLEMENTATION_VERSION
        )

    @staticmethod
    def _trace(scene, path: Path) -> dict[str, Any]:
        path.parent.mkdir(parents=True, exist_ok=True)
        value = dict(scene.save_trace(path))
        value["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        return value

    def run(
        self,
        *,
        output_dir: Path,
        planned_root_slot_spec: Mapping[str, Any],
        planner_only_output_dir: Path,
    ) -> dict[str, Any]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        started = time.time()
        spec = validate_f4_template_candidate_spec_v1(planned_root_slot_spec)
        source = Path(planner_only_output_dir)
        current = json.loads((source / "reference_current.json").read_text(encoding="utf-8"))
        anchor = json.loads((source / "reference_anchor.json").read_text(encoding="utf-8"))
        programs = json.loads((source / "canonical_programs.json").read_text(encoding="utf-8"))
        neutral = json.loads(
            (source / "post_stage0_canonical_neutral.json").read_text(encoding="utf-8")
        )
        manifest, arrays = load_canonical_prefix_artifact(source / "prefix_artifact")
        if [item.get("program_id") for item in programs] != [
            "F4-ABC",
            "F4-ACB",
            "F4-BAC",
        ]:
            raise ValueError("F4 A-only source programs changed")
        planned_hash = canonical_hash_json(spec)
        receipt: dict[str, Any] = {
            "schema_version": "cmf_f4_a_only_execution_qualification_v1",
            "implementation_version": IMPLEMENTATION_VERSION,
            "candidate_id": spec["selected_layout_candidate_id"],
            "candidate_sha256": spec["selected_layout_candidate_sha256"],
            "source_planner_only_receipt_sha256": json.loads(
                (source / "receipt.json").read_text(encoding="utf-8")
            )["receipt_sha256"],
            "execution_attempt_count": 0,
            "release_execution_count": 0,
            "planner_query_count": 0,
            "cleanup_records": [],
            "formal_data": False,
            "stage0_data": False,
            "stage1_authorized": False,
            "status": "running",
            "pass": False,
        }
        self.helper._event_log_path = output_dir / "events.jsonl"

        def callback(scene, program):
            require_same_current(current, dict(self.adapter.capture_current(scene)))
            start_anchor = dict(self.adapter.capture_anchor(scene))
            if compare_anchors(anchor, start_anchor)["equivalent"] is not True:
                raise ValueError("F4 A-only start anchor mismatch")
            self.adapter.initialize_prefix_replay_trace(scene)
            replay = replay_canonical_prefix(
                scene,
                manifest=manifest,
                arrays=arrays,
                reference_current=current,
                capture_current=self.adapter.capture_current,
                capture_anchor=self.adapter.capture_anchor,
            )
            physical = dict(self.adapter.validate_replayed_prefix_physical(scene, replay))
            if physical.get("pass") is not True:
                raise RuntimeError("F4 A-only prefix physical Gate failed")
            scene._cmf_post_stage0_f4_canonical_neutral_pose = list(neutral["pose"])
            controller = self.adapter.controller_v3_3
            all_targets, extra = controller._top_down_full_targets_v8(scene, program)
            suffix_targets = all_targets[controller.COMMON_SEGMENT_COUNT :]
            group = next(item for item in extra["object_target_groups"] if item["role"] == "A")
            start = int(group["target_start_index"])
            count = int(group.get("target_count", len(group["targets"])))
            targets = suffix_targets[start : start + count]
            before = int(getattr(scene, "planner_query_count", 0))
            planner = _cache_suffix_controls(
                scene,
                program_id="F4-A-ONLY-QUALIFICATION-V1",
                arm="right",
                targets=targets,
                query_limit=32,
                extra={
                    "object_order": ["A"],
                    "object_target_groups": [
                        {**group, "target_start_index": 0, "target_count": count}
                    ],
                    "block_carry_route_version": extra["block_carry_route_version"],
                    "block_carry_route_audit": extra["block_carry_route_audit"],
                    "common_prefix_artifact_required": True,
                    "a_only_execution_qualification": True,
                },
            )
            receipt["planner_query_count"] += int(
                getattr(scene, "planner_query_count", 0)
            ) - before
            if planner.get("planner_solvable") is not True:
                raise RuntimeError("F4 A-only planner chain failed")
            receipt["execution_attempt_count"] += 1
            receipt["release_execution_count"] += 1
            rollout = self.adapter.execute_frozen_suffix_spec(
                scene,
                program,
                planner["execution_spec"],
                replay,
                {
                    "realization": "a_only_qualification",
                    "formal_data": False,
                    "stage0_data": False,
                    "stage1_authorized": False,
                },
            )
            verifier = self.adapter.verify(scene, program, rollout)
            return {
                "program_id": program["program_id"],
                "executed_object_order": ["A"],
                "prefix_replay": replay,
                "prefix_physical_acceptance": physical,
                "planner_receipt": {
                    key: value
                    for key, value in planner.items()
                    if not key.startswith("_")
                },
                "family_verifier": verifier,
                "semantic_verifier": rollout["semantic_verifier"],
                "trace_source": self._trace(scene, output_dir / "a_only_trace.npz"),
                "pass": verifier.get("pass") is True,
            }

        try:
            result = self.helper._scene_call(
                receipt=receipt,
                planned_spec=_immutable_copy(spec),
                planned_spec_sha256=planned_hash,
                phase="f4_template_qualification_v1_a_only_execution",
                program=programs[0],
                program_sha256=canonical_hash_json(programs[0]),
                callback=callback,
            )
            receipt["result"] = result
            receipt["pass"] = result["pass"] is True
            receipt["status"] = (
                "a_only_execution_pass"
                if receipt["pass"]
                else "a_only_execution_failed_verifier"
            )
        except BaseException as exc:
            receipt["status"] = "a_only_execution_failed"
            receipt["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        receipt["cleanup_safety_pass"] = bool(receipt["cleanup_records"]) and all(
            item.get("cleanup_safety_pass") is True
            and int(item.get("orphan_process_count", -1)) == 0
            for item in receipt["cleanup_records"]
        )
        if not receipt["cleanup_safety_pass"]:
            receipt["pass"] = False
            receipt["status"] = "a_only_execution_failed_cleanup_uncertain"
        receipt["elapsed_seconds"] = time.time() - started
        receipt["receipt_sha256"] = canonical_hash_json(receipt)
        canonical_write_json(output_dir / "receipt.json", receipt, mode=0o600)
        return receipt


__all__ = ["F4AOnlyExecutionQualificationV1"]
