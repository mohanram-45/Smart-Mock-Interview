"""Stage 9C: grounded written feedback (six separate sections, abstention kept honest, no numeric grade). Uses the mock verifier / hand-built views: no model, no network."""
import copy

import pytest

from src.demo import experimental as MA, grounded as G
from src.retrieval.service import get_service


def rec(scorable=True):
    for r in get_service().records():
        if MA.is_scorable(r["question_id"]) == scorable:
            return r
    pytest.skip("no such record")


def view_for(r, answer):
    return MA.evaluate("mock", r, answer)


def test_no_view_means_nothing_is_invented():
    assert G.build(None) is None
    assert G.build({"status": "provider_error"}) is None


def test_six_sections_and_no_numeric_grade():
    r = rec()
    g = G.build(view_for(r, r["canonical_answer"]), answer=r["canonical_answer"])
    assert g["numeric_grade"] is None and g["human_validated"] is False and g["experimental"] is True
    for k in ("answer", "evidence", "supported", "maybe_missing", "errors", "uncertain"):
        assert k in g
    assert g["evidence"]["concepts"], "curated concepts are shown as the evidence base"
    assert g["supported"] and all(x["your_words"] for x in g["supported"]), "support is shown in the candidate's own words"
    assert "score" not in g and "grade" not in g["headline"].lower().replace("nothing here is a grade", "")


def test_unrelated_answer_is_undecided_not_accused():
    r = rec()
    g = G.build(view_for(r, "It is a type of model that people use a lot in many places today."), answer="x")
    assert g["status"] == "abstained" and g["errors"] == [] and g["supported"] == [] and len(g["uncertain"]) == len(g["evidence"]["concepts"])


def _view_with(finding, penalty="full", with_ref=True, claim=True):
    v = {"status": "scored", "answer": "A stack is first in first out.", "claims": [{"id": "c1", "text": "A stack is first in first out."}],
         "verdicts": [{"requirement_id": "E1", "tier": "essential", "member": "last in first out", "finding_class": finding, "claim_ids": ["c1"] if claim else [], "explanation": "contradicts"}],
         "outcomes": [{"requirement_id": "E1", "label": "last in first out", "tier": "essential", "kind": "concept", "status": "contradicted"}],
         "feedback": {"factual_errors": [{"concept": "last in first out", "reference_says": "A stack is last in first out." if with_ref else None}], "could_not_verify": []},
         "requirements": {"available": True, "penalty_mode": penalty, "flags": ["scope_ai_reviewed_not_human_verified"], "alternatives": ["none recorded"], "requirements": [{"id": "E1", "label": "last in first out", "tier": "essential"}]},
         "source": {"kind": "mock", "tags": []}, "taxonomy": {}}
    return v


def test_error_requires_penalty_scope_claim_and_reference_evidence():
    g = G.build(_view_with("incorrect"))
    assert len(g["errors"]) == 1 and g["errors"][0]["reference_says"] and g["errors"][0]["your_words"]
    for kw in ({"penalty": "advisory"}, {"with_ref": False}, {"claim": False}):
        g = G.build(_view_with("incorrect", **kw))
        assert g["errors"] == [] and g["uncertain"], kw          # a doubtful accusation is demoted to 'could not be decided', never asserted


def test_unconfirmed_model_credit_is_not_counted():
    g = G.build(_view_with("correct_unsupported"))
    assert g["supported"] == [] and g["uncertain"] and "not counted" in g["uncertain"][0]["reason"]


def test_abstention_is_stated_not_turned_into_a_pass():
    v = _view_with("unverified_by_model")
    v["status"] = "abstained"
    v["taxonomy"] = {"primary": "model_uncertain"}
    g = G.build(v)
    assert g["status"] == "abstained" and g["abstention"] and "could not reach a firm judgement" in g["headline"] and g["numeric_grade"] is None
    assert g["supported"] == [] and g["errors"] == []


def test_input_view_is_not_mutated():
    v = _view_with("incorrect")
    before = copy.deepcopy(v)
    G.build(v)
    assert v == before


def test_missing_concepts_are_worded_as_prompts_not_mistakes():
    v = _view_with("omitted")
    g = G.build(v)
    assert g["maybe_missing"] and "not a mistake" in g["maybe_missing"][0]["note"] and g["errors"] == []
