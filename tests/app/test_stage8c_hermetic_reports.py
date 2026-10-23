"""Stage 8C regression: Flask report tests must not depend on a local Ollama.

Found on Windows: llm_report reads OLLAMA_HOST once at import (default 127.0.0.1:11434). On a machine that runs Ollama the background report job waited for the
real model (timeout 180 s) while the tests poll for 10 s, so test_end_interview_is_async and test_full_curated_interview_and_report failed with HTTP 202.
"""
import http.server
import threading
import time


def test_client_fixture_points_the_report_llm_at_a_refusing_port(client):
    import llm_report  # top-level module name, importable once the app module has put src/components on sys.path

    assert llm_report.OLLAMA_BASE_URL == "http://127.0.0.1:9"


def test_end_interview_never_contacts_a_listening_ollama(client, monkeypatch):
    import llm_report

    hits = []

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            hits.append(self.path)
            self.send_response(500)
            self.end_headers()

        do_POST = do_GET

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        # simulate "the default Ollama address is live": the fixture must have moved the report LLM away from it
        assert llm_report.OLLAMA_BASE_URL != f"http://127.0.0.1:{srv.server_port}"
        d = client.post("/api/start-interview", json={"role": "Python Developer"}).get_json()
        sid = d["session_id"]
        client.post("/api/submit-answer", json={"session_id": sid, "answer": "x y z"})
        assert client.post("/api/end-interview", json={"session_id": sid}).status_code == 202
        for _ in range(100):
            s = client.get(f"/api/reports/{sid}/status")
            if s.status_code != 202:
                break
            time.sleep(0.1)
        assert s.status_code in (200, 500) and hits == []
    finally:
        srv.shutdown()
