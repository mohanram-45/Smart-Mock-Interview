"""Do the corpus, the DVC parameters, the built indexes, the frozen files and the stored results agree with each other? (Stage 8A)

    python scripts/check_versions.py            # exit 0 = no disagreement (skips are listed, not hidden); exit 1 = at least one FAIL

Read-only. Loads no model, downloads nothing, writes nothing. See src/mlops/consistency.py for the list of checks."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.mlops import consistency  # noqa: E402


def main() -> int:
    findings = consistency.check_all()
    for f in findings:
        print(f"[{f['status'].upper():4}] {f['id']} - {f['detail']}")
    s = consistency.summarise(findings)
    print(f"\n{s['pass']} passed, {s['fail']} FAILED, {s['skip']} skipped")
    return 1 if s["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
