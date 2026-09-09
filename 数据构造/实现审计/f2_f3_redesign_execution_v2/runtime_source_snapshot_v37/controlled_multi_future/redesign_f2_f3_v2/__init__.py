"""V2.1 F2/F3 execution control plane.

The package is deliberately additive and lazy: importing it does not import
SAPIEN, CUDA, or start a worker.  It provides the independent contract,
budget ledger, GPU guard, asset readback, strict model boundary, and the
minimum lifecycle needed before a real F2/F3 job can be dispatched.
"""

from .canonical import canonical_sha256, canonical_json
from .contract import BUDGET_CAPS, ALLOWED_PHYSICAL_GPU_INDICES
from .ledger import BudgetLedger, LedgerError

__all__ = [
    "ALLOWED_PHYSICAL_GPU_INDICES",
    "BUDGET_CAPS",
    "BudgetLedger",
    "LedgerError",
    "canonical_json",
    "canonical_sha256",
]
