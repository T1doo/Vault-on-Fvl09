"""Launch-time source/environment lock for nonformal CMF GPU scopes.

The lock is captured and revalidated before an authorization is consumed.  It
reads files and package metadata only; importing this module does not import
SAPIEN, Torch, CuRobo, or initialize CUDA.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence


SOURCE_LOCK_SCHEMA_VERSION = "cmf_runtime_source_lock_v1"
SOURCE_COMMIT = "c3ddfa8b97d5519efa828b075999bd0006778e5e"
WORKSPACE_ROOT = Path("/nfs_share/lijunhui")
DEFAULT_REPO_ROOT = WORKSPACE_ROOT / "Robotwin2/project/RoboTwin"
DEFAULT_ENVIRONMENT_ROOT = WORKSPACE_ROOT / "Robotwin2"

COMMON_CRITICAL_FILES = (
    "envs/_base_task.py",
    "envs/robot/robot.py",
    "envs/robot/planner.py",
    "envs/camera/camera.py",
    "envs/utils/create_actor.py",
)

FAMILY_ENV_FILES = {
    "F1": ("envs/blocks_ranking_rgb.py", "envs/place_cans_plasticbox.py"),
    "F2": (
        "envs/place_cans_plasticbox.py",
        "envs/place_object_scale.py",
        "envs/place_object_stand.py",
        "envs/move_can_pot.py",
    ),
    "F3": ("envs/shake_bottle.py", "envs/shake_bottle_horizontally.py", "envs/adjust_bottle.py"),
    "F4": ("envs/blocks_ranking_rgb.py", "envs/stack_blocks_three.py", "envs/place_burger_fries.py"),
}

FAMILY_ASSET_FILES = {
    "F1": (
        "assets/objects/062_plasticbox/model_data3.json",
        "assets/objects/062_plasticbox/points_info.json",
        "assets/objects/062_plasticbox/visual/base3.glb",
        "assets/objects/062_plasticbox/collision/base3.glb",
    ),
    "F2": (
        "assets/objects/071_can/model_data1.json",
        "assets/objects/071_can/visual/base1.glb",
        "assets/objects/071_can/collision/base1.glb",
        "assets/objects/062_plasticbox/model_data2.json",
        "assets/objects/062_plasticbox/visual/base2.glb",
        "assets/objects/062_plasticbox/collision/base2.glb",
        "assets/objects/072_electronicscale/model_data0.json",
        "assets/objects/072_electronicscale/visual/base0.glb",
        "assets/objects/072_electronicscale/collision/base0.glb",
        "assets/objects/074_displaystand/model_data3.json",
        "assets/objects/074_displaystand/visual/base3.glb",
        "assets/objects/074_displaystand/collision/base3.glb",
        "assets/objects/060_kitchenpot/100015/model_data.json",
        "assets/objects/060_kitchenpot/100015/mobility.urdf",
        "assets/objects/060_kitchenpot/points_info.json",
        "assets/objects/060_kitchenpot/visual/base0.glb",
    ),
    "F3": (
        "assets/objects/001_bottle/model_data13.json",
        "assets/objects/001_bottle/points_info.json",
        "assets/objects/001_bottle/visual/base13.glb",
        "assets/objects/001_bottle/collision/base13.glb",
    ),
    "F4": (
        "assets/objects/008_tray/model_data0.json",
        "assets/objects/008_tray/points_info.json",
        "assets/objects/008_tray/visual/base0.glb",
        "assets/objects/008_tray/collision/base0.glb",
    ),
}

CONFIG_FILES = (
    "task_config/_camera_config.yml",
    "task_config/_config_template.yml",
    "task_config/_embodiment_config.yml",
    "task_config/_eval_step_limit.yml",
)


class SourceLockError(RuntimeError):
    failure_status = "failed_runtime_source_lock"


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_files(root: Path, relatives: Sequence[str], label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    missing: list[str] = []
    for relative in relatives:
        path = root / relative
        if not path.is_file():
            missing.append(relative)
        else:
            result[relative] = _sha256_file(path)
    if missing:
        raise SourceLockError(f"missing {label} files: {missing}")
    return result


def _hash_python_tree(root: Path) -> str:
    if not root.is_dir():
        raise SourceLockError(f"implementation source tree missing: {root}")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _hash_tree(root: Path) -> str:
    if not root.is_dir():
        raise SourceLockError(f"dependency source tree missing: {root}")
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file() and "__pycache__" not in item.parts):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def _distribution_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _nvcc_version(environment_root: Path) -> str | None:
    nvcc = environment_root / "tools/cuda-12.1/bin/nvcc"
    if not nvcc.is_file():
        return None
    completed = subprocess.run(
        [str(nvcc), "--version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip().splitlines()[-1]


def build_runtime_source_lock_snapshot(
    *,
    family: str,
    repo_root: Path = DEFAULT_REPO_ROOT,
    environment_root: Path = DEFAULT_ENVIRONMENT_ROOT,
) -> dict:
    if family not in FAMILY_ENV_FILES:
        raise SourceLockError(f"unsupported family for source lock: {family}")
    repo_root = Path(repo_root).resolve()
    environment_root = Path(environment_root).resolve()
    if not str(repo_root).startswith(str(WORKSPACE_ROOT) + "/"):
        raise SourceLockError("RoboTwin repo is outside the authorized workspace")
    if not str(environment_root).startswith(str(WORKSPACE_ROOT) + "/"):
        raise SourceLockError("environment root is outside the authorized workspace")

    official_commit = _git(repo_root, "rev-parse", "HEAD")
    tracked_status = _git(repo_root, "status", "--porcelain", "--untracked-files=no")
    official_files = tuple(COMMON_CRITICAL_FILES) + tuple(FAMILY_ENV_FILES[family])
    activation = environment_root / "config/activate_robotwin2.sh"
    curobo_source = repo_root / "envs/curobo"
    pytorch3d_repo = environment_root / "project/pytorch3d"
    dependencies = {
        "curobo_source_tree_sha256": _hash_tree(curobo_source),
        "curobo_source_path": str(curobo_source),
        "pytorch3d_repo_commit": _git(pytorch3d_repo, "rev-parse", "HEAD") if (pytorch3d_repo / ".git").is_dir() else None,
        "pytorch3d_tracked_worktree_clean": (
            _git(pytorch3d_repo, "status", "--porcelain", "--untracked-files=no") == ""
            if (pytorch3d_repo / ".git").is_dir()
            else None
        ),
    }
    snapshot = {
        "family": family,
        "repo_root": str(repo_root),
        "official_repo_commit": official_commit,
        "expected_official_repo_commit": SOURCE_COMMIT,
        "official_worktree_clean": tracked_status == "",
        "official_tracked_status": tracked_status,
        "critical_source_hashes": _hash_files(repo_root, official_files, "critical source"),
        "asset_hashes": _hash_files(repo_root, FAMILY_ASSET_FILES[family], "asset/model_data"),
        "config_hashes": _hash_files(repo_root, CONFIG_FILES, "task config"),
        "implementation_source_sha256": _hash_python_tree(repo_root / "controlled_multi_future"),
        "environment_lock": {
            "activation_script_path": str(activation),
            "activation_script_sha256": _sha256_file(activation),
            "python_executable": str(Path(sys.executable).resolve()),
            "python_version": sys.version,
            "cuda_nvcc_version": _nvcc_version(environment_root),
            "sapien_version": _distribution_version("sapien"),
            "torch_version": _distribution_version("torch"),
            "numpy_version": _distribution_version("numpy"),
            "curobo_distribution_version": _distribution_version("curobo"),
        },
        "dependency_locks": dependencies,
    }
    snapshot["source_lock_pass"] = bool(
        official_commit == SOURCE_COMMIT
        and snapshot["official_worktree_clean"]
        and all(snapshot["critical_source_hashes"].values())
        and all(snapshot["asset_hashes"].values())
        and all(snapshot["config_hashes"].values())
        and snapshot["implementation_source_sha256"]
        and snapshot["environment_lock"]["activation_script_sha256"]
        and snapshot["environment_lock"]["sapien_version"]
        and snapshot["environment_lock"]["torch_version"]
    )
    return snapshot


def capture_runtime_source_lock(
    *,
    family: str,
    repo_root: Path = DEFAULT_REPO_ROOT,
    environment_root: Path = DEFAULT_ENVIRONMENT_ROOT,
) -> dict:
    snapshot = build_runtime_source_lock_snapshot(
        family=family,
        repo_root=repo_root,
        environment_root=environment_root,
    )
    if not snapshot["source_lock_pass"]:
        raise SourceLockError("runtime source lock snapshot did not pass")
    receipt = {
        "schema_version": SOURCE_LOCK_SCHEMA_VERSION,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": snapshot,
    }
    receipt["source_lock_receipt_sha256"] = _canonical_sha256(receipt)
    return receipt


def validate_runtime_source_lock(
    value: Mapping[str, Any],
    *,
    expected_family: str,
    repo_root: Path = DEFAULT_REPO_ROOT,
    environment_root: Path = DEFAULT_ENVIRONMENT_ROOT,
) -> dict:
    if not isinstance(value, Mapping) or value.get("schema_version") != SOURCE_LOCK_SCHEMA_VERSION:
        raise SourceLockError("runtime source lock schema mismatch")
    receipt = json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))
    sealed = dict(receipt)
    expected_hash = sealed.pop("source_lock_receipt_sha256", None)
    if not isinstance(expected_hash, str) or _canonical_sha256(sealed) != expected_hash:
        raise SourceLockError("runtime source lock receipt hash mismatch")
    snapshot = receipt.get("snapshot")
    if not isinstance(snapshot, Mapping) or snapshot.get("family") != expected_family:
        raise SourceLockError("runtime source lock family mismatch")
    current = build_runtime_source_lock_snapshot(
        family=expected_family,
        repo_root=repo_root,
        environment_root=environment_root,
    )
    if dict(snapshot) != current:
        raise SourceLockError("runtime source/environment state changed after source lock capture")
    if current.get("source_lock_pass") is not True:
        raise SourceLockError("runtime source lock no longer passes")
    return receipt


def write_runtime_source_lock(path: Path, receipt: Mapping[str, Any]) -> None:
    path = Path(path)
    if not path.is_absolute() or not str(path).startswith(str(WORKSPACE_ROOT) + "/"):
        raise SourceLockError("source lock output must stay in the workspace")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(
            receipt,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        os.fchmod(fd, 0o600)
        handle.write(data)
        handle.flush()
        os.fsync(fd)


def load_runtime_source_lock(path: Path, *, expected_family: str) -> dict:
    path = Path(path)
    if not path.is_file():
        raise SourceLockError("runtime source lock receipt is missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceLockError("runtime source lock receipt is unreadable") from exc
    return validate_runtime_source_lock(value, expected_family=expected_family)
