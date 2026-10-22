"""Extractors that turn EXISTING result files into MLflow RunSpecs (imported historical results).

Rules: values are copied verbatim from the source file (no recomputation, no rounding beyond what the file holds); every run records the source path and
sha256; expectations/labels are tagged with their real provenance (AI-authored, not human ground truth); nothing is re-run. Missing keys are skipped, not invented."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from . import version
from .tracking import PROVENANCE_IMPORTED, ROOT, RunSpec

STAGE2C = "data/retrieval/stage2c/eval_results.json"
STAGE3B = {
    "stage3b_llama_smoke": "data/evaluation/stage3b/analysis_llama3.2_3b.json",
    "stage3b_llama_confirm": "data/evaluation/stage3b_confirm/analysis_llama3.2_3b.json",
    "stage3b_qwen_v1": "data/evaluation/stage3b_qwen/analysis_qwen2.5_7b.json",
    "stage3b_qwen_v2": "data/evaluation/stage3b_qwen_v2/analysis_qwen2.5_7b.json",
}
STAGE3C2_DIR = "data/evaluation/stage3c2_results/20261015T120208Z"
DOC_FORMAT = {"dense_qka": "qka", "dense_question": "question", "dense_qk": "qk", "dense_qk_concise": "qk_concise", "bm25_qka": "qka"}
HIST_DESC = "IMPORTED HISTORICAL RESULT. Copied from {src} (sha256 {sha}); not re-run. {extra}"


def _load(rel: str):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")), version.sha256_file(p)


def _g(d: Any, *path: str, default=None):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def _num(d: Dict[str, Any], out: Dict[str, Any], mapping: Dict[str, Any]) -> None:
    for name, v in mapping.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[name] = v


def retrieval_stage2c() -> List[RunSpec]:
    d, sha = _load(STAGE2C)
    emb = d.get("embedder", {})
    specs: List[RunSpec] = []
    for set_name, block in d["sets"].items():
        for system, m in block["systems"].items():
            metrics: Dict[str, Any] = {}
            for k in (
                "n_answerable",
                "n_primary",
                "success@1",
                "success@3",
                "success@5",
                "mrr@10",
                "ndcg@5",
                "success@5_lenient",
                "recall@5",
                "unjudged_top10",
            ):
                if k in m:
                    metrics[k] = m[k]
            na = m.get("no_answer") or {}
            for k_src, k_dst in (
                ("n", "no_answer_n"),
                ("mean_top1_score_no_answer", "no_answer_mean_top1"),
                ("mean_top1_score_answerable", "answerable_mean_top1"),
                ("top1_score_auroc_answerable_vs_no_answer", "no_answer_auroc"),
                ("frac_no_answer_top1_above_answerable_median", "no_answer_frac_above_median"),
            ):
                if k_src in na:
                    metrics[k_dst] = na[k_src]
            dense = system.startswith("dense")
            if dense:
                for k, v in (d.get("query_encode_ms") or {}).items():
                    if isinstance(v, (int, float)):
                        metrics[f"query_encode_ms_{k}"] = v
                es = (d.get("embed_seconds") or {}).get(DOC_FORMAT[system])
                if es is not None:
                    metrics["embed_corpus_seconds"] = es
            params = {
                "stage": "2C",
                "eval_set": set_name,
                "system": system,
                "doc_format": DOC_FORMAT.get(system),
                "retriever": "dense (FAISS)" if dense else "BM25 (lexical)",
                "corpus_sha256": d.get("corpus_sha256"),
                "tokenizer": d.get("tokenizer"),
                "faiss_vs_numpy": d.get("faiss_vs_numpy"),
            }
            if dense:
                params.update(
                    embedder_backend=emb.get("backend"),
                    embedder_model=emb.get("model"),
                    embedder_dim=emb.get("dim"),
                    embedder_max_seq_length=emb.get("max_seq_length"),
                    embedder_normalised=emb.get("normalised"),
                    sentence_transformers=emb.get("sentence_transformers"),
                    torch=emb.get("torch"),
                    device=emb.get("device"),
                    embedder_revision="not recorded in the source file",
                )
            specs.append(
                RunSpec(
                    experiment="smart-retrieval",
                    run_name=f"[imported] stage2c {set_name} / {system}",
                    key=f"stage2c:{set_name}:{system}",
                    params=params,
                    metrics=metrics,
                    tags={
                        "smart.label_source": "ai_authored_pooled_judgements_not_human_validated",
                        "smart.stage": "2C",
                        "smart.eval_set": set_name,
                        "smart.note": "retrieval metrics use AI-authored relevance labels; they are not human ground truth",
                    },
                    source_path=STAGE2C,
                    source_sha256=sha,
                    description=HIST_DESC.format(
                        src=STAGE2C, sha=sha[:12], extra="Relevance labels are AI-authored; the challenge_min/_max sets are label-sensitivity variants."
                    ),
                )
            )
    return specs


def evaluation_stage3b() -> List[RunSpec]:
    specs: List[RunSpec] = []
    for key, rel in STAGE3B.items():
        p = ROOT / rel
        if not p.is_file():
            continue
        d, sha = _load(rel)
        meta = d.get("meta", {})
        m: Dict[str, Any] = {}
        n = d.get("n_calls")
        m["n_calls"] = n
        sc = d.get("schema", {})
        _num(
            sc,
            m,
            {
                "schema_valid_first_attempt_pct": sc.get("valid_on_first_attempt_pct"),
                "schema_valid_first_attempt_n": sc.get("valid_on_first_attempt"),
                "schema_needed_repair": sc.get("needed_repair"),
                "schema_invalid_response": sc.get("invalid_response"),
                "schema_provider_error": sc.get("provider_error"),
                "calls_reached_model": sc.get("calls_that_reached_the_model"),
            },
        )
        sv = d.get("status_vs_expectation", {})
        _num(sv, m, {"status_match_vs_ai_expectation": sv.get("match"), "status_mismatch_vs_ai_expectation": sv.get("mismatch")})
        sb = d.get("score_in_band_overall", {})
        _num(sb, m, {"score_in_ai_band_n": sb.get("n"), "score_in_ai_band": sb.get("in_band"), "score_in_ai_band_pct": sb.get("pct")})
        fe = d.get("factual_errors", {})
        _num(
            fe,
            m,
            {
                "seeded_error_items": fe.get("items_with_seeded_errors"),
                "seeded_error_items_detected": fe.get("item_level_detection"),
                "false_error_flags_any": fe.get("false_error_flags_any"),
            },
        )
        ev = d.get("evidence", {})
        _num(ev, m, {"evidence_dropped_share_pct": ev.get("dropped_share_pct"), "evidence_kept": ev.get("kept")})
        lr = d.get("latency_and_resources", {})
        _num(
            lr,
            m,
            {
                "latency_wall_s_median": lr.get("wall_s_median"),
                "latency_wall_s_p90": lr.get("wall_s_p90"),
                "latency_wall_s_max": lr.get("wall_s_max"),
                "total_minutes": lr.get("total_minutes"),
                "output_tokens_per_s_median": lr.get("output_tokens_per_s_median"),
                "prompt_tokens_median": lr.get("prompt_tokens_median"),
                "possible_context_truncation_calls": lr.get("possible_context_truncation_calls"),
            },
        )
        for st, c in (d.get("status_counts") or {}).items():
            if isinstance(c, int):
                m[f"status_count_{st}"] = c
        if n:
            ins = (d.get("status_counts") or {}).get("insufficient_evidence", 0)
            m["abstain_like_share_insufficient_evidence"] = ins / n
        params = {
            "stage": "3B",
            "model": meta.get("model"),
            "provider": "ollama (local)",
            "ollama_version": meta.get("ollama_version"),
            "num_ctx": meta.get("num_ctx"),
            "prompt_version": meta.get("prompt_version"),
            "rubric_version": meta.get("rubric_version"),
            "evaluation_code_fingerprint": meta.get("evaluation_code_fingerprint"),
            "bench": meta.get("bench"),
            "bench_set": meta.get("set"),
            "repeats": meta.get("repeats"),
            "is_mock": meta.get("is_mock"),
            "platform": meta.get("platform"),
            "python": meta.get("python"),
            "started_utc": meta.get("started_utc"),
            "evaluator_implementation": "legacy single-call evaluator (src/evaluation)",
        }
        specs.append(
            RunSpec(
                experiment="smart-evaluation",
                run_name=f"[imported] {key} ({meta.get('model')}, prompt {meta.get('prompt_version')})",
                key=key,
                params=params,
                metrics=m,
                tags={
                    "smart.label_source": "ai_authored_unreviewed_not_ground_truth",
                    "smart.stage": "3B",
                    "smart.n_calls": str(n),
                    "smart.note": f"tiny sample (n={n}); exploratory only. {d.get('label_provenance', '')}"[:480],
                },
                source_path=rel,
                source_sha256=sha,
                description=HIST_DESC.format(src=rel, sha=sha[:12], extra=f"Tiny sample (n={n}); expectations are AI-authored."),
            )
        )
    return specs


def evaluation_stage3c2() -> List[RunSpec]:
    a, a_sha = _load(f"{STAGE3C2_DIR}/analysis_v2.json")
    r, _ = _load(f"{STAGE3C2_DIR}/results.json")
    fm_rel = "data/evaluation/stage3c2/freeze_manifest_v2.json"
    fm, fm_sha = _load(fm_rel)
    met = a["metrics"]
    m: Dict[str, Any] = {}
    for k, v in met.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            m[k] = v
    for grp, prefix in (
        ("verdict_states_after_gate", "verdicts_after_gate_"),
        ("verdict_states_as_returned_by_model", "verdicts_model_returned_"),
        ("modular_status", "modular_rows_"),
        ("evidence_rejection_reasons", "evidence_rejected_"),
    ):
        for k, v in (met.get(grp) or {}).items():
            if isinstance(v, (int, float)):
                m[prefix + k] = v
    for k, v in (a.get("warm_latency", {}).get("modular_warm") or {}).items():
        if isinstance(v, (int, float)):
            m[f"warm_latency_modular_{k}"] = v
    for k, v in (a.get("warm_latency", {}).get("legacy_warm") or {}).items():
        if isinstance(v, (int, float)):
            m[f"warm_latency_legacy_{k}"] = v
    ra = a.get("repeat_agreement", {})
    _num(
        ra,
        m,
        {
            "repeat_members_compared": ra.get("members_compared"),
            "repeat_agreement_after_gate": ra.get("agreement_after_gate"),
            "repeat_agreement_before_gate": ra.get("agreement_before_gate"),
        },
    )
    passes = fails = 0
    for c in a.get("mechanical_criteria", []):
        name = c["criterion"]
        if isinstance(c.get("value"), (int, float)):
            m[f"criterion_{name}_value"] = c["value"]
        ok = c.get("result") == "PASS"
        m[f"criterion_{name}_pass"] = 1.0 if ok else 0.0
        passes, fails = passes + ok, fails + (not ok)
    m["criteria_passed"], m["criteria_failed"] = passes, fails
    fc = r.get("meta", {}).get("frozen_config", {})
    params = {
        "stage": "3C-2",
        "model": fc.get("model"),
        "provider": fc.get("provider"),
        "temperature": fc.get("temperature"),
        "seed_rule": fc.get("seed_rule"),
        "num_ctx": fc.get("num_ctx"),
        "max_output_tokens": fc.get("max_output_tokens"),
        "timeout_s": fc.get("timeout_s"),
        "modular_repeats": fc.get("modular_repeats"),
        "structured_output": fc.get("structured_output"),
        "answers": r.get("meta", {}).get("answers"),
        "partial_run": r.get("meta", {}).get("partial_run"),
        "ollama_version": r.get("meta", {}).get("ollama_version"),
        "platform": r.get("meta", {}).get("platform"),
        "started_utc": r.get("meta", {}).get("started_utc"),
        "run_dir": STAGE3C2_DIR.rsplit("/", 1)[-1],
        "analyzer_version": a.get("analyzer_version"),
        "freeze_manifest_v2_version": fm.get("version"),
        "freeze_manifest_v2_sha256": fm_sha,
        "freeze_manifest_sha256_reported_by_results_json": r.get("meta", {}).get("freeze_manifest_sha256"),
        "modular_pipeline_version": version.evaluator_versions().get("pipeline"),
        "qwen_prompt_version": version.evaluator_versions().get("qwen_prompt"),
        "verifier_system_prompt_sha256": _g(fm, "unchanged_since_v1", "verifier_system_prompt_sha256"),
        "modular_code_sha256": _g(fm, "unchanged_since_v1", "modular_code_sha256"),
        "sample_jsonl_sha256": _g(fm, "unchanged_since_v1", "sample_jsonl_sha256"),
    }
    arts = [(f"{STAGE3C2_DIR}/analysis_v2.json", "source")]
    spec = RunSpec(
        experiment="smart-evaluation",
        run_name="[imported] stage3c2 qwen2.5:7b modular evaluator, 20-answer frozen experiment",
        key="stage3c2:20261015T120208Z",
        params=params,
        metrics=m,
        tags={
            "smart.stage": "3C-2",
            "smart.decision": "DO NOT ADVANCE",
            "smart.decision_reason": "abstain_rate 0.45 > max 0.40 (criterion abstain_rate_max FAIL)",
            "smart.label_source": "ai_provisional_not_human_reviewed",
            "smart.frozen": "true",
            "smart.n_answers": "20",
            "smart.note": "exploratory, n=20 answers / 40 modular rows; NOT grading accuracy and NOT human agreement",
        },
        source_path=f"{STAGE3C2_DIR}/analysis_v2.json",
        source_sha256=a_sha,
        artifacts=arts,
        description=HIST_DESC.format(
            src=f"{STAGE3C2_DIR}/analysis_v2.json", sha=a_sha[:12], extra="Frozen experiment. Decision: DO NOT ADVANCE. " + str(a.get("disclaimer", ""))
        ),
    )
    return [spec]


def all_specs() -> List[RunSpec]:
    return retrieval_stage2c() + evaluation_stage3b() + evaluation_stage3c2()


def import_all(allow_drift: bool = False) -> Dict[str, Any]:
    from .tracking import record

    out = {"created": 0, "exists": 0, "runs": []}
    for s in all_specs():
        rid, st = record(s, provenance=PROVENANCE_IMPORTED, allow_drift=allow_drift)
        out[st] += 1
        out["runs"].append({"key": s.key, "run_id": rid, "status": st})
    return out
