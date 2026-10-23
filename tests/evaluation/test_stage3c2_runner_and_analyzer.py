"""The Windows runner and analyzer, exercised end-to-end against a FAKE local Ollama server (stdlib http.server).
This proves the plumbing and the safety refusals only. The fake's replies are canned and say nothing about any real model."""
import importlib.util, json, re, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from tests.evaluation.conftest import llm_json

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


run_mod = _load("run3c2", ROOT / "scripts" / "stage3c2_run.py")
ana = _load("ana3c2", ROOT / "audit" / "evaluation" / "stage3c2_analyze.py")


def make_server(models=("qwen2.5:7b",), chat_mode="ok"):
    seen = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _send(self, obj, code=200):
            data = json.dumps(obj).encode()
            self.send_response(code); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            seen.append(("GET", self.path))
            if self.path == "/api/tags": return self._send({"models": [{"name": m} for m in models]})
            if self.path == "/api/version": return self._send({"version": "0.0-fake"})
            if self.path == "/api/ps": return self._send({"models": [{"name": "qwen2.5:7b", "size": 5_000_000_000, "size_vram": 4_500_000_000}]})
            self._send({}, 404)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
            seen.append(("POST", self.path))
            if self.path in ("/api/show",): return self._send({"details": {"family": "fake"}, "parameters": ""})
            if self.path == "/api/generate": return self._send({"done": True})
            if self.path == "/api/pull": return self._send({"status": "NEVER"})
            system, user = body["messages"][0]["content"], body["messages"][1]["content"]
            if "VERDICTS TO RETURN" in user:
                if chat_mode == "garbage": text = "I cannot comply."
                else:
                    keys = re.findall(r'requirement_id=(\S+) member=("(?:[^"\\]|\\.)*")', user)
                    cids = re.findall(r"^\[(c\d+)\]", user, re.M)
                    vs = []
                    for i, (rid, m) in enumerate(keys):
                        ok = i == 0 and cids
                        vs.append({"requirement_id": rid, "member": json.loads(m), "state": "states_correctly" if ok else "unverified", "claim_ids": [cids[0]] if ok else [],
                                   "explanation": "", "reference_quote": "", "severity": "minor", "proposed_member": ""})
                    text = json.dumps({"verdicts": vs, "on_topic": "on_topic", "reasoning_claim_ids": cids[:1]})
            else:
                text = json.dumps(llm_json((3, 3, 4, 3)))
            self._send({"message": {"content": text}, "done_reason": "stop", "prompt_eval_count": 800, "eval_count": 150, "eval_duration": 3_000_000_000})

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen


@pytest.fixture()
def server():
    made = []
    def mk(**kw):
        s = make_server(**kw); made.append(s[0]); return s
    yield mk
    for s in made: s.shutdown()


def test_dry_run_builds_every_prompt_offline_and_fits_the_context(tmp_path, capsys):
    rc = run_mod.main(["--dry-run", "--out-dir", str(tmp_path / "d.json")])
    doc = json.loads((tmp_path / "d.json").read_text())
    assert rc == 0 and doc["fits_context"] and len(doc["prompts"]) == 20 and doc["max_approx_prompt_tokens"] < 8192 - 1800
    assert doc["meta"]["dry_run"] is True


def test_full_run_against_fake_ollama_writes_audit_trail_and_analyses(tmp_path, server):
    srv, seen = server()
    out = tmp_path / "res"
    assert run_mod.main(["--host", f"http://127.0.0.1:{srv.server_port}", "--out-dir", str(out)]) == 0
    doc = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert len(doc["modular"]) == 40 and len(doc["legacy"]) == 20 and doc["meta"]["partial_run"] is False and doc["meta"]["model_load_s"] >= 0
    assert ("POST", "/api/pull") not in seen and not any("pull" in p or "delete" in p for _, p in seen)           # never downloads
    m0 = doc["modular"][0]
    assert {"result", "verifier_trace", "feedback", "ollama_ps", "wall_ms", "seed"} <= set(m0) and m0["verifier_trace"][0]["raw"]
    assert {r["seed"] for r in doc["modular"]} == {7, 8} and {r["seed"] for r in doc["legacy"]} == {7}
    # analysis
    a = ana.analyze(doc, {}, json.loads((ROOT / "data/evaluation/stage3c2/acceptance_criteria.json").read_text()))
    m = a["metrics"]
    assert m["answers"] == 20 and m["valid_output_rate"] == 1.0 and m["unsupported_completeness_penalties"] == 0 and m["evidence_claim_ids_not_in_answer"] == 0
    assert m["injection_flagged_claims_used_as_evidence"] == 0 and m["peak_ollama_size_vram_bytes"] == 4_500_000_000
    assert {r["result"] for r in a["human_criteria"]} == {"PENDING_HUMAN"} and "accuracy" in a["disclaimer"]
    assert a["decision"] and "PARTIAL" not in a["decision"]
    assert len(a["side_by_side_for_reading_only"]) == 20
    assert "EXPLORATORY" in a["decision"] or "DO NOT ADVANCE" in a["decision"]            # never "advance" without human labels
    assert "# Stage 3C-2 analysis" in ana.to_markdown(a)


def test_model_garbage_is_reported_as_failure_never_as_scores(tmp_path, server):
    srv, _ = server(chat_mode="garbage")
    out = tmp_path / "res"
    run_mod.main(["--host", f"http://127.0.0.1:{srv.server_port}", "--out-dir", str(out), "--skip-legacy"])
    doc = json.loads((out / "results.json").read_text(encoding="utf-8"))
    reached = [m for m in doc["modular"] if m["result"]["status"] not in ("not_gradable",)]
    assert reached and all(m["result"]["status"] == "invalid_response" and m["result"]["score"] is None for m in reached)
    a = ana.analyze(doc, {}, json.loads((ROOT / "data/evaluation/stage3c2/acceptance_criteria.json").read_text()))
    assert a["metrics"]["valid_output_rate"] == 0.0 and "valid_output_rate_min" in [r["criterion"] for r in a["mechanical_criteria"] if r["result"] == "FAIL"]
    assert a["decision"].startswith("DO NOT ADVANCE")


def test_subset_run_is_marked_partial_and_gets_no_decision(tmp_path, server):
    srv, _ = server()
    out = tmp_path / "res"
    run_mod.main(["--host", f"http://127.0.0.1:{srv.server_port}", "--out-dir", str(out), "--ids", "s2-f01,b2-006"])
    doc = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert doc["meta"]["partial_run"] is True and len({m["sample_id"] for m in doc["modular"]}) == 2
    a = ana.analyze(doc, {}, json.loads((ROOT / "data/evaluation/stage3c2/acceptance_criteria.json").read_text()))
    assert a["decision"].startswith("PARTIAL RUN")


def test_runner_refuses_when_model_missing_unreachable_or_wrong(tmp_path, server):
    srv, seen = server(models=("llama3:8b",))
    with pytest.raises(SystemExit) as e:
        run_mod.main(["--host", f"http://127.0.0.1:{srv.server_port}", "--out-dir", str(tmp_path / "a")])
    assert "not installed" in str(e.value) and ("POST", "/api/pull") not in seen
    with pytest.raises(SystemExit) as e:
        run_mod.main(["--host", "http://127.0.0.1:9", "--out-dir", str(tmp_path / "b")])
    assert "Cannot reach Ollama" in str(e.value)
    with pytest.raises(SystemExit) as e:
        run_mod.main(["--model", "llama3:8b", "--host", f"http://127.0.0.1:{srv.server_port}", "--out-dir", str(tmp_path / "c")])
    assert "frozen model" in str(e.value)


def test_runner_refuses_on_freeze_drift_and_never_contacts_the_server(tmp_path, server, monkeypatch):
    srv, seen = server()
    import stage3c2_freeze as fz
    monkeypatch.setattr(fz, "verify", lambda quiet=False: ["modular_code_sha256"])
    with pytest.raises(SystemExit) as e:
        run_mod.main(["--host", f"http://127.0.0.1:{srv.server_port}", "--out-dir", str(tmp_path / "x")])
    assert "REFUSING TO RUN" in str(e.value) and seen == []


def test_existing_results_are_never_overwritten(tmp_path, server):
    srv, _ = server()
    out = tmp_path / "res"; out.mkdir(); (out / "keep.txt").write_text("x")
    with pytest.raises(SystemExit) as e:
        run_mod.main(["--host", f"http://127.0.0.1:{srv.server_port}", "--out-dir", str(out)])
    assert "refusing to overwrite" in str(e.value) and (out / "keep.txt").read_text() == "x"


# ------------------------------------------------------------------------------------------- analyzer unit tests on hand-made results
def _row(sid, status="abstained", score=None, verdicts=(), outcomes=(), claims=None, mode="full", reasons=("x",), rep=0, dims=None, wall=1000):
    claims = claims or [{"id": "c1", "text": "t", "flags": []}, {"id": "c2", "text": "u", "flags": ["possible_instruction"]}]
    return {"sample_id": sid, "repeat": rep, "seed": 7 + rep, "wall_ms": wall, "verifier_trace": [], "ollama_ps": {}, "gpu": None,
            "result": {"question_id": "q", "status": status, "score": score, "penalty_mode": mode, "claims": claims, "verdicts": list(verdicts), "outcomes": list(outcomes),
                       "dimensions": dims if dims is not None else [{"name": "correctness", "level": 4, "derivation": "d"}], "abstain_reasons": list(reasons), "provenance": {}}}


def V(rid, member, state, ev=(), **kw):
    return {"requirement_id": rid, "member": member, "state": state, "evidence": [{"claim_id": c} for c in ev], "original_state": kw.get("orig", ""), "downgrade_reason": kw.get("why")}


CRIT = json.loads((ROOT / "data/evaluation/stage3c2/acceptance_criteria.json").read_text())


def test_analyzer_flags_unsupported_penalties_bad_ids_and_injection_evidence():
    out = {"kind": "concept", "label": "X", "tier": "essential", "requirement_id": "E1", "status": "missing", "detail": {}}
    doc = {"meta": {}, "legacy": [], "modular": [
        _row("a", outcomes=[out], verdicts=[V("E1", "X", "unverified")]),                                # missing penalty NOT backed by not_stated
        _row("b", status="scored", score=80, verdicts=[V("E1", "X", "states_correctly", ev=["c9"])], dims=[{"name": "c", "level": 4, "derivation": ""}]),
        _row("c", verdicts=[V("E1", "X", "states_correctly", ev=["c2"])], reasons=())]}
    m = ana.analyze(doc, {}, CRIT)["metrics"]
    assert m["unsupported_completeness_penalties"] == 1 and m["evidence_claim_ids_not_in_answer"] == 1
    assert m["scored_results_without_derivation"] == 1 and m["injection_flagged_claims_used_as_evidence"] == 1 and m["abstentions_without_recorded_reason"] == 1


def test_analyzer_accepts_a_penalty_backed_by_not_stated_and_group_by_other_valid():
    c = {"kind": "concept", "label": "X", "tier": "essential", "requirement_id": "E1", "status": "missing", "detail": {}}
    g = {"kind": "group", "label": "G", "tier": "essential", "requirement_id": "G1", "status": "missing", "detail": {}}
    doc = {"meta": {}, "legacy": [], "modular": [_row("a", outcomes=[c, g], verdicts=[V("E1", "X", "not_stated"), V("G1", "m1", "unverified"), V("G1", "__other_valid__", "not_stated")])]}
    assert ana.analyze(doc, {}, CRIT)["metrics"]["unsupported_completeness_penalties"] == 0


def test_analyzer_never_penalises_advisory_records_and_measures_stability_and_gate_rate():
    out = {"kind": "concept", "label": "X", "tier": "essential", "requirement_id": "E1", "status": "missing", "detail": {}}
    doc = {"meta": {}, "legacy": [], "modular": [
        _row("a", mode="advisory", outcomes=[out], verdicts=[V("E1", "X", "unverified", orig="states_correctly", why="no evidence")], rep=0, status="scored", score=90),
        _row("a", mode="advisory", outcomes=[out], verdicts=[V("E1", "X", "states_correctly", ev=["c1"])], rep=1, status="scored", score=70)]}
    m = ana.analyze(doc, {}, CRIT)["metrics"]
    assert m["essential_missing_penalties"] == 0 and m["gate_downgrade_rate"] == 0.5 and m["repeat_member_state_agreement"] == 0.0 and m["repeat_score_delta_max_points"] == 20
    a = ana.analyze(doc, {}, CRIT)
    assert {r["criterion"]: r["result"] for r in a["mechanical_criteria"]}["repeat_member_state_agreement_min"] == "FAIL" and a["decision"].startswith("DO NOT ADVANCE")


def test_analyzer_never_reports_human_agreement_or_accuracy():
    doc = {"meta": {}, "legacy": [], "modular": [_row("a")]}
    a = ana.analyze(doc, {"a": {"kind": "correct_full", "expected_score_min": 90, "expected_score_max": 100}}, CRIT)
    txt = json.dumps(a).lower()
    assert "agreement_with" not in txt and "accuracy\":" not in txt and a["side_by_side_for_reading_only"][0]["ai_provisional_score_range"] == [90, 100]
