"""Engine variant 3c4.0 (opt-in, versioned). The frozen 3c1.0 modules are untouched and remain the default; this module only PATCHES them for the duration of a
`use_3c4()` block and restores them afterwards.

Contents = the two 3c1.1 corrections (Type I/Type II veto, variant-tolerant concept words) PLUS the general reliability gates found while analysing the 20-answer
Qwen run. Every gate has one property, checked by an invariant test: it can only move a verdict to UNVERIFIED. None can create credit, create a penalty, or turn
anything into "missing". "Cannot establish" is reported as uncertainty, never as a mark.

  G1 credit_without_concept_in_cited_claim   a CREDIT cites claims that contain none of the concept's words (prose claims only). The gate checks the cited claim id exists
                                              but not that it says anything about the concept (b2-028 credited "feedforward neural network" from a sentence about CNNs).
                                              Where the words DO occur in another claim the reason is credit_cites_wrong_claim. We never re-point the credit: that would create credit.
  G2 error_without_concept_in_cited_claim    the same test for a PENALTY: an "incorrect" finding whose cited claims never mention the concept (b2-105 blamed "unpinned dependencies" on a
                                              sentence about GPUs). An unsupported penalty is as unacceptable as an unsupported credit.
  G3 error_alleges_omission                  an "incorrect" finding whose own explanation says the answer LACKS something, or negates the concept itself ("not a heap"). That is an omission, not an error; the two stay distinct and
                                              an omission claim is not trusted as an error (s2-f02). It is NOT converted to "missing" (that would create a penalty).
  (considered and REJECTED: an "error matches a sanctioned alternative" gate. Word overlap cannot tell an equivalent formulation from a contradictory one: it would also
   have hidden the genuine Type I/Type II and O(n)/O(log n) errors. b2-109's valid-alternative false error is only caught where the model's own explanation negates the
   concept ("not a heap"), which G3 treats as a non-use/omission statement.)
  + lexnorm: Type I/II veto, -ise/-ize, British forms, irregular technical plurals (matrices/matrix), compound joins (tf-idf/tfidf) for the omission guard.

What lexical matching does and does not mean here: zero shared words between a cited claim and the concept is treated as "support cannot be shown" -> uncertainty.
Shared words are NEVER treated as proof of correctness (nothing here grants anything). Known cost: a correct answer that paraphrases a concept with no shared word
(b2-072 "68-95-99.7 rule" from a sentence about |z|>1 tails) becomes UNVERIFIED instead of credited, which can turn a number into an abstention. That is deliberate:
without human validation we prefer uncertainty to unsupported credit, and the cost is measured, not hidden (see replay in the 3C-4 report).

NOT changed (policy decisions pending): rubric weights, free reasoning marks, off-topic numeric policy, completeness thresholds, scope eligibility, the frozen prompt/schema.
Scores produced under 3c4.0 are a DIFFERENT experiment version and must never be mixed into 3c1.0 results or used for adaptive difficulty.

Thread-safety: patching is process-wide, so every evaluation under a variant takes one lock; call `evaluate_3c4` / `evaluate_frozen`, never patch by hand.
"""
from __future__ import annotations

import contextlib
import re
import threading
from dataclasses import replace
from typing import Dict, List, Optional, Tuple

from . import consistency as C0, verification as V0
from .claims import Claim, Segmentation
from .lexnorm import compact_present, content_stems_v31, negates_concept
from .requirements import OTHER_VALID
from .variant_v31 import check_v31

VARIANT = "3c4.0"
_C, _X, _N, _U = V0.ConceptState.STATES_CORRECTLY, V0.ConceptState.STATES_INCORRECTLY, V0.ConceptState.NOT_STATED, V0.ConceptState.UNVERIFIED

GATE_REASONS = ("credit_without_concept_in_cited_claim", "credit_cites_wrong_claim", "error_without_concept_in_cited_claim", "error_alleges_omission")

_OMISSION_RX = re.compile(
    r"\b(?:does\s*n[o']?t|do\s+not|did\s+not|did\s*n[o']?t|never|fails?\s+to|failed\s+to|without)\s+(?:\w+\s+){0,2}?(?:mention|specify|state|say|discuss|explain|include|cover|address|provide|define|describe|identify|name|give|show|note|refer)\w*\b"
    r"|\bno\s+(?:explicit\s+|clear\s+|direct\s+)?(?:mention|reference|discussion|explanation|statement|definition|description)\b"
    r"|\b(?:omits?|omitted|omission|lacks?|lacking|missing|absent|not\s+(?:explicitly\s+|clearly\s+)?(?:mentioned|stated|specified|discussed|addressed|covered|included|defined|described|explained))\b", re.I)

_LOCK = threading.RLock()
ALL_GATES = frozenset({"support", "omission"})      # support = G1+G2, omission = G3
_active_gates = ALL_GATES


# ------------------------------------------------------------------------------------------------- gate helpers
def _share(member: str, texts: List[str]) -> Optional[float]:
    ms = content_stems_v31(member)
    if not ms:
        return None
    have = set()
    for t in texts:
        have |= content_stems_v31(t)
    return len(ms & have) / len(ms)


def support_for(member: str, cited: List[Claim], others: List[Claim]) -> Dict:
    """How much of the concept's wording appears in the cited claims, and whether it appears elsewhere. Reporting + gate input."""
    share = _share(member, [c.text for c in cited])
    in_other = [c.id for c in others if (_share(member, [c.text]) or 0) >= 0.8]
    code_only = bool(cited) and all(c.kind == "code" for c in cited)
    return {"share": share, "found_in_other_claims": in_other, "code_only": code_only}


def _claim_lookup(seg: Segmentation) -> Dict[str, Claim]:
    return {c.id: c for c in seg.claims}


def _gate_down(v: V0.VerifiedVerdict, why: str) -> V0.VerifiedVerdict:
    return C0._down(v, why)


def check_3c4(validated: V0.Validated, seg: Segmentation) -> C0.Consistent:
    """3c1.1 consistency (frozen logic + the Type I/II veto) followed by the support gates G1-G3. Downgrade-only."""
    base = check_v31(validated, seg)
    claims = _claim_lookup(seg)
    gradable = list(seg.gradable_claims)
    vs = list(base.verdicts)
    adj = list(base.adjustments)
    flags = list(base.flags)
    for i, v in enumerate(vs):
        if v.member == OTHER_VALID or v.state not in (_C, _X):
            continue
        cited = [claims[c] for c in v.claim_ids if c in claims]
        others = [c for c in gradable if c.id not in {x.id for x in cited}]
        sup = support_for(v.member, cited, others)
        if v.state is _X:
            if "omission" in _active_gates and v.explanation and (_OMISSION_RX.search(v.explanation) or negates_concept(v.explanation, v.member)):
                vs[i] = _gate_down(v, "error_alleges_omission"); adj.append(f"{v.requirement_id}/{v.member}: error finding describes an omission"); flags.append("gate_error_alleges_omission")
                continue
        if "support" not in _active_gates or sup["share"] is None or sup["code_only"] or not cited:
            continue                                                    # no wording to check (or code has no lexical anchor): the 3c1.0 treatment stands
        if sup["share"] == 0.0:
            if v.state is _C:
                why = "credit_cites_wrong_claim" if sup["found_in_other_claims"] else "credit_without_concept_in_cited_claim"
            else:
                why = "error_without_concept_in_cited_claim"
            vs[i] = _gate_down(v, why)
            adj.append(f"{v.requirement_id}/{v.member}: {why}")
            flags.append("gate_" + why)
    return C0.Consistent(tuple(vs), base.on_topic, base.reasoning_claim_ids, tuple(dict.fromkeys(flags)), tuple(adj))


def _lexically_present_3c4(member: str, claims) -> bool:
    """The omission guard with variant-tolerant stems (patched in as V0.content_stems) plus the compound-join check. It can only REFUSE a model's 'not stated'."""
    return V0_lexically_present_orig(member, claims) or any(compact_present(member, c.text) for c in claims)


V0_lexically_present_orig = V0._lexically_present


@contextlib.contextmanager
def use_3c4(gates=None):
    """Temporarily route the pipeline through 3c4.0 (process-local, restored on exit, serialised by a lock). `gates` (default all) exists so each gate's own effect can be
    measured in isolation; a result produced with fewer gates is stamped accordingly."""
    global _active_gates
    with _LOCK:
        _active_gates = ALL_GATES if gates is None else frozenset(gates)
        old = (C0.check, V0.content_stems, V0._lexically_present)
        C0.check, V0.content_stems, V0._lexically_present = check_3c4, content_stems_v31, _lexically_present_3c4
        try:
            yield VARIANT
        finally:
            C0.check, V0.content_stems, V0._lexically_present = old
            _active_gates = ALL_GATES


def evaluate_3c4(evaluator, *args, gates=None, **kwargs):
    """Run evaluator.evaluate under 3c4.0 and stamp the variant (and which gates fired) into provenance so it can never be mistaken for a 3c1.0 result."""
    with use_3c4(gates):
        res = evaluator.evaluate(*args, **kwargs)
    fired = sorted({f[5:] for f in res.flags if f.startswith("gate_")})
    res.provenance["engine_variant"] = VARIANT
    res.provenance["variant_gates_fired"] = fired
    res.provenance["variant_gates_enabled"] = sorted(ALL_GATES if gates is None else gates)
    return res


def evaluate_frozen(evaluator, *args, **kwargs):
    """Run the frozen 3c1.0 engine under the same lock so a concurrent variant evaluation can never leak into it."""
    with _LOCK:
        return evaluator.evaluate(*args, **kwargs)
