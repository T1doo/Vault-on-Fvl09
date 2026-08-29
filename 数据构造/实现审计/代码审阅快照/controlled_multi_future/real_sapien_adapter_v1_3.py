"""Real SAPIEN adapter for runtime-v3_3 strict-prefix roots.

Import remains lazy with respect to SAPIEN scene creation and CUDA.
"""

from __future__ import annotations

from .family_runners_v3_3 import get_family_controller_v3_3
from .real_sapien_adapter_v1_2 import RoboTwinRealSapienPilotRootAdapterV1_2


ADAPTER_VERSION_V1_3 = "RoboTwinRealSapienStrictPrefixAdapterV1_3"
GENERATOR_VERSION_V1_3 = "controlled_multi_future_joint_scene_v3_3_adapter_v1_3"


class RoboTwinRealSapienStrictPrefixAdapterV1_3(
    RoboTwinRealSapienPilotRootAdapterV1_2
):
    """Bind real scenes to one-prefix generation and exact replay APIs."""

    def __init__(self, *, family, output_root):
        super().__init__(family=family, output_root=output_root)
        self.controller_v3_3 = get_family_controller_v3_3(family)

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION_V1_3
        scene._cmf_generator_version = GENERATOR_VERSION_V1_3

    def capture_current(self, scene):
        self._mark_v1_3_context(scene)
        return super().capture_current(scene)

    def capture_anchor(self, scene):
        self._mark_v1_3_context(scene)
        return super().capture_anchor(scene)

    def canonical_prefix_contract(self, programs):
        return self.controller_v3_3.canonical_prefix_contract(programs)

    def audit_task_physical_feasibility(self, disposable_scene, program):
        return self.controller_v3_3.audit_task_physical_feasibility(
            disposable_scene, program
        )

    def plan_and_execute_canonical_prefix(self, scene, prefix_contract):
        return self.controller_v3_3.plan_and_execute_canonical_prefix(
            scene,
            prefix_contract,
            capture_anchor=self.capture_anchor,
        )

    def initialize_prefix_replay_trace(self, scene):
        return self.controller_v3_3.initialize_prefix_replay_trace(scene)

    def plan_suffix_from_actual_prefix_end_state(self, scene, program, replay):
        return self.controller_v3_3.plan_suffix_from_actual_prefix_end_state(
            scene, program, replay
        )

    def execute_frozen_suffix_spec(
        self,
        scene,
        program,
        execution_spec,
        replay,
        realization_spec,
    ):
        return self.controller_v3_3.execute_frozen_suffix_spec(
            scene,
            program,
            execution_spec,
            replay,
            realization_spec,
        )

    def validate_family_suffix_gate(self, receipts):
        return self.controller_v3_3.validate_family_suffix_gate(receipts)

    def validate_replayed_prefix_physical(self, scene, replay):
        return self.controller_v3_3.validate_replayed_prefix_physical(
            scene, replay
        )

    def verify(self, scene, program, rollout_result):
        semantic = rollout_result.get("semantic_verifier")
        if not isinstance(semantic, dict):
            raise ValueError("runtime-v3_3 rollout lacks family semantic verifier")
        return {
            "pass": semantic.get("pass") is True,
            "family_semantic_verifier": semantic,
            "strict_prefix_adapter_version": ADAPTER_VERSION_V1_3,
        }
