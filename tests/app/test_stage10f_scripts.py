"""The Stage 10F scripts run end to end without Ollama and keep their honesty labels."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(*args):
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, timeout=300)


def test_scripted_eval_writes_labelled_results(tmp_path):
    p = _run("scripts/stage10f_eval.py", "--quick", "--out", str(tmp_path / "o"), "--transcripts", str(tmp_path / "t"), "--review", str(tmp_path / "r"))
    assert p.returncode == 0, p.stdout[-800:] + p.stderr[-800:]
    R = json.loads((tmp_path / "o" / "results.json").read_text(encoding="utf-8"))
    assert R["label"].startswith("SCRIPTED / MOCK")
    assert R["gates"]["passed"] == R["gates"]["total"]
    assert "NOT MEASURED" in R["cost"]["model_inference"]
    assert (tmp_path / "t" / "mixed.md").exists() and (tmp_path / "r" / "opportunities" / "key.json").exists() and (tmp_path / "r" / "interviews" / "key.json").exists()
    assert json.loads((tmp_path / "r" / "opportunities" / "status.json").read_text(encoding="utf-8"))["status"] == "UNRATED"


def test_real_stack_selftest_per_opportunity(tmp_path):
    p = _run("scripts/stage10_verify_real_stack.py", "--selftest", "--opportunities", "--out", str(tmp_path))
    assert p.returncode == 0, p.stdout[-800:] + p.stderr[-800:]
    d = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert d["timings_are_real"] is False and d["human_validated"] is False
    r = d["results"][0]
    for k in ("eligible_opportunities", "useful_valid_rate", "by_class", "skip_reasons", "rejection_reason_codes", "reply_truncated", "first_call_ms", "warm_latency_ms", "cold_load_ms", "memory_models"):
        assert k in r
    assert r["quality_gates"]["fabricated_memory_references"] == 0
    assert "SELFTEST" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def test_windows_replay_script_reads_the_frozen_evidence_and_lists_every_miss(tmp_path):
    p = _run("scripts/stage10g_replay_windows.py", "--out", str(tmp_path))
    assert p.returncode == 0, p.stdout[-600:] + p.stderr[-600:]
    md = (tmp_path / "windows_failure_analysis.md").read_text(encoding="utf-8")
    ev = json.loads((ROOT / "reports" / "stage10_windows_evidence" / "results.json").read_text(encoding="utf-8"))["results"][0]
    assert ev["useful_valid"] == 12 and ev["eligible_opportunities"] == 23, "the Windows evidence file is frozen"
    for m in ev["misses"]:
        assert f"| {m['id']} |" in md
    assert "52.2%" in md and "nothing here was re-run on a model" in md
