"""Stage 3C-3: normalisation variant, diagnostics, recovery, blind exports, human comparison, views, offline replay."""
import csv, json, re
from pathlib import Path

import pytest

from src.evaluation.modular import ScopeStore
from src.evaluation.modular.claims import content_stems
from src.evaluation.modular.lexnorm import content_stems_v31, discriminators, labels_may_overlap, stem_token
from src.evaluation.modular.review import blind as B, compare as C, diagnostics as DG, recovery as R, views as V
from src.evaluation.modular.review.terms import describe_confidence, source_label
from src.evaluation.modular.variant_v31 import use_v31
from src.evaluation.modular import consistency as C0, verification as V0

ROOT = Path(__file__).resolve().parents[2]
S = ROOT / "data" / "evaluation" / "stage3c2"
PILOT = ROOT / "data" / "evaluation" / "stage3c2_results" / "20261015T120208Z" / "results.json"


# ---------------------------------------------------------------- normalisation
@pytest.mark.parametrize("a,b", [("regularization", "regularisation"), ("convolution", "convolutional"), ("normalise", "normalization"), ("behaviour", "behavior"),
                                 ("modelling", "modeling"), ("dependency", "dependencies"), ("optimizer", "optimisation"), ("tokenizer", "tokenisation")])
def test_variants_map_together(a, b):
    assert stem_token(a) == stem_token(b)


@pytest.mark.parametrize("a,b", [("normal", "normalization"), ("precise", "precision"), ("recall", "precision"), ("bias", "variance"), ("rise", "rising")])
def test_unrelated_terms_stay_apart(a, b):
    assert stem_token(a) != stem_token(b)


def test_discriminators_separate_sibling_concepts():
    assert not labels_may_overlap("Type I error", "Type II error")
    assert not labels_may_overlap("L1 regularization", "L2 regularization")
    assert labels_may_overlap("Type I error", "type I errors")
    assert labels_may_overlap("non-linear activation function", "non-linear activation")
    assert discriminators("Type II error") == {"ii"}
    assert len(content_stems("Type I error") & content_stems("Type II error")) / len(content_stems("Type I error") | content_stems("Type II error")) >= 0.5   # the 3c1.0 defect


def test_variant_is_scoped_and_restored():
    old = (C0.check, V0.content_stems)
    with use_v31():
        assert C0.check is not old[0] and V0.content_stems is content_stems_v31
    assert (C0.check, V0.content_stems) == old


def test_normaliser_cannot_create_credit():
    # the guard may only REFUSE "not stated"; _lexically_present returns a bool and verification never maps it to states_correctly
    src = (ROOT / "src/evaluation/modular/verification.py").read_text(encoding="utf-8")
    assert "omission_contradicted_by_lexical_check" in src and src.count("_lexically_present(") == 2


# ---------------------------------------------------------------- diagnostics / terms
def _res(status="abstained", **kw):
    base = {"status": status, "score": None, "score_range": None, "confidence": "low", "penalty_mode": "full", "flags": [], "uncertainty_flags": [], "abstain_reasons": ["completeness undetermined"],
            "dimensions": [{"name": "relevance", "level": 4, "inputs": {"on_topic_verifier": "on_topic", "lexical_overlap": 0.4}}], "outcomes": [], "verdicts": [], "claims": [], "provenance": {"verifier": "x", "is_mock": False}}
    base.update(kw); return base


def test_taxonomy_separates_provider_off_topic_model_and_gate():
    assert DG.abstain_taxonomy(_res("provider_error"))["primary"] == "provider_failure"
    off = _res(dimensions=[{"name": "relevance", "level": 0, "inputs": {"on_topic_verifier": "off_topic", "lexical_overlap": 0.0}}])
    assert DG.abstain_taxonomy(off)["primary"] == "off_topic_confirmed"
    oc = [{"requirement_id": "E1", "label": "a", "tier": "essential", "kind": "concept", "status": "undetermined"}]
    m = _res(outcomes=oc, verdicts=[{"requirement_id": "E1", "member": "a", "state": "unverified", "original_state": "unverified"}])
    g = _res(outcomes=oc, verdicts=[{"requirement_id": "E1", "member": "a", "state": "unverified", "original_state": "states_incorrectly", "downgrade_reason": "no_valid_evidence"}])
    assert DG.abstain_taxonomy(m)["primary"] == "model_uncertain" and DG.abstain_taxonomy(g)["primary"] == "evidence_gate"
    assert DG.abstain_taxonomy(_res("advisory_only"))["primary"] == "not_scored_by_design"


def test_confidence_wording_never_claims_accuracy():
    assert "not human-verified" in describe_confidence("high")
    assert "human" not in describe_confidence("high", True).replace("not human-verified", "")
    s = source_label({"status": "advisory_only", "provenance": {"is_mock": True, "verifier": "m"}})
    assert s["tags"] == ["ADVISORY ONLY", "MOCK VERIFIER"] and s["human"] == "NOT human-validated"


def test_disagreement_classifies_cause():
    def r(state, orig, why=None):
        return {"status": "scored", "score": 1, "outcomes": [{"requirement_id": "E1", "tier": "essential"}], "verdicts": [{"requirement_id": "E1", "member": "m", "state": state, "original_state": orig, "downgrade_reason": why}]}
    rep = DG.disagreement_report({"s": {0: r("states_correctly", "states_correctly"), 1: r("unverified", "states_correctly", "no_valid_evidence")}})
    assert rep["mismatches"][0]["cause"] == "gate_induced" and rep["agreement_before_gate"] == 1.0 and rep["agreement_after_gate"] == 0.0


# ---------------------------------------------------------------- recovery
def test_truncated_results_are_salvaged_and_merge_refuses_drift(tmp_path):
    doc = {"meta": {"freeze_manifest_sha256": "a", "frozen_config": {"x": 1}}, "modular": [{"sample_id": f"s{i}", "repeat": 0, "result": {}} for i in range(5)], "legacy": []}
    p = tmp_path / "r.json"; t = json.dumps(doc, indent=1); p.write_text(t[: len(t) - 40], encoding="utf-8")
    d, rep = R.load_results_tolerant(p)
    assert rep["repaired"] and rep["dropped_incomplete_record"] and len(d["modular"]) == 4
    plan = R.plan_resume(d, [f"s{i}" for i in range(5)], modular_repeats=1, legacy_repeats=0)
    assert plan["answers_to_rerun"] == ["s4"] and "-Ids" in plan["rerun_command_hint"]
    other = {"meta": {"freeze_manifest_sha256": "b", "frozen_config": {"x": 1}}, "modular": [], "legacy": []}
    with pytest.raises(ValueError):
        R.merge_runs([d, other], ["s0"])
    m = R.merge_runs([d, {"meta": d["meta"], "modular": [{"sample_id": "s4", "repeat": 0, "result": {}}, {"sample_id": "s0", "repeat": 0, "result": {"dup": 1}}], "legacy": []}], [f"s{i}" for i in range(5)], 1, 0)
    assert len(m["modular"]) == 5 and m["modular"][0]["result"] == {} and m["meta"]["assembled_run"] and not m["meta"]["partial_run"]


def test_atomic_write_leaves_no_temp_files(tmp_path):
    R.atomic_write_text(tmp_path / "a.txt", "x"); R.atomic_write_text(tmp_path / "a.txt", "y")
    assert (tmp_path / "a.txt").read_text() == "y" and [p.name for p in tmp_path.iterdir()] == ["a.txt"]


# ---------------------------------------------------------------- blind exports
def test_header_matches_frozen_sheet_and_frozen_rows_load():
    with open(S / "review" / "blind_review_sheet.csv", encoding="utf-8-sig", newline="") as f:
        assert next(csv.reader(f)) == B.HEADER
    assert len(B.rows_from_csv(S / "review" / "blind_review_sheet.csv")) == 20


def test_blind_files_contain_nothing_from_the_model_or_the_ai_labels(tmp_path):
    store = ScopeStore.load()
    items = B.load_bench_v2(ROOT)
    assert len(items) == 120
    built = B.make_rows(items, store, seed=1, prefix="b")
    paths = B.write_blind_set(built["rows"], tmp_path, title="t", set_id="x", key=built["key"], meta=built["meta"])
    ids = list(built["key"].values())
    for k in ("csv", "md", "html"):
        assert B.blindness_violations(Path(paths[k]).read_text(encoding="utf-8"), ids) == [], k
    assert sum(m["scope_eligible"] for m in built["meta"].values()) == 40
    again = B.make_rows(items, store, seed=1, prefix="b")
    assert again["key"] == built["key"]                                  # deterministic
    assert B.blindness_violations("see b2-004 and modular score", ["b2-004"])


def test_frozen_sample_html_is_blind():
    rows = B.rows_from_csv(S / "review" / "blind_review_sheet.csv")
    key = json.loads((S / "review" / "review_key.json").read_text(encoding="utf-8"))
    assert B.blindness_violations(B.to_html(rows, "t", "s"), list(key.values())) == []


# ---------------------------------------------------------------- human comparison
def _doc():
    def outcome(rid, state, status):
        return {"requirement_id": rid, "tier": "essential", "kind": "concept", "label": rid, "status": status, "detail": {"state": state}}
    def mod(sid, score, outs, status="scored"):
        return {"sample_id": sid, "repeat": 0, "result": {"status": status, "score": score, "score_range": None, "outcomes": outs}}
    return {"modular": [mod("a", 100, [outcome("E1", "states_correctly", "satisfied"), outcome("E2", "states_correctly", "satisfied")]),
                        mod("b", 30, [outcome("E1", "states_incorrectly", "incorrect"), outcome("E2", "not_stated", "missing")]),
                        mod("c", None, [outcome("E1", "unverified", "undetermined")], "abstained")],
            "legacy": [{"sample_id": s, "result": {"provisional_score": v, "missing_concepts": m, "factual_errors": e}} for s, v, m, e in
                       [("a", 60, ["E2"], []), ("b", 20, [], []), ("c", 50, [], [])]]}


def test_human_comparison_counts(tmp_path):
    sheet = tmp_path / "h.csv"
    with open(sheet, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(B.HEADER)
        w.writerow(["r1", "q", "a", "", "partly_correct", "partial", "E1: stated_correctly\nE2: stated_incorrectly", "70", "", "me"])      # a: modular credited E2 wrongly
        w.writerow(["r2", "q", "a", "", "partly_correct", "partial", "E1: stated_correctly\nE2: stated_correctly", "80", "", "me"])         # b: false error on E1, E2 missing contradicted
        w.writerow(["r3", "q", "a", "", "correct", "complete", "E1: stated_correctly", "90", "", "me"])                                    # c: abstained
        w.writerow(["r4", "q", "a", "", "", "", "", "", "", "me"])                                                                         # blank row ignored
    imp = C.import_human_sheets([sheet])
    assert imp["problems"] == [] and set(imp["reviews"]) == {"r1", "r2", "r3"}
    cons, inter = C.consensus(imp["reviews"])
    res = C.compare(_doc(), {"r1": "a", "r2": "b", "r3": "c"}, cons, inter, requirement_labels={"a": {"E1": "x", "E2": "E2"}, "b": {}, "c": {}},
                    criteria=json.loads((S / "acceptance_criteria.json").read_text()))
    rq = res["requirement_level_modular"]
    assert rq["false_credit"] == 1 and rq["credits"] == 2 and rq["false_error"] == 1 and rq["errors_called"] == 1
    ci = res["criteria_inputs"]
    assert ci["essential_missing_contradicted"] == 1 and ci["false_credit_rate"] == pytest.approx(1 / 2, abs=1e-3)
    assert res["score_level"]["modular_repeat0"]["abstained"] == 1 and res["score_level"]["modular_repeat0"]["inflated_ge15"] == 1
    fh = res["frozen_human_criteria"]["criteria"]
    assert fh["false_credit_rate_max"]["result"] == "FAIL" and fh["essential_missing_penalties_contradicted_by_human_max"]["result"] == "FAIL"
    assert "HUMAN-VALIDATED" in res["label"]


def test_importer_reports_bad_cells_instead_of_guessing(tmp_path):
    sheet = tmp_path / "h.csv"
    with open(sheet, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(B.HEADER); w.writerow(["r1", "q", "a", "", "maybe", "", "E1: perhaps", "150", "", "me"])
    imp = C.import_human_sheets([sheet])
    assert len(imp["problems"]) == 3 and imp["reviews"] == {}


# ---------------------------------------------------------------- views + replay on the real full run (skipped if the results are absent)
needs_run = pytest.mark.skipif(not PILOT.exists(), reason="full-run results not present")


def _fixtures():
    from src.retrieval.corpus import load_corpus
    sample = {r["sample_id"]: r for r in map(json.loads, filter(None, (S / "sample.jsonl").read_text(encoding="utf-8").splitlines()))}
    return json.loads(PILOT.read_text(encoding="utf-8")), sample, {r["question_id"]: r for r in load_corpus()["records"]}


@needs_run
def test_views_label_real_model_results_and_never_leak_ai_labels_into_demo():
    doc, sample, _ = _fixtures()
    vs = V.build_views(doc, sample, ScopeStore.load(), None)
    assert len(vs) == 20 and all(m["source"]["tags"] == ["REAL MODEL"] for v in vs for m in v["modular"])
    html_ = V.render_html(vs[:2], "t", unblinded_ai=False)
    assert "REAL MODEL" in html_ and "provisional expectation" not in html_
    assert "REAL MODEL" in V.render_cli(vs[0]) and "NOT human-validated" in V.render_cli(vs[0])


def test_mock_demo_on_an_advisory_question_carries_both_labels():
    from src.retrieval.corpus import load_corpus
    recs = {r["question_id"]: r for r in load_corpus()["records"]}
    store = ScopeStore.load()
    adv = next(q for q in store.ids() if q not in set(store.eligible_ids()))
    v = V.mock_view(adv, recs[adv]["question"], "Some answer text about the topic.", store, recs[adv])
    assert v["modular"][0]["source"]["tags"] == ["ADVISORY ONLY", "MOCK VERIFIER"] and v["modular"][0]["score"] is None
    assert "ADVISORY ONLY + MOCK VERIFIER" in V.render_cli(v)


@needs_run
def test_replay_of_recorded_output_reproduces_every_frozen_result_and_variant_changes_only_documented_rows():
    from src.evaluation.modular.review.replay import replay_run
    doc, sample, recs = _fixtures()
    store = ScopeStore.load()
    assert [r for r in replay_run(doc, sample, recs, store) if r["diff"]] == []
    changed = {(r["sample_id"], r["repeat"]) for r in replay_run(doc, sample, recs, store, variant="3c1.1") if r["diff"]}
    assert changed == {("b2-012", 0), ("b2-012", 1), ("b2-045", 1), ("b2-109", 0), ("b2-109", 1)}
