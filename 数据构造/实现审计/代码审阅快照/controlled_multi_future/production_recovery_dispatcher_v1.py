"""Exact in-process dispatcher for reviewed production-recovery runners.

This module is intentionally not a CLI and grants no execution authority.  A
future Guard-bound child may call it only after loading a matching single-use
authorization and constructing the exact scene/spec pair.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .f2_controlled_insertion_physical_v2 import (
    run_f2_controlled_insertion_physical_v2,
)
from .f3_shared_v_physical_v1 import run_f3_shared_v_physical_v1
from .f4_bounded_physical_micro_v1 import run_f4_bounded_physical_micro_v1
from .f2_controlled_insertion_physical_v2 import (
    validate_f2_controlled_insertion_physical_spec_v2,
)
from .f3_shared_v_physical_v1 import validate_f3_shared_v_physical_spec_v1
from .f4_bounded_physical_micro_v1 import (
    validate_f4_bounded_physical_micro_spec_v1,
)
from .real_sapien_adapter_high_level_v1 import (
    RoboTwinRealSapienF2HierarchicalStageAV1Adapter,
    RoboTwinRealSapienF3AssetGraspV2Adapter,
    RoboTwinRealSapienF4HierarchicalStageAV1Adapter,
)


RUNNER_SYMBOLS = {
    "F2_CONTROLLED_INSERTION_PHYSICAL": (
        "controlled_multi_future.f2_controlled_insertion_physical_v2."
        "run_f2_controlled_insertion_physical_v2"
    ),
    "F3_SHARED_V_PHYSICAL": (
        "controlled_multi_future.f3_shared_v_physical_v1."
        "run_f3_shared_v_physical_v1"
    ),
    "F4_BOUNDED_PHYSICAL_MICRO": (
        "controlled_multi_future.f4_bounded_physical_micro_v1."
        "run_f4_bounded_physical_micro_v1"
    ),
}


def build_production_recovery_adapter_v1(
    *,
    job_kind: str,
    spec: Mapping[str, Any],
    output_root: Path,
    expected_implementation_source_sha256: str,
):
    validators = {
        "F2_CONTROLLED_INSERTION_PHYSICAL": (
            validate_f2_controlled_insertion_physical_spec_v2,
            RoboTwinRealSapienF2HierarchicalStageAV1Adapter,
        ),
        "F3_SHARED_V_PHYSICAL": (
            validate_f3_shared_v_physical_spec_v1,
            RoboTwinRealSapienF3AssetGraspV2Adapter,
        ),
        "F4_BOUNDED_PHYSICAL_MICRO": (
            validate_f4_bounded_physical_micro_spec_v1,
            RoboTwinRealSapienF4HierarchicalStageAV1Adapter,
        ),
    }
    if job_kind not in validators:
        raise ValueError("unknown production recovery adapter kind")
    validate, adapter_class = validators[job_kind]
    checked = validate(spec)
    return adapter_class(
        output_root=Path(output_root),
        expected_implementation_source_sha256=expected_implementation_source_sha256,
        planned_spec=checked["legacy_scene_spec"],
    )


def dispatch_production_recovery_v1(
    scene,
    *,
    job_kind: str,
    runner_symbol: str,
    spec: Mapping[str, Any],
    capture_anchor_callback=None,
):
    if RUNNER_SYMBOLS.get(job_kind) != runner_symbol:
        raise ValueError("production recovery job kind/runner symbol mismatch")
    if job_kind == "F2_CONTROLLED_INSERTION_PHYSICAL":
        if capture_anchor_callback is not None:
            raise ValueError("F2 recovery runner does not accept an anchor callback")
        return run_f2_controlled_insertion_physical_v2(scene, spec)
    if job_kind == "F3_SHARED_V_PHYSICAL":
        if capture_anchor_callback is not None:
            raise ValueError("F3 recovery runner does not accept an anchor callback")
        return run_f3_shared_v_physical_v1(scene, spec)
    if job_kind == "F4_BOUNDED_PHYSICAL_MICRO":
        if not callable(capture_anchor_callback):
            raise ValueError("F4 recovery runner requires an adapter-bound anchor callback")
        return run_f4_bounded_physical_micro_v1(
            scene,
            spec,
            capture_anchor_callback=capture_anchor_callback,
        )
    raise ValueError("unknown production recovery job kind")


__all__ = [
    "RUNNER_SYMBOLS",
    "build_production_recovery_adapter_v1",
    "dispatch_production_recovery_v1",
]
