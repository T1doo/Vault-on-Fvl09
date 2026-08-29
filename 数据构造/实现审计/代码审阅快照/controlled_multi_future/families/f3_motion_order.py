from ..base import ControlledMultiFutureSceneBase


class F3MotionOrder(ControlledMultiFutureSceneBase):
    family_id = "F3"
    family_implementation_version = "f3_release_and_full_program_v3_2"
    audit_status = "terminal_failed_prefix_lift_after_two_versioned_repairs"

    def build_provisional_programs(self):
        return [
            {"program_id": "F3-VVHH", "steps": [{"op": "oscillate", "axis": axis} for axis in "VVHH"]},
            {"program_id": "F3-VHVH", "steps": [{"op": "oscillate", "axis": axis} for axis in "VHVH"]},
            {"program_id": "F3-VHHV", "steps": [{"op": "oscillate", "axis": axis} for axis in "VHHV"]},
        ]
