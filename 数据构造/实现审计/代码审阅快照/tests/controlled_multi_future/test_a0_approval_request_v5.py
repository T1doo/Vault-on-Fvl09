import unittest

from controlled_multi_future.a0_approval_request_v5 import build_a0_user_approval_request_v5


class A0ApprovalRequestV5Test(unittest.TestCase):
    def test_request_is_fully_bound_but_never_self_approved(self):
        request = build_a0_user_approval_request_v5(
            content_commit="1" * 40,
            authorization_receipt_path="/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/authorizations/a0.json",
            output_namespace="/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/probe_outputs/a0-v5-run1",
            consumption_ledger_directory="/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/authorization_consumed",
            guard_receipt_path="/nfs_share/lijunhui/Vault-on-Fvl09/数据构造/实现审计/probe_outputs/a0-v5-run1.guard.json",
        )
        self.assertFalse(request["approved"])
        self.assertFalse(request["gpu_probe_authorized"])
        self.assertFalse(request["stage0_authorized"])
        template = request["authorization_template_pending_user_action"]
        self.assertFalse(template["approved"])
        self.assertIsNone(template["issued_at"])
        self.assertIsNone(template["expires_at"])
        self.assertIsNone(template["receipt_sha256"])
        self.assertEqual(request["family"], "F1")
        self.assertEqual(request["scene_seed"], 20260829)
        self.assertEqual(request["post_setup_planner_query_limit"], 0)
        self.assertEqual(request["post_setup_controlled_action_limit"], 0)
        self.assertEqual(request["timeout_seconds"], 600)
        self.assertEqual(request["max_invocations"], 1)
        self.assertEqual(len(request["approval_request_sha256"]), 64)

    def test_request_rejects_non_workspace_paths_and_non_commit(self):
        common = dict(
            content_commit="1" * 40,
            authorization_receipt_path="/nfs_share/lijunhui/auth.json",
            output_namespace="/nfs_share/lijunhui/output",
            consumption_ledger_directory="/nfs_share/lijunhui/ledger",
            guard_receipt_path="/nfs_share/lijunhui/guard.json",
        )
        bad = dict(common)
        bad["content_commit"] = "short"
        with self.assertRaises(ValueError):
            build_a0_user_approval_request_v5(**bad)
        bad = dict(common)
        bad["output_namespace"] = "/tmp/out"
        with self.assertRaises(ValueError):
            build_a0_user_approval_request_v5(**bad)


if __name__ == "__main__":
    unittest.main()
