"""Interface-only binding for ``F3CommonGraspPrefixV2``.

V2_1 does not change the frozen physical contract.  It only makes the
constructor, canonical-prefix contract, immutable artifact, per-scene receipt,
and finalizer carry and verify one explicit contract identity.
"""

from __future__ import annotations

from typing import Any, Mapping

from .current_hasher import hash_json
from .f3_common_grasp_prefix_v2 import (
    CONTRACT_VERSION,
    build_f3_common_grasp_prefix_v2,
    validate_f3_common_grasp_prefix_v2,
)


IMPLEMENTATION_VERSION = "controlled_multi_future_post_stage0_closure_f3_v2_1"
BINDING_SCHEMA_VERSION = "cmf_f3_common_grasp_prefix_binding_v2_1"
BINDING_FIELD = "f3_common_grasp_prefix_v2"
LEGACY_BINDING_FIELD = "shared_prefix_repair_v11"


def build_f3_common_grasp_prefix_binding_v2_1(
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    value = validate_f3_common_grasp_prefix_v2(contract)
    binding = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "binding_field": BINDING_FIELD,
        "contract_version": CONTRACT_VERSION,
        "contract_sha256": value["contract_sha256"],
        "physical_contract_unchanged": value == build_f3_common_grasp_prefix_v2(),
    }
    binding["binding_sha256"] = hash_json(binding)
    return binding


def validate_bound_f3_common_grasp_prefix_v2_1(
    prefix_contract: Mapping[str, Any],
    *,
    expected_contract: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(prefix_contract, Mapping):
        raise ValueError("F3 V2_1 canonical prefix contract must be a mapping")
    if not isinstance(expected_contract, Mapping):
        raise ValueError("F3 V2_1 constructor contract must be a mapping")
    expected = validate_f3_common_grasp_prefix_v2(expected_contract)
    if prefix_contract.get(LEGACY_BINDING_FIELD) is not None:
        raise ValueError("F3 V2_1 cannot coexist with the historical v11 binding")
    embedded = prefix_contract.get(BINDING_FIELD)
    if not isinstance(embedded, Mapping):
        raise ValueError("F3CommonGraspPrefixV2_1 binding is missing")
    actual = validate_f3_common_grasp_prefix_v2(embedded)
    if actual != expected:
        raise ValueError("F3CommonGraspPrefixV2_1 binding differs from constructor")
    binding = build_f3_common_grasp_prefix_binding_v2_1(actual)
    return {
        "binding": binding,
        "prefix_contract_sha256": hash_json(prefix_contract),
    }


def build_f3_common_grasp_prefix_context_binding_v2_1(
    validation: Mapping[str, Any],
    *,
    artifact_sha256: str,
) -> dict[str, Any]:
    binding = dict(validation.get("binding", {}))
    if binding.get("binding_sha256") != hash_json(
        {key: value for key, value in binding.items() if key != "binding_sha256"}
    ):
        raise ValueError("F3 V2_1 binding receipt hash mismatch")
    prefix_contract_sha256 = validation.get("prefix_contract_sha256")
    if not isinstance(prefix_contract_sha256, str) or len(prefix_contract_sha256) != 64:
        raise ValueError("F3 V2_1 prefix contract SHA-256 is invalid")
    if not isinstance(artifact_sha256, str) or len(artifact_sha256) != 64:
        raise ValueError("F3 V2_1 artifact SHA-256 is invalid")
    result = {
        **binding,
        "prefix_contract_sha256": prefix_contract_sha256,
        "artifact_sha256": artifact_sha256,
    }
    result["context_binding_sha256"] = hash_json(result)
    return result


__all__ = [
    "BINDING_FIELD",
    "BINDING_SCHEMA_VERSION",
    "IMPLEMENTATION_VERSION",
    "LEGACY_BINDING_FIELD",
    "build_f3_common_grasp_prefix_binding_v2_1",
    "build_f3_common_grasp_prefix_context_binding_v2_1",
    "validate_bound_f3_common_grasp_prefix_v2_1",
]
