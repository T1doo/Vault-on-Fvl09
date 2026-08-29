from ..base import ControlledMultiFutureSceneBase


class F4SubtaskOrder(ControlledMultiFutureSceneBase):
    family_id = "F4"
    family_implementation_version = "f4_common_carry_and_full_program_v3_2"
    audit_status = "terminal_failed_common_carry_no_authorized_tray_layout_candidate"

    def build_provisional_programs(self):
        def place(role):
            return {"op": "place", "object": role, "relation": "at_slot", "reference": f"slot_{role}"}

        common = {"op": "place", "object": "common_X", "relation": "inside", "reference": "common_tray"}
        return [
            {"program_id": "F4-ABC", "steps": [common, place("A"), place("B"), place("C")]},
            {"program_id": "F4-ACB", "steps": [common, place("A"), place("C"), place("B")]},
            {"program_id": "F4-BAC", "steps": [common, place("B"), place("A"), place("C")]},
        ]
