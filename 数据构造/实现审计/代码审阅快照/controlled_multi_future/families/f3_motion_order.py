from ..base import ControlledMultiFutureSceneBase


class F3MotionOrder(ControlledMultiFutureSceneBase):
    family_id = "F3"
    audit_status = "unresolved_pending_realized_motion_gpu0_probe"

    def build_provisional_programs(self):
        return [
            {"program_id": "F3-VVHH", "steps": [{"op": "oscillate", "axis": axis} for axis in "VVHH"]},
            {"program_id": "F3-VHVH", "steps": [{"op": "oscillate", "axis": axis} for axis in "VHVH"]},
            {"program_id": "F3-VHHV", "steps": [{"op": "oscillate", "axis": axis} for axis in "VHHV"]},
        ]
