from ..base import ControlledMultiFutureSceneBase


class F3MotionOrder(ControlledMultiFutureSceneBase):
    family_id = "F3"
    family_implementation_version = "f3_return_equivalence_v2"
    audit_status = "runtime_v2_bounded_probe_authorized_not_run"

    def build_provisional_programs(self):
        return [
            {"program_id": "F3-VVHH", "steps": [{"op": "oscillate", "axis": axis} for axis in "VVHH"]},
            {"program_id": "F3-VHVH", "steps": [{"op": "oscillate", "axis": axis} for axis in "VHVH"]},
            {"program_id": "F3-VHHV", "steps": [{"op": "oscillate", "axis": axis} for axis in "VHHV"]},
        ]
