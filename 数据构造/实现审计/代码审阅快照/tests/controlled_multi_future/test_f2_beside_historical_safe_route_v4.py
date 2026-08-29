import copy
import json
import unittest

import numpy as np

from controlled_multi_future.f2_beside_historical_safe_route_v4 import (
    FACILITY_CLEARANCE_MARGIN_M,
    HISTORICAL_SAFE_STAND_RELATIVE_XY_M,
    PREPLACE_OFFSET_M,
    RELEASE_TARGET_INDEX,
    SEGMENT_IDS,
    TABLE_SUPPORT_PLANE_Z_M,
    actor_origin_z_for_table_support,
    audit_historical_safe_beside_route,
    build_historical_safe_beside_route,
)
from controlled_multi_future.f2_mutually_exclusive_region_layout_v2 import LAYOUT
from controlled_multi_future.current_hasher import hash_json


CURRENT_EEF_POSE = [
    -0.28126898407936096,
    0.03950060158967972,
    1.0534868240356445,
    0.6529548211117748,
    -0.2691218087914074,
    0.6530879779012335,
    0.2733121781783769,
]
CURRENT_ACTOR_POSE = [
    -0.2819966971874237,
    0.04167619347572327,
    0.8619921207427979,
    0.4986494183540344,
    0.5014686584472656,
    0.4990118741989136,
    0.5008647441864014,
]
REST_EEF_POSE = [
    -0.297923743724823,
    -0.31380218267440796,
    0.9419903755187988,
    0.7000005275036494,
    -1.61680875200991e-05,
    6.60717435563285e-06,
    0.7141423255833185,
]
STAND_POSE = [
    0.20000000298023224,
    -0.029999999329447746,
    0.7699999809265137,
    0.7071068286895752,
    0.7071068286895752,
    0.0,
    0.0,
]
CAN_HALF_EXTENTS = [
    0.03254198611123893,
    0.04828508321025152,
    0.03263935967162212,
]
CAN_LOCAL_GEOMETRY_CENTER = [
    -4.492628302420404e-06,
    0.04756748877763528,
    -5.966823217269159e-05,
]
FACILITY_AABBS = {
    "box": {
        "lower": [-0.3867366615532792, -0.2967524444804943, 0.7782640365609332],
        "upper": [-0.19326477115196167, -0.10323940641182028, 0.8902039954675898],
    },
    "scale": {
        "lower": [-0.17783340246447576, -0.2585192468935225, 0.7684947985166519],
        "upper": [-0.02176928676077758, -0.14148053028181595, 0.8091258285265568],
    },
    "stand": {
        "lower": [0.10332784420150587, -0.061157665244199716, 0.768167213612969],
        "upper": [0.2966662074960559, 0.001157561351189499, 0.8130094874900812],
    },
}


def build_route():
    return build_historical_safe_beside_route(
        current_eef_pose=CURRENT_EEF_POSE,
        current_actor_pose=CURRENT_ACTOR_POSE,
        stand_pose=STAND_POSE,
        rest_eef_pose=REST_EEF_POSE,
        can_local_geometry_center_m=CAN_LOCAL_GEOMETRY_CENTER,
        can_half_extents_m=CAN_HALF_EXTENTS,
        facility_aabbs=FACILITY_AABBS,
    )


class F2BesideHistoricalSafeRouteV4Test(unittest.TestCase):
    def test_single_historical_sector_has_center_aware_table_support(self):
        route = build_route()
        self.assertTrue(route["audit"]["pass"])
        self.assertFalse(route["candidate_search_enabled"])
        self.assertEqual(route["route_count"], 1)
        self.assertEqual(
            tuple(route["stand_relative_xy_m"]),
            HISTORICAL_SAFE_STAND_RELATIVE_XY_M,
        )
        self.assertTrue(
            np.allclose(route["stand_pose"], STAND_POSE, atol=1e-7, rtol=0.0)
        )
        self.assertTrue(
            np.allclose(
                route["target_actor_pose"][:2],
                np.asarray(STAND_POSE[:2])
                + np.asarray(HISTORICAL_SAFE_STAND_RELATIVE_XY_M),
                atol=1e-12,
                rtol=0.0,
            )
        )
        expected_z = actor_origin_z_for_table_support(
            table_plane_z_m=TABLE_SUPPORT_PLANE_Z_M,
            actor_quaternion_wxyz=[0.5, 0.5, 0.5, 0.5],
            can_local_geometry_center_m=CAN_LOCAL_GEOMETRY_CENTER,
            can_half_extents_m=CAN_HALF_EXTENTS,
        )
        self.assertAlmostEqual(expected_z, 0.7407175944326162, places=12)
        self.assertAlmostEqual(route["target_actor_pose"][2], expected_z, places=12)
        self.assertGreater(LAYOUT["can_xyz"][2] - expected_z, 0.049)
        self.assertAlmostEqual(
            route["audit"]["target_geometry"]["target_obb_bottom_z_m"],
            TABLE_SUPPORT_PLANE_Z_M,
            places=12,
        )

    def test_route_has_one_exact_reciprocal_hub_and_eight_cm_preplace(self):
        route = build_route()
        targets = route["targets"]
        self.assertEqual(
            tuple(item["segment_id"] for item in targets), SEGMENT_IDS
        )
        self.assertEqual(route["release_target_index"], RELEASE_TARGET_INDEX)
        self.assertEqual(targets[0]["pose"], targets[4]["pose"])
        self.assertEqual(targets[1]["pose"], targets[3]["pose"])
        self.assertTrue(
            np.allclose(
                np.asarray(targets[1]["pose"][:3])
                - np.asarray(targets[2]["pose"][:3]),
                [0.0, 0.0, PREPLACE_OFFSET_M],
                atol=1e-12,
                rtol=0.0,
            )
        )
        self.assertTrue(
            np.allclose(
                targets[2]["pose"][:3],
                [0.05054307392, -0.07128073079, 0.93222098593],
                atol=2e-8,
                rtol=0.0,
            )
        )
        self.assertTrue(
            np.allclose(
                targets[0]["pose"][:3],
                [-0.11536295508, -0.01589006460, 1.01222098593],
                atol=2e-8,
                rtol=0.0,
            )
        )

    def test_strict_predicate_and_exact_obb_clearance_audits_pass(self):
        audit = build_route()["audit"]
        self.assertTrue(audit["predicate_audit"]["exclusive_beside"])
        self.assertFalse(audit["predicate_audit"]["inside"])
        self.assertFalse(audit["predicate_audit"]["on"])
        self.assertAlmostEqual(
            audit["predicate_audit"]["radial_distance_m"],
            np.hypot(0.15, 0.04),
            places=12,
        )
        clearance = audit["target_facility_clearance_audit"]
        self.assertTrue(clearance["pass"])
        for role in ("box", "scale", "stand"):
            self.assertGreaterEqual(
                clearance["facility_clearances"][role]["separating_clearance_m"],
                FACILITY_CLEARANCE_MARGIN_M,
            )
        held = audit["held_waypoint_envelope_audit"]
        self.assertTrue(held["pass"])
        self.assertFalse(held["curved_planned_path_covered"])
        self.assertTrue(held["official_curobo_whole_robot_collision_still_required"])
        self.assertTrue(held["actual_execution_contact_gate_required"])
        json.dumps(audit, allow_nan=False)
        self.assertEqual(len(hash_json(audit)), 64)

    def test_stand_move_or_spawn_height_tampering_fails_closed(self):
        moved = build_route()
        moved["stand_pose"][0] += 0.01
        moved["target_actor_pose"][0] += 0.01
        for item in moved["targets"]:
            item["pose"][0] += 0.01
        self.assertFalse(audit_historical_safe_beside_route(moved)["pass"])
        self.assertFalse(
            audit_historical_safe_beside_route(moved)["checks"]["no_stand_move"]
        )

        elevated = build_route()
        elevated["target_actor_pose"][2] = LAYOUT["can_xyz"][2]
        elevated_audit = audit_historical_safe_beside_route(elevated)
        self.assertFalse(elevated_audit["pass"])
        self.assertFalse(elevated_audit["checks"]["target_actor_exact"])
        self.assertFalse(elevated_audit["checks"]["center_aware_table_support"])

    def test_missing_facility_or_intruding_facility_fails_closed(self):
        missing = build_route()
        del missing["facility_aabbs"]["stand"]
        with self.assertRaisesRegex(ValueError, "exactly box, scale, and stand"):
            audit_historical_safe_beside_route(missing)

        intruding = build_route()
        target = np.asarray(intruding["target_actor_pose"][:3])
        intruding["facility_aabbs"]["stand"] = {
            "lower": (target - 0.02).tolist(),
            "upper": (target + 0.02).tolist(),
        }
        audit = audit_historical_safe_beside_route(intruding)
        self.assertFalse(audit["pass"])
        self.assertFalse(audit["checks"]["target_facility_clearance"])
        self.assertFalse(audit["checks"]["sampled_exact_obb_held_envelope"])


if __name__ == "__main__":
    unittest.main()
