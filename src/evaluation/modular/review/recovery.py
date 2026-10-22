"""Result persistence and recovery for interrupted experiment runs, WITHOUT changing the experiment protocol.

The frozen runner rewrites results.json after every model call but (a) not atomically, so a kill during the write can leave a truncated file, and (b) it cannot
resume. This module does what can be done safely around it:
  load_results_tolerant   read a complete or truncated results.json, keeping every COMPLETE record and reporting exactly what was dropped
  plan_resume             what is done / missing per pass, and the exact `--ids` command for the frozen runner for the missing answers
  merge_runs              assemble several (partial) runs of the SAME frozen experiment into one document, refusing any drift, labelling it as assembled
  atomic_write_text       tmp-file + rename, for every writer in the review tools
Nothing here re-runs a model or edits a recorded row."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def _decode_array(text: str, start: int) -> Tuple[List[Any], bool, int]:
    """Decode consecutive JSON values of an array starting just after '['. Returns (items, closed_properly, end_index)."""
    dec, i, items = json.JSONDecoder(), start, []
    n = len(text)
    while i < n:
        while i < n and text[i] in " \n\r\t,":
            i += 1
        if i >= n:
            return items, False, i
        if text[i] == "]":
            return items, True, i + 1
        try:
            obj, i = dec.raw_decode(text, i)
        except ValueError:
            return items, False, i
        items.append(obj)
    return items, False, i


def load_results_tolerant(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """(doc, report). A valid file loads normally. A truncated one is salvaged: meta + every complete record of each pass; the partial record is discarded."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        doc = json.loads(text)
        return doc, {"repaired": False, "dropped_incomplete_record": False, "modular": len(doc.get("modular", [])), "legacy": len(doc.get("legacy", []))}
    except ValueError:
        pass
    dec = json.JSONDecoder()
    k = text.find('"meta"')
    if k < 0:
        raise ValueError("not a results file: no meta block")
    j = text.find("{", k)
    try:
        meta, _ = dec.raw_decode(text, j)
    except ValueError as e:
        raise ValueError("results file is truncated inside the meta block; nothing can be recovered") from e
    doc: Dict[str, Any] = {"meta": meta, "modular": [], "legacy": []}
    dropped = False
    for key in ("modular", "legacy"):
        a = text.find(f'"{key}"', j)
        if a < 0:
            continue
        b = text.find("[", a)
        items, closed, _ = _decode_array(text, b + 1)
        doc[key] = items
        dropped = dropped or not closed
        if not closed:
            break                                   # the file ends inside this array: later passes cannot exist
    doc["meta"] = {**meta, "recovered_from_truncated_file": True, "partial_run": True}
    return doc, {"repaired": True, "dropped_incomplete_record": dropped, "modular": len(doc["modular"]), "legacy": len(doc["legacy"])}


def plan_resume(doc: Dict[str, Any], sample_ids: Iterable[str], modular_repeats: int = 2, legacy_repeats: int = 1, host: str = "") -> Dict[str, Any]:
    ids = list(sample_ids)
    have_m = {(r["sample_id"], r["repeat"]) for r in doc.get("modular", [])}
    have_l = {(r["sample_id"], r["repeat"]) for r in doc.get("legacy", [])}
    miss_m = [(s, r) for r in range(modular_repeats) for s in ids if (s, r) not in have_m]
    miss_l = [(s, r) for r in range(legacy_repeats) for s in ids if (s, r) not in have_l]
    need = sorted({s for s, _ in miss_m + miss_l}, key=ids.index)
    cmd = (f'powershell -ExecutionPolicy Bypass -File scripts\\stage3c2_run_v2.ps1 -Ids "{",".join(need)}"' if need else "")
    return {"modular_done": len(have_m), "modular_missing": miss_m, "legacy_done": len(have_l), "legacy_missing": miss_l, "answers_to_rerun": need,
            "complete": not need, "rerun_command_hint": cmd,
            "note": "a subset run re-runs BOTH passes for those answers and is labelled partial; merge_runs keeps the earlier complete record and ignores duplicates."}


def merge_runs(docs: List[Dict[str, Any]], expected_ids: Iterable[str], modular_repeats: int = 2, legacy_repeats: int = 1) -> Dict[str, Any]:
    """Assemble runs of the same frozen experiment. Refuses a different freeze manifest or model config. Earlier records win on duplicates."""
    if not docs:
        raise ValueError("nothing to merge")
    m0 = docs[0]["meta"]
    for d in docs[1:]:
        for k in ("freeze_manifest_sha256", "frozen_config"):
            if d["meta"].get(k) != m0.get(k):
                raise ValueError(f"cannot merge runs with different {k}: they are not the same frozen experiment")
    out = {"meta": {**m0, "assembled_from_runs": [d["meta"].get("started_utc") for d in docs], "assembled_run": True,
                    "latency_caveat": "records come from separate process sessions; cold-start and memory conditions differ between them"},
           "modular": [], "legacy": []}
    seen_m, seen_l = set(), set()
    for d in docs:
        for r in d.get("modular", []):
            k = (r["sample_id"], r["repeat"])
            if k not in seen_m: seen_m.add(k); out["modular"].append(r)
        for r in d.get("legacy", []):
            k = (r["sample_id"], r["repeat"])
            if k not in seen_l: seen_l.add(k); out["legacy"].append(r)
    plan = plan_resume(out, expected_ids, modular_repeats, legacy_repeats)
    out["meta"]["partial_run"] = not plan["complete"]
    out["meta"]["finished_utc"] = max((d["meta"].get("finished_utc") or "") for d in docs) or None
    return out
