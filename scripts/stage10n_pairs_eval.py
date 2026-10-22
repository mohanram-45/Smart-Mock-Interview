"""Stage 10N: validator false-acceptance / false-rejection rates on hand-written question pairs (fixture T cases + unseen holdouts). No model involved; not human validation.
Usage: python scripts/stage10n_pairs_eval.py [--out reports/stage10n_eval/pairs.json]"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.demo import question_pairs_eval as Q  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/stage10n_eval/pairs.json")
    a = ap.parse_args()
    r = Q.run()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    for k in ("fixture", "holdout", "holdout2", "all"):
        v = r[k]
        print(f"{k:9s} false rejections {v['false_rejections']}/{v['n_good']}  false acceptances {v['false_acceptances']}/{v['n_bad']} (detectable {v['false_acceptances_detectable']}/{v['n_bad_detectable']}, known gaps accepted {v['known_gap_accepted']}/{v['known_gap_total']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
