#!/usr/bin/env python3
"""Run one manifest-bound micro-qualification family job on one idle GPU."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


WORKSPACE = Path("/nfs_share/lijunhui")
PROJECT = WORKSPACE / "Robotwin2/project/RoboTwin"
ENV_PYTHON = WORKSPACE / "Robotwin2/env/bin/python"
CUDA_ROOT = WORKSPACE / "Robotwin2/tools/cuda-12.1"
LEASE_ROOT = WORKSPACE / "Robotwin2/gpu_leases/production_micro_gate_v1"


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def python_tree_sha(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(root).rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def write_new(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def load_manifest(path: Path):
    path = Path(path).resolve()
    if not str(path).startswith(str(WORKSPACE) + "/"):
        raise ValueError("manifest is outside workspace")
    value = json.loads(path.read_text(encoding="utf-8"))
    payload = dict(value)
    digest = payload.pop("manifest_sha256", None)
    if digest != canonical_hash(payload):
        raise ValueError("manifest self-hash mismatch")
    if value.get("approved") is not True:
        raise PermissionError("micro gate is not approved")
    if value.get("source_freeze_vault_head") != "02d3b65198c2482b4f84dcab705f8e5379aa733f":
        raise PermissionError("micro gate source freeze changed")
    return value


def nvidia_snapshot():
    gpu = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,uuid,memory.used,utilization.gpu,pstate",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    )
    rows = []
    for line in gpu.stdout.splitlines():
        fields = [item.strip() for item in line.split(",")]
        if len(fields) != 5:
            raise RuntimeError("unexpected nvidia-smi GPU row")
        rows.append(
            {
                "index": int(fields[0]),
                "uuid": fields[1],
                "memory_used_mib": int(fields[2]),
                "utilization_gpu_percent": int(fields[3]),
                "pstate": fields[4],
                "compute_processes": [],
            }
        )
    compute = subprocess.run(
        [
            "nvidia-smi",
            "--query-compute-apps=gpu_uuid,pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    )
    by_uuid = {item["uuid"]: item for item in rows}
    for line in compute.stdout.splitlines():
        if not line.strip():
            continue
        fields = [item.strip() for item in line.split(",")]
        if len(fields) != 4:
            raise RuntimeError("unexpected nvidia-smi compute row")
        if fields[0] in by_uuid:
            by_uuid[fields[0]]["compute_processes"].append(
                {
                    "pid": int(fields[1]),
                    "process_name": fields[2],
                    "used_memory_mib": int(fields[3]),
                }
            )
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "gpus": rows,
    }


def selected(snapshot, physical_index: int, uuid: str):
    matches = [
        item
        for item in snapshot["gpus"]
        if item["index"] == physical_index and item["uuid"] == uuid
    ]
    if len(matches) != 1:
        raise RuntimeError("physical GPU index/UUID binding mismatch")
    return matches[0]


def idle(item) -> bool:
    return bool(
        item["memory_used_mib"] <= 64
        and item["utilization_gpu_percent"] == 0
        and item["pstate"] in {"P8", "P12"}
        and not item["compute_processes"]
    )


def child_environment(uuid: str, physical_index: int, cache: Path):
    environment = dict(os.environ)
    environment.pop("LD_LIBRARY_PATH", None)
    environment.update(
        {
            "CUDA_VISIBLE_DEVICES": uuid,
            "CUDA_HOME": str(CUDA_ROOT),
            "PYTHONPATH": str(PROJECT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PATH": ":".join(
                [
                    str(WORKSPACE / "Robotwin2/env/bin"),
                    str(CUDA_ROOT / "bin"),
                    str(WORKSPACE / "Robotwin2/tools/miniforge3/bin"),
                    "/usr/local/sbin",
                    "/usr/local/bin",
                    "/usr/sbin",
                    "/usr/bin",
                    "/sbin",
                    "/bin",
                ]
            ),
            "CMF_GPU_GUARD_PHYSICAL_INDEX": str(physical_index),
        }
    )
    for name, relative in {
        "CONDA_PKGS_DIRS": "conda_pkgs",
        "CUDA_CACHE_PATH": "cuda",
        "HOME": "home",
        "MPLCONFIGDIR": "matplotlib",
        "NUMBA_CACHE_DIR": "numba",
        "TMPDIR": "tmp",
        "TORCH_EXTENSIONS_DIR": "torch_extensions",
        "TORCH_HOME": "torch",
        "XDG_CACHE_HOME": "xdg",
    }.items():
        target = cache / relative
        target.mkdir(parents=True, exist_ok=False)
        environment[name] = str(target)
    return environment


def terminate_group(child):
    errors = []
    if child is None:
        return errors
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            break
        except BaseException as exc:
            errors.append({"signal": int(sig), "type": type(exc).__name__, "message": str(exc)})
        try:
            child.wait(timeout=30)
            break
        except subprocess.TimeoutExpired:
            continue
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--physical-index", type=int, choices=range(8), required=True)
    parser.add_argument("--expected-uuid", required=True)
    args = parser.parse_args(argv)
    manifest = load_manifest(args.manifest)
    jobs = {item["job_id"]: item for item in manifest["jobs"]}
    if args.job_id not in jobs:
        raise ValueError("job is outside unified manifest")
    job = jobs[args.job_id]
    if args.physical_index not in manifest["allowed_physical_gpu_indices"]:
        raise PermissionError("physical GPU is outside approved indices")
    if file_sha(Path(manifest["guard_script_path"])) != manifest["guard_script_sha256"]:
        raise RuntimeError("guard script hash mismatch")
    runner = Path(manifest["runner_script_path"])
    if file_sha(runner) != manifest["runner_script_sha256"]:
        raise RuntimeError("job runner script hash mismatch")
    if python_tree_sha(PROJECT / "controlled_multi_future") != manifest[
        "implementation_source_sha256"
    ]:
        raise RuntimeError("active controlled source differs from frozen Phase A")
    official_head = subprocess.run(
        ["git", "-C", str(PROJECT), "rev-parse", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    ).stdout.strip()
    official_status = subprocess.run(
        ["git", "-C", str(PROJECT), "status", "--porcelain", "--untracked-files=no"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    ).stdout.strip()
    if official_head != manifest["robotwin_tracked_head"] or official_status:
        raise RuntimeError("official RoboTwin tracked source changed")
    for relative, digest in manifest["asset_hashes_by_family"][job["family"]].items():
        path = PROJECT / relative
        if not path.is_file() or file_sha(path) != digest:
            raise RuntimeError(f"asset hash mismatch: {relative}")
    output = Path(job["output_namespace"]).resolve()
    if not str(output).startswith(str(WORKSPACE) + "/") or output.exists():
        raise FileExistsError("job output namespace must be new and within workspace")
    guard_dir = Path(manifest["guard_directory"]).resolve()
    start_path = guard_dir / f"{args.job_id}.start.json"
    terminal_path = guard_dir / f"{args.job_id}.terminal.json"
    stdout_path = guard_dir / f"{args.job_id}.stdout.log"
    stderr_path = guard_dir / f"{args.job_id}.stderr.log"
    for path in (start_path, terminal_path, stdout_path, stderr_path):
        if path.exists():
            raise FileExistsError(f"immutable guard path already exists: {path}")
    LEASE_ROOT.mkdir(parents=True, exist_ok=True)
    lease_path = LEASE_ROOT / f"physical_gpu_{args.physical_index}.lock"
    lease_handle = lease_path.open("a+")
    try:
        fcntl.flock(lease_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        lease_handle.close()
        raise RuntimeError("selected GPU already has a production micro-gate lease") from exc
    started = time.time()
    child = None
    cache = Path(manifest["cache_directory"]) / args.job_id
    cleanup_errors = []
    timed_out = False
    interrupted = None
    pre = None
    launch = None
    post = None
    exit_code = None
    try:
        pre = nvidia_snapshot()
        selected_pre = selected(pre, args.physical_index, args.expected_uuid)
        if not idle(selected_pre):
            raise RuntimeError("selected GPU is not independently fresh-idle")
        start_receipt = {
            "schema_version": "cmf_production_micro_gate_guard_start_v1",
            "run_id": manifest["run_id"],
            "job_id": args.job_id,
            "family": job["family"],
            "manifest_sha256": manifest["manifest_sha256"],
            "physical_gpu_index": args.physical_index,
            "gpu_uuid": args.expected_uuid,
            "guard_pid": os.getpid(),
            "pre_snapshot": pre,
            "lease_path": str(lease_path),
        }
        start_receipt["receipt_sha256"] = canonical_hash(start_receipt)
        write_new(start_path, start_receipt)
        if cache.exists():
            raise FileExistsError("job cache must be new")
        cache.mkdir(parents=True, exist_ok=False)
        environment = child_environment(
            args.expected_uuid, args.physical_index, cache
        )
        launch = nvidia_snapshot()
        if not idle(selected(launch, args.physical_index, args.expected_uuid)):
            raise RuntimeError("GPU stopped being idle immediately before child launch")
        command = [
            str(ENV_PYTHON),
            str(runner),
            "--manifest",
            str(args.manifest.resolve()),
            "--job-id",
            args.job_id,
        ]
        stdout_file = stdout_path.open("xb")
        stderr_file = stderr_path.open("xb")
        try:
            child = subprocess.Popen(
                command,
                cwd=str(PROJECT),
                env=environment,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
            )
            try:
                exit_code = child.wait(timeout=int(job["timeout_seconds"]))
            except subprocess.TimeoutExpired:
                timed_out = True
                cleanup_errors.extend(terminate_group(child))
                exit_code = 124
            except KeyboardInterrupt:
                interrupted = "KeyboardInterrupt"
                cleanup_errors.extend(terminate_group(child))
                exit_code = 130
        finally:
            stdout_file.close()
            stderr_file.close()
        cleanup_errors.extend(terminate_group(child))
    except BaseException as exc:
        cleanup_errors.append({"type": type(exc).__name__, "message": str(exc)})
        if child is not None:
            cleanup_errors.extend(terminate_group(child))
        if exit_code is None:
            exit_code = 96
    finally:
        try:
            post = nvidia_snapshot()
        except BaseException as exc:
            cleanup_errors.append({"post_snapshot_error": type(exc).__name__, "message": str(exc)})
        cache_removed = True
        if cache.exists():
            try:
                shutil.rmtree(cache)
            except BaseException as exc:
                cache_removed = False
                cleanup_errors.append({"cache_cleanup_error": type(exc).__name__, "message": str(exc)})
        try:
            fcntl.flock(lease_handle.fileno(), fcntl.LOCK_UN)
            lease_released = True
        except BaseException as exc:
            lease_released = False
            cleanup_errors.append({"lease_release_error": type(exc).__name__, "message": str(exc)})
        lease_handle.close()
    post_selected = None
    returned = False
    if pre is not None and post is not None:
        post_selected = selected(post, args.physical_index, args.expected_uuid)
        pre_selected = selected(pre, args.physical_index, args.expected_uuid)
        returned = bool(
            post_selected["memory_used_mib"] <= max(64, pre_selected["memory_used_mib"] + 32)
            and post_selected["utilization_gpu_percent"] == 0
            and not post_selected["compute_processes"]
        )
    terminal = {
        "schema_version": "cmf_production_micro_gate_guard_terminal_v1",
        "run_id": manifest["run_id"],
        "job_id": args.job_id,
        "family": job["family"],
        "manifest_sha256": manifest["manifest_sha256"],
        "physical_gpu_index": args.physical_index,
        "gpu_uuid": args.expected_uuid,
        "guard_pid": os.getpid(),
        "child_pid": child.pid if child is not None else None,
        "child_process_group": child.pid if child is not None else None,
        "child_exit_code": exit_code,
        "timed_out": timed_out,
        "interrupted": interrupted,
        "pre_snapshot": pre,
        "launch_snapshot": launch,
        "post_snapshot": post,
        "cache_removed": cache_removed,
        "lease_released": lease_released,
        "cleanup_errors": cleanup_errors,
        "gpu_returned_to_idle_baseline": returned,
        "task_owned_cleanup_pass": not cleanup_errors and cache_removed and lease_released and returned,
        "output_exists": output.exists(),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "elapsed_seconds": time.time() - started,
    }
    terminal["status"] = (
        "completed"
        if exit_code == 0 and terminal["task_owned_cleanup_pass"]
        else "failed_or_blocked_with_cleanup_evidence"
    )
    terminal["receipt_sha256"] = canonical_hash(terminal)
    write_new(terminal_path, terminal)
    return 0 if terminal["status"] == "completed" else int(exit_code or 1)


if __name__ == "__main__":
    raise SystemExit(main())
