"""A tiny fake Ollama server for tests and the benchmark self-test. Its timings are SCRIPTED: nothing measured against it says anything about a real model.

Speaks just enough of the real protocol: POST /api/chat (streaming NDJSON with a final object carrying the metric fields), GET /api/tags. Options:
  load_delay      seconds the first request after start/unload spends 'loading'
  first_delay     seconds before the first token (prompt processing)
  token_delay     seconds between generated chunks
  reply           str | callable(request_json) -> str : the full assistant text, streamed in 6-character chunks
  status          HTTP status to answer with (e.g. 404 = model missing)
It counts requests, completed generations and cancellations (client closed the connection mid-stream)."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeOllama:
    def __init__(self, reply="{}", load_delay=0.0, first_delay=0.0, token_delay=0.0, status=200, models=("llama3.2:3b", "qwen2.5:7b")):
        self.reply, self.load_delay, self.first_delay, self.token_delay, self.status, self.models = reply, load_delay, first_delay, token_delay, status, list(models)
        self.requests, self.completed, self.cancelled, self.loaded, self.bodies = 0, 0, 0, False, []
        self.in_flight = 0
        self.max_in_flight = 0
        self._lock = threading.Lock()
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                body = json.dumps({"models": [{"name": m} for m in fake.models]}).encode()
                self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                req = json.loads(self.rfile.read(n) or b"{}")
                with fake._lock:
                    fake.requests += 1; fake.bodies.append(req); fake.in_flight += 1; fake.max_in_flight = max(fake.max_in_flight, fake.in_flight)
                try:
                    if req.get("keep_alive") == 0:
                        fake.loaded = False
                        self.send_response(200); self.end_headers(); self.wfile.write(b'{"done":true}\n'); return
                    if fake.status != 200:
                        self.send_response(fake.status); self.end_headers(); self.wfile.write(b'{"error":"model not found"}'); return
                    self.send_response(200); self.send_header("Content-Type", "application/x-ndjson"); self.end_headers()
                    t0 = time.perf_counter()
                    load = 0.0
                    if not fake.loaded:
                        time.sleep(fake.load_delay); fake.loaded = True; load = fake.load_delay
                    time.sleep(fake.first_delay)
                    text = fake.reply(req) if callable(fake.reply) else fake.reply
                    if (req.get("options") or {}).get("num_predict", 99) <= 2:
                        text = "ok"
                    try:
                        for i in range(0, len(text), 6):
                            self.wfile.write(json.dumps({"message": {"role": "assistant", "content": text[i:i + 6]}, "done": False}).encode() + b"\n"); self.wfile.flush()
                            time.sleep(fake.token_delay)
                        total = time.perf_counter() - t0
                        final = {"message": {"role": "assistant", "content": ""}, "done": True, "done_reason": "stop", "total_duration": int(total * 1e9), "load_duration": int(load * 1e9),
                                 "prompt_eval_count": 123, "prompt_eval_duration": int(fake.first_delay * 1e9), "eval_count": max(1, len(text) // 4), "eval_duration": int(max(0.001, total - fake.first_delay) * 1e9)}
                        self.wfile.write(json.dumps(final).encode() + b"\n"); self.wfile.flush()
                        with fake._lock:
                            fake.completed += 1
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        with fake._lock:
                            fake.cancelled += 1
                finally:
                    with fake._lock:
                        fake.in_flight -= 1

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *a):
        self.server.shutdown(); self.server.server_close()
