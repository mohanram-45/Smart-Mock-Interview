"""Stage 10M: false rejections and false acceptances, internal-id leaks, payload consistency, memory kept across a retry, faithful lead-ins. Scripted: these prove validator and plumbing behaviour for the
failure shapes the Windows run reported (T01-T12, M01-M07); they do not show what a language model writes. Real replies of that run were not available to this cycle, so each test is built from the described symptom."""
import json

import pytest

from src.demo import followup_llm as FL, memory as M, opportunity_eval as OE
from src.evaluation.providers.mock import MockProvider


@pytest.fixture(autouse=True)
def _vocab_isolated():
    FL.set_vocabulary_source(lambda: [])
    yield
    FL.set_vocabulary_source(None)


def mk(question, answer, concepts, ref="", topic="Topic", domain="d"):
    return FL.Context(role="Data Scientist", stage="core", question_id="q", question=question, topic=topic, answer=answer, concepts=concepts, reference=ref, domain=domain)


def C(i, label, members=()):
    return {"id": i, "label": label, "tier": "essential", "members": list(members) or [label]}


def ask(q, quote, cid="K1", purpose="probe_concept", **kw):
    d = {"decision": "ask", "question": q, "purpose": purpose, "concept_id": cid, "answer_quote": quote, "memory_id": "none"}
    d.update(kw)
    return d


# ------------------------------------------------------------------------------------------------ false rejections of valid wording
BIN = mk("How does binary search work?", "It is O(log n).", [C("K1", "comparison with linear search"), C("K2", "halving the sorted range")], "Binary search halves a sorted range each step, O(log n), versus O(n) for linear search.")


def test_T03_worst_case_is_ordinary_english_not_a_new_technical_term():
    p, why = FL.validate(ask("How does the worst-case cost of binary search compare with linear search?", "It is O(log n)."), BIN)
    assert p is not None, why
    assert any(n.startswith("terms:accepted:worst-case:plain_compound") for n in p.notes)


def test_an_invented_hyphenated_term_is_still_rejected():
    p, why = FL.validate(ask("How does the hyper-quantum-sieve change the cost compared with linear search?", "It is O(log n)."), BIN)
    assert p is None and any(w.startswith("question:novel_terms") for w in why)


def test_an_acronym_of_a_phrase_in_the_material_is_accepted_and_an_unrelated_one_is_not():
    c = mk("What is logistic regression?", "It predicts the probability of a class.", [C("K1", "maximum likelihood estimation"), C("K2", "sigmoid function")], "Weights are fit by maximum likelihood estimation.")
    p, why = FL.validate(ask("How does MLE choose the weights behind the probability you described?", "predicts the probability of a class", purpose="clarify"), c)
    assert p is not None, why
    p, why = FL.validate(ask("How does QZX choose the weights behind the probability you described?", "predicts the probability of a class", purpose="clarify"), c)
    assert p is None and any(w.startswith("question:novel_terms") for w in why)


def test_M06_a_standard_term_of_the_curated_bank_is_vetted_vocabulary_but_only_for_that_domain():
    c = mk("What is deep learning?", "It uses neural networks with many layers.", [C("K1", "representation learning"), C("K2", "contrast with other algorithms")], "Deep learning stacks many layers of neural networks and learns representations.", domain="ml")
    q = ask("How does representation learning in neural networks contrast with k-nearest approaches?", "neural networks with many layers")
    p, why = FL.validate(q, c)
    assert p is None and any("k-nearest" in w for w in why), "without the bank, an unsupported term is rejected"
    FL.set_vocabulary_source(lambda: [{"domain": "ml", "question": "How does k-nearest neighbours classify?", "canonical_answer": "It votes among the k-nearest points.", "key_concepts": []}])
    p, why = FL.validate(q, c)
    assert p is not None and any("k-nearest:vetted_bank_vocabulary" in n for n in p.notes), why
    FL.set_vocabulary_source(lambda: [{"domain": "sql", "question": "k-nearest", "canonical_answer": "k-nearest", "key_concepts": []}])
    p, why = FL.validate(q, c)
    assert p is None, "vocabulary from another domain does not vet the term"


# ------------------------------------------------------------------------------------------------ evidence: a paraphrased quote is not a bad question (T01, T06); a fabricated one is
SUP = mk("What is supervised learning?", "Supervised learning means you train a model on labelled data, so each example has an input and the correct output. Classification and regression are the two kinds.",
         [C("K1", "loss minimisation"), C("K2", "generalisation"), C("K3", "train and test split")], "A model is fit by minimising a loss and judged on held-out data.")


def test_T01_a_paraphrased_or_empty_quote_no_longer_voids_a_grounded_question():
    for quote in ("train a model using labelled data with inputs and correct outputs", "", "photosynthesis converts sunlight"):
        p, why = FL.validate(ask("How does the model decide which output is correct for a labelled example, and which loss does it minimise?", quote, "K1"), SUP)
        assert p is not None, (quote, why)
        assert p.evidence[0]["ref"] in SUP.answer and p.evidence[0]["source"] == "answer", "evidence is a verbatim sentence of the answer chosen by code"
        assert any(e["source"] == "curated_concept" for e in p.evidence)


def test_a_question_that_is_not_tied_to_the_answer_is_still_rejected_whatever_quote_the_model_sends():
    p, why = FL.validate(ask("How do tectonic plates move over the mantle?", "Supervised learning means you train a model on labelled data", "K1"), SUP)
    assert p is None and any(w in why for w in ("question:not_tied_to_answer", "question:not_anchored")), why


# ------------------------------------------------------------------------------------------------ T05: internal ids never reach the candidate
IS = mk("What is the difference between is and ==?", "The 'is' operator compares values just like == does.", [C("K1", "identity versus equality"), C("K2", "object identity")], "is compares identity, == compares values.")


@pytest.mark.parametrize("q", ["How does E1 relate to what you said about the is operator and ==?", "How does e1 relate to what you said about the is operator and ==?", "How does (K1) relate to the is operator you described?"])
def test_known_ids_in_any_case_are_replaced_by_the_label(q):
    p, why = FL.validate(ask(q, "The 'is' operator compares values", "K1"), IS)
    assert (p is not None and not FL._ID_SCHEMES.search(p.question)) or (p is None), (why,)
    if p is not None:
        assert "identity versus equality" in p.question


def test_an_unknown_id_is_rejected_not_passed_through():
    p, why = FL.validate(ask("How does E7 change what you said about the is operator and ==?", "The 'is' operator compares values", "K1"), IS)
    assert p is None and "question:id_leak" in why


def test_a_legitimate_token_that_looks_like_an_id_is_allowed_when_the_candidate_said_it():
    c = mk("What is regularisation?", "L2 regularisation shrinks weights.", [C("K1", "weight shrinkage"), C("K2", "bias variance trade-off")], "L2 shrinks weights.")
    p, why = FL.validate(ask("How does L2 regularisation shrink the weights you mentioned, and what does that do to variance?", "L2 regularisation shrinks weights", "K1"), c)
    assert p is not None, why


# ------------------------------------------------------------------------------------------------ T12: a wrong premise is rejected; a right one is not
T12 = mk("What is a Type I error?", "A Type I error is rejecting a true null hypothesis. I remember it as a false alarm.", [C("K1", "Type II error"), C("K2", "false positive")], "Type I is a false positive; Type II is a false negative.")


def test_T12_asking_how_two_names_for_one_thing_differ_is_rejected():
    p, why = FL.validate(ask("How does a Type I error differ from a false positive in a hypothesis test?", "rejecting a true null hypothesis", "K2"), T12)
    assert p is None and any(w.startswith("question:false_premise") for w in why)


def test_a_question_about_the_open_concept_is_not_a_false_premise():
    p, why = FL.validate(ask("How would you describe a Type II error next to the false alarm you mentioned?", "I remember it as a false alarm", "K1"), T12)
    assert p is not None, why


def test_a_pair_that_is_not_in_the_vetted_list_is_not_judged():
    assert FL.false_premise("How does precision differ from accuracy?") is None
    assert FL.false_premise("How does recall differ from sensitivity?") == "recall/sensitivity"


# ------------------------------------------------------------------------------------------------ payload consistency (task 4)
def test_an_ask_with_a_conflicting_skip_reason_is_normalised_visibly_not_silently():
    p, why = FL.validate(ask("How does the worst-case cost of binary search compare with linear search?", "It is O(log n).", skip_reason="covered"), BIN)
    assert p is not None and p.decision == "ask" and getattr(p, "skip_reason", None) in (None, "") and "payload:ask_with_skip_reason" in p.notes


def test_an_ask_without_a_skip_reason_is_valid_and_the_schema_does_not_require_one():
    assert "skip_reason" not in FL.build_schema(BIN)["required"]
    p, why = FL.validate(ask("How does the worst-case cost of binary search compare with linear search?", "It is O(log n)."), BIN)
    assert p is not None and "payload:ask_with_skip_reason" not in p.notes


def test_skip_with_a_question_is_rejected_and_can_be_repaired():
    p, why = FL.validate({"decision": "skip", "skip_reason": "nothing_to_add", "question": "How do non-linearities help?", "purpose": "deepen", "concept_id": "none", "answer_quote": ""}, BIN)
    assert p is None and why == ["payload:skip_with_question"] and FL.repair_instruction(why, "How do non-linearities help?", BIN)


def test_harmless_terminology_is_repairable_not_a_safety_rejection():
    fix = FL.repair_instruction(["question:novel_terms:worst-case"], "How does worst-case cost compare?", BIN)
    assert fix and "technical word" in fix
    assert FL.fallback_class(["question:novel_terms:foo"]) == "wording_failed"
    assert FL.repair_instruction(["question:novel_terms:foo", "question:instruction_like"], "x", BIN) == "", "a safety rejection beside it is never repaired"


# ------------------------------------------------------------------------------------------------ memory kept across the retry (M06)
MEMQ = "I used PyTorch to train a convolutional neural network for tumour detection in scans."


def _mem_ctx():
    c = mk("What is deep learning?", "It uses neural networks with many layers.", [C("K1", "representation learning"), C("K2", "contrast with other algorithms")], "Deep learning stacks many layers of neural networks and learns representations.", domain="ml")
    c.memory = [{"id": "m1", "kind": "project", "text": "trained a convolutional neural network for tumour detection", "quote": MEMQ, "turn": 1, "subject": "a convolutional neural network", "confidence": "high",
                 "lead": M.recall_lead({"quote": MEMQ, "kind": "project", "text": "x", "subject": None})}]
    return c


def test_M06_the_retry_keeps_the_memory_id_and_the_grounding():
    c = _mem_ctx()
    replies = [ask("How does your convolutional neural network contrast with k-nearest methods for tumour detection?", "neural networks with many layers", "K2", "trade_off", memory_id="m1"),
               ask("How does your convolutional neural network for tumour detection contrast with other algorithms?", "neural networks with many layers", "K2", "trade_off", memory_id="m1")]
    seen = []

    def script(sy, us):
        seen.append(us)
        return json.dumps(replies[len(seen) - 1])
    out = FL.LLMFollowUpGenerator(MockProvider(script), deadline=5).propose(c)
    assert out.kind == "mock" and len(seen) == 2
    assert 'Keep memory_id "m1"' in seen[1] and "EARLIER" in seen[1], "the second prompt still shows the statement and says to keep it"
    assert out.info["memory_stage"] == "used" and out.proposal.memory_id == "m1" and out.proposal.lead == c.memory[0]["lead"]
    assert out.info["mode_trace"] == ["memory", "memory"] and out.metrics.get("repaired") == 1


def test_a_retry_that_drops_the_memory_is_reported_as_not_used_never_as_success():
    c = _mem_ctx()
    replies = [ask("How does your convolutional neural network contrast with k-nearest methods?", "neural networks with many layers", "K2", "trade_off", memory_id="m1"),
               ask("How do many layers help a network represent its inputs differently from other algorithms?", "neural networks with many layers", "K2", "trade_off", memory_id="none")]
    n = []
    out = FL.LLMFollowUpGenerator(MockProvider(lambda sy, us: json.dumps(replies[len(n.append(1) or n) - 1])), deadline=5).propose(c)
    assert out.kind == "mock" and out.proposal.memory_id is None and out.info["memory_stage"] in ("declined", "not_used", "not_connected")


# ------------------------------------------------------------------------------------------------ lead-ins keep the meaning of the stored statement (M05)
def test_M05_an_explanation_lead_does_not_claim_more_than_the_candidate_said():
    it = {"kind": "explanation", "subject": "Linear and logistic regression", "quote": "Logistic regression predicts the probability of a class from the input features.", "text": "x"}
    lead = M.recall_lead(it)
    assert lead and "linear" not in lead.lower().replace("logistic regression", "") and "Logistic regression predicts the probability of a class" in lead


def test_an_explanation_lead_that_names_the_topic_is_kept_when_every_word_of_it_was_said():
    it = {"kind": "explanation", "subject": "Logistic regression", "quote": "Logistic regression predicts the probability of a class.", "text": "x"}
    assert M.recall_lead(it) == "Earlier you explained Logistic regression."


@pytest.mark.parametrize("quote,kind", [("I developed an oral cancer classification model using PyTorch.", "project"), ("The hardest challenge was class imbalance in the training data.", "challenge"),
                                        ("Binary search halves the sorted range each step.", "explanation")])
def test_every_lead_in_is_made_of_the_candidates_own_words(quote, kind):
    lead = M.recall_lead({"kind": kind, "quote": quote, "text": quote, "subject": "Searching"})
    assert lead
    body = {w.strip(".,“”").lower() for w in lead.split()}
    said = {w.strip(".,;:").lower() for w in quote.replace("My", "your").replace("I", "you").split()}
    assert len(body - said - {"earlier", "you", "said", "described", "a", "challenge", "explained", "are", "were", "your", "have", "team", "was", "the"}) <= 2


# ------------------------------------------------------------------------------------------------ the fixture cases T01-T12 through the real pipeline (scripted stand-in)
@pytest.fixture(scope="module")
def engine():
    return OE.offline_engine()


@pytest.mark.parametrize("cid", [f"T{i:02d}" for i in range(1, 13)])
def test_the_t_cases_get_an_accepted_relevant_question_from_the_well_behaved_stand_in(engine, cid):
    data = OE.load()
    row = OE.run_all(engine, OE.scripted_generator(), data, only=[cid])["rows"][0]
    assert row["success"] and row["audit"] == [] and not OE._ID_LEAK.search(row["question"]), (row["reasons"], row["question"])


def test_the_trace_script_replays_a_recorded_run_without_a_model_and_leaves_the_verdicts_unrated(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    r = subprocess.run([sys.executable, str(root / "scripts" / "stage10m_trace.py"), "--results", str(root / "reports" / "stage10_windows_evidence_2" / "results.json"), "--out", str(tmp_path), "--cases", "T02,M06"],
                       capture_output=True, text=True, cwd=root, timeout=300)
    assert r.returncode == 0, r.stderr[-600:]
    t = json.loads((tmp_path / "trace.json").read_text(encoding="utf-8"))
    assert {x["id"] for x in t["rows"]} == {"T02", "M06"}
    assert all(x["human_verdict"]["rejection_correct"] is None and x["human_verdict"]["question_useful"] is None for x in t["rows"])
    assert "not a model run" in (tmp_path / "trace.md").read_text(encoding="utf-8")
