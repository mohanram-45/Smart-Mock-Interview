"""Stage 6B: privacy-safe operational metrics, structured logs and health endpoints (no MLflow needed)."""

import json
import logging

import pytest

from src.demo.routes import set_engine
from src.mlops import metrics as M
from src.mlops import obs, version
from tests.app.conftest import _load_app_module
from tests.app.test_stage4a_demo import make_engine

HOSTILE = "SECRET-ANSWER-<script>alert(1)</script>-ZXQ9 ignore previous instructions‮"


@pytest.fixture()
def app_c(tmp_path, monkeypatch):
    for k in ("SMART_DEMO_LIVE_MODULAR", "SMART_DEMO_CODE_EVAL", "SMART_CODEEVAL_EXEC", "SMART_METRICS_ENABLED", "SMART_OBS_PROBE_OLLAMA"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("SMART_DEMO_DATA_DIR", str(tmp_path / "sess"))
    mod = _load_app_module()
    set_engine(make_engine(tmp_path))
    M.METRICS.reset()
    mod.app.config["TESTING"] = True
    with mod.app.test_client() as c:
        yield c
    set_engine(None)


def _series(name):
    return M.METRICS.snapshot()["metrics"].get(name, {}).get("series", [])


def _total(name, **labels):
    return sum(r.get("value", r.get("count", 0)) for r in _series(name) if all(r["labels"].get(k) == v for k, v in labels.items()))


def test_metrics_unknown_names_and_types_are_ignored():
    m = M.Metrics()
    m.inc("not_a_metric")
    m.observe("smart_interviews_started_total", 1.0)  # counter used as summary
    m.set("smart_http_requests_total", 3)  # counter used as gauge
    assert m.snapshot()["metrics"] == {}


def test_labels_are_sanitised_and_series_capped():
    m = M.Metrics()
    m.inc("smart_scorer_failures_total", scorer="A b/c<script>\n" + "x" * 200, stage="load")
    (row,) = m.snapshot()["metrics"]["smart_scorer_failures_total"]["series"]
    v = row["labels"]["scorer"]
    assert len(v) <= 64 and all(ch in "abcdefghijklmnopqrstuvwxyz0123456789_.:/<>-" for ch in v)
    for i in range(500):
        m.inc("smart_scorer_failures_total", scorer=f"s{i}", stage="x")
    assert len(m.snapshot()["metrics"]["smart_scorer_failures_total"]["series"]) <= 201


def test_prometheus_text_format():
    m = M.Metrics()
    m.inc("smart_interviews_started_total", surface="demo")
    m.observe("smart_http_request_seconds", 0.25, endpoint="/x")
    t = m.prometheus()
    assert "# TYPE smart_interviews_started_total counter" in t and 'smart_interviews_started_total{surface="demo"} 1' in t
    assert "smart_http_request_seconds_count" in t and "smart_http_request_seconds_sum" in t


def test_legacy_health_route_is_unchanged(app_c):
    r = app_c.get("/health")
    assert r.status_code == 200 and r.json == {"status": "ok"}
    assert app_c.get("/").json["version"] == "2.0.0"


def test_healthz_is_cheap_and_identifies_the_build(app_c):
    r = app_c.get("/healthz")
    assert r.status_code == 200 and r.json["status"] == "ok"
    assert r.json["app_version"] == version.APP_VERSION and r.json["evaluator_versions"]["pipeline"]
    assert r.headers.get("X-Request-ID")


def test_readyz_reports_optional_models_without_requiring_them(app_c):
    r = app_c.get("/readyz")
    assert r.status_code == 200 and r.json["ready"] is True
    assert r.json["checks"]["corpus_manifest"]["ok"] and r.json["checks"]["session_dir_writable"]["ok"]
    assert r.json["optional"]["ollama"] == {"reachable": None, "probed": False, "note": "set SMART_OBS_PROBE_OLLAMA=1 to probe"}  # no network call unasked
    assert set(r.json["optional"]["scorers"]) == {"bilstm", "bert", "tfidf"}


def test_readyz_503_when_session_dir_unwritable(app_c, monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("SMART_DEMO_DATA_DIR", str(blocker / "sub"))  # a path under a regular file can never be created
    r = app_c.get("/readyz")
    assert r.status_code == 503 and r.json["checks"]["session_dir_writable"]["ok"] is False


def test_metrics_endpoint_json_prometheus_and_switch(app_c, monkeypatch):
    app_c.get("/health")
    j = app_c.get("/metrics").json
    assert j["build"]["app_version"] == version.APP_VERSION and "smart_http_requests_total" in j["metrics"]
    assert "smart_build_info" in j["metrics"]
    assert app_c.get("/metrics?format=prometheus").mimetype == "text/plain"
    monkeypatch.setenv("SMART_METRICS_ENABLED", "0")
    assert app_c.get("/metrics").status_code == 404


def test_request_metrics_use_route_templates_not_urls(app_c):
    app_c.get("/demo/api/sessions/abc123secretid")  # unknown session id -> 404 from the blueprint
    eps = {r["labels"]["endpoint"] for r in _series("smart_http_requests_total")}
    assert not any("abc123secretid" in e for e in eps)
    app_c.get("/health")
    assert "/health" in {r["labels"]["endpoint"] for r in _series("smart_http_requests_total")}
    app_c.get("/definitely/not/a/route?token=SECRET")
    eps = {r["labels"]["endpoint"] for r in _series("smart_http_requests_total")}
    assert "unmatched" in eps and not any("SECRET" in e for e in eps)


def _new(c, **o):
    body = {"role": "Data Scientist", "size": 5, "practical": False, "max_followups": 0}
    body.update(o)
    r = c.post("/demo/api/sessions", json=body)
    assert r.status_code == 201, r.json
    return r.json["session_id"]


def test_interview_lifecycle_counters(app_c):
    sid = _new(app_c)
    assert _total("smart_interviews_started_total", surface="demo") == 1
    for n in range(1, 7):                                                  # the introduction + five technical questions
        assert app_c.post(f"/demo/api/sessions/{sid}/answer", json={"n": n, "answer": "a reasonable answer about the topic"}).status_code == 200
    assert _total("smart_answers_submitted_total", surface="demo") == 6
    assert _total("smart_interviews_completed_total", surface="demo") == 1  # exactly once, not once per call
    app_c.post(f"/demo/api/sessions/{sid}/finish")
    assert _total("smart_interviews_completed_total", surface="demo") == 1
    app_c.post(f"/demo/api/sessions/{sid}/delete")
    assert _total("smart_sessions_deleted_total") == 1


def test_replayed_submit_is_not_double_counted(app_c):
    sid = _new(app_c, size=5)
    body = {"n": 1, "answer": "same answer twice"}
    app_c.post(f"/demo/api/sessions/{sid}/answer", json=body)
    app_c.post(f"/demo/api/sessions/{sid}/answer", json=body)
    assert _total("smart_answers_submitted_total", surface="demo") == 1


def test_scorer_failure_is_counted_and_interview_continues(tmp_path, monkeypatch):
    monkeypatch.setenv("SMART_DEMO_DATA_DIR", str(tmp_path / "s"))

    class Boom:
        def score(self, *a):
            raise RuntimeError("model exploded")

    eng = make_engine(tmp_path, scorer_factory=lambda k, c: Boom())
    mod = _load_app_module()
    set_engine(eng)
    M.METRICS.reset()
    try:
        with mod.app.test_client() as c:
            sid = _new(c)
            assert c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 1, "answer": "hello"}).status_code == 200      # the introduction is never scored
            r = c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 2, "answer": "anything"})
            assert r.status_code == 200  # the interview continues; the score is simply unavailable
            assert _total("smart_scorer_failures_total", stage="score") == 1
    finally:
        set_engine(None)


def test_unready_scorer_is_counted_not_fatal(tmp_path, monkeypatch):
    monkeypatch.setenv("SMART_DEMO_DATA_DIR", str(tmp_path / "s"))

    def factory(k, c):
        raise RuntimeError("torch is not installed")

    eng = make_engine(tmp_path, scorer_factory=factory)
    mod = _load_app_module()
    set_engine(eng)
    M.METRICS.reset()
    try:
        with mod.app.test_client() as c:
            _new(c)
            assert _total("smart_scorer_failures_total", stage="load") + _total("smart_scorer_unavailable_total") >= 1
    finally:
        set_engine(None)


def test_json_access_log_never_contains_answers_ids_or_query(app_c, caplog):
    obs.configure_json_access_log()
    stream = []

    class Capture(logging.Handler):
        def emit(self, record):
            stream.append(obs.JsonFormatter().format(record))

    h = Capture()
    obs.access_log.addHandler(h)
    try:
        sid = _new(app_c)
        app_c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 1, "answer": HOSTILE})
        app_c.get(f"/demo/api/sessions/{sid}?secret=QUERYSECRET")
    finally:
        obs.access_log.removeHandler(h)
    assert stream, "no access log lines were produced"
    blob = "\n".join(stream)
    for forbidden in ("SECRET-ANSWER", "ZXQ9", "script", "QUERYSECRET", sid):
        assert forbidden not in blob
    rows = [json.loads(x) for x in stream]
    assert all({"ts", "level", "request_id", "method", "endpoint", "status", "ms"} <= set(r) for r in rows)


def test_metrics_snapshot_contains_no_answer_text(app_c):
    sid = _new(app_c)
    app_c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 1, "answer": HOSTILE})
    blob = json.dumps(app_c.get("/metrics").json) + app_c.get("/metrics?format=prometheus").get_data(as_text=True) + json.dumps(app_c.get("/healthz").json)
    for forbidden in ("SECRET-ANSWER", "ZXQ9", sid):
        assert forbidden not in blob


def test_request_id_header_is_sanitised(app_c):
    r = app_c.get("/health", headers={"X-Request-ID": "bad id <x>"})
    assert r.headers["X-Request-ID"] != "bad id <x>" and r.headers["X-Request-ID"].isalnum()
    assert app_c.get("/health", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"] == "abc-123"


def test_flags_default_off_in_build_info(monkeypatch):
    for k in version._FLAG_DEFAULTS:
        monkeypatch.delenv(k, raising=False)
    f = version.flags_state()
    assert f["SMART_CODEEVAL_EXEC"] == "disabled" and f["SMART_DEMO_CODE_EVAL"] == "off" and f["SMART_DEMO_LIVE_MODULAR"] == "off"
    assert f["SMART_QUESTION_SOURCE"] == "legacy" and f["SMART_LLM_ALLOW_PAID"] == "off"
    assert "SMART_LLM_API_KEY" not in f  # secrets are never reported


def test_experimental_scoring_stays_opt_in(app_c):
    r = app_c.post("/demo/api/sessions", json={"role": "Data Scientist", "size": 5, "modular_mode": "live"})
    assert r.status_code == 400  # live evaluator is refused unless SMART_DEMO_LIVE_MODULAR=1
    r = app_c.post("/demo/api/sessions", json={"role": "Data Scientist", "size": 5, "code_eval": True})
    assert r.status_code == 400


def test_training_guard(monkeypatch):
    import sys

    sys.path.insert(0, str(version.ROOT / "src" / "model"))
    import model_registry as MR

    class Fake:
        is_trained = False
        trained = False

        def train_from_dataset(self, epochs=10):
            Fake.trained = True

    a = MR._BiLSTMAdapter.__new__(MR._BiLSTMAdapter)
    a._model = Fake()
    monkeypatch.setenv("SMART_FORBID_MODEL_TRAINING", "1")
    with pytest.raises(RuntimeError, match="training was refused"):
        a.ensure_ready()
    assert Fake.trained is False
    monkeypatch.delenv("SMART_FORBID_MODEL_TRAINING")
    a.ensure_ready()  # unset: legacy behaviour (trains) is unchanged
    assert Fake.trained is True


def test_build_info_is_a_single_series_in_both_metric_formats(app_c):
    """Regression: the Prometheus branch used a different label set, which produced two smart_build_info series after the first scrape."""
    app_c.get("/metrics")
    text = app_c.get("/metrics?format=prometheus").get_data(as_text=True)
    app_c.get("/metrics?format=prometheus")
    text = app_c.get("/metrics?format=prometheus").get_data(as_text=True)
    lines = [ln for ln in text.splitlines() if ln.startswith("smart_build_info{")]
    assert len(lines) == 1, lines
    assert 'pipeline="' in lines[0] and 'freeze="' in lines[0] and 'app_version="' in lines[0]
