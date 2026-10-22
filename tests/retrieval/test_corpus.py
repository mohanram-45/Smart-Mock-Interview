import csv
import hashlib
import json
import random

import pytest

from src.retrieval.corpus import CorpusValidationError, corpus_fingerprint, load_corpus


def test_loads_expected_counts(real_root):
    c = load_corpus(real_root)
    m = c["manifest"]
    assert m["record_count"] == 666 and m["unique_ids"] == 666
    assert [x["records"] for x in m["components"]] == [487, 46, 48, 45, 40]
    assert c["problems"] == []


def test_two_new_domains_supported(real_root):
    m = load_corpus(real_root)["manifest"]
    assert m["domain_counts"]["Generative AI & RAG"] == 94 and m["domain_counts"]["MLOps & Model Deployment"] == 85
    assert len(m["domain_counts"]) == 8


def test_quarantined_record_excluded(real_root):
    recs = load_corpus(real_root)["records"]
    assert all(r["provenance"]["plan_id"] != "B4-MLO-13-4" for r in recs)
    assert load_corpus(real_root)["manifest"]["excluded_quarantined"] == ["B4-MLO-13-4"]


def test_ids_unique_and_order_deterministic(real_root):
    a, b = load_corpus(real_root)["records"], load_corpus(real_root)["records"]
    ids = [r["question_id"] for r in a]
    assert len(set(ids)) == len(ids) and ids == [r["question_id"] for r in b]
    assert [r["provenance"]["batch"] for r in a][:487] == ["v5"] * 487


def test_canonical_and_alternatives_preserved(real_root):
    recs = {r["question_id"]: r for r in load_corpus(real_root)["records"]}
    multi = [r for r in recs.values() if r["alternative_answers"]]
    assert len(multi) == 123
    for r in multi:
        for name, text in r["alternative_answers"].items():
            assert name in ("concise", "practical", "detailed") and text and text != r["canonical_answer"]
    assert all(r["canonical_answer"] for r in recs.values())


def test_provenance_and_verification_preserved(real_root):
    for r in load_corpus(real_root)["records"]:
        assert r["provenance"]["origin"] in {"v5", "batch_01", "batch_02", "batch_03", "batch_04"}
        assert r["provenance"]["dataset_fingerprint"]
        assert r["verification"]["verification"] and r["verification"]["human_reviewed"] is False
        assert isinstance(r["sources"], list)


def test_time_sensitive_flags_carried(real_root):
    recs = load_corpus(real_root)["records"]
    assert sum(r["verification"]["time_sensitive"] for r in recs) == 17


def test_fingerprint_stable_and_order_independent(real_root):
    recs = load_corpus(real_root)["records"]
    shuffled = recs[:]
    random.Random(1).shuffle(shuffled)
    assert corpus_fingerprint(recs) == corpus_fingerprint(shuffled) == load_corpus(real_root)["manifest"]["corpus_sha256"]
    changed = [dict(r) for r in recs]
    changed[0]["canonical_answer"] += " x"
    assert corpus_fingerprint(changed) != corpus_fingerprint(recs)


def test_loader_does_not_modify_dataset_files(real_root):
    f = real_root / "data/curated/v5/curated_questions.csv"
    before = hashlib.sha256(f.read_bytes()).hexdigest()
    load_corpus(real_root)
    assert hashlib.sha256(f.read_bytes()).hexdigest() == before == "7d7287a73f96276c5455c7949a8e7a8dc236b1515798f5a2b4a817f8a99fec94"


def test_tampered_batch_csv_rejected(corpus_copy):
    p = corpus_copy / "data/expansion/batch_02/batch_02_accepted.csv"
    p.write_bytes(p.read_bytes() + b"\n")
    with pytest.raises(CorpusValidationError, match="hash differs"):
        load_corpus(corpus_copy)


def test_tampered_v5_rejected(corpus_copy):
    p = corpus_copy / "data/curated/v5/curated_questions.csv"
    p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises(CorpusValidationError):
        load_corpus(corpus_copy)


def test_unapproved_batch_rejected(corpus_copy):
    p = corpus_copy / "data/expansion/approved_batches.json"
    reg = json.loads(p.read_text())
    reg["batches"][3]["status"] = "pending"
    p.write_text(json.dumps(reg))
    with pytest.raises(CorpusValidationError, match="not approved"):
        load_corpus(corpus_copy)


def test_registry_count_mismatch_rejected(corpus_copy):
    p = corpus_copy / "data/expansion/approved_batches.json"
    reg = json.loads(p.read_text())
    reg["totals"]["combined_if_merged"] = 667
    p.write_text(json.dumps(reg))
    with pytest.raises(CorpusValidationError, match="total"):
        load_corpus(corpus_copy)


def test_non_strict_reports_problems_without_raising(corpus_copy):
    p = corpus_copy / "data/expansion/batch_01/batch_01_accepted.csv"
    p.write_bytes(p.read_bytes() + b"\n")
    c = load_corpus(corpus_copy, strict=False)
    assert c["problems"]


def _rewrite_batch(corpus_copy, mutate, n=3):
    """Mutate rows of a batch csv and re-point the registry hash so only the record-level check can catch it."""
    p = corpus_copy / f"data/expansion/batch_0{n}/batch_0{n}_accepted.csv"
    rows = list(csv.DictReader(open(p, encoding="utf-8", newline="")))
    fields = list(rows[0].keys())
    rows = mutate(rows)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    reg_p = corpus_copy / "data/expansion/approved_batches.json"
    reg = json.loads(reg_p.read_text())
    reg["batches"][n - 1]["accepted_csv_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    reg_p.write_text(json.dumps(reg))


def test_missing_required_field_detected(corpus_copy):
    def mut(rows):
        rows[0]["key_concepts"] = ""
        return rows
    _rewrite_batch(corpus_copy, mut)
    c = load_corpus(corpus_copy, strict=False)
    assert any("missing key_concepts" in x for x in c["problems"])


def test_duplicate_id_detected(corpus_copy):
    def mut(rows):
        rows[1]["id"] = rows[0]["id"]
        return rows
    _rewrite_batch(corpus_copy, mut)
    assert any("duplicate id" in x for x in load_corpus(corpus_copy, strict=False)["problems"])


def test_bad_difficulty_detected(corpus_copy):
    def mut(rows):
        rows[0]["difficulty"] = "Extreme"
        return rows
    _rewrite_batch(corpus_copy, mut)
    assert any("bad difficulty" in x for x in load_corpus(corpus_copy, strict=False)["problems"])
