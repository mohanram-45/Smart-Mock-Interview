"""Container/host health probe: exit 0 if GET /healthz answers 200 with status ok, else 1. Standard library only.

python scripts/healthcheck.py                          # http://127.0.0.1:5000
python scripts/healthcheck.py http://127.0.0.1:5000 --ready      # also require /readyz = ready"""

import json
import sys
import urllib.request


def get(url: str, timeout: float = 4.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8") or "{}")
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": f"{type(e).__name__}: {e}"}


def main(argv) -> int:
    base = next((a for a in argv[1:] if a.startswith("http")), "http://127.0.0.1:5000").rstrip("/")
    code, body = get(base + "/healthz")
    if code != 200 or body.get("status") != "ok":
        print(f"UNHEALTHY: {base}/healthz -> {code} {body}")
        return 1
    print(f"healthy: app {body.get('app_version')} commit {body.get('git_commit')} pipeline {body.get('evaluator_versions', {}).get('pipeline')}")
    if "--ready" in argv:
        code, body = get(base + "/readyz")
        print(json.dumps(body.get("checks", {})), "| optional:", json.dumps(body.get("optional", {}))[:300])
        if code != 200 or not body.get("ready"):
            print("NOT READY (see checks above)")
            return 1
        print("ready")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
