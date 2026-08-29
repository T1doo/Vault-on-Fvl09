"""Independent post-setup activity instrumentation for the A0 smoke gate.

The monitor is installed only after ``setup_demo`` and the canonical 60-step
settle have completed.  It therefore proves a deliberately narrow statement:
no planner query, controlled command, or physics step occurred while A0
captured the current and physical anchor.  It never treats an absent dense
trace as evidence of zero activity.

All instrumentation is additive and instance-local.  No tracked RoboTwin file
or class is patched globally.  Importing this module has no SAPIEN/CUDA side
effects.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import time
from typing import Any, Mapping, Sequence


ACTIVITY_SCHEMA_VERSION = "cmf_a0_activity_audit_v2"
SOURCE_COMMIT = "c3ddfa8b97d5519efa828b075999bd0006778e5e"


class ActivityMonitorError(RuntimeError):
    """Base class for fail-closed instrumentation errors."""

    def __init__(self, message: str, *, receipt: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.receipt = dict(receipt) if isinstance(receipt, Mapping) else None


class ActivityMonitorInstallationError(ActivityMonitorError):
    """Required instance-local wrappers could not be installed."""


class ActivityMonitorRestorationError(ActivityMonitorError):
    """One or more wrappers could not be restored."""


class ActivityMonitorBoundaryError(ActivityMonitorError):
    """The monitored window was started/stopped out of order."""


OFFICIAL_SOURCE_HASHES = {
    "envs/_base_task.py": "448f7152b65cb9102217cf5463aa821d72810ca56f63d5a797ec7bd43e23e101",
    "envs/robot/robot.py": "3dcd80acc8cab489a4c5edb507cc460dab1724be0226b8d5c4c1b218dee605cb",
    "envs/robot/planner.py": "f1012345542483f4cfbac64880a266b7ee0d4a64362d5ec6fd6985ed9c34b564",
    "envs/camera/camera.py": "e4d17e99c8a68f44a12bef248a2164f52206efeaf24168172b778cc1e32832dd",
}


def _entries(owner: str, names: Sequence[str], category: str, source_file: str) -> list[dict]:
    return [
        {
            "owner": owner,
            "attribute": name,
            "category": category,
            "required": True,
            "source_file": source_file,
            "source_commit": SOURCE_COMMIT,
            "source_file_sha256": OFFICIAL_SOURCE_HASHES[source_file],
        }
        for name in names
    ]


def _additive_entries(owner: str, names: Sequence[str], category: str, source_file: str, source_hash: str) -> list[dict]:
    return [
        {
            "owner": owner,
            "attribute": name,
            "category": category,
            "required": True,
            "source_file": source_file,
            "source_commit": "controlled_multi_future_runtime_v3_1_additive",
            "source_file_sha256": source_hash,
        }
        for name in names
    ]


# This registry is derived from the fixed official call graph.  High-level
# wrappers and leaf drive/planner APIs are both instrumented.  Nested calls may
# increment several per-entry counters; A0 only accepts an all-zero window.
A0_POST_SETUP_ENTRY_POINT_REGISTRY_V2 = tuple(
    _entries(
        "task",
        (
            "delay",
            "set_gripper",
            "together_close_gripper",
            "together_open_gripper",
            "left_move_to_pose",
            "right_move_to_pose",
            "together_move_to_pose",
            "move",
            "grasp_actor",
            "place_actor",
            "move_by_displacement",
            "move_to_pose",
            "close_gripper",
            "open_gripper",
            "back_to_origin",
            "take_dense_action",
            "take_action",
        ),
        "controlled_action",
        "envs/_base_task.py",
    )
    + _additive_entries(
        "task",
        ("_reserve_planner_query",),
        "planner_wrapper",
        "controlled_multi_future/probes/runtime_trace.py",
        "37c0a5da686cd08e26c0d737676b771b5a4899a935418eb7052f0f922ca571df",
    )
    + _entries(
        "task",
        ("_update_render",),
        "renderer_update",
        "envs/_base_task.py",
    )
    + _entries(
        "robot",
        (
            "left_plan_grippers",
            "right_plan_grippers",
            "left_plan_multi_path",
            "right_plan_multi_path",
            "left_plan_path",
            "right_plan_path",
        ),
        "planner_query",
        "envs/robot/robot.py",
    )
    + _entries(
        "robot",
        ("set_arm_joints", "set_gripper", "move_to_homestate"),
        "controlled_action",
        "envs/robot/robot.py",
    )
    + _entries(
        "robot",
        ("set_planner", "update_world_pcd"),
        "planner_wrapper",
        "envs/robot/robot.py",
    )
    + _entries(
        "cameras",
        ("update_picture",),
        "renderer_update",
        "envs/camera/camera.py",
    )
)


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def activity_entry_point_registry_artifact() -> dict:
    payload = {
        "schema_version": "cmf_a0_post_setup_entry_point_registry_v2",
        "source_commit": SOURCE_COMMIT,
        "monitor_scope": "post_setup_canonical_settle_complete_to_a0_capture_complete",
        "entries": [dict(item) for item in A0_POST_SETUP_ENTRY_POINT_REGISTRY_V2],
        "physics_step_instrumentation": {
            "owner": "task.scene",
            "attribute": "step",
            "mechanism": "instance-local forwarding proxy",
            "required": True,
        },
        "trace_is_authoritative_for_zero_action": False,
    }
    payload["registry_sha256"] = canonical_json_sha256(payload)
    return payload


class _SceneStepProxy:
    """Forward every scene API except ``step``, which is counted."""

    def __init__(self, wrapped: Any, monitor: "A0PostSetupActivityMonitorV2"):
        object.__setattr__(self, "_wrapped", wrapped)
        object.__setattr__(self, "_monitor", monitor)

    def step(self, *args, **kwargs):
        self._monitor._record_call("task.scene.step", "physics_step")
        return self._wrapped.step(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._wrapped, name)

    def __setattr__(self, name, value):
        setattr(self._wrapped, name, value)


@dataclass
class _InstalledWrapper:
    owner: Any
    owner_name: str
    attribute: str
    original_bound: Any
    had_instance_attribute: bool
    original_instance_value: Any


def _mapping_or_none(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


class A0PostSetupActivityMonitorV2:
    """Install, stop, and restore one scene-bound monitored window."""

    def __init__(
        self,
        task: Any,
        *,
        scene_instance_id: str,
        phase: str,
        setup_activity: Mapping[str, Any],
        registry: Sequence[Mapping[str, Any]] = A0_POST_SETUP_ENTRY_POINT_REGISTRY_V2,
    ):
        if not isinstance(scene_instance_id, str) or not scene_instance_id:
            raise ValueError("scene_instance_id must be non-empty")
        if not isinstance(phase, str) or not phase:
            raise ValueError("phase must be non-empty")
        self.task = task
        self.scene_instance_id = scene_instance_id
        self.phase = phase
        self.setup_activity = dict(setup_activity)
        self.registry = tuple(dict(item) for item in registry)
        self.started = False
        self.stopped = False
        self._installed: list[_InstalledWrapper] = []
        self._wrapped_entry_ids: list[str] = []
        self._original_scene = None
        self._scene_proxy_installed = False
        self._counts: dict[str, int] = {}
        self._per_entry_counts: dict[str, int] = {}
        self._planner_records: list[dict] = []
        self._controlled_records: list[dict] = []
        self._missing_expected: list[str] = []
        self._installation_errors: list[dict] = []
        self._restoration_errors: list[dict] = []
        self._monitor_start_time = None
        self._monitor_end_time = None
        self._start_native = None
        self._end_native = None
        self.last_receipt: dict | None = None

    @staticmethod
    def _native_counters(task: Any) -> dict:
        trace = getattr(task, "trace", None)
        planner_queries = getattr(task, "planner_queries", None)
        return {
            "take_action_count": int(getattr(task, "take_action_cnt", 0))
            if hasattr(task, "take_action_cnt")
            else None,
            "trace_available": isinstance(trace, (list, tuple)),
            "trace_rows": len(trace) if isinstance(trace, (list, tuple)) else None,
            "native_planner_query_count": int(getattr(task, "planner_query_count", 0))
            if hasattr(task, "planner_query_count")
            else None,
            "native_planner_record_count": len(planner_queries)
            if isinstance(planner_queries, (list, tuple))
            else None,
        }

    def _owner_for(self, owner_name: str) -> Any:
        if owner_name == "task":
            return self.task
        if owner_name == "robot":
            return getattr(self.task, "robot", None)
        if owner_name == "cameras":
            return getattr(self.task, "cameras", None)
        raise ValueError(f"unknown instrumentation owner {owner_name}")

    def _record_call(self, entry_id: str, category: str) -> None:
        if not self.started or self.stopped:
            return
        self._counts[category] = self._counts.get(category, 0) + 1
        self._per_entry_counts[entry_id] = self._per_entry_counts.get(entry_id, 0) + 1
        record = {
            "entry_point": entry_id,
            "category": category,
            "ordinal": self._per_entry_counts[entry_id],
            "monotonic_time": time.monotonic(),
        }
        if category == "planner_query":
            self._planner_records.append(record)
        elif category == "controlled_action":
            self._controlled_records.append(record)

    def _install_method(self, owner: Any, owner_name: str, attribute: str, category: str) -> None:
        entry_id = f"{owner_name}.{attribute}"
        original = getattr(owner, attribute)
        instance_dict = getattr(owner, "__dict__", None)
        had_instance = isinstance(instance_dict, dict) and attribute in instance_dict
        original_instance = instance_dict.get(attribute) if had_instance else None

        def wrapped(*args, **kwargs):
            self._record_call(entry_id, category)
            return original(*args, **kwargs)

        setattr(owner, attribute, wrapped)
        if getattr(owner, attribute) is not wrapped:
            raise RuntimeError(f"wrapper assignment did not bind {entry_id}")
        self._installed.append(
            _InstalledWrapper(
                owner=owner,
                owner_name=owner_name,
                attribute=attribute,
                original_bound=original,
                had_instance_attribute=had_instance,
                original_instance_value=original_instance,
            )
        )
        self._wrapped_entry_ids.append(entry_id)

    def _install_scene_proxy(self) -> None:
        if not hasattr(self.task, "scene") or not callable(getattr(self.task.scene, "step", None)):
            raise RuntimeError("task.scene.step is missing")
        self._original_scene = self.task.scene
        self.task.scene = _SceneStepProxy(self._original_scene, self)
        if not isinstance(self.task.scene, _SceneStepProxy):
            raise RuntimeError("task.scene step proxy installation failed")
        self._scene_proxy_installed = True

    def start(self) -> None:
        if self.started or self.stopped:
            raise ActivityMonitorBoundaryError("A0 monitor may start exactly once")
        self._counts = {
            "planner_query": 0,
            "planner_wrapper": 0,
            "controlled_action": 0,
            "physics_step": 0,
            "renderer_update": 0,
        }
        self._start_native = self._native_counters(self.task)
        try:
            for entry in self.registry:
                owner_name = entry["owner"]
                attribute = entry["attribute"]
                owner = self._owner_for(owner_name)
                entry_id = f"{owner_name}.{attribute}"
                if owner is None or not callable(getattr(owner, attribute, None)):
                    if entry.get("required") is True:
                        self._missing_expected.append(entry_id)
                    continue
                self._install_method(owner, owner_name, attribute, entry["category"])
            if self._missing_expected:
                raise RuntimeError(f"missing expected entry points: {self._missing_expected}")
            self._install_scene_proxy()
        except BaseException as exc:
            self._installation_errors.append({"type": type(exc).__name__, "message": str(exc)})
            self._restore_all()
            receipt = self._build_receipt(installation_pass=False, restoration_pass=not self._restoration_errors)
            self.last_receipt = receipt
            raise ActivityMonitorInstallationError(str(exc), receipt=receipt) from exc
        self.started = True
        self._monitor_start_time = time.monotonic()

    def _restore_all(self) -> None:
        if self._scene_proxy_installed:
            try:
                self.task.scene = self._original_scene
            except BaseException as exc:
                self._restoration_errors.append(
                    {"entry_point": "task.scene.step", "type": type(exc).__name__, "message": str(exc)}
                )
            else:
                self._scene_proxy_installed = False
        failed_wrappers: list[_InstalledWrapper] = []
        for item in reversed(self._installed):
            entry_id = f"{item.owner_name}.{item.attribute}"
            try:
                if item.had_instance_attribute:
                    setattr(item.owner, item.attribute, item.original_instance_value)
                else:
                    delattr(item.owner, item.attribute)
                restored = getattr(item.owner, item.attribute)
                if item.had_instance_attribute:
                    if restored is not item.original_instance_value:
                        raise RuntimeError("original instance attribute identity was not restored")
                elif getattr(restored, "__func__", restored) is not getattr(item.original_bound, "__func__", item.original_bound):
                    raise RuntimeError("class descriptor was not restored")
            except BaseException as exc:
                failed_wrappers.append(item)
                self._restoration_errors.append(
                    {"entry_point": entry_id, "type": type(exc).__name__, "message": str(exc)}
                )
        self._installed = list(reversed(failed_wrappers))

    @staticmethod
    def _delta(start: Mapping[str, Any], end: Mapping[str, Any], key: str) -> int | None:
        left, right = start.get(key), end.get(key)
        if left is None or right is None:
            return None
        return int(right) - int(left)

    def _build_receipt(self, *, installation_pass: bool, restoration_pass: bool) -> dict:
        start_native = self._start_native or self._native_counters(self.task)
        end_native = self._end_native or self._native_counters(self.task)
        trace_delta = self._delta(start_native, end_native, "trace_rows")
        payload = {
            "schema_version": ACTIVITY_SCHEMA_VERSION,
            "scene_instance_id": self.scene_instance_id,
            "phase": self.phase,
            "monitor_boundary": {
                "monitor_started": self.started,
                "monitor_stopped": self.stopped,
                "monitor_start_step": 0 if self.started else None,
                "monitor_end_step": int(self._counts.get("physics_step", 0)) if self.stopped else None,
                "monitor_start_monotonic_time": self._monitor_start_time,
                "monitor_end_monotonic_time": self._monitor_end_time,
            },
            "setup_activity": dict(self.setup_activity),
            "post_setup_activity": {
                "planner_query_delta": int(self._counts.get("planner_query", 0)),
                "planner_query_record_delta": len(self._planner_records),
                "controlled_action_delta": int(self._counts.get("controlled_action", 0)),
                "instrumented_control_call_delta": int(self._counts.get("controlled_action", 0)),
                "instrumented_planner_wrapper_delta": int(self._counts.get("planner_wrapper", 0)),
                "take_action_count_delta": self._delta(start_native, end_native, "take_action_count"),
                "trace_row_delta": trace_delta,
                "trace_counter_available": bool(start_native.get("trace_available") and end_native.get("trace_available")),
                "physics_step_delta": int(self._counts.get("physics_step", 0)),
                "renderer_update_delta": int(self._counts.get("renderer_update", 0)),
                "native_planner_query_count_delta_if_available": self._delta(
                    start_native, end_native, "native_planner_query_count"
                ),
                "native_planner_record_delta_if_available": self._delta(
                    start_native, end_native, "native_planner_record_count"
                ),
            },
            "instrumentation": {
                "entry_point_registry_schema": "cmf_a0_post_setup_entry_point_registry_v2",
                "entry_point_registry_sha256": activity_entry_point_registry_artifact()["registry_sha256"],
                "wrapped_entry_points": sorted(self._wrapped_entry_ids),
                "all_registry_entry_points": sorted(
                    f"{item['owner']}.{item['attribute']}" for item in self.registry
                ),
                "missing_expected_entry_points": sorted(self._missing_expected),
                "wrapper_installation_pass": bool(installation_pass),
                "wrapper_restoration_pass": bool(restoration_pass),
                "installation_errors": list(self._installation_errors),
                "restoration_errors": list(self._restoration_errors),
                "per_entry_call_counts": dict(sorted(self._per_entry_counts.items())),
                "planner_query_records": list(self._planner_records),
                "controlled_action_records": list(self._controlled_records),
                "counter_sources": {
                    "planner_query_delta": "independent leaf planner entry-point wrappers",
                    "planner_query_record_delta": "independent monitor planner record ledger",
                    "controlled_action_delta": "independent task/robot control entry-point wrappers",
                    "take_action_count_delta": "RoboTwin Base_Task.take_action_cnt when available",
                    "trace_row_delta": "dense trace only when initialized; never used as zero-action proof",
                    "physics_step_delta": "instance-local task.scene.step forwarding proxy",
                    "renderer_update_delta": "task/camera renderer-only wrappers",
                    "native_planner_query_count_delta_if_available": (
                        "RoboTwin RuntimeTraceMixin.planner_query_count when available"
                    ),
                    "native_planner_record_delta_if_available": (
                        "RoboTwin RuntimeTraceMixin.planner_queries length when available"
                    ),
                },
            },
            "limits": {
                "planner_query_limit": 0,
                "controlled_action_limit": 0,
                "physics_step_limit": 0,
            },
        }
        payload["activity_receipt_sha256"] = canonical_json_sha256(payload)
        return payload

    def stop(self) -> dict:
        if not self.started or self.stopped:
            raise ActivityMonitorBoundaryError("A0 monitor must be active before it can stop")
        self._monitor_end_time = time.monotonic()
        self._end_native = self._native_counters(self.task)
        self.stopped = True
        self._restore_all()
        receipt = self._build_receipt(
            installation_pass=not self._installation_errors and not self._missing_expected,
            restoration_pass=not self._restoration_errors,
        )
        self.last_receipt = receipt
        if self._restoration_errors:
            raise ActivityMonitorRestorationError(
                "one or more A0 instrumentation wrappers were not restored",
                receipt=receipt,
            )
        return receipt

    def ensure_restored(self) -> dict | None:
        """Best-effort cleanup retry; an earlier failure remains a terminal failure."""

        if self._scene_proxy_installed or self._installed:
            self._restore_all()
        return self.last_receipt


def validate_activity_receipt_v2(
    value: Mapping[str, Any],
    *,
    expected_scene_instance_id: str,
    expected_phase: str,
) -> dict:
    """Validate schema, binding, monitor boundaries, and the zero-activity Gate."""

    if not isinstance(value, Mapping):
        raise ActivityMonitorError("A0 activity receipt is missing")
    receipt = dict(value)
    if receipt.get("schema_version") != ACTIVITY_SCHEMA_VERSION:
        raise ActivityMonitorError("A0 activity receipt uses the wrong schema")
    if receipt.get("scene_instance_id") != expected_scene_instance_id:
        raise ActivityMonitorError("A0 activity receipt is bound to a different scene")
    if receipt.get("phase") != expected_phase:
        raise ActivityMonitorError("A0 activity receipt is bound to a different phase")
    sealed = dict(receipt)
    expected_hash = sealed.pop("activity_receipt_sha256", None)
    if not isinstance(expected_hash, str) or canonical_json_sha256(sealed) != expected_hash:
        raise ActivityMonitorError("A0 activity receipt hash mismatch")
    boundary = _mapping_or_none(receipt.get("monitor_boundary"))
    setup = _mapping_or_none(receipt.get("setup_activity"))
    post = _mapping_or_none(receipt.get("post_setup_activity"))
    instrumentation = _mapping_or_none(receipt.get("instrumentation"))
    limits = _mapping_or_none(receipt.get("limits"))
    if None in (boundary, setup, post, instrumentation, limits):
        raise ActivityMonitorError("A0 activity receipt is missing structured sections")
    if boundary.get("monitor_started") is not True or boundary.get("monitor_stopped") is not True:
        raise ActivityMonitorBoundaryError("A0 monitor boundary is incomplete", receipt=receipt)
    for key in ("monitor_start_step", "monitor_end_step", "monitor_start_monotonic_time", "monitor_end_monotonic_time"):
        if boundary.get(key) is None:
            raise ActivityMonitorBoundaryError(f"A0 monitor boundary missing {key}", receipt=receipt)
    if float(boundary["monitor_end_monotonic_time"]) < float(boundary["monitor_start_monotonic_time"]):
        raise ActivityMonitorBoundaryError("A0 monitor monotonic interval is negative", receipt=receipt)
    if setup.get("setup_demo_completed") is not True:
        raise ActivityMonitorError("A0 setup_demo completion is not proven", receipt=receipt)
    if not isinstance(setup.get("setup_activity_source"), str) or not setup["setup_activity_source"]:
        raise ActivityMonitorError("A0 setup activity source is missing", receipt=receipt)
    if setup.get("canonical_settle_is_control_action") is not False:
        raise ActivityMonitorError("canonical settle must not be classified as controlled action", receipt=receipt)
    if int(setup.get("canonical_settle_steps", -1)) != 60:
        raise ActivityMonitorError("A0 canonical settle must contain exactly 60 steps", receipt=receipt)
    if float(setup.get("simulator_timestep_seconds", -1)) != 0.004:
        raise ActivityMonitorError("A0 simulator timestep must equal 0.004 seconds", receipt=receipt)
    if int(setup.get("control_steps_per_action", -1)) != 1:
        raise ActivityMonitorError("A0 control_steps_per_action must equal one", receipt=receipt)
    if abs(float(setup.get("effective_action_interval_seconds", -1)) - 0.004) > 1e-12:
        raise ActivityMonitorError("A0 effective action interval must equal 0.004 seconds", receipt=receipt)
    if instrumentation.get("wrapper_installation_pass") is not True:
        raise ActivityMonitorInstallationError("A0 wrapper installation failed", receipt=receipt)
    if instrumentation.get("wrapper_restoration_pass") is not True:
        raise ActivityMonitorRestorationError("A0 wrapper restoration failed", receipt=receipt)
    if instrumentation.get("missing_expected_entry_points") != []:
        raise ActivityMonitorInstallationError("A0 entry-point coverage is incomplete", receipt=receipt)
    wrapped = instrumentation.get("wrapped_entry_points")
    registered = instrumentation.get("all_registry_entry_points")
    expected_entries = sorted(
        f"{item['owner']}.{item['attribute']}" for item in A0_POST_SETUP_ENTRY_POINT_REGISTRY_V2
    )
    if (
        not isinstance(wrapped, list)
        or not wrapped
        or sorted(wrapped) != expected_entries
        or sorted(registered or []) != expected_entries
    ):
        raise ActivityMonitorInstallationError("A0 wrapped entry-point set is incomplete", receipt=receipt)
    if instrumentation.get("entry_point_registry_sha256") != activity_entry_point_registry_artifact()["registry_sha256"]:
        raise ActivityMonitorInstallationError("A0 entry-point registry hash mismatch", receipt=receipt)
    if not isinstance(instrumentation.get("counter_sources"), Mapping):
        raise ActivityMonitorError("A0 counter source registry is missing", receipt=receipt)
    if limits != {
        "planner_query_limit": 0,
        "controlled_action_limit": 0,
        "physics_step_limit": 0,
    }:
        raise ActivityMonitorError("A0 activity limits are not the frozen zero limits", receipt=receipt)
    required_zero = (
        "planner_query_delta",
        "planner_query_record_delta",
        "controlled_action_delta",
        "instrumented_control_call_delta",
        "instrumented_planner_wrapper_delta",
        "take_action_count_delta",
        "physics_step_delta",
    )
    for key in required_zero:
        if post.get(key) != 0:
            raise ActivityMonitorError(f"A0 post-setup activity is nonzero: {key}={post.get(key)}", receipt=receipt)
    native_query_delta = post.get("native_planner_query_count_delta_if_available")
    native_record_delta = post.get("native_planner_record_delta_if_available")
    native_required = setup.get("native_planner_counters_required") is True
    if native_required and (native_query_delta is None or native_record_delta is None):
        raise ActivityMonitorError(
            "A0 real adapter requires both native planner counters",
            receipt=receipt,
        )
    if (native_query_delta is None) != (native_record_delta is None):
        raise ActivityMonitorError(
            "A0 native planner query/record counter availability differs",
            receipt=receipt,
        )
    if native_query_delta is not None:
        if native_query_delta != 0:
            raise ActivityMonitorError(
                f"A0 native planner query delta is nonzero: {native_query_delta}",
                receipt=receipt,
            )
        if native_record_delta != 0:
            raise ActivityMonitorError(
                f"A0 native planner record delta is nonzero: {native_record_delta}",
                receipt=receipt,
            )
        if native_query_delta != native_record_delta:
            raise ActivityMonitorError(
                "A0 native planner query/record deltas disagree",
                receipt=receipt,
            )
    trace_delta = post.get("trace_row_delta")
    if trace_delta is not None and trace_delta != 0:
        raise ActivityMonitorError("A0 dense trace changed during the monitored window", receipt=receipt)
    if boundary.get("monitor_end_step") != post.get("physics_step_delta"):
        raise ActivityMonitorBoundaryError("A0 monitor step boundary disagrees with physics delta", receipt=receipt)
    if not isinstance(post.get("renderer_update_delta"), int) or post["renderer_update_delta"] < 0:
        raise ActivityMonitorError("A0 renderer update delta is invalid", receipt=receipt)
    return receipt
