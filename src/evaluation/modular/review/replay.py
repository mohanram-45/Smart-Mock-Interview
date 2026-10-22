"""Offline replay of RECORDED model output through the deterministic pipeline (no model call, no network).

Two uses:
  * reproducibility check: replaying a run with the frozen 3c1.0 code must reproduce every recorded status, score, verdict and flag. If it does, everything
    after the model (parse, gate, consistency, rubric) is deterministic and the recorded numbers follow from the recorded model text.
  * defect impact: replaying with a variant (3c1.1) shows exactly what a defect did, WITHOUT any new model call. A replay is a diagnostic about the post-model
    code; it is never a new experiment result, never an acceptance re-evaluation, and never evidence that a variant is better (the model text is the same,
    the answers are the same 20, and the frozen rule forbids re-scoring them after a change)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ...providers.base import LLMProvider, ProviderResponse
from .. import ModularEvaluator, ReferenceMaterial, ScopeStore
from ..qwen_verifier import QwenConceptVerifier
from ..variant_3c4 import use_3c4
from ..variant_v31 import use_v31


class ReplayProvider(LLMProvider):
    name = "replay_of_recorded_output"
    is_mock = True          # so a replayed result can never be mistaken for a live model result
    paid = False

    def __init__(self, raw_text: str, usage: Optional[Dict[str, Any]] = None, model: str = "recorded"):
        self.raw_text, self.usage, self.model = raw_text, dict(usage or {}), model

    def generate(self, system: str, user: str) -> ProviderResponse:
        return ProviderResponse(text=self.raw_text, model=self.model, usage=self.usage)


def replay_row(row: Dict[str, Any], question_id: str, question: str, answer: str, record: Dict[str, Any], store: ScopeStore, *, variant: Optional[str] = None) -> Dict[str, Any]:
    t = row["verifier_trace"][0]
    prov = ReplayProvider(t.get("raw", ""), t.get("usage"), model=row["result"]["provenance"].get("verifier_model", "recorded"))
    ev = ModularEvaluator(store, QwenConceptVerifier(prov), max_retries=0)
    ref = ReferenceMaterial.from_corpus_record(record)
    if variant == "3c1.1":
        with use_v31():
            res = ev.evaluate(question_id, question, answer, ref)
    elif variant == "3c4.0":
        with use_3c4():
            res = ev.evaluate(question_id, question, answer, ref)
    elif variant in (None, "3c1.0"):
        res = ev.evaluate(question_id, question, answer, ref)
    else:
        raise ValueError(f"unknown variant {variant!r}")
    return res.to_dict()


def _verdict_view(r: Dict[str, Any]) -> Dict[str, Any]:
    return {f"{v['requirement_id']}|{v['member']}": [v["state"], v.get("downgrade_reason")] for v in r.get("verdicts", [])}


def diff_results(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Differences that matter between two result dicts (timing and provenance excluded)."""
    out: Dict[str, Any] = {}
    for k in ("status", "score", "score_range", "confidence"):
        if a.get(k) != b.get(k):
            out[k] = [a.get(k), b.get(k)]
    va, vb = _verdict_view(a), _verdict_view(b)
    vd = {k: [va.get(k), vb.get(k)] for k in sorted(set(va) | set(vb)) if va.get(k) != vb.get(k)}
    if vd:
        out["verdicts"] = vd
    if sorted(a.get("flags", [])) != sorted(b.get("flags", [])):
        out["flags"] = [sorted(a.get("flags", [])), sorted(b.get("flags", []))]
    da = {d["name"]: d["level"] for d in a.get("dimensions", [])}; db = {d["name"]: d["level"] for d in b.get("dimensions", [])}
    if da != db:
        out["dimension_levels"] = [da, db]
    return out


def replay_run(doc: Dict[str, Any], sample: Dict[str, Dict[str, Any]], recs: Dict[str, Dict[str, Any]], store: ScopeStore, *, variant: Optional[str] = None) -> List[Dict[str, Any]]:
    """Replay every modular row of a results document; returns [{sample_id, repeat, recorded, replayed, diff}]."""
    rows = []
    for m in doc.get("modular", []):
        s = sample[m["sample_id"]]
        rep = replay_row(m, s["question_id"], s["question"], s["answer_text"], recs[s["question_id"]], store, variant=variant)
        rows.append({"sample_id": m["sample_id"], "repeat": m["repeat"], "recorded": m["result"], "replayed": rep, "diff": diff_results(m["result"], rep)})
    return rows
