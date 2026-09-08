"""Independent, lock-protected budget ledger for the v2 physical collection.

The historical ``ledger.py`` belongs to the old task and keeps its old caps.
This module deliberately takes a contract hash and cap set from the new P3
execution contract so a restart cannot inherit the old Goal or ledger.
"""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .canonical import canonical_sha256


COUNTERS = ("fresh_scenes", "action_scenes", "collection_attempts", "solver_problems", "gpu_lease_seconds")


class ExecutionLedgerError(ValueError):
    """Raised when a budget event is malformed or would be unsafe."""


def _counters(value: Mapping[str, Any] | None, *, label: str) -> dict[str, int]:
    value = value or {}
    result: dict[str, int] = {}
    for key in COUNTERS:
        item = value.get(key)
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise ExecutionLedgerError(f"{label}.{key} must be a non-negative integer")
        result[key] = item
    return result


class ExecutionLedgerV2:
    """Append-only ledger with NFS advisory locking and idempotent events."""

    def __init__(self, path: str | Path, *, contract_sha256: str, task_id: str, caps: Mapping[str, int], parent_contract_sha256: str | None = None, ancestor_contract_sha256s: list[str] | tuple[str, ...] | None = None):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.contract_sha256 = str(contract_sha256)
        self.task_id = str(task_id)
        self.caps = _counters(caps, label="caps")
        chain = [*(ancestor_contract_sha256s or ())]
        if parent_contract_sha256:
            chain.append(str(parent_contract_sha256))
        chain.append(self.contract_sha256)
        if len(chain) != len(set(chain)):
            raise ExecutionLedgerError("contract ancestry contains duplicate hashes")
        self.contract_chain = tuple(chain)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.touch(exist_ok=True)

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        last_contract_index = 0
        with self.path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ExecutionLedgerError(f"invalid JSON at line {line_number}") from exc
                expected_hash = canonical_sha256({key: value for key, value in event.items() if key != "event_sha256"})
                if event.get("event_sha256") != expected_hash:
                    raise ExecutionLedgerError(f"event hash mismatch at line {line_number}")
                if event.get("prev_event_sha256") != (events[-1].get("event_sha256") if events else None):
                    raise ExecutionLedgerError(f"event chain mismatch at line {line_number}")
                if event.get("task_id") != self.task_id or event.get("contract_sha256") not in self.contract_chain:
                    raise ExecutionLedgerError("event belongs to another task or contract")
                contract_index = self.contract_chain.index(event["contract_sha256"])
                if contract_index < last_contract_index:
                    raise ExecutionLedgerError("ancestor-contract event appears after a newer contract")
                if contract_index > last_contract_index:
                    if contract_index != last_contract_index + 1 or event.get("event_type") != "BUDGET_CAP_AMENDMENT":
                        raise ExecutionLedgerError("new contract requires a contiguous budget amendment event")
                    metadata = event.get("metadata", {})
                    if metadata.get("parent_contract_sha256") != self.contract_chain[contract_index - 1]:
                        raise ExecutionLedgerError("budget amendment parent contract mismatch")
                    last_contract_index = contract_index
                _counters(event.get("reserved_after"), label="reserved_after")
                _counters(event.get("consumed_after"), label="consumed_after")
                events.append(event)
        return events

    def events(self) -> list[dict[str, Any]]:
        with self.lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
            try:
                return self._read_unlocked()
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def totals(self) -> dict[str, dict[str, int]]:
        events = self.events()
        if not events:
            zero = {key: 0 for key in COUNTERS}
            return {"reserved": zero.copy(), "consumed": zero.copy()}
        return {"reserved": _counters(events[-1]["reserved_after"], label="reserved_after"), "consumed": _counters(events[-1]["consumed_after"], label="consumed_after")}

    def append(self, *, event_type: str, reserved_after: Mapping[str, int], consumed_after: Mapping[str, int], metadata: Mapping[str, Any] | None = None, idempotency_key: str | None = None) -> dict[str, Any]:
        if not isinstance(event_type, str) or not event_type:
            raise ExecutionLedgerError("event_type must be non-empty")
        reserved = _counters(reserved_after, label="reserved_after")
        consumed = _counters(consumed_after, label="consumed_after")
        with self.lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                events = self._read_unlocked()
                if idempotency_key:
                    for prior in events:
                        if prior.get("idempotency_key") == idempotency_key:
                            return prior
                if event_type != "BUDGET_OVERRUN" and any(reserved[key] + consumed[key] > self.caps[key] for key in COUNTERS):
                    raise ExecutionLedgerError("requested reservation or consumption exceeds contract cap")
                event: dict[str, Any] = {
                    "schema_version": "cmf_f2_f3_v2_execution_budget_event_v1",
                    "event_id": f"evt-{len(events) + 1:06d}",
                    "event_type": event_type,
                    "task_id": self.task_id,
                    "contract_sha256": self.contract_sha256,
                    "reserved_after": reserved,
                    "consumed_after": consumed,
                    "prev_event_sha256": events[-1].get("event_sha256") if events else None,
                    "metadata": dict(metadata or {}),
                }
                if idempotency_key:
                    event["idempotency_key"] = idempotency_key
                event["event_sha256"] = canonical_sha256(event)
                with self.path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                return event
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def reserve(self, job_id: str, reservation: Mapping[str, int], *, idempotency_key: str) -> dict[str, Any]:
        amount = _counters(reservation, label="reservation")
        totals = self.totals()
        reserved = {key: totals["reserved"][key] + amount[key] for key in COUNTERS}
        if any(reserved[key] + totals["consumed"][key] > self.caps[key] for key in COUNTERS):
            raise ExecutionLedgerError("reservation exceeds contract cap")
        return self.append(event_type="RESERVATION_CREATED", reserved_after=reserved, consumed_after=totals["consumed"], metadata={"job_id": job_id, "reservation": amount}, idempotency_key=idempotency_key)

    def settle(self, job_id: str, reservation: Mapping[str, int], actual: Mapping[str, int], *, idempotency_key: str) -> dict[str, Any]:
        reserved_amount = _counters(reservation, label="reservation")
        actual_amount = _counters(actual, label="actual")
        totals = self.totals()
        reserved = {key: max(0, totals["reserved"][key] - reserved_amount[key]) for key in COUNTERS}
        consumed = {key: totals["consumed"][key] + actual_amount[key] for key in COUNTERS}
        overrun = any(actual_amount[key] > reserved_amount[key] for key in COUNTERS) or any(consumed[key] > self.caps[key] for key in COUNTERS)
        return self.append(event_type="BUDGET_OVERRUN" if overrun else "JOB_SETTLED", reserved_after=reserved, consumed_after=consumed, metadata={"job_id": job_id, "reservation": reserved_amount, "actual": actual_amount, "overrun": overrun}, idempotency_key=idempotency_key)
