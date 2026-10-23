"""Stage 11R: quality and safety repair of the objective engine. Offline/scripted: these tests prove code behaviour (marker expansion, unsupported-reference detection, final-output checks, objective choice);
they say nothing about what a language model writes. The held-out question sets were written by the same author as the rules (sanity sets, not independent evidence)."""
import copy
import json
import re
from pathlib import Path

import pytest

from src.demo import followup_llm as FL, intel, opportunity_eval as OE, question_pairs_eval as Q
from src.evaluation.providers.mock import MockProvider

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "src" / "demo" / "eval_data"
CASES = {c["id"]: c for c in OE.load()["cases"]}


@pytest.fixture(scope="module")
def eng():
    return OE.offline_engine()


@pytest.fixture(autouse=True)
def _vocab():
    FL.set_vocabulary_source(lambda: [])
    yield
    FL.set_vocabulary_source(None)


def case(eng, id_):
    return OE.build_case(eng, copy.deepcopy(CASES[id_]))[0]


def ctx(**over):
    d = dict(role="Backend Developer", stage="core", question_id="q", question="Explain ACID properties.", topic="Databases", answer="Atomicity means all or nothing.",
             concepts=[{"id": "E1", "label": "atomicity", "tier": "essential", "members": []}, {"id": "E2", "label": "consistency", "tier": "essential", "members": []},
                       {"id": "E3", "label": "sigmoid function", "tier": "essential", "members": []}, {"id": "E4", "label": "isolation", "tier": "essential", "members": []}],
             reference="Atomicity: all or nothing. Consistency: valid state to valid state. Isolation: concurrent transactions do not interfere.")
    d.update(over)
    return FL.Context(**d)


# ------------------------------------------------------------------------------------------------ B. internal markers never reach the candidate, and expanding one never doubles a word
@pytest.mark.parametrize("raw,expected", [
    ("How does E2 consistency ensure that data stays valid?", "How does consistency ensure that data stays valid?"),                  # T02 / N02
    ("How does the logistic regression model use the E3 sigmoid function to get a probability?", "How does the logistic regression model use the sigmoid function to get a probability?"),   # T08
    ("How does consistency (E2) ensure that data stays valid?", "How does consistency ensure that data stays valid?"),
    ("How does [E2] consistency ensure it?", "How does consistency ensure it?"),
    ("How does E2: consistency ensure it?", "How does consistency ensure it?"),
    ("E2 consistency matters how?", "Consistency matters how?"),
    ("How does E-2 fit here?", "How does consistency fit here?"),
    ("How does concept E4 fit here?", "How does isolation fit here?"),
    ("How does e4 fit here?", "How does isolation fit here?"),
    ("How do E2 and E4 differ in a crash?", "How do consistency and isolation differ in a crash?"),
    ("How does E3 sigmoid affect the output?", "How does sigmoid affect the output?"),               # the model's own shorter wording stands; nothing is added
])
def test_marker_expansion_never_duplicates_and_never_leaks(raw, expected):
    out = FL.sanitise_ids(raw, ctx())
    assert out == expected
    assert not FL.adjacent_repeat(out) and not re.search(r"\b[ESGK]\s?-?\d\b", out, re.I)


def test_legitimate_repeats_and_unknown_markers_are_not_rewritten():
    c = ctx(answer="I stored the files in S3 and used a binary tree tree-walk.")
    assert FL.sanitise_ids("How would the S3 bucket matter?", c) == "How would the S3 bucket matter?"          # the candidate said S3
    assert "E9" in FL.sanitise_ids("How does E9 fit?", c)                                                    # not this case's concept: left for the validator to refuse
    assert FL.adjacent_repeat("What happens that that happens?") is None and FL.adjacent_repeat("We had had a plan") is None
    assert FL.adjacent_repeat("How does consistency consistency work") == "consistency"
    assert FL.adjacent_repeat("How does the sigmoid function sigmoid function work") == "sigmoid function"
    assert FL.adjacent_repeat("Compare gradient descent with stochastic gradient descent") is None


def test_validate_checks_the_final_postprocessed_question_not_the_raw_reply():
    base = {"decision": "ask", "skip_reason": "none", "purpose": "probe_concept", "concept_id": "E2", "memory_id": "none"}
    p, why = FL.validate(dict(base, question="How does E2 consistency ensure that data remains valid after a crash?"), ctx())
    assert p is not None and "E2" not in p.question and "consistency consistency" not in p.question, why
    p, why = FL.validate(dict(base, question="How does consistency consistency ensure that data remains valid after a crash?"), ctx())
    assert p is None and "question:duplicated_phrase" in why                                              # a doubled phrase the model itself wrote is refused, not silently edited
    p, why = FL.validate(dict(base, question="How does E9 ensure that data remains valid after a crash?"), ctx())
    assert p is None and "question:id_leak" in why


def test_objective_prompt_shows_no_internal_ids_for_any_benchmark_case(eng):
    for id_, c in CASES.items():
        if c["mode"] != "technical":
            continue
        x = OE.build_case(eng, copy.deepcopy(c))[0]
        obj = intel.plan_objective(x)
        if obj is None:
            continue
        for mode in ("standard", "memory"):
            system, user, _ = intel.build_prompt(x, obj, "n", mode)
            assert not re.search(r"\b[ESGK]\d{1,2}\b", user), (id_, mode)
            assert not re.search(r"\bm\d\b", user), (id_, mode)
    assert intel.OBJ_PROMPT_VERSION == "11.obj5"


def test_the_final_gate_catches_what_slipped_through_and_passes_clean_text():
    c = ctx()
    clean = FL.Proposal("ask", "How would isolation change what two concurrent transfers see?", "probe_concept", ["E4"])
    assert FL.final_gate(clean, c) == []
    for q, code in [("How does E2 consistency ensure it?", "final:id_marker"), ("How does consistency consistency ensure it?", "final:duplicated_phrase"),
                    ("How does it work on the dataset you mentioned?", "final:unsupported_reference")]:
        assert code in FL.final_gate(FL.Proposal("ask", q, "probe_concept", ["E2"]), c)
    p = FL.Proposal("ask", "How does it compare?", "probe_concept", ["E2"], lead="Earlier you said you said you built built a ledger.")
    assert "final:duplicated_phrase" in FL.final_gate(p, c)


# ------------------------------------------------------------------------------------------------ A. unsupported personal references (T09), their paraphrases, supported ones, and cross-session
REF = json.loads((EVAL / "stage11r_reference_pairs_v1.json").read_text(encoding="utf-8"))
REF_CTX = dict(question=REF["base"]["question"], topic=REF["base"]["topic"], answer=REF["base"]["answer"], role="Data Scientist")


def _rctx():
    return FL.Context(stage="core", question_id="q", concepts=[{"id": "E1", "label": "evaluation without labels", "tier": "essential", "members": []}], reference="", **REF_CTX)


@pytest.mark.parametrize("c", [c for c in REF["cases"] if not c["supported"]], ids=lambda c: c["kind"] + ":" + c["q"][:36])
def test_every_unsupported_personal_reference_is_flagged(c):
    assert FL.unsupported_reference(c["q"], _rctx(), "")


@pytest.mark.parametrize("c", [c for c in REF["cases"] if c["supported"]], ids=lambda c: c["kind"] + ":" + c["q"][:36])
def test_genuine_references_to_this_turn_or_the_attributed_statement_are_kept(c):
    assert FL.unsupported_reference(c["q"], _rctx(), REF["base"]["memory"] if c.get("memory") else "") == []


def test_a_reference_backed_only_by_another_sessions_memory_is_unsupported():
    q = "How would your spam classifier change if you had no labelled emails?"
    assert FL.unsupported_reference(q, _rctx(), "") != [], "no attributed statement in this session: 'your spam classifier' is a claim nobody made"
    assert FL.unsupported_reference(q, _rctx(), REF["base"]["memory"]) == []


def test_T09_is_refused_by_both_engines_and_by_the_audit():
    q = "How does unsupervised learning help identify clusters in a dataset like the one you mentioned?"
    c = case(__import__("pytest").importorskip("src.demo.opportunity_eval").offline_engine(), "T09")
    p, why = FL.validate({"decision": "ask", "skip_reason": "none", "question": q, "purpose": "probe_concept", "concept_id": FL.target_concept(c)["id"], "memory_id": "none"}, c)
    assert p is None and any(r.startswith("reference:unsupported") for r in why)
    obj = intel.plan_objective(c)
    assert intel.evaluate_question(q, c, obj).prop is None
    assert "fabricated_memory_reference" in OE.audit(q, c, None, [])


def test_objective_engine_never_shows_a_fabricated_reference_even_when_the_model_repeats_it(eng):
    c = case(eng, "T09")
    calls = []

    def reply(s, u):
        calls.append(u)
        return json.dumps({"question": "How does unsupervised learning help identify clusters in a dataset like the one you mentioned?"})
    out = FL.LLMFollowUpGenerator(MockProvider(reply), deadline=30, engine="objective").propose(c)
    assert out.kind == "fallback" and out.proposal is None and any(r.startswith("reference:unsupported") for r in out.reasons)
    assert len(calls) <= 2
    assert len(calls) == 1 or "did not say" in calls[-1].lower(), "the single retry must tell the model what it may not refer to"


def _engine_with_unsafe_generator(tmp_path, monkeypatch, question, memory_id=None):
    from src.demo.routes import set_engine
    from tests.app.test_stage4a_demo import make_engine
    for v in ("SMART_DEMO_LIVE_MODULAR", "SMART_DEMO_CODE_EVAL", "SMART_CODEEVAL_EXEC"):
        monkeypatch.delenv(v, raising=False)
    e = make_engine(tmp_path)

    class Unsafe:
        """A generator that bypasses validation (as a future bug might): the engine's last gate must still stop it."""
        def propose(self, c):
            return FL.Outcome("llm", FL.Proposal("ask", question, "probe_concept", [c.concepts[0]["id"]] if c.concepts else [], memory_id=memory_id), latency_ms=1.0, model="x", info={"engine": "objective"})
    e._followup_generator = Unsafe()
    set_engine(e)
    return e


@pytest.mark.parametrize("q", ["How does it work for the dataset you mentioned?", "How does consistency consistency matter here?", "How does E2 consistency matter here?"])
def test_the_engine_refuses_an_unsafe_model_question_before_it_is_stored(app_module, tmp_path, monkeypatch, q):
    from src.demo.routes import set_engine
    from tests.app.test_stage9b_interview import create, play
    e = _engine_with_unsafe_generator(tmp_path, monkeypatch, q)
    app_module.app.config["TESTING"] = True
    try:
        with app_module.app.test_client() as c:
            sid = create(c, followup_mode="mock")
            s = play(c, e, sid)
    finally:
        set_engine(None)
    assert all(q != it.get("question") for it in s["questions"]), "an unsafe question must never be persisted"
    assert s["status"] == "finished"


# ------------------------------------------------------------------------------------------------ acceptance and audit cannot contradict each other
def _pool():
    out = []
    for c in REF["cases"]:
        out.append((_rctx(), c["q"], REF["base"]["memory"] if c.get("memory") else ""))
    return out


def test_an_accepted_question_never_carries_an_audit_reference_finding():
    bad = []
    for x, q, mem in _pool():
        mid = "m1" if mem else None
        c = copy.copy(x)
        c.memory = [{"id": "m1", "kind": "project", "text": mem, "quote": mem, "turn": 1, "subject": "a spam classifier", "lead": "Earlier you said " + mem}] if mem else []
        p, why = FL.validate({"decision": "ask", "skip_reason": "none", "question": q, "purpose": "probe_concept", "concept_id": "E1", "memory_id": mid or "none"}, c, "memory" if mem else "standard")
        aud = OE.audit(q, c, mid, ["m1"] if mem else [], None)
        if p is not None and (set(aud) & {"fabricated_memory_reference", "duplicated_phrase"}):
            bad.append((q, aud))
    assert bad == []


def test_acceptance_and_audit_agree_on_every_recorded_real_reply():
    for f in ("stage10n_real_llama3.2_3b_20261021_205846.json", "stage11_objective_real_llama3.2_3b_20261021_221628.json"):
        path = ROOT / "reports" / "stage11_eval" / f
        if not path.exists():
            pytest.skip("recorded real runs are not in this checkout")
        eng = OE.offline_engine()
        for r in json.loads(path.read_text(encoding="utf-8"))["results"][0]["rows"]:
            if r.get("mode") != "technical":
                continue
            x = OE.build_case(eng, copy.deepcopy(CASES[r["id"]]))[0]
            obj = intel.plan_objective(x)
            for d in r.get("debug") or []:
                q = (d.get("question") or "").strip()
                if not q or obj is None:
                    continue
                v = intel.evaluate_question(q, x, obj)
                if v.prop is not None:
                    aud = OE.audit(v.prop.question, x, v.prop.memory_id, [m["id"] for m in x.memory], v.prop.lead)
                    assert not (set(aud) & {"fabricated_memory_reference", "duplicated_phrase", "id_leak"}), (r["id"], q, aud)


# ------------------------------------------------------------------------------------------------ C. the five misses, by cause
def test_T11_plain_compounds_made_of_words_the_candidate_said_are_not_novel():
    allowed = "the network learns its own representations instead of relying on hand designed features"
    assert FL.novel_technical_terms("How do self-learned representations differ?", allowed, "d") == []
    assert FL.novel_technical_terms("How do hand-designed features differ?", allowed, "d") == []
    assert FL.novel_technical_terms("How does the HyperTokenizer9 step relate?", allowed, "d") != []
    assert FL.novel_technical_terms("How does quantum-annealed sampling relate?", allowed, "d") != []


def test_target_is_not_the_topic_the_question_already_named_and_follows_the_stored_work(eng):
    m03 = intel.plan_objective(case(eng, "M03"))
    assert FL._content_tokens(m03.target["label"]) - FL._GENERIC - intel._ABSTRACT - FL._content_tokens("How do you use mocking in unit tests with pytest?"), "M03-type: a concept that is only the question's own topic is not the objective"
    m04 = intel.plan_objective(case(eng, "M04"))
    assert m04.target["label"] == "isolation", "concurrent transactions in the stored work point at isolation, not at consistency"
    assert m04.handle == "your money transfers" and intel.plan_objective(case(eng, "M02")).handle == "your spam classifier"


def test_target_choice_without_memory_keeps_the_first_open_concept(eng):
    c = case(eng, "T02")
    assert intel.plan_objective(c).target["id"] == FL.target_concept(c)["id"]


@pytest.mark.parametrize("q,attributed", [
    ("How would labelled training data matter in your spam classifier?", True),
    ("How would labelled data help the system that sorts incoming mail?", False),
    ("How does supervised learning apply to training a classifier on labelled emails?", False),          # M02-type: not framed as the candidate's own work
])
def test_memory_is_attributed_only_when_the_question_is_about_their_work_and_the_objective(eng, q, attributed):
    c = case(eng, "M02")
    obj = intel.plan_objective(c)
    v = intel.evaluate_question(q, c, obj)
    assert bool(v.prop is not None and v.prop.memory_id) == attributed, (v.reasons, v.prop and v.prop.memory_id)
    if not attributed:
        assert v.prop is None or v.prop.memory_id is None


def test_M07_type_presupposition_and_M06_type_restatement_are_not_credited_as_memory_use(eng):
    c = case(eng, "M07")
    v = intel.evaluate_question("How does your experience with the library catalogue search feature inform your understanding of the time complexity of binary search?", c, intel.plan_objective(c))
    assert v.prop is None or v.prop.memory_id is None
    # 11T: the earlier wording here ("... compare with halving the list in your search feature?") said their feature halves a list, which they never claimed; it is now a negative case
    implied = intel.evaluate_question("How would scanning every record one by one, as a linear search does, compare with halving the list in your search feature?", c, intel.plan_objective(c))
    assert implied.prop is None and "memory:implies_unclaimed_use" in implied.reasons
    ok = intel.evaluate_question("If your search feature scanned every record with a linear search, how would its cost grow with the catalogue size?", c, intel.plan_objective(c))
    assert ok.prop is not None and ok.prop.memory_id, ok.reasons
    c6 = case(eng, "M06")
    v6 = intel.evaluate_question("How does the use of neural networks in your convolutional neural network for tumour detection in scans relate to hierarchical representations?", c6, intel.plan_objective(c6))
    assert v6.prop is None or v6.prop.memory_id is None
    good6 = intel.evaluate_question("How would hierarchical representations show up in your tumour detection model?", c6, intel.plan_objective(c6))
    assert good6.prop is not None and good6.prop.memory_id, good6.reasons


def test_attribution_never_comes_from_word_overlap_alone(eng):
    c = case(eng, "M04")
    obj = intel.plan_objective(c)
    for q in ["Can you tell me more about your money transfers in PostgreSQL billing?", "How is a PostgreSQL billing database for money transfers usually designed?"]:
        v = intel.evaluate_question(q, c, obj)
        assert v.prop is None or v.prop.memory_id is None, (q, v.reasons)


# ------------------------------------------------------------------------------------------------ D. weak wording: premise restatement, stated-value probes, word lists, over-long questions
def test_T02_premise_restatement_is_refused_but_a_scenario_question_is_kept(eng):
    c = case(eng, "T02")
    obj = intel.plan_objective(c)
    bad = intel.evaluate_question("How does consistency ensure that data stays valid after a crash, given that atomicity guarantees that a transaction is fully committed or not at all?", c, obj)
    assert bad.prop is None and any("restates_answer_in_premise" in r or "ignores" in r for r in bad.reasons)
    good = intel.evaluate_question("What could two concurrent transfers see of each other's uncommitted changes without isolation?", c, obj)
    assert good.prop is not None, good.reasons


def test_T06_type_a_wrong_stated_value_is_probed_on_the_case_they_named(eng):
    c = case(eng, "T06")
    obj = intel.plan_objective(c)
    assert obj.kind == "misconception_probe" and obj.stated == "O(n)"
    assert "worst" in obj.stated_words
    side = intel.evaluate_question("What is the order of growth of bubble sort for nearly sorted data?", c, obj)
    assert side.prop is None and "question:sidesteps_stated_value" in side.reasons
    for q in ["How many comparisons would bubble sort make on a list sorted in reverse order?", "What would the worst case cost of bubble sort look like for a list of n elements?"]:
        v = intel.evaluate_question(q, c, obj)
        assert v.prop is not None, (q, v.reasons)
    system, user, _ = intel.build_prompt(c, obj, "n")
    assert "O(n)" in user and "n^2" not in user and "squared" not in user.lower(), "the prompt names the candidate's value only; the curated one is never shown"


def test_M05_type_word_lists_and_overlong_questions_are_refused():
    assert intel._LIST_OF_WORDS.search("How does the concept of probability, function, and weighted relate to maximum likelihood estimation?")
    assert not intel._LIST_OF_WORDS.search("How would you compare precision, recall, and F1 for an imbalanced classifier?")
    assert len(("word " * 40).split()) > intel.MAX_WORDS


def test_valid_complex_vocabulary_and_scenarios_survive(eng):
    for id_, q in [("T03", "How does binary search compare to linear search when the target is not in the sorted list?"),
                   ("T08", "How does logistic regression use the sigmoid function to turn a weighted sum into a probability?")]:
        c = case(eng, id_)
        v = intel.evaluate_question(q, c, intel.plan_objective(c))
        assert v.prop is not None, (id_, v.reasons)


# ------------------------------------------------------------------------------------------------ E. false acceptance and false rejection on the pair sets (old vs repaired is in scripts/stage11r_validator_compare.py)
def _pairs():
    out = {}
    eng_ = OE.offline_engine()
    cases = {c["id"]: c for c in OE.load()["cases"]}
    for path in (EVAL / "stage10n_question_pairs_v1.json", EVAL / "stage11r_question_pairs_v1.json"):
        for it in json.loads(path.read_text(encoding="utf-8"))["items"]:
            x = Q._context(it, eng_, cases)
            obj = intel.plan_objective(x)
            s = out.setdefault(it["src"], {"FR": 0, "FA": 0, "good": 0, "bad": 0})
            for kind, qs in (("good", it["good"]), ("bad", [b["q"] for b in it["bad"]])):
                for q in qs:
                    ok = obj is not None and intel.evaluate_question(q, x, obj).prop is not None
                    s[kind] += 1
                    s["FR" if kind == "good" else "FA"] += (not ok) if kind == "good" else ok
    return out


def test_false_rejection_and_false_acceptance_do_not_regress_on_any_pair_set():
    s = _pairs()
    budget = {"fixture": (1, 2), "holdout": (5, 0), "holdout2": (5, 0), "holdout3": (2, 1)}     # (max false rejections, max false acceptances) as measured; a regression fails the test
    for src, (fr, fa) in budget.items():
        assert s[src]["FR"] <= fr and s[src]["FA"] <= fa, (src, s[src])
    assert s["holdout3"]["bad"] >= 25 and s["holdout3"]["good"] >= 15


# ------------------------------------------------------------------------------------------------ F. integration: the baseline engine and the frozen benchmark are untouched
def test_frozen_benchmark_and_default_engine_are_unchanged(monkeypatch):
    import hashlib
    raw = (EVAL / "stage10f_opportunities_v1.json").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == "59e92f47c50657b53b7c93e80d327046954238af08d1d7fa936def3609ff0737"
    monkeypatch.delenv(intel.ENV_ENGINE, raising=False)
    assert intel.engine_name() == "stage10n" and FL.PROMPT_VERSION == "10.fu8"


def test_scripted_stand_in_through_the_objective_engine_attributes_memory_by_code(eng, monkeypatch):
    monkeypatch.setenv(intel.ENV_ENGINE, "objective")
    n, grounded = 0, 0
    for id_ in ("M01", "M02", "M03", "M04", "M05", "M06", "M07"):
        c = case(eng, id_)
        o = OE.scripted_generator("well_behaved").propose(c)
        n += 1
        if o.proposal is not None and o.proposal.memory_id:
            grounded += 1
    assert n == 7 and grounded >= 3
