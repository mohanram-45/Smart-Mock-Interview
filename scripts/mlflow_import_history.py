"""Import EXISTING experiment results into the local MLflow store (no model is run). Idempotent: re-running creates nothing new.

    python scripts/mlflow_import_history.py            # import + verify
    python scripts/mlflow_import_history.py --verify   # verify only (exit 1 on any mismatch with the source files)
Then browse:  mlflow ui --backend-store-uri <printed uri>"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.mlops import tracking  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true", help="only check that MLflow matches the source files")
    ap.add_argument("--tracking-uri", help="override MLFLOW_TRACKING_URI (default: sqlite in ./mlflow/)")
    ap.add_argument("--allow-drift", action="store_true", help="accept a changed source file (frozen files should never change)")
    a = ap.parse_args()
    if a.tracking_uri:
        os.environ["MLFLOW_TRACKING_URI"] = a.tracking_uri
    if not tracking.available():
        print("MLflow is not installed. Run:  pip install -r requirements-mlops.txt")
        return 2
    from src.mlops import historical, verify

    print("tracking uri:", tracking.tracking_uri())
    if not a.verify:
        r = historical.import_all(allow_drift=a.allow_drift)
        print(f"imported: {r['created']} created, {r['exists']} already present")
    v = verify.verify_history()
    print(json.dumps({k: v[k] for k in ("ok", "runs_checked", "metrics_checked")}))
    for p in v["problems"]:
        print("PROBLEM:", p)
    print("MLflow records match the source result files." if v["ok"] else "MISMATCH - see problems above.")
    print(f"browse: mlflow ui --backend-store-uri {tracking.tracking_uri()}")
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
