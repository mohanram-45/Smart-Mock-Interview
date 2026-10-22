"""The frozen sample, the blind review sheet and the freeze manifest."""
import csv, importlib.util, json, shutil, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data" / "evaluation" / "stage3c2"
sys.path.insert(0, str(ROOT / "scripts"))
import stage3c2_freeze as fz   # noqa: E402


def jl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def _load_builder():
    spec = importlib.util.spec_from_file_location("b3c2", ROOT / "audit" / "evaluation" / "stage3c2_build_sample.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_sample_shape_and_coverage():
    s, e = jl(D / "sample.jsonl"), jl(D / "provisional_ai_expectations.jsonl")
    assert 12 <= len(s) == 20 and len({x["sample_id"] for x in s}) == 20 and [x["sample_id"] for x in s] == [x["sample_id"] for x in e]
    kinds = {x["kind"] for x in e}
    assert {"correct_full", "concise_sufficient", "valid_alternative", "partial", "incorrect", "hallucinated", "off_topic", "injection", "injection_weak", "injection_with_correct", "non_substantive"} <= kinds
    from src.evaluation.modular import ScopeStore
    elig = set(ScopeStore.load().eligible_ids())
    assert {x["question_id"] for x in s} <= elig and len({x["question_id"] for x in s}) == 8
    assert sum(1 for x in e if "injection" in x["kind"]) == 3


def test_evaluator_inputs_contain_no_labels_or_expectations():
    for r in jl(D / "sample.jsonl"):
        assert set(r) == {"sample_id", "question_id", "question", "answer_text", "source"}
    assert all(e["label_status"] == "ai_provisional_not_human_reviewed" for e in jl(D / "provisional_ai_expectations.jsonl"))


def test_sample_uses_fresh_bench_not_the_tuned_b_cases():
    ids = [r["sample_id"] for r in jl(D / "sample.jsonl")]
    assert all(i.startswith(("b2-", "s2-")) for i in ids) and not any(i.startswith("B") for i in ids)
    qs = {q["question_id"] for q in jl(ROOT / "data/evaluation/bench_v1/items.jsonl")} if (ROOT / "data/evaluation/bench_v1/items.jsonl").exists() else set()
    man = json.loads((ROOT / "data/evaluation/bench_v2/manifest.json").read_text(encoding="utf-8"))
    assert not ({r["question_id"] for r in jl(D / "sample.jsonl")} & set(man["excluded_used_question_ids"]))


def test_blind_sheet_has_blank_review_fields_and_no_ai_expectations():
    rows = list(csv.DictReader(open(D / "review" / "blind_review_sheet.csv", encoding="utf-8")))
    assert len(rows) == 20 and sorted(r["review_id"] for r in rows) == [f"r{i:02d}" for i in range(1, 21)]
    blank = [c for c in rows[0] if c.startswith(("technical_correctness", "completeness", "requirement_judgements", "reviewer_"))]
    assert len(blank) == 6 and all(r[c] == "" for r in rows for c in blank)
    text = (D / "review" / "blind_review_sheet.csv").read_text(encoding="utf-8") + (D / "review" / "blind_review_sheet.md").read_text(encoding="utf-8")
    for forbidden in ("expected_score", "answer_kind", "hallucinated", "valid_alternative", "concise_sufficient", "ai_provisional", "b2-0", "s2-f"):
        assert forbidden not in text, forbidden
    assert all("E1" in r["essential_requirements_ai_drafted"] for r in rows)
    assert "NOT human-verified" in (D / "review" / "blind_review_sheet.md").read_text(encoding="utf-8")


def test_review_key_maps_every_review_id_and_is_separate():
    key = json.loads((D / "review" / "review_key.json").read_text(encoding="utf-8"))
    assert sorted(key.values()) == sorted(r["sample_id"] for r in jl(D / "sample.jsonl"))
    rows = list(csv.DictReader(open(D / "review" / "blind_review_sheet.csv", encoding="utf-8")))
    assert [key[r["review_id"]] for r in rows] != sorted(key.values())       # shuffled, not in sample order


def test_builder_is_deterministic(tmp_path):
    b = _load_builder(); b.OUT = tmp_path
    b.main()
    for rel in ("sample.jsonl", "provisional_ai_expectations.jsonl", "review/blind_review_sheet.csv", "review/blind_review_sheet.md", "review/review_key.json"):
        assert (tmp_path / rel).read_bytes() == (D / rel).read_bytes(), rel


def test_freeze_manifest_matches_the_current_files():
    assert fz.verify(quiet=True) == []
    m = json.loads(fz.MANIFEST.read_text(encoding="utf-8"))
    assert m["status"] == "FROZEN_BEFORE_ANY_REAL_MODEL_RUN" and "none human-reviewed" in m["labels"]
    f = m["fingerprints"]
    assert f["model_config"]["model"] == "qwen2.5:7b" and f["model_config"]["paid_apis"] is False and f["model_config"]["model_downloads"] is False
    for k in ("sample_jsonl_sha256", "scope_sidecar_sha256", "verifier_system_prompt_sha256", "modular_code_sha256", "legacy_code_sha256", "model_config_sha256"):
        assert len(f[k]) == 64
    assert f["scope_sidecar_sha256"].startswith("7332f65c")
    assert {"reports/stage3c2_protocol.md", "data/evaluation/stage3c2/acceptance_criteria.json", "scripts/stage3c2_run.py"} <= set(f["protocol_files_sha256"])


def test_any_change_to_a_frozen_input_is_detected(tmp_path, monkeypatch):
    fake = tmp_path / "d"; shutil.copytree(D, fake)
    monkeypatch.setattr(fz, "D", fake)
    assert fz.verify(quiet=True) == []
    s = (fake / "sample.jsonl").read_text(encoding="utf-8")
    (fake / "sample.jsonl").write_text(s.replace("Type", "Typo", 1), encoding="utf-8")
    assert "sample_jsonl_sha256" in fz.verify(quiet=True)


def test_crlf_checkout_hashes_the_same(tmp_path):
    p = tmp_path / "x.txt"; p.write_bytes(b"a\nb\n"); h1 = fz.sha_file(p); p.write_bytes(b"a\r\nb\r\n")
    assert fz.sha_file(p) == h1


def test_acceptance_criteria_are_defined_and_frozen():
    c = json.loads((D / "acceptance_criteria.json").read_text(encoding="utf-8"))
    assert c["frozen_before_any_real_model_run"] is True and "false_credit_rate_max" in c["needs_human_labels"]
    assert set(c["decision_rule"]) >= {"any_mechanical_fail", "all_mechanical_pass_but_no_human_labels"}
    assert "never general grading accuracy" in c["note"] or "never general" in c["note"]
