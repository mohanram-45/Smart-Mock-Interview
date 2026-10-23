import re
import pytest
from src.retrieval.doc_formats import FORMATS, build_text, split_sentences, head_text

def toks(t):                       # stand-in tokenizer: words and punctuation (the real one runs in the Windows experiment)
    return len(re.findall(r"\w+|[^\w\s]", t))

REC = {"question_id": "smi-x", "topic": "Sorting", "question": "What is bubble sort and what is its time complexity?",
       "key_concepts": ["bubble sort", "O(n^2)", "adjacent swaps"],
       "canonical_answer": "Bubble sort repeatedly swaps adjacent out-of-order elements. It runs in O(n^2) time in the average and worst case. "
                           "With an early-exit flag the best case is O(n). It is stable and in place. " + "Filler sentence number %d adds more text. " * 1}

def test_formats_are_deterministic_and_distinct():
    t = {f: build_text(REC, f, toks)["text"] for f in FORMATS}
    assert t["question"] == REC["question"]
    assert t["qk"] == head_text(REC) and t["qk"].startswith("Sorting\n")
    assert t["qka"].startswith(t["qk"]) and t["qka"].endswith(REC["canonical_answer"])
    assert t["qk_concise"].startswith(t["qk"])
    assert build_text(REC, "qk_concise", toks) == build_text(REC, "qk_concise", toks)

def test_concise_packs_whole_sentences_within_budget():
    out = build_text(REC, "qk_concise", toks, max_seq_length=60)
    assert toks(out["text"]) <= 58 and not out["flags"]["answer_cut"] and out["flags"]["answer_sentences"] >= 1
    assert out["text"].rstrip().endswith(".")                                  # ends on a sentence boundary
    for s in split_sentences(out["text"].split("Key concepts:")[1].split("\n", 1)[1]):
        assert s in REC["canonical_answer"]                                    # only verbatim existing sentences

def test_concise_never_exceeds_budget_for_any_budget():
    for m in range(40, 300, 7):
        out = build_text(REC, "qk_concise", toks, max_seq_length=m)
        assert toks(out["text"]) <= max(m - 2, toks(head_text(REC))), m

def test_long_first_sentence_is_cut_and_flagged():
    r = dict(REC, canonical_answer="word " * 200 + ".")
    out = build_text(r, "qk_concise", toks, max_seq_length=80)
    assert out["flags"]["answer_cut"] is True and toks(out["text"]) <= 78

def test_head_over_budget_flagged_not_hidden():
    r = dict(REC, question="scenario " * 300)
    out = build_text(r, "qk_concise", toks, max_seq_length=256)
    assert out["flags"]["head_over_budget"] is True and out["flags"]["answer_sentences"] == 0

def test_never_adds_text_not_in_record():
    out = build_text(REC, "qk_concise", toks, max_seq_length=100)["text"]
    for line in out.splitlines()[:2]:
        assert line in (REC["topic"], REC["question"])

def test_unknown_format_and_missing_counter():
    with pytest.raises(ValueError): build_text(REC, "nope")
    with pytest.raises(ValueError): build_text(REC, "qk_concise")


def test_joined_text_is_remeasured_and_trimmed():
    def odd(t):                       # counter where joining costs more than the parts (like subword merges across a boundary)
        return toks(t) + t.count("\n") * 3
    for m in range(50, 200, 11):
        out = build_text(REC, "qk_concise", odd, max_seq_length=m)
        assert odd(out["text"]) <= max(m - 2, odd(head_text(REC))), m
