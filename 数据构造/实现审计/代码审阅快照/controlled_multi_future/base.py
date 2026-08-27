"""Fail-closed lifecycle interface for controlled multi-future families."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence

from .schemas import validate_exactly_three_programs


class ImplementationAuditError(RuntimeError):
    """Raised when code is called before its implementation audit is complete."""


class ControlledMultiFutureSceneBase(ABC):
    """Common interface required by protocol ``controlled_multi_future_f1_f4_v1_2``.

    Runtime methods fail closed until a family supplies an audited implementation.
    This scaffold cannot collect Stage 0 or formal data.
    """

    design_version = "controlled_multi_future_f1_f4_v1_2"
    implementation_status = "skeleton_runtime_not_implemented"
    stage0_authorized = False

    @property
    @abstractmethod
    def family_id(self) -> str:
        raise NotImplementedError

    def build_provisional_scene(self, planned_root_slot_spec: Mapping[str, Any]) -> Any:
        raise ImplementationAuditError(f"{self.family_id}: scene builder pending audited runtime implementation")

    @abstractmethod
    def build_provisional_programs(self) -> Sequence[Mapping[str, Any]]:
        raise NotImplementedError

    def checked_provisional_programs(self) -> Sequence[Mapping[str, Any]]:
        programs = self.build_provisional_programs()
        validate_exactly_three_programs(programs)
        return programs

    def audit_task_and_physical_feasibility(self, program: Mapping[str, Any]) -> Any:
        raise ImplementationAuditError(f"{self.family_id}: feasibility audit pending GPU0 probe")

    def freeze_candidate_universe_and_task_tree(self) -> Any:
        raise ImplementationAuditError(f"{self.family_id}: candidate freeze unavailable in skeleton")

    def build_and_freeze_canonical_prefix(self) -> Any:
        raise ImplementationAuditError(f"{self.family_id}: prefix generator pending audited runtime implementation")

    def reconstruct_fresh_scene_and_anchor(self) -> Any:
        raise ImplementationAuditError(f"{self.family_id}: fresh-scene anchor pending audited runtime implementation")

    def rollout(self, program: Mapping[str, Any], realization_spec: Mapping[str, Any]) -> Any:
        raise ImplementationAuditError(f"{self.family_id}: rollout is not authorized or implemented")

    def extract_realized_events(self) -> Any:
        raise ImplementationAuditError(f"{self.family_id}: realized-event adapter pending GPU0 probe")

    def verify_family_semantics(self) -> Any:
        raise ImplementationAuditError(f"{self.family_id}: family verifier pending audited signals")

    def verify_final_state_equivalence(self) -> Any:
        raise ImplementationAuditError(f"{self.family_id}: final-state verifier pending audited signals")

    def write_attempt_receipt_and_terminal_status(self) -> Any:
        raise ImplementationAuditError(f"{self.family_id}: attempt writer is deliberately absent from skeleton")
