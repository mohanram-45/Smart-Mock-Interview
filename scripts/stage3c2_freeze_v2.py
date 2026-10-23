"""Stage 3C-2 freeze, version 3c2.1 (a thin layer over the ORIGINAL freeze, which stays byte-identical and still verifiable).

v2 exists because the pilot exposed one implementation defect in the run harness (the model warm-up loaded Ollama's default 4096-token context, so the
first real call re-loaded the model at 8192; see reports/stage3c2_pilot_diagnosis.md). The fix lives in NEW files; prompts, gates, rubric, sample, scope,
model settings, acceptance criteria and the v1 runner/analyzer are all carried over unchanged and this script proves it by re-verifying v1.

  python scripts/stage3c2_freeze_v2.py build|verify
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage3c2_freeze as fz   # noqa: E402  (v1)

MANIFEST_V2 = fz.D / "freeze_manifest_v2.json"
V2_FILES = ["scripts/stage3c2_run_v2.py", "scripts/stage3c2_run_v2.ps1", "scripts/stage3c2_freeze_v2.py", "audit/evaluation/stage3c2_analyze_v2.py"]
REASON = ("Pilot 20261015T113555Z (2 answers, partial) showed that the warm-up call used Ollama's default context (4096) while the experiment uses num_ctx=8192, "
          "so the first measured call reloaded the model (70.7 s load inside a 103 s call). v2 sends the warm-up with the frozen num_ctx and adds tooling-only analyzer diagnostics. "
          "Nothing else changed: no prompt, gate, rubric, sample, threshold or model-setting edit, and no pilot output was used to tune anything.")


def build():
    if fz.verify(quiet=True):
        sys.exit("v1 freeze has drifted; refusing to build v2")
    v1 = json.loads(fz.MANIFEST.read_text(encoding="utf-8"))
    doc = {"stage": "3C-2", "version": "3c2.1", "status": "FROZEN_BEFORE_ANY_FURTHER_REAL_MODEL_RUN", "reason": REASON,
           "supersedes": {"manifest": "freeze_manifest.json", "manifest_sha256": fz.sha_file(fz.MANIFEST)},
           "pilot": {"run": "20261015T113555Z", "partial": True, "used_to_tune": "nothing"},
           "unchanged_since_v1": {k: v1["fingerprints"][k] for k in ("sample_jsonl_sha256", "scope_sidecar_sha256", "verifier_system_prompt_sha256", "modular_code_sha256", "legacy_code_sha256", "model_config_sha256")},
           "acceptance_criteria_sha256": v1["fingerprints"]["protocol_files_sha256"]["data/evaluation/stage3c2/acceptance_criteria.json"],
           "v2_files_sha256": {f: fz.sha_file(ROOT / f) for f in V2_FILES}}
    MANIFEST_V2.write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print("froze v2:", MANIFEST_V2)


def verify(quiet=False) -> list:
    bad = [f"v1:{x}" for x in fz.verify(quiet=True)]
    try:
        m = json.loads(MANIFEST_V2.read_text(encoding="utf-8"))
    except Exception as e:
        return bad + [f"freeze_manifest_v2.json unreadable: {e}"]
    if m["supersedes"]["manifest_sha256"] != fz.sha_file(fz.MANIFEST):
        bad.append("v1 manifest changed")
    v1 = json.loads(fz.MANIFEST.read_text(encoding="utf-8"))["fingerprints"]
    bad += [f"carried-over {k} no longer equals v1" for k, v in m["unchanged_since_v1"].items() if v1.get(k) != v]
    bad += [f for f, h in m["v2_files_sha256"].items() if not (ROOT / f).exists() or fz.sha_file(ROOT / f) != h]
    if not quiet:
        print("freeze v2 verified: no drift" if not bad else "DRIFT in: " + ", ".join(bad))
    return bad


if __name__ == "__main__":
    if (sys.argv[1] if len(sys.argv) > 1 else "verify") == "build":
        build()
    else:
        sys.exit(1 if verify() else 0)
