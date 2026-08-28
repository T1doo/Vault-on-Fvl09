"""Frozen implementation-only contracts for ``controlled_multi_future_runtime_v2``.

The scientific design remains ``controlled_multi_future_f1_f4_v1_2``.  These
values are implementation mappings and provisional probe tolerances; none is
a Stage-2-frozen scientific threshold.
"""

from __future__ import annotations

from .geometry import IMPLEMENTATION_VERSION


FAMILY_IMPLEMENTATION_VERSIONS = {
    "F1": "f1_transport_and_true_inside_v2",
    "F2": "f2_actor_to_eef_beside_mapping_v3",
    "F3": "f3_return_equivalence_v2",
    "F4": "f4_common_prefix_mapping_v2",
}

# Actor-local conservative empty volume for 062_plasticbox/base3.  Unlike the
# previous outer OBB, this region excludes the collision-mesh bottom and walls.
# It was derived from the official collision decomposition and both official
# inside-bottom functional points.  GPU runtime still has to verify contacts.
PLASTICBOX_BASE3_CAVITY = {
    "coordinate_frame": "062_plasticbox/base3 actor-local xyz",
    "lower_m": [-0.050, 0.018, -0.040],
    "upper_m": [0.050, 0.070, 0.040],
    "collision_free_core_lower_m": [-0.050, 0.024, -0.040],
    "support_surface_band_local_y_m": [0.018, 0.026],
    "target_center_local_m": [0.0, 0.047, 0.0],
    "collision_mesh_sha256": "3a8d2074dbbc59b8e521469eb571e09c70864a18f57fef1c0711ff3569a7617c",
    "model_data_sha256": "a42959362e9a0c94e8aa1ad36e75c866455e951fb6ee90da706fe203b7620ad0",
    "derivation_status": "containment_includes_support_boundary; collision-free core excludes bottom; pending runtime contact validation",
}

# The common-X block is supported by the tray floor; its footprint, rather
# than its full height, must remain within this interior region.
TRAY_BASE0_SUPPORT_REGION = {
    "coordinate_frame": "008_tray/base0 actor-local xyz",
    "lower_m": [-0.120, 0.006, -0.070],
    "upper_m": [0.120, 0.029, 0.070],
    "target_center_local_m": [-0.0745, 0.030, 0.0],
    "horizontal_axes": [0, 2],
    "collision_mesh_sha256": "77d926998fb1a58ea2c2951be3221fff561c5e8df5af317fa0dd23bdbd6b7373",
    "model_data_sha256": "d5ed105c12c12f7e2be3b2be2305c21badbd11da3a10f4f00dac0bf7d44b469f",
    "derivation_status": "conservative_support_region_pending_runtime_contact_validation",
}

PROVISIONAL_RUNTIME_THRESHOLDS = {
    "non_target_displacement_m": 0.010,
    "stable_linear_speed_mps": 0.020,
    "stable_window_frames": 50,
    "position_error_m": 0.030,
    "orientation_error": 0.020,
    "rest_position_error_m": 0.030,
    "neutral_position_error_m": 0.030,
    "support_height_tolerance_m": 0.012,
    "eef_stationary_linear_speed_mps": 0.010,
    "eef_stationary_angular_speed_rps": 0.050,
    "motion_min_axis_amplitude_m": 0.040,
    "motion_max_off_axis_m": 0.015,
    "motion_max_return_error_m": 0.015,
    "motion_max_orientation_drift": 0.050,
    "motion_min_contact_fraction": 0.950,
    "motion_max_contact_break_count": 0,
}

RUNTIME_V2_PROBE_VARIANTS = {
    "F1": ("transport_true_inside",),
    "F2": ("actor_to_eef_stand",),
    "F3": ("return_equivalence",),
    "F4": ("common_prefix_mapping",),
}

PROBE_PLANNER_QUERY_LIMITS = {"F1": 12, "F2": 12, "F3": 18, "F4": 12}

RUNTIME_V2_AUTHORIZATION = {
    "cpu_static_repairs_authorized": True,
    "gpu_probe_authorized": True,
    "gpu_probe_authorization_scope": "four bounded nonformal runtime-v2 probes on any independently fresh-idle physical GPU0-7, sequentially",
    "stage0_authorized": False,
    "formal_collection_authorized": False,
}
