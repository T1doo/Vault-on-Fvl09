"""Stream all contact rows from sealed NPZ segments without allocating their full Unicode array."""
import importlib.util
import hashlib
import json
import zipfile
from pathlib import Path
import numpy as np
from gate import evaluate_window, base

OLD = Path(__file__).resolve().parent.parent / "f3_preclose_physical_consistency_gate_v1/replay.py"
if hashlib.sha256(OLD.read_bytes()).hexdigest() != "e3fc6fcfec6353a04dede6704cbf4e1f8be479a4d0042d9926f99e9ee397d656":
    raise ValueError("V1 replay changed")
s = importlib.util.spec_from_file_location("f3_replay_v1_bound", OLD)
old = importlib.util.module_from_spec(s)
# V1 replay imports these pure helpers from the local gate module.
import gate
gate.canonical_hash = base.canonical_hash
gate.evaluate_preclose_sequence = base.evaluate_preclose_sequence
s.loader.exec_module(old)
CASE_DIRECTORIES = old.CASE_DIRECTORIES
TRACE_ROOT = old.TRACE_ROOT
replay_sealed_cohort = old.replay_sealed_cohort


def contact_window(path, start, end, positions):
    with zipfile.ZipFile(path) as z:
        with z.open("contact_pairs_json.npy") as f:
            version = np.lib.format.read_magic(f)
            shape, fortran, dtype = np.lib.format._read_array_header(f, version)
            if fortran or len(shape) != 1 or dtype.kind != "U" or end >= shape[0]:
                raise ValueError("invalid contact stream")
            f.seek(f.tell() + (start + 1) * dtype.itemsize)
            for i in range(start + 1, end + 1):
                raw = f.read(dtype.itemsize)
                if len(raw) != dtype.itemsize:
                    raise ValueError("truncated contact row")
                pairs = json.loads(str(np.frombuffer(raw, dtype=dtype, count=1)[0]))
                if not isinstance(pairs, list):
                    raise ValueError("invalid contact list")
                yield {"row_index": i, "contact_pairs": pairs,
                       "contact_signal_complete": True, "bottle_position_m": positions[i, :3]}


def replay_case(name):
    case = old.TRACE_ROOT / name
    scene, scene_sha = old._load_self_hashed(case / "physical/scene_receipt.json", "receipt_sha256")
    spec, spec_sha = old._load_self_hashed(case / "physical_spec.json", "spec_sha256")
    trace = case / "physical/physical_trace.npz"
    digest = old.file_sha(trace)
    if digest != scene["trace"]["sha256"]:
        raise ValueError("trace changed")
    physical = scene["result"]["physical_result"]
    executions = physical["execution_receipts"]
    planners = physical["planner_result"]["segment_receipts"]
    targets = {t["segment_id"]: t for t in spec["ordered_targets"]}
    with np.load(trace, allow_pickle=False) as z:
        if str(z["action_layout_version"].item()) != old.ACTION_LAYOUT_VERSION:
            raise ValueError("layout changed")
        if tuple(json.loads(str(z["action_layout_dimensions_json"].item()))) != old.ACTION_LAYOUT_DIMENSIONS:
            raise ValueError("dimensions changed")
        links = json.loads(str(z["selected_gripper_links_json"].item()))
        arrays = {k: z[k] for k in ("eef_pose", "object_pose", "joint_qpos", "component_masks")}
    ends = [int(x["end_trace_row"]) for x in executions[:2]]
    endpoints = old._read_contact_rows(trace, ends)
    reports = []
    for i, stage in enumerate(("pregrasp", "grasp")):
        e = executions[i]
        boundary = old._segment_snapshot(stage=stage, execution=e, target=targets[e["segment_id"]],
                     planner_segment=planners[i], arm=spec["arm"], selected_links=links,
                     contact_pairs=endpoints[ends[i]], **arrays)
        start, end = int(e["start_trace_row"]), int(e["end_trace_row"])
        reports.append(evaluate_window(boundary, contact_window(trace, start, end, arrays["object_pose"]),
                                       start=start, end=end))
    result = {"case": name, "recipe_id": spec["recipe_id"] if "recipe_id" in spec else spec["recipe"]["recipe_id"],
              "trace_sha256": digest, "scene_file_sha256": scene_sha, "spec_file_sha256": spec_sha,
              "segments": reports, "rejected_before_close": any(not x["pass"] for x in reports)}
    result["receipt_sha256"] = base.canonical_hash(result)
    return result


if __name__ == "__main__":
    rows = [replay_case(n) for n in old.CASE_DIRECTORIES]
    result = {"schema_version": "cmf_f3_full_window_replay_v1_1", "rows": rows,
              "case_count": len(rows), "all_four_rejected_before_close": all(r["rejected_before_close"] for r in rows),
              "gpu_used": False, "scene_created": False, "source_mutated": False}
    result["receipt_sha256"] = base.canonical_hash(result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
