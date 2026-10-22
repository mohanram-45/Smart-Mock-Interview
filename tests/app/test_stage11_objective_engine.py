"""Stage 11: the code-owned objective engine (flag `SMART_DEMO_FOLLOWUP_ENGINE=objective`). Offline/scripted: these tests prove decision, attribution and validation CODE and plumbing; they say
nothing about what a language model writes (no Ollama in the build sandbox). Recorded question texts below are the real llama3.2:3b replies from the Stage 10N benchmark, used as fixed inputs."""
import copy
import json
import re

import pytest

from src.demo import followup_llm as FL, intel, opportunity_eval as OE
from src.evaluation.providers.mock import MockProvider


@pytest.fixture(scope="module")
def eng():
    return OE.offline_engine()


@pytest.fixture(autouse=True)
def _vocab():
    FL.set_vocabulary_source(lambda: [])
    yield
    FL.set_vocabulary_source(None)


CASES = {c["id"]: c for c in OE.load()["cases"]}


def case(eng, id_, **over):
    c = copy.deepcopy(CASES[id_])
    c.update(over)
    return OE.build_case(eng, c)


def verdict(eng, id_, q, **over):
    ctx, offered, _s, _core = case(eng, id_, **over)
    obj = intel.plan_objective(ctx)
    assert obj is not None
    return intel.evaluate_question(q, ctx, obj), ctx, obj


# ------------------------------------------------------------------------------------------------ flag and baseline
def test_default_engine_is_the_stage10n_baseline(monkeypatch):
    monkeypatch.delenv(intel.ENV_ENGINE, raising=False)
    assert intel.engine_name() == "stage10n"
    for junk in ("", "Objective2", "true", "stage10n"):
        assert intel.engine_name(junk) == "stage10n"
    assert intel.engine_name("OBJECTIVE") == "objective"
    monkeypatch.setenv(intel.ENV_ENGINE, "objective")
    assert intel.engine_name() == "objective" and intel.engine_name("stage10n") == "stage10n"


def test_baseline_generator_keeps_prompt_10fu8_and_does_not_use_the_objective_path():
    g = FL.LLMFollowUpGenerator(MockProvider(lambda s, u: "{}"), deadline=5, engine="stage10n")
    assert g.engine == "stage10n" and FL.PROMPT_VERSION == "10.fu8"
    assert FL.describe()["engine"] in ("stage10n", "objective")


def test_baseline_validator_profile_is_unchanged_by_default():
    import inspect
    assert inspect.signature(FL.validate).parameters["profile"].default == "stage10n"


# ------------------------------------------------------------------------------------------------ the model never sees or owns a memory id
def test_prompt_has_no_memory_id_and_schema_is_question_only(eng):
    ctx, _o, _s, _c = case(eng, "M04")
    obj = intel.plan_objective(ctx)
    system, user, _ = intel.build_prompt(ctx, obj, "n0nce", "memory")
    assert set(intel.QUESTION_SCHEMA["properties"]) == {"question"}
    assert "memory_id" not in system + user and "decision" not in intel.QUESTION_SCHEMA["properties"]
    for m in ctx.memory:
        assert m["id"] not in user


def test_decision_is_made_by_code_open_concept_means_ask_covered_means_skip(eng):
    ctx, *_ = case(eng, "M04")
    assert intel.plan_objective(ctx) is not None
    full = copy.deepcopy(CASES["T01"])
    ctx2 = OE.build_case(eng, full)[0]
    assert (intel.plan_objective(ctx2) is None) == (not FL.open_concepts(ctx2))


# ------------------------------------------------------------------------------------------------ the five memory failures (M01, M03, M04, M05, M06)
def test_M04_memory_is_attached_by_code_when_the_question_really_uses_it(eng):
    # 11S: the question this test used ("How does atomicity in your money transfer handling ... relate to ensuring data consistency?") is now refused, and rightly: it places atomicity INSIDE their
    # system, which they never said, and revisits the one ACID property they did explain. The conditional form below claims nothing about their code and probes the property that is still open.
    q = "How would isolation change what two overlapping money transfers see in your billing database?"
    v, ctx, obj = verdict(eng, "M04", q)
    assert v.prop is not None and v.prop.memory_id == obj.memory["id"], v.reasons
    assert v.prop.validity["memory_attribution"].startswith("code")
    assert v.prop.memory_ref["quote"] if hasattr(v.prop, "memory_ref") and v.prop.memory_ref else True


def test_M05_memory_is_attached_by_code(eng):
    q = "How does the use of the sigmoid function in logistic regression relate to the concept of maximum likelihood estimation?"
    v, ctx, obj = verdict(eng, "M05", q)
    assert v.prop is not None and v.prop.memory_id == obj.memory["id"], v.reasons


@pytest.mark.parametrize("id_,q", [
    ("M01", "How would you evaluate the performance of your oral cancer classification model using PyTorch?"),
    ("M03", "How does pytest's mocking mechanism allow you to replace real objects in your Flask API tests with fake ones?"),
    ("M06", "How does the use of neural networks in your PyTorch project relate to the concept of deep learning?"),
])
def test_references_that_only_repeat_a_name_or_ignore_the_gap_are_rejected_not_cited(eng, id_, q):
    v, *_ = verdict(eng, id_, q)
    assert v.prop is None or v.prop.memory_id is None, "a superficial reference must never be credited as grounded memory"


def test_valid_question_without_memory_is_kept_but_is_not_memory_use(eng):
    q = "What does consistency mean for a transaction, and which part of ACID is responsible for it?"
    v, ctx, obj = verdict(eng, "M04", q)
    assert v.prop is not None and v.prop.memory_id is None, v.reasons


def test_model_cannot_vouch_for_a_citation_by_writing_an_id(eng):
    ctx, offered, *_ = case(eng, "M04")
    obj = intel.plan_objective(ctx)
    gen = FL.LLMFollowUpGenerator(MockProvider(lambda s, u: json.dumps({"question": "How does atomicity work?", "memory_id": offered[0]["id"], "decision": "ask"})), deadline=5, engine="objective")
    out = gen.propose(ctx)
    if out.proposal is not None and out.proposal.decision == "ask":
        assert out.proposal.memory_id is None


# ------------------------------------------------------------------------------------------------ unseen cross-turn scenarios (written after the rules; same author: sanity, not independent evidence)
UNSEEN = [
    ("M04", {"earlier": [{"turn": 1, "stage": "introduction", "answer": "I built a payments ledger on PostgreSQL where two transfers could touch the same account at once."}]},
     "In your payments ledger, what could go wrong if two transfers touching the same account ran at once without isolation?", True),
    ("M04", {"earlier": [{"turn": 1, "stage": "introduction", "answer": "I built a payments ledger on PostgreSQL where two transfers could touch the same account at once."}]},
     "Tell me more about your payments ledger on PostgreSQL.", False),
]


@pytest.mark.parametrize("id_,over,q,should_attribute", UNSEEN)
def test_unseen_cross_turn_attribution(eng, id_, over, q, should_attribute):
    v, ctx, obj = verdict(eng, id_, q, **over)
    got = bool(v.prop is not None and v.prop.memory_id)
    if should_attribute:
        assert got and v.prop.memory_id == obj.memory["id"], v.reasons
    else:
        assert not got, "a tautological question that only repeats the project is not memory use"


def test_cross_session_memory_is_never_attributed(eng):
    ctx, *_ = case(eng, "M04")
    obj = intel.plan_objective(ctx)
    ctx.memory = [dict(m, id="m_other_session") for m in ctx.memory]
    q = "How does atomicity in your money transfer handling in PostgreSQL relate to ensuring data consistency in the database?"
    v = intel.evaluate_question(q, ctx, obj)
    assert v.prop is None or v.prop.memory_id in (None, obj.memory["id"] if obj.memory else None)


def test_tautology_is_flagged(eng):
    v, *_ = verdict(eng, "M04", "Can you tell me more about your money transfer handling in PostgreSQL?")
    assert v.prop is None or not v.prop.memory_id


# ------------------------------------------------------------------------------------------------ accepted-but-weak questions (T02, T04, T10, M07, N02 patterns; no case-ID logic in the code)
@pytest.mark.parametrize("id_,q,reason", [
    ("T02", "How does atomicity ensure that data remains consistent after a crash, and what happens to data that is partially written?", "ignores_objective"),
    ("T04", "How many filters does a typical convolutional layer use in a CNN?", "unanswerable_quantity"),
    ("T10", "How does cross-validation help evaluate the model's performance on classes with imbalanced data?", "revisits_explained_concept"),
    ("N02", "How does atomicity ensure that data is consistent across all nodes in a distributed system?", "ignores_objective"),
])
def test_recorded_weak_questions_are_rejected_for_the_right_reason(eng, id_, q, reason):
    v, *_ = verdict(eng, id_, q)
    assert v.prop is None and any(reason in r for r in v.reasons), v.reasons


def test_standalone_weak_pattern_checks_do_not_depend_on_case_ids():
    assert intel.unanswerable_quantity("How many filters does a typical convolutional layer use?")
    assert intel.unanswerable_quantity("How many hidden units should a usual network have?")
    assert not intel.unanswerable_quantity("How many comparisons does binary search need for n elements in the worst case?")
    assert not intel.unanswerable_quantity("How does a convolutional filter slide over an image?")


def test_valid_paraphrase_and_scenario_questions_survive(eng):
    v, *_ = verdict(eng, "T08", "How does logistic regression use the sigmoid function to transform the input features into a probability output?")
    assert v.prop is not None, v.reasons
    v, *_ = verdict(eng, "T03", "How does binary search compare to linear search in terms of the number of elements that need to be checked for a sorted list?")
    assert v.prop is not None, v.reasons


def test_word_overlap_with_the_topic_alone_is_not_gap_progression(eng):
    v, ctx, obj = verdict(eng, "T10", "What is cross-validation and why do we validate models?")
    assert v.prop is None


# ------------------------------------------------------------------------------------------------ plumbing: telemetry and provenance
def test_objective_outcome_is_labelled_and_schema_consistent(eng):
    ctx, *_ = case(eng, "T08")
    seen = []

    def reply(s, u):
        seen.append(u)
        return json.dumps({"question": "How does logistic regression use the sigmoid function to transform the input features into a probability output?"})
    gen = FL.LLMFollowUpGenerator(MockProvider(reply), deadline=5, engine="objective")
    out = gen.propose(ctx)
    assert out.prompt_version == intel.OBJ_PROMPT_VERSION and out.info.get("engine") == "objective"
    assert out.kind in ("mock", "llm", "fallback", "skip")
    assert len(seen) <= 2, "at most two bounded model calls"


def test_objective_engine_falls_back_on_garbage_and_never_raises(eng):
    ctx, *_ = case(eng, "M04")
    for text in ("not json", "{}", json.dumps({"question": ""}), json.dumps({"question": 5})):
        gen = FL.LLMFollowUpGenerator(MockProvider(lambda s, u, t=text: t), deadline=5, engine="objective")
        out = gen.propose(ctx)
        assert out.kind in ("fallback", "skip") or out.proposal is not None


def test_repair_keeps_the_memory_objective_after_a_missing_citation(eng):
    ctx, *_ = case(eng, "M04")
    modes, replies = [], iter(["Tell me about databases.",
                                "How does atomicity in your money transfer handling in PostgreSQL relate to ensuring data consistency in the database?"])

    def reply(s, u):
        modes.append("EARLIER" in u)
        return json.dumps({"question": next(replies)})
    gen = FL.LLMFollowUpGenerator(MockProvider(reply), deadline=30, engine="objective")
    out = gen.propose(ctx)
    assert modes and all(modes), "the repair attempt still carries the earlier statement (Stage 10N switched to standard mode here)"


# ------------------------------------------------------------------------------------------------ the real interview journey (Flask + DemoEngine) with the objective engine
def test_generator_cache_is_keyed_by_engine(monkeypatch):
    monkeypatch.setenv("SMART_DEMO_LIVE_MODULAR", "1")
    monkeypatch.setattr(FL, "_generators", {})
    seen = {}
    monkeypatch.setattr(FL, "LLMFollowUpGenerator", lambda prov, **kw: object())
    import src.demo.ollama_stream as OS
    monkeypatch.setattr(OS, "StreamingOllama", lambda *a, **k: object())
    monkeypatch.delenv(intel.ENV_ENGINE, raising=False)
    a = FL.make_generator("live")
    monkeypatch.setenv(intel.ENV_ENGINE, "objective")
    b = FL.make_generator("live")
    assert a is not b and len(FL._generators) == 2


def test_full_flask_journey_with_the_objective_engine_labels_provenance_and_finishes(app_module, tmp_path, monkeypatch):
    from src.demo.routes import set_engine
    from tests.app.test_stage4a_demo import make_engine
    from tests.app.test_stage9b_interview import create, play
    for v in ("SMART_DEMO_LIVE_MODULAR", "SMART_DEMO_CODE_EVAL", "SMART_CODEEVAL_EXEC"):
        monkeypatch.delenv(v, raising=False)
    e = make_engine(tmp_path)
    # The stand-in answers whatever the prompt says the objective is, so this stays a test of the plumbing (provenance labels, persistence, the interview finishing) and not of one fixed wording.
    def on_objective(system, user):
        target = re.search(r"^TARGET \(not covered yet\): (.+)$", user, re.M)
        return json.dumps({"question": f"How would {target.group(1) if target else 'that'} change what you would look at here?"})
    e._followup_generator = FL.LLMFollowUpGenerator(MockProvider(on_objective), deadline=5, engine="objective")
    set_engine(e)
    app_module.app.config["TESTING"] = True
    try:
        with app_module.app.test_client() as c:
            sid = create(c, followup_mode="mock")
            s = play(c, e, sid)
    finally:
        set_engine(None)
    assert s["status"] == "finished"
    labelled = [q for q in s["questions"] if q.get("followup_kind") in ("llm", "mock")]
    assert labelled, "at least one model-written follow-up reached the interview"
    for q in labelled:
        assert q["provenance"].get("engine") == "objective"


# ------------------------------------------------------------------------------------------------ comparison tooling
def _run_script(*args):
    import subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    return subprocess.run([sys.executable, "-I", *args], capture_output=True, text=True, timeout=180, cwd=root)


def test_compare_refuses_to_treat_selftest_data_as_evidence_and_builds_a_blind_unrated_pack(tmp_path):
    for eng in ("stage10n", "objective"):
        p = _run_script("scripts/stage10_verify_real_stack.py", "--selftest", "--opportunities", "--engine", eng, "--out", str(tmp_path / eng))
        assert p.returncode == 0, p.stderr[-400:]
    c = _run_script("scripts/stage11_compare.py", "--runs", str(tmp_path / "stage10n/results.json"), str(tmp_path / "objective/results.json"), "--out", str(tmp_path / "cmp"))
    assert c.returncode == 0, c.stderr[-400:]
    doc = json.loads((tmp_path / "cmp/comparison.json").read_text(encoding="utf-8"))
    assert all("NOT EVALUABLE" in d["decision"] for d in doc["decisions"])
    sheet = (tmp_path / "cmp/human_review_pack/review_sheet.csv").read_text(encoding="utf-8")
    assert "objective" not in sheet and "stage10n" not in sheet, "engine identity stays in key.json"
    assert doc["human_pack"]["rated"] is False


def test_gates_require_every_condition_including_rated_human_review():
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location("s11c", pathlib.Path(__file__).resolve().parents[2] / "scripts/stage11_compare.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    base = {"technical": [7, 12], "memory_grounded": [2, 7], "fabricated": 0, "strict_skip": [10, 10], "inconsistent_payload_rows": 7, "fallbacks": 9, "success": 13, "median_warm_ms": 1000}
    new = dict(base, technical=[9, 12], memory_grounded=[5, 7], inconsistent_payload_rows=0, fallbacks=4, success=17, median_warm_ms=1100)
    g = dict(m.gates(base, new, None))
    assert all(v for k, v in g.items() if k != "G9") and g["G9"] is False
    assert all(dict(m.gates(base, new, {"not_worse": True})).values())
    assert dict(m.gates(base, dict(new, fabricated=1), {"not_worse": True}))["G3"] is False
    assert dict(m.gates(base, dict(new, memory_grounded=[3, 7]), {"not_worse": True}))["G2"] is False
