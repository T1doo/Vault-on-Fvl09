from ..base import ControlledMultiFutureSceneBase


class F1ObjectSelection(ControlledMultiFutureSceneBase):
    family_id = "F1"
    family_implementation_version = "f1_three_branch_coverage_v3_1"
    audit_status = "terminal_failed_planner_after_two_versioned_repairs"

    def build_provisional_programs(self):
        return [
            {
                "program_id": f"F1-{role}",
                "target_role": role,
                "canonical_prefix_id": "f1_cluster_common_pregrasp_v1_1",
                "steps": [
                    {"op": "pick", "object": role},
                    {"op": "place", "object": role, "relation": "inside", "reference": "common_box"},
                ],
            }
            for role in ("red", "green", "blue")
        ]
