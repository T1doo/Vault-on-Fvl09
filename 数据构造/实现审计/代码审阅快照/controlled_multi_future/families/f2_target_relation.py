from ..base import ControlledMultiFutureSceneBase


class F2TargetRelation(ControlledMultiFutureSceneBase):
    family_id = "F2"
    audit_status = "unresolved_pending_same_object_gpu0_probe"

    def build_provisional_programs(self):
        return [
            {"program_id": "F2-inside", "steps": [{"op": "pick", "object": "main_object"}, {"op": "place", "object": "main_object", "relation": "inside", "reference": "plastic_box"}]},
            {"program_id": "F2-on", "steps": [{"op": "pick", "object": "main_object"}, {"op": "place", "object": "main_object", "relation": "on", "reference": "electronic_scale"}]},
            {"program_id": "F2-beside", "steps": [{"op": "pick", "object": "main_object"}, {"op": "place", "object": "main_object", "relation": "beside", "reference": "pot_or_stand"}]},
        ]
