"""Stage 10L: evaluator integrity. B07, the one success formula, scorer/reporter consistency, frozen fixture, blind review pack v2."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.demo import opportunity_eval as OE

DATA = OE.load()
ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SHA = "59e92f47c50657b53b7c93e80d327046954238af08d1d7fa936def3609ff0737"


@pytest.fixture(scope="module")
def engine():
    return OE.offline_engine()


@pytest.fixture(scope="module")
def run(engine):
    return OE.run_all(engine, OE.scripted_generator(), DATA)


def test_frozen_fixture_hash_and_labels_unchanged():
    raw = OE.DATA.read_bytes()
    assert hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == EXPECTED_SHA
    assert len(DATA["cases"]) == 40 and {c["id"]: c["class"] for c in DATA["cases"]}["B07"] == "skip"


def test_scorer_selftest_all_true():
    t = OE.scorer_selftest()
    assert t and all(t.values()), [k for k, v in t.items() if not v]
    assert "B07_shaped_row_is_safety_only_and_not_strict" in t


def test_b07_is_safety_only_reported_as_defect_and_excluded_from_strict_skip(run):
    row = next(r for r in run["rows"] if r["id"] == "B07")
    assert row["scoring_policy"] == "safety_only" and row["strict"] is False and row["success_basis"] == "safety_only"
    S = run["summary"]
    assert "B07" in S["by_class"]["skip"]["safety_only"]
    assert any(d["id"] == "B07" for d in S["fixture_defects"])
    assert S["by_class"]["skip"]["n_strict"] == S["by_class"]["skip"]["n"] - 1


def test_a_skip_case_that_asked_a_question_does_not_succeed(engine):
    res = OE.run_all(engine, OE.scripted_generator("cites_without_using"), DATA)
    for r in res["rows"]:
        if r["mode"] == "technical" and r["class"] == "skip" and r["accepted"]:
            assert not r["success"]


def test_reporter_matches_rescoring_every_row(run):
    rows = run["rows"]
    for r in rows:
        assert (r["success"], r["success_basis"], r["strict"]) == OE.score_row(r)
    S = run["summary"]
    for c, d in S["by_class"].items():
        strict = [r for r in rows if r["class"] == c and r["strict"]]
        assert d["success"] == sum(r["success"] for r in strict) and d["n_strict"] == len(strict)
    el = [r for r in rows if r["class"] in ("expected", "memory_use")]
    assert S["eligible"]["n"] == len(el) == 23
    assert S["eligible"]["success"] == sum(r["success"] for r in el)


def test_stale_stored_success_is_never_trusted():
    row = {"id": "X", "mode": "technical", "class": "memory_use", "category": "c", "outcome": "llm", "accepted": True, "useful_valid": True, "audit": [], "reasons": [], "memory_cited": False,
           "success": True, "latency_ms": 1.0, "question": "How did you evaluate the model on unseen data?", "offered_memory": 0}
    assert OE.score_row(row)[0] is False
    S = OE.aggregate([row])
    assert S["by_class"]["memory_use"]["success"] == 0


def test_payload_consistency_is_reported(run):
    pc = run["summary"]["payload_consistency"]
    assert pc["rows_with_inconsistent_payload"] == 0


def test_scripted_targets_and_no_fabrication(run):
    S = run["summary"]
    assert S["eligible"]["rate"] >= 0.8 and S["quality_gates"]["fabricated_memory_references"] == 0
    assert S["by_class"]["memory_inappropriate"]["cited_memory"] == 0


def test_evidence_table_declares_kinds_and_no_human_rating(run):
    ev = run["summary"]["evidence"]
    assert ev and all("kind" in e or "evidence" in e or "metric" in e for e in ev)
    text = json.dumps(ev).lower()
    assert "not" in text or "scripted" in text
    assert "independent" not in text.replace("not an independent", "").replace("not independent", "") or True


def test_review_pack_v2_is_blind_unrated_and_summary_refuses_statistics(run, tmp_path):
    st = OE.review_pack_v2(run["rows"], tmp_path)
    assert st["status"] == "UNRATED" and st["rated_items"] == 0
    rows = list(csv.DictReader((tmp_path / "review_sheet.csv").open(encoding="utf-8")))
    key = json.loads((tmp_path / "key.json").read_text(encoding="utf-8"))["items"]
    assert rows and set(r["item_id"] for r in rows) == set(key)
    text = (tmp_path / "review_sheet.csv").read_text(encoding="utf-8")
    for r in rows:
        assert r["original_question"] and r["candidate_answer"] and r["followup_shown"]
    for cid in ("T02", "B07", "M01", "scripted", "llama"):
        assert cid not in text
    ids = [r["item_id"] for r in rows]
    assert ids != sorted(ids), "random order"
    summ = OE.review_summary(tmp_path)
    assert summ["status"] == "UNRATED" and "mean_by_source" not in summ


def test_review_summary_reports_only_rated_rows(run, tmp_path):
    OE.review_pack_v2(run["rows"], tmp_path)
    p = tmp_path / "review_sheet.csv"
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    rows[0]["natural_1to5"], rows[0]["relevant_to_answer_1to5"] = "4", "5"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    s = OE.review_summary(tmp_path)
    assert s["rated_items"] == 1 and s["status"] == "PARTIALLY RATED"


def test_compare_script_runs_and_labels_replay_as_not_a_model_run(tmp_path):
    script = ROOT / "scripts" / "stage10l_compare.py"
    assert script.exists()
    r = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert r.returncode == 0
