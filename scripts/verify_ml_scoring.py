"""Stage 14: proof that REAL Sentence-BERT scoring works (run it INSIDE the INSTALL_ML=1 image, or on any machine with the ML extras and the model cache).

A passing /healthz does not prove this: the lean image is healthy without torch, and the demo then reports "similarity unavailable". This script
  1. loads the registry's "bert" scorer (all-MiniLM-L6-v2) and refuses to pass if the real model is not what answered,
  2. checks the behaviour a real embedding model must have (identical text ~1, an unrelated sentence low, the reference's own first sentence clearly above it),
  3. drives the actual /demo app: answers a real core question with its own reference text and with an unrelated sentence, and checks the stored similarity values.
Only similarity numbers are printed, never answer text.   Exit 0 = real scoring verified.

    docker compose run --rm app python scripts/verify_ml_scoring.py          (after: set SMART_INSTALL_ML=1 & docker compose build app, and the one-time model-cache fill; see verify_docker_ml.bat)
    python scripts/verify_ml_scoring.py --pairs-only                          (skip the app drive)"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "model"))

IDENTICAL_MIN, UNRELATED_MAX, MARGIN = 0.95, 0.40, 0.20
UNRELATED = "My favourite weekend activity is hiking in the hills and cooking pasta with friends."


def load_corpus(path: Path = ROOT / "data" / "processed" / "questions_cleaned.json"):
    qs = json.loads(path.read_text(encoding="utf-8"))
    return [q for q in qs if len(str(q.get("reference_answer") or "").split()) >= 25]


def first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]


def check_pairs(score, corpus) -> list:
    """`score(reference, answer) -> 0..1`. Returns a list of (name, value, ok). Pure: the tests run it with a stand-in scorer.
    The corpus references are templated ("X is a core ... concept related to ..."), so another topic's reference can legitimately score fairly high; the 'far' case is an
    everyday sentence instead, and another topic's reference only has to score below identical text."""
    a = corpus[0]
    other = next(q for q in corpus if q.get("domain") != a.get("domain"))
    ref = a["reference_answer"]
    same, part, far, topic = score(ref, ref), score(ref, first_sentence(ref)), score(ref, UNRELATED), score(ref, other["reference_answer"])
    return [("identical text", same, same >= IDENTICAL_MIN), ("unrelated sentence is low", far, far <= UNRELATED_MAX),
            ("the reference's own first sentence is clearly above unrelated", part, part >= far + MARGIN), ("another topic's reference is below identical text", topic, topic <= same - 0.02)]


def drive_app(corpus_all) -> list:
    from main.app import app
    from src.demo.routes import get_engine
    by_id = {q["id"]: q for q in corpus_all}
    out = []
    with app.test_client() as c:
        sid = c.post("/demo/api/sessions", json={"role": "Data Scientist", "size": 3, "practical": False, "max_followups": 0}).json["session_id"]
        c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 1, "answer": "Hello, I am a candidate."})
        for k in (2, 3):
            s = get_engine().get(sid)
            q = s["questions"][k - 1]
            ref = (get_engine().record(q.get("question_id")) or {}).get("canonical_answer")
            text = ref if (k == 2 and ref) else UNRELATED
            r = c.post(f"/demo/api/sessions/{sid}/answer", json={"n": k, "answer": text})
            leg = get_engine().get(sid)["answers"][k - 1]["legacy"]
            ok = r.status_code == 200 and leg.get("status") == "scored"
            out.append((("own reference text" if k == 2 else "unrelated sentence") + " via /demo", (leg.get("score") or 0) / 100.0, ok))
        out[0] = (out[0][0], out[0][1], out[0][2] and out[0][1] >= 0.85)
        out[1] = (out[1][0], out[1][1], out[1][2] and out[1][1] <= UNRELATED_MAX and out[1][1] < out[0][1] - MARGIN)
    return out


def main(argv) -> int:
    try:
        import sentence_transformers
        import torch
    except ImportError as e:
        print(f"FAIL: the ML extras are not installed ({e}). Build with INSTALL_ML=1 (SMART_INSTALL_ML=1 docker compose build app).")
        return 1
    print(f"torch {torch.__version__} | sentence-transformers {sentence_transformers.__version__}")
    from model_registry import get_scorer
    try:
        scorer = get_scorer("bert")
    except Exception as e:
        print(f"FAIL: the Sentence-BERT scorer could not be loaded: {type(e).__name__}: {str(e)[:300]}. Fill the model cache once (see .env.example / verify_docker_ml.bat).")
        return 1
    inner = type(getattr(scorer, "_model", scorer)).__name__
    print(f"scorer: {type(scorer).__name__} -> {inner}")
    if inner != "SentenceBertAnswerScorer":
        print("FAIL: not the Sentence-BERT scorer")
        return 1
    corpus_all = json.loads((ROOT / "data" / "processed" / "questions_cleaned.json").read_text(encoding="utf-8"))
    rows = check_pairs(scorer.score, load_corpus())
    if "--pairs-only" not in argv:
        rows += drive_app(corpus_all)
    bad = 0
    for name, value, ok in rows:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {value:.3f}")
        bad += 0 if ok else 1
    print("REAL SENTENCE-BERT SCORING VERIFIED" if not bad else f"{bad} check(s) failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
