"""Stage 3C-1: modular, evidence-grounded evaluator (offline, mock-verifier only). NOT wired into Flask; legacy scoring stays the default."""
from .pipeline import ModularEvaluator, ModularResult, ModularStatus
from .reference import ReferenceMaterial
from .scope import ScopeStore

__all__ = ["ModularEvaluator", "ModularResult", "ModularStatus", "ReferenceMaterial", "ScopeStore"]
