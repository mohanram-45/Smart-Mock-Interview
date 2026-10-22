"""Stage 3C-2 runner, version 3c2.1: the ORIGINAL runner with one fix (the warm-up now uses the frozen num_ctx, so the first measured call does not
re-load the model). Everything else, including all freeze checks of v1, runs unchanged.

  python scripts/stage3c2_run_v2.py [--dry-run] [--ids a,b] [--skip-legacy]
"""
import importlib.util, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load_v1():
    spec = importlib.util.spec_from_file_location("stage3c2_run_v1", HERE / "stage3c2_run.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def main(argv=None):
    import stage3c2_freeze_v2 as fz2
    bad = fz2.verify(quiet=True)
    if bad:
        sys.exit("REFUSING TO RUN: the frozen experiment (v1 + v2) has changed: " + ", ".join(bad))
    r1 = _load_v1()
    want_ctx = fz2.fz.MODEL_CONFIG["num_ctx"]
    orig = r1.http_json

    def http_json(host, path, body=None, timeout=20):
        if path == "/api/generate" and isinstance(body, dict) and "options" not in body:      # the warm-up: load the model exactly as the experiment will use it
            body = {**body, "options": {"num_ctx": want_ctx}}
        out = orig(host, path, body, timeout)
        if path == "/api/ps" and isinstance(out, dict):
            for m in out.get("models", []):
                if m.get("context_length") not in (None, want_ctx):
                    print(f"WARNING: Ollama reports context_length={m.get('context_length')} for {m.get('name')}, frozen num_ctx is {want_ctx}; the first call may reload the model.")
        return out

    r1.http_json = http_json
    return r1.main(argv)


if __name__ == "__main__":
    sys.exit(main())
