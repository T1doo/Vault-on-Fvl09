import copy
import json
import unittest

from controlled_multi_future.f2_gripper_assembly_topology_v5 import (
    build_f2_gripper_assembly_topology_receipt,
    validate_f2_gripper_assembly_topology_receipt,
)


VALID_TOPOLOGY = [
    {
        "joint_name": "fl_joint7",
        "parent_link_name": "fl_link6",
        "child_link_name": "fl_link7",
    },
    {
        "joint_name": "fl_joint8",
        "parent_link_name": "fl_link6",
        "child_link_name": "fl_link8",
    },
]
VALID_LINKS = [
    "fl_link5",
    "fl_link6",
    "fl_link7",
    "fl_link8",
    "left_camera",
]


def valid_receipt():
    return build_f2_gripper_assembly_topology_receipt(
        arm="left",
        move_group_link_name="fl_link6",
        gripper_joint_topology=VALID_TOPOLOGY,
        articulation_link_names=VALID_LINKS,
        selected_contact_signal_link_names=["fl_link7", "fl_link8"],
    )


class F2GripperAssemblyTopologyV5Test(unittest.TestCase):
    def test_valid_aloha_topology_keeps_finger_signal_and_adds_only_palm(self):
        receipt = valid_receipt()
        self.assertTrue(receipt["pass"])
        self.assertEqual(
            receipt["selected_contact_signal_link_names"],
            ["fl_link7", "fl_link8"],
        )
        self.assertEqual(
            receipt["additional_allowed_gripper_assembly_body_names"],
            ["fl_link6"],
        )
        self.assertEqual(
            receipt["allowed_gripper_assembly_body_names"],
            ["fl_link6", "fl_link7", "fl_link8"],
        )
        self.assertTrue(receipt["finger_contact_signal_remains_required"])
        self.assertFalse(receipt["palm_contact_alone_satisfies_selected_contact"])
        json.dumps(receipt, allow_nan=False)
        self.assertEqual(len(receipt["receipt_sha256"]), 64)
        self.assertEqual(
            validate_f2_gripper_assembly_topology_receipt(receipt), receipt
        )

    def test_wrong_common_parent_or_missing_palm_fails_closed(self):
        wrong_parent = copy.deepcopy(VALID_TOPOLOGY)
        wrong_parent[1]["parent_link_name"] = "fl_link5"
        with self.assertRaisesRegex(ValueError, "common_finger_parent"):
            build_f2_gripper_assembly_topology_receipt(
                arm="left",
                move_group_link_name="fl_link6",
                gripper_joint_topology=wrong_parent,
                articulation_link_names=VALID_LINKS,
                selected_contact_signal_link_names=["fl_link7", "fl_link8"],
            )

        with self.assertRaisesRegex(ValueError, "move_group_palm_exists"):
            build_f2_gripper_assembly_topology_receipt(
                arm="left",
                move_group_link_name="fl_link6",
                gripper_joint_topology=VALID_TOPOLOGY,
                articulation_link_names=["fl_link5", "fl_link7", "fl_link8"],
                selected_contact_signal_link_names=["fl_link7", "fl_link8"],
            )

    def test_palm_may_not_enter_selected_contact_signal(self):
        with self.assertRaisesRegex(
            ValueError,
            "selected_signal_is_exactly_fingers_and_fixed_links",
        ):
            build_f2_gripper_assembly_topology_receipt(
                arm="left",
                move_group_link_name="fl_link6",
                gripper_joint_topology=VALID_TOPOLOGY,
                articulation_link_names=VALID_LINKS,
                selected_contact_signal_link_names=[
                    "fl_link6",
                    "fl_link7",
                    "fl_link8",
                ],
            )

    def test_duplicate_or_incomplete_finger_topology_fails_closed(self):
        duplicate_child = copy.deepcopy(VALID_TOPOLOGY)
        duplicate_child[1]["child_link_name"] = "fl_link7"
        with self.assertRaisesRegex(ValueError, "child links must be unique"):
            build_f2_gripper_assembly_topology_receipt(
                arm="left",
                move_group_link_name="fl_link6",
                gripper_joint_topology=duplicate_child,
                articulation_link_names=VALID_LINKS,
                selected_contact_signal_link_names=["fl_link7", "fl_link8"],
            )

        with self.assertRaisesRegex(ValueError, "exactly two finger joints"):
            build_f2_gripper_assembly_topology_receipt(
                arm="left",
                move_group_link_name="fl_link6",
                gripper_joint_topology=VALID_TOPOLOGY[:1],
                articulation_link_names=VALID_LINKS,
                selected_contact_signal_link_names=["fl_link7"],
            )

    def test_right_arm_or_unknown_link_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "frozen to the left arm"):
            build_f2_gripper_assembly_topology_receipt(
                arm="right",
                move_group_link_name="fr_link6",
                gripper_joint_topology=[
                    {
                        "joint_name": "fr_joint7",
                        "parent_link_name": "fr_link6",
                        "child_link_name": "fr_link7",
                    },
                    {
                        "joint_name": "fr_joint8",
                        "parent_link_name": "fr_link6",
                        "child_link_name": "fr_link8",
                    },
                ],
                articulation_link_names=["fr_link6", "fr_link7", "fr_link8"],
                selected_contact_signal_link_names=["fr_link7", "fr_link8"],
            )

        with self.assertRaisesRegex(ValueError, "finger_children_exist"):
            build_f2_gripper_assembly_topology_receipt(
                arm="left",
                move_group_link_name="fl_link6",
                gripper_joint_topology=VALID_TOPOLOGY,
                articulation_link_names=["fl_link5", "fl_link6", "fl_link7"],
                selected_contact_signal_link_names=["fl_link7", "fl_link8"],
            )

    def test_tampering_or_collection_flags_break_receipt_validation(self):
        tampered = valid_receipt()
        tampered["allowed_gripper_assembly_body_names"].append("fl_link5")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_f2_gripper_assembly_topology_receipt(tampered)

        rehashed_flag = valid_receipt()
        rehashed_flag["stage0_authorized"] = True
        # A caller cannot legitimize this mutation by retaining the old hash.
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_f2_gripper_assembly_topology_receipt(rehashed_flag)


if __name__ == "__main__":
    unittest.main()
