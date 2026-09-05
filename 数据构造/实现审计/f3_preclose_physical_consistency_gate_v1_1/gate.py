"""Full-window CPU-only pre-close evaluation; no simulator or GPU entry point."""
import importlib.util
import hashlib
from pathlib import Path
import numpy as np

OLD = Path(__file__).resolve().parent.parent / "f3_preclose_physical_consistency_gate_v1/gate.py"
if hashlib.sha256(OLD.read_bytes()).hexdigest() != "ca33ced9e4da99d9c3fcc21f4e7133a99bacd6cdfecd74183fe79012de9274e1":
    raise ValueError("immutable V1 Gate changed")
spec = importlib.util.spec_from_file_location("f3_preclose_v1_bound", OLD)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def evaluate_window(boundary, rows, *, start, end):
    """Rows must cover start+1..end exactly, including empty contact lists."""
    if type(start) is not int or type(end) is not int or end <= start:
        raise ValueError("invalid segment bounds")
    terminal = base.evaluate_preclose_stage(boundary)
    expected = start + 1
    first = None
    maximum_displacement = 0.0
    maximum_impulse = 0.0
    minimum_separation = None
    n = 0
    for row in rows:
        if type(row.get("row_index")) is not int or row["row_index"] != expected:
            raise ValueError("missing, duplicated or reordered window row")
        if expected > end:
            raise ValueError("extra window row")
        if row.get("contact_signal_complete") is not True or "contact_pairs" not in row:
            failures = ["contact_signal_incomplete"]
            pairs = []
        else:
            snap = dict(boundary)
            snap["contact_pairs"] = row["contact_pairs"]
            snap["realized_bottle_position_m"] = row["bottle_position_m"]
            # Only contacts/displacement are evaluated at intermediate rows.
            # Endpoint qpos/EEF checks remain in terminal.
            checked = base.evaluate_preclose_stage(snap)
            failures = [x for x in checked["failure_codes"] if x not in
                        {"selected_arm_qpos_tracking_failed", "eef_tracking_failed"}]
            pairs = checked["contact_audit"]["relevant_pairs"]
        xyz = np.asarray(row["bottle_position_m"], dtype=float)
        initial = np.asarray(boundary["initial_bottle_position_m"], dtype=float)
        if xyz.shape != (3,) or not np.all(np.isfinite(xyz)):
            raise ValueError("invalid row bottle position")
        displacement = float(np.linalg.norm(xyz - initial))
        maximum_displacement = max(maximum_displacement, displacement)
        if displacement > base.BOTTLE_PRECLOSE_DISPLACEMENT_LIMIT_M:
            if "bottle_displaced_before_close" not in failures:
                failures.append("bottle_displaced_before_close")
        for pair in pairs:
            impulse = pair.get("impulse_norm_sum")
            separation = pair.get("minimum_signed_separation_m")
            if impulse is not None:
                maximum_impulse = max(maximum_impulse, float(impulse))
            if separation is not None:
                minimum_separation = float(separation) if minimum_separation is None else min(minimum_separation, float(separation))
        if failures and first is None:
            bad_pair = next((p for p in pairs if p["evidence_complete"] is not True
                             or p["physical_hit_for_gate"] is True), None)
            first = {"row_index": expected, "failure_codes": failures, "pair": bad_pair}
        expected += 1
        n += 1
    if expected != end + 1:
        raise ValueError("incomplete segment window")
    if first is None and terminal["pass"] is not True:
        first = {"row_index": end, "failure_codes": terminal["failure_codes"], "pair": None}
    result = {
        "schema_version": "cmf_f3_full_window_preclose_v1_1",
        "stage": boundary["stage"], "arm": boundary["arm"],
        "start_exclusive": start, "end_inclusive": end, "rows_checked": n,
        "first_failure": first, "maximum_bottle_displacement_m": maximum_displacement,
        "maximum_relevant_impulse": maximum_impulse,
        "minimum_signed_separation_m": minimum_separation,
        "endpoint_receipt": terminal, "pass": first is None,
        "stop_before_close": first is not None,
        "close_permitted_by_this_check": first is None and boundary["stage"] == "grasp",
        "gpu_execution_authorized": False,
    }
    result["receipt_sha256"] = base.canonical_hash(result)
    return result
