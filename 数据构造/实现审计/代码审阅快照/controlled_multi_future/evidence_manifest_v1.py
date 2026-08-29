"""Byte-level immutable evidence manifests for nonformal runtime namespaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


SCHEMA_VERSION = "cmf_immutable_evidence_file_manifest_v1"
WORKSPACE_ROOT = Path("/nfs_share/lijunhui")


def _require_workspace(path: Path, label: str) -> Path:
    path = Path(path).resolve()
    if not str(path).startswith(str(WORKSPACE_ROOT) + "/"):
        raise ValueError(f"{label} must remain in the workspace")
    return path


def build_evidence_manifest(namespace_dir: Path) -> dict:
    root = _require_workspace(namespace_dir, "evidence namespace")
    if not root.is_dir():
        raise ValueError("evidence namespace is missing")
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.is_symlink():
            raise ValueError("evidence manifest refuses symlinked files")
        data = path.read_bytes()
        files.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "bytes": len(data),
                "file_sha256": hashlib.sha256(data).hexdigest(),
                "format": path.suffix.lstrip(".") or "none",
            }
        )
    if not files:
        raise ValueError("evidence namespace has no files")
    tree_sha256 = hashlib.sha256(
        json.dumps(
            files, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "namespace": root.name,
        "namespace_path": str(root),
        "formal_data": False,
        "stage0_data": False,
        "file_count": len(files),
        "files": files,
        "tree_sha256": tree_sha256,
    }


def write_evidence_manifest(namespace_dir: Path, output_path: Path) -> dict:
    output = _require_workspace(output_path, "evidence manifest output")
    value = build_evidence_manifest(namespace_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = write_evidence_manifest(args.namespace, args.output)
    print(json.dumps({"file_count": value["file_count"], "tree_sha256": value["tree_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
