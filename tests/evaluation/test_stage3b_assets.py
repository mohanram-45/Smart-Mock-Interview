"""Stage 3B assets: benchmark integrity and script plumbing. No real model is used; the --selftest run is a scripted mock."""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from src.retrieval.corpus import load_corpus

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "evaluation" / "bench_v1"


def jl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_benchmark_is_aligned_and_separated():
    items, exps = jl(BENCH / "items.jsonl"), jl(BENCH / "expectations.jsonl")
    assert 30 <= len(items) <= 50 and [i["item_id"] for i in items] == [e["item_id"] for e in exps]
    ids = {r["question_id"]: r for r in load_corpus()["records"]}
    assert all(i["question_id"] in ids for i in items)
    for i in items:                                                    # inputs never contain judgments
        assert set(i) == {"item_id", "question_id", "category", "candidate_answer"}
    for e in exps:
        assert e["label_source"] == "ai_authored_by_claude_unreviewed"
        if e["score_min"] is not None:
            assert 0 <= e["score_min"] <= e["score_max"] <= 100
    cats = Counter(i["category"] for i in items)
    for needed in ("correct", "partial", "incorrect", "valid_alternative", "short_sufficient", "confident_inaccurate", "off_topic", "empty", "injection", "weak_reference"):
        assert cats[needed] >= 1, needed
    assert len({ids[i["question_id"]]["domain"] for i in items}) >= 6


def test_benchmark_answers_do_not_copy_the_reference_verbatim():
    from src.evaluation.evaluator import AnswerEvaluator
    ids = {r["question_id"]: r for r in load_corpus()["records"]}
    for i in jl(BENCH / "items.jsonl"):
        if i["candidate_answer"]:
            assert not AnswerEvaluator._copies_reference(i["candidate_answer"], ids[i["question_id"]]["canonical_answer"], window=80), i["item_id"]


def test_runner_refuses_to_run_without_a_reachable_server_and_never_downloads(tmp_path):
    r = subprocess.run([sys.executable, "scripts/stage3b_run.py", "--model", "x", "--host", "http://127.0.0.1:1", "--out-dir", str(tmp_path)],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode != 0 and "Cannot reach Ollama" in (r.stderr + r.stdout) and not list(tmp_path.iterdir())


def test_selftest_pipeline_runs_end_to_end_and_is_labelled_mock(tmp_path):
    r = subprocess.run([sys.executable, "scripts/stage3b_run.py", "--selftest", "--set", "smoke", "--out-dir", str(tmp_path)], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    runs = tmp_path / "runs_SELFTEST-MOCK.json"
    doc = json.loads(runs.read_text(encoding="utf-8"))
    assert doc["meta"]["is_mock"] is True and len(doc["runs"]) == 12 and all(x["result"]["provenance"]["is_mock"] for x in doc["runs"])
    a = subprocess.run([sys.executable, "audit/evaluation/stage3b_analyze.py", str(runs)], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert a.returncode == 0, a.stderr
    assert "SAY NOTHING" in a.stdout.upper() or "NOTHING ABOUT ANY REAL MODEL" in a.stdout.upper() or "SAYS NOTHING" in a.stdout.upper()
    assert (tmp_path / "analysis_SELFTEST-MOCK.json").exists() and (tmp_path / "review_sheet_SELFTEST-MOCK.csv").exists()


def test_probe_script_is_read_only_and_degrades_without_ollama(tmp_path):
    src = (ROOT / "scripts" / "stage3b_probe_ollama.py").read_text(encoding="utf-8")
    for forbidden in ("/api/pull", "/api/create", "/api/delete", "ollama pull", '"pull"', "winget", "pip install"):
        assert forbidden not in src
    committed = ROOT / "data" / "evaluation" / "stage3b" / "ollama_probe.json"
    before = committed.read_bytes() if committed.exists() else None
    out = tmp_path / "probe.json"
    env = {**__import__("os").environ, "OLLAMA_HOST": "http://127.0.0.1:1", "SMART_PROBE_OUT": str(out)}
    r = subprocess.run([sys.executable, "scripts/stage3b_probe_ollama.py"], cwd=ROOT, capture_output=True, text=True, timeout=60, env=env)
    assert r.returncode == 0 and '"server_reachable": false' in r.stdout
    assert out.exists()  # Stage 7B regression: the probe used to overwrite the committed evidence file on every test run
    assert (committed.read_bytes() if committed.exists() else None) == before
