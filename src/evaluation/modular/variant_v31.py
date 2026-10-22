"""Engine variant 3c1.1 (opt-in; the frozen 3c1.0 modules are untouched and remain the default).

Two general, non-policy corrections, both found as implementation defects rather than tuned to scores:
  1. consistency.check rule 3 ("one claim credited AND blamed for overlapping concepts") compared concept labels with a stemmer that drops one-letter tokens,
     so "Type I error" and "Type II error" overlapped by 67% and were treated as the same concept. 3c1.1 vetoes the overlap when the labels differ in a
     discriminating token (Type I/II, L1/L2).
  2. the omission guard (verification._lexically_present) used a crude suffix stripper, so spelling/morphological variants of a concept name were not recognised
     ("regularisation"/"regularization", "convolution"/"convolutional"). 3c1.1 uses lexnorm.content_stems_v31.
Neither change can create credit: the guard only refuses a model's "not stated", and the overlap rule only refuses to downgrade distinct concepts.
NOT changed (policy, pending a decision): rubric weights, reasoning convention, off-topic numeric policy, tiers, thresholds, frozen prompt/schema.

Use:   with use_v31():  ModularEvaluator(...).evaluate(...)      (or evaluate_v31(evaluator, ...) which also stamps provenance)
Any score produced under 3c1.1 is a different experiment version: it must never be mixed into 3c1.0 results.
"""
from __future__ import annotations

import contextlib
from dataclasses import replace
from typing import List

from . import consistency as C0, verification as V0
from ..injection import detect_injection
from .claims import Segmentation
from .lexnorm import content_stems_v31, labels_may_overlap
from .requirements import OTHER_VALID
from .verification import Validated

VARIANT = "3c1.1"
_C, _X, _N, _U = V0.ConceptState.STATES_CORRECTLY, V0.ConceptState.STATES_INCORRECTLY, V0.ConceptState.NOT_STATED, V0.ConceptState.UNVERIFIED


def check_v31(validated: Validated, seg: Segmentation) -> C0.Consistent:
    """consistency.check with ONLY rule 3's overlap test replaced; everything else is the frozen logic, copied verbatim."""
    vs: List[V0.VerifiedVerdict] = list(validated.verdicts)
    adj: List[str] = []
    flags = list(validated.flags)
    for i, v in enumerate(vs):
        if v.explanation and detect_injection(v.explanation):
            vs[i] = C0._down(v, "verdict_echoes_candidate_instruction"); adj.append(f"{v.requirement_id}/{v.member}: echoes instruction")
            flags.append("verifier_output_echoes_instruction")
    by_label = {}
    for i, v in enumerate(vs):
        if v.member != OTHER_VALID:
            by_label.setdefault(C0._norm(v.member), []).append(i)
    for label, idxs in by_label.items():
        states = {vs[i].state for i in idxs} - {_U}
        if len(states) > 1:
            for i in idxs:
                if vs[i].state is not _U:
                    adj.append(f"{vs[i].requirement_id}/{vs[i].member}: inconsistent across requirements"); vs[i] = C0._down(vs[i], "inconsistent_across_requirements")
            flags.append("contradictory_verdicts")
    for i, a in enumerate(vs):
        if a.state is not _C:
            continue
        for j, b in enumerate(vs):
            if b.state is not _X or i == j or not (set(a.claim_ids) & set(b.claim_ids)):
                continue
            if labels_may_overlap(a.member, b.member):                      # <- the only change (3c1.0: Jaccard of frozen stems >= 0.5)
                adj.append(f"claim shared: {a.member} credited and {b.member} blamed")
                vs[i] = C0._down(vs[i], "same_claim_correct_and_incorrect"); vs[j] = C0._down(vs[j], "same_claim_correct_and_incorrect")
                flags.append("contradictory_verdicts")
                break
    credited = {c for v in vs if v.state is _C for c in v.claim_ids}
    blamed = {c for v in vs if v.state is _X for c in v.claim_ids}
    if credited & blamed:
        flags.append("mixed_claim_correct_and_incorrect")
    on_topic = validated.on_topic
    if on_topic == "off_topic" and any(v.state is _C for v in vs):
        on_topic = "unclear"; flags.append("off_topic_contradicted_by_credit"); adj.append("on_topic off_topic -> unclear")
    rc = validated.reasoning_claim_ids
    if rc is not None:
        rc = tuple(i for i in rc if i not in blamed)
    return C0.Consistent(tuple(vs), on_topic, rc, tuple(dict.fromkeys(flags)), tuple(adj))


@contextlib.contextmanager
def use_v31():
    """Temporarily route the pipeline through the 3c1.1 corrections (process-local, restored on exit)."""
    old_check, old_stems = C0.check, V0.content_stems
    C0.check, V0.content_stems = check_v31, content_stems_v31
    try:
        yield VARIANT
    finally:
        C0.check, V0.content_stems = old_check, old_stems


def evaluate_v31(evaluator, *args, **kwargs):
    """Run evaluator.evaluate under 3c1.1 and stamp the variant into provenance so the result can never be mistaken for a 3c1.0 result."""
    with use_v31():
        res = evaluator.evaluate(*args, **kwargs)
    res.provenance["engine_variant"] = VARIANT
    return res
