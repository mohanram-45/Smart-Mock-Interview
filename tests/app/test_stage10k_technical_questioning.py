"""Stage 10K: technical questioning. T02/T03/T07/T09/T10 regressions, depth states, skip/question consistency, repair, fallback classes. Scripted stand-in only: mechanics, not model quality."""
import pytest

from src.demo import followup_llm as FL, opportunity_eval as OE

DATA = OE.load()
CASES = {c["id"]: c for c in DATA["cases"]}


@pytest.fixture(scope="module")
def engine():
    return OE.offline_engine()


def _ctx(engine, cid):
    return OE.build_case(engine, CASES[cid])[0]


def test_all_forty_cases_build_a_context_with_open_concepts_or_a_documented_reason(engine):
    assert len(DATA["cases"]) == 40
    for c in DATA["cases"]:
        if c["mode"] != "technical":
            continue
        ctx = _ctx(engine, c["id"])
        code = FL.opportunity_class(ctx)
        assert isinstance(code, str) and code
        if code != "covered" and FL.open_concepts(ctx):
            t = FL.target_concept(ctx)
            assert t and t.get("label")


def test_target_concept_is_never_one_the_answer_already_explained(engine):
    for cid in ("T02", "T03", "T10"):
        ctx = _ctx(engine, cid)
        t = FL.target_concept(ctx)
        if t is not None:
            assert t["id"] in {c["id"] for c in FL.open_concepts(ctx)}


@pytest.mark.parametrize("kind", OE.FAULTY)
def test_every_faulty_model_is_rejected_on_the_t_cases(engine, kind):
    res = OE.run_all(engine, OE.scripted_generator(kind), DATA, only=["T02", "T03", "T07", "T09", "T10"])
    for r in res["rows"]:
        assert not r["useful_valid"] or not r["audit"], (kind, r["id"], r["audit"])
        if r["accepted"]:
            assert r["audit"] == [], (kind, r["id"])


def test_skip_with_question_payload_is_detected_logged_and_not_silently_accepted(engine):
    res = OE.run_all(engine, OE.scripted_generator("skip_with_question"), DATA, only=["T07"])
    r = res["rows"][0]
    assert not r["accepted"] and any("skip_with_question" in x for x in r["payload_issues"] + r["reasons"])
    assert r["fallback_class"] in ("payload_inconsistent", "wording_failed", "no_followup_needed", "model_error")


def test_no_internal_concept_id_reaches_a_user_visible_question(engine):
    res = OE.run_all(engine, OE.scripted_generator(), DATA)
    for r in res["rows"]:
        if r["mode"] == "technical" and r["accepted"]:
            assert not OE._ID_LEAK.search(r["question"]), (r["id"], r["question"])


def test_repair_text_quotes_the_rejected_question_and_names_the_defect():
    for key in ("ignores_target", "targets_covered_concept", "repeats_earlier", "payload:skip_with_question"):
        assert any(key in k for k in FL._REPAIR_TEXT), key


def test_at_most_two_model_calls_per_follow_up(engine):
    res = OE.run_all(engine, OE.scripted_generator("repeats_question"), DATA)
    assert all(r["attempts"] <= 2 for r in res["rows"] if r["mode"] == "technical")


def test_fallback_class_separates_wording_failure_from_no_followup_needed(engine):
    rows = OE.run_all(engine, OE.scripted_generator("invalid_json"), DATA, only=["T02", "S01"])["rows"]
    classes = {r["id"]: r["fallback_class"] for r in rows}
    assert classes["T02"] in ("model_error", "wording_failed", "payload_inconsistent")
    assert classes["S01"] in ("no_followup_needed", "not_attempted", "model_error", "wording_failed", None)


def test_scripted_well_behaved_run_has_no_rejections_on_the_five_cases(engine):
    rows = OE.run_all(engine, OE.scripted_generator(), DATA, only=["T02", "T03", "T07", "T09", "T10"])["rows"]
    for r in rows:
        assert r["success"], (r["id"], r["reasons"], r["audit"])
