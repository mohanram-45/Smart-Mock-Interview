"""Stage 3C-3: human-review workflow and read-only demonstration for the modular evaluator.  NOTHING here calls a model, scores live traffic, or touches Flask.

  python scripts/stage3c3_review.py blind   --set sample20|bench_v2 [--out DIR] [--seed N] [--force]
  python scripts/stage3c3_review.py report  --results RUN/results.json [--out DIR]
  python scripts/stage3c3_review.py compare --results RUN/results.json --human sheet1.csv [sheet2.csv ...] [--key review_key.json] [--out DIR]
  python scripts/stage3c3_review.py demo    --results RUN/results.json --id b2-006 [--repeat 0] [--html FILE]
  python scripts/stage3c3_review.py demo    --mock --question smi-0449 --answer "O(log n) because it halves the range" [--html FILE]
  python scripts/stage3c3_review.py diagnose --results RUN/results.json
  python scripts/stage3c3_review.py recover --results RUN/results.json [--merge OTHER/results.json ...] [--out FILE]
  python scripts/stage3c3_review.py replay  --results RUN/results.json [--variant 3c1.1]      (offline replay of RECORDED model output; a diagnostic, not a new result)
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
D = ROOT / "data" / "evaluation"


def _jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def _store():
    from src.evaluation.modular import ScopeStore
    return ScopeStore.load()


def _sample(name="stage3c2"):
    return {r["sample_id"]: r for r in _jl(D / name / "sample.jsonl")}


def _results(path):
    from src.evaluation.modular.review.recovery import load_results_tolerant
    doc, rep = load_results_tolerant(Path(path))
    if rep["repaired"]:
        print(f"NOTE: results file was truncated; recovered {rep['modular']} modular + {rep['legacy']} legacy complete records (incomplete record dropped: {rep['dropped_incomplete_record']}).")
    return doc


def cmd_blind(a):
    from src.evaluation.modular.review import blind as B
    store = _store()
    if a.set == "sample20":
        csvp = D / "stage3c2" / "review" / "blind_review_sheet.csv"
        keyp = D / "stage3c2" / "review" / "review_key.json"
        rows = B.rows_from_csv(csvp)
        key = json.loads(keyp.read_text(encoding="utf-8"))
        out = Path(a.out or D / "stage3c3" / "review_sample20")
        if (out / "blind_review.html").exists() and not a.force:
            sys.exit(f"{out}/blind_review.html exists; use --force to rebuild it")
        paths = B.write_blind_set(rows, out, title="Blind review: 20 evaluated answers", set_id="stage3c2_sample20", write_csv=False)   # the frozen CSV/MD/key are NOT regenerated
        print("built from the FROZEN blind sheet (unchanged):", paths["html"])
        ids = list(key.values())
    else:
        items = B.load_bench_v2(ROOT)
        built = B.make_rows(items, store, seed=a.seed, prefix="b")
        out = Path(a.out or D / "stage3c3" / "review_bench_v2")
        if (out / "review_key.json").exists() and not a.force:
            sys.exit(f"{out}/review_key.json exists; refusing to overwrite a key (use --force)")
        paths = B.write_blind_set(built["rows"], out, title="Blind review: bench_v2 (120 answers)", set_id="bench_v2", key=built["key"], meta=built["meta"])
        rows, ids = built["rows"], list(built["key"].values())
        print(f"{len(rows)} answers; scope-eligible (scorable by the modular evaluator): {sum(m['scope_eligible'] for m in built['meta'].values())}")
        print("KEEP PRIVATE (do not give to the reviewer):", paths["key"], paths["meta"])
    for k in ("csv", "md", "html"):
        if k in paths:
            bad = B.blindness_violations(Path(paths[k]).read_text(encoding="utf-8"), ids)
            print(f"  {k}: {paths[k]}  blindness check: {'OK' if not bad else 'VIOLATIONS ' + str(bad[:5])}")
            if bad: return 2
    return 0


def cmd_report(a):
    from src.evaluation.modular.review import views as V
    from src.evaluation.modular.review.recovery import atomic_write_text
    doc = _results(a.results)
    run = Path(a.results).parent
    exp = {e["sample_id"]: e for e in _jl(D / "stage3c2" / "provisional_ai_expectations.jsonl")}
    vs = V.build_views(doc, _sample(), _store(), exp)
    out = Path(a.out or run)
    atomic_write_text(out / "side_by_side.md", V.render_markdown(vs, "Stage 3C-2 side-by-side review report (UNBLINDED)"))
    atomic_write_text(out / "side_by_side.html", V.render_html(vs, "Stage 3C-2 side-by-side review report (UNBLINDED)"))
    print("wrote", out / "side_by_side.md", "and", out / "side_by_side.html", f"({len(vs)} answers)")
    return 0


def cmd_compare(a):
    from src.evaluation.modular.review import compare as C
    from src.evaluation.modular.requirements import build_requirements
    from src.evaluation.modular.review.recovery import atomic_write_text
    doc = _results(a.results)
    key = json.loads(Path(a.key or D / "stage3c2" / "review" / "review_key.json").read_text(encoding="utf-8"))
    imp = C.import_human_sheets(a.human)
    print(f"read {imp['rows_read']} rows; {imp['rows_incomplete']} without a score; {len(imp['problems'])} problems")
    for p in imp["problems"][:20]: print("  PROBLEM:", p)
    cons, inter = C.consensus(imp["reviews"])
    if not cons:
        sys.exit("no completed review rows found: nothing to compare")
    sample, store = _sample(), _store()
    labels = {}
    for sid, s in sample.items():
        try: labels[sid] = {r.id: r.label for r in build_requirements(store.get(s["question_id"]), s["question"]).requirements}
        except Exception: labels[sid] = {}
    kinds = {sid: e["kind"] for sid, e in ((e["sample_id"], e) for e in _jl(D / "stage3c2" / "provisional_ai_expectations.jsonl"))}
    crit = json.loads((D / "stage3c2" / "acceptance_criteria.json").read_text(encoding="utf-8"))
    run = Path(a.results).parent
    mech = None
    a2 = run / "analysis_v2.json"
    if a2.exists():
        mech = {k: v for k, v in (json.loads(a2.read_text(encoding="utf-8")).get("criteria") or {}).items()}
    res = C.compare(doc, key, cons, inter, kinds=kinds, requirement_labels=labels, criteria=crit, mechanical=mech)
    res["import_problems"] = imp["problems"]
    out = Path(a.out or run)
    atomic_write_text(out / "human_comparison.json", json.dumps(res, indent=1, ensure_ascii=False, default=str))
    atomic_write_text(out / "human_comparison.md", C.to_markdown(res))
    print("wrote", out / "human_comparison.json", "and .md;", res["label"])
    return 0


def cmd_demo(a):
    from src.evaluation.modular.review import views as V
    if a.mock:
        from src.retrieval.corpus import load_corpus
        recs = {r["question_id"]: r for r in load_corpus()["records"]}
        q = recs[a.question]
        ans = Path(a.answer_file).read_text(encoding="utf-8") if a.answer_file else a.answer
        v = V.mock_view(a.question, q["question"], ans, _store(), q)
    else:
        doc = _results(a.results)
        vs = V.build_views(doc, _sample(), _store(), None, [a.id])
        if not vs: sys.exit(f"{a.id} not found in results")
        v = vs[0]
    print(V.render_cli(v, a.repeat))
    if a.html:
        from src.evaluation.modular.review.recovery import atomic_write_text
        atomic_write_text(Path(a.html), V.render_html([v], "Modular evaluator demonstration (read-only)", unblinded_ai=False)); print("\nwrote", a.html)
    return 0


def cmd_diagnose(a):
    from src.evaluation.modular.review.diagnostics import abstain_taxonomy, disagreement_report
    from collections import Counter, defaultdict
    doc = _results(a.results)
    tax = Counter(abstain_taxonomy(m["result"])["primary"] for m in doc["modular"])
    print("modular rows by outcome class:", dict(tax))
    by = defaultdict(dict)
    for m in doc["modular"]: by[m["sample_id"]][m["repeat"]] = m["result"]
    rep = disagreement_report(by)
    print(f"repeat agreement after gate {rep['agreement_after_gate']}, before gate {rep['agreement_before_gate']}; mismatches by cause {rep['by_cause']}")
    for r in rep["mismatches"]: print("  ", r["sample_id"], r["requirement"], r["tier"], r["member"], "model", r["model"], "final", r["final"], r["cause"])
    return 0


def cmd_recover(a):
    from src.evaluation.modular.review import recovery as R
    doc, rep = R.load_results_tolerant(Path(a.results))
    print("load report:", rep)
    docs = [doc] + [R.load_results_tolerant(Path(p))[0] for p in (a.merge or [])]
    ids = [s["sample_id"] for s in _jl(D / "stage3c2" / "sample.jsonl")]
    merged = R.merge_runs(docs, ids) if len(docs) > 1 else doc
    plan = R.plan_resume(merged, ids)
    print("modular done:", plan["modular_done"], "of", 2 * len(ids), "| legacy done:", plan["legacy_done"], "of", len(ids), "| complete:", plan["complete"])
    if plan["rerun_command_hint"]: print("to finish, run the FROZEN runner for the missing answers:\n  " + plan["rerun_command_hint"])
    if a.out:
        R.atomic_write_text(Path(a.out), json.dumps(merged, indent=1, ensure_ascii=False, default=str)); print("wrote", a.out)
    return 0


def cmd_replay(a):
    from src.evaluation.modular.review.replay import replay_run
    from src.retrieval.corpus import load_corpus
    recs = {r["question_id"]: r for r in load_corpus()["records"]}
    rows = replay_run(_results(a.results), _sample(), recs, _store(), variant=a.variant)
    diffs = [r for r in rows if r["diff"]]
    print(f"replayed {len(rows)} recorded model outputs offline with engine {a.variant or '3c1.0'}: {len(diffs)} differ from the recorded results")
    for r in diffs: print("  ", r["sample_id"], r["repeat"], json.dumps(r["diff"], default=str)[:300])
    if a.variant and diffs:
        print("\nDIAGNOSTIC ONLY: these are NOT new results and cannot be used to re-evaluate the frozen acceptance criteria.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("blind"); s.add_argument("--set", choices=["sample20", "bench_v2"], required=True); s.add_argument("--out"); s.add_argument("--seed", type=int, default=20261015); s.add_argument("--force", action="store_true"); s.set_defaults(f=cmd_blind)
    s = sp.add_parser("report"); s.add_argument("--results", required=True); s.add_argument("--out"); s.set_defaults(f=cmd_report)
    s = sp.add_parser("compare"); s.add_argument("--results", required=True); s.add_argument("--human", nargs="+", required=True); s.add_argument("--key"); s.add_argument("--out"); s.set_defaults(f=cmd_compare)
    s = sp.add_parser("demo"); s.add_argument("--results"); s.add_argument("--id"); s.add_argument("--repeat", type=int, default=0); s.add_argument("--html")
    s.add_argument("--mock", action="store_true"); s.add_argument("--question"); s.add_argument("--answer", default=""); s.add_argument("--answer-file"); s.set_defaults(f=cmd_demo)
    s = sp.add_parser("diagnose"); s.add_argument("--results", required=True); s.set_defaults(f=cmd_diagnose)
    s = sp.add_parser("recover"); s.add_argument("--results", required=True); s.add_argument("--merge", nargs="*"); s.add_argument("--out"); s.set_defaults(f=cmd_recover)
    s = sp.add_parser("replay"); s.add_argument("--results", required=True); s.add_argument("--variant", choices=["3c1.0", "3c1.1", "3c4.0"]); s.set_defaults(f=cmd_replay)
    a = ap.parse_args(argv)
    if a.cmd == "demo" and not a.mock and not (a.results and a.id): ap.error("demo needs --results and --id, or --mock --question --answer")
    if a.cmd == "demo" and a.mock and not (a.question and (a.answer or a.answer_file)): ap.error("--mock needs --question and --answer (or --answer-file)")
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
