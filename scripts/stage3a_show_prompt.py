"""Print the exact evaluation prompt for a curated question and a candidate answer. NO model is called, nothing is sent anywhere.

    python scripts/stage3a_show_prompt.py --qid smi-0453 --answer "Bubble sort swaps neighbours until sorted, O(n^2)."
    python scripts/stage3a_show_prompt.py --qid smi-0453 --answer-file answer.txt --support
"""
import argparse, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qid", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--answer")
    g.add_argument("--answer-file")
    ap.add_argument("--support", action="store_true", help="include retrieved neighbours (uses the configured retrieval backend)")
    a = ap.parse_args()
    from src.evaluation.grounding import build_request
    from src.evaluation.injection import detect_injection
    from src.evaluation.prompt import build_prompt
    from src.retrieval.service import RetrievalService
    ans = a.answer if a.answer is not None else Path(a.answer_file).read_text(encoding="utf-8")
    svc = RetrievalService()
    req = build_request(a.qid, ans, service=svc, with_support=a.support)
    p = build_prompt(req)
    print("=" * 30, "SYSTEM", "=" * 30, "\n" + p.system, "\n" + "=" * 30, "USER", "=" * 30, "\n" + p.user)
    print("\n[prompt_version=%s, injection heuristics matched: %s]" % (p.prompt_version, detect_injection(ans) or "none"))


if __name__ == "__main__":
    main()
