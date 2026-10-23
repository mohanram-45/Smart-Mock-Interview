"""The ONLY module of the demo layer that touches the experimental modular evaluator (a narrow, test-enforced exemption of the "application code must not import the
modular package" guard). Everything is imported lazily, so a session that never asks for experimental evaluation never loads it.

Modes:   mock   LexicalMockVerifier: a rule-based test double. Shows the pipeline; says NOTHING about answer quality.
         live   QwenConceptVerifier over the LOCAL Ollama server (frozen target qwen2.5:7b, no paid API, no download). Same adapter that produced the recorded 3C-2 run.
Engine:  3c4.0 variant (opt-in, versioned; the frozen 3c1.0 modules remain the default and are untouched). Scores are labelled with the variant and are never fed to
         adaptive difficulty.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
MODES = ("off", "mock", "live")
_lock = threading.Lock()
_store = None


def live_enabled() -> bool:
    return os.environ.get("SMART_DEMO_LIVE_MODULAR", "").strip().lower() in ("1", "true", "yes", "on")


def available_modes() -> List[str]:
    return ["off", "mock"] + (["live"] if live_enabled() else [])


def scope_store():
    global _store
    with _lock:
        if _store is None:
            from src.evaluation.modular import ScopeStore
            _store = ScopeStore.load()
        return _store


def concept_catalog(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Curated requirements (ids E1, G1, ...) for a question from the scope sidecar: [{id, label, tier, members}]. Empty when there is no scope record."""
    from src.evaluation.modular.review.views import requirement_view
    rv = requirement_view(scope_store(), record["question_id"], record["question"])
    if not rv.get("available"):
        return []
    return [{"id": r["id"], "label": r["label"], "tier": r["tier"], "members": list(r["members"])} for r in rv["requirements"]][:8]


def is_scorable(question_id: str) -> bool:
    """True when the scope sidecar makes this question penalty-eligible (a numeric experimental score is possible). False -> ADVISORY ONLY (or no scope record)."""
    try:
        return bool(scope_store().get(question_id).penalty_eligible)
    except Exception:
        return False


def scorable_ids(question_ids) -> List[str]:
    return [q for q in question_ids if is_scorable(q)]


def _live_verifier():
    from src.evaluation.modular.qwen_verifier import QwenConceptVerifier
    from src.evaluation.providers.http import OllamaProvider
    host = (os.environ.get("SMART_DEMO_OLLAMA_HOST") or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").strip()
    if not host.startswith("http"):
        host = "http://" + host
    model = os.environ.get("SMART_DEMO_QWEN_MODEL", "qwen2.5:7b")
    # frozen 3C-2 settings: temperature 0, num_ctx 8192, 1800 output tokens, 300 s timeout
    return QwenConceptVerifier(OllamaProvider(model, host.rstrip("/"), 300, max_output_tokens=1800, num_ctx=8192, temperature=0.0, seed=7))


def make_verifier(mode: str):
    if mode == "mock":
        from src.evaluation.modular.mock_verifiers import LexicalMockVerifier
        return LexicalMockVerifier()
    if mode == "live":
        if not live_enabled():
            raise RuntimeError("live modular evaluation is not enabled (set SMART_DEMO_LIVE_MODULAR=1 and run Ollama locally)")
        return _live_verifier()
    raise ValueError(f"unknown modular mode {mode!r}")


class ProviderCircuitBreaker:
    """Stage 8B: after `threshold` consecutive provider failures the LIVE evaluator is skipped for `cooldown_s`, so a stopped local model server does not make every queued
    answer wait out its full timeout (300 s each). One probe call is allowed after the cool-down; success closes the breaker. Counts connectivity failures only."""

    def __init__(self, threshold: int = 2, cooldown_s: float = 60.0, clock=time.monotonic):
        self.threshold, self.cooldown_s, self._clock = int(threshold), float(cooldown_s), clock
        self._fails, self._opened_at, self._lock = 0, None, threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if self._clock() - self._opened_at >= self.cooldown_s:
                self._opened_at = self._clock()        # half-open: let ONE probe through, re-arm the timer so concurrent callers still wait
                return True
            return False

    def record(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self._fails, self._opened_at = 0, None
                return
            self._fails += 1
            if self._fails >= self.threshold:
                self._opened_at = self._clock()

    @property
    def is_open(self) -> bool:
        with self._lock:
            return self._opened_at is not None


_breaker = ProviderCircuitBreaker()


def breaker() -> ProviderCircuitBreaker:
    return _breaker


def _unavailable_view(mode: str, answer: str, code: str, message: str) -> Dict[str, Any]:
    return {"status": "provider_error", "score": None, "score_range": None, "mode": mode, "answer": answer, "error": {"code": code, "message": message[:300]},
            "source": {"kind": "UNAVAILABLE", "tags": ["UNAVAILABLE"], "text": "The experimental evaluator could not run.", "human": "NOT human-validated", "caveat": ""},
            "dimensions": [], "verdicts": [], "claims": [], "outcomes": [], "flags": [], "uncertainty_flags": [], "abstain_reasons": [], "feedback": None,
            "taxonomy": {"primary": "provider_failure", "blockers": []}, "consistency": "not applicable (not human-verified)", "requirements": None, "variant": None, "engine": None,
            "reliability": None, "contradictions": {"status": "not_checked", "items": [], "rejected": [], "reason": "evaluator_did_not_run"}}


def _contradiction_pass(mode: str, v: Any, record: Dict[str, Any], view: Dict[str, Any], provider: Any = None) -> Dict[str, Any]:
    """Stage 12: one evidence-checked contradiction call (src/evaluation/modular/contradictions.py) over the claims the evaluator already split. Live mode reuses the
    verifier's own local-model provider; the mock verifier is a word-overlap test double, so it is never asked. Never raises."""
    from src.evaluation.modular import contradictions as CX
    try:
        if view.get("status") in ("provider_error", "invalid_response", "scope_unavailable", "not_gradable"):
            return CX.not_checked("evaluator_did_not_run")
        if (view.get("safeguards") or {}).get("applied"):
            return CX.not_checked("answer_safeguard_applied")
        claims = [{"id": c["id"], "text": c["text"]} for c in (view.get("claims") or []) if c.get("id") and c.get("text")]
        prov = provider if provider is not None else (getattr(v, "provider", None) if mode == "live" else None)
        if prov is None:
            return CX.not_checked("mock_verifier" if mode == "mock" else "no_model")
        return CX.check(prov, record["question"], record.get("canonical_answer") or "", claims)
    except Exception as e:                                           # the evaluation view stays valid without it
        return {**CX.not_checked("contradiction_pass_failed"), "status": "error", "error": type(e).__name__}


def evaluate(mode: str, record: Dict[str, Any], answer: str, *, verifier=None, contradiction_provider=None) -> Dict[str, Any]:
    """Run ONE answer through the 3c4.0 variant and return a plain, JSON-serialisable view. Never raises: a failure is returned as an 'unavailable' view with no score.

    Stage 8B: invisible characters are removed first (the displayed answer is that cleaned text; spaces, newlines and code formatting are untouched); a score is withheld
    for truncated answers and answers with a hidden instruction (src/evaluation/modular/safeguards.py); a live provider that keeps failing is skipped (circuit breaker)."""
    live = mode == "live" and verifier is None
    if live and not _breaker.allow():
        return _unavailable_view(mode, answer, "circuit_open", "The local model server failed repeatedly just now; live evaluation is paused for a minute. No score and no penalty.")
    try:
        from src.evaluation.modular import ModularEvaluator, ReferenceMaterial
        from src.evaluation.modular.feedback import build_feedback, feedback_payload
        from src.evaluation.modular.review.views import modular_view, requirement_view
        from src.evaluation.modular.safeguards import apply_safeguards, sanitise_answer
        from src.evaluation.modular.variant_3c4 import evaluate_3c4
        answer, san = sanitise_answer(answer)
        v = verifier if verifier is not None else make_verifier(mode)
        ev = ModularEvaluator(scope_store(), v, max_retries=1 if mode == "live" else 0)
        res = evaluate_3c4(ev, record["question_id"], record["question"], answer, ReferenceMaterial.from_corpus_record(record))
        res = apply_safeguards(res, answer)
        fb = build_feedback(feedback_payload(res)).__dict__
        trace = getattr(v, "trace", None)
        view = modular_view(res.to_dict(), fb, trace=trace)
        view["requirements"] = requirement_view(scope_store(), record["question_id"], record["question"])
        view["error"] = res.error
        view["answer"] = answer
        view["mode"] = mode
        view["safeguards"] = {**san, "applied": list((res.provenance.get("safeguards") or {}).get("applied", []))}
        for reason in view["safeguards"]["applied"]:
            if res.status.value == "abstained" and reason in res.abstain_reasons:
                view["taxonomy"] = {**(view.get("taxonomy") or {}), "primary": reason}
        view["contradictions"] = _contradiction_pass(mode, v, record, view, contradiction_provider)
        if live:
            _breaker.record(res.status.value != "provider_error")
        return view
    except Exception as e:                                           # the interview must survive any evaluator problem
        if live:
            _breaker.record(False)
        return _unavailable_view(mode, answer, type(e).__name__, str(e))


# ------------------------------------------------------------------------------------------------ presentation helpers (pure; used by templates)
_ABSTAIN_TEXT = {
    "off_topic_confirmed": "The answer was judged off-topic and shared almost no wording with the question, so no number is shown.",
    "model_uncertain": "The model could not decide on one or more required concepts, so no number is shown rather than guessing.",
    "evidence_gate": "The model's findings on one or more required concepts were rejected by the evidence checks (for example a claim that does not mention the concept), so no number is shown.",
    "mixed_model_and_gate": "Required concepts stayed undecided: the model was unsure about some and the evidence checks rejected its findings on others, so no number is shown.",
    "provider_failure": "The model service failed. No score and no penalty were produced.",
    "answer_truncated_not_fully_assessed": "The answer is longer than the evaluator reads (20,000 characters), so part of it was not assessed and no number is shown.",
    "possible_hidden_instruction": "The answer appears to contain an instruction aimed at the evaluator (possibly disguised with invisible or look-alike characters), so no number is shown.",
    "not_scored_by_design": "This question is not eligible for a numeric experimental score.",
    "undetermined_other": "The evidence did not determine every required rubric dimension, so no number is shown.",
}


def describe_state(view: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Which of the five demo situations is this? -> {state, title, text, css}. `state` is one of scored | advisory | abstained | unavailable | not_gradable | not_requested."""
    if not view:
        return {"state": "not_requested", "title": "Experimental evaluation not requested", "text": "Only the legacy score is shown. Experimental evaluation is opt-in.", "css": "muted"}
    st = view.get("status")
    if st == "scored":
        return {"state": "scored", "title": "Experimental score", "text": "Computed by fixed rules over evidence-checked findings. Not validated against human scores.", "css": "ok"}
    if st == "advisory_only":
        return {"state": "advisory", "title": "Advisory feedback only (no score by design)", "text": "This question has no penalty-eligible scope, so findings are shown without a number.", "css": "adv"}
    if st == "abstained":
        why = (view.get("taxonomy") or {}).get("primary", "undetermined_other")
        rng = view.get("score_range")
        extra = f" Informational range only (not a score): {rng[0]}-{rng[1]}." if rng else ""
        text = _ABSTAIN_TEXT.get(why, _ABSTAIN_TEXT["undetermined_other"])
        if "MOCK VERIFIER" in ((view.get("source") or {}).get("tags") or []):
            text = text.replace("The model", "The mock verifier (a simple word-overlap stand-in)").replace("the model", "the mock verifier")
        return {"state": "abstained", "title": "No score: the evaluator abstained", "text": text + extra, "css": "warn"}
    if st == "not_gradable":
        code = (view.get("error") or {}).get("code", "not_gradable")
        return {"state": "not_gradable", "title": "No score: answer not gradable", "text": f"The answer was not gradable ({code}); no model call was made.", "css": "warn"}
    if st in ("provider_error", "invalid_response", "scope_unavailable"):
        msg = (view.get("error") or {}).get("message", "")
        return {"state": "unavailable", "title": "Evaluation unavailable", "text": ("The evaluator did not return a usable result; no score and no penalty. " + msg).strip(), "css": "bad"}
    return {"state": "unavailable", "title": "Evaluation unavailable", "text": f"Unknown status {st!r}; no score shown.", "css": "bad"}


def highlight_html(view: Dict[str, Any], answer: Optional[str] = None) -> str:
    """The candidate's answer with the claims used as evidence marked (already HTML-escaped by the review renderer)."""
    from src.evaluation.modular.review.views import _highlight
    text = answer if answer is not None else view.get("answer", "")
    if not view.get("claims"):
        import html
        return html.escape(text)
    return _highlight(text, view)


def finding_label(cls: Optional[str]) -> str:
    from src.evaluation.modular.review.findings import LABELS
    return LABELS.get(cls or "", "")


# ------------------------------------------------------------------------------------------------ recorded real-model results (read-only)
def find_recorded_results() -> Optional[Path]:
    """The recorded REAL-model run to display: SMART_DEMO_RECORDED_RESULTS if set, else the newest COMPLETE (non-partial, non-dry) results.json."""
    env = os.environ.get("SMART_DEMO_RECORDED_RESULTS", "").strip()
    if env:
        p = Path(env)
        return p if p.is_file() else None
    base = ROOT / "data" / "evaluation" / "stage3c2_results"
    best = None
    for p in sorted(base.glob("*/results.json")) if base.is_dir() else []:
        try:
            meta = json.loads(p.read_text(encoding="utf-8")).get("meta", {})
        except Exception:
            continue
        if not meta.get("partial_run") and not meta.get("dry_run"):
            best = p
    return best


def recorded_views(path: Path) -> Dict[str, Any]:
    """Build the read-only views of a recorded run. The AI-authored expectations are deliberately NOT loaded (they are provisional and not ground truth)."""
    from src.evaluation.modular.review.recovery import load_results_tolerant
    from src.evaluation.modular.review.views import build_views
    doc, report = load_results_tolerant(Path(path))
    sample = {r["sample_id"]: r for r in map(json.loads, filter(None, (ROOT / "data/evaluation/stage3c2/sample.jsonl").read_text(encoding="utf-8").splitlines()))}
    views = build_views(doc, sample, scope_store(), None)
    return {"path": str(path), "views": views, "meta": doc.get("meta", {}), "load_report": report}
