"""F1 batch-pilot adapter identity with frozen display-order permutation."""

from __future__ import annotations

from .families import F1ObjectSelection
from .real_sapien_adapter_v1_5 import RoboTwinRealSapienStrictPrefixAdapterV1_5


ADAPTER_VERSION = "RoboTwinRealSapienF1BatchPilotAdapterV1"
IMPLEMENTATION_VERSION = "controlled_multi_future_f1_batch_pilot_v1"


class RoboTwinRealSapienF1BatchPilotAdapterV1(
    RoboTwinRealSapienStrictPrefixAdapterV1_5
):
    def __init__(self, **kwargs):
        if kwargs.get("family") != "F1":
            raise ValueError("F1 batch adapter only accepts family F1")
        super().__init__(**kwargs)

    @staticmethod
    def _mark_v1_3_context(scene):
        scene._cmf_adapter_version = ADAPTER_VERSION
        scene._cmf_generator_version = (
            "controlled_multi_future_f1_batch_pilot_adapter_v1"
        )

    def build_programs(self, pristine_scene):
        programs = list(F1ObjectSelection().checked_provisional_programs())
        planned = getattr(pristine_scene, "_cmf_planned_root_slot_spec", {})
        display_order = planned.get("candidate_display_order")
        by_id = {item["program_id"]: item for item in programs}
        if not isinstance(display_order, list) or set(display_order) != set(by_id):
            raise ValueError("F1 batch candidate display order is not a permutation")
        return [by_id[program_id] for program_id in display_order]

    def verify(self, scene, program, rollout_result):
        value = super().verify(scene, program, rollout_result)
        value["strict_prefix_adapter_version"] = ADAPTER_VERSION
        value["implementation_version"] = IMPLEMENTATION_VERSION
        value["formal_data"] = False
        value["stage0_data"] = False
        value["stage1_authorized"] = False
        return value


__all__ = ["RoboTwinRealSapienF1BatchPilotAdapterV1"]
