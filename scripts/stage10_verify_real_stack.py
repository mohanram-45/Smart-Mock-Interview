"""Stage 10: run the memory-aware interviewer against the REAL local stack on YOUR machine (real Ollama; real Sentence-BERT when installed), and record what happened.

  .bot\\Scripts\\python.exe scripts\\stage10_verify_real_stack.py                              llama3.2:3b (the measured latency baseline), 2 scripted interviews
  .bot\\Scripts\\python.exe scripts\\stage10_verify_real_stack.py --models llama3.2:3b qwen2.5:7b --runs 3
  .bot\\Scripts\\python.exe scripts\\stage10_verify_real_stack.py --mlflow                     also log metrics/params (NO answers) to the existing MLflow tracking store
  .bot\\Scripts\\python.exe scripts\\stage10_verify_real_stack.py --sbert                      use Sentence-BERT for memory retrieval when it is cached (never downloads)
  .bot\\Scripts\\python.exe scripts\\stage10_verify_real_stack.py --opportunities --models llama3.2:3b --mlflow --sbert   per eligible opportunity on the fixed 10F set (preferred)
  python scripts/stage10_verify_real_stack.py --selftest [--opportunities]                                       scripted fake server: tests THIS SCRIPT only; its timings are NOT real

What it does: for each model, one background warm-up (cold-load cost reported separately), then scripted technical interviews (a Data Scientist whose introduction states a project and whose later answers
mention it) in live follow-up mode. It records, per model: how many model proposals were accepted by the fixed rules and why the others were rejected (codes only), how many cited a stored memory,
latency (Ollama's own counters where reported), prompt size, and the circuit-breaker state. It writes results.json, summary.md and a BLIND review sheet for human raters.

NOT claimed: that accepted questions are good (no human has rated them), that one model is better than another (it prints a table; it does not rank), or anything about candidates. Candidate answers here are
synthetic scripts. Nothing is downloaded and nothing leaves this computer. The MLflow run (if requested) holds counts, timings and versions only; never question or answer text."""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

INTRO = ("I developed an oral cancer classification model using PyTorch. I achieved 91% accuracy on the test set. The hardest challenge was class imbalance in the training data. "
         "I want a data science role because I enjoy turning messy data into decisions.")
SUFFIX = " I used the same idea in my oral cancer classification model, where class imbalance was the hardest problem."


def FL_NP():
    from src.demo import followup_llm as FL
    return FL.num_predict()


def partial(canonical: str) -> str:
    """A realistic partial answer: the first half of the reference answer, so there is something left to probe."""
    w = canonical.split()
    return " ".join(w[:max(8, len(w) // 2)]).rstrip(",;") + "."


def http_json(url, timeout=5, body=None):
    import urllib.request
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8") if body is not None else None, headers={"Content-Type": "application/json"} if body is not None else {})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": f"{type(e).__name__}"}


def pct(xs, p):
    xs = sorted(xs)
    return None if not xs else round(xs[min(len(xs) - 1, int(p * (len(xs) - 1) + 0.5))], 1)


def make_engine(tmp: Path, provider_factory, selftest: bool):
    from src.demo import followup_llm as FL, sim
    gen = FL.LLMFollowUpGenerator(provider_factory(), deadline=float(os.environ.get("S10_DEADLINE", "30")))
    real_sbert = False
    if not selftest:
        try:
            from src.demo.engine import DemoEngine
            from src.demo.store import DemoStore
            eng = DemoEngine(DemoStore(tmp / "sessions"), followup_generator=gen)
            eng.records()
            eng._scorer_factory("bert", ["warm"])                               # raises when torch / the cached model are missing
            real_sbert = True
            return eng, gen, real_sbert
        except Exception as e:
            print(f"[note] real Sentence-BERT scorer unavailable ({type(e).__name__}); using the labelled word-overlap stand-in for the SIMILARITY panel only")
    return sim.offline_engine(tmp, followup_generator=gen), gen, real_sbert


def one_model(model, host, runs, selftest, sbert, out):
    from src.demo import interview as I, memory as M, sim
    from src.demo.ollama_stream import StreamingOllama, derived
    if sbert:
        os.environ["SMART_DEMO_MEMORY_SBERT"] = "1"
    os.environ["SMART_DEMO_LIVE_MODULAR"] = "1"
    tmp = Path(tempfile.mkdtemp(prefix="s10real_"))
    eng, gen, real_sbert = make_engine(tmp, lambda: StreamingOllama(model, host, num_predict=FL_NP(), num_ctx=2048), selftest)
    info = {"model": model, "host": host if not selftest else "fake-server", "real_sbert_scorer": real_sbert, "memory_embedder": M.default_embedder().name, "timings_are_real": not selftest}
    t0 = time.perf_counter()
    try:
        warm = gen.provider.warm(180.0)
        info["cold_load"] = {"client_ms": warm.get("client_elapsed_ms"), **derived(warm)}
    except Exception as e:
        info["cold_load"] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
        info["status"] = "unavailable"
        return info, [], []
    gen.warm_state = "ready"
    gen._needs_warm = False                                                         # already warmed here: the engine's own background warm-up would only race the first call
    rows, review = [], []
    for k in range(runs):
        def ans(n, q, s):
            if I.stage_of(q) == I.INTRO:
                return INTRO
            rec = eng.record(q["question_id"]) if q.get("question_id") else None
            return (partial(rec["canonical_answer"]) + SUFFIX) if rec else "I would explain it with an example."
        s, t = sim.run(eng, {"role": "Data Scientist", "practical": False, "size": 5, "followup_mode": "live", "max_followups": 2}, ans)
        for e in s["plan"].get("followup_log", []):
            rows.append({"run": k, "n": e["n"], "outcome": e["outcome"], "reasons": e.get("reasons", []), "latency_ms": e.get("latency_ms"), "metrics": e.get("metrics", {})})
        for i, q in enumerate(s["questions"]):
            if q.get("followup_kind") == "llm":
                prev = (s["answers"][q["parent_n"] - 1] or {}).get("answer", "") if q.get("parent_n") else ""
                mem = M.get(s["memory"], q["memory_id"]) if q.get("memory_id") else None
                review.append({"model": model, "context_previous_answer": prev[:300], "context_earlier_statement_cited": (mem or {}).get("quote", ""), "interviewer_text": q["question"], "cites_memory": bool(mem)})
        info.setdefault("interviews", []).append({"status": s["status"], "turns": len(s["questions"]), "memory_refs": sum(1 for q in s["questions"] if (q.get("provenance") or {}).get("memory_ref") or q.get("memory_id")),
                                                  "sequence_valid": I.check_sequence(s["questions"]) == []})
    lat = [r["latency_ms"] for r in rows if r["latency_ms"] is not None]
    acc = [r for r in rows if r["outcome"] in ("llm", "mock")]
    skip = [r for r in rows if r["outcome"] == "skip"]
    fb = [r for r in rows if r["outcome"] == "fallback"]
    reasons = {}
    for r in fb:
        for x in r["reasons"]:
            key = x.split(":")[0] + (":" + x.split(":")[1] if x.startswith(("question:", "memory:", "evidence:", "schema:", "concepts:")) and ":" in x else "")
            reasons[key] = reasons.get(key, 0) + 1
    gens = [r["metrics"].get("generated_tokens") for r in rows if isinstance(r["metrics"].get("generated_tokens"), (int, float))]
    info.update(status="ran", calls=len(rows), accepted=len(acc), model_chose_skip=len(skip), fell_back=len(fb), rejection_reason_codes=reasons, accepted_citing_memory=len(review and [x for x in review if x["cites_memory"]]),
                latency_ms={"median": pct(lat, .5), "p95": pct(lat, .95), "max": max(lat) if lat else None}, generated_tokens_median=statistics.median(gens) if gens else None,
                wall_s=round(time.perf_counter() - t0, 1), circuit_breaker_state=str(getattr(gen.breaker, "state", "n/a")))
    return info, rows, review


def opportunities(model, host, selftest, sbert, out, engine=None):
    """Per-ELIGIBLE-OPPORTUNITY run of the fixed set (src/demo/eval_data/stage10f_opportunities_v1.json) with the real model. The set and its expectations were written before any model ran."""
    from src.demo import followup_llm as FL, memory as M, opportunity_eval as OE
    from src.demo.ollama_stream import StreamingOllama, derived
    if sbert:
        os.environ["SMART_DEMO_MEMORY_SBERT"] = "1"
    M.reset_model_cache()
    prov = StreamingOllama(model, host, num_predict=FL.num_predict(), num_ctx=2048)
    from src.demo import intel
    eng_name = intel.engine_name(engine)                                               # None -> SMART_DEMO_FOLLOWUP_ENGINE -> baseline 'stage10n'
    gen = FL.LLMFollowUpGenerator(prov, deadline=float(os.environ.get("S10_DEADLINE", "60")), engine=eng_name)
    info = {"engine": eng_name, "model": model, "host": host if not selftest else "fake-server", "timings_are_real": not selftest, "num_predict": FL.num_predict(), "prompt_version": intel.OBJ_PROMPT_VERSION if eng_name == "objective" else FL.PROMPT_VERSION}
    if not selftest:
        info["ollama_version"] = http_json(host.rstrip("/") + "/api/version").get("version")
        det = (http_json(host.rstrip("/") + "/api/show", body={"model": model}) or {}).get("details") or {}
        info["model_details"] = {k: det.get(k) for k in ("family", "parameter_size", "quantization_level", "format")}
    try:
        warm = prov.warm(180.0)
        info["cold_load_ms"] = warm.get("client_elapsed_ms")
        info["cold_load"] = derived(warm)
    except Exception as e:
        info.update(status="unavailable", error=f"{type(e).__name__}: {str(e)[:120]}")
        return info, []
    gen.warm_state = "ready"
    gen._needs_warm = False
    eng = OE.offline_engine()
    res = OE.run_all(eng, gen, evidence="selftest_fake_server" if selftest else "real_model")
    S = res["summary"]
    rows = res["rows"]
    called = [r for r in rows if r.get("model_called") and r.get("latency_ms")]
    lat = [r["latency_ms"] for r in called]
    E = S["eligible"]
    elig, useful = E["n"], E["success"]
    trunc = sum(1 for r in rows if any("reply_truncated" in str(x) for x in r.get("reasons", [])))
    mem_diag = [{"id": r["id"], "stage": r.get("memory_stage"), "offered": r.get("offered_memory"), "offered_ids": r.get("memory_offered_ids"), "failure_type": r.get("failure_type"), "success": r["success"], "audit": r.get("audit"),
                 "reasons": r.get("reasons"), "mode_trace": r.get("mode_trace"), "retrieval": r.get("retrieval"), "model_replies": r.get("debug")} for r in rows if r["class"] in ("memory_use", "memory_inappropriate")]
    info.update(status="ran", eligible_opportunities=elig, useful_valid=useful, useful_valid_rate=round(useful / elig, 3) if elig else None, target=0.8, eligible=E, evidence_kind="real_model" if not selftest else "selftest_fake_server",
                by_class={c: {k: v for k, v in d.items() if k != "policy"} for c, d in S["by_class"].items()}, evidence=S["evidence"], fixture_defects=S["fixture_defects"], outcomes=S["outcomes"], payload_consistency=S["payload_consistency"],
                scorer=S["scorer"], memory_use_diagnostics=mem_diag,
                quality_gates=S["quality_gates"], skip_reasons=S["skip_reasons"], rejection_reason_codes=S["reason_codes"], reply_truncated=trunc, model_calls=len(called),
                first_call_ms=lat[0] if lat else None, warm_latency_ms={"median": pct(lat[1:], .5), "p95": pct(lat[1:], .95), "max": max(lat) if lat else None},
                generated_tokens_median=statistics.median([r["metrics"].get("generated_tokens") for r in called if isinstance(r["metrics"].get("generated_tokens"), (int, float))] or [0]),
                memory_models=dict(M.MODEL_STATS), misses=[{"id": r["id"], "class": r["class"], "outcome": r["outcome"], "reasons": r.get("reasons", []), "basis": r.get("success_basis"), "failure_type": r.get("failure_type")}
                                                            for r in rows if r.get("strict", True) and not r["success"]],
                circuit_breaker_state=str(getattr(gen.breaker, "state", "n/a")), dimensions=S["dimensions"], synthetic_benchmark_text=True,
                rule_skips=sum(1 for r in rows if r.get("decided_by") == "rules" and r.get("outcome") == "skip"), repair_attempts=sum(1 for r in rows if r.get("attempts", 0) > 1), repaired_ok=sum(1 for r in rows if r.get("repaired")),
                rows=[{k: r.get(k) for k in ("id", "class", "category", "mode", "outcome", "reasons", "skip_reason", "decided_by", "model_called", "attempts", "repaired", "offered_memory", "memory_offered_ids", "memory_cited",
                                             "citation_dropped", "accepted", "useful_valid", "success", "success_basis", "strict", "audit", "audit_kind", "latency_ms", "opportunity_code", "question", "model_question", "lead",
                                             "memory_stage", "memory_grounded", "failure_type", "fallback_class", "mode_trace", "payload_issues", "retrieval", "debug", "review_context", "evidence", "scoring_policy",
                                             "expected_followup", "probe_kind", "expected_probe")} for r in rows])
    info["_rows_full"] = rows
    return info, []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opportunities", action="store_true", help="per-eligible-opportunity evaluation of the fixed Stage 10F set (recommended)")
    ap.add_argument("--models", nargs="+", default=["llama3.2:3b"])
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--mlflow", action="store_true")
    ap.add_argument("--sbert", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--engine", default=None, choices=["stage10n", "objective"], help="follow-up engine for --opportunities (default: SMART_DEMO_FOLLOWUP_ENGINE, else the Stage 10N baseline)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.opportunities:
        return main_opportunities(a)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    out = Path(a.out or ROOT / "tmp" / f"stage10_real_{time.strftime('%Y%m%d_%H%M%S')}")
    out.mkdir(parents=True, exist_ok=True)
    results, all_review = [], []
    if a.selftest:
        from tests.helpers.fake_ollama import FakeOllama

        def reply(req):
            c = req["messages"][-1]["content"]
            import re
            mem = re.search(r"^(m\d+) \(turn", c, re.M)
            if not mem:
                return json.dumps({"decision": "skip", "question": "", "purpose": "deepen", "concept_id": "none", "answer_quote": "", "uses_given_facts_only": True, "already_in_answer": False})
            ans = re.search(r"=====BEGIN_UNTRUSTED_ANSWER_\w+=====\n(.*?)\n=====END", c, re.S).group(1)
            quote = " ".join(ans.split()[:5])
            return json.dumps({"decision": "ask", "question": f"Earlier you said you developed an oral cancer classification model, so how does {quote} apply in that work?", "purpose": "apply", "concept_id": "none",
                               "answer_quote": quote, "uses_given_facts_only": True, "already_in_answer": False, "memory_id": mem.group(1)})
        with FakeOllama(reply=reply, load_delay=0.2, first_delay=0.02, token_delay=0.002) as f:
            info, rows, review = one_model("fake-model:1b", f.url, a.runs, True, False, out)
            results.append(info); all_review += review
    else:
        for m in a.models:
            info, rows, review = one_model(m, a.host, a.runs, False, a.sbert, out)
            results.append(info); all_review += review
    from src.demo import behavioural as B, followup_llm as FL
    doc = {"timings_are_real": not a.selftest, "human_validated": False, "prompt_version": FL.PROMPT_VERSION, "rubric_versions": B.versions(), "results": results,
           "note": "No model is ranked. Acceptance means the fixed rules accepted the wording; it is not a relevance or quality judgement."}
    (out / "results.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    L = ["# Stage 10 real-stack run", "", "**SELFTEST: scripted fake server, NOT real measurements.**" if a.selftest else "Measured on this computer with your local Ollama.", "",
         "| model | calls | accepted by rules | cited a stored memory | model chose skip | fell back | median ms | p95 ms | cold load ms | rejection codes |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        L.append(f"| {r['model']} | {r.get('calls', '-')} | {r.get('accepted', '-')} | {r.get('accepted_citing_memory', '-')} | {r.get('model_chose_skip', '-')} | {r.get('fell_back', '-')} | "
                 f"{(r.get('latency_ms') or {}).get('median', '-')} | {(r.get('latency_ms') or {}).get('p95', '-')} | {(r.get('cold_load') or {}).get('client_ms', '-')} | {r.get('rejection_reason_codes', r.get('status'))} |")
    L += ["", "Acceptance by rules is not human validation. Rate `review_sheet.csv` blind (docs/STAGE10_MODEL_AND_POLICY.md section 8) before saying anything about quality.", ""]
    (out / "summary.md").write_text("\n".join(L), encoding="utf-8")
    import random
    random.Random(10).shuffle(all_review)
    with (out / "review_sheet.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["item_id", "context_previous_answer", "context_earlier_statement_cited", "interviewer_text", "natural_1to5", "relevant_to_context_1to5", "grounded_yes_no", "repeats_earlier_yes_no", "notes"])
        w.writeheader()
        for i, it in enumerate(all_review, 1):
            w.writerow({"item_id": f"M{i:03d}", **{k: it[k] for k in ("context_previous_answer", "context_earlier_statement_cited", "interviewer_text")}})
    (out / "key.json").write_text(json.dumps({f"M{i:03d}": {"model": it["model"], "cites_memory": it["cites_memory"]} for i, it in enumerate(all_review, 1)}, indent=1), encoding="utf-8")
    if a.mlflow and not a.selftest:
        try:
            from src.mlops import tracking
            if not tracking.available():
                print("[note] MLflow is not installed; skipping tracking")
            else:
                for r in results:
                    if r.get("status") != "ran":
                        continue
                    with tracking.live_run("smart-stage10-interview", f"{r['model']} stage10 real-stack", params={"followup.model": r["model"], "followup.prompt_version": FL.PROMPT_VERSION, "rubric.version": B.versions()["rubric"],
                                                                                                                     "bank.version": B.versions()["questions"], "memory.embedder": r["memory_embedder"], "real_sbert_scorer": r["real_sbert_scorer"],
                                                                                                                     "runs": a.runs, "contains_candidate_text": False}, tags={"smart.stage": "10", "smart.human_validated": "false"}) as run:
                        run.log_metrics({"calls": r["calls"], "accepted": r["accepted"], "accepted_citing_memory": r["accepted_citing_memory"], "fell_back": r["fell_back"], "model_chose_skip": r["model_chose_skip"],
                                         "latency_ms_median": (r["latency_ms"] or {}).get("median") or 0, "latency_ms_p95": (r["latency_ms"] or {}).get("p95") or 0})
                        for code, n in (r.get("rejection_reason_codes") or {}).items():
                            run.log_metrics({"reject_" + code.replace(":", "_"): n})
                print("[ok] logged to MLflow (counts, timings, versions only)")
        except Exception as e:
            print(f"[note] MLflow logging skipped: {type(e).__name__}: {str(e)[:100]}")
    print((out / "summary.md").read_text(encoding="utf-8"))
    print(f"wrote {out}")


def main_opportunities(a):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    out = Path(a.out or ROOT / "tmp" / f"stage10_opps_{time.strftime('%Y%m%d_%H%M%S')}")
    out.mkdir(parents=True, exist_ok=True)
    results, review = [], []
    if a.selftest:
        from tests.helpers.fake_ollama import FakeOllama
        from src.demo import opportunity_eval as OE

        def reply(req):
            c = req["messages"]
            return json.dumps(OE.scripted_reply(c[0]["content"], c[-1]["content"]))
        with FakeOllama(reply=reply, load_delay=0.2, first_delay=0.02, token_delay=0.002) as f:
            info, rv = opportunities("fake-model:1b", f.url, True, False, out, a.engine)
            results.append(info); review += rv
    else:
        for m in a.models:
            info, rv = opportunities(m, a.host, False, a.sbert, out, a.engine)
            results.append(info); review += rv
    from src.demo import followup_llm as FL
    doc = {"timings_are_real": not a.selftest, "human_validated": False, "prompt_version": results[0].get("prompt_version", FL.PROMPT_VERSION) if results else FL.PROMPT_VERSION, "engine": results[0].get("engine") if results else None, "results": results,
           "note": "Acceptance = the fixed rules accepted the wording and an independent audit found nothing wrong. It is not human-rated quality. No model is ranked."}
    from src.demo import opportunity_eval as OE2
    packs = {}
    for r in results:
        full = r.pop("_rows_full", None)
        if r.get("status") == "ran" and full:
            d = out / ("review_" + r["model"].replace(":", "_").replace("/", "_"))
            packs[r["model"]] = OE2.review_pack_v2(full, d, evidence=r["evidence_kind"])
            packs[r["model"]]["dir"] = d.name
    doc["review_packs"] = packs
    (out / "results.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    L = ["# Stage 10 per-opportunity real-stack run (10J-10L scoring)", "", "**SELFTEST: scripted fake server, NOT real measurements.**" if a.selftest else "Measured on this computer with your local Ollama.", "",
         "Scoring: one formula (`opportunity_eval.score_row`). Skip success = the model path produced no question. Memory-use success = a grounded, validated, code-led memory reference. B07 is a fixture defect, scored on safety only.", "",
         "| model | ollama | eligible | useful+valid | rate | technical expected | behavioural probes (scripted) | grounded memory use | memory offered | fabricated memory | strict skip | truncated | fell back | cold ms | first call ms | warm median ms | warm p95 ms |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        if r.get("status") != "ran":
            L.append(f"| {r['model']} | - | unavailable: {r.get('error')} |"); continue
        bc, E = r["by_class"], r["eligible"]
        L.append(f"| {r['model']} | {r.get('ollama_version')} | {r['eligible_opportunities']} | {r['useful_valid']} | {r['useful_valid_rate']} | {E['technical_expected'][0]}/{E['technical_expected'][1]} | {E['behavioural_scripted_probes'][0]}/{E['behavioural_scripted_probes'][1]} | "
                 f"{E['memory_use_grounded'][0]}/{E['memory_use_grounded'][1]} | {bc['memory_use']['offered_memory']}/{bc['memory_use']['n']} | {r['quality_gates']['fabricated_memory_references']} | "
                 f"{bc['skip']['success']}/{bc['skip']['n_strict']} | {r['reply_truncated']} | {sum(d['fell_back'] for d in bc.values())} | {r.get('cold_load_ms')} | {r['first_call_ms']} | {r['warm_latency_ms']['median']} | {r['warm_latency_ms']['p95']} |")
    for r in results:
        if r.get("status") != "ran":
            continue
        d = r["dimensions"]
        L += ["", f"### {r['model']}: nine dimensions, reported separately", "", f"- follow-up generation on eligible (expected): {d['follow_up_generation_on_eligible']}", f"- correct skipping (strict): {d['correct_skipping']}",
              f"- evidence-supported memory: {d['evidence_supported_memory']}", f"- technical relevance: {d['technical_relevance']}", f"- behavioural relevance: {d['behavioural_relevance']}",
              f"- wording proxies (form only, not rated naturalness): {d['wording_proxies']}", f"- repetition: {d['repetition']}", f"- fabricated claims: {d['fabricated_claims']}", f"- latency and fallbacks: {d['latency_and_fallbacks']}",
              f"- rule skips (model not called): {r['rule_skips']} · repair attempts: {r['repair_attempts']} · repaired ok: {r['repaired_ok']}",
              f"- outcomes (transparent counts): {r['outcomes']}", f"- payload consistency: {r['payload_consistency']}", f"- fixture defects: {[x['id'] for x in r['fixture_defects']]} (scored on safety only; see results.json)",
              f"- memory-use failure types: {r['by_class']['memory_use'].get('failure_types')}",
              "- evidence kinds: " + "; ".join(f"{e['metric']} = {e['kind']}" for e in r["evidence"])]
        if r["eligible"]["rate"] is not None and r["eligible"]["rate"] < 0.8:
            L.append(f"- **TARGET NOT MET:** {r['eligible']['success']}/{r['eligible']['n']} = {r['eligible']['rate']:.1%} < 80%. This is reported as measured.")
    L += ["", "Per class, rejection codes, memory-use diagnostics and per-case rows (with the model's rejected replies on this synthetic set) are in results.json. The blind review packs are in `review_*/` and are UNRATED until a person fills them.", ""]
    (out / "summary.md").write_text("\n".join(L), encoding="utf-8")
    if a.mlflow and not a.selftest:
        try:
            from src.mlops import tracking
            if tracking.available():
                for r in results:
                    if r.get("status") != "ran":
                        continue
                    with tracking.live_run("smart-stage10-interview", f"{r['model']} stage10f opportunities", params={"followup.model": r["model"], "followup.prompt_version": FL.PROMPT_VERSION, "ollama.version": r.get("ollama_version") or "n/a", "contains_candidate_text": False},
                                           tags={"smart.stage": "10L", "smart.human_validated": "false"}) as run:
                        run.log_metrics({"eligible": r["eligible_opportunities"], "useful_valid": r["useful_valid"], "useful_valid_rate": r["useful_valid_rate"] or 0, "fabricated_memory": r["quality_gates"]["fabricated_memory_references"],
                                         "memory_grounded": r["eligible"]["memory_use_grounded"][0], "strict_skip_success": r["by_class"]["skip"]["success"], "payload_inconsistent": r["payload_consistency"]["rows_with_inconsistent_payload"], "fallbacks": sum(d["fell_back"] for d in r["by_class"].values()), "repair_attempts": r["repair_attempts"], "repaired_ok": r["repaired_ok"], "reply_truncated": r["reply_truncated"], "warm_median_ms": r["warm_latency_ms"]["median"] or 0, "first_call_ms": r["first_call_ms"] or 0, "cold_load_ms": r.get("cold_load_ms") or 0})
                print("[ok] logged to MLflow (counts, timings, versions only)")
        except Exception as e:
            print(f"[note] MLflow logging skipped: {type(e).__name__}: {str(e)[:100]}")
    print((out / "summary.md").read_text(encoding="utf-8"))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
