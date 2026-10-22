"""What a coding question requires, expressed as DATA so the evaluator is reusable (no scores are hard-coded for any sample answer).

A requirement has one of three kinds, and the kinds are never mixed into one number:
  functional   a behaviour test (see harness.py). Passed/failed ONLY when the sandbox actually ran it; otherwise "not run".
  structure    evidence in the code TEXT (via `ast`) that an approach is present: shows what the author wrote, not that it works.
  explanation  topics the question asks to be explained. Matching wording is only a "mentioned" signal: it can never verify that an explanation is correct.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .static import StaticReport

STRUCTURE_STATUSES = ("demonstrated", "missing", "contradicted", "unclear", "not_applicable")
EXPLANATION_STATUSES = ("mentioned_unverified", "partial_unverified", "missing")


@dataclass
class Finding:
    status: str
    evidence: List[str] = field(default_factory=list)
    note: str = ""


@dataclass
class Context:
    report: StaticReport
    code: str
    prose: str          # explanation text: prose + comments + docstrings

    def snippet(self, line: int) -> str:
        return f"line {line}: {self.report.line(line)}"


@dataclass(frozen=True)
class Requirement:
    id: str
    label: str
    kind: str                                   # functional | structure | explanation
    test_id: str = ""                           # functional: id of the harness test
    check: Optional[Callable[[Context], Finding]] = None
    help: str = ""                              # one line on what this requirement means


@dataclass(frozen=True)
class CodeSpec:
    spec_id: str
    question_id: str
    title: str
    harness_id: str
    requirements: Tuple[Requirement, ...]
    limitations: Tuple[str, ...] = ()
    cases: Tuple[Dict[str, object], ...] = ()      # declarative functional cases (data); empty for the hand-written specs


_REGISTRY: Dict[str, CodeSpec] = {}


def register(spec: CodeSpec) -> CodeSpec:
    for r in spec.requirements:
        if r.kind not in ("functional", "structure", "explanation"):
            raise ValueError(f"{spec.spec_id}/{r.id}: unknown kind {r.kind}")
        if r.kind == "functional" and not r.test_id:
            raise ValueError(f"{spec.spec_id}/{r.id}: functional requirements need a test_id")
        if r.kind != "functional" and r.check is None:
            raise ValueError(f"{spec.spec_id}/{r.id}: {r.kind} requirements need a check")
    ids = [r.id for r in spec.requirements]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{spec.spec_id}: duplicate requirement ids")
    _REGISTRY[spec.question_id] = spec
    return spec


def get_spec(question_id: str) -> Optional[CodeSpec]:
    _load_builtin()
    return _REGISTRY.get(question_id)


def spec_question_ids() -> List[str]:
    _load_builtin()
    return sorted(_REGISTRY)


def _load_builtin() -> None:
    if not _REGISTRY:
        from . import specs_builtin  # noqa: F401  (registers on import)


# ------------------------------------------------------------------------------------------------ helpers shared by specs
def topic_match(prose: str, groups: List[List[str]]) -> Tuple[str, List[str]]:
    """Wording evidence for an explanation topic. `groups` are alternatives that must ALL be hit for 'mentioned'. Returns (status, matched phrases)."""
    hit_groups, phrases = 0, []
    for g in groups:
        found = [m.group(0) for p in g for m in [re.search(p, prose or "", re.I)] if m]
        if found:
            hit_groups += 1; phrases.append(found[0])
    if hit_groups == len(groups):
        return "mentioned_unverified", phrases
    return ("partial_unverified" if hit_groups else "missing"), phrases


def explanation_check(groups: List[List[str]], label: str) -> Callable[[Context], Finding]:
    def check(ctx: Context) -> Finding:
        status, phrases = topic_match(ctx.prose, groups)
        note = {"mentioned_unverified": f"The answer's text mentions this ({label}). Only wording was checked: whether the explanation is correct is NOT verified.",
                "partial_unverified": f"Only part of this explanation ({label}) appears in the answer's text, and wording alone cannot show it is correct.",
                "missing": f"No explanation of this ({label}) was found in the answer's text (prose, comments or docstrings)."}[status]
        return Finding(status, [f"wording found: “{p}”" for p in phrases], note)
    return check
