"""Stage 9D: performance and reliability of the live follow-up path, against a FAKE Ollama server with scripted timings.

These tests prove behaviour (deadline, real cancellation, prewarm, no cold load inside a turn, single request in flight, back-off, recovery, compact prompt). The delays are scripted:
nothing here measures a real model."""
import json
import time

import pytest

from src.demo import followup_llm as FL, ollama_stream as OS
from src.evaluation.errors import ProviderUnavailable
from tests.app.test_stage9c_followup import ctx, good
from tests.helpers.fake_ollama import FakeOllama


def prov(url, **kw):
    return OS.StreamingOllama("llama3.2:3b", url, **kw)


def wait_for(cond, t=3.0):
    end = time.time() + t
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


# ------------------------------------------------------------------------------------------------ prompt and output size
def test_prompt_and_schema_are_compact_and_carry_no_reference_text():
    c = ctx()
    c.reference = "R" * 3000
    system, user, _ = FL.build_prompt(c)
    assert "RRRR" not in user, "the full reference answer is no longer sent"
    assert FL.estimate_tokens(system, user) < 450
    assert len(json.dumps(FL.build_schema(c))) < 700
    assert set(FL.build_schema(c)["required"]) == {"decision", "question", "purpose", "concept_id"}


def test_prompt_shows_at_most_four_concepts_essential_and_unfound_first():
    many = [{"id": f"E{i}", "label": f"concept number {i}", "tier": "essential" if i < 3 else "supporting", "members": []} for i in range(1, 8)]
    c = ctx(concepts=many)
    shown = [x["id"] for x in FL.shown_concepts(c)]
    assert len(shown) == 4 and shown[:3] == ["E1", "E2", "E3"]
    assert FL.build_schema(c)["properties"]["concept_id"]["enum"] == shown + ["none"]


# ------------------------------------------------------------------------------------------------ the streaming client
def test_streaming_client_returns_text_and_ollama_metrics():
    with FakeOllama(reply=json.dumps(good()), first_delay=0.05) as f:
        r = prov(f.url).generate_bounded("sys", "user", 5)
    assert json.loads(r.text)["decision"] == "ask"
    u = r.usage
    assert u["prompt_eval_count"] == 123 and u["eval_count"] >= 1 and u["first_token_ms"] >= 40 and u["keep_alive"] == "30m" and u["num_ctx"] == 2048
    d = OS.derived(u)
    assert d["generated_tokens"] == u["eval_count"] and d["prompt_tok_per_s"] and d["generate_tok_per_s"]


def test_request_carries_keep_alive_small_ctx_and_hard_token_limit():
    with FakeOllama(reply=json.dumps(good())) as f:
        p = prov(f.url, num_predict=160)
        p.response_schema = {"type": "object"}
        p.generate_bounded("sys", "user", 5)
        body = f.bodies[-1]
    assert body["stream"] is True and body["keep_alive"] == "30m" and body["options"]["num_predict"] == 160 and body["options"]["num_ctx"] == 2048
    assert body["format"] == {"type": "object"} and body["options"]["temperature"] == 0.0


def test_deadline_is_enforced_and_the_server_side_generation_is_cancelled():
    with FakeOllama(reply="x" * 600, first_delay=0.05, token_delay=0.05) as f:
        t0 = time.perf_counter()
        with pytest.raises(OS.DeadlineExceeded) as ei:
            prov(f.url).generate_bounded("s", "u", 0.5)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.5
        assert ei.value.metrics["chunks_received"] >= 1 and ei.value.metrics["first_token_ms"]
        assert wait_for(lambda: f.cancelled == 1 and f.in_flight == 0), "closing the connection must stop the server-side generation"
        assert f.completed == 0


def test_unreachable_and_missing_model_are_clean_errors():
    with pytest.raises(ProviderUnavailable):
        prov("http://127.0.0.1:9").generate_bounded("s", "u", 2)
    with FakeOllama(status=404) as f:
        with pytest.raises(ProviderUnavailable) as ei:
            prov(f.url).generate_bounded("s", "u", 2)
        assert "not found" in str(ei.value)


# ------------------------------------------------------------------------------------------------ the generator on top of it
def live_gen(f, **kw):
    g = FL.LLMFollowUpGenerator(prov(f.url), deadline=kw.pop("deadline", 3), **kw)
    return g


def test_cold_load_never_happens_inside_a_turn():
    with FakeOllama(reply=json.dumps(good()), load_delay=1.0) as f:
        g = live_gen(f)
        t0 = time.perf_counter()
        out = g.propose(ctx())
        assert out.kind == "fallback" and out.reasons == ["model_warming"] and time.perf_counter() - t0 < 0.3, "the first turn falls back immediately instead of waiting for the load"
        assert wait_for(lambda: g.warm_state == "ready", 5)
        assert g.warm_info["load_ms"] >= 900, "the real load time (as the server reports it) is recorded, in the background"
        out = g.propose(ctx())
        assert out.kind == "llm" and out.proposal.question.endswith("?") and out.metrics["generated_tokens"] and out.metrics["prompt_estimate_tokens"] < 450


def test_one_request_in_flight_at_a_time():
    with FakeOllama(reply=json.dumps(good()), first_delay=0.6) as f:
        g = live_gen(f)
        g.start_warm(); assert wait_for(lambda: g.warm_state == "ready")
        import threading
        res = []
        t = threading.Thread(target=lambda: res.append(g.propose(ctx())))
        t.start(); time.sleep(0.15)
        second = g.propose(ctx())
        t.join()
        assert second.reasons == ["model_busy"] and res[0].kind == "llm" and f.max_in_flight == 1


def test_timeouts_open_the_breaker_with_backoff_and_it_recovers():
    with FakeOllama(reply=json.dumps(good()), first_delay=2.0) as f:
        now = [0.0]
        br = FL.CircuitBreaker(threshold=2, cooldown_s=10, clock=lambda: now[0], max_cooldown_s=40)
        g = FL.LLMFollowUpGenerator(prov(f.url), deadline=0.3, breaker=br)
        g.start_warm(); assert wait_for(lambda: g.warm_state == "ready", 4)
        r = [g.propose(ctx()).reasons for _ in range(3)]
        assert r[0] == ["deadline_exceeded"] and r[1] == ["deadline_exceeded"] and r[2] == ["circuit_open"]
        calls = f.requests
        assert g.propose(ctx()).reasons == ["circuit_open"] and f.requests == calls, "an open breaker sends nothing to the model"
        now[0] = 11                                      # cooldown over: one probe, which fails again -> pause doubles
        assert g.propose(ctx()).reasons == ["deadline_exceeded"] and br.cooldown_s == 20
        now[0] = 25
        assert g.propose(ctx()).reasons == ["circuit_open"]
        f.first_delay = 0.0                              # the model recovers
        now[0] = 40
        out = g.propose(ctx())
        assert out.kind == "llm" and br.cooldown_s == 10 and g.propose(ctx()).kind == "llm"


def test_ollama_down_then_back_recovers_after_the_retry_window(monkeypatch):
    monkeypatch.setattr(FL, "WARM_RETRY_S", 0.2)
    with FakeOllama(reply=json.dumps(good())) as up:
        g = FL.LLMFollowUpGenerator(prov("http://127.0.0.1:9"), deadline=2)
        assert g.propose(ctx()).reasons == ["model_warming"]
        assert wait_for(lambda: g.warm_state == "unavailable")
        assert g.propose(ctx()).reasons == ["model_unavailable"]
        g.provider.port = up.port                          # "Ollama started"
        time.sleep(0.3)
        g.propose(ctx())                                   # triggers the retry in the background
        assert wait_for(lambda: g.warm_state == "ready", 3)
        assert g.propose(ctx()).kind == "llm"


def test_missing_model_is_reported_not_retried_in_a_loop():
    with FakeOllama(status=404) as f:
        g = live_gen(f)
        assert g.propose(ctx()).reasons == ["model_warming"]
        assert wait_for(lambda: g.warm_state == "unavailable")
        n = f.requests
        for _ in range(5):
            assert g.propose(ctx()).reasons == ["model_unavailable"]
        assert f.requests == n, "no request storm while unavailable"


def test_truncated_and_invalid_replies_are_rejected_after_generation():
    with FakeOllama(reply='{"decision":"ask","question":"How does an enq') as f:
        g = live_gen(f); g.start_warm(); wait_for(lambda: g.warm_state == "ready")
        assert g.propose(ctx()).reasons == ["invalid_json"]
    with FakeOllama(reply=json.dumps(good(question="How does a ring_buffer13 affect the order you described?"))) as f:
        g = live_gen(f); g.start_warm(); wait_for(lambda: g.warm_state == "ready")
        out = g.propose(ctx())
        assert out.kind == "fallback" and any("novel_terms" in r for r in out.reasons) and out.metrics["generated_tokens"]


def test_unrelated_answer_costs_no_model_call():
    with FakeOllama(reply=json.dumps(good())) as f:
        g = live_gen(f); g.start_warm(); wait_for(lambda: g.warm_state == "ready")
        n = f.requests
        out = g.propose(ctx(answer="My favourite food is pasta and I enjoy hiking at the weekend."))
        assert out.reasons == ["answer_unrelated_to_question"] and f.requests == n


def test_per_model_deadlines_and_model_selection(monkeypatch):
    monkeypatch.delenv("SMART_DEMO_FOLLOWUP_MODEL", raising=False)
    monkeypatch.setenv("SMART_DEMO_FOLLOWUP_DEADLINES", "qwen2.5:7b=45,llama3.2:3b=12")
    assert FL.model_name() == "llama3.2:3b" and FL.deadline_for("qwen2.5:7b") == 45 and FL.deadline_for("llama3.2:3b") == 12 and FL.deadline_for("other") == FL.deadline_s()
    monkeypatch.setenv("SMART_DEMO_FOLLOWUP_MODEL", "qwen2.5:7b")
    assert FL.model_name() == "qwen2.5:7b" and FL.describe()["deadline_s"] == 45


def test_make_generator_uses_the_selected_model_and_never_needs_a_download(monkeypatch):
    monkeypatch.setenv("SMART_DEMO_LIVE_MODULAR", "1")
    monkeypatch.setenv("SMART_DEMO_FOLLOWUP_MODEL", "gemma2:9b")
    monkeypatch.setattr(FL, "_generators", {})
    g = FL.make_generator("live")
    assert g.model == "gemma2:9b" and g.provider.num_predict == FL.NUM_PREDICT_DEFAULT and g.provider.num_ctx == 2048 and g.warm_state == "unknown"


# ------------------------------------------------------------------------------------------------ relevance safeguards (Mission E): hand-written candidate proposals, not model output
@pytest.mark.parametrize("q,answer,ok", [
    ("How does an enqueue operation affect the order you described?", "A queue releases items in the order they arrive.", True),
    ("You said items leave in the order they arrive; when would that ordering matter in a real system?", "A queue releases items in the order they arrive.", True),
    ("Explain enqueue and dequeue operations.", "A queue releases items in the order they arrive.", False),          # generic definition request, nothing from the answer
    ("What is a stack?", "A queue releases items in the order they arrive.", False),                                 # unrelated to what was said
    ("That is incorrect, so what is the actual ordering of a queue?", "A queue releases items in the order they arrive.", False),    # accuses a correct answer
    ("Which hashing algorithm would you use for password storage?", "A queue releases items in the order they arrive.", False),     # new concept outside the evidence
])
def test_generic_accusatory_or_ungrounded_followups_are_rejected(q, answer, ok):
    quote = "in the order they arrive"
    prop, reasons = FL.validate(good(question=q, answer_quote=quote, purpose="deepen", concept_id="none"), ctx(answer=answer))
    assert (prop is not None) == ok, reasons


def test_engine_live_flow_persists_metrics_and_survives_a_restart(app_module, tmp_path, monkeypatch):
    from src.demo import interview as I
    from src.demo.routes import set_engine
    from tests.app.test_stage4a_demo import make_engine
    from tests.app.test_stage9b_interview import create, current, LONG
    for v in ("SMART_DEMO_CODE_EVAL", "SMART_CODEEVAL_EXEC"):
        monkeypatch.delenv(v, raising=False)
    with FakeOllama(reply=lambda req: "ok" if req["options"]["num_predict"] <= 2 else "not json", load_delay=0.1) as f:
        g = FL.LLMFollowUpGenerator(prov(f.url), deadline=2)
        e = make_engine(tmp_path)
        e._followup_generator = g
        set_engine(e)
        app_module.app.config["TESTING"] = True
        with app_module.app.test_client() as c:
            sid = create(c, followup_mode="live")
            assert wait_for(lambda: g.warm_state == "ready", 4), "creating a live interview starts the warm-up in the background"
            for _ in range(40):
                s = e.get(sid)
                if s["status"] == "finished":
                    break
                n, q = current(e, sid)
                r = c.post(f"/demo/api/sessions/{sid}/answer", json={"n": n, "answer": "Hi, I am a data person." if I.stage_of(q) == I.INTRO else LONG})
                assert r.status_code == 200
        s = e.get(sid)
        assert s["status"] == "finished"
        log = s["plan"]["followup_log"]
        assert log and all(x["outcome"] == "fallback" and x["reasons"] and "latency_ms" in x for x in log)
        assert any(x["reasons"] == ["invalid_json"] and x["metrics"].get("generated_tokens") for x in log) or any(x["reasons"] == ["answer_unrelated_to_question"] for x in log)
        e2 = make_engine(tmp_path)                                         # a fresh process reads the same session
        assert e2.get(sid)["plan"]["followup_log"] == log
    set_engine(None)
