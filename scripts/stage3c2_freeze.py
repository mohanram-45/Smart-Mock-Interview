"""Stage 3C-2 freeze: fingerprints of everything that defines the experiment. `build` writes data/evaluation/stage3c2/freeze_manifest.json;
`verify` recomputes and compares (the runner calls it and refuses to run on any drift). Line endings are normalised (CRLF->LF) before hashing so a
Windows checkout hashes like the Linux build.

  python scripts/stage3c2_freeze.py build|verify
"""
import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
D = ROOT / "data" / "evaluation" / "stage3c2"
MANIFEST = D / "freeze_manifest.json"
MODEL_CONFIG = {"model": "qwen2.5:7b", "provider": "ollama (local)", "temperature": 0.0, "seed_base": 7, "seed_rule": "seed = 7 + repeat_index", "num_ctx": 8192,
                "max_output_tokens": 1800, "timeout_s": 300, "structured_output": "per-request JSON schema (closed enums), all verdict fields required",
                "modular_repeats": 2, "modular_max_retries": 1, "legacy_repeats": 1, "legacy_schema": "evaluation.schema.OUTPUT_JSON_SCHEMA", "legacy_max_retries": 1,
                "legacy_support_snippets": "none (identical reference material; only the architecture differs)", "paid_apis": False, "model_downloads": False}
MODULAR_FILES = ["claims", "consistency", "feedback", "llm_verifier", "pipeline", "qwen_verifier", "reference", "requirements", "rubric_engine", "scope", "verification"]
PROTOCOL_FILES = ["reports/stage3c2_protocol.md", "data/evaluation/stage3c2/acceptance_criteria.json", "scripts/stage3c2_run.py", "scripts/stage3c2_run.ps1",
                  "audit/evaluation/stage3c2_analyze.py", "scripts/stage3c2_freeze.py", "audit/evaluation/stage3c2_build_sample.py"]


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def sha_many(paths) -> str:
    h = hashlib.sha256()
    for p in paths:
        h.update(p.name.encode()); h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def compute() -> dict:
    from src.evaluation.modular import qwen_verifier as qv
    from src.retrieval.corpus import load_corpus
    recs = {r["question_id"]: r for r in load_corpus()["records"]}
    sample = [json.loads(l) for l in (D / "sample.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    qids = sorted({s["question_id"] for s in sample})
    corpus_h = hashlib.sha256(json.dumps([recs[q] for q in qids], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    scope = ROOT / "data" / "evaluation" / "scope"
    ev = ROOT / "src" / "evaluation"
    return {
        "sample_jsonl_sha256": sha_file(D / "sample.jsonl"),
        "sample_ids": [s["sample_id"] for s in sample],
        "question_ids": qids,
        "corpus_records_for_sample_sha256": corpus_h,
        "scope_sidecar_sha256": sha_file(scope / "scope_v1.jsonl"),
        "scope_manifest_sha256": sha_file(next(scope.glob("*manifest*.json"))),
        "provisional_ai_expectations_sha256": sha_file(D / "provisional_ai_expectations.jsonl"),
        "blind_review_sheet_csv_sha256": sha_file(D / "review" / "blind_review_sheet.csv"),
        "verifier_prompt_version": qv.QWEN_PROMPT_VERSION,
        "verifier_system_prompt_sha256": hashlib.sha256(qv.SYSTEM.encode("utf-8")).hexdigest(),
        "modular_code_sha256": sha_many([ev / "modular" / f"{n}.py" for n in MODULAR_FILES]),
        "rubric_engine_version": __import__("src.evaluation.modular.rubric_engine", fromlist=["x"]).ENGINE_VERSION,
        "legacy_code_sha256": sha_many(sorted(ev.glob("*.py")) + sorted((ev / "providers").glob("*.py"))),
        "model_config": MODEL_CONFIG,
        "model_config_sha256": hashlib.sha256(json.dumps(MODEL_CONFIG, sort_keys=True).encode()).hexdigest(),
        "protocol_files_sha256": {f: sha_file(ROOT / f) for f in PROTOCOL_FILES if (ROOT / f).exists()},
    }


def build():
    fp = compute()
    MANIFEST.write_text(json.dumps({"stage": "3C-2", "status": "FROZEN_BEFORE_ANY_REAL_MODEL_RUN", "labels": "all AI-authored; none human-reviewed", "fingerprints": fp},
                                   indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print("froze", len(fp["sample_ids"]), "answers;", MANIFEST)


def verify(quiet=False) -> list:
    want = json.loads(MANIFEST.read_text(encoding="utf-8"))["fingerprints"]
    got = compute()
    bad = []
    for k, v in want.items():
        if k == "protocol_files_sha256":
            bad += [f"{f}" for f, h in v.items() if got[k].get(f) != h] + [f"{f} (missing)" for f in v if f not in got[k]]
        elif got.get(k) != v:
            bad.append(k)
    if not quiet:
        print("freeze verified: no drift" if not bad else "DRIFT in: " + ", ".join(bad))
    return bad


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "build":
        build()
    else:
        sys.exit(1 if verify() else 0)
