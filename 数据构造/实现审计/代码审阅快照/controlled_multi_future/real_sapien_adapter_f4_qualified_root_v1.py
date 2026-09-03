"""Strict-prefix root adapter for the Run9-qualified F4 mixed-arm schedule."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

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
