"""Shared fail-closed SAPIEN scene lifecycle for nonformal probes."""

from __future__ import annotations

from contextlib import contextmanager
import traceback


def initialize_cleanup_fields(receipt: dict) -> None:
    receipt.update({
        "scene_created": False,
        "scene_cleanup_attempted": False,
        "scene_cleanup_succeeded": False,
        "cleanup_error": None,
        "partial_output_status": "none",
        "gpu_postcheck": "pending_external_postcheck",
        "orphan_process_count": None,
        "scene_cleanup_records": [],
    })


@contextmanager
def managed_scene(scene_cls, setup_kwargs: dict, receipt: dict, label: str):
    scene = None
    record = {
        "label": label,
        "scene_created": False,
        "scene_setup_succeeded": False,
        "scene_cleanup_attempted": False,
        "scene_cleanup_succeeded": False,
        "cleanup_error": None,
    }
    receipt.setdefault("scene_cleanup_records", []).append(record)
    try:
        scene = scene_cls()
        record["scene_created"] = True
        receipt["scene_created"] = True
        scene.setup_demo(**setup_kwargs)
        record["scene_setup_succeeded"] = True
        yield scene
    finally:
        if scene is not None:
            record["scene_cleanup_attempted"] = True
            receipt["scene_cleanup_attempted"] = True
            try:
                scene.close_env(clear_cache=True)
                record["scene_cleanup_succeeded"] = True
            except BaseException as exc:
                record["cleanup_error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
        records = receipt["scene_cleanup_records"]
        created = [item for item in records if item["scene_created"]]
        receipt["scene_cleanup_succeeded"] = bool(created) and all(item["scene_cleanup_succeeded"] for item in created)
        errors = [item["cleanup_error"] for item in records if item["cleanup_error"] is not None]
        receipt["cleanup_error"] = errors or None


def cleanup_status(receipt: dict, requested_status: str) -> str:
    if receipt.get("scene_created") and not receipt.get("scene_cleanup_succeeded"):
        return "failed_cleanup_uncertain"
    return requested_status
