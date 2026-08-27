from ..base import ControlledMultiFutureSceneBase


class F4SubtaskOrder(ControlledMultiFutureSceneBase):
    family_id = "F4"
    audit_status = "single_A_supported_full_program_probe_pending"

    def build_provisional_programs(self):
        def place(role):
            return {"op": "place", "object": role, "relation": "at_slot", "reference": f"slot_{role}"}

        common = {"op": "place", "object": "common_X", "relation": "inside", "reference": "common_tray"}
        return [
            {"program_id": "F4-ABC", "steps": [common, place("A"), place("B"), place("C")]},
            {"program_id": "F4-ACB", "steps": [common, place("A"), place("C"), place("B")]},
            {"program_id": "F4-BAC", "steps": [common, place("B"), place("A"), place("C")]},
        ]
