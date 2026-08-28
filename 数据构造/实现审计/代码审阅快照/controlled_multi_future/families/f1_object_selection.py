from ..base import ControlledMultiFutureSceneBase


class F1ObjectSelection(ControlledMultiFutureSceneBase):
    family_id = "F1"
    family_implementation_version = "f1_transport_and_true_inside_v2"
    audit_status = "runtime_v2_bounded_probe_authorized_not_run"

    def build_provisional_programs(self):
        return [
            {"program_id": f"F1-{role}", "steps": [{"op": "pick", "object": role}, {"op": "place", "object": role, "relation": "inside", "reference": "common_box"}]}
            for role in ("red_block", "green_block", "blue_block")
        ]
