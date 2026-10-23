"""Interview catalogue built from the curated corpus (the same source `SMART_QUESTION_SOURCE=curated` serves). No question data is created here."""
from __future__ import annotations

import random
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

DIFFICULTIES = ("Easy", "Medium", "Hard")
MIX = "Mixed"
SIZES = (3, 5, 8)
DEFAULT_SIZE = 5


class CatalogError(ValueError):
    """The requested interview cannot be built (unknown role/domain/difficulty, empty pool). The message is safe to show to the user."""


def _alias(domains: Sequence[str]) -> List[str]:
    from src.retrieval.question_source import normalise_domains          # light import: no faiss / torch
    return normalise_domains(list(domains))


def roles() -> Dict[str, List[str]]:
    """Role -> curated domain labels (the existing ROLE_MAPPING, mapped through the curated-source aliases). 'Custom Interview' is represented by the free domain picker."""
    import sys
    from pathlib import Path
    comp = str(Path(__file__).resolve().parents[1] / "components")
    if comp not in sys.path:                                                  # main/app.py adds this; do not depend on it (embedding, tests, scripts)
        sys.path.insert(0, comp)
    from config import ROLE_MAPPING
    return {r: _alias(d) for r, d in ROLE_MAPPING.items() if d}


def domain_counts(records: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    for r in records:
        out.setdefault(r["domain"], Counter())[r["difficulty"]] += 1
    return {d: {k: int(c.get(k, 0)) for k in DIFFICULTIES} for d, c in sorted(out.items())}


def resolve_domains(records: Sequence[Dict[str, Any]], role: Optional[str], domains: Optional[Sequence[str]]) -> List[str]:
    known = {r["domain"] for r in records}
    if domains:
        want = list(dict.fromkeys(str(d) for d in domains))
        bad = [d for d in want if d not in known]
        if bad:
            raise CatalogError(f"Unknown domain(s): {', '.join(bad)}")
        return want
    if role:
        m = roles()
        if role not in m:
            raise CatalogError(f"Unknown role: {role}")
        return [d for d in m[role] if d in known]
    raise CatalogError("Choose a role or at least one domain.")


def _split(n: int) -> Dict[str, int]:
    """Fixed Easy -> Medium -> Hard progression for 'Mixed' (NOT adaptive: it never depends on any score)."""
    base = {3: (1, 1, 1), 5: (2, 2, 1), 8: (3, 3, 2)}.get(n)
    if base is None:
        e = n // 3; h = n // 3; base = (n - e - h, e, h)
    return dict(zip(DIFFICULTIES, base))


def select_questions(records: Sequence[Dict[str, Any]], domains: Sequence[str], difficulty: str, n: int, *, eligible_ids: Sequence[str] = (),
                     prefer_scorable: bool = False, rng: Optional[random.Random] = None) -> Dict[str, Any]:
    """Pick `n` distinct questions. Returns {questions, shortfall, pool}. A shortfall (fewer than asked) is reported, never padded from other domains/difficulties
    silently: in 'Mixed' mode a short level is topped up from the neighbouring levels and that is reported too."""
    if difficulty not in DIFFICULTIES + (MIX,):
        raise CatalogError(f"Unknown difficulty: {difficulty}")
    if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= 20:
        raise CatalogError("Question count must be between 1 and 20.")
    rng = rng or random.Random()
    want = set(domains)
    pool = [r for r in records if r["domain"] in want]
    elig = set(eligible_ids)

    def draw(level: str, k: int, taken: set) -> List[Dict[str, Any]]:
        cands = [r for r in pool if r["difficulty"] == level and r["question_id"] not in taken]
        rng.shuffle(cands)
        if prefer_scorable:
            cands.sort(key=lambda r: r["question_id"] not in elig)
        return cands[:k]

    chosen: List[Dict[str, Any]] = []
    notes: List[str] = []
    if difficulty != MIX:
        chosen = draw(difficulty, n, set())
        if len(chosen) < n:
            notes.append(f"Only {len(chosen)} {difficulty} question(s) exist for the selected domains (you asked for {n}).")
    else:
        split = _split(n)
        taken: set = set()
        for level in DIFFICULTIES:
            got = draw(level, split[level], taken)
            taken |= {r["question_id"] for r in got}
            chosen += got
            if len(got) < split[level]:
                notes.append(f"Only {len(got)} {level} question(s) available (wanted {split[level]}).")
        missing = n - len(chosen)
        for level in ("Medium", "Easy", "Hard"):
            if missing <= 0:
                break
            extra = draw(level, missing, taken)
            taken |= {r["question_id"] for r in extra}
            chosen += extra
            missing -= len(extra)
        order = {d: i for i, d in enumerate(DIFFICULTIES)}
        chosen.sort(key=lambda r: order[r["difficulty"]])
        if len(chosen) < n:
            notes.append(f"Only {len(chosen)} question(s) exist in total for the selected domains.")
    if not chosen:
        raise CatalogError("No questions match this domain / difficulty combination. Pick another difficulty or add domains.")
    return {"questions": chosen, "notes": notes, "pool_size": len(pool)}


MIN_ROLE_QUESTIONS = 12


def supported_roles(records: Sequence[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Roles the curated bank can actually interview for: role -> the role's domains that exist in the bank, only when they hold enough questions (Stage 9B).
    A role whose domains are missing from, or too thin in, the bank is not offered."""
    count = Counter(r["domain"] for r in records)
    out: Dict[str, List[str]] = {}
    for role, doms in roles().items():
        have = [d for d in doms if count.get(d)]
        if have and sum(count[d] for d in have) >= MIN_ROLE_QUESTIONS:
            out[role] = have
    return out
