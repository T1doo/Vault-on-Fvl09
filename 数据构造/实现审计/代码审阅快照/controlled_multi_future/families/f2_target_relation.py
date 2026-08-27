from ..base import ControlledMultiFutureSceneBase


class F2TargetRelation(ControlledMultiFutureSceneBase):
    family_id = "F2"
    audit_status = "repair_v1_pending_same_can_left_arm_beside"

    main_object = {"modelname": "071_can", "model_id": 1, "arm": "left"}

    def build_provisional_programs(self):
        return [
            {"program_id": "F2-inside", "steps": [{"op": "pick", "object": "main_object"}, {"op": "place", "object": "main_object", "relation": "inside", "reference": "plastic_box"}]},
            {"program_id": "F2-on", "steps": [{"op": "pick", "object": "main_object"}, {"op": "place", "object": "main_object", "relation": "on", "reference": "electronic_scale"}]},
            {"program_id": "F2-beside", "steps": [{"op": "pick", "object": "main_object"}, {"op": "place", "object": "main_object", "relation": "beside", "reference": "pot_or_stand"}]},
        ]

    def validate_shared_execution_identity(self, branch_specs):
        identities = {(item["modelname"], item["model_id"], item["arm"]) for item in branch_specs}
        if identities != {("071_can", 1, "left")}:
            raise ValueError("F2 branches must all use 071_can/base1 with the left arm")
        return True
