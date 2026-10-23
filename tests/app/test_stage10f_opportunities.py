"""Stage 10F: the per-opportunity evaluation harness, the fixed test set, the faulty-model safety net and the regression guards. Scripted/mock: mechanics only, never model quality."""
import json
import random

import pytest

from src.demo import followup_llm as FL, interview as I, opportunity_eval as OE, sim

DATA = OE.load()


@pytest.fixture(scope="module")
def engine():
    return OE.offline_engine()


@pytest.fixture(scope="module")
def baseline(engine):
    return OE.run_all(engine, OE.scripted_generator(), DATA)


def test_the_fixed_set_covers_every_class_mode_and_answer_category():
    cases = DATA["cases"]
    assert {c["class"] for c in cases} == set(OE.CLASSES)
    assert {c["mode"] for c in cases} == {"technical", "behavioural"} and {i["mode"] for i in DATA["interviews"]} == {"technical", "behavioural", "mixed"}
    cats = {c["category"] for c in cases}
    assert {"correct", "incorrect", "partial", "short_correct", "alternate_valid", "irrelevant", "adversarial", "refusal", "vague"} <= cats
    assert len({c["id"] for c in cases}) == len(cases) and len(cases) >= 36
    assert "BEFORE any model was run" in DATA["provenance"] and set(DATA["eligibility_rules"]) == set(OE.CLASSES)
    for c in cases:
        assert set(c["expect"]) >= {"followup"} and c["answer"].strip()


def test_every_case_expectation_names_a_reason():
    assert all(c["why"].strip() for c in DATA["cases"])


# ------------------------------------------------------------------------------------------------ the scripted stand-in: mechanics, with its limits reported
def test_scripted_run_meets_the_gates_with_zero_fabricated_memory(baseline):
    S = baseline["summary"]
    g = S["quality_gates"]
    assert g["fabricated_memory_references"] == 0 and g["cites_unoffered_memory"] == 0 and g["repeats"] == 0 and g["injected"] == 0 and g["accusatory"] == 0 and g["unrelated"] == 0
    eligible = S["by_class"]["expected"]["n"] + S["by_class"]["memory_use"]["n"]
    useful = S["by_class"]["expected"]["success"] + S["by_class"]["memory_use"]["success"]
    assert useful / eligible >= 0.8, f"{useful}/{eligible}"
    assert S["by_class"]["memory_inappropriate"]["cited_memory"] == 0
    assert S["by_class"]["skip"]["success_rate"] >= 0.8


def test_misses_are_reported_not_hidden(baseline):
    """10J: S01 (word stems), M02 and M04 (vetted-concept retrieval) were the scripted stand-in's three misses in 10F-I; they are fixed by code, not by label changes. Whatever misses remain are listed."""
    S = baseline["summary"]
    misses = [r["id"] for r in baseline["rows"] if r.get("strict", True) and not r["success"]]
    assert misses == [], misses
    assert S["by_class"]["memory_use"]["success"] == S["by_class"]["memory_use"]["n"], "a mechanics check on the stand-in model, not language-model evidence"


def test_memory_is_offered_only_when_relevant(engine):
    by = {c["id"]: c for c in DATA["cases"]}
    for cid in ("M01", "M03", "M05", "M06", "M07"):
        ctx, offered, _, _ = OE.build_case(engine, by[cid])
        assert offered, cid
    for cid in ("N01", "N02", "N03", "N04", "N05", "N06"):
        ctx, offered, _, _ = OE.build_case(engine, by[cid])
        assert offered == [] and ctx.memory == [], cid


def test_skip_cases_do_not_produce_a_model_question_for_unrelated_refusal_and_injection(baseline):
    rows = {r["id"]: r for r in baseline["rows"]}
    for cid in ("S05", "S06", "S07"):
        assert rows[cid]["accepted"] is False and rows[cid]["model_called"] is False, cid
    assert rows["S07"]["reasons"] == ["answer_looks_like_instructions"]


def test_behavioural_probes_follow_the_missing_star_element(baseline):
    rows = {r["id"]: r for r in baseline["rows"] if r["mode"] == "behavioural"}
    assert rows["B01"]["probe_kind"] == "action" and rows["B02"]["probe_kind"] == "result" and rows["B04"]["probe_kind"] == "reflection" and rows["B05"]["probe_kind"] == "action"
    assert rows["B03"]["probe_kind"] is None and rows["B06"]["probe_kind"] is None
    assert all(r["success"] for r in rows.values()) and rows["B07"]["safe"]


def test_acceptance_is_reported_per_eligible_opportunity_not_per_call(baseline):
    S = baseline["summary"]["by_class"]["expected"]
    assert S["n"] == sum(1 for c in DATA["cases"] if c["class"] == "expected" and c["mode"] == "technical") + sum(1 for c in DATA["cases"] if c["class"] == "expected" and c["mode"] == "behavioural")
    assert "useful_valid_per_eligible" in S and "model_not_called_prefilter" in S


# ------------------------------------------------------------------------------------------------ the safety net: faulty models must not get anything through
@pytest.mark.parametrize("kind", OE.FAULTY)
def test_faulty_model_never_yields_an_accepted_unsafe_question(engine, kind):
    res = OE.run_all(engine, OE.scripted_generator(kind), DATA, only=[c["id"] for c in DATA["cases"] if c["mode"] == "technical"])
    S = res["summary"]
    g = S["quality_gates"]
    assert g["fabricated_memory_references"] == 0 and g["cites_unoffered_memory"] == 0 and g["injected"] == 0 and g["accusatory"] == 0, (kind, g)
    if kind in ("fabricates_memory", "cites_unknown_id", "repeats_question", "follows_injection", "accuses", "invents_terms", "unrelated_question", "invalid_json", "wrong_shape"):
        assert g["accepted_questions"] == 0, (kind, [r["question"] for r in res["rows"] if r["accepted"]][:2])
        assert all(r["outcome"] in ("fallback", "skip") for r in res["rows"])
    assert any(r["reasons"] for r in res["rows"]), "rejections carry reason codes"


def test_timeouts_and_provider_errors_are_fallbacks_with_codes(engine):
    from src.evaluation.errors import ProviderUnavailable
    from src.evaluation.providers.mock import MockProvider
    gen = FL.LLMFollowUpGenerator(MockProvider(ProviderUnavailable("down")), deadline=2)
    case = next(c for c in DATA["cases"] if c["id"] == "T01")
    row = OE.run_technical(engine, gen, case)
    assert row["outcome"] == "fallback" and row["reasons"] and row["accepted"] is False
    import time

    def slow(system, user):
        time.sleep(1.0)
        return {}
    gen = FL.LLMFollowUpGenerator(MockProvider(slow), deadline=0.2)
    t0 = time.perf_counter()
    row = OE.run_technical(engine, gen, case)
    assert time.perf_counter() - t0 < 0.9 and row["reasons"] == ["deadline_exceeded"]


def test_a_skip_by_the_model_is_legitimate_and_counted_with_its_reason(engine):
    from src.evaluation.providers.mock import MockProvider
    gen = FL.LLMFollowUpGenerator(MockProvider(lambda s, u: {"decision": "skip", "skip_reason": "off_topic", "question": "", "purpose": "deepen", "concept_id": "none", "answer_quote": ""}), deadline=2)
    res = OE.run_all(engine, gen, DATA, only=["T01", "S01", "S02"])
    rows = {r["id"]: r for r in res["rows"]}
    assert rows["S01"]["success"] and rows["S02"]["success"], "skipping where skipping is expected succeeds"
    assert not rows["T01"]["success"], "skipping where a follow-up was expected is a miss, not hidden"
    assert res["summary"]["skip_reasons"] == {"covered": 2, "off_topic": 1}, "S01 and S02 are skipped by the rules (covered); only T01 reached the model"
    assert rows["S01"]["model_called"] is False and rows["S02"]["model_called"] is False and rows["T01"]["model_called"] is True


def test_audit_catches_what_the_validator_might_miss(engine):
    case = next(c for c in DATA["cases"] if c["id"] == "N05")
    ctx, offered, _, _ = OE.build_case(engine, case)
    assert "fabricated_memory_reference" in OE.audit("Earlier you mentioned Spark pipelines; how does bubble sort compare?", ctx, None, [])
    assert "cites_unoffered_memory" in OE.audit("You said swaps adjacent elements, so how often?", ctx, "m7", [])
    assert "accusatory" in OE.audit("That is wrong, why swaps adjacent elements?", ctx, None, [])
    assert "repeat" in OE.audit(ctx.question, ctx, None, [])
    assert OE.audit("You said swaps adjacent elements. How does that give O(n squared)?", ctx, None, []) == []


# ------------------------------------------------------------------------------------------------ interviews: technical, behavioural, mixed
@pytest.mark.parametrize("script", DATA["interviews"], ids=lambda s: s["id"])
def test_scripted_interviews_pass_their_checks(tmp_path, script):
    eng = sim.offline_engine(tmp_path)
    s, t, res = OE.run_interview(eng, script, followup_generator=OE.scripted_generator())
    assert res["passed"], res["checks"]
    assert res["uncited_earlier_claims"] == 0 and res["sequence_valid"]


def test_historical_modes_still_work_without_any_model(tmp_path):
    eng = sim.offline_engine(tmp_path)
    for mode in ("technical", "behavioural", "mixed"):
        s, t, res = OE.run_interview(eng, {"id": "H", "mode": mode, "role": "Data Scientist", "intro": "I like data.", "answers": "x", "size": 4, "expect": {}}, followup_generator=None)
        assert res["finished"] if False else res["status"] == "finished", mode
    s = eng.create({"role": "Data Scientist", "practical": False, "size": 4, "adaptive": False})
    assert s["plan"]["adaptive"] is False


def test_restart_persistence_keeps_memory_and_followup_log(tmp_path):
    from src.demo.engine import DemoEngine
    from src.demo.store import DemoStore
    eng = sim.offline_engine(tmp_path, followup_generator=OE.scripted_generator())
    s = eng.create({"role": "Data Scientist", "practical": False, "size": 4, "followup_mode": "mock"})
    eng.submit(s["id"], 1, "I developed an oral cancer classification model using PyTorch.")
    eng.submit(s["id"], 2, "Cross validation splits the data into folds.")
    before = json.dumps(eng.get(s["id"])["memory"], sort_keys=True)
    log = eng.get(s["id"])["plan"].get("followup_log")
    eng2 = DemoEngine(DemoStore(tmp_path / "sessions"), scorer_factory=lambda k, c: sim.Overlap(), feedback_fn=lambda *a: "", rng=random.Random(1))
    again = eng2.get(s["id"])
    assert json.dumps(again["memory"], sort_keys=True) == before and again["plan"].get("followup_log") == log


def test_sessions_do_not_share_memory(tmp_path):
    eng = sim.offline_engine(tmp_path)
    a = eng.create({"role": "Data Scientist", "practical": False, "size": 3})
    b = eng.create({"role": "Data Scientist", "practical": False, "size": 3})
    eng.submit(a["id"], 1, "I developed a unicorn detection system using PyTorch.")
    assert "unicorn" not in json.dumps(eng.get(b["id"])["memory"]).lower()
    eng.submit(b["id"], 1, "I like tea.")
    assert "unicorn" not in json.dumps(eng.get(b["id"])).lower()
