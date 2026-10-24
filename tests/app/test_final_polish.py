"""Final pre-release polish (23 Oct 2026): candidate-facing wording, redundant follow-ups, the summary's feedback and the PDF when the correctness check is OFF.

Deterministic tests only (stand-in scorer, no model). They pin behaviour found in a real manual Data Scientist interview: robotic transitions, engineering language in the
conversation, a follow-up that repeated an answer ("How would '== vs is' come into play in what you described?"), a summary that listed 'missing' terms the candidate had
explained in other words, and a PDF made of repeated 'Not assessed' panels and '0/0 judged correct'."""
import re

import pytest
from reportlab import rl_config

from report_delivery.pdf_generator import build_pdf
from src.demo import assessment as AS, insights as INS, interview as I, pdf_report
from tests.app.test_stage9a_product_ui import c, eng, run_interview, start_bare, _session  # noqa: F401  (fixtures)

IS_VS_EQ = ("`is` checks identity: whether two names point at the same object in memory, while `==` compares the values. For example a = [1, 2] and b = [1, 2] give a == b True but "
            "a is b False. Small integers and None are cached, which is why `is None` is the usual way to test for it.")
REC = {"question_id": "q-is", "key_concepts": ["== vs is", "identity vs equality", "mutable objects", "None comparison"], "topic": "Core language"}
PARENT = {"question_id": "q-is", "domain": "Python", "topic": "Core language", "difficulty": "Easy", "question": "What is the difference between == and is?", "stage": I.CORE}


# ------------------------------------------------------------------------------------------------ 1. interview wording and layout
@pytest.mark.parametrize("topic,phrase", [("Core language", "core language"), ("NLP fundamentals", "NLP fundamentals"), ("SQL fundamentals", "SQL fundamentals"), ("Hypothesis testing and A/B testing", "hypothesis testing and A/B testing"),
                                          ("ML in production", "ML in production"), ("", "the next area")])
def test_topic_labels_read_naturally_inside_a_sentence(topic, phrase):
    assert I.topic_phrase(topic) == phrase


def test_transitions_are_natural_for_every_bank_topic():
    from pathlib import Path
    import csv
    topics = {r["topic"] for r in csv.DictReader(open(str(Path(__file__).resolve().parents[2] / "data/curated/v5/curated_questions.csv"), encoding="utf8"))}
    assert len(topics) > 50
    seen = set()
    for t in topics:
        for k in range(len(I._CORE_LEADS)):
            lead = I.lead_in({"stage": I.CORE, "topic": t, "domain": "x"}, k)
            seen.add(lead)
            assert lead.endswith(".") and "Switching topics" not in lead and "Moving on to" not in lead and ":" not in lead
            assert I.topic_phrase(t) in lead and "  " not in lead
            assert not re.search(r"\bnlp\b|\bsql\b|\bml\b", lead), lead                       # acronyms keep their capitals
    assert any("Core language".lower() in x for x in seen) and len({x.split(" ")[0] for x in seen}) >= 3


def test_first_core_question_and_other_stages_keep_their_lead_ins():
    assert I.lead_in({"stage": I.CORE, "topic": "Core language"}, 0, first_core=True) == "Thanks, that is helpful context. Now the technical part, starting with core language."
    assert I.lead_in({"stage": I.FOLLOW_UP}, 0) == "Thanks. One follow-up on that." and I.lead_in({"stage": I.INTRO}, 0) == ""


def _without_details(html: str) -> str:
    return re.sub(r"<details.*?</details>", "", html, flags=re.S)


def test_provenance_is_out_of_the_conversation_but_still_available(c):
    sid = start_bare(c, intro=True)
    html = c.get(f"/demo/s/{sid}").get_data(as_text=True)
    visible = _without_details(html)
    for engineering in ("Vetted bank question chosen by the interview policy", "Planned question from the curated bank", "Deterministic follow-up from the curated key concepts"):
        assert engineering not in visible
    assert "About this question" in html and "Planned question from the curated bank" in html                     # preserved in the optional details


def test_conversational_box_for_ordinary_questions_and_editor_only_for_code(c):
    sid = start_bare(c, intro=False)
    html = c.get(f"/demo/s/{sid}").get_data(as_text=True)                                                       # the introduction: not a code question
    assert re.search(r'<div class="ed-bar" hidden>', html) and 'class="composer"' in html and 'id="gutter" aria-hidden="true" hidden' in html and "answer.txt" in html
    assert 'data-code="0"' in html and 'wrap="off"' not in html
    css = open(I.__file__.replace("interview.py", "static/app.css"), encoding="utf8").read()
    assert ".ed-bar[hidden]" in css and ".composer:not(.is-code) .editor" in css
    js = open(I.__file__.replace("interview.py", "static/demo.js"), encoding="utf8").read()
    assert "eb.hidden = !code" in js                                                                           # the editor chrome follows the question type when the next prompt arrives


# ------------------------------------------------------------------------------------------------ 2. follow-ups
@pytest.mark.parametrize("concept,covered", [("== vs is", True), ("identity vs equality", False), ("mutable objects", False), ("garbage collection", False),
                                             ("None comparison", True), ("", True)])
def test_concepts_the_answer_already_discusses_are_recognised_without_the_exact_phrase(concept, covered):
    assert I.concept_covered_loosely(concept, IS_VS_EQ) is covered


def test_the_reported_redundant_followup_is_gone():
    assert I.followup_item(2, PARENT, REC, IS_VS_EQ, used=0) is None
    # the exact-phrase check alone would have asked about it (this is what happened in the manual interview)
    assert "== vs is" in I.term_check(REC, IS_VS_EQ)["missing"]


def test_a_missing_idea_still_gets_a_followup_and_existing_limits_hold():
    ans = "It compares two objects and tells you whether they are the same thing, I use it for None checks all the time in my code."
    fu = I.followup_item(2, PARENT, {**REC, "key_concepts": ["garbage collection", "reference counting"]}, ans, used=0)
    assert fu and fu["followup_kind"] == "curated_key_concept" and fu["concept"] in ("garbage collection", "reference counting") and fu["provenance"]["llm"] is False
    assert I.followup_item(2, PARENT, REC, "x " * 3, used=0)["followup_kind"] == "expand_short"                  # a very short answer still gets the fixed prompt
    assert I.followup_item(2, PARENT, {**REC, "key_concepts": ["garbage collection"]}, ans, used=I.MAX_FOLLOWUPS) is None
    assert I.followup_item(2, {**PARENT, "stage": I.FOLLOW_UP}, REC, ans, used=0) is None


def test_an_answer_covering_most_of_the_ideas_gets_no_followup_even_with_unmatched_wording():
    rec = {**REC, "key_concepts": ["identity vs equality", "reference semantics", "interning", "singleton comparison", "memory address"]}
    ans = ("Identity asks whether both names refer to the same object, equality asks whether the values are the same. Small integers are interned so the identity test can look surprising, "
           "and for a singleton like None you compare identity. The memory address is what identity is about.")
    assert I.followup_item(2, PARENT, rec, ans, used=0) is None


def test_coverage_check_is_deterministic_and_makes_no_model_call(monkeypatch):
    import socket

    def boom(*a, **k):
        raise AssertionError("network used")
    monkeypatch.setattr(socket.socket, "connect", boom)
    assert I.followup_item(2, PARENT, REC, IS_VS_EQ, used=0) is None


# ------------------------------------------------------------------------------------------------ 3. summary feedback
def _answered(text, topic="Core language", n_terms=("== vs is", "mutable objects")):
    return {"n": 2, "skipped": False, "answer": text, "elapsed_s": 40, "legacy": {"status": "scored", "score": 62.0}, "modular": {"status": "not_requested", "view": None},
            "terms": {"found": [], "missing": list(n_terms)}}


def _sess(answer_a, answer_b=None, skip_b=False):
    qs = [{"stage": "core", "question_id": "a", "domain": "Python", "topic": "Core language", "difficulty": "Easy", "question": "What is the difference between == and is?"},
          {"stage": "core", "question_id": "b", "domain": "Machine Learning", "topic": "Neural network fundamentals", "difficulty": "Medium", "question": "What is a neural network?"}]
    ans = [_answered(answer_a), {"n": 3, "skipped": True, "answer": "", "legacy": {"status": "skipped", "score": None}} if skip_b else _answered(answer_b or "x", "Neural network fundamentals", ())]
    return {"id": "demo_x", "status": "finished", "config": {"role": "Data Scientist", "modular_mode": "off"}, "questions": qs, "answers": ans}


def test_observations_state_facts_and_never_list_missing_terms():
    obs = INS.observations(_sess(IS_VS_EQ, "It is layers of units."))
    text = " ".join(o["text"] for o in obs)
    assert "== vs is" not in text and "mutable objects" not in text and "not found" not in text.lower() and "not used" not in text.lower()
    assert obs[0]["text"].startswith("You wrote ") and "included an example" in obs[0]["text"] and "included an example" not in obs[1]["text"]


def test_practice_prompts_follow_recorded_facts_not_missing_terms():
    s = _sess(IS_VS_EQ, "It is layers of units.")
    p = INS.practice_prompts(s)
    assert [x["n"] for x in p] == [2] and "5 words" in p[0]["detail"] and p[0]["text"] == "Neural network fundamentals"
    areas = INS.improvement_areas(s)
    assert [a["source"] for a in areas] == ["practice"] and "== vs is" not in repr(areas)
    nothing = INS.improvement_areas(_sess(IS_VS_EQ, IS_VS_EQ))
    assert nothing == []


def test_skipped_questions_are_listed_apart_and_never_as_weaknesses():
    s = _sess(IS_VS_EQ, skip_b=True)
    assert [(x["n"], x["detail"]) for x in INS.skipped_questions(s)] == [(2, "skipped")]
    assert all(a["source"] != "session" for a in INS.improvement_areas(s)) and not any("skipped" in repr(a["items"]) for a in INS.improvement_areas(s))
    assert [o["n"] for o in INS.observations(s)] == [1]                                                       # nothing is 'observed' about a skipped answer


def test_term_diagnostics_separate_other_wording_from_no_sign():
    d = INS.term_diagnostics(_sess(IS_VS_EQ))
    assert d[0]["other_words"] == ["== vs is"] and d[0]["no_sign"] == ["mutable objects"] and d[0]["written"] == []


def test_summary_page_has_no_missing_keyword_lists_but_keeps_optional_diagnostics(c):
    sid = run_interview(c, text="Overfitting means the model memorises noise in the training data, for example a deep tree that fits every training row.", skip=(2,))
    html = c.get(f"/demo/s/{sid}/summary").get_data(as_text=True)
    visible = _without_details(html)
    for needle in ("Key terms not found", "not used:", "Key terms from the question bank that your answer did not use", "Lowest similarity to the reference answer"):
        assert needle not in visible and needle not in html
    for needle in ("What I noticed in your answers", "Areas for future practice", "Skipped or not reached", "not counted as weaknesses", "Correctness was not checked"):
        assert needle in html
    assert "Optional: exact key-term check" in html and "not a mistake" in html
    assert 'class="area session"' in html


def test_correctness_stays_off_by_default_in_the_summary(c):
    sid = run_interview(c)
    s = c.application.extensions["demo_engine"].get(sid) if "demo_engine" in c.application.extensions else None
    html = c.get(f"/demo/s/{sid}/summary").get_data(as_text=True)
    assert "Correctness was not checked" in html and "Correct</dt>" not in html and "Partially correct</dt>" not in html
    assert s is None or all((a or {}).get("modular", {}).get("mode", "off") == "off" for a in s["answers"])


# ------------------------------------------------------------------------------------------------ 4. PDF
def _pdf_text(report, monkeypatch):
    monkeypatch.setattr(rl_config, "pageCompression", 0)
    return build_pdf(report)


def _build(s, answered, skipped):
    return pdf_report.build(s, {"answered": answered, "skipped": skipped, "unanswered": 0, "followups": 1})


def test_pdf_with_correctness_off_is_one_compact_report(monkeypatch):
    s = _sess(IS_VS_EQ, skip_b=True)
    rep = _build(s, 1, 1)
    assert "overview" in rep and "correctness" not in rep
    pdf = _pdf_text(rep, monkeypatch)
    assert pdf.count(b"Correctness not assessed") == 1 and b"Not assessed" not in pdf
    for banned in (b"0/0", b"0 / 0", b"judged correct", b"CORRECTNESS FEEDBACK", b"Overall score", b"Judged correct"):
        assert banned not in pdf
    assert b"not a grade" in pdf and b"TOPICS COVERED" in pdf and b"WHAT WE NOTICED IN YOUR ANSWERS" in pdf
    assert b"NOT COUNTED AS WEAKNESSES" in pdf and b"Neural network fundamentals" in pdf
    assert not re.search(rb"\d+\.\d%", pdf)                                                                   # similarity is 0-1, never a percentage
    assert len(re.findall(rb"/Type /Page\b(?!s)", pdf)) == 1                                                   # one page for a short interview
    assert b"== vs is" not in pdf and b"mutable objects" not in pdf                                          # no missing-keyword list in the report


def test_pdf_overview_labels_similarity_as_not_a_grade_and_omits_it_when_unavailable(monkeypatch):
    s = _sess(IS_VS_EQ, "x")
    assert b"Similarity: 0.62" in _pdf_text(_build(s, 2, 0), monkeypatch)
    for a in s["answers"]:
        a["legacy"] = {"status": "unavailable"}
    pdf = _pdf_text(_build(s, 2, 0), monkeypatch)
    assert b"Similarity:" not in pdf and b"Correctness not assessed" in pdf


def test_pdf_with_correctness_on_still_renders_assessments_safely(monkeypatch):
    s = _sess(IS_VS_EQ, "Neural networks are layers of units.", skip_b=False)
    view = {"status": "advisory_only", "outcomes": [{"requirement_id": "E1", "label": "alpha", "tier": "essential", "kind": "concept", "status": "satisfied"}],
            "feedback": {"factual_errors": []}, "source": {"tags": []}, "safeguards": {"applied": []}, "contradictions": {"status": "checked", "items": [
                {"claim": "It <always> needs & uses labels.", "why": "x", "reference_quote": "without any supervision"}]}, "taxonomy": {}}
    s["answers"][0]["modular"] = {"mode": "live", "status": "done", "view": view}
    rep = _build(s, 2, 0)
    assert "correctness" in rep and rep["correctness"]["assessed"] >= 1
    pdf = _pdf_text(rep, monkeypatch)
    assert b"CORRECTNESS FEEDBACK" in pdf and b"Check this statement" in pdf and b"labels" in pdf
    assert not re.search(rb"\d+\.\d%", pdf)


def test_pdf_route_downloads_the_compact_report_when_the_check_is_off(c):
    sid = run_interview(c, skip=(2,))
    r = c.get(f"/demo/s/{sid}/report.pdf")
    assert r.status_code == 200 and r.data.startswith(b"%PDF") and len(r.data) < 60_000
