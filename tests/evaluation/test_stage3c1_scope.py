"""Phase 1: scope integration - read-only loading, eligibility gates, requirements, uncertainty."""
import copy, dataclasses, hashlib, json
from pathlib import Path

import pytest

from src.evaluation.modular.requirements import OTHER_VALID, Tier, build_requirements
from src.evaluation.modular.scope import (DEFAULT_SIDECAR, ScopeIntegrityError, ScopeRecord, ScopeStore, ScopeUnavailable)
from tests.evaluation.mod_helpers import store

ELIGIBLE = {"smi-0064", "smi-0118", "smi-0119", "smi-0134", "smi-0153", "smi-0198", "smi-0314", "smi-0345", "smi-0427", "smi-0441", "smi-0449",
            "smi-0451", "smi-0453", "smi-0463", "smi-h0016", "smi-l0002"}


def test_loads_all_666_and_exactly_the_16_eligible_records():
    s = store()
    assert len(s) == 666
    assert set(s.eligible_ids()) == ELIGIBLE and len(s.eligible_ids()) == 16


def test_loader_is_read_only_and_does_not_touch_the_file():
    before = hashlib.sha256(DEFAULT_SIDECAR.read_bytes()).hexdigest()
    s = ScopeStore.load()
    with pytest.raises(TypeError):
        s._records["x"] = None                    # mappingproxy
    r = s.get("smi-0118")
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.human_review_required = True
    assert hashlib.sha256(DEFAULT_SIDECAR.read_bytes()).hexdigest() == before


def test_checksum_mismatch_and_missing_manifest_are_rejected(tmp_path):
    side = tmp_path / "scope.jsonl"
    side.write_bytes(DEFAULT_SIDECAR.read_bytes() + b"\n")
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"sidecar_sha256": hashlib.sha256(DEFAULT_SIDECAR.read_bytes()).hexdigest()}))
    with pytest.raises(ScopeIntegrityError):
        ScopeStore.load(side, man)
    with pytest.raises(ScopeIntegrityError):
        ScopeStore.load(side, tmp_path / "missing.json")


def _tampered(tmp_path, mutate):
    rows = [json.loads(x) for x in DEFAULT_SIDECAR.read_text(encoding="utf-8").splitlines()]
    for r in rows:
        mutate(r)
    body = "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n"
    side = tmp_path / "s.jsonl"
    side.write_bytes(body.encode("utf-8"))        # bytes, not write_text: on Windows write_text turns "\n" into "\r\n", so the file no longer matches the sha256 below
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"sidecar_sha256": hashlib.sha256(body.encode()).hexdigest()}))
    return ScopeStore.load(side, man)


def test_heuristic_only_flag_true_in_sidecar_still_cannot_be_eligible(tmp_path):
    """Even a (re-checksummed) sidecar that claims eligibility for heuristic rows must not unlock penalties."""
    def mut(r):
        r["completeness_penalty_eligible"] = True
        r["human_review_required"] = False
    s = _tampered(tmp_path, mut)
    assert set(s.eligible_ids()) <= {q for q in s.ids() if s.get(q).verification_status == "ai_reviewed_pilot"}
    for r in s.records():
        if r.tier_source == "heuristic_v2":
            assert not r.penalty_eligible and "not_ai_reviewed" in r.gate_failures and "tier_source_not_manual" in r.gate_failures


def test_human_review_flag_blocks_eligibility(tmp_path):
    s = _tampered(tmp_path, lambda r: r.update(human_review_required=True))
    assert s.eligible_ids() == ()


def test_unknown_or_human_status_is_rejected(tmp_path):
    with pytest.raises(ScopeIntegrityError):
        _tampered(tmp_path, lambda r: r.update(verification_status="human_verified"))


def test_no_record_is_human_verified_and_status_is_ai_only():
    for r in store().records():
        assert r.human_verified is False and r.verification_status in {"ai_heuristic_draft", "ai_reviewed_pilot"}


def test_650_remaining_records_are_advisory_never_full():
    s = store()
    adv = [q for q in s.ids() if q not in ELIGIBLE]
    assert len(adv) == 650
    for q in adv:
        assert build_requirements(s.get(q), "q").penalty_mode == "advisory"
    for q in ELIGIBLE:
        assert build_requirements(s.get(q), "q").penalty_mode == "full"


def test_unknown_question_id():
    with pytest.raises(ScopeUnavailable):
        store().get("smi-9999")


def test_requirements_tiers_groups_and_background(by_id):
    s = store()
    rs = build_requirements(s.get("smi-0119"), by_id["smi-0119"]["question"])
    assert [r.id for r in rs.essentials()] == ["E1", "G1"] and rs.get("G1").is_group and rs.get("G1").min_required == 2
    assert all(r.tier is Tier.SUPPORTING for r in rs.supporting())
    # label concepts and background concepts never become requirements
    rec = s.get("smi-0441")
    rs2 = build_requirements(rec, by_id["smi-0441"]["question"])
    labels = {r.label for r in rs2.requirements}
    assert not set(rec.label_concepts) & labels
    heur = next(r for r in s.records() if r.tier_source == "heuristic_v2" and r.background_concepts)
    rs3 = build_requirements(heur, "q")
    assert set(rs3.background) == set(heur.background_concepts) and not set(rs3.background) & {r.label for r in rs3.requirements}


def test_bubble_sort_complexity_is_essential_and_dense_rank_is_supporting(by_id):
    s = store()
    rs = build_requirements(s.get("smi-0453"), by_id["smi-0453"]["question"])
    assert "O(n²)" in {r.label for r in rs.essentials()}
    rs = build_requirements(s.get("smi-0431"), by_id["smi-0431"]["question"])
    assert "DENSE_RANK" in {r.label for r in rs.supporting()} and rs.penalty_mode == "advisory"


def test_ambiguity_produces_uncertainty_flags(by_id):
    s = store()
    rs = build_requirements(s.get("smi-0431"), "q")
    assert "scope_ambiguity:reference_broader_than_question" in rs.scope_flags and "scope_requires_human_review" in rs.scope_flags
    assert "scope_ai_reviewed_not_human_verified" in rs.scope_flags and rs.human_verified is False
    rs = build_requirements(s.get("smi-0314"), "q")                         # eligible but numeric -> still flagged
    assert "scope_ambiguity:numeric_answer" in rs.scope_flags
    heur = next(r for r in s.records() if r.tier_source == "heuristic_v2")
    assert "scope_unreviewed_heuristic_tiers" in build_requirements(heur, "q").scope_flags


def test_question_ids_and_reference_answers_are_preserved(by_id):
    from src.evaluation.modular.reference import ReferenceMaterial
    rec = by_id["smi-0449"]
    ref = ReferenceMaterial.from_corpus_record(rec)
    assert ref.question_id == "smi-0449" and ref.canonical_answer == rec["canonical_answer"]
    assert set(store().ids()) == set(by_id)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ref.canonical_answer = "changed"


def test_tamper_fixture_writes_exactly_the_bytes_it_hashes(tmp_path):
    """Stage 8C regression (found on Windows): write_text turned "\\n" into "\\r\\n", so the sidecar no longer matched the sha256 recorded for it
    and two eligibility tests failed with ScopeIntegrityError before reaching their real assertions."""
    s = _tampered(tmp_path, lambda r: None)
    side = tmp_path / "s.jsonl"
    assert b"\r\n" not in side.read_bytes()
    assert json.loads((tmp_path / "m.json").read_text())["sidecar_sha256"] == hashlib.sha256(side.read_bytes()).hexdigest()
    assert len(s) == 666
