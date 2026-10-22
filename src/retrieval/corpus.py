"""Read-only unified retrieval corpus: frozen v5 + approved expansion batches.

Nothing here writes to or modifies any dataset file. The loader validates the
inputs against the approval registry and per-dataset manifests and refuses to
return a corpus that fails validation (unless ``strict=False``, which is for
tests only).
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

csv.field_size_limit(10_000_000)

V5_CSV = "data/curated/v5/curated_questions.csv"
V5_MANIFEST = "data/curated/v5/manifest.json"
REGISTRY = "data/expansion/approved_batches.json"
EXPECTED_V5_FINGERPRINT = "9eb94d8fe8bc83486dd401c5651878ebef0c4d0bd2c359d6e58fe12ba4637123"
EXPECTED_V5_RECORDS = 487

REQUIRED_FIELDS = ("id", "domain", "topic", "difficulty", "question", "answer", "key_concepts", "verification")
DIFFICULTIES = ("Easy", "Medium", "Hard")
# fields of the dataset fingerprint (same definition as the staged-batch validator)
_FP_FIELDS = ["id", "domain", "topic", "difficulty", "question_type", "question", "answer", "key_concepts", "common_mistakes"]
_ID_RE = re.compile(r"^smi-[a-z]?\d{4}$")
_ALT_FIELDS = (("concise", "concise_answer"), ("detailed", "detailed_answer"), ("practical", "practical_answer"))


class CorpusValidationError(RuntimeError):
    """Raised when the corpus fails validation against the registry/manifests."""


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(p: Path) -> str:
    return _sha256_bytes(p.read_bytes())


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        # malformed/short rows yield None values: normalise to "" so validation reports them instead of crashing
        return [{k: (v if isinstance(v, str) else "") for k, v in r.items() if k is not None} for r in csv.DictReader(f)]


def _json_list(s: str) -> list:
    s = (s or "").strip()
    if not s:
        return []
    try:
        v = json.loads(s)
        return v if isinstance(v, list) else []
    except json.JSONDecodeError:
        return []


def _split_concepts(s: str) -> List[str]:
    return [c.strip() for c in (s or "").split(";") if c.strip()]


def _dataset_fingerprint(rows: List[Dict[str, str]], tests_path: Path) -> Dict[str, str]:
    content = hashlib.sha256(json.dumps(
        [[str(r.get(f, "")) for f in _FP_FIELDS] for r in sorted(rows, key=lambda r: r["id"])],
        ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    tests = json.loads(tests_path.read_text(encoding="utf-8"))
    tsha = hashlib.sha256(json.dumps(tests, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"content_sha256": content, "code_tests_sha256": tsha,
            "combined_sha256": hashlib.sha256((content + tsha).encode()).hexdigest()}


def _to_record(row: Dict[str, str], origin: str, provenance: Dict[str, Any]) -> Dict[str, Any]:
    """Map one dataset row to a structured knowledge record (all original fields preserved)."""
    canonical = row["answer"].strip()
    alternatives: Dict[str, str] = {}
    for name, col in _ALT_FIELDS:
        val = (row.get(col) or "").strip()
        # 'detailed' equals the canonical answer for multi-variant records: not a separate alternative
        if val and val != canonical:
            alternatives[name] = val
    sources = _json_list(row.get("sources", ""))
    return {
        "question_id": row["id"],
        "domain": row["domain"],
        "topic": row["topic"],
        "difficulty": row["difficulty"],
        "question_type": (row.get("question_type") or "").strip(),
        "question": row["question"].strip(),
        "canonical_answer": canonical,
        "alternative_answers": alternatives,
        "answer_set": (row.get("answer_set") or "").strip() or "legacy_v5",
        "key_concepts": _split_concepts(row.get("key_concepts", "")),
        "common_mistakes": _json_list(row.get("common_mistakes", "")),
        "rubric_points": (row.get("rubric_points") or "").strip(),
        "tags": _split_concepts(row.get("tags", "")),
        "verification": {
            "verification": row.get("verification", ""),
            "v6_verification": row.get("v6_verification", ""),
            "human_reviewed": False,  # no record in v5 or any batch has been human-reviewed
            "has_code_test": (row.get("has_code_test", "") == "yes"),
            "source_opened": "source_opened" in row.get("verification", ""),
            "code_executed": "code_executed" in row.get("verification", ""),
            "time_sensitive": (row.get("time_sensitive", "") == "yes"),
            "review_by": row.get("review_by", ""),
            "remaining_limitations": row.get("remaining_limitations", ""),
        },
        "sources": sources,
        "provenance": {"origin": origin, "source_type": row.get("source_type", ""),
                       "plan_id": row.get("plan_id", ""), "introduced_in": row.get("introduced_in", ""),
                       **provenance},
    }


def _fail(msgs: List[str], strict: bool) -> None:
    if msgs and strict:
        raise CorpusValidationError("; ".join(msgs[:8]) + (f" (+{len(msgs) - 8} more)" if len(msgs) > 8 else ""))


def load_corpus(root: Optional[Path | str] = None, strict: bool = True) -> Dict[str, Any]:
    """Load the unified corpus. Returns {'records': [...], 'manifest': {...}, 'problems': [...]}.

    Records are ordered deterministically (v5 by id, then batches 1-4 by id), which fixes
    the vector-row order used by the index.
    """
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    problems: List[str] = []

    registry = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    v5_manifest = json.loads((root / V5_MANIFEST).read_text(encoding="utf-8"))
    v5_path = root / V5_CSV

    # --- frozen v5 ---
    if v5_manifest["fingerprint"]["combined_sha256"] != EXPECTED_V5_FINGERPRINT:
        problems.append("v5 manifest fingerprint differs from the frozen value")
    if registry["frozen_base"]["fingerprint"] != EXPECTED_V5_FINGERPRINT:
        problems.append("registry frozen_base fingerprint differs from the frozen value")
    if _sha256_file(v5_path) != v5_manifest["files"]["curated_questions.csv"]:
        problems.append("v5 curated_questions.csv hash differs from its manifest")
    v5_rows = _read_csv(v5_path)
    if len(v5_rows) != EXPECTED_V5_RECORDS or len(v5_rows) != registry["frozen_base"]["records"]:
        problems.append(f"v5 record count {len(v5_rows)} != {EXPECTED_V5_RECORDS}")
    v5_fp = _dataset_fingerprint(v5_rows, root / "data/curated/v5/code_tests.json")
    if v5_fp["combined_sha256"] != EXPECTED_V5_FINGERPRINT:
        problems.append("v5 recomputed fingerprint differs from the frozen value")

    records: List[Dict[str, Any]] = []
    components: List[Dict[str, Any]] = [{"name": "v5", "records": len(v5_rows), "fingerprint": v5_fp["combined_sha256"],
                                         "csv": V5_CSV, "csv_sha256": _sha256_file(v5_path)}]
    for r in sorted(v5_rows, key=lambda r: r["id"]):
        records.append(_to_record(r, "v5", {"batch": "v5", "dataset_fingerprint": v5_fp["combined_sha256"]}))

    # --- approved batches ---
    quarantined = {q["id"] for q in registry.get("quarantined", [])}
    for b in registry["batches"]:
        name = b["batch"]
        if not str(b["status"]).startswith("approved"):
            problems.append(f"{name}: not approved in registry ({b['status']})")
            continue
        d = root / "data/expansion" / name
        csv_path = root / b["accepted_csv"]
        man_path = d / "manifest.json"
        if _sha256_file(csv_path) != b["accepted_csv_sha256"]:
            problems.append(f"{name}: accepted csv hash differs from registry")
        if _sha256_file(man_path) != b["manifest_sha256"]:
            problems.append(f"{name}: manifest hash differs from registry")
        man = json.loads(man_path.read_text(encoding="utf-8"))
        rows = _read_csv(csv_path)
        if len(rows) != b["records"] or len(rows) != man["record_count"]:
            problems.append(f"{name}: record count {len(rows)} != registry {b['records']} / manifest {man['record_count']}")
        fp = _dataset_fingerprint(rows, d / "code_tests.json")
        if not (fp["combined_sha256"] == b["fingerprint"] == man["fingerprint"]["combined_sha256"]):
            problems.append(f"{name}: recomputed fingerprint differs from registry/manifest")
        for r in sorted(rows, key=lambda r: r["id"]):
            if r["id"] in quarantined:
                problems.append(f"{name}: quarantined id {r['id']} present in accepted csv")
                continue
            records.append(_to_record(r, name, {"batch": name, "batch_revision": b["revision"],
                                                "dataset_fingerprint": fp["combined_sha256"]}))
        components.append({"name": name, "records": len(rows), "fingerprint": fp["combined_sha256"],
                           "revision": b["revision"], "csv": b["accepted_csv"], "csv_sha256": b["accepted_csv_sha256"]})

    # --- record-level validation ---
    seen: Dict[str, int] = {}
    for i, rec in enumerate(records):
        qid = rec["question_id"]
        if qid in seen:
            problems.append(f"duplicate id {qid}")
        seen[qid] = i
        if not _ID_RE.match(qid):
            problems.append(f"{qid}: id format")
        for f in ("domain", "topic", "difficulty", "question", "canonical_answer", "key_concepts"):
            if not rec[f]:
                problems.append(f"{qid}: missing {f}")
        if not rec["verification"]["verification"]:
            problems.append(f"{qid}: missing verification status")
        if rec["difficulty"] not in DIFFICULTIES:
            problems.append(f"{qid}: bad difficulty {rec['difficulty']!r}")
    if len(records) != registry["totals"]["combined_if_merged"]:
        problems.append(f"record total {len(records)} != registry combined {registry['totals']['combined_if_merged']}")
    problems = list(dict.fromkeys(problems))
    _fail(problems, strict)

    manifest = build_manifest(records, components, registry)
    return {"records": records, "manifest": manifest, "problems": problems}


def corpus_fingerprint(records: List[Dict[str, Any]]) -> str:
    """sha256 over every retrieval-relevant field, in id order (independent of row order)."""
    payload = [[r["question_id"], r["domain"], r["topic"], r["difficulty"], r["question"], r["canonical_answer"],
                json.dumps(r["alternative_answers"], sort_keys=True, ensure_ascii=False), "; ".join(r["key_concepts"])]
               for r in sorted(records, key=lambda r: r["question_id"])]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def build_manifest(records: List[Dict[str, Any]], components: List[Dict[str, Any]], registry: Dict[str, Any]) -> Dict[str, Any]:
    from collections import Counter
    return {
        "corpus": "smart-mock-interview-retrieval-corpus",
        "stage": "2A",
        "record_count": len(records),
        "unique_ids": len({r["question_id"] for r in records}),
        "order": "v5 by id, then batch_01..batch_04 each by id",
        "components": components,
        "registry_totals": registry["totals"],
        "excluded_quarantined": [q["id"] for q in registry.get("quarantined", [])],
        "domain_counts": dict(sorted(Counter(r["domain"] for r in records).items())),
        "difficulty_counts": dict(sorted(Counter(r["difficulty"] for r in records).items())),
        "records_with_alternatives": sum(1 for r in records if r["alternative_answers"]),
        "records_time_sensitive": sum(1 for r in records if r["verification"]["time_sensitive"]),
        "human_reviewed_records": 0,
        "corpus_sha256": corpus_fingerprint(records),
        "fingerprint_definition": "sha256 of compact JSON of [id,domain,topic,difficulty,question,canonical_answer,alternatives(json),key_concepts] sorted by id",
    }
