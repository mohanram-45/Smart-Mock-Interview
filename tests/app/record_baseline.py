"""Record the pre-integration golden baseline. Run ONLY against the unmodified legacy app."""
import json, sys
from pathlib import Path
import pytest

OUT = Path(__file__).parent / "golden" / "legacy_baseline.json"

def test_record(client):
    from tests.app.scenario import run
    steps = [[l, c, j] for l, c, j in run(client)]
    again = None
    OUT.write_text(json.dumps(steps, indent=1, sort_keys=True), encoding="utf-8")
