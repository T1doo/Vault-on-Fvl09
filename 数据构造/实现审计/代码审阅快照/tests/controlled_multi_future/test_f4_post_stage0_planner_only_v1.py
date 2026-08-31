import unittest

from controlled_multi_future.f4_post_stage0_planner_only_v1 import (
    PROGRAM_IDS,
    _segment_chain_audit,
    finalize_f4_post_stage0_planner_only_v1,
)


class F4PostStage0PlannerOnlyV1Tests(unittest.TestCase):
    def test_segment_chain_requires_success_limits_and_no_execution(self):
        segments = []
        previous = "start"
        for index in range(3):
            end = f"end-{index}"
            segments.append(
                {
                    "segment_id": f"A_{index}",
                    "planner_status": "Success",
                    "start_qpos_sha256": previous,
                    "end_qpos_sha256": end,
                    "joint_limit_evidence_complete": True,
                    "terminal_qpos_within_joint_limits": True,
                    "minimum_terminal_joint_limit_margin_rad": 0.1,
                    "executed": False,
                }
            )
            previous = end
        self.assertTrue(_segment_chain_audit(segments)["pass"])
        segments[1]["planner_status"] = "Fail"
        self.assertFalse(_segment_chain_audit(segments)["pass"])

    def test_finalizer_requires_three_programs_and_four_cleanups(self):
        values = []
        cleanups = []
        for index, program_id in enumerate(PROGRAM_IDS):
            values.append(
                {
                    "program_id": program_id,
                    "pass": True,
                    "scene_instance_id": f"program-scene-{index}",
                    "executed_prefix_action_sha256": "a" * 64,
                    "canonical_neutral_pose_sha256": "b" * 64,
                    "selected_corridor_id": "lower_carry_height",
                    "suffix_execution_attempt_count": 0,
                    "release_execution_count": 0,
                }
            )
        for index in range(4):
            cleanups.append(
                {
                    "scene_instance_id": f"scene-{index}",
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }
            )
        result = finalize_f4_post_stage0_planner_only_v1(
            values,
            cleanup_records=cleanups,
            canonical_neutral_pose_sha256="b" * 64,
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["accepted_root_increment"], 0)
        values[0]["release_execution_count"] = 1
        self.assertFalse(
            finalize_f4_post_stage0_planner_only_v1(
                values,
                cleanup_records=cleanups,
                canonical_neutral_pose_sha256="b" * 64,
            )["pass"]
        )


if __name__ == "__main__":
    unittest.main()
