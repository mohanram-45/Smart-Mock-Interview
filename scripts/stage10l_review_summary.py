"""Summarise a blind review pack. Refuses to print any rating statistic for unrated rows."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.demo import opportunity_eval as OE  # noqa: E402

if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("reports/stage10_jkl_eval/review")
    print(json.dumps(OE.review_summary(d), indent=1))
