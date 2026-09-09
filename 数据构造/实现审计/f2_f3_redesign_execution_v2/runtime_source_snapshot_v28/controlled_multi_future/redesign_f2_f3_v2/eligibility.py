"""Versioned current research eligibility, separate from historical acceptance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical import atomic_write_json, canonical_sha256


SCHEMA = "cmf_f2_f3_current_research_eligibility_v2"


def empty_index() -> dict[str, Any]:
    return {"schema_version": SCHEMA, "version": "v2", "historical_source": "cmf_f2_f3_redesign_20260907", "cells": {}, "roots": {}, "research_loader_default": "current_research_eligibility", "old_complete_is_not_sufficient": True}


def set_cell(index: dict[str, Any], *, cell_key: str, historical: str, current: str, reasons: list[str], superseded_by: str | None = None, permitted_use: list[str] | None = None) -> None:
    index.setdefault("cells", {})[cell_key] = {"historical_implementation_acceptance": historical, "current_research_eligibility": current, "blocking_reasons": list(reasons), "superseded_by": superseded_by, "permitted_use": permitted_use or ["development", "audit"]}


def set_root(index: dict[str, Any], *, root_id: str, current: str, reasons: list[str]) -> None:
    index.setdefault("roots", {})[root_id] = {"current_research_eligibility": current, "blocking_reasons": list(reasons)}


def write_index(path: Path, index: dict[str, Any]) -> dict[str, Any]:
    value = dict(index); value["index_sha256"] = canonical_sha256(value); atomic_write_json(path, value); return value


def load_for_research(path: Path, cell_key: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != SCHEMA:
        raise ValueError("eligibility schema mismatch")
    cell = value.get("cells", {}).get(cell_key)
    if cell is None or cell.get("current_research_eligibility") != "ELIGIBLE":
        raise PermissionError(f"cell is not currently research eligible: {cell_key}")
    return cell
