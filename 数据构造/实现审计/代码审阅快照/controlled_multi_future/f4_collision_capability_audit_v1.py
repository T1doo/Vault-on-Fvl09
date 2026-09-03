"""Fail-closed F4 collision-capability declaration for the current planner.

This contract records the reviewed capabilities of the unmodified RoboTwin
CuRobo wrapper.  It prevents table-only planner success from being promoted to
carried-object or dynamic-scene noninterference evidence.
"""

from __future__ import annotations

from .canonical_artifact import canonical_hash_json
from .f4_program_planner_integration_v2 import PLANNER_COLLISION_SCOPE


def build_f4_collision_capability_audit_v1() -> dict:
    checks = {
        "planner_scope_declares_table_only": PLANNER_COLLISION_SCOPE.get(
            "configured_world_objects"
        )
        == ["table"],
        "dynamic_scene_objects_absent": PLANNER_COLLISION_SCOPE.get(
            "scene_dynamic_objects_in_curobo_world"
        )
        is False,
        "carried_object_attachment_absent": PLANNER_COLLISION_SCOPE.get(
            "attached_carried_object_modeled"
        )
        is False,
        "robot_scene_collision_unproven": PLANNER_COLLISION_SCOPE.get(
            "robot_link_vs_scene_object_collision_proven"
        )
        is False,
    }
    value = {
        "schema_version": "cmf_f4_collision_capability_audit_v1",
        "planner_collision_scope": PLANNER_COLLISION_SCOPE,
        "reviewed_project_interface": {
            "curobo_world_initialization": "envs/robot/planner.py:CuroboPlanner.__init__",
            "configured_world_objects": ["table"],
            "curobo_update_point_cloud_implemented": False,
            "curobo_attached_object_api_exposed_by_robot_wrapper": False,
            "mplib_use_attach_arguments_are_commented_out": True,
        },
        "checks": checks,
        "table_only_planner_can_qualify_physical_noninterference": False,
        "full_1696_query_panel_recommended_before_physical_micro_gate": False,
        "selected_recovery_route": "bounded_staged_physical_noninterference",
        "ordered_physical_micro_gates": [
            "A_only",
            "B_only",
            "C_only",
            "AB_noninterference",
            "AC_noninterference",
            "ABC_ACB_BAC_one_development_root",
        ],
        "maximum_f4_development_roots": 1,
        "gpu_execution_authorized": False,
        "physical_execution_authorized": False,
        "stage1_authorized": False,
        "formal_data": False,
        "pass": all(checks.values()),
    }
    value["receipt_sha256"] = canonical_hash_json(value)
    return value


__all__ = ["build_f4_collision_capability_audit_v1"]
