import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from controlled_multi_future.canonical_artifact import canonical_hash_json
from controlled_multi_future.f3_scene_binding_equivalence_v1 import (
    audit_f3_scene_binding_equivalence_v1,
)
from controlled_multi_future.planner_qualification_integration_v2_3_1a import (
    build_manifest_bundle_v2_3_1a,
)
from controlled_multi_future.planner_qualification_scene_bridges_v2_3_1a import (
    prepare_exact_job_bridge_envelope_v2_3_1a,
    run_with_production_scene_bridge_v2_3_1a,
)


def recipe():
    return {
        "arm": "left",
        "asset": {"modelname": "001_bottle", "model_id": 13},
        "asset_record_sha256": "a" * 64,
    }


def expected_binding():
    return {
        "scene_spec_sha256": "1" * 64,
        "scene_layout_sha256": "2" * 64,
        "bottle_asset_sha256": "a" * 64,
        "bottle_actor_pose_sha256": "3" * 64,
        "robot_config_sha256": "4" * 64,
    }


def runtime_asset():
    return {
        "actor_name": "f3_main_bottle",
        "modelname": "001_bottle",
        "model_id": 13,
    }


def runtime_tuple():
    return {
        "asset": {"modelname": "001_bottle", "model_id": 13},
        "arm": "left",
    }


class F3SceneBindingEquivalenceV1Test(unittest.TestCase):
    def audit(self, *, bottle_pose=None, pad_contact=True, asset=None):
        return audit_f3_scene_binding_equivalence_v1(
            recipe=recipe(),
            expected_scene_binding=expected_binding(),
            actual_scene_binding={
                **expected_binding(),
                "bottle_actor_pose_sha256": "9" * 64,
            },
            actual_bottle_pose=bottle_pose
            or [-0.1849084, -0.0599338, 0.7838153, 0.0721385, 0.0003441, 0.9973943, -0.0009695],
            actual_pad_pose=[-0.180000007, -0.059999999, 0.745000005, 1, 0, 0, 0],
            actual_marker_pose=[0, -0.050000001, 0.949999988, 1, 0, 0, 0],
            scene_seed=2026090201,
            scene_instance_id="scene-1",
            canonical_settle_steps=60,
            actor_sleep_state=True,
            contact_state={
                "contact_api_available": True,
                "bottle_pad_contact": pad_contact,
                "bottle_table_contact": False,
            },
            runtime_asset=runtime_asset() if asset is None else asset,
            runtime_tuple=runtime_tuple(),
        )

    def test_historical_settle_drift_is_retained_and_accepted(self):
        result = self.audit()
        self.assertTrue(result["pass"])
        self.assertFalse(result["exact_post_settle_pose_equality_required"])
        self.assertNotEqual(
            result["expected_scene_binding"],
            result["actual_scene_binding_observation"],
        )
        payload = dict(result)
        digest = payload.pop("receipt_sha256")
        self.assertEqual(digest, canonical_hash_json(payload))

    def test_out_of_tolerance_bottle_fails_closed(self):
        result = self.audit(bottle_pose=[-0.16, -0.06, 0.785, 0, 0, 1, 0])
        self.assertFalse(result["pass"])
        self.assertEqual(
            result["failure_code"],
            "F3_ACTUAL_SCENE_BINDING_NOT_PHYSICALLY_EQUIVALENT",
        )

    def test_wrong_asset_identity_fails_even_when_pose_matches(self):
        result = self.audit(
            asset={
                "actor_name": "f3_main_bottle",
                "modelname": "001_bottle",
                "model_id": 5,
            }
        )
        self.assertFalse(result["pass"])
        self.assertFalse(result["exact_identity_checks"]["runtime_asset_model_bound"])

    def test_missing_support_contact_fails(self):
        result = self.audit(pad_contact=False)
        self.assertFalse(result["pass"])
        self.assertFalse(
            result["physical_equivalence_checks"]["bottle_supported_by_pad"]
        )

    def test_production_bridge_accepts_supported_settle_drift_but_keeps_nominal_identity(self):
        bundle = build_manifest_bundle_v2_3_1a()
        entry = bundle["manifests"]["F3_STAGE_A"]["ordered_recipes"][0]
        envelope = prepare_exact_job_bridge_envelope_v2_3_1a(
            job_kind="F3_STAGE_A",
            job_id="f3-equivalence-e2e",
            manifest_entry=entry,
            manifest_context={},
            manifest_sha256=bundle["f3_stage_a_panel_sha256"],
            planner_reset_nonce=303,
        )

        class Actor:
            def __init__(self, pose):
                self.pose = pose

            def get_pose(self):
                return SimpleNamespace(
                    p=np.asarray(self.pose[:3]), q=np.asarray(self.pose[3:])
                )

            def get_components(self):
                return []

        source_x = -0.18 if entry["recipe"]["arm"] == "left" else 0.18
        scene = SimpleNamespace(
            bottle=Actor(
                [
                    source_x - 0.0049 if source_x < 0 else source_x + 0.0049,
                    -0.05993,
                    0.78382,
                    0.07214,
                    0.00034,
                    0.99739,
                    -0.00097,
                ]
            ),
            pad=Actor([source_x, -0.06, 0.745, 1, 0, 0, 0]),
            central_marker=Actor([0, -0.05, 0.95, 1, 0, 0, 0]),
            _cmf_setup_kwargs={"seed": envelope["actual_scene_seed"]},
            _cmf_canonical_settle_steps=60,
            _cmf_scene_instance_id="f3-equivalence-scene",
            _cmf_f3_asset_grasp_tuple_v2={
                "asset": entry["recipe"]["asset"],
                "arm": entry["recipe"]["arm"],
            },
        )

        class Context:
            cleanup_receipt = None

            def __enter__(self):
                return SimpleNamespace(scene=scene)

            def __exit__(self, exc_type, exc, tb):
                self.cleanup_receipt = {
                    "cleanup_safety_pass": True,
                    "orphan_process_count": 0,
                }

        class Adapter:
            def __init__(self, **kwargs):
                pass

            def scene(self, *args, **kwargs):
                return Context()

            def _entity_payloads(self, value):
                return {
                    "bottle": {
                        "actor_name": "f3_main_bottle",
                        "modelname": entry["recipe"]["asset"]["modelname"],
                        "model_id": entry["recipe"]["asset"]["model_id"],
                    }
                }

        auth = {
            "job_kind": "F3_STAGE_A",
            "family": "F3",
            "runner_symbol": envelope["runner_symbol"],
            "scene_seed": envelope["actual_scene_seed"],
            "implementation_source_sha256": "a" * 64,
            "job_spec": {
                "job_id": "f3-equivalence-e2e",
                "scene_seed": envelope["actual_scene_seed"],
                "planner_reset_nonce": 303,
                "manifest_entry": entry,
                "bridge_envelope": envelope,
            },
        }
        terminal = {"stage_a_pass": True, "candidate_ready": False}
        with patch(
            "controlled_multi_future.planner_qualification_scene_bridges_v2_3_1a."
            "RoboTwinRealSapienF3AssetGraspV2Adapter",
            Adapter,
        ), patch(
            "controlled_multi_future.planner_qualification_scene_bridges_v2_3_1a."
            "_entity_sleep_state",
            return_value=True,
        ), patch(
            "controlled_multi_future.planner_qualification_scene_bridges_v2_3_1a."
            "_f3_contact_state",
            return_value={
                "contact_api_available": True,
                "bottle_pad_contact": True,
                "bottle_table_contact": False,
            },
        ), patch(
            "controlled_multi_future.planner_qualification_scene_bridges_v2_3_1a."
            "run_f3_stage_a_planner_v3_1",
            return_value=terminal,
        ):
            result = run_with_production_scene_bridge_v2_3_1a(
                auth,
                output_root=__import__("pathlib").Path(
                    "/nfs_share/lijunhui/Robotwin2/tmp/f3-equivalence-not-created"
                ),
            )
        self.assertEqual(result["terminal"], terminal)
        self.assertTrue(result["f3_scene_binding_equivalence"]["pass"])
        self.assertEqual(scene._cmf_f3_scene_binding_v3_1, entry["scene_binding"])


if __name__ == "__main__":
    unittest.main()
