"""Run the demonstration app with deterministic stand-ins so the WHOLE interview flow can be exercised without torch, a trained scorer or Ollama.

  python scripts/stage4a_demo_server.py [--port 5055] [--live-fake]

This is a TEST/SCREENSHOT harness. The legacy scorer is a transparent word-overlap stand-in (labelled "Siamese Bi-LSTM" only because the session asks for that
key) and `--live-fake` simulates a slow / failing live model. It exists so browser tests are reproducible anywhere. The real app is `python main\\app.py`."""
import argparse, random, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class OverlapScorer:
    def score(self, reference, answer):
        ref, ans = set((reference or "").lower().split()), (answer or "").lower().split()
        return 0.0 if not ans else min(1.0, sum(w in ref for w in ans) / len(ans))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5055)
    ap.add_argument("--fail-legacy", action="store_true")
    ap.add_argument("--not-ready", metavar="KEY", help="pretend this legacy scorer (bilstm|bert|tfidf) needs one-time setup (shows the 4B start-up safety UI)")
    ap.add_argument("--live-fake", choices=["ok", "fail"], help="enable 'live' mode backed by a fake verifier (ok = mock-speed, fail = provider error)")
    a = ap.parse_args()
    import os
    os.environ.setdefault("SMART_DEMO_DATA_DIR", tempfile.mkdtemp(prefix="demo_sessions_"))
    if a.live_fake:
        os.environ["SMART_DEMO_LIVE_MODULAR"] = "1"
    import importlib.util
    spec = importlib.util.spec_from_file_location("smart_app", ROOT / "main" / "app.py")
    mod = importlib.util.module_from_spec(spec); sys.modules["smart_app"] = mod; spec.loader.exec_module(mod)
    from src.demo import experimental as MA
    from src.demo.engine import DemoEngine
    from src.demo.routes import set_engine
    from src.demo.store import DemoStore

    def scorer(key, corpus):
        if a.fail_legacy:
            raise RuntimeError("scoring model files not found (simulated)")
        return OverlapScorer()
    ev = MA.evaluate
    if a.live_fake:
        from src.evaluation.errors import ProviderUnavailable
        from src.evaluation.modular.mock_verifiers import LexicalMockVerifier, ScriptedVerifier

        class Slow(LexicalMockVerifier):
            def verify(self, request):
                time.sleep(4)
                if a.live_fake == "fail":
                    from src.evaluation.modular.verification import VerifierProviderError
                    raise VerifierProviderError("cannot reach Ollama at http://127.0.0.1:11434 (simulated)")
                return super().verify(request)
        ev = lambda mode, rec, ans: MA.evaluate("live" if mode == "live" else mode, rec, ans, verifier=Slow()) if mode == "live" else MA.evaluate(mode, rec, ans)
    ready = (lambda key: {"ready": False, "not_ready_reason": "No trained checkpoint was found (simulated).", "setup_hint": "python src\\model\\SiameseBiLSTM.py"}
             if key == a.not_ready else {"ready": True, "not_ready_reason": None, "setup_hint": None}) if a.not_ready else None
    set_engine(DemoEngine(DemoStore(), scorer_factory=scorer, readiness_fn=ready, feedback_fn=lambda s, q, an, m: f"Your answer resembles the reference answer at {s:.0f}%.", modular_evaluate=ev))
    mod.app.run(host="127.0.0.1", port=a.port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
