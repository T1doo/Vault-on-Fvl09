from ..base import ControlledMultiFutureSceneBase


class F3MotionOrder(ControlledMultiFutureSceneBase):
    family_id = "F3"
    family_implementation_version = "f3_release_dynamics_diagnosis_v3_1"
    audit_status = "runtime_v3_1_cpu_static_gpu_unauthorized"

    def build_provisional_programs(self):
        return [
            {"program_id": "F3-VVHH", "steps": [{"op": "oscillate", "axis": axis} for axis in "VVHH"]},
            {"program_id": "F3-VHVH", "steps": [{"op": "oscillate", "axis": axis} for axis in "VHVH"]},
            {"program_id": "F3-VHHV", "steps": [{"op": "oscillate", "axis": axis} for axis in "VHHV"]},
        ]
