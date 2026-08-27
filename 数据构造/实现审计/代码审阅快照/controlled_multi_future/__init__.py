"""Additive F1--F4 implementation scaffold.

This package is intentionally isolated from the official RoboTwin task modules.
It contains no Stage 0 collector and performs no work on import.
"""

from .base import ControlledMultiFutureSceneBase, ImplementationAuditError

__all__ = ["ControlledMultiFutureSceneBase", "ImplementationAuditError"]
