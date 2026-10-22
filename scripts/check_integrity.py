"""Dataset / frozen-experiment integrity gate (no models, no network, read-only). Reuses the project's own controls:

  1. src.retrieval.corpus.load_corpus(strict=True)  - frozen v5 fingerprint + per-batch fingerprints against the registry
  2. data/retrieval/corpus_manifest.json            - per-component csv sha256 and corpus fingerprint still match the files on disk
  3. scripts/stage3c2_freeze_v2.verify()            - Stage 3C-2 prompt/gate/rubric/sample/config hashes unchanged
  4. data/evaluation/bench_v2/manifest.json         - bench_v2 file hashes unchanged
  (the scope sidecar hash is covered by item 3: it is one of the frozen files)

Exit code 0 = no drift. Run:  python scripts/check_integrity.py"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def crlf_files(root: Path = ROOT) -> list:
    """Hash-pinned data files whose bytes contain CRLF. On Windows, Git's core.autocrlf=true produces these on checkout and every sha256 then differs."""
    pinned = [root / "data/curated/v5/curated_questions.csv", root / "data/retrieval/corpus_manifest.json"]
    pinned += sorted((root / "data/expansion").glob("batch_*/batch_*_accepted.csv")) + sorted((root / "data/evaluation/bench_v2").glob("*.jsonl"))
    return [p.relative_to(root).as_posix() for p in pinned if p.is_file() and b"\r\n" in p.read_bytes()]


CRLF_HINT = (
    "HINT: these hash-pinned files contain Windows line endings (CRLF), which is what Git for Windows does when core.autocrlf=true and no .gitattributes\n"
    "  applies. Fix:  git config core.autocrlf false  &&  git rm --cached -r -q .  &&  git reset --hard   (commit or stash your work first)\n"
    "  or re-clone after .gitattributes (eol=lf) is present. Do NOT edit the manifests to match: that would hide real drift."
)


def main() -> int:
    problems = []
    try:
        from src.retrieval.corpus import corpus_fingerprint, load_corpus

        c = load_corpus(strict=True)
        print(f"[1] corpus loader strict: OK ({len(c['records'])} records, fingerprint {corpus_fingerprint(c['records'])[:16]}...)")
        man = json.loads((ROOT / "data/retrieval/corpus_manifest.json").read_text(encoding="utf-8"))
        for comp in man["components"]:
            if sha(ROOT / comp["csv"]) != comp["csv_sha256"]:
                problems.append(f"corpus component {comp['name']}: csv sha256 differs from corpus_manifest.json")
        if man.get("record_count") != len(c["records"]):
            problems.append("corpus_manifest.json record_count differs from the loaded corpus")
        print("[2] corpus_manifest.json component hashes:", "OK" if not any("corpus" in p for p in problems) else "DRIFT")
    except Exception as e:
        problems.append(f"corpus integrity: {type(e).__name__}: {str(e)[:200]}")
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("freeze_v2", ROOT / "scripts/stage3c2_freeze_v2.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        drift = mod.verify(quiet=True)
        print("[3] Stage 3C-2 freeze v2:", "no drift" if not drift else f"DRIFT {drift}")
        problems += [f"freeze v2: {d}" for d in drift]
    except Exception as e:
        problems.append(f"freeze v2: {type(e).__name__}: {str(e)[:200]}")
    try:
        bm = json.loads((ROOT / "data/evaluation/bench_v2/manifest.json").read_text(encoding="utf-8"))
        bad = [f for f, h in bm["sha256"].items() if sha(ROOT / "data/evaluation/bench_v2" / f) != h]
        print("[4] bench_v2 file hashes:", "OK" if not bad else f"DRIFT {bad}")
        problems += [f"bench_v2 {f} changed" for f in bad]
    except Exception as e:
        problems.append(f"bench_v2: {type(e).__name__}: {str(e)[:200]}")
    print("INTEGRITY OK - no frozen file drifted." if not problems else "INTEGRITY FAILED:\n  " + "\n  ".join(problems))
    if problems:
        bad_eol = crlf_files()
        if bad_eol:
            print(CRLF_HINT + "\n  affected: " + ", ".join(bad_eol[:6]))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
