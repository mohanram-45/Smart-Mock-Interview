"""Stage 9C: the blind review pack hides system labels and refuses to report accuracy without human labels."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import stage9c_review_pack as RP  # noqa: E402


def test_pack_is_blind_and_scoring_refuses_without_labels(tmp_path):
    info = RP.build(ROOT / "docs/stage9c_eval/cases_seed.json", tmp_path, "mock")
    assert info["rows"] == 7 and info["skipped_slots"] == 3
    text = (tmp_path / "reviewer_sheet.csv").read_text(encoding="utf-8")
    for leak in ("synthetic", "prompt_injection", "correct_concise", "mock", "origin", "category", "mock-rules"):
        assert leak not in text, leak
    key = json.loads((tmp_path / "key.json").read_text())
    assert len(key["review_to_case"]) == 7 and all(v["origin"] == "synthetic" for v in key["cases"].values())
    assert RP.score(tmp_path / "key.json", [tmp_path / "reviewer_sheet.csv"])["status"] == "no human labels"


def test_scoring_reports_agreement_only_with_two_reviewers(tmp_path):
    RP.build(ROOT / "docs/stage9c_eval/cases_seed.json", tmp_path, "mock")
    rows = list(csv.DictReader(open(tmp_path / "reviewer_sheet.csv", encoding="utf-8")))
    for name, val in (("a.csv", "y"), ("b.csv", "n")):
        for r in rows:
            r["followup_relevant"] = val
        with open(tmp_path / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)
    one = RP.score(tmp_path / "key.json", [tmp_path / "a.csv"])
    two = RP.score(tmp_path / "key.json", [tmp_path / "a.csv", tmp_path / "b.csv"])
    assert one["agreement"] == {} and "NOT accuracy" in one["claim"]
    assert two["agreement"]["followup_relevant"]["n"] == 7 and "accuracy" not in json.dumps(two["rates"]).lower()
