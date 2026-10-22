"""Stage 3B Phase 1: READ-ONLY probe of local LLM availability. Downloads nothing, installs nothing, changes nothing.

    python scripts/stage3b_probe_ollama.py            ->  prints a summary and writes data/evaluation/stage3b/ollama_probe.json

Checks: ollama executable, server reachability (OLLAMA_HOST or 127.0.0.1:11434), installed models (/api/tags), currently loaded
models (/api/ps), RAM/CPU/GPU, and a rough fit estimate per model. Send me the JSON (or the printed output).
"""
import json, os, platform, re, shutil, subprocess, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").strip()
if not HOST.startswith("http"):
    HOST = "http://" + HOST
HOST = HOST.rstrip("/")
NOT_CHAT = re.compile(r"embed|nomic|bge|minilm|e5-|rerank|whisper|clip|vision-only", re.I)


def get(path, timeout=5):
    with urllib.request.urlopen(HOST + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def ram_gb():
    try:
        if platform.system() == "Windows":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                            ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]
            m = MS(); m.l = ctypes.sizeof(MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return round(m.tp / 2**30, 1), round(m.ap / 2**30, 1)
        import psutil
        v = psutil.virtual_memory(); return round(v.total / 2**30, 1), round(v.available / 2**30, 1)
    except Exception:
        return None, None


def gpu():
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"nvidia_smi": False}
    try:
        out = subprocess.run([exe, "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout
        gpus = [dict(zip(("name", "vram_total_mb", "vram_used_mb"), [x.strip() for x in l.split(",")])) for l in out.strip().splitlines() if l.strip()]
        return {"nvidia_smi": True, "gpus": gpus}
    except Exception as e:
        return {"nvidia_smi": True, "error": str(e)}


def find_exe():
    cands = [shutil.which("ollama"), str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"),
             r"C:\Program Files\Ollama\ollama.exe"]
    return next((c for c in cands if c and Path(c).exists()), None)


def main():
    res = {"platform": platform.platform(), "python": sys.version.split()[0], "host": HOST}
    _exe = find_exe()
    res["ollama_executable"] = _exe.replace(str(Path.home()), "~") if _exe else _exe   # never record the machine's user name in a file that gets committed
    if res["ollama_executable"]:
        try:
            res["ollama_cli_version"] = subprocess.run([_exe, "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception as e:
            res["ollama_cli_version"] = f"error: {e}"
    res["ollama_models_env"] = os.environ.get("OLLAMA_MODELS")
    res["default_models_dir_exists"] = (Path.home() / ".ollama" / "models").exists()
    total, avail = ram_gb()
    res["ram_gb_total"], res["ram_gb_available_now"], res["cpu_count"] = total, avail, os.cpu_count()
    res["gpu"] = gpu()
    try:
        res["server_version"] = get("/api/version").get("version")
        res["server_reachable"] = True
    except Exception as e:
        res["server_reachable"] = False
        res["server_error"] = str(e)[:200]
    models = []
    if res["server_reachable"]:
        for m in get("/api/tags").get("models", []):
            d = m.get("details") or {}
            size_gb = round(m.get("size", 0) / 2**30, 2)
            models.append({"name": m.get("name"), "size_gb": size_gb, "family": d.get("family"), "parameter_size": d.get("parameter_size"),
                           "quantization": d.get("quantization_level"), "modified_at": m.get("modified_at"),
                           "chat_capable_guess": not NOT_CHAT.search(m.get("name", "") + " " + str(d.get("family", "")))})
        try:
            res["currently_loaded"] = [{"name": x.get("name"), "size_gb": round(x.get("size", 0) / 2**30, 2), "vram_gb": round(x.get("size_vram", 0) / 2**30, 2)} for x in get("/api/ps").get("models", [])]
        except Exception:
            res["currently_loaded"] = None
    vram = None
    try:
        vram = max(float(g["vram_total_mb"]) for g in res["gpu"].get("gpus", [])) / 1024 if res["gpu"].get("gpus") else None
    except Exception:
        pass
    for m in models:
        need = m["size_gb"] * 1.25 + 1.5            # weights + KV cache at 8k ctx + overhead (ROUGH estimate)
        m["est_memory_gb_at_8k_ctx"] = round(need, 1)
        m["fits_ram"] = None if total is None else need <= (total * 0.8)
        m["fits_vram"] = None if vram is None else need <= vram * 0.95
        try:
            p = float(re.sub(r"[^\d.]", "", str(m["parameter_size"] or "")) or 0)
        except ValueError:
            p = 0
        m["param_billions"] = p
        m["worth_trying"] = bool(m["chat_capable_guess"] and p >= 3 and m["fits_ram"] is not False)
    res["installed_models"] = models
    res["note"] = ("Compatibility with the structured evaluator is NOT established by this probe; only the Stage 3B smoke run shows whether a model "
                   "returns valid, rubric-following JSON. Memory figures are rough estimates.")
    out = Path(os.environ["SMART_PROBE_OUT"]) if os.environ.get("SMART_PROBE_OUT") else ROOT / "data" / "evaluation" / "stage3b" / "ollama_probe.json"   # tests redirect it
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "installed_models"}, indent=2))
    print("\nINSTALLED MODELS:" if models else "\nNo installed models found (or server not reachable).")
    for m in models:
        print(f"  {m['name']:<32} {m['size_gb']:>6} GB  {str(m['parameter_size']):>7}  {str(m['quantization']):<8} chat={m['chat_capable_guess']}  ~{m['est_memory_gb_at_8k_ctx']} GB needed  fits_ram={m['fits_ram']} fits_vram={m['fits_vram']}  worth_trying={m['worth_trying']}")
    print("\nwritten:", out)


if __name__ == "__main__":
    main()
