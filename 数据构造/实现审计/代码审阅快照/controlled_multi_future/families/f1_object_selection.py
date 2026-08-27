from ..base import ControlledMultiFutureSceneBase


class F1ObjectSelection(ControlledMultiFutureSceneBase):
    family_id = "F1"
    audit_status = "supported_with_official_rgb_blocks_runtime_pending"

    def build_provisional_programs(self):
        return [
            {"program_id": f"F1-{role}", "steps": [{"op": "pick", "object": role}, {"op": "place", "object": role, "relation": "inside", "reference": "common_box"}]}
            for role in ("red_block", "green_block", "blue_block")
        ]
