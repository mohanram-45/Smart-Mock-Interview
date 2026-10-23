"""Stage 11S: technical correctness of the written question, and memory attribution owned by the application.

What these tests are: offline checks of CODE behaviour (which questions the rules refuse, which stored statement the code attaches, what the prompt contains). What they are not: evidence about what a
language model writes, and not human judgement of interview quality. The good/bad question sets were written by the same author as the rules, so they are sanity sets rather than independent evidence;
the real-model numbers quoted in the report come from the Windows run, not from here."""
import copy
import json
import re
from pathlib import Path

import pytest

from src.demo import followup_llm as FL, intel, opportunity_eval as OE, question_pairs_eval as QP
from src.evaluation.providers.mock import MockProvider

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "src" / "demo" / "eval_data"
CASES = {c["id"]: c for c in OE.load()["cases"]}
HOLDOUT4 = json.loads((EVAL / "stage11s_correctness_pairs_v1.json").read_text(encoding="utf-8"))
# The questions the real Windows run (prompt 11.obj2, llama3.2:3b, tmp/stage10_opps_20261022_162322) accepted or fell back on, and what was wrong with each. Used to prove the repair refuses them; the
# ids identify the recorded data, never a rule: no rule in src/demo reads a case id.
RECORDED = [
    ("T12", "How does a false positive affect the outcome of a test when a true null hypothesis is actually false?", "contradictory_premise"),
    ("T11", "How do deep learning's learned representations compare to those found in hierarchical representations?", "circular_contrast"),
    ("T10", "What metrics would you use to evaluate the model's performance on the classes with the lowest and highest probabilities?", "invented_qualifier"),
    ("T03", "How does the growth of the number of comparisons relate to the size of the list when the number of comparisons is found to be log n?", "ignores_objective"),
    ("T04", "How do these small learned filters in a convolutional layer interact with the input data to detect local patterns like edges?", "repeats_answer_phrase"),
    ("M01", "How would evaluating the accuracy of your oral cancer classification model using cross-validation inform your understanding of its performance on unseen data?", "objective"),
    ("M02", "How does the concept of supervised learning apply to your spam classifier?", "objective"),
    ("M03", "How do you use the return_value and side_effect features of a mocking mechanism in pytest to isolate dependencies in your Flask API tests?", "presupposes_use"),
    ("M04", "How does atomicity relate to handling money transfers in your money transfers, and how does it impact the consistency of the database?", "duplicated_subject"),
    ("M06", "How does the use of neural networks with many layers in your convolutional neural network for tumour detection in scans relate to hierarchical representations?", "repeats_answer_phrase"),
    ("M07", "How does the process of halving the sorted list at each step relate to the time complexity of your search feature in the library catalogue?", "implies_unclaimed_use"),
]
# One question per memory case that uses the candidate's own earlier statement, asks about the still-open objective and claims nothing they did not say.
GROUNDED = {
    "M01": "How would a ROC curve change what you conclude about your oral cancer classification model?",
    "M02": "How would labelled training data matter in your spam classifier?",
    "M03": "How would a mock's return value let you test your Flask API without the database?",
    "M04": "How would isolation change what two overlapping money transfers see in your billing database?",
    "M05": "How would maximum likelihood estimation pick the weights behind that sigmoid output?",
    "M06": "How would hierarchical representations show up in your tumour detection model?",
    "M07": "How would a linear search through your library catalogue compare with halving a sorted list?",
}


@pytest.fixture(scope="module")
def eng():
    return OE.offline_engine()


@pytest.fixture(autouse=True)
def _vocab():
    FL.set_vocabulary_source(lambda: [])
    yield
    FL.set_vocabulary_source(None)


def built(eng, id_):
    """(context, offered statements, session, core) exactly as the benchmark builds a case."""
    return OE.build_case(eng, copy.deepcopy(CASES[id_]))


def case(eng, id_):
    return built(eng, id_)[0]


def audit_of(prop, ctx, session):
    """The independent rule audit, called the way the evaluator calls it (with the session, so lead provenance can be re-derived)."""
    return set(OE.audit(prop.question, ctx, prop.memory_id, [m["id"] for m in ctx.memory], prop.lead, session))


def judge(eng, id_, q):
    ctx = case(eng, id_)
    obj = intel.plan_objective(ctx)
    return intel.evaluate_question(q, ctx, obj), ctx, obj


def h4ctx(it):
    return FL.Context(role="Software Engineer", stage="core", question_id=it["id"], question=it["question"], topic=it["topic"], answer=it["answer"], concepts=it["concepts"], reference=it["reference"])


# ---------------------------------------------------------------------------------------------- 1. the recorded defects, and the questions that must survive
@pytest.mark.parametrize("id_,q,reason", RECORDED, ids=[r[0] for r in RECORDED])
def test_every_question_the_brief_calls_wrong_is_now_refused(eng, id_, q, reason):
    v, *_ = judge(eng, id_, q)
    assert v.prop is None, "accepted: " + q
    assert any(reason in r for r in v.reasons), v.reasons


@pytest.mark.parametrize("id_", sorted(GROUNDED))
def test_a_grounded_question_is_accepted_and_the_code_attaches_the_statement(eng, id_):
    ctx, _offered, session, _core = built(eng, id_)
    obj = intel.plan_objective(ctx)
    v = intel.evaluate_question(GROUNDED[id_], ctx, obj)
    assert v.prop is not None, v.reasons
    assert v.prop.memory_id == obj.memory["id"], "the application attaches the id it chose"
    assert v.prop.validity["memory_attribution"].startswith("code") and v.prop.validity["decided_by"] == "code"
    assert not (audit_of(v.prop, ctx, session) & OE.REF_AUDITS), audit_of(v.prop, ctx, session)


# ---------------------------------------------------------------------------------------------- 2. each correctness rule, with the wrong shape AND the right one
@pytest.mark.parametrize("bad,good", [
    ("How does a true null hypothesis behave when the hypothesis is false?", "How does a false positive relate to rejecting a hypothesis that actually holds?"),
    ("How does a sorted list behave once the list is unsorted?", "What happens to a sorted list when the next input arrives unsorted?"),
    ("How does a committed transaction behave while the transaction is uncommitted?", "What can another transaction see while this one is still uncommitted?"),
    ("How does a stateless service behave when the service is stateful?", "How would a stateless service handle a user's session?"),
])
def test_a_premise_that_contradicts_itself_is_refused_and_its_consistent_form_is_not(bad, good):
    assert intel.contradictory_premise(bad), bad
    assert intel.contradictory_premise(good) is None, good


@pytest.mark.parametrize("q", [
    "How does a positive result differ when the test is negative?",                      # two different things, each with its own property
    "How does supervised learning differ from unsupervised learning?",
    "What happens to an invalid transaction in a valid database?",
    "How would a labelled set and an unlabelled set change your approach?",
    "How does a stale response get revalidated when the copy is fresh enough?",
])
def test_opposites_used_legitimately_are_left_alone(q):
    assert intel.contradictory_premise(q) is None, q


def test_a_contrast_with_the_candidates_own_words_is_refused_and_a_real_contrast_is_kept(eng):
    ctx, = (case(eng, "T11"),)
    obj = intel.plan_objective(ctx)
    assert intel.circular_contrast("How do deep learning's learned representations compare to those found in hierarchical representations?", ctx, obj)
    for keep in ["How would hierarchical representations differ from features designed by hand for the same images?",
                 "Why would stacking more layers produce representations at different levels of detail?"]:
        assert not intel.circular_contrast(keep, ctx, obj), keep
    c3 = case(eng, "T03")
    assert not intel.circular_contrast("How does binary search compare to linear search when the target is not in the sorted list?", c3, intel.plan_objective(c3))


def test_handing_back_a_phrase_of_the_answer_is_refused_but_a_technical_term_is_not(eng):
    ctx = case(eng, "T04")
    assert intel.repeats_answer_phrase("How do these small learned filters in a convolutional layer interact with the input data to detect local patterns like edges?", ctx)
    for keep in ["How would a filter respond to a region with no edge in it at all?",
                 "Why would a second convolutional layer see something a first one cannot?"]:
        assert intel.repeats_answer_phrase(keep, ctx) is None, keep
    t10 = case(eng, "T10")
    assert intel.repeats_answer_phrase("How would cross-validation and accuracy mislead you on a rare class?", t10) is None


@pytest.mark.parametrize("q,dup", [
    ("How does atomicity relate to handling money transfers in your money transfers, and how does it impact consistency?", "money transfers"),
    ("How does the use of neural networks in your convolutional neural network relate to hierarchical representations?", "neural networks"),
    ("How does a hash table resize when the hash table is full?", "hash table"),
])
def test_naming_the_same_thing_twice_is_refused(q, dup):
    assert intel.duplicated_subject(q) == dup


@pytest.mark.parametrize("q", [
    "How does binary search compare to linear search for a large dataset?",
    "How does a sorted list differ from an unsorted list?",
    "How would a labelled email and an unlabelled email change training?",
    "What happens to the search space at each step of the search?",
])
def test_ordinary_repetition_is_not_a_duplicate_subject(q):
    assert intel.duplicated_subject(q) is None, q


def test_two_questions_in_one_turn_are_refused_and_a_leading_phrase_is_not():
    assert intel.two_questions("How does atomicity relate to money transfers, and how does it impact the consistency of the database?")
    for keep in ["In your payments ledger, what could go wrong if two transfers ran at once without isolation?",
                 "How would isolation matter, in practice, for two overlapping transfers?",
                 "How would class imbalance change what the accuracy tells you, and which metric would you look at instead?"]:
        assert not intel.two_questions(keep), keep


def test_a_superlative_nobody_mentioned_is_refused_and_a_supported_one_is_kept(eng):
    t10 = case(eng, "T10")
    assert sorted(intel.invented_qualifier("What metrics would you use for the classes with the lowest and highest probabilities?", t10)) == ["highest", "lowest"]
    assert intel.invented_qualifier("How would a ROC curve change what you conclude about this model?", t10) == []
    t06 = case(eng, "T06")
    assert intel.invented_qualifier("What would the worst case of bubble sort cost for a list of n elements?", t06) == [], "'worst case' is in the candidate's own answer"


def test_stating_the_value_is_not_probing_for_it(eng):
    ctx = case(eng, "T03")
    assert intel.value_stated("... when the number of comparisons is found to be log n?", "O(log n)")
    assert not intel.value_stated("How does the number of comparisons grow as the list gets longer?", "O(log n)")
    obj = intel.plan_objective(ctx)
    probe = "How would the number of comparisons grow for a linear search as the list doubles in length?"
    assert intel.evaluate_question(probe, ctx, obj).prop is not None, intel.evaluate_question(probe, ctx, obj).reasons


# ---------------------------------------------------------------------------------------------- 3. the objective comes from the verified rubric, not from the model
def test_a_second_name_for_something_already_explained_is_not_the_objective(eng):
    ctx = case(eng, "T12")
    s1 = next(c for c in ctx.concepts if c["label"] == "false positive")
    assert intel.equated_with_explained(s1, ctx) == "E1", "the reference says Type I error IS a false positive, and Type I error was explained"
    assert intel.plan_objective(ctx).target["id"] != s1["id"]
    t11 = case(eng, "T11")
    hier = next(c for c in t11.concepts if c["label"] == "hierarchical representations")
    assert intel.equated_with_explained(hier, t11) is None, "a sentence that says deep learning USES hierarchical representations does not make them the same thing"
    assert intel.plan_objective(t11).target["id"] == hier["id"]


def test_the_prompt_carries_a_vetted_premise_and_never_a_value_or_an_id(eng):
    seen = 0
    for id_, c in CASES.items():
        if c["mode"] != "technical":
            continue
        ctx = OE.build_case(eng, copy.deepcopy(c))[0]
        obj = intel.plan_objective(ctx)
        if obj is None:
            continue
        prem = intel.target_premise(ctx, obj)
        for mode in ("standard", "memory"):
            _, user, _ = intel.build_prompt(ctx, obj, "n", mode)
            assert not re.search(r"\b[ESGK]\d{1,2}\b", user) and not re.search(r"\bm\d\b", user), (id_, mode)
            if prem:
                assert prem in user and not intel._VALUE_RX.search(prem) and not re.search(r"\d", prem), (id_, prem)
        seen += bool(prem)
    assert seen >= 6, "the rubric supplies a premise for most technical cases"
    assert intel.OBJ_PROMPT_VERSION == "11.obj5"


def test_an_explanation_is_not_called_the_candidates_own_work(eng):
    ctx = case(eng, "M05")
    obj = intel.plan_objective(ctx)
    assert obj.memory["kind"] not in intel.OWN_WORK_KINDS and obj.handle is None
    system, _, _ = intel.build_prompt(ctx, obj, "n", "memory")
    assert system is intel.SYSTEM_OBJ_IDEA and 'never write "your project"' in system
    assert "do not write 'your'" in intel.memory_nudge(obj, ctx)
    own = case(eng, "M02")
    sys_own, _, _ = intel.build_prompt(own, intel.plan_objective(own), "n", "memory")
    assert sys_own is intel.SYSTEM_OBJ_MEM


# ---------------------------------------------------------------------------------------------- 4. the five conditions the application checks before it attaches a memory id
def test_the_model_never_supplies_the_id_and_a_wrong_one_changes_nothing(eng):
    ctx = case(eng, "M02")
    replies = [json.dumps({"question": GROUNDED["M02"], "memory_id": wrong}) for wrong in ("m9", "none", None)]
    for raw in replies:
        gen = FL.LLMFollowUpGenerator(MockProvider(lambda s, u, r=raw: r), deadline=30, engine="objective")
        out = gen.propose(ctx)
        assert out.proposal is not None and out.proposal.memory_id == "m1", (raw, out.reasons)


def test_condition_1_a_statement_that_is_not_this_sessions_is_never_attributed(eng):
    ctx = case(eng, "M02")
    obj = intel.plan_objective(ctx)
    assert intel.in_session(obj.memory, ctx)
    for broken in ({**obj.memory, "id": "m99"}, {**obj.memory, "quote": obj.memory["quote"] + " and I also wrote the database"}, {**obj.memory, "id": ""}):
        assert not intel.in_session(broken, ctx)
        bad_obj = intel.Objective(obj.kind, obj.target, obj.open_ids, obj.anchor, broken, obj.memory_reason, obj.hint, obj.stated, obj.stated_words, obj.handle)
        v = intel.evaluate_question(GROUNDED["M02"], ctx, bad_obj)
        assert v.prop is None or v.prop.memory_id is None


def test_condition_3_claiming_the_work_uses_something_they_never_mentioned_is_refused(eng):
    ctx = case(eng, "M07")
    obj = intel.plan_objective(ctx)
    assert intel.implies_unclaimed_use("How does halving the sorted list relate to the time complexity of your search feature?", ctx, obj.memory)
    assert not intel.implies_unclaimed_use(GROUNDED["M07"], ctx, obj.memory), "asked as a possibility, it claims nothing"
    assert not intel.implies_unclaimed_use("How would a linear search behave on your catalogue?", ctx, obj.memory)
    m2 = case(eng, "M02")
    o2 = intel.plan_objective(m2)
    assert not intel.implies_unclaimed_use("How would labelled training data matter in your spam classifier?", m2, o2.memory)


def test_condition_4_a_generic_question_about_the_topic_is_not_memory_use(eng):
    for id_, q in [("M02", "How does supervised learning apply to training a classifier on labelled emails?"),
                   ("M01", "How would you evaluate a classification model in general?"),
                   ("M04", "How is a billing database usually designed for money transfers?")]:
        v, *_ = judge(eng, id_, q)
        assert v.prop is None or v.prop.memory_id is None, (id_, q)


def test_condition_5_a_presupposition_is_refused_while_the_conditional_form_is_accepted(eng):
    v, *_ = judge(eng, "M03", "How do you use return_value and side_effect in your Flask API tests?")
    assert v.prop is None and "memory:presupposes_use" in v.reasons
    ok, *_ = judge(eng, "M03", GROUNDED["M03"])
    assert ok.prop is not None and ok.prop.memory_id == "m1", ok.reasons
    hypo, *_ = judge(eng, "M01", "How would cross-validation on your oral cancer classification model inform what you expect on unseen scans?")
    assert hypo.prop is None or "memory:presupposes_use" not in hypo.reasons, "a question about a possibility presupposes nothing"


def test_the_lead_is_dropped_when_the_question_already_names_the_work(eng):
    ctx, _o, session, _c = built(eng, "M01")
    obj = intel.plan_objective(ctx)
    assert obj.handle and FL._norm(obj.handle) in FL._norm(GROUNDED["M01"])
    v = intel.evaluate_question(GROUNDED["M01"], ctx, obj)
    assert v.prop is not None and v.prop.memory_id == obj.memory["id"]
    assert v.prop.lead is None and "memory:lead_dropped_question_names_the_work" in v.prop.notes
    assert audit_of(v.prop, ctx, session) == set(), "no lead is a valid state for the audit too, as long as the cited statement was offered"
    other, *_ = judge(eng, "M05", GROUNDED["M05"])
    assert other.prop is not None and other.prop.lead, "a question that does not name the work keeps its lead-in"


def test_a_reference_the_session_offered_is_supported_and_an_unoffered_one_is_not(eng):
    ctx = case(eng, "M02")
    assert FL.offered_support(ctx).strip() and FL.unsupported_reference("How would labelled data matter in your spam classifier?", ctx, FL.offered_support(ctx)) == []
    assert FL.unsupported_reference("How would labelled data matter in your spam classifier?", ctx, "") != [], "without the session's own statements nothing backs it"
    assert FL.unsupported_reference("How would indexing speed up your Kubernetes cluster migration?", ctx, FL.offered_support(ctx)) != []
    n = case(eng, "N02")
    assert FL.offered_support(n).strip() == "" and FL.unsupported_reference("How would consistency matter in the ledger you built?", n, FL.offered_support(n)) != []


# ---------------------------------------------------------------------------------------------- 5. acceptance and the independent audit may not disagree
def test_nothing_accepted_anywhere_carries_an_audit_finding_about_the_candidate(eng):
    pool = [(id_, q) for id_, q in GROUNDED.items()] + [(id_, q) for id_, q, _ in RECORDED] + \
           [(id_, q) for id_ in ("M01", "M02", "M03", "M04", "M05", "M06", "M07") for q in (f"How would the idea apply in your work on {id_}?",)]
    checked = 0
    for id_, q in pool:
        ctx, _offered, session, _core = built(eng, id_)
        v = intel.evaluate_question(q, ctx, intel.plan_objective(ctx))
        if v.prop is None:
            continue
        checked += 1
        assert not (audit_of(v.prop, ctx, session) & OE.REF_AUDITS), (id_, q, sorted(audit_of(v.prop, ctx, session)))
    assert checked >= 7


def test_the_audit_reports_an_implied_implementation_on_its_own(eng):
    ctx = case(eng, "M07")
    m = intel.plan_objective(ctx).memory
    aud = OE.audit("How does halving the sorted list relate to the time complexity of your search feature?", ctx, m["id"], [x["id"] for x in ctx.memory], None)
    assert "implied_unclaimed_implementation" in aud and "implied_unclaimed_implementation" in OE.REF_AUDITS


# ---------------------------------------------------------------------------------------------- 6. false rejection and false acceptance, measured
def test_the_new_rules_refuse_no_good_question_on_any_set(eng):
    budget = {"fixture": (1, 2), "holdout": (5, 0), "holdout2": (5, 0), "holdout3": (2, 1)}      # unchanged from Stage 11R: the repair adds no false rejection
    seen = {}
    for path in (EVAL / "stage10n_question_pairs_v1.json", EVAL / "stage11r_question_pairs_v1.json"):
        for it in json.loads(path.read_text(encoding="utf-8"))["items"]:
            ctx = QP._context(it, eng, CASES)
            obj = intel.plan_objective(ctx)
            s = seen.setdefault(it["src"], {"FR": 0, "FA": 0})
            for q in it["good"]:
                s["FR"] += not (obj is not None and intel.evaluate_question(q, ctx, obj).prop is not None)
            for b in it["bad"]:
                s["FA"] += bool(obj is not None and intel.evaluate_question(b["q"], ctx, obj).prop is not None)
    for src, (fr, fa) in budget.items():
        assert (seen[src]["FR"], seen[src]["FA"]) <= (fr, fa), (src, seen[src])


def test_the_new_question_set_catches_the_defects_without_refusing_the_good_ones():
    fr, fa = [], []
    for it in HOLDOUT4["items"]:
        ctx = h4ctx(it)
        obj = intel.plan_objective(ctx)
        for q in it["good"]:
            v = intel.evaluate_question(q, ctx, obj)
            if v.prop is None:
                fr.append((it["id"], q, v.reasons))
        for b in it["bad"]:
            if intel.evaluate_question(b["q"], ctx, obj).prop is not None:
                fa.append((it["id"], b["q"], b["why"]))
    assert fr == [], fr
    # Three bad questions are not detected and are named in the report: two contrast a concept with another concept that is not a rival of it (knowing that needs meaning, not words), and one has its
    # second interrogative separated from its verb. The count is pinned so that a later change cannot quietly add more.
    assert len(fa) <= 3, fa
    assert sum(len(i["bad"]) for i in HOLDOUT4["items"]) - len(fa) >= 15


# ---------------------------------------------------------------------------------------------- 7. integration: nothing else moved
def test_the_engine_still_stops_an_unsafe_question_and_the_default_engine_is_unchanged(monkeypatch, eng):
    ctx = case(eng, "M07")
    gen = FL.LLMFollowUpGenerator(MockProvider(lambda s, u: json.dumps({"question": "How does halving the sorted list relate to the time complexity of your search feature?"})), deadline=30, engine="objective")
    out = gen.propose(ctx)
    assert out.proposal is None or out.proposal.memory_id is None
    monkeypatch.delenv(intel.ENV_ENGINE, raising=False)
    assert intel.engine_name() == "stage10n" and FL.PROMPT_VERSION == "10.fu8"


def test_the_frozen_benchmark_is_untouched():
    import hashlib
    raw = (EVAL / "stage10f_opportunities_v1.json").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == "59e92f47c50657b53b7c93e80d327046954238af08d1d7fa936def3609ff0737"
    assert len(CASES) == 40 and sorted(OE.load()["classes"]) == sorted(OE.load()["classes"])
