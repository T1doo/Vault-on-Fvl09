"""Hash-chained, idempotent budget events with per-job accounting."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .canonical import atomic_write_json, canonical_sha256
from .contract import BUDGET_CAPS, COUNTERS, ContractError, validate_counters


class LedgerError(ValueError):
    """Raised when an event would make accounting ambiguous or unsafe."""


def _zero() -> dict[str, int]:
    return {key: 0 for key in COUNTERS}


class BudgetLedger:
    """Append-only ledger; the caller remains the single state publisher."""

    def __init__(self, path: str | Path, *, contract_sha256: str, task_id: str, parent_contract_sha256: str | None = None, ancestor_contract_sha256s: list[str] | tuple[str, ...] | None = None):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.contract_sha256 = contract_sha256
        self.parent_contract_sha256 = parent_contract_sha256
        self.ancestor_contract_sha256s = tuple(ancestor_contract_sha256s or ())
        self.task_id = task_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.touch(exist_ok=True)

    def _events_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        contract_chain = [*self.ancestor_contract_sha256s]
        if self.parent_contract_sha256:
            contract_chain.append(self.parent_contract_sha256)
        contract_chain.append(self.contract_sha256)
        if len(contract_chain) != len(set(contract_chain)):
            raise LedgerError("contract ancestry contains duplicates")
        last_contract_index = 0
        with self.path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise LedgerError(f"invalid JSON at ledger line {line_number}") from exc
                expected = canonical_sha256({key: value for key, value in event.items() if key != "event_sha256"})
                if event.get("event_sha256") != expected:
                    raise LedgerError(f"event hash mismatch at ledger line {line_number}")
                if event.get("prev_event_sha256") != (events[-1]["event_sha256"] if events else None):
                    raise LedgerError(f"event chain mismatch at ledger line {line_number}")
                if event.get("task_id") != self.task_id:
                    raise LedgerError("ledger event belongs to another task")
                event_contract = event.get("contract_sha256")
                if event_contract not in contract_chain:
                    raise LedgerError("ledger event belongs to another contract")
                contract_index = contract_chain.index(event_contract)
                if contract_index < last_contract_index:
                    raise LedgerError("ancestor-contract event appears after a newer contract")
                if contract_index > last_contract_index:
                    if contract_index != last_contract_index + 1:
                        raise LedgerError("ledger skipped a contract generation")
                    if event.get("event_type") != "BUDGET_CAP_AMENDMENT":
                        raise LedgerError("new contract requires a budget amendment event")
                    metadata = event.get("metadata", {})
                    if metadata.get("parent_contract_sha256") != contract_chain[contract_index - 1]:
                        raise LedgerError("budget amendment parent contract mismatch")
                    last_contract_index = contract_index
                validate_counters(event.get("reserved_after", {}), label="reserved_after")
                validate_counters(event.get("consumed_after", {}), label="consumed_after")
                events.append(event)
        return events

    def events(self) -> list[dict[str, Any]]:
        with self.lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
            try:
                return self._events_unlocked()
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def totals(self) -> dict[str, dict[str, int]]:
        events = self.events()
        if not events:
            return {"reserved": _zero(), "consumed": _zero()}
        last = events[-1]
        return {
            "reserved": validate_counters(last["reserved_after"], label="reserved_after"),
            "consumed": validate_counters(last["consumed_after"], label="consumed_after"),
        }

    def append(
        self,
        *,
        event_type: str,
        delta: Mapping[str, int] | None = None,
        reserved_after: Mapping[str, int] | None = None,
        consumed_after: Mapping[str, int] | None = None,
        metadata: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not event_type or not isinstance(event_type, str):
            raise LedgerError("event_type must be non-empty")
        delta_value = validate_counters(delta or _zero(), label="delta")
        metadata_value = dict(metadata or {})
        with self.lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                events = self._events_unlocked()
                if idempotency_key:
                    for prior in events:
                        if prior.get("idempotency_key") == idempotency_key:
                            return prior
                totals = self.totals_unlocked(events)
                reserved = validate_counters(reserved_after or totals["reserved"], label="reserved_after")
                consumed = validate_counters(consumed_after or totals["consumed"], label="consumed_after")
                for key in COUNTERS:
                    if reserved[key] > BUDGET_CAPS[key] or consumed[key] > BUDGET_CAPS[key]:
                        raise LedgerError(f"budget cap exceeded for {key}")
                event: dict[str, Any] = {
                    "schema_version": "cmf_f2_f3_budget_event_v1",
                    "event_id": f"evt-{len(events) + 1:06d}",
                    "event_type": event_type,
                    "task_id": self.task_id,
                    "contract_sha256": self.contract_sha256,
                    "delta": delta_value,
                    "reserved_after": reserved,
                    "consumed_after": consumed,
                    "prev_event_sha256": events[-1]["event_sha256"] if events else None,
                    "metadata": metadata_value,
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

    @staticmethod
    def totals_unlocked(events: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
        if not events:
            return {"reserved": _zero(), "consumed": _zero()}
        return {
            "reserved": validate_counters(events[-1]["reserved_after"], label="reserved_after"),
            "consumed": validate_counters(events[-1]["consumed_after"], label="consumed_after"),
        }

    def reserve(self, job_id: str, reservation: Mapping[str, int], *, idempotency_key: str) -> dict[str, Any]:
        reservation_value = validate_counters(reservation, label="reservation")
        totals = self.totals()
        reserved = {key: totals["reserved"][key] + reservation_value[key] for key in COUNTERS}
        for key in COUNTERS:
            if reserved[key] + totals["consumed"][key] > BUDGET_CAPS[key]:
                raise LedgerError(f"reservation plus consumed exceeds cap for {key}")
        return self.append(
            event_type="RESERVATION_CREATED",
            delta=reservation_value,
            reserved_after=reserved,
            consumed_after=totals["consumed"],
            metadata={"job_id": job_id, "reservation": reservation_value},
            idempotency_key=idempotency_key,
        )

    def settle(self, job_id: str, reservation: Mapping[str, int], actual: Mapping[str, int], *, idempotency_key: str) -> dict[str, Any]:
        reservation_value = validate_counters(reservation, label="reservation")
        actual_value = validate_counters(actual, label="actual")
        totals = self.totals()
        reserved = {key: max(0, totals["reserved"][key] - reservation_value[key]) for key in COUNTERS}
        consumed = {key: totals["consumed"][key] + actual_value[key] for key in COUNTERS}
        overrun = any(actual_value[key] > reservation_value[key] for key in COUNTERS)
        return self.append(
            event_type="BUDGET_OVERRUN" if overrun else "JOB_SETTLED",
            delta=actual_value,
            reserved_after=reserved,
            consumed_after=consumed,
            metadata={"job_id": job_id, "reservation": reservation_value, "actual": actual_value, "overrun": overrun},
            idempotency_key=idempotency_key,
        )
