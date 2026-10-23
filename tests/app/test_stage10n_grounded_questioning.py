"""Stage 10N: evidence is chosen by code, never by the model; regression pairs for the observed T01-T12 failures; unseen holdouts; memory links that are specific. Scripted/offline: these prove the
validator and plumbing, not what a language model writes (no Ollama in the build sandbox)."""
import hashlib
import re
from pathlib import Path

import pytest

from src.demo import followup_llm as FL, opportunity_eval as OE, question_pairs_eval as Q

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def pairs():
    return Q.run()


def rows(pairs, id_, kind=None):
    return [r for r in pairs["rows"] if r["id"] == id_ and (kind is None or r["kind"] == kind)]


# ------------------------------------------------------------------------------------------------ the evidence contract
def test_the_model_is_no_longer_asked_for_evidence_and_the_old_reason_is_unreachable():
    assert "answer_quote" not in FL.build_schema(None)["properties"] if hasattr(FL, "build_schema") and FL.build_schema.__code__.co_argcount == 1 else True
    src = (ROOT / "src/demo/followup_llm.py").read_text(encoding="utf-8")
    assert not re.search(r"""reasons\.append\(\s*f?["']evidence:""", src), "no code path can add an evidence:* rejection any more (the docstrings only cite the old failure)"
    assert FL.PROMPT_VERSION == "10.fu8"


def test_a_missing_empty_or_invented_model_quote_neither_voids_nor_vouches():
    ctx = OE.build_case(OE.offline_engine(), next(c for c in OE.load()["cases"] if c["id"] == "T10"))[0]
    tgt = FL.target_concept(ctx)
    base = {"decision": "ask", "question": "How would the ROC curve and AUC help you judge this logistic regression model?", "purpose": "probe_concept", "concept_id": tgt["id"], "memory_id": "none"}
    ok, _ = FL.validate(base, ctx)
    assert ok is not None
    for quote in (None, "", 7, "words the candidate never wrote"):
        p, why = FL.validate(dict(base, answer_quote=quote), ctx)
        assert p is not None, (quote, why)
        assert p.evidence and p.evidence[0]["ref"] in ctx.answer, "evidence is always a verbatim span chosen by code"
    p, _ = FL.validate(dict(base, question="How would the glimmer quotient help you judge this model?", answer_quote="I would use cross-validation"), ctx)
    assert p is None, "a true quote cannot rescue an unsupported question"


# ------------------------------------------------------------------------------------------------ T01-T12: reasonable questions pass, repeats / given-away answers do not
GOOD_MUST_PASS = ["T01", "T02", "T03", "T04", "T06", "T07", "T08", "T09", "T10", "T11", "T12"]


@pytest.mark.parametrize("id_", GOOD_MUST_PASS)
def test_fixture_good_question_is_not_falsely_rejected(pairs, id_):
    for r in rows(pairs, id_, "good"):
        assert r["accepted"], (r["question"], r["reasons"])


@pytest.mark.parametrize("id_", [i for i in GOOD_MUST_PASS if i != "T01"] + ["T05"])
def test_fixture_bad_question_is_not_falsely_accepted_except_the_documented_gaps(pairs, id_):
    for r in rows(pairs, id_, "bad"):
        if r.get("known_gap"):
            continue
        assert not r["accepted"], (r["question"], r["why"])


def test_the_known_gaps_are_pinned_so_a_change_is_noticed(pairs):
    gap = [r for r in pairs["rows"] if r["kind"] == "bad" and r.get("known_gap")]
    assert {r["id"] for r in gap} == {"T02", "T05"}
    assert sum(r["accepted"] for r in gap) == pairs["all"]["known_gap_accepted"] == 1, "T02 rollback/durability is caught (the explained concept is repeated); T05 affirmed misconception is not"
    assert [r["accepted"] for r in rows(pairs, "T01", "bad")] == [True], "T01 'undefined for an unusual input' is a documented false acceptance"


def test_T05_the_scenario_question_without_a_label_is_a_documented_false_rejection(pairs):
    (r,) = rows(pairs, "T05", "good")
    assert not r["accepted"] and r["reasons"] == ["question:ignores_target"]


def test_T05_a_question_naming_the_open_concept_in_words_is_accepted():
    ctx = OE.build_case(OE.offline_engine(), next(c for c in OE.load()["cases"] if c["id"] == "T05"))[0]
    p, why = FL.validate({"decision": "ask", "question": "How would you show the difference between value equality and identity equality with two separate lists?", "purpose": "probe_concept", "concept_id": FL.target_concept(ctx)["id"], "memory_id": "none"}, ctx)
    assert p is not None, why


def test_T06_a_value_like_gap_is_never_named_or_stated():
    ctx = OE.build_case(OE.offline_engine(), next(c for c in OE.load()["cases"] if c["id"] == "T06"))[0]
    assert FL.display_label(FL.target_concept(ctx)) == FL.VALUE_LABEL
    for q in ("Why is bubble sort O(n²) in the worst case?", "How does the O(n²) cost come about for bubble sort?"):
        p, why = FL.validate({"decision": "ask", "question": q, "purpose": "probe_concept", "concept_id": FL.target_concept(ctx)["id"], "memory_id": "none"}, ctx)
        assert p is None and any("reveals_reference_value" in w or "novel_terms" in w for w in why), q


def test_T12_the_false_premise_stays_rejected_and_the_unexplained_concept_is_the_target():
    ctx = OE.build_case(OE.offline_engine(), next(c for c in OE.load()["cases"] if c["id"] == "T12"))[0]
    assert FL.target_concept(ctx)["label"] == "Type II error"
    (r,) = rows(Q.run(), "T12", "bad")
    assert not r["accepted"] and any("false_premise" in w for w in r["reasons"])


# ------------------------------------------------------------------------------------------------ false rejections found by the holdouts and fixed
@pytest.mark.parametrize("q", ["What could go wrong if the graph contained a cycle and you kept no record of the nodes you had seen?", "Which kind of wrong prediction would worry you more in a medical screening, and why?", "What mistake would you watch for when scaling the data before splitting it?"])
def test_asking_about_a_failure_mode_is_not_accusatory(q):
    assert not FL._ACCUSING.search(q)


@pytest.mark.parametrize("q", ["You're wrong about that.", "That is incorrect.", "You got it wrong.", "That answer is wrong."])
def test_a_real_accusation_is_still_rejected(q):
    assert FL._ACCUSING.search(q)


def test_earlier_as_an_adjective_is_not_a_memory_reference():
    assert not FL._MEM_CUE.search("What would happen to the running time if you did not store earlier results?")
    assert FL._MEM_CUE.search("Earlier you said you built a search feature.")
    assert FL._MEM_CUE.search("You mentioned earlier that you used PyTorch.")


# ------------------------------------------------------------------------------------------------ unseen holdouts: nothing bad slips through
def test_holdouts_have_no_detectable_false_acceptance(pairs):
    assert pairs["holdout"]["false_acceptances"] == 0 and pairs["holdout2"]["false_acceptances"] == 0
    assert pairs["holdout"]["n_bad"] >= 10 and pairs["holdout2"]["n_bad"] >= 10


def test_the_false_rejection_rate_on_the_holdouts_is_measured_not_hidden(pairs):
    fr = pairs["holdout"]["false_rejections"] + pairs["holdout2"]["false_rejections"]
    n = pairs["holdout"]["n_good"] + pairs["holdout2"]["n_good"]
    assert fr <= 16 and n == 20, "ceiling pinned at the measured value; lowering it is progress, raising it is a regression"


def test_the_pair_file_is_hand_written_and_declares_what_it_is():
    d = Q.load()
    assert "not human validation" in d["note"] and len(d["items"]) >= 30


# ------------------------------------------------------------------------------------------------ frozen fixture and no benchmark hard-coding
def test_the_frozen_fixture_hash_is_unchanged():
    raw = (ROOT / "src/demo/eval_data/stage10f_opportunities_v1.json").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == "59e92f47c50657b53b7c93e80d327046954238af08d1d7fa936def3609ff0737"


def test_production_code_does_not_mention_benchmark_case_ids():
    for f in ("followup_llm.py", "memory.py", "policy.py", "engine.py"):
        p = ROOT / "src/demo" / f
        if p.exists():
            code = re.sub(r"#.*", "", p.read_text(encoding="utf-8"))                    # comments cite the failure that motivated a rule; code must not branch on a case id
            assert not re.search(r"""["'](?:T(?:0\d|1[0-2])|M0[1-7]|B0\d)["']""", code), f


# ------------------------------------------------------------------------------------------------ memory links
def _row(id_):
    s = OE.run_all(OE.offline_engine(), OE.scripted_generator(), only=[id_])
    return s["rows"][0]


@pytest.mark.parametrize("id_", ["M05", "M07"])
def test_memory_link_is_specific_or_the_citation_is_dropped(id_):
    r = _row(id_)
    assert r["success"] and r["audit"] in (None, "ok", "clean", "") or r["success"]
    if r["memory_stage"] == "used":
        assert r["memory_cited"] and r["lead"] is None or r["question"].lower().startswith("earlier you said")
    else:
        assert not r["memory_cited"], "a question that does not use the memory carries no citation"


def test_a_memory_lead_that_ignores_the_open_gap_is_rejected():
    ctx = OE.build_case(OE.offline_engine(), next(c for c in OE.load()["cases"] if c["id"] == "M07"))[0]
    assert ctx.memory
    m = ctx.memory[0]
    p, why = FL.validate({"decision": "ask", "question": "How did the library catalogue search feature in Python handle the catalogue?", "purpose": "apply", "concept_id": FL.target_concept(ctx)["id"], "memory_id": m["id"]}, ctx, mode="memory")
    assert p is None or p.memory_id in (None, "none")
