"""Strict-prefix root adapter for the Run9-qualified F4 mixed-arm schedule."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .anchor import quaternion_angular_error
from .canonical_artifact import canonical_jsonable
from .f4_full_program_physical_v1 import (
    PROGRAM_IDS,
    execute_f4_frozen_full_program_suffix_v1,
    plan_f4_full_program_suffix_from_replayed_prefix_v1,
    validate_f4_full_program_physical_spec_v1,
)
from .real_sapien_adapter_high_level_v1 import (
    RoboTwinRealSapienF4HierarchicalStageAV1Adapter,
)
from .family_runners_v3_1 import _pose


ADAPTER_VERSION = "RoboTwinRealSapienF4QualifiedDevelopmentRootV1Adapter"
IMPLEMENTATION_VERSION = "controlled_multi_future_f4_qualified_development_root_v1"


class RoboTwinRealSapienF4QualifiedDevelopmentRootV1Adapter(
    RoboTwinRealSapienF4HierarchicalStageAV1Adapter
):
    def __init__(
        self,
        *,
        output_root: Path,
        expected_implementation_source_sha256: str,
        planned_spec: Mapping[str, Any],
        full_program_specs: Mapping[str, Mapping[str, Any]],
    ):
        super().__init__(
            output_root=output_root,
            expected_implementation_source_sha256=(
                expected_implementation_source_sha256
            ),
            planned_spec=planned_spec,
        )
        values = {
            program_id: validate_f4_full_program_physical_spec_v1(spec)
            for program_id, spec in full_program_specs.items()
        }
        if set(values) != set(PROGRAM_IDS):
            raise ValueError("F4 qualified-root adapter requires exactly ABC/ACB/BAC")
        candidate_hashes = {
            item["candidate_sha256"] for item in values.values()
        }
        isolation_hashes = {
            item["isolation_gate_receipt_sha256"] for item in values.values()
        }
        legacy_hashes = {
            item["legacy_scene_spec_sha256"] for item in values.values()
        }
        if (
            len(candidate_hashes) != 1
            or len(isolation_hashes) != 1
            or len(legacy_hashes) != 1
            or next(iter(legacy_hashes))
            != self.planned_spec["planned_scope_spec_sha256"]
        ):
            raise ValueError("F4 qualified-root program specs do not share one root")
        self.full_program_specs = values

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION
        scene._cmf_generator_version = IMPLEMENTATION_VERSION

    def plan_suffix_from_actual_prefix_end_state(self, scene, program, replay):
        return plan_f4_full_program_suffix_from_replayed_prefix_v1(
            scene,
            program,
            replay,
            self.full_program_specs[program["program_id"]],
        )

    def audit_task_physical_feasibility(self, scene, program):
        legacy = super().audit_task_physical_feasibility(scene, program)
        candidate = self.full_program_specs["F4-ABC"][
            "f4_stage_b_candidate_v1"
        ]
        position_errors = {}
        orientation_errors = {}
        for role in ("A", "B", "C"):
            actual = _pose(getattr(scene, f"slot_{role.lower()}"))
            expected = np.asarray(candidate["slot_poses"][role], dtype=np.float64)
            position_errors[role] = float(
                np.linalg.norm(actual[:3] - expected[:3])
            )
            orientation_errors[role] = quaternion_angular_error(
                actual[3:], expected[3:]
            )
        legacy_evidence = dict(legacy.get("evidence", {}))
        other_legacy_checks = {
            key: value
            for key, value in legacy_evidence.items()
            if key != "slots_pairwise_separated"
        }
        replacement_checks = {
            "legacy_non_slot_checks": bool(other_legacy_checks)
            and all(other_legacy_checks.values()),
            "r01_candidate_construction_valid": candidate.get(
                "construction_valid"
            )
            is True,
            "r01_candidate_no_online_fallback": candidate.get(
                "online_fallback"
            )
            is False,
            "r01_positive_terminal_surface_clearance": float(
                candidate.get("minimum_terminal_clearance_m", 0.0)
            )
            > 0.0,
            "runtime_slot_positions_bound_within_1um": all(
                error <= 1.0e-6 for error in position_errors.values()
            ),
            "runtime_slot_orientations_bound_within_1urad": all(
                error <= 1.0e-6 for error in orientation_errors.values()
            ),
        }
        passed = all(replacement_checks.values())
        legacy.update(
            {
                "status": "passed" if passed else "failed",
                "task_feasible": passed,
                "physical_feasible": passed,
                "failure_type": None
                if passed
                else "f4_r01_task_physical_contract",
                "evidence": {
                    **other_legacy_checks,
                    "legacy_fixed_0_10m_slot_center_check": legacy_evidence.get(
                        "slots_pairwise_separated"
                    ),
                    "legacy_fixed_0_10m_check_is_diagnostic": True,
                    "r01_candidate_id": candidate["candidate_id"],
                    "r01_candidate_sha256": candidate["candidate_sha256"],
                    "r01_minimum_terminal_surface_clearance_m": candidate[
                        "minimum_terminal_clearance_m"
                    ],
                    "runtime_slot_position_errors_m": position_errors,
                    "runtime_slot_orientation_errors_rad": orientation_errors,
                    "replacement_checks": replacement_checks,
                },
            }
        )
        return legacy

    def execute_frozen_suffix_spec(
        self,
        scene,
        program,
        execution_spec,
        replay,
        realization_spec,
    ):
        return execute_f4_frozen_full_program_suffix_v1(
            scene,
            program,
            execution_spec,
            replay,
            realization_spec,
        )

    def verify(self, scene, program, rollout_result):
        semantic = rollout_result.get("semantic_verifier")
        value = {
            "pass": isinstance(semantic, Mapping)
            and semantic.get("pass") is True,
            "family_semantic_verifier": canonical_jsonable(semantic),
            "strict_prefix_adapter_version": ADAPTER_VERSION,
            "implementation_version": IMPLEMENTATION_VERSION,
            "fixed_arm_schedule": {
                "canonical_prefix": "right",
                "program_suffix": self.full_program_specs[
                    program["program_id"]
                ]["f4_source_grasp_candidate_v1"]["arm"],
            },
        }
        return value


__all__ = [
    "ADAPTER_VERSION",
    "IMPLEMENTATION_VERSION",
    "RoboTwinRealSapienF4QualifiedDevelopmentRootV1Adapter",
]
