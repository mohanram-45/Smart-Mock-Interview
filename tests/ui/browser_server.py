"""Serve the REAL Flask app (main/app.py, real routes, real curated question bank, real session store) for browser tests on a machine without torch or model files.

The only substitution is the Sentence-BERT similarity scorer (torch and the model files are absent here): a deterministic word-overlap stand-in (same `.score(reference, answer)` interface), registered under a label that says
so on every page. Usage:  python tests/ui/browser_server.py PORT DATA_DIR      (env SMART_DEMO_CODE_EVAL=1 / SMART_DEMO_LIVE_MODULAR as for the real launcher)."""
import importlib.util
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "model"))


class OverlapScorer:
    def score(self, reference, answer):
        ref, ans = set((reference or "").lower().split()), (answer or "").lower().split()
        return 0.0 if not ans else min(1.0, sum(w in ref for w in ans) / len(ans))


def main(port: int, data_dir: str) -> None:
    import os
    os.environ["SMART_DEMO_DATA_DIR"] = data_dir
    os.environ["SMART_RETRIEVAL_BACKEND"] = "dev-lsa"
    import model_registry
    model_registry.MODEL_CHOICES["bert"] = {**model_registry.MODEL_CHOICES["bert"], "label": "Sentence-BERT (test stand-in: word overlap, not the real model)"}
    spec = importlib.util.spec_from_file_location("smart_app_ui", ROOT / "main" / "app.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["smart_app_ui"] = mod
    spec.loader.exec_module(mod)
    from src.demo.engine import DemoEngine
    from src.demo.routes import set_engine
    from src.demo.store import DemoStore
    set_engine(DemoEngine(DemoStore(Path(data_dir)), scorer_factory=lambda k, c: OverlapScorer(), readiness_fn=lambda k: {"ready": True, "not_ready_reason": None, "setup_hint": None},
                          feedback_fn=lambda s, q, a, m: "Answers in this similarity band get this standard comment." if s >= 50 else "Answers in this similarity band get a different standard comment.",
                          rng=random.Random(5)))
    mod.app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2])
