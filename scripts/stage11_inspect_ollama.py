"""Stage 11: read-only inventory of the local Ollama models and the hardware, to decide which models can be compared WITHOUT downloading anything.

  .bot\\Scripts\\python.exe scripts\\stage11_inspect_ollama.py [--host http://127.0.0.1:11434] [--out tmp\\stage11_models.json]

Never pulls a model, never calls a paid service. Prints the exact comparison commands for the models that are already installed.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import urllib.request


def get(url: str, timeout: float = 5.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:                          # noqa: S310 (local host only)
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:                                                               # noqa: BLE001
        return {"error": f"{type(e).__name__}: {str(e)[:100]}"}


def hardware() -> dict:
    hw = {"platform": platform.platform(), "cpu_count": os.cpu_count()}
    try:
        import psutil
        hw["ram_gb"] = round(psutil.virtual_memory().total / 2**30, 1)
        hw["ram_available_gb"] = round(psutil.virtual_memory().available / 2**30, 1)
    except Exception:                                                                    # noqa: BLE001
        hw["ram_gb"] = None
    if shutil.which("nvidia-smi"):
        try:
            hw["gpu"] = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader"], capture_output=True, text=True, timeout=10).stdout.strip().splitlines()
        except Exception as e:                                                           # noqa: BLE001
            hw["gpu"] = f"nvidia-smi failed: {type(e).__name__}"
    else:
        hw["gpu"] = "no nvidia-smi found (CPU or non-NVIDIA)"
    return hw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    host = a.host.rstrip("/")
    tags, ver, ps = get(host + "/api/tags"), get(host + "/api/version"), get(host + "/api/ps")
    models = [{"name": m.get("name"), "size_gb": round((m.get("size") or 0) / 2**30, 2), "parameter_size": (m.get("details") or {}).get("parameter_size"), "quantization": (m.get("details") or {}).get("quantization_level"),
               "family": (m.get("details") or {}).get("family")} for m in (tags.get("models") or [])]
    hw = hardware()
    ram = hw.get("ram_available_gb")
    for m in models:
        m["fits_in_available_ram"] = None if ram is None else m["size_gb"] * 1.3 < ram       # rough: weights + context; a GPU may change this
        m["is_embedding_only"] = "embed" in (m["name"] or "").lower() or m["family"] in ("bert", "nomic-bert")
    cand = [m["name"] for m in models if not m["is_embedding_only"] and m["fits_in_available_ram"] is not False]
    doc = {"ollama": ver, "loaded_now": [m.get("name") for m in (ps.get("models") or [])], "models": models, "hardware": hw, "comparable_models": cand, "downloads_performed": 0,
           "note": "Only models already installed are listed. Nothing was pulled. Fit estimates are rough."}
    if tags.get("error"):
        doc["error"] = tags["error"]
    print(json.dumps(doc, indent=1))
    if len(cand) >= 1:
        print("\nBaseline vs objective engine, per installed model (run each, then compare):")
        for m in cand:
            for eng in ("stage10n", "objective"):
                print(f"  .bot\\Scripts\\python.exe scripts\\stage10_verify_real_stack.py --opportunities --models {m} --engine {eng} --mlflow --sbert")
        print("  .bot\\Scripts\\python.exe scripts\\stage11_compare.py --runs <each results.json>")
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
