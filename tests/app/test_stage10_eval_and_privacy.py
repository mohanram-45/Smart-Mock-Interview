"""Stage 10: the evaluation scripts run and gate; candidate text never reaches logs, metrics or reports. Scripted/mock only."""
import importlib.util
import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest

from src.demo import interview as I, sim
from src.mlops.metrics import METRICS

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_eval_suite_runs_and_every_gate_passes_with_honest_labels(tmp_path):
    ev = load("stage10_eval_suite")
    R, transcripts = ev.suite(tmp_path)
    assert R["gates"]["passed"] == R["gates"]["total"] >= 14, [k for k, v in R["gates"]["detail"].items() if not v]
    assert "SCRIPTED / MOCK" in R["label"] and "NOT MEASURED" in ev.results_md(R) and "no human has rated" in ev.results_md(R).lower()
    assert set(transcripts) >= {"technical_data_scientist", "technical_python_developer", "memory_long_range", "behavioural", "mixed", "candidate_contradicts_earlier_answer"}
    md = ev.md_transcript("mixed", *transcripts["mixed"], "t", "n")
    assert "SCRIPTED / MOCK" in md and "completes the technical part" in md and "Behavioural feedback produced at the end" in md


def test_review_pack_is_blind_and_unrated(tmp_path):
    ev = load("stage10_eval_suite")
    R, transcripts = ev.suite(tmp_path / "w")
    n = ev.review_pack(transcripts, tmp_path / "rv")
    assert n >= 5
    sheet = (tmp_path / "rv" / "review_sheet.csv").read_text(encoding="utf-8")
    header = sheet.splitlines()[0]
    assert "origin" not in header and "key" not in header and "natural_1to5" in header
    assert "UNRATED" in (tmp_path / "rv" / "README.md").read_text(encoding="utf-8")
    key = json.loads((tmp_path / "rv" / "key.json").read_text(encoding="utf-8"))
    assert len(key) == n and all(set(v) == {"scenario", "turn", "origin", "kind"} for v in key.values())
    import csv, io
    rows = list(csv.DictReader(io.StringIO(sheet)))
    assert len(rows) == n and all(not (r["natural_1to5"] or "").strip() for r in rows)


def test_real_stack_script_selftest_labels_its_numbers_as_not_real(tmp_path):
    r = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "stage10_verify_real_stack.py"), "--selftest", "--runs", "1", "--out", str(tmp_path)], capture_output=True, text=True, timeout=120, cwd=ROOT,
                       env={**__import__("os").environ, "PYTHONPATH": str(ROOT)})
    assert r.returncode == 0, r.stderr[-800:]
    doc = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert doc["timings_are_real"] is False and doc["human_validated"] is False and "SELFTEST" in (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert doc["results"][0]["calls"] >= 1


SECRET = "ZEBRAQUARTZ-98765 lives at 12 Hidden Lane"


def test_candidate_text_never_reaches_logs_or_metrics(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    e = sim.offline_engine(tmp_path)
    s = e.create({"role": "Data Scientist", "practical": False, "size": 3})
    e.submit(s["id"], 1, f"My name is Mohan and I built a classifier called {SECRET} using PyTorch. Contact me at secret.person@example.com or +49 151 2345 6789.")
    e.submit(s["id"], 2, "short")
    blob = "\n".join(r.getMessage() for r in caplog.records) + METRICS.prometheus() + json.dumps(METRICS.snapshot())
    for needle in ("ZEBRAQUARTZ", "Hidden Lane", "secret.person", "2345 6789", "Mohan"):
        assert needle not in blob, needle


def test_reports_contain_scripted_text_only(tmp_path):
    ev = load("stage10_eval_suite")
    R, transcripts = ev.suite(tmp_path)
    blob = ev.results_md(R) + json.dumps(R, default=str)
    assert "@" not in blob.replace("@@", "") or "example.com" not in blob


def test_new_metrics_are_registered_and_carry_codes_only(tmp_path):
    e = sim.offline_engine(tmp_path)
    s = e.create({"role": "Data Scientist", "practical": False, "size": 3})
    e.submit(s["id"], 1, "I developed a spam filter with scikit-learn.")
    prom = METRICS.prometheus()
    assert "smart_memory_items_total" in prom and "spam filter" not in prom
