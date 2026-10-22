"""The Phase 5 script is a mock-only behavioural comparison; these tests pin the behavioural invariants it reports (not accuracy)."""
import importlib.util, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location("cmp3c1", ROOT / "scripts" / "stage3c1_compare.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_modular_never_scores_without_verified_evidence_and_is_deterministic(tmp_path, capsys):
    m = _load()
    import sys
    sys.argv = ["x", "--out", str(tmp_path / "o.json")]
    m.main()
    out = json.loads((tmp_path / "o.json").read_text())
    assert "MOCK-ONLY" in out["disclaimer"] and len(out["eligible_questions_used"]) == 8
    for sc in ("fabricated_evidence", "provider_garbage", "provider_error", "nothing_stated", "contradictory", "all_unsure"):
        assert out["scenarios"][sc]["modular"]["numeric_score_issued"] == 0, sc
        assert out["scenarios"][sc]["modular"]["credited_and_blamed_same_text"] == 0
    for sc, t in out["scenarios"].items():
        assert t["modular_deterministic_repeat"] and t["modular_dimension_derivations_recorded"]
    assert out["scenarios"]["fabricated_evidence"]["legacy"]["score_lt_50"] > 0          # legacy caps instead of abstaining
    assert out["scenarios"]["valid_evidence"]["modular"]["numeric_score_issued"] > 0
