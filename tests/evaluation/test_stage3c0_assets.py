"""Stage 3C-0: concept-scope sidecar + bench_v2 quality controls."""
import copy, json, sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from audit.evaluation import stage3c_validate as V

@pytest.fixture(scope="module")
def results():
    return V.run()

CHECKS = ["ids_map_666", "question_type_matches", "corpus_unchanged", "frozen_csv_sha", "tiers_consistent", "optional_never_penalised",
          "essential_vs_question_proxy", "alternatives_have_basis", "human_review_identifiable", "scope_reproducible", "bench_size_and_ids",
          "bench_fresh", "bench_inputs_label_free", "bench_coverage", "bench_labels_provisional", "bench_manifest_matches", "bench_reproducible", "review_sheet"]

@pytest.mark.parametrize("name", CHECKS)
def test_quality_check(results, name):
    ok, detail = results[name]
    assert ok, detail

def test_no_human_verified_anywhere():
    rows = V.read_jsonl(V.SCOPE / "scope_v1.jsonl")
    assert not any("human" in r["verification_status"] and "required" not in r["verification_status"] for r in rows)
    assert {r["verification_status"] for r in rows} <= V.STATUSES

def test_penalty_contract_only_essentials_and_only_when_eligible():
    rows = {r["question_id"]: r for r in V.read_jsonl(V.SCOPE / "scope_v1.jsonl")}
    r = copy.deepcopy(rows["smi-0453"])
    r["completeness_penalty_eligible"] = True
    rel = V.penalty_relevant_concepts(r)
    assert set(rel) == set(r["essential_concepts"]) and not set(r["supporting_concepts"]) & set(rel)
    r["completeness_penalty_eligible"] = False
    assert V.penalty_relevant_concepts(r) == []

def test_known_risk_cases_tiering():
    rows = {r["question_id"]: r for r in V.read_jsonl(V.SCOPE / "scope_v1.jsonl")}
    assert "O(n²)" in rows["smi-0453"]["essential_concepts"]               # bubble sort complexity is the asked answer
    assert "memory addresses" in rows["smi-0441"]["supporting_concepts"]    # identity wording is not an extra requirement
    assert "DENSE_RANK" in rows["smi-0431"]["supporting_concepts"] and "ROW_NUMBER" in rows["smi-0431"]["essential_concepts"]
    assert "reference_broader_than_question" in rows["smi-0431"]["ambiguity_flags"]

def test_zero_essential_records_not_silently_forced():
    rows = {r["question_id"]: r for r in V.read_jsonl(V.SCOPE / "scope_v1.jsonl")}
    zero = [r for r in rows.values() if r["tier_source"] == "manual_zero_essential"]
    assert len(zero) == 37
    # list-type / open questions keep group semantics instead of an invented single essential concept
    assert any(not r["essential_concepts"] and r["essential_groups"] for r in zero)
    # each is either flagged ambiguous or has explicit essential content after review (never an empty, unflagged record)
    assert all(r["ambiguity_flags"] or r["essential_concepts"] or r["essential_groups"] for r in zero)

def test_validator_detects_tampering(tmp_path, monkeypatch):
    rows = V.read_jsonl(V.SCOPE / "scope_v1.jsonl")
    rows[0]["supporting_concepts"] = rows[0]["supporting_concepts"] + rows[0]["essential_concepts"][:1]
    d = tmp_path; (d / "scope_v1.jsonl").write_bytes("\n".join(json.dumps(r) for r in rows).encode("utf-8"))
    (d / "scope_v1_manifest.json").write_bytes((V.SCOPE / "scope_v1_manifest.json").read_bytes())
    monkeypatch.setattr(V, "SCOPE", d)
    ok, _ = V.run()["tiers_consistent"]
    assert not ok

def test_bench_answer_ids_do_not_reveal_kind():
    a = V.read_jsonl(V.BENCH / "answers.jsonl"); l = {x["answer_id"]: x["answer_kind"] for x in V.read_jsonl(V.BENCH / "ai_labels.jsonl")}
    first = [l[x["answer_id"]] for x in a[:12]]
    assert len(set(first)) > 3          # shuffled, not grouped by kind
