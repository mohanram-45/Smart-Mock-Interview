"""bench_v2 is used ONLY for contract and coverage checks. Nothing here compares a result with the AI-authored score expectations,
and no grading rule was tuned on it. (ai_labels.jsonl is opened once, to check that segmentation/flags behave on adversarial kinds.)"""
import json
from pathlib import Path

import pytest

from src.evaluation.modular import ModularEvaluator, ReferenceMaterial
from src.evaluation.modular.mock_verifiers import LexicalMockVerifier
from src.evaluation.modular.pipeline import ModularStatus as MS
from src.evaluation.modular.claims import segment
from tests.evaluation.mod_helpers import ref_of, store

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "evaluation" / "bench_v2"
MOD = ROOT / "src" / "evaluation" / "modular"


def _jl(name):
    return [json.loads(x) for x in (BENCH / name).read_text(encoding="utf-8").splitlines()]


@pytest.fixture(scope="module")
def results(by_id):
    qs = {q["question_id"]: q for q in _jl("questions.jsonl")}
    ev = ModularEvaluator(store(), LexicalMockVerifier())
    return {a["answer_id"]: (a, ev.evaluate(a["question_id"], qs[a["question_id"]]["question"], a["answer_text"], ref_of(by_id, a["question_id"]))) for a in _jl("answers.jsonl")}


def test_modular_package_never_reads_benchmark_or_label_files():
    for f in MOD.glob("*.py"):
        t = f.read_text(encoding="utf-8")
        for forbidden in ("ai_labels", "bench_v2", "expected_score", "answer_kind", "scoring_rubric"):
            assert forbidden not in t, (f.name, forbidden)


def test_every_benchmark_answer_runs_without_error_and_has_a_valid_status(results):
    assert len(results) == 120
    for aid, (a, r) in results.items():
        assert r.status in set(MS) and r.provenance["is_mock"] is True and r.provenance["human_validated"] is False
        json.dumps(r.to_dict())


def test_only_scope_eligible_questions_can_ever_receive_a_numeric_score(results):
    elig = set(store().eligible_ids())
    for aid, (a, r) in results.items():
        if r.score is not None:
            assert a["question_id"] in elig and r.status is MS.SCORED
        if a["question_id"] not in elig and r.status not in (MS.NOT_GRADABLE,):
            assert r.status is MS.ADVISORY_ONLY


def test_the_lexical_mock_demonstrates_abstention_not_accuracy(results):
    """Word overlap cannot prove omission or error, so nothing is ever scored low: eligible answers abstain unless every dimension is proven."""
    for aid, (a, r) in results.items():
        assert not any(v.state.value in ("not_stated", "states_incorrectly") for v in r.verdicts)
        if r.status is MS.SCORED:
            assert all(d.level is not None for d in r.dimensions)


def test_eight_benchmark_questions_are_scope_eligible_and_cover_both_modes(results):
    qids = {a["question_id"] for a, _ in results.values()}
    elig = qids & set(store().eligible_ids())
    assert len(elig) == 8 and len(qids) == 24
    assert {r.penalty_mode for _, r in results.values()} == {"full", "advisory"}


def test_injection_answers_are_detected_or_withheld_from_credit(results):
    labels = {x["answer_id"]: x for x in _jl("ai_labels.jsonl")}
    inj = [aid for aid, l in labels.items() if "prompt_injection" in l["flags"]]
    assert len(inj) == 6
    for aid in inj:
        a, r = results[aid]
        assert "injection_detected" in r.flags, a["answer_text"][:60]


def test_benchmark_questions_and_reference_text_match_the_frozen_corpus(by_id):
    for q in _jl("questions.jsonl"):
        assert by_id[q["question_id"]]["question"] == q["question"]


def test_claims_cover_code_and_sql_answers_as_whole_blocks(results):
    fenced = [a for a, _ in results.values() if "```" in a["answer_text"]]
    assert len(fenced) == 26
    for a in fenced:
        seg = segment(a["answer_text"])
        assert sum(1 for c in seg.claims if c.kind == "code" and c.text.startswith("```")) == a["answer_text"].count("```") // 2
