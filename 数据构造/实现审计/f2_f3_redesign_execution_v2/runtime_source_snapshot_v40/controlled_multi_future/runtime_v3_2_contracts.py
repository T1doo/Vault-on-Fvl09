"""Frozen implementation mappings selected by runtime-v3_2 CPU audits."""

from __future__ import annotations


IMPLEMENTATION_VERSION = "controlled_multi_future_runtime_v3_2"

F2_SELECTED_MAIN_OBJECT = {"modelname": "071_can", "model_id": 1, "arm": "left"}
F2_SELECTED_PLASTICBOX = {"modelname": "062_plasticbox", "model_id": 2}
F2_INSIDE_LOCAL_AXIS_PERMUTATION = (1, 0, 2)
F2_INSIDE_LOCAL_QUATERNION_WXYZ = (2 ** -0.5, 0.0, 0.0, 2 ** -0.5)
F2_PLASTICBOX_BASE2_CAVITY = {
    "coordinate_frame": "062_plasticbox/base2 actor-local xyz",
    "lower_m": [-0.07824613475799559, 0.02176539531350136, -0.07823097729682921],
    "upper_m": [0.07775386524200455, 0.10476539531350136, 0.07776902270317093],
    "target_center_local_m": [-0.00024613475799552, 0.06326539531350136, -0.00023097729682914],
    "safety_margin_per_side_m": 0.005,
    "collision_mesh_sha256": "089b4b11fac544d2225fc8d7b0113b6059322047e57167559360444457b5838b",
    "model_data_sha256": "e2712f8aa9f0e53a2a7f24a6ee815a488faf7f19abc82cb0697cdd9b4ce7dbbf",
    "derivation": "15 official convex pieces; 1mm line-grid; raw cavity contracted 5mm per side",
}
