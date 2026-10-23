"""Regression tests from the Stage 3C-2 pilot diagnosis.
Part A pins FACTS about the recorded pilot (skipped if the pilot file is absent). Part B covers the v2 fixes against a fake Ollama that simulates the
context-size reload. No real model is called; nothing here infers grading accuracy."""
import importlib.util, json, re, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from tests.evaluation.conftest import llm_json

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
PILOT = ROOT / "data" / "evaluation" / "stage3c2_results" / "20261015T113555Z" / "results.json"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


a2 = _load("a2_3c2", ROOT / "audit" / "evaluation" / "stage3c2_analyze_v2.py")
run1 = _load("run1_3c2", ROOT / "scripts" / "stage3c2_run.py")
run2 = _load("run2_3c2", ROOT / "scripts" / "stage3c2_run_v2.py")
import stage3c2_freeze as fz1          # noqa: E402
import stage3c2_freeze_v2 as fz2       # noqa: E402

CRIT = json.loads((ROOT / "data/evaluation/stage3c2/acceptance_criteria.json").read_text())
pilot = pytest.mark.skipif(not PILOT.exists(), reason="pilot results file not present")


@pytest.fixture(scope="module")
def doc():
    return json.loads(PILOT.read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------------ Part A: facts about the pilot
@pilot
def test_pilot_is_labelled_partial_and_ran_on_the_v1_freeze(doc):
    assert doc["meta"]["partial_run"] is True and len(doc["modular"]) == 4 and len(doc["legacy"]) == 2
    assert doc["meta"]["freeze_manifest_sha256"] == fz1.sha_file(fz1.MANIFEST)            # the manifest it ran under is the one on disk now
    a = a2.analyze_v2(doc, {}, CRIT)
    assert a["decision"].startswith("PARTIAL RUN")
    assert all(r["result"].startswith("NOT_EVALUATED_PARTIAL_RUN") for r in a["mechanical_criteria"])


@pilot
def test_the_83_percent_is_one_member_and_it_is_a_model_disagreement(doc):
    ra = a2.repeat_mismatches(doc)
    assert ra["members_compared"] == 6 and ra["agreement_after_gate"] == 0.8333 and ra["agreement_before_gate"] == 0.8333 and len(ra["mismatches"]) == 1
    x = ra["mismatches"][0]
    assert (x["sample_id"], x["requirement_id"], x["member"], x["tier"]) == ("s2-f01", "E1", "O(log n)", "essential")
    assert (x["repeat0_model"], x["repeat1_model"]) == ("states_incorrectly", "not_stated") and x["differs_before_gate"]          # the MODEL disagreed with itself
    assert x["repeat0_after_gate"] == "unverified" and x["repeat0_downgrade"] == "no_valid_evidence" and x["repeat1_after_gate"] == "not_stated"
    raw0 = json.loads(next(m for m in doc["modular"] if m["sample_id"] == "s2-f01" and m["repeat"] == 0)["verifier_trace"][0]["raw"])
    v = raw0["verdicts"][0]
    assert v["state"] == "states_incorrectly" and v["claim_ids"] == [] and "Does not state" in v["explanation"]               # an omission mislabelled as an error


@pilot
def test_gate_did_its_job_on_the_mislabelled_omission(doc):
    r0 = next(m for m in doc["modular"] if m["sample_id"] == "s2-f01" and m["repeat"] == 0)["result"]
    e1 = next(v for v in r0["verdicts"] if v["requirement_id"] == "E1")
    assert e1["state"] == "unverified" and not any(o["status"] == "incorrect" for o in r0["outcomes"])           # never reported as the candidate's error


@pilot
def test_offtopic_abstention_cause_and_that_the_cap_makes_the_score_unique(doc):
    from src.evaluation.modular.rubric_engine import _cap, _score
    for m in (x for x in doc["modular"] if x["sample_id"] == "s2-f01"):
        r = m["result"]
        assert r["status"] == "abstained" and "correctness undetermined" in r["abstain_reasons"] and r["error"] is None
        rel = next(d for d in r["dimensions"] if d["name"] == "relevance")
        assert rel["level"] == 0 and rel["inputs"]["on_topic_verifier"] == "off_topic" and rel["inputs"]["lexical_overlap"] == 0.0
    finals = set()
    for c in range(5):
        for comp in range(5):
            lv = {"correctness": c, "completeness": comp, "relevance": 0, "reasoning": 4}
            finals.add(_cap(_score(lv), lv, ())[0])
    assert finals == {10}          # existing relevance=0 cap: every resolution of the undetermined dimensions ends at 10 (documents a PROPOSAL basis only)


@pilot
def test_b2_006_full_marks_are_mechanically_consistent_and_evidence_ids_exist(doc):
    for m in (x for x in doc["modular"] if x["sample_id"] == "b2-006"):
        r = m["result"]; ids = {c["id"] for c in r["claims"]}
        assert r["score"] == 100 and r["confidence"] == "high" and {d["name"]: d["level"] for d in r["dimensions"]} == {"correctness": 4, "completeness": 4, "relevance": 4, "reasoning": 4}
        assert all(e["claim_id"] in ids for v in r["verdicts"] for e in v["evidence"]) and all(v["state"] == "states_correctly" for v in r["verdicts"])
        reasoning = next(d for d in r["dimensions"] if d["name"] == "reasoning")
        assert reasoning["inputs"] == {"expected": False} and "convention" in reasoning["derivation"]               # 15 points are by convention, not evidence


@pilot
def test_known_limitation_credit_is_not_lexically_cross_checked_and_stemmer_is_crude(doc):
    from src.evaluation.modular.claims import content_stems
    assert content_stems("convolution") != content_stems("convolutional") and content_stems("regularization") != content_stems("regularisation")
    r = next(x for x in doc["modular"] if x["sample_id"] == "b2-006")["result"]
    e1 = next(v for v in r["verdicts"] if v["requirement_id"] == "E1")
    assert e1["claim_ids"] == ["c1"] and "convolutional" not in next(c for c in r["claims"] if c["id"] == "c1")["text"].lower()      # credited on a derived form of the word


@pilot
def test_cold_load_is_detected_and_excluded_from_warm_latency(doc):
    cc = a2.cold_calls(doc)
    assert [(c["kind"], c["sample_id"], c["repeat"]) for c in cc] == [("modular", "b2-006", 0)] and cc[0]["load_s"] > 60
    w = a2.warm_latency(doc)
    assert w["modular_warm"]["n"] == 3 and w["modular_warm"]["max_s"] < 30 and w["excluded_cold_calls"] == 1


@pilot
def test_pilot_shows_the_warmup_context_defect(doc):
    c = a2.warmup_context(doc)
    assert c == {"frozen_num_ctx": 8192, "context_length_after_warmup": 4096, "matches": False}


# ------------------------------------------------------------------------------------------------ Part B: v2 fix against a context-simulating fake
def make_server(ignore_ctx=False):
    st = {"loaded": None, "generate_bodies": [], "chat_loads": [], "paths": []}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _send(self, obj, code=200):
            data = json.dumps(obj).encode()
            self.send_response(code); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            st["paths"].append(self.path)
            if self.path == "/api/tags": return self._send({"models": [{"name": "qwen2.5:7b"}]})
            if self.path == "/api/version": return self._send({"version": "fake"})
            if self.path == "/api/ps": return self._send({"models": [{"name": "qwen2.5:7b", "context_length": st["loaded"], "size_vram": 1}]})
            self._send({}, 404)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
            st["paths"].append(self.path)
            if self.path == "/api/show": return self._send({"details": {}, "parameters": ""})
            if self.path == "/api/generate":
                st["generate_bodies"].append(body); st["loaded"] = 4096 if ignore_ctx else (body.get("options") or {}).get("num_ctx", 4096); return self._send({"done": True})
            ctx = body["options"]["num_ctx"]
            load = 70_000_000_000 if st["loaded"] != ctx else 200_000_000
            st["chat_loads"].append(load); st["loaded"] = ctx
            user = body["messages"][1]["content"]
            if "VERDICTS TO RETURN" in user:
                keys = re.findall(r'requirement_id=(\S+) member=("(?:[^"\\]|\\.)*")', user); cids = re.findall(r"^\[(c\d+)\]", user, re.M)
                vs = [{"requirement_id": r, "member": json.loads(m), "state": "unverified", "claim_ids": [], "explanation": "", "reference_quote": "", "severity": "minor", "proposed_member": ""} for r, m in keys]
                text = json.dumps({"verdicts": vs, "on_topic": "on_topic", "reasoning_claim_ids": cids[:1]})
            else:
                text = json.dumps(llm_json((3, 3, 4, 3)))
            self._send({"message": {"content": text}, "done_reason": "stop", "prompt_eval_count": 800, "eval_count": 100, "eval_duration": 1_000_000_000, "load_duration": load})

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, st


@pytest.fixture()
def fake():
    srv, st = make_server(); yield srv, st; srv.shutdown()


def test_defect_reproduced_offline_with_v1_runner(fake, tmp_path):
    srv, st = fake
    run1.main(["--host", f"http://127.0.0.1:{srv.server_port}", "--out-dir", str(tmp_path / "r"), "--ids", "s2-f01", "--skip-legacy"])
    assert "options" not in st["generate_bodies"][0] and st["chat_loads"][0] >= 70_000_000_000            # v1: warm-up at default context, first real call reloads


def test_v2_runner_warms_up_with_the_frozen_context_so_no_call_reloads(fake, tmp_path):
    srv, st = fake
    run2.main(["--host", f"http://127.0.0.1:{srv.server_port}", "--out-dir", str(tmp_path / "r"), "--ids", "s2-f01,b2-006"])
    assert st["generate_bodies"][0]["options"] == {"num_ctx": 8192} and st["generate_bodies"][0]["keep_alive"] == "30m"
    assert max(st["chat_loads"]) < 1_000_000_000 and len(st["chat_loads"]) == 2 * 2 + 2                  # 2 answers x (2 modular + 1 legacy)
    doc = json.loads((tmp_path / "r" / "results.json").read_text(encoding="utf-8"))
    a = a2.analyze_v2(doc, {}, CRIT)
    assert a["cold_calls"] == [] and a["warmup_context_check"]["matches"] is True and a["warm_latency"]["excluded_cold_calls"] == 0
    assert all(r["result"].startswith("NOT_EVALUATED_PARTIAL_RUN") for r in a["mechanical_criteria"]) and a["decision"].startswith("PARTIAL RUN")
    assert "v2 diagnostics" in a2.to_markdown_v2(a)


def test_v2_warns_loudly_if_ollama_still_reports_another_context(tmp_path, capsys):
    srv, st = make_server(ignore_ctx=True)
    try:
        run2.main(["--host", f"http://127.0.0.1:{srv.server_port}", "--out-dir", str(tmp_path / "r"), "--ids", "s2-f01", "--skip-legacy"])
    finally:
        srv.shutdown()
    out = capsys.readouterr().out
    assert "WARNING: Ollama reports context_length=4096" in out and "frozen num_ctx is 8192" in out
    doc = json.loads((tmp_path / "r" / "results.json").read_text(encoding="utf-8"))
    assert a2.warmup_context(doc)["matches"] is False and a2.cold_calls(doc)                      # and the analyzer records both symptoms


def test_v2_refuses_on_any_drift_before_contacting_the_server(fake, tmp_path, monkeypatch):
    srv, st = fake
    monkeypatch.setattr(fz2, "verify", lambda quiet=False: ["v1:modular_code_sha256"])
    with pytest.raises(SystemExit) as e:
        run2.main(["--host", f"http://127.0.0.1:{srv.server_port}", "--out-dir", str(tmp_path / "x")])
    assert "REFUSING TO RUN" in str(e.value) and st["paths"] == []


# ------------------------------------------------------------------------------------------------ freeze integrity (v1 intact, v2 layered)
def test_v1_freeze_is_intact_and_v2_freeze_verifies():
    assert fz1.verify(quiet=True) == [] and fz2.verify(quiet=True) == []


def test_v2_changes_nothing_that_defines_the_experiment():
    m2 = json.loads(fz2.MANIFEST_V2.read_text(encoding="utf-8")); m1 = json.loads(fz1.MANIFEST.read_text(encoding="utf-8"))
    assert m2["supersedes"]["manifest_sha256"] == fz1.sha_file(fz1.MANIFEST) and m2["pilot"]["used_to_tune"] == "nothing" and m2["version"] == "3c2.1"
    for k, v in m2["unchanged_since_v1"].items():
        assert m1["fingerprints"][k] == v
    assert m2["acceptance_criteria_sha256"] == m1["fingerprints"]["protocol_files_sha256"]["data/evaluation/stage3c2/acceptance_criteria.json"] == fz1.sha_file(ROOT / "data/evaluation/stage3c2/acceptance_criteria.json")
    assert set(m2["v2_files_sha256"]) == set(fz2.V2_FILES) and not any("analyze.py" in f or "run.py" in f for f in m2["v2_files_sha256"])        # v1 runner/analyzer are not edited


def test_v2_tooling_does_not_touch_scoring_code_or_thresholds():
    for f in ("scripts/stage3c2_run_v2.py", "audit/evaluation/stage3c2_analyze_v2.py"):
        t = (ROOT / f).read_text(encoding="utf-8")
        assert "rubric_engine" not in t and "WEIGHTS" not in t and "_cap(" not in t
    t = (ROOT / "audit/evaluation/stage3c2_analyze_v2.py").read_text(encoding="utf-8")
    assert not any(k in t for k in CRIT["mechanical"] if not k.startswith("_"))                      # thresholds are only ever read from the frozen JSON by the v1 analyzer
