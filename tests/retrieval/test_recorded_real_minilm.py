"""Relevance-based regression over the RECORDED real all-MiniLM-L6-v2 results (Windows run, Stage 2C-final).

These do not require the model: they pin the *properties* of the diagnosed bubble-sort case, using relevance, never exact rankings
or scores. A stale recording (different corpus) makes them fail loudly instead of passing on old data.
"""
import json
from pathlib import Path

import pytest

D = Path(__file__).resolve().parents[2] / "data" / "retrieval" / "stage2c"
pytestmark = pytest.mark.skipif(not (D / "diagnosis_minilm.json").exists(), reason="recorded real-MiniLM results not present")

FORMATS = ("qka", "question", "qk", "qk_concise")
BUBBLE, QUICK, FIZZ, BSEARCH = "smi-0453", "smi-0452", "smi-0450", "smi-0449"


@pytest.fixture(scope="module")
def diag():
    return json.loads((D / "diagnosis_minilm.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rankings():
    return json.loads((D / "rankings_minilm.json").read_text(encoding="utf-8"))


def test_recording_matches_current_corpus_and_real_model(rankings):
    from src.retrieval.corpus import load_corpus
    assert rankings["corpus_sha256"] == load_corpus()["manifest"]["corpus_sha256"]
    assert rankings["embedder"]["model"] == "sentence-transformers/all-MiniLM-L6-v2" and rankings["embedder"]["backend"] == "sentence-transformers"
    assert rankings["faiss_vs_numpy_top10_identical_queries"] == "166/166"


@pytest.mark.parametrize("fmt", FORMATS)
def test_paraphrased_bubble_sort_query_finds_the_bubble_sort_record_first(diag, fmt):
    p = next(x for x in diag["probes"] if x["label"].startswith("paraphrase"))
    top = p["per_format"][fmt]["top10_all"]
    assert top[0]["id"] == BUBBLE
    assert top[0]["score"] > 0.6                                                   # a real match scores far above the neighbours
    assert top[0]["score"] - top[1]["score"] > 0.25


@pytest.mark.parametrize("fmt", FORMATS)
def test_keyword_query_finds_bubble_sort_first(diag, fmt):
    p = next(x for x in diag["probes"] if x["label"].startswith("short keyword"))
    assert p["per_format"][fmt]["top10_all"][0]["id"] == BUBBLE


@pytest.mark.parametrize("fmt", FORMATS)
def test_self_is_the_best_match_and_the_only_other_sorting_record_is_within_the_top_five_after_exclusion(diag, fmt):
    p = next(x for x in diag["probes"] if x["label"].startswith("exact question"))
    pf = p["per_format"][fmt]
    assert pf["rank_of_self"] == 1                                                  # why the demo excluded it: it IS the query
    others = [x["id"] for x in pf["top10_excluding_self"]]
    assert QUICK in others[:5]                                                      # relevance, not an exact position (FizzBuzz/quicksort are a near-tie)
    assert all(x["domain"] == "Python" for x in pf["top10_excluding_self"][:4])     # nothing from an unrelated domain in the top 4


def test_quicksort_vs_fizzbuzz_is_a_near_tie_not_a_confident_error(diag):
    p = next(x for x in diag["probes"] if x["label"].startswith("exact question"))
    cr = p["per_format"]["qka"]["cluster_rank_score"]
    assert abs(cr[FIZZ]["score"] - cr[QUICK]["score"]) < 0.05                       # recorded: 0.454 vs 0.446
    assert max(cr[FIZZ]["score"], cr[QUICK]["score"]) < 0.5                         # and both are weak matches in absolute terms


def test_truncation_did_not_cause_the_case(diag):
    for rid in (BUBBLE, QUICK, FIZZ, BSEARCH):
        assert diag["records"][rid]["tokens"]["qka"] <= 256, rid                   # every record involved fits the model window


def test_exactly_one_other_sorting_record_exists_in_the_corpus():
    from src.retrieval.corpus import load_corpus
    import re
    hits = [r["question_id"] for r in load_corpus()["records"] if re.search(r"\b(bubble|quick|merge|insertion|heap|selection) ?sort", r["question"], re.I)]
    assert sorted(hits) == [QUICK, BUBBLE]                                          # coverage limit: only these two


def test_selected_format_has_no_silent_truncation_outside_the_flagged_long_records():
    f = json.loads((D / "formats_minilm.json").read_text(encoding="utf-8"))
    qkc = f["docs"]["qk_concise"]
    over = [d["id"] for d in qkc if d["tokens"] > 256]
    flagged = [d["id"] for d in qkc if d["flags"]["head_over_budget"]]
    assert sorted(over) == sorted(flagged)                                          # only the 31 long-head records exceed the window
    assert len(flagged) == 31 and f["stats"]["qka"]["n_over_limit"] == 450
