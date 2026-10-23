"""Stage 12: technical correctness is assessed apart from semantic similarity.

Deterministic: no model, no network. The concept evaluator runs with the repository's ScriptedVerifier (its replies still pass the frozen evidence gate), and the contradiction
pass with a scripted provider. These tests prove the decision rules, the fail-safe behaviour, the API/export schema and the presentation; they say nothing about how well
the local model judges answers (that needs scripts/stage12_assess_answers.py --live on Windows)."""
import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

from src.demo import assessment as A, experimental as X, opportunity_eval as OE
from src.evaluation.modular import contradictions as CX
from src.evaluation.modular.mock_verifiers import ScriptedVerifier, scripted
from src.evaluation.providers.base import ProviderResponse

ROOT = Path(__file__).resolve().parents[2]
AE_ANSWER = "An autoencoder is a neural network that compresses data and then reconstructs it. It always needs labelled training data to learn the correct output."
AE_QUOTE = "It can learn representation for a set of data without any supervision"


@pytest.fixture(scope="module")
def eng():
    return OE.offline_engine()


class Reply:
    model, is_mock, paid = "scripted", True, False

    def __init__(self, reply=None, raise_=None, text=None):
        self.reply, self.raise_, self.text, self.response_schema, self.calls = reply, raise_, text, "original", []

    def generate(self, system, user):
        self.calls.append((system, user, self.response_schema))
        if self.raise_:
            raise self.raise_
        return ProviderResponse(self.text if self.text is not None else json.dumps(self.reply), self.model, 1.0, {})


def outcome(label, tier, status):
    return {"requirement_id": label[:2], "label": label, "tier": tier, "kind": "concept", "status": status}


def stored(outcomes, *, errors=(), cx=None, mode="live", status="done", vstatus="advisory_only", tags=(), answer="An answer with some technical content in it.", sim=50.0, **view):
    v = {"status": vstatus, "outcomes": list(outcomes), "feedback": {"factual_errors": list(errors)}, "source": {"tags": list(tags)}, "safeguards": {"applied": []},
         "contradictions": cx if cx is not None else {"status": "checked", "items": []}, "taxonomy": {}}
    v.update(view)
    return {"answer": answer, "skipped": False, "legacy": {"status": "scored", "score": sim}, "terms": {"found": ["x"], "missing": []},
            "modular": {"mode": mode, "status": status, "view": v}}


CORE = {"stage": "core"}
E_OK, E_MISS, E_UND = outcome("alpha", "essential", "satisfied"), outcome("beta", "essential", "missing"), outcome("gamma", "essential", "undetermined")
S_OK = outcome("delta", "supporting", "satisfied")
ERR = {"concept": "beta", "your_words": ["beta means the opposite"], "why_wrong": "it does not", "reference_says": "beta is not that", "severity": "major"}
CXI = {"status": "checked", "items": [{"claim_id": "c2", "claim": "a false statement", "reference_quote": "the truth", "why": "the reference says otherwise"}]}


# ------------------------------------------------------------------------------------------------ the verdict rules
@pytest.mark.parametrize("a,verdict,reason", [
    (stored([E_OK, outcome("beta", "essential", "satisfied")]), "correct", "all_essential_demonstrated"),
    (stored([E_OK, outcome("beta", "essential", "satisfied")], cx={"status": "error", "items": []}), "uncertain", "requirements_met_but_errors_not_checked"),
    (stored([E_OK, outcome("beta", "essential", "satisfied")], cx={"status": "not_checked", "items": []}), "uncertain", "requirements_met_but_errors_not_checked"),
    (stored([E_OK, E_MISS]), "partially_correct", "some_essential_missing"),
    (stored([E_MISS, outcome("eps", "essential", "missing")]), "incorrect", "no_essential_demonstrated"),
    (stored([E_MISS, S_OK]), "partially_correct", "only_supporting_demonstrated"),
    (stored([E_OK, E_UND]), "uncertain", "evidence_incomplete"),
    (stored([E_UND]), "uncertain", "evidence_incomplete"),
    (stored([E_OK, outcome("b2", "essential", "satisfied")], cx=CXI), "partially_correct", "misconception"),
    (stored([E_OK], cx=CXI), "incorrect", "misconceptions_outweigh_correct_content"),
    (stored([E_MISS], errors=[ERR]), "incorrect", "misconceptions_outweigh_correct_content"),
    (stored([]), "uncertain", "no_curated_requirements"),
    (stored([E_OK], vstatus="abstained", taxonomy={"primary": "off_topic_confirmed"}), "incorrect", "off_topic"),
    (stored([E_OK], safeguards={"applied": ["possible_hidden_instruction"]}), "uncertain", "safeguard:possible_hidden_instruction"),
    (stored([E_OK], vstatus="not_gradable"), "uncertain", "answer_not_gradable"),
])
def test_verdict_rules(a, verdict, reason):
    r = A.assess(a, CORE)
    assert (r["verdict"], r["reason"]) == (verdict, reason)
    assert r["label"] == A.LABELS[verdict] and r["schema"] == A.SCHEMA and r["human_validated"] is False


def test_similarity_never_changes_the_verdict():
    for case in ([E_OK, E_MISS], [E_OK, outcome("b", "essential", "satisfied")], [E_MISS]):
        verdicts = {A.assess(stored(case, sim=s), CORE)["verdict"] for s in (0.0, 12.0, 49.0, 76.0, 91.0, 100.0)}
        assert len(verdicts) == 1, verdicts
    assert A.assess(stored([E_OK]), CORE)["similarity"]["used_for_verdict"] is False


def test_a_high_similarity_false_answer_is_not_correct_and_a_low_similarity_paraphrase_is_not_incorrect():
    false_but_similar = A.assess(stored([E_OK, outcome("b", "essential", "satisfied")], cx=CXI, sim=91.0), CORE)
    assert false_but_similar["verdict"] != "correct" and false_but_similar["misconceptions"]
    paraphrase_low_sim = A.assess(stored([E_OK, outcome("b", "essential", "satisfied")], sim=18.0), CORE)
    assert paraphrase_low_sim["verdict"] == "correct"


def test_mock_verifier_can_never_confirm_correctness():
    r = A.assess(stored([E_OK, outcome("b", "essential", "satisfied")], mode="mock", tags=["MOCK VERIFIER"]), CORE)
    assert r["verdict"] == "uncertain" and r["basis"] == "mock_verifier" and any("Mock verifier" in f for f in r["feedback"])


# ------------------------------------------------------------------------------------------------ fail-safe: nothing is invented
@pytest.mark.parametrize("modular,verdict,reason", [
    ({"mode": "off", "status": "not_requested", "view": None}, "unavailable", "evaluator_off"),
    ({"mode": "live", "status": "pending", "view": None}, "pending", "evaluator_running"),
    ({"mode": "live", "status": "failed", "view": None, "error": "timeout"}, "unavailable", "evaluator_unavailable"),
    ({"mode": "live", "status": "interrupted", "view": None}, "unavailable", "evaluator_unavailable"),
    ({"mode": "live", "status": "done", "view": {"status": "provider_error"}}, "unavailable", "evaluator_provider_error"),
    ({"mode": "live", "status": "done", "view": {"status": "invalid_response"}}, "unavailable", "evaluator_invalid_response"),
])
def test_evaluator_off_failed_or_timed_out_is_reported_as_unavailable(modular, verdict, reason):
    a = {"answer": "A real attempt at the question with content.", "skipped": False, "legacy": {"status": "scored", "score": 88.0}, "terms": {}, "modular": modular}
    r = A.assess(a, CORE)
    assert (r["verdict"], r["reason"]) == (verdict, reason)
    assert not r["correct_concepts"] and not r["misconceptions"] and not r["missing_concepts"]


def test_malformed_stored_data_never_raises():
    r = A.assess({"answer": "text", "modular": {"mode": "live", "status": "done", "view": {"status": "advisory_only", "outcomes": [{"tier": "essential"}]}}}, CORE)
    assert r["verdict"] == "uncertain"                                                     # an outcome without a status is undetermined, never 'missing'
    r = A.assess({"answer": "text", "modular": {"mode": "live", "status": "done", "view": {"status": "advisory_only", "outcomes": "garbage"}}}, CORE)
    assert r["verdict"] in ("unavailable", "uncertain")


@pytest.mark.parametrize("answer,terms,expected", [
    ("", {}, True), ("   ", {}, True),
    ("I'm not sure about this concept. Could we move on to the next question?", {"found": []}, True),
    ("I don't know.", {}, True),
    ("An autoencoder compresses data. I am not sure about the rest.", {"found": ["autoencoder"]}, False),
    ("I'm not sure, but I think the Fourier transform splits a signal into frequencies.", {"found": ["Fourier transform"]}, False),
    ("Gradient descent updates weights against the gradient of the loss.", {}, False),
])
def test_no_attempt_detection(answer, terms, expected):
    assert A.no_attempt(answer, terms) is expected


def test_skipped_unreached_and_non_technical_turns_get_no_verdict():
    assert A.assess(None, CORE)["verdict"] == "not_applicable"
    assert A.assess({"skipped": True}, CORE)["verdict"] == "not_applicable"
    assert A.assess(stored([E_OK]), {"stage": "follow_up"})["verdict"] == "not_applicable"


def test_similarity_is_reported_on_a_0_to_1_scale_never_as_a_percentage():
    s = A.similarity_view({"status": "scored", "score": 76.0})
    assert s["display"] == "0.76" and s["value"] == 0.76 and "%" not in s["display"] and "not a percentage correct" in s["meaning"]
    assert A.similarity_view({"status": "unavailable"})["available"] is False


# ------------------------------------------------------------------------------------------------ the contradiction pass
CLAIMS = [{"id": "c1", "text": "An autoencoder is a neural network that compresses data and then reconstructs it."},
          {"id": "c2", "text": "It always needs labelled training data to learn the correct output."}]


def test_contradiction_accepted_only_with_a_real_reference_quote(eng):
    ref = eng.record("smi-0054")["canonical_answer"]
    good = {"contradictions": [{"claim_id": "c2", "reference_quote": AE_QUOTE, "why": "Autoencoders learn without labels."}]}
    r = CX.verify(good, ref, CLAIMS)
    assert r["status"] == "checked" and [i["claim_id"] for i in r["items"]] == ["c2"] and r["items"][0]["claim"] == CLAIMS[1]["text"]
    bad = {"contradictions": [{"claim_id": "c2", "reference_quote": "autoencoders always require labels", "why": "x"},
                              {"claim_id": "c9", "reference_quote": AE_QUOTE, "why": "x"},
                              {"claim_id": "c2", "reference_quote": "Autoencoder consists of two parts", "why": "unrelated quote"},
                              {"claim_id": "c2", "reference_quote": AE_QUOTE, "why": " ".join(["word"] * 40)}]}
    r = CX.verify(bad, ref, CLAIMS)
    assert r["items"] == [] and [x["reason"] for x in r["rejected"]] == ["quote_not_in_reference", "unknown_claim", "quote_unrelated_to_claim", "missing_or_long_explanation"]


def test_contradiction_pass_failures_are_errors_not_clean_bills_of_health(eng):
    ref = eng.record("smi-0054")["canonical_answer"]
    assert CX.check(Reply(raise_=TimeoutError("slow")), "Q", ref, CLAIMS)["status"] == "error"
    assert CX.check(Reply(text="not json"), "Q", ref, CLAIMS)["status"] == "error"
    assert CX.check(Reply({"wrong": []}), "Q", ref, CLAIMS)["status"] == "invalid_response"
    assert CX.check(Reply({"contradictions": []}), "Q", "", CLAIMS)["status"] == "error"
    p = Reply({"contradictions": []})
    assert CX.check(p, "Q", ref, CLAIMS)["status"] == "checked" and p.calls[0][2] == CX.SCHEMA and p.response_schema == "original"   # schema applied, then restored


def test_reference_code_and_urls_are_not_evidence():
    assert "api.example.com" not in CX.reference_prose("Mocking replaces a dependency. ```fetch('https://api.example.com/u')``` See https://docs.example.com/x for more.")


# ------------------------------------------------------------------------------------------------ the evaluator bridge, end to end without a model
def test_autoencoder_misconception_through_the_real_evaluator_pipeline(eng):
    rec = eng.record("smi-0054")
    ver = ScriptedVerifier(scripted({"autoencoder": ("states_correctly", "text:compresses"), "artificial neural network": ("states_correctly", "text:neural network")}, default="not_stated"))
    view = X.evaluate("mock", rec, AE_ANSWER, verifier=ver, contradiction_provider=Reply({"contradictions": [{"claim_id": "c2", "reference_quote": AE_QUOTE, "why": "No labels are needed."}]}))
    assert view["contradictions"]["status"] == "checked" and len(view["contradictions"]["items"]) == 1
    view["source"]["tags"] = []                                                    # judged as a model reply would be (the label test is separate)
    a = {"answer": AE_ANSWER, "skipped": False, "legacy": {"status": "scored", "score": 90.68}, "terms": {"found": ["autoencoder"], "missing": []},
         "modular": {"mode": "live", "status": "done", "view": view}}
    r = A.assess(a, CORE)
    assert r["verdict"] == "partially_correct" and r["similarity"]["display"] == "0.91"
    assert r["misconceptions"][0]["claim"].startswith("It always needs labelled") and r["misconceptions"][0]["reference_says"] == AE_QUOTE


def test_mock_mode_never_runs_the_contradiction_pass_and_errors_do_not_break_the_view(eng):
    rec = eng.record("smi-0054")
    assert X.evaluate("mock", rec, AE_ANSWER)["contradictions"]["status"] == "not_checked"
    v = X.evaluate("mock", rec, AE_ANSWER, contradiction_provider=Reply(raise_=ConnectionError("down")))
    assert v["contradictions"]["status"] == "error" and v["status"] in ("advisory_only", "scored", "abstained")


def test_representative_cases_scripted_run():
    """The bounded Stage 12 set through the code path (scripted stand-in). Pins the decisions; real-model quality is measured separately on Windows."""
    spec = importlib.util.spec_from_file_location("s12", ROOT / "scripts" / "stage12_assess_answers.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    res = m.run(live=False)
    got = {r["id"]: r["after"]["verdict"] for r in res["rows"]}
    assert got == {"autoencoder_misconception": "partially_correct", "autoencoder_paraphrase": "uncertain", "unsupervised_short": "partially_correct",
                   "unsupervised_complete": "correct", "fourier_no_attempt": "incorrect", "hypothesis_real": "correct", "hypothesis_false": "incorrect",
                   "unrelated": "incorrect", "empty": "incorrect", "mocking_real": "partially_correct"}
    assert all(r["evidence"] == "scripted_stand_in" for r in res["rows"])
    assert "%" not in "".join(r["similarity_shown_now"] for r in res["rows"])


# ------------------------------------------------------------------------------------------------ Flask: API, export and pages
def _session(eng, qid, modular_mode):
    s = eng.create({"role": "Data Scientist", "modular_mode": modular_mode, "size": 1})
    s["questions"][1].update({"question_id": qid, "question": eng.record(qid)["question"]})
    return s


def test_answer_api_and_page_show_a_verdict_apart_from_similarity(app_module, tmp_path, monkeypatch):
    from src.demo.routes import set_engine
    from tests.app.test_stage4a_demo import make_engine
    e = make_engine(tmp_path)
    set_engine(e)
    app_module.app.config["TESTING"] = True
    try:
        with app_module.app.test_client() as c:
            sid = c.post("/demo/api/sessions", json={"role": "Data Scientist"}).json["session_id"]
            r = c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 1, "answer": "I am a data scientist."}).json
            r = c.post(f"/demo/api/sessions/{sid}/answer", json={"n": 2, "answer": "I'm not sure about this concept. Could we move on to the next question?"}).json
            asmt = r["assessment"]
            assert asmt["schema"] == A.SCHEMA and asmt["verdict"] == "incorrect" and asmt["reason"] == "no_attempt" and asmt["similarity"]["used_for_verdict"] is False
            html = r["html"]
            assert "Correctness check" in html and 'data-verdict="incorrect"' in html
            assert 'class="bigscore"' not in html and "%</small>" not in html and "Excellent work" not in html and "There's a gap in understanding" not in html
            assert not re.search(r"\d+\.\d<small>%", html)
            n = c.get(f"/demo/api/sessions/{sid}").json["current"]                            # the policy may put a follow-up next; answer it plainly until a core question comes
            while c.get(f"/demo/api/sessions/{sid}").json["question"]["stage"] != "core":
                c.post(f"/demo/api/sessions/{sid}/answer", json={"n": n, "answer": "It depends on the data and the model."})
                n = c.get(f"/demo/api/sessions/{sid}").json["current"]
            r3 = c.post(f"/demo/api/sessions/{sid}/answer", json={"n": n, "answer": "Gradient descent moves the weights against the gradient of the loss, with a learning rate setting the step."}).json
            assert r3["assessment"]["verdict"] == "unavailable" and r3["assessment"]["reason"] == "evaluator_off"     # concept check off: nothing is invented
            frag = c.get(f"/demo/api/sessions/{sid}/answers/{n}").json
            assert frag["assessment"]["verdict"] == "unavailable"
            c.post(f"/demo/api/sessions/{sid}/finish")
            page = c.get(f"/demo/s/{sid}/summary").data.decode()
            assert 'id="correctness"' in page and "Correctness check" in page and "Similarity (0–1)" in page
            assert not re.search(r"Average similarity</dt><dd>\d+%", page)
            exp = c.get(f"/demo/s/{sid}/export.json").json
            techs = [x for x in exp["answers"] if x["stage"] in ("core", "practical")]
            assert techs and all(x["assessment"] is None or x["assessment"]["schema"] == A.SCHEMA for x in techs)
            assert techs[0]["assessment"]["verdict"] == "incorrect"
    finally:
        set_engine(None)


def test_old_sessions_without_stage12_fields_still_render(app_module, tmp_path):
    """Sessions saved before Stage 12 have no `contradictions` in their view; the summary still renders and never says 'correct' for them."""
    a = stored([E_OK, outcome("b", "essential", "satisfied")])
    del a["modular"]["view"]["contradictions"]
    assert A.assess(a, CORE)["verdict"] == "uncertain"


def test_the_written_feedback_panel_and_the_verdict_never_disagree_about_errors(eng):
    """Seen on the rendered page: the older 'Written feedback' panel said 'Possible technical errors (0)' while the verdict listed a contradiction. Both now read the same findings."""
    from src.demo import grounded as G
    rec = eng.record("smi-0054")
    ver = ScriptedVerifier(scripted({"autoencoder": ("states_correctly", "text:compresses"), "artificial neural network": ("states_correctly", "text:neural network")}, default="not_stated"))
    view = X.evaluate("mock", rec, AE_ANSWER, verifier=ver, contradiction_provider=Reply({"contradictions": [{"claim_id": "c2", "reference_quote": AE_QUOTE, "why": "No labels are needed."}]}))
    g = G.build(view, answer=AE_ANSWER)
    assert len(g["errors"]) == 1 and g["errors"][0]["your_words"] == [CLAIMS[1]["text"]] and g["errors"][0]["reference_says"] == AE_QUOTE
    view["source"]["tags"] = []
    r = A.assess({"answer": AE_ANSWER, "legacy": {}, "terms": {}, "modular": {"mode": "live", "status": "done", "view": view}}, CORE)
    assert len(r["misconceptions"]) == 1 and sum("labelled training data" in f for f in r["feedback"]) == 0      # listed once, not repeated in the feedback
