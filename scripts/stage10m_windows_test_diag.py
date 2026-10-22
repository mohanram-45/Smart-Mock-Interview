"""Explain a platform-dependent test result: prints the environment and the memory/follow-up trace of the scripted engine run the three Stage 10J tests depend on. Run on the machine where they failed:
    .bot\\Scripts\\python.exe scripts\\stage10m_windows_test_diag.py > diag.txt
Nothing here calls Ollama; it needs no network."""
import json
import os
import platform
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    from src.demo import opportunity_eval as OE, sim
    env = {k: os.environ.get(k) for k in sorted(os.environ) if k.startswith("SMART_")}
    try:
        import sentence_transformers as st
        sbert = st.__version__
    except Exception as e:                                                             # noqa: BLE001
        sbert = f"not importable ({type(e).__name__})"
    print(json.dumps({"python": sys.version.split()[0], "platform": platform.platform(), "sentence_transformers": sbert, "SMART_env": env}, indent=1))
    e = sim.offline_engine(tempfile.mkdtemp())
    e._followup_generator = OE.scripted_generator()
    s, t = sim.run(e, {"role": "Data Scientist", "practical": False, "size": 8, "followup_mode": "mock", "max_followups": 2}, OE._partial_answers(e, OE.MED))
    print("status:", s["status"], "| retrieval:", json.dumps(s["plan"].get("retrieval")))
    print("questions:")
    for i, q in enumerate(s["questions"], 1):
        print(f"  {i:2d} {q.get('stage') or ''} {q.get('followup_kind') or ''} mem={q.get('memory_id')} | {q['question'][:90]}")
    print("follow-up log:")
    for x in s["plan"].get("followup_log", []):
        print("  ", json.dumps({k: x.get(k) for k in ("n", "memory_stage", "fallback_class", "decision", "reasons", "retrieval")}, default=str))
    print("memory items:", [(m["id"], m["kind"], m["turn"]) for m in s["memory"]["items"]])
    print("answers legacy:", [(a or {}).get("legacy", {}).get("status") for a in s["answers"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
