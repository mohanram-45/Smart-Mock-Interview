"""Interview engine for the demo: sessions, question selection, answer handling, three independent evaluation layers.

Design rules (each is tested):
  * the interview FLOW never depends on any evaluator: a scorer that fails to load, a modular error or an Ollama outage only changes what is shown next to the answer
  * Sentence-BERT is the ONLY similarity scorer for new interviews (Stage 9B); if it cannot load, the similarity is reported unavailable. There is no silent switch to
    another scorer. The older Bi-LSTM and TF-IDF scorers stay in the repository (model_registry) for stored sessions, checkpoints and historical tests only
  * an interview is a conversation planned by `interview.py` (introduction, technical questions, deterministic follow-ups, a practical exercise, wrap-up). Experimental modular
    evaluation is opt-in per session and is never fed back into question selection (Stage 10: the NEXT technical question is chosen by `policy.py` from answer-evidence signals; modular evaluation still never feeds it)
  * a result is stored with its source labels; an abstention keeps its reason; an advisory-only question never receives a number
  * a duplicate / out-of-order submission is rejected without changing state
"""
from __future__ import annotations

import logging
import random
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import behavioural as B, catalog, codeassess as CA, experimental as MA, followup_llm as FL, insights, interview as I, memory as MEM, policy as POL
from .store import DemoStore, new_id
from ..mlops.metrics import inc as _inc
from ..mlops.metrics import observe as _observe

logger = logging.getLogger(__name__)
MAX_ANSWER_CHARS = 8000
SCORER_KEY = "bert"            # Sentence-BERT (all-MiniLM-L6-v2): the only similarity scorer new interviews use
_UNSET = object()
ROOT = Path(__file__).resolve().parents[2]


def _record_modular_outcome(view: Any) -> None:
    """Count an experimental evaluation by outcome only (scored / abstained / other). Never reads or stores answer text."""
    try:
        st = (view or {}).get("status")
        outcome = st if st in ("scored", "abstained", "provider_error", "advisory") else "other"
        _inc("smart_experimental_evaluations_total", outcome=outcome)
        if st == "abstained":
            _inc("smart_experimental_abstentions_total")
    except Exception:
        pass


_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_answer(text: Any) -> Any:
    """Remove control characters (NUL etc.; keep tab/newline/carriage return) so an 'answer' of invisible bytes is empty, not scoreable."""
    return _CTRL.sub("", text) if isinstance(text, str) else text


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DemoError(Exception):
    """An expected, user-presentable failure. `status` is the HTTP status the route should use."""
    def __init__(self, message: str, status: int = 400, **extra):
        super().__init__(message)
        self.status, self.extra = status, extra


# ------------------------------------------------------------------------------------------------ legacy scoring (the app's existing scorers)
def _legacy_scorer(model_key: str, corpus: List[str]):
    for p in (ROOT / "src" / "model", ROOT / "src" / "components"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    from model_registry import get_scorer
    return get_scorer(model_key, corpus=corpus)


def _legacy_feedback(similarity: float, question: str, answer: str, model_key: str) -> str:
    for p in (ROOT / "src" / "components",):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    from feedback_generator import FeedbackGenerator
    return FeedbackGenerator().generate(similarity_score=similarity, question=question, user_answer=answer, model_choice=model_key)


def legacy_models(readiness_fn: Optional[Callable[[str], Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """The scorers new interviews may use: Sentence-BERT only. (`model_registry` still lists the older scorers; they are filtered out here on purpose.)"""
    for p in (ROOT / "src" / "model",):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    from model_registry import list_models
    models = [m for m in list_models() if m["key"] == SCORER_KEY]
    for m in models:
        m.update((readiness_fn or _readiness)(m["key"]))
        m.update(default=True, configured_default=True)
    return models


def _readiness(model_key: str) -> Dict[str, Any]:
    for p in (ROOT / "src" / "model",):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    try:
        from model_registry import readiness
        r = readiness(model_key)
    except Exception as e:                                                       # a broken probe must not break the page
        r = {"ready": False, "reason": f"Could not check this scorer ({type(e).__name__}).", "hint": None}
    return {"ready": bool(r["ready"]), "not_ready_reason": r.get("reason"), "setup_hint": r.get("hint")}


def allow_scorer_setup() -> bool:
    """SMART_DEMO_ALLOW_SCORER_SETUP=1 lets the demo train / download a missing scorer on first use (the legacy /api routes always did)."""
    import os
    return os.environ.get("SMART_DEMO_ALLOW_SCORER_SETUP", "").strip().lower() in ("1", "true", "yes", "on")


def _service_search(query: str, domain: str) -> Dict[str, Any]:
    from src.retrieval.service import get_service
    return get_service().search(query, k=40, domain=domain)


def retrieval_summary(diag: List[Dict[str, Any]], hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Counts and gate names for one retrieval: enough to tell a retrieval failure from a generation failure, never any candidate text."""
    gates: Dict[str, int] = {}
    for d in diag:
        g = str(d.get("gate") or d.get("stage") or "?")
        gates[g] = gates.get(g, 0) + 1
    return {"offered": len(hits), "kinds": [h["item"]["kind"] for h in hits], "reasons": [h.get("reason") for h in hits], "gates": gates}


def _memory_is_current(session: Dict[str, Any], mid: str, ctx: "FL.Context") -> bool:
    it = MEM.get(session.get("memory") or {}, mid)
    return bool(it is not None and any(m["id"] == mid for m in ctx.memory) and it["turn"] <= len(session.get("answers") or []) and not it.get("deleted"))


class DemoEngine:
    def __init__(self, store: Optional[DemoStore] = None, *, records_fn: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                 scorer_factory: Callable[[str, List[str]], Any] = _legacy_scorer, feedback_fn: Callable[..., str] = _legacy_feedback,
                 modular_evaluate: Callable[..., Dict[str, Any]] = MA.evaluate, executor=None, rng: Optional[random.Random] = None,
                 readiness_fn: Optional[Callable[[str], Dict[str, Any]]] = None, search_fn: Any = _UNSET, followup_generator: Any = None):
        self.store = store or DemoStore()
        self._records_fn = records_fn
        self._scorer_factory, self._feedback_fn, self._modular_evaluate = scorer_factory, feedback_fn, modular_evaluate
        self._executor = executor                      # None -> one background worker for LIVE jobs (a 4 GB GPU runs one model call at a time)
        self._executor_lock = threading.Lock()
        self._scorers: Dict[str, Any] = {}
        self._load_lock = threading.Lock()             # one scorer load at a time (a second request waits instead of loading the model twice)
        self._session_locks: Dict[str, threading.Lock] = {}
        self._session_locks_guard = threading.Lock()
        if readiness_fn is None and scorer_factory is not _legacy_scorer:
            readiness_fn = lambda key: {"ready": True, "not_ready_reason": None, "setup_hint": None}      # an injected scorer (tests, embedding apps) manages its own readiness
        self._readiness_fn = readiness_fn
        self._rng = rng
        self._followup_generator = followup_generator        # tests / embedding apps: an object with propose(ctx) -> Outcome, used for every non-deterministic mode
        # Retrieval ranking (MiniLM + FAISS, BM25 fallback) of candidate questions. Only the real curated corpus uses the process-wide service; an engine built with its own
        # records (tests, embedding apps) has no ranking unless it passes search_fn explicitly.
        self._search_fn = (_service_search if records_fn is None else None) if search_fn is _UNSET else search_fn
        self._by_id: Optional[Dict[str, Dict[str, Any]]] = None

    # ------------------------------------------------------------------------------------------- data
    def legacy_models(self) -> List[Dict[str, Any]]:
        return legacy_models(self._readiness_fn)

    def _lock_for(self, sid: str) -> threading.Lock:
        """One lock per session: a slow scorer in one interview never blocks another, and two submits of the same question can never both be scored."""
        with self._session_locks_guard:
            if len(self._session_locks) > 1000:
                self._session_locks = {k: v for k, v in self._session_locks.items() if v.locked()}
            return self._session_locks.setdefault(sid, threading.Lock())

    def records(self) -> List[Dict[str, Any]]:
        if self._records_fn is not None:
            return self._records_fn()
        from src.retrieval.service import CorpusUnavailable, get_service
        try:
            return get_service().records()
        except CorpusUnavailable as e:
            _inc("smart_retrieval_failures_total", kind="corpus_unavailable", surface="demo")
            raise DemoError(str(e), 503, question_source="curated")

    def record(self, qid: str) -> Optional[Dict[str, Any]]:
        if self._by_id is None or qid not in self._by_id:
            self._by_id = {r["question_id"]: r for r in self.records()}
        return self._by_id.get(qid)

    def expose_reference(self) -> bool:
        import os
        return os.environ.get("SMART_RETRIEVAL_EXPOSE_REFERENCE", "").strip().lower() in ("1", "true", "yes", "on")

    def status(self) -> Dict[str, Any]:
        rec = MA.find_recorded_results()
        try:
            n = len(self.records()); err = None
        except DemoError as e:
            n, err = 0, str(e)
        return {"questions": n, "corpus_error": err, "modular_modes": MA.available_modes(), "followup_modes": ["deterministic"] + [m for m in FL.available_modes() if m != "deterministic"], "followup_model": FL.model_name() if FL.live_enabled() else None, "recorded_results": bool(rec), "legacy_models": self.legacy_models()}

    def catalog(self) -> Dict[str, Any]:
        recs = self.records()
        return {"roles": catalog.supported_roles(recs), "domains": catalog.domain_counts(recs), "legacy_models": self.legacy_models(), "modular_modes": MA.available_modes(), "followup_modes": ["deterministic"] + [m for m in FL.available_modes() if m != "deterministic"],
                "code_eval": CA.describe(), "total_questions": len(recs), "jd_max_chars": I.JD_MAX_CHARS, "core_questions": I.CORE_COUNT}

    def digests(self) -> List[Dict[str, Any]]:
        """Numbers-only digests of every saved interview (no question or answer text), newest first."""
        return [insights.digest(s) for s in self.store.all_sessions()]

    def scorable_info(self) -> Dict[str, Any]:
        """How many questions can receive a numeric experimental score. Loads the scope sidecar (and so the modular package), hence a separate, on-demand call:
        the default (legacy-only) flow never triggers it."""
        recs = self.records()
        return {"scorable_questions": len(MA.scorable_ids([r["question_id"] for r in recs])), "total_questions": len(recs)}

    # ------------------------------------------------------------------------------------------- sessions
    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Start an interview: role (+ optional job description) in, a planned conversation out. Difficulty, length and scorer are NOT candidate choices any more."""
        if not isinstance(payload, dict):
            raise DemoError("JSON object body required")
        recs = self.records()
        model = payload.get("legacy_model")
        if model not in (None, "", SCORER_KEY):
            raise DemoError("Sentence-BERT is the only similarity scorer for new interviews.", 400)
        mode = payload.get("modular_mode", "off")
        if mode not in MA.MODES:
            raise DemoError(f"modular_mode must be one of {list(MA.MODES)}")
        if mode not in MA.available_modes():
            raise DemoError(f"modular_mode '{mode}' is not enabled on this server", 400)
        fmode = payload.get("followup_mode", "deterministic")
        if fmode not in FL.MODES:
            raise DemoError(f"followup_mode must be one of {list(FL.MODES)}")
        if fmode != "deterministic" and self._followup_generator is None and fmode not in FL.available_modes():
            raise DemoError(f"followup_mode '{fmode}' is not enabled on this server", 400)
        itype = payload.get("interview_type", "technical")
        if itype not in B.INTERVIEW_TYPES:
            raise DemoError(f"interview_type must be one of {list(B.INTERVIEW_TYPES)}")
        adaptive = payload.get("adaptive", True)
        if not isinstance(adaptive, bool):
            raise DemoError("adaptive must be true or false")
        tb = payload.get("time_budget_min")
        if tb is not None and (not isinstance(tb, int) or isinstance(tb, bool) or not 1 <= tb <= 240):
            raise DemoError("time_budget_min must be a whole number between 1 and 240")
        code_eval = payload.get("code_eval", CA.enabled())
        if not isinstance(code_eval, bool):
            raise DemoError("code_eval must be true or false")
        if code_eval and not CA.enabled():
            raise DemoError("The experimental code check is not enabled on this server (set SMART_DEMO_CODE_EVAL=1).", 400)
        size = payload.get("size", I.CORE_COUNT)
        if not isinstance(size, int) or isinstance(size, bool) or not I.CORE_MIN <= size <= I.CORE_MAX:
            raise DemoError(f"size must be a whole number between {I.CORE_MIN} and {I.CORE_MAX}")
        practical, max_fu = payload.get("practical", True), payload.get("max_followups", I.MAX_FOLLOWUPS)
        if not isinstance(practical, bool):
            raise DemoError("practical must be true or false")
        if not isinstance(max_fu, int) or isinstance(max_fu, bool) or not 0 <= max_fu <= I.MAX_FOLLOWUPS:
            raise DemoError(f"max_followups must be a whole number between 0 and {I.MAX_FOLLOWUPS}")
        try:
            role = payload.get("role") or None
            domains = catalog.resolve_domains(recs, role, payload.get("domains") or None)
            if role and role not in catalog.supported_roles(recs):
                raise catalog.CatalogError(f"Unknown role: {role}")
            jd = I.sanitize_jd(payload.get("job_description"))
            pool_ids = [r["question_id"] for r in recs if r["domain"] in set(domains)]
            boost = MA.scorable_ids(pool_ids) if (bool(payload.get("prefer_scorable", False)) and mode != "off") else []
            pboost = [q for q in CA.spec_ids() if q in set(pool_ids)] if code_eval else []
            hints, rmeta = self._hints(role, domains, jd)
            rng = self._rng or random.Random()
            if itype == "behavioural":
                jd_info = ({"provided": True, "chars": jd["chars"], "matched_terms": B.jd_terms(jd["text"]), "text_stored": False, "redactions": jd["redactions"],
                            "injection_flagged": jd["injection_flagged"]} if jd else None)
                plan = {"items": [B.intro_item(role, bool(jd))] + B.plan_behavioural(role, jd["text"] if jd else None, B.N_BEHAVIOURAL, rng), "notes": [], "jd_info": jd_info, "pool_size": 0}
                if jd and jd["injection_flagged"]:
                    plan["notes"].append("The job description contained instruction-like text. It was ignored: job descriptions are only used to match topic keywords.")
            else:
                plan = I.plan_items(recs, domains, role, rng=rng, n_core=(B.N_MIXED_TECH if itype == "mixed" else size), jd=jd, hints=hints, retrieval_mode=rmeta["mode"], boost_ids=boost,
                                    practical_boost_ids=pboost, want_practical=practical and itype == "technical")
                if itype == "mixed":
                    plan["items"] += B.plan_behavioural(role, jd["text"] if jd else None, B.N_MIXED_BEH, rng)
        except (catalog.CatalogError, I.InputError) as e:
            raise DemoError(str(e))
        legacy = self._prepare_legacy(SCORER_KEY, [r["canonical_answer"] for r in recs if r["domain"] in set(domains)])
        items, first_core, k = plan["items"], True, 0
        kb, prev_st = 0, None
        for it in items:
            st = it["stage"]
            if st == I.BEHAVIOURAL:
                comp = B.competency(it["competency"])
                intro_t = B.transition_text("first") if prev_st == I.INTRO else B.transition_text("to_behavioural") if prev_st != I.BEHAVIOURAL else ""
                it["lead"] = (intro_t + " " + B.competency_lead(comp, kb)).strip()
                kb += 1
            else:
                it["lead"] = I.lead_in(it, k, first_core) if st != I.INTRO else ""
            prev_st = st
            if st == I.CORE:
                first_core, k = False, k + 1
            has_rec = bool(it.get("question_id")) and st in (I.CORE, I.PRACTICAL)
            it["scorable"] = MA.is_scorable(it["question_id"]) if (has_rec and mode != "off") else None
            it["code_spec"] = CA.has_spec(it["question_id"]) if (has_rec and code_eval) else None
        n_tech = sum(1 for it in items if I.is_question(it))
        has_practical = any(it["stage"] == I.PRACTICAL for it in items)
        n_beh = sum(1 for it in items if it["stage"] == I.BEHAVIOURAL)
        welcome = I.welcome_text(role, list(dict.fromkeys(it["domain"] for it in items if it["stage"] == I.CORE)), n_tech - (1 if has_practical else 0), has_practical, itype, n_beh)
        items[0]["lead"] = welcome
        s = {"id": new_id(), "created_at": now(), "status": "active", "finished_at": None,
             "config": {"role": role, "domains": domains, "difficulty": "Mixed", "size": size, "legacy_model": SCORER_KEY, "modular_mode": mode,
                        "prefer_scorable": bool(payload.get("prefer_scorable", False)), "code_eval": code_eval, "flow": "interview", "followup_mode": fmode, "interview_type": itype},
             "plan": {"flow": "interview", "core": sum(1 for it in items if it["stage"] == I.CORE), "practical": has_practical, "followups_used": 0, "followups_max": max_fu,
                      "consecutive_skips": 0, "type": itype, "adaptive": adaptive, "time_budget_s": (tb * 60 if tb else POL.DEFAULT_TIME_BUDGET_S), "behavioural": n_beh,
                      "versions": B.versions() if n_beh else None, "memory_ttl_days": MEM.DEFAULT_TTL_DAYS, "retrieval": rmeta, "jd": plan["jd_info"], "ended_reason": None},
             "notes": plan["notes"], "memory": MEM.new_memory(), "legacy": legacy, "questions": items, "answers": [None] * len(items), "current": 0, "q_started": now(),
             "script": {"welcome": welcome, "wrapup": I.wrapup_text(0, 0)}}
        self.store.put(s)
        self.store.save(s)
        _inc("smart_interviews_started_total", surface="demo")
        if fmode == "live":
            FL.prewarm(fmode, self._followup_generator)               # background model load; the interview never waits for it
        return s

    def _hints(self, role: Optional[str], domains: List[str], jd: Optional[Dict[str, Any]]):
        """Retrieval ranking of candidate questions: {question_id: (relevance 0..1, rank)} plus how it was obtained. It only ORDERS candidates; it never judges a candidate.
        A failure here changes nothing but the ordering, and the mode is recorded so the report can say what was (not) used."""
        fn = self._search_fn
        if fn is None:
            return {}, {"mode": "none", "reason": "retrieval ranking is not attached to this engine"}
        query = (jd["text"][:600] if jd else (role or " ".join(domains)))
        hints: Dict[str, Any] = {}
        modes, reason = set(), None
        for d in domains:
            try:
                res = fn(query, d)
            except Exception as e:                                                   # semantic stack broken or corpus problem: plan without ranking, say so
                logger.warning("retrieval ranking unavailable for %s: %s", d, e)
                modes.add("none"); reason = f"{type(e).__name__}: {str(e)[:120]}"
                continue
            modes.add(res.get("mode") or "none")
            reason = res.get("degraded_reason") or reason
            hits = res.get("results") or []
            for i, h in enumerate(hits):
                hints[h["question_id"]] = (round(1 - i / max(len(hits), 1), 3), i + 1)
        mode = "semantic" if modes == {"semantic"} else "bm25_fallback" if "bm25_fallback" in modes else "none"
        return hints, {"mode": mode, "reason": reason, "query_source": "job description (keywords)" if jd else "role name"}

    def _prepare_legacy(self, model: str, corpus: List[str]) -> Dict[str, Any]:
        meta = next(m for m in self.legacy_models() if m["key"] == model)
        info = {"model": model, "label": meta["label"], "available": True, "reason": None}
        if model not in self._scorers and not meta.get("ready", True) and not allow_scorer_setup():
            # Never train or download inside a web request. The interview still runs; the legacy score is simply unavailable, with the exact one-time fix.
            hint = f" To enable it: {meta['setup_hint']}." if meta.get("setup_hint") else ""
            info.update(available=False, reason=f"{meta['label']} is not set up on this machine. {meta.get('not_ready_reason') or ''}{hint} "
                                                 f"No other scorer is used instead. (Or set SMART_DEMO_ALLOW_SCORER_SETUP=1 to let the demo set it up.)".strip())
            _inc("smart_scorer_unavailable_total", scorer=model, reason="not_ready")
            return info
        try:
            with self._load_lock:
                if model not in self._scorers:
                    self._scorers[model] = self._scorer_factory(model, corpus)
        except Exception as e:                                                      # torch / model files / Java missing, training failure, ...
            logger.warning("legacy scorer %s unavailable: %s", model, e)
            _inc("smart_scorer_failures_total", scorer=model, stage="load")
            info.update(available=False, reason=f"{type(e).__name__}: {str(e)[:200]}")
        return info

    def _load_scorer(self, model: str, s: Dict[str, Any]):
        """Load a scorer that a stored session already declared available (same factory and corpus rule as at creation). Raises if it cannot load: the caller reports 'unavailable' with the reason."""
        recs = self.records()
        domains = set((s.get("config") or {}).get("domains") or [])
        corpus = [r["canonical_answer"] for r in recs if r["domain"] in domains]
        with self._load_lock:
            if model not in self._scorers:
                self._scorers[model] = self._scorer_factory(model, corpus)
        return self._scorers[model]

    def _session(self, sid: str) -> Dict[str, Any]:
        s = self.store.get(sid)
        if s is None:
            raise DemoError("This interview could not be found. It may have been deleted, or it is older than the retention period (14 days by default).", 404)
        return s

    def get(self, sid: str) -> Dict[str, Any]:
        return self._session(sid)

    # ------------------------------------------------------------------------------------------- answering
    def _check_turn(self, s: Dict[str, Any], n: Any) -> int:
        if s["status"] != "active":
            raise DemoError("This interview is already finished.", 409, finished=True)
        if not isinstance(n, int) or isinstance(n, bool) or n != s["current"] + 1:
            raise DemoError("That question is no longer the current one (already answered or out of order).", 409, current=s["current"] + 1)
        return n - 1

    @staticmethod
    def question_elapsed(s: Dict[str, Any]) -> Optional[int]:
        """Seconds since the current question was shown (None for sessions saved before timing existed). Wall-clock; callers cap it for statistics."""
        try:
            return max(0, int((datetime.now(timezone.utc) - datetime.fromisoformat(s["q_started"])).total_seconds()))
        except (KeyError, TypeError, ValueError):
            return None

    def submit(self, sid: str, n: Any, answer: Any) -> Dict[str, Any]:
        s = self._session(sid)
        answer = clean_answer(answer)
        with self._lock_for(sid):                                  # per-session: scoring happens outside the global store lock
            existing = self._replay(s, n, answer)
            if existing is not None:
                return existing                                    # same answer to the same question again (double click, retry after a lost response)
            i = self._check_turn(s, n)
            if not isinstance(answer, str) or not answer.strip():
                raise DemoError("Answer cannot be empty.")
            if len(answer) > MAX_ANSWER_CHARS:
                raise DemoError(f"Answer is too long (limit {MAX_ANSWER_CHARS} characters).", 413)
            q = s["questions"][i]
            scored = I.is_scored(q) and bool(q.get("question_id"))
            rec = self.record(q["question_id"]) if q.get("question_id") else None
            if scored and (rec is None or rec.get("question") != q["question"]):
                raise DemoError("The question bank changed since this interview started, so this question can no longer be scored. Start a new interview.", 409, stale=True)
            legacy = self._legacy_result(s, rec, answer) if scored else self._not_scored(q)
            mode = s["config"]["modular_mode"] if scored else "off"
            code_on = scored and bool(s["config"].get("code_eval")) and bool(q.get("code_spec"))
            try:
                code_async = bool(code_on and CA.sandboxed_runner())
            except Exception as e:                                                     # a broken code layer must never break the interview
                logger.warning("code runner lookup failed: %s", e); code_async = False
            a = {"n": n, "question_id": q.get("question_id"), "skipped": False, "answer": answer, "answered_at": now(), "elapsed_s": self.question_elapsed(s), "legacy": legacy,
                 "modular": {"mode": mode, "status": "not_requested" if mode == "off" else "pending", "view": None},
                 "code": {"status": ("pending" if code_async else "not_requested" if not code_on else "done"), "report": None, "requested": code_on}}
            if I.is_question(q) and rec is not None:
                a["terms"] = I.term_check(rec, answer)             # exact-word check against the curated key concepts (evidence for the report; not a grade)
            if code_on and not code_async:
                try:
                    a["code"]["report"] = CA.assess(q["question_id"], answer)         # static read only (fast, in-process: parses text, runs nothing)
                    _inc("smart_code_assessments_total", outcome="done")
                except Exception as e:
                    logger.warning("code assessment crashed: %s", e)
                    a["code"]["status"] = "failed"
                    _inc("smart_code_assessments_total", outcome="failed")
            _inc("smart_answers_submitted_total", surface="demo")
            with self.store.lock:
                s["answers"][i] = a
                plan = s.setdefault("plan", {})
                plan["consecutive_skips"] = 0
                for k_, v_ in MEM.update(s, n=n, answer=answer, q=q, record=rec).items():     # evidence-grounded memory (rules; never raises into the turn)
                    if v_ and k_ in ("added", "merged", "conflicts", "rejected"):
                        _inc("smart_memory_items_total", v_, outcome=k_)
                wants_fu = self._followup_wanted(s, i)
            self._link_memory_topics(s, n)                                                 # retrieval-derived topic pointers for this turn's new memory items (outside the global lock)
            proposed = self._llm_followup(s, i, rec, answer) if wants_fu else None      # slow part: outside the global store lock, bounded by a hard deadline
            with self.store.lock:
                self._maybe_follow_up(s, i, rec, answer, proposed)
                self._adapt(s, i, rec, answer, n)
                self._advance_locked(s)
        if mode != "off":
            self._start_modular(s, i, rec, answer, mode)
        if a["code"]["status"] == "pending":
            self._start_code(s, i, q["question_id"], answer)
        return a

    @staticmethod
    def _budget_spent(s: Dict[str, Any]) -> bool:
        """True once the interview's time budget is used up. 10N-repair: no follow-up (rule, memory or model) may be added then. A follow-up inserted after the budget ran out kept the interview
        'active' beyond its configured time, and the existing wrap-up only removed the planned questions, not the follow-up. Never raises: a clock problem means 'not spent'."""
        try:
            return POL.time_state(s) == "over"
        except Exception:
            return False

    def _followup_wanted(self, s: Dict[str, Any], i: int) -> bool:
        plan = s.get("plan") or {}
        if self._budget_spent(s):
            return False
        return plan.get("flow") == "interview" and I.followup_allowed(s["questions"], s["answers"], i) and int(plan.get("followups_used", 0)) < int(plan.get("followups_max", I.MAX_FOLLOWUPS))

    def _generator_for(self, mode: str):
        return self._followup_generator if self._followup_generator is not None else FL.make_generator(mode)

    def _llm_followup(self, s: Dict[str, Any], i: int, rec: Optional[Dict[str, Any]], answer: str) -> Optional[Dict[str, Any]]:
        """EXPERIMENTAL, opt-in. Returns {"item": follow-up item | None, "log": {...}} or None when the session uses the deterministic follow-ups. Never raises, never waits past the deadline."""
        mode = (s.get("config") or {}).get("followup_mode", "deterministic")
        if mode == "deterministic" or rec is None or I.stage_of(s["questions"][i]) != I.CORE:
            return None
        n = i + 1
        try:
            gen = self._generator_for(mode)
            qi = s["questions"][i]
            rdiag: List[Dict[str, Any]] = []
            hits = POL.retrieve_for_followup(s, qi, answer, n, rec, k=2, diag=rdiag)            # the ONE retrieval used by the benchmark too; vetted concepts and quotes are part of the query (10J)
            ctx = FL.build_context(s, i, rec, answer, memory=hits)
            out = gen.propose(ctx)
        except Exception as e:                                                                       # configuration problem, missing model package, anything
            logger.warning("follow-up generator failed: %s", type(e).__name__)
            return {"item": None, "log": {"n": n, "mode": mode, "outcome": "fallback", "reasons": [f"error:{type(e).__name__}"]}}
        prop = out.proposal
        opp = FL.opportunity_class(ctx)
        log = {"n": n, "mode": mode, "outcome": out.kind, "reasons": list(out.reasons), "latency_ms": round(out.latency_ms, 1), "model": out.model, "prompt_version": out.prompt_version,
               "opportunity": opp, "engine": (out.info or {}).get("engine", "stage10n"), "objective": (out.info or {}).get("objective"), "memory_offered": len(ctx.memory), "skip_reason": (prop.skip_reason if prop is not None and prop.decision == "skip" else None),
               "decided_by": (out.metrics or {}).get("decided_by", "model"), "attempts": int((out.metrics or {}).get("attempts", 1 if out.latency_ms else 0) or 0), "memory_cited": bool(prop is not None and prop.memory_id), "citation_dropped": bool(prop is not None and "memory:not_connected" in prop.notes),
               "memory_stage": (out.info or {}).get("memory_stage"), "fallback_class": (out.info or {}).get("fallback_class"), "mode_trace": list((out.info or {}).get("mode_trace") or []),
               "payload_notes": [x for x in (prop.notes if prop is not None else []) if x.startswith("payload:")],
               "retrieval": retrieval_summary(rdiag, hits),
               "metrics": {k: v for k, v in (out.metrics or {}).items() if isinstance(v, (int, float)) or k == "done_reason"}}
        _inc("smart_followups_total", mode=mode, outcome=out.kind)
        if out.kind != "fallback" or not any(r in ("model_warming", "model_unavailable", "circuit_open", "model_busy", "answer_unrelated_to_question", "answer_looks_like_instructions", "no_curated_concepts") for r in out.reasons):
            _inc("smart_followup_opportunities_total", mode=mode, cls=opp)                  # a call that really reached (or was meant for) the model
        if out.kind == "skip":
            _inc("smart_followup_skips_total", reason=log["skip_reason"] or "nothing_to_add", by=log["decided_by"])
        elif out.kind == "fallback" and out.reasons:
            first = str(out.reasons[0])
            _inc("smart_followup_rejections_total", reason=":".join(first.split(":")[:2]) if first.startswith(("question:", "memory:", "evidence:", "schema:", "concepts:", "self_report:")) else first)
        if log["attempts"] > 1:
            _inc("smart_followup_repairs_total", outcome="ok" if out.kind in ("llm", "mock", "skip") else "failed")
        _inc("smart_followup_memory_stage_total", stage=str(log.get("memory_stage") or "unknown"))
        if ctx.memory:
            if prop is not None and prop.memory_id:
                _inc("smart_followup_memory_citations_total", outcome="valid")
            elif log["citation_dropped"]:
                _inc("smart_followup_memory_citations_total", outcome="dropped")
            elif out.kind == "fallback" and any(str(r).startswith("memory:") for r in out.reasons):
                _inc("smart_followup_memory_citations_total", outcome="rejected")
        if out.latency_ms and out.kind in ("llm", "mock", "skip", "fallback") and out.model:
            _observe("smart_followup_latency_seconds", out.latency_ms / 1000.0, model=out.model, phase=("first_call" if not getattr(gen, "_seen_first_call", False) else "later_call"))
            try:
                gen._seen_first_call = True
            except Exception:
                pass
        if out.kind in ("llm", "mock") and out.proposal is not None:
            gate = FL.final_gate(prop, ctx) if out.kind == "llm" else []                    # 11R: the text about to be shown is checked once more; a model question that fails goes to the deterministic follow-up
            if gate:
                log["outcome"], log["reasons"], log["fallback_class"] = "fallback", gate, "wording_failed"
                _inc("smart_followup_rejections_total", reason=gate[0])
                return {"item": None, "log": log}
            if prop.memory_id and not _memory_is_current(s, prop.memory_id, ctx):          # the id must exist in THIS session's memory and be one that was offered; otherwise no lead-in is attached
                prop.memory_id, prop.lead = None, None
                log["memory_cited"], log["memory_stage"] = False, "citation_invalid"
                _inc("smart_followup_memory_stage_total", stage="citation_invalid")
            return {"item": FL.build_item(n, s["questions"][i], ctx, out), "log": log}
        return {"item": None, "log": log}

    def _maybe_follow_up(self, s: Dict[str, Any], i: int, rec: Optional[Dict[str, Any]], answer: str, proposed: Optional[Dict[str, Any]] = None) -> None:
        """After a technical answer, insert at most one follow-up right after it. `proposed` (experimental) wins when it produced a vetted question; a model 'skip' means no follow-up;
        any failure falls back to the deterministic bank-backed follow-up (interview.followup_item). Caller holds the store lock."""
        qs = s["questions"]
        plan = s.setdefault("plan", {})
        if plan.get("flow") != "interview" or not I.followup_allowed(qs, s["answers"], i):
            return
        if int(plan.get("followups_used", 0)) >= int(plan.get("followups_max", I.MAX_FOLLOWUPS)):
            return
        if self._budget_spent(s):                                                          # the budget decides before any follow-up source is consulted (rules, memory, model)
            plan["ended_reason"] = plan.get("ended_reason") or "time_budget"
            return
        if MEM.is_refusal(answer):                                                         # a candidate who declines is not pressed
            return
        fu = self._clarification_item(s, i)                                               # an unresolved contradiction outranks everything else
        skip_all = False
        if fu is None and proposed is not None:
            plan.setdefault("followup_log", []).append(proposed["log"])
            if proposed["item"] is not None:
                fu = proposed["item"]
                if fu.get("memory_id"):
                    MEM.mark_referenced(s, [fu["memory_id"]], i + 2)
            elif proposed["log"]["outcome"] == "skip":
                skip_all = True
        elif proposed is not None:
            plan.setdefault("followup_log", []).append(proposed["log"])
        if skip_all:
            return
        if fu is None:
            fu = self._memory_followup(s, i, rec, answer)
        if fu is None:
            fu = I.followup_item(i + 1, qs[i], rec, answer, used=int(plan.get("followups_used", 0)), limit=int(plan.get("followups_max", I.MAX_FOLLOWUPS)))
        if fu is None:
            return
        fu["lead"] = fu.get("lead") or I.lead_in(fu, 0)
        qs.insert(i + 1, fu); s["answers"].insert(i + 1, None)
        problems = I.check_sequence(qs)
        if problems:                                                                       # never leave an invalid sequence behind
            logger.error("follow-up rejected: %s", problems)
            qs.pop(i + 1); s["answers"].pop(i + 1)
            return
        plan["followups_used"] = int(plan.get("followups_used", 0)) + 1

    # ---------------------------------------------------------------------------------------------- Stage 10: memory-aware follow-ups, behavioural probes, adaptive policy
    def _link_memory_topics(self, s: Dict[str, Any], n: int) -> None:
        try:
            mem = MEM.ensure(s)
            todo = [it for it in mem["items"] if it["turn"] == n and it.get("topics") is None]
            if todo:
                MEM.link_topics(todo, self._search_fn, self.record, list((s.get("config") or {}).get("domains") or []))
        except Exception as e:                                                             # memory enrichment is optional
            logger.warning("memory topic linking failed: %s", type(e).__name__)

    def _insert_after(self, s: Dict[str, Any], i: int, item: Dict[str, Any]) -> bool:
        qs = s["questions"]
        qs.insert(i + 1, item); s["answers"].insert(i + 1, None)
        problems = I.check_sequence(qs)
        if problems:                                                                       # never leave an invalid sequence behind
            logger.error("inserted item rejected: %s", problems)
            qs.pop(i + 1); s["answers"].pop(i + 1)
            return False
        return True

    def _clarification_item(self, s: Dict[str, Any], i: int) -> Optional[Dict[str, Any]]:
        """A non-accusatory question that quotes BOTH of the candidate's statements when the memory holds an unresolved contradiction between them."""
        mem = MEM.ensure(s)
        for c in MEM.open_contradictions(mem):
            a, b = MEM.get(mem, c["a"]), MEM.get(mem, c["b"])
            if not a or not b or a["quote"] == b["quote"] or len(a["quote"]) > 160 or len(b["quote"]) > 160:
                continue
            text = f'Earlier you said "{a["quote"]}" and later you said "{b["quote"]}". Could you help me understand how those fit together?'
            if POL.verify_question(s, text, memory_ids=[a["id"], b["id"]], upto=i):
                continue
            c["clarified_turn"] = i + 1
            parent = s["questions"][i]
            root = parent if I.stage_of(parent) in (I.CORE, I.BEHAVIOURAL) else None
            base = {"question_id": parent.get("question_id"), "domain": parent.get("domain"), "difficulty": parent.get("difficulty"), "topic": parent.get("topic"), "question_type": "", "stage": I.FOLLOW_UP,
                    "origin": "memory_followup", "parent_n": i + 1, "scored": False, "scorable": None, "code_spec": None, "question": text, "followup_kind": "contradiction_clarification",
                    "competency": parent.get("competency") if I.stage_of(parent) == I.BEHAVIOURAL else None, "lead": "Thanks. I would like to make sure I understood you.",
                    "provenance": {"record_id": parent.get("question_id"), "source": "two statements from this interview, quoted exactly", "method": "deterministic: the memory holds two incompatible values for the same slot",
                                   "llm": False, "memory_ids": [a["id"], b["id"]], "claim_status": "candidate claims (not verified); this is a clarification, not an accusation"}}
            if root is None:
                return None
            return base
        return None

    def _memory_followup(self, s: Dict[str, Any], i: int, rec: Optional[Dict[str, Any]], answer: str) -> Optional[Dict[str, Any]]:
        q = s["questions"][i]
        if I.stage_of(q) != I.CORE or I.word_count(answer) < I.SHORT_ANSWER_WORDS or MEM.uncertainty_cues(answer):
            return None
        n = i + 1
        hits = POL.memory_relevance(s, POL.query_parts(q["question"], q.get("topic") or "", answer), n + 1, answered_turn=n, kinds=("project", "achievement", "challenge", "technology", "role"), target_topic=(q.get("domain"), q.get("topic")))
        if not hits:
            return None
        it = hits[0]["item"]
        text = POL.memory_followup_text(it, hits[0].get("theme"))
        if not text or POL.verify_question(s, text, memory_ids=[it["id"]], upto=i + 1):
            return None
        MEM.mark_referenced(s, [it["id"]], n + 1)
        return {"question_id": q.get("question_id"), "domain": q.get("domain"), "difficulty": q.get("difficulty"), "topic": q.get("topic"), "question_type": "", "stage": I.FOLLOW_UP,
                "origin": "memory_followup", "parent_n": n, "scored": False, "scorable": None, "code_spec": None, "question": text, "followup_kind": "memory", "memory_id": it["id"],
                "provenance": {"record_id": q.get("question_id"), "source": "something you said earlier in this interview, quoted from your own words",
                               "method": "deterministic template filled with the candidate's own stored words; relevance = " + str(hits[0].get("reason") or "text similarity to the current topic"), "llm": False,
                               "memory_ref": {"id": it["id"], "turn": it["turn"], "kind": it["kind"], "claim_status": "candidate claim (not verified)", "score": hits[0]["score"]}}}

    def _adapt(self, s: Dict[str, Any], i: int, rec: Optional[Dict[str, Any]], answer: str, n: int) -> None:
        """After every answer: time check, behavioural probe / memory-driven behavioural prompt, adaptive re-selection of the next technical question. Never raises into the turn. Caller holds the lock."""
        plan = s.setdefault("plan", {})
        if plan.get("flow") != "interview":
            return
        try:
            qs, ans = s["questions"], s["answers"]
            q = qs[i]
            st = I.stage_of(q)
            entry: Dict[str, Any] = {"n": n, "stage": st, "type": plan.get("type", "technical")}
            if st == I.CORE:
                sig = POL.signals(rec, answer)
                inserted = len(qs) > i + 1 and ans[i + 1] is None and qs[i + 1].get("followup_kind") == "contradiction_clarification"
                dec = POL.decide(s, i, sig, has_open_contradiction=inserted, revisit_available=False)
                rep = POL.apply_adaptation(self, s, i, rec, answer, n, dec)
                if rep.get("memory_ref") and dec["decision"] in ("explore_related", "deeper"):
                    dec = {**dec, "decision": "revisit", "reasons": dec["reasons"] + ["memory_reference"]}
                entry.update({"decision": dec["decision"], "reasons": dec["reasons"], "target": POL._DIFF[dec["step"]], "replaced": rep["replaced"], "memory_ref": rep["memory_ref"],
                              "truncated": rep["truncated"], "coverage_band": POL.band(sig)})
                if rep["truncated"]:
                    plan["ended_reason"] = "time_budget"
            else:
                ts = POL.time_state(s)
                remaining = [k for k in range(i + 1, len(qs)) if ans[k] is None and I.stage_of(qs[k]) in (I.CORE, I.BEHAVIOURAL, I.PRACTICAL)]
                if ts != "ok" and remaining:
                    rep = POL.apply_adaptation(self, s, i, rec, answer, n, {"decision": "wrapup", "step": 1, "reasons": [f"time:{ts}", "time_budget"], "keep_next": ts == "wrapping"})
                    entry.update({"decision": "wrapup", "reasons": ["time_budget"], "truncated": rep["truncated"]})
                    plan["ended_reason"] = "time_budget"
                else:
                    entry["decision"] = "continue"
            if st in (I.BEHAVIOURAL, I.FOLLOW_UP) and (q.get("competency") or st == I.BEHAVIOURAL):
                self._behavioural_probe(s, i, answer, n, entry)
            if plan.get("type") in ("behavioural", "mixed") and entry.get("decision") != "wrapup":
                mem_rep = B.adapt_next_behavioural(s, i, n)
                if mem_rep:
                    entry["memory_ref"] = mem_rep["memory_id"]
                    entry["decision"] = "revisit"
            POL.log(s, entry)
            _inc("smart_policy_decisions_total", decision=str(entry.get("decision") or "continue"))
            if entry.get("memory_ref"):
                _inc("smart_memory_references_total", kind="policy_lead")
            if entry.get("probe"):
                _inc("smart_behavioural_probes_total", kind=str(entry["probe"]).replace("behavioural_", ""))
        except Exception as e:                                                             # the policy is an aid: a bug must never block the interview
            logger.warning("adaptive policy failed: %s", type(e).__name__)
            s.setdefault("plan", {}).setdefault("policy_log", []).append({"n": n, "decision": "continue", "reasons": [f"error:{type(e).__name__}"]})

    def _behavioural_probe(self, s: Dict[str, Any], i: int, answer: str, n: int, entry: Dict[str, Any]) -> None:
        qs, ans = s["questions"], s["answers"]
        q = qs[i]
        root = i if I.stage_of(q) == I.BEHAVIOURAL else (q["parent_n"] - 1 if q.get("parent_n") else None)
        if root is None or I.stage_of(qs[root]) != I.BEHAVIOURAL:
            return
        if len(qs) > i + 1 and ans[i + 1] is None and I.stage_of(qs[i + 1]) == I.FOLLOW_UP:   # a follow-up (for example a clarification) is already queued right after this answer
            return
        group = [root] + [k for k, x in enumerate(qs) if I.stage_of(x) == I.FOLLOW_UP and x.get("parent_n") == root + 1 and x.get("competency")]
        texts = [ans[k]["answer"] for k in group if k < len(ans) and ans[k] and not ans[k]["skipped"]]
        ev = B.star_evidence(B.combine(texts), qs[root].get("competency"))
        used = [qs[k].get("followup_kind", "").replace("behavioural_", "") for k in group if k != root and qs[k].get("followup_kind", "").startswith("behavioural_")]
        c = self._clarification_item(s, i)
        seen_kinds = [x.get("followup_kind") for x in qs[:i + 1]]
        pr = None if c else B.probe_for(ev, competency_id=qs[root].get("competency"), probes_used=len(used), asked=used, answer=answer, rotation=0)
        if pr is not None:
            pr["text"] = B.competencies()["probes"][pr["kind"]][sum(1 for k in seen_kinds if k == f"behavioural_{pr['kind']}") % len(B.competencies()["probes"][pr["kind"]])]
        if c is not None:
            item = c
        elif pr is not None and int(s["plan"].get("beh_probes_total", 0)) < 4:
            item = B.probe_item(root + 1, qs[root], pr)
        else:
            entry["probe"] = None
            return
        if self._insert_after(s, i, item):
            s["plan"]["beh_probes_total"] = int(s["plan"].get("beh_probes_total", 0)) + (0 if c else 1)
            entry["probe"] = item.get("followup_kind")
            entry["decision"] = "clarify"
            entry.setdefault("reasons", []).append(pr["reason"].split("'")[1] if pr and "'" in pr["reason"] else "probe")

    def _advance_locked(self, s: Dict[str, Any], skipped: bool = False) -> None:
        """Move to the next item; finish the interview when the plan is exhausted or the stop rule fires. Caller holds the store lock."""
        s["current"] += 1
        s["q_started"] = now()
        plan = s.setdefault("plan", {})
        if s["current"] >= len(s["questions"]):
            plan["ended_reason"] = plan.get("ended_reason") or "plan_complete"
            self._finish_locked(s)
        elif skipped and plan.get("flow") == "interview" and int(plan.get("consecutive_skips", 0)) >= I.MAX_CONSECUTIVE_SKIPS:
            plan["ended_reason"] = "consecutive_skips"
            self._finish_locked(s)
        else:
            self.store.save(s)

    @staticmethod
    def _not_scored(q: Dict[str, Any]) -> Dict[str, Any]:
        st = I.stage_of(q)
        why = ("Introductions are not compared with a reference answer." if st == I.INTRO else
               "Behavioural answers are read for the evidence they contain, not compared with a reference answer." if st == I.BEHAVIOURAL or q.get("competency") else
               "Follow-up answers are not compared with a reference answer.")
        return {"status": "not_scored", "score": None, "feedback": "", "reason": why}

    def _replay(self, s: Dict[str, Any], n: Any, answer: Any) -> Optional[Dict[str, Any]]:
        """If question n was already answered with exactly this text, return the stored result instead of an error (idempotent submit)."""
        if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(s["answers"]):
            a = s["answers"][n - 1]
            if a and not a["skipped"] and isinstance(answer, str) and a["answer"] == answer:
                return {**a, "duplicate": True}
        return None

    def skip(self, sid: str, n: Any) -> Dict[str, Any]:
        s = self._session(sid)
        with self._lock_for(sid):
            if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(s["answers"]) and s["answers"][n - 1] and s["answers"][n - 1]["skipped"]:
                return {**s["answers"][n - 1], "duplicate": True}
            i = self._check_turn(s, n)
            a = {"n": n, "question_id": s["questions"][i].get("question_id"), "skipped": True, "answer": "", "answered_at": now(), "elapsed_s": self.question_elapsed(s),
                 "legacy": {"status": "skipped", "score": None, "feedback": "", "reason": "Question skipped"},
                 "modular": {"mode": s["config"]["modular_mode"], "status": "not_requested", "view": None},
                 "code": {"status": "not_requested", "report": None, "requested": False}}
            with self.store.lock:
                s["answers"][i] = a
                plan = s.setdefault("plan", {})
                MEM.update(s, n=n, answer="", q=s["questions"][i], record=self.record(s["questions"][i]["question_id"]) if s["questions"][i].get("question_id") else None, skipped=True)
                if I.is_question(s["questions"][i]):                                    # the stop rule counts skipped technical questions only
                    plan["consecutive_skips"] = int(plan.get("consecutive_skips", 0)) + 1
                self._advance_locked(s, skipped=True)
        return a

    def finish(self, sid: str) -> Dict[str, Any]:
        s = self._session(sid)
        with self._lock_for(sid):
            with self.store.lock:
                if s["status"] == "active":
                    s.setdefault("plan", {})["ended_reason"] = "ended_by_candidate"
                    self._finish_locked(s)
        return s

    def delete(self, sid: str) -> bool:
        """Erase one session (memory and disk). A model job still running for it finishes harmlessly into the discarded object."""
        with self._lock_for(sid):
            ok = self.store.delete(sid)
        if ok:
            _inc("smart_sessions_deleted_total")
        return ok

    def _finish_locked(self, s: Dict[str, Any]) -> None:
        s["status"] = "finished"
        _inc("smart_interviews_completed_total", surface="demo")
        s["finished_at"] = now()
        self.store.save(s)

    def _legacy_result(self, s: Dict[str, Any], rec: Dict[str, Any], answer: str) -> Dict[str, Any]:
        info = s["legacy"]
        if not info["available"]:
            return {"status": "unavailable", "score": None, "feedback": "", "reason": info["reason"], "model": info["model"], "label": info["label"]}
        try:
            scorer = self._scorers.get(info["model"])
            if scorer is None:                                       # 10M: the registry is per process. After a restart (or in a second worker) the session says "available" but nothing is loaded: load it now
                scorer = self._load_scorer(info["model"], s)
            sc = scorer.score(rec["canonical_answer"], answer)
            score = round(float(sc) * 100, 2)
            fb = self._feedback_fn(score, rec["question"], answer, info["model"])
            return {"status": "scored", "score": score, "feedback": fb, "reason": None, "model": info["model"], "label": info["label"]}
        except Exception as e:
            logger.warning("legacy scoring failed: %s", e)
            _inc("smart_scorer_failures_total", scorer=info["model"], stage="score")
            return {"status": "unavailable", "score": None, "feedback": "", "reason": f"{type(e).__name__}: {str(e)[:200]}", "model": info["model"], "label": info["label"]}

    # ------------------------------------------------------------------------------------------- experimental modular (opt-in)
    def _start_modular(self, s: Dict[str, Any], i: int, rec: Dict[str, Any], answer: str, mode: str) -> None:
        def job():
            try:
                view, status = self._modular_evaluate(mode, rec, answer), "done"
            except Exception as e:                                  # MA.evaluate never raises; an injected / future evaluator might. Never leave the answer "running".
                logger.warning("experimental evaluation crashed: %s", e)
                view, status = None, "failed"
                _inc("smart_experimental_evaluations_total", outcome="failed")
            with self.store.lock:
                m = s["answers"][i]["modular"]
                m["view"], m["status"] = view, status
                if status == "done":
                    _record_modular_outcome(view)
                if status == "failed":
                    m["error"] = "The experimental evaluator stopped unexpectedly."
                self.store.save(s)
        if mode == "live":
            with self._executor_lock:
                if self._executor is None:
                    self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="demo-live")
            self._executor.submit(job)
        else:
            (self._executor.submit(job).result() if self._executor is not None else job())

    def _start_code(self, s: Dict[str, Any], i: int, qid: str, answer: str) -> None:
        """Sandboxed behaviour tests can take seconds: run them off the request thread (one at a time). Static-only assessments never come here."""
        def job():
            try:
                report, status = CA.assess(qid, answer), "done"
            except Exception as e:
                logger.warning("code assessment crashed: %s", e)
                report, status = None, "failed"
            _inc("smart_code_assessments_total", outcome=status)
            with self.store.lock:
                c = s["answers"][i]["code"]
                c["report"], c["status"] = report, status
                self.store.save(s)
        with self._executor_lock:
            if getattr(self, "_code_executor", None) is None:
                self._code_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="demo-code")
        self._code_executor.submit(job)

    # ------------------------------------------------------------------------------------------- views
    def summary(self, s: Dict[str, Any]) -> Dict[str, Any]:
        """Counts are over TECHNICAL questions (core + practical). Introduction and follow-up turns are counted separately: they are conversation, not graded questions."""
        pairs = list(zip(s["questions"], s["answers"]))
        tech = [(q, a) for q, a in pairs if I.is_question(q)]
        ans = [a for _, a in tech if a]
        scored = [a["legacy"]["score"] for a in ans if a["legacy"]["status"] == "scored"]
        by_level: Dict[str, List[float]] = {}
        for q, a in tech:
            if a and a["legacy"]["status"] == "scored":
                by_level.setdefault(q["difficulty"], []).append(a["legacy"]["score"])
        every = [a for _, a in pairs if a]
        return {"asked": len(tech), "answered": sum(1 for a in ans if not a["skipped"]), "skipped": sum(1 for a in ans if a["skipped"]),
                "unanswered": sum(1 for _, a in tech if a is None), "legacy_scored": len(scored),
                "legacy_average": round(sum(scored) / len(scored), 1) if scored else None,
                "legacy_by_level": {k: round(sum(v) / len(v), 1) for k, v in by_level.items()},
                "followups": sum(1 for q, a in pairs if I.stage_of(q) == I.FOLLOW_UP and a and not a["skipped"]),
                "behavioural": sum(1 for q, a in pairs if I.stage_of(q) == I.BEHAVIOURAL and a and not a["skipped"]),
                "turns": sum(1 for a in every if not a["skipped"]),
                "modular_pending": sum(1 for a in every if a["modular"]["status"] == "pending"),
                "code_pending": sum(1 for a in every if (a.get("code") or {}).get("status") == "pending"),
                "code_checked": sum(1 for a in every if (a.get("code") or {}).get("requested") and (a.get("code") or {}).get("status") == "done")}
