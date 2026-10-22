"""Demo-layer adapter for the experimental code-aware assessment (src/codeeval). OFF by default: SMART_DEMO_CODE_EVAL=1 turns the option on in the setup form.
Imports are lazy, so a session that never asks for it never loads the package. Execution of candidate code is a separate switch inside codeeval (SMART_CODEEVAL_EXEC=docker)
and is NEVER done in this process: the default is a static read of the code text."""
from __future__ import annotations

import os
from typing import Any, Dict, List


def enabled() -> bool:
    return os.environ.get("SMART_DEMO_CODE_EVAL", "").strip().lower() in ("1", "true", "yes", "on")


def execution_requested() -> bool:
    return (os.environ.get("SMART_CODEEVAL_EXEC") or "").strip().lower() == "docker"


def spec_ids() -> List[str]:
    from src.codeeval.spec import spec_question_ids
    return spec_question_ids()


def has_spec(question_id: str) -> bool:
    from src.codeeval.spec import get_spec
    return get_spec(question_id) is not None


def sandboxed_runner() -> bool:
    """True when a real execution backend is configured (so the assessment may take seconds and runs in the background). Does not touch Docker."""
    from src.codeeval.runner import shared_runner
    return bool(shared_runner().sandboxed)


def assess(question_id: str, answer: str) -> Dict[str, Any]:
    """Never raises (the codeeval layer contains its own failures)."""
    from src.codeeval.evaluate import assess as _assess
    return _assess(question_id, answer)


def describe() -> Dict[str, Any]:
    return {"enabled": enabled(), "execution_requested": execution_requested(), "questions": sorted(spec_ids()) if enabled() else [],
            "text": ("Reads your code (never runs it) and reports which required parts are present, missing or unclear."
                     + (" A locked-down Docker sandbox was requested for behaviour tests; it is used only if its self-test passes." if execution_requested() else " Behaviour tests are not run."))}
