"""Generate personalized report content with Ollama and a rule-based fallback."""
import logging
import json
import os
import re
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_REPORT_TIMEOUT", "180"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")

# Tone rules mirror the ones already used for live per-answer feedback
# (see feedback_generator.py): stay positive for a candidate who did
# well, only turn direct/corrective if performance was genuinely weak.
_SYSTEM_PROMPT = (
    "You are an interview coach writing short, personalized feedback for a "
    "candidate who just finished a mock technical interview. Write 3 to 4 "
    "recommendation sentences based ONLY on the facts given below - never "
    "invent topics, scores, or details that aren't in the facts.\n\n"
    "Every recommendation must be technically specific. Name the exact concepts, "
    "algorithms, terminology, implementation details, evaluation methods, or tools "
    "the candidate should learn. Convert each weak question into a concrete study "
    "instruction. Use the supplied technical study points when present. Never tell "
    "the candidate to look elsewhere in the report, revisit a lowest-scoring topic, "
    "research the areas for improvement, read a topic aloud, or merely explain it "
    "out loud. Avoid generic advice such as 'study documentation' unless you also "
    "name exactly what must be learned from it. Include at least one hands-on task "
    "using a named method, dataset type, metric, API, library, or implementation step.\n\n"
    "Tone rules: if the candidate's overall performance is good or "
    "excellent, keep the tone entirely positive and encouraging - no "
    "hedging, no backhanded compliments like 'good, but...'. Only if the "
    "overall performance is genuinely weak should the tone be direct and "
    "corrective about what to fix. Never be harsh or discouraging either "
    "way.\n\n"
    "Output format: one plain recommendation sentence per line. No "
    "markdown, no headers, no bullet symbols, no numbering, nothing else."
)

_COACHING_SYSTEM_PROMPT = """You are a senior technical interviewer and curriculum designer.
Create a deeply personalized post-interview coaching report from the evidence provided.
You may use accurate domain knowledge to expand a weak question into the exact concepts,
algorithms, APIs, tools, equations, implementation details, trade-offs, failure modes, and
evaluation methods the candidate needs to learn. Never invent a score, answer, weakness,
or interview event.

The report must work for any interview domain, including software engineering, data,
machine learning, cloud/DevOps, cybersecurity, product, business, finance, and HR.
Adapt terminology and practice tasks to the actual role and questions. A coding topic
should receive coding/debugging tasks; a system-design topic should receive architecture,
capacity, reliability, and trade-off tasks; a behavioural topic should receive STAR-based
evidence and decision-quality tasks; a business topic should receive frameworks, metrics,
calculations, and scenario analysis.

Rules:
- Convert every weak item into named technical or professional concepts to study.
- Treat skipped items as unassessed knowledge, never as demonstrated weaknesses or strengths.
- If answered_count is zero, explicitly state that no knowledge was demonstrated and create
  a foundations-from-scratch curriculum. Begin with what the language/domain is, syntax or
  core vocabulary, basic workflow, and prerequisites; then cover every skipped topic plus
  closely related fundamentals needed for role readiness. Skipped questions are evidence
  of scope, not headings to copy.
- If some questions were answered, recognize only strong_items as demonstrated strengths,
  then create a separate preparation curriculum for weak and skipped topics.
- Use the candidate's answer and evaluator feedback to identify what was missing.
- Give executable practice tasks with a concrete deliverable and success criteria.
- Make every practice task and success criterion different and appropriate to its module.
- Rewrite question-shaped text into concise curriculum labels (for example, "How do you
  write a basic unit test in Python?" becomes "Basic unit testing in Python").
- Make every learning-plan action self-contained; never say "see above", "review the
  lowest-scoring topics", "check Areas for Improvement", "research it", or "read it aloud".
- Avoid generic filler. Timing practice is allowed only when paired with a named task,
  measurable output, and quality criteria.
- Recommend only supported product actions. The application can start a new interview for
  a selected role, but cannot let candidates repeat or select exact previous questions.
- Produce exactly three learning phases: Technical Foundation, Applied Mastery, and
  Targeted Reassessment. Each phase must have 2 to 4 actions.
- Produce 3 to 5 recommendations.
- Keep each action and recommendation under 55 words.

Return only valid JSON with this shape:
{
  "technical_focus": [
    {
      "topic": "specific topic label",
      "terms": ["specific term", "specific method"],
      "practice_task": "concrete hands-on task",
      "success_criteria": "measurable evidence of mastery"
    }
  ],
  "learning_plan": [
    {"phase": "Phase 1: Technical Foundation", "focus": "named concepts", "actions": ["..."]},
    {"phase": "Phase 2: Applied Mastery", "focus": "named concepts", "actions": ["..."]},
    {"phase": "Phase 3: Targeted Reassessment", "focus": "named concepts", "actions": ["..."]}
  ],
  "recommendations": ["..."]
}"""

_GENERIC_PHRASES = (
    "lowest-scoring topic", "areas for improvement", "out loud", "read aloud",
    "topics listed under", "research them", "see above", "review the topic",
    "select exact", "repeat only skipped", "repeat the skipped", "built-in timed",
)


def _installed_models() -> List[str]:
    """Read locally installed models without requiring the Python package."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return [item.get("name") or item.get("model") for item in payload.get("models", []) if item.get("name") or item.get("model")]
    except Exception:
        return []


def _active_model() -> str:
    """Use the configured model when installed, otherwise use the first local model."""
    models = _installed_models()
    if not models or OLLAMA_MODEL in models:
        return OLLAMA_MODEL
    selected = models[0]
    logger.info("Configured Ollama model %s is unavailable; using installed model %s", OLLAMA_MODEL, selected)
    return selected


def _ollama_chat(system_prompt: str, user_prompt: str, json_output: bool = False) -> str:
    """Call local Ollama through its HTTP API so every Python environment works."""
    model = _active_model()
    body = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "options": {"temperature": 0.25 if json_output else 0.4, "num_predict": 1100 if json_output else 500},
        "keep_alive": "10m",
    }
    if json_output:
        body["format"] = "json"
    request = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str((payload.get("message") or {}).get("content") or "").strip()


def _compact_facts(facts: Dict[str, Any]) -> Dict[str, Any]:
    """Bound prompt size while retaining the evidence needed for personalization."""
    compact = {
        "role": facts.get("role") or "General interview",
        "overall_score": facts.get("average_score"),
        "performance_label": facts.get("performance_label"),
        "strong_domains": facts.get("strong_domains") or [],
        "weak_domains": facts.get("weak_domains") or [],
        "answered_count": int(facts.get("answered_count") or 0),
        "skipped_count": int(facts.get("skipped_count") or 0),
        "weak_items": [],
        "strong_items": [],
        "skipped_items": facts.get("skipped_items") or [],
        "product_capabilities": [
            "start a new mock interview by role",
            "receive a new role-appropriate question set",
            "compare overall and domain scores across saved reports",
        ],
        "unsupported_actions": [
            "select exact interview questions",
            "repeat only skipped questions",
            "run built-in timed coding exercises",
        ],
    }
    for key in ("weak_items", "strong_items"):
        for item in (facts.get(key) or [])[:5]:
            compact[key].append({
                "topic": str(item.get("topic") or "")[:240],
                "question": str(item.get("question") or "")[:400],
                "candidate_answer": str(item.get("candidate_answer") or "")[:900],
                "evaluator_feedback": str(item.get("feedback") or "")[:700],
                "score": item.get("score"),
                "domain": str(item.get("domain") or "")[:80],
                "difficulty": str(item.get("difficulty") or "")[:30],
            })
    return compact


def _valid_text(value: Any, minimum: int = 12) -> bool:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        return False
    lowered = value.lower()
    return not any(phrase in lowered for phrase in _GENERIC_PHRASES)


def _validate_coaching_payload(payload: Any) -> Optional[Dict[str, Any]]:
    """Validate the model response before it reaches the frontend."""
    if not isinstance(payload, dict):
        return None

    technical_focus = payload.get("technical_focus")
    learning_plan = payload.get("learning_plan")
    recommendations = payload.get("recommendations")
    if not isinstance(technical_focus, list) or not technical_focus:
        return None
    if not isinstance(learning_plan, list) or len(learning_plan) != 3:
        return None
    if not isinstance(recommendations, list):
        return None

    clean_focus = []
    for item in technical_focus[:5]:
        if not isinstance(item, dict) or not _valid_text(item.get("topic"), 3):
            continue
        terms = [str(term).strip() for term in item.get("terms", []) if _valid_text(term, 3)][:8]
        if len(terms) < 2 or not _valid_text(item.get("practice_task")) or not _valid_text(item.get("success_criteria")):
            continue
        clean_focus.append({
            "topic": item["topic"].strip(),
            "terms": terms,
            "practice_task": item["practice_task"].strip(),
            "success_criteria": item["success_criteria"].strip(),
        })
    if not clean_focus:
        return None

    clean_plan = []
    required_names = ("Technical Foundation", "Applied Mastery", "Targeted Reassessment")
    for index, (phase, required_name) in enumerate(zip(learning_plan, required_names), start=1):
        if not isinstance(phase, dict):
            return None
        actions = [str(action).strip() for action in phase.get("actions", []) if _valid_text(action)][:4]
        if len(actions) < 2 or not _valid_text(phase.get("focus"), 3):
            return None
        clean_plan.append({
            "phase": f"Phase {index}: {required_name}",
            "focus": phase["focus"].strip(),
            "actions": actions,
        })

    clean_recommendations = [
        str(item).strip() for item in recommendations if _valid_text(item)
    ][:5]
    if len(clean_recommendations) < 3:
        return None
    return {
        "technical_focus": clean_focus,
        "learning_plan": clean_plan,
        "recommendations": clean_recommendations,
    }


def generate_coaching_analysis(facts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate and validate the full personalized coaching section with Ollama."""
    try:
        raw = _ollama_chat(
            _COACHING_SYSTEM_PROMPT,
            "Interview evidence:\n" + json.dumps(_compact_facts(facts), ensure_ascii=False),
            json_output=True,
        )
        validated = _validate_coaching_payload(json.loads(raw))
        if not validated:
            logger.warning("Ollama coaching response failed validation - using rule-based plan")
            return None
        logger.info("Generated complete coaching analysis via Ollama (%s)", _active_model())
        return validated
    except Exception as e:
        logger.warning("Ollama coaching generation failed, using rule-based plan: %s", e)
        return None


def _build_user_prompt(facts: Dict[str, Any]) -> str:
    lines = [
        f"Role practiced: {facts.get('role') or 'General technical'}",
        f"Overall score: {facts.get('average_score')}% ({facts.get('performance_label')})",
    ]
    if facts.get("strong_domains"):
        lines.append(f"Strong domains: {', '.join(facts['strong_domains'])}")
    if facts.get("weak_domains"):
        lines.append(f"Weak domains: {', '.join(facts['weak_domains'])}")
    if facts.get("weak_topics"):
        lines.append(f"Weakest topics answered: {', '.join(facts['weak_topics'])}")
    if facts.get("technical_study_points"):
        lines.append("Required technical study points:")
        for topic, points in facts["technical_study_points"].items():
            lines.append(f"- {topic}: {', '.join(points)}")
    if facts.get("skipped_count"):
        skipped_topics = facts.get("skipped_topics") or []
        extra = f" ({', '.join(skipped_topics)})" if skipped_topics else ""
        lines.append(f"Skipped {facts['skipped_count']} question(s){extra}")
    lines.append("Write the recommendations now, one plain sentence per line.")
    return "\n".join(lines)


def _strip_leading_marker(line: str) -> str:
    """Strip a leading '- ', '* ', '1. ' / '1) ' etc. if the model added one anyway."""
    line = line.strip().lstrip("-*•").strip()
    return re.sub(r"^\d+[.)]\s*", "", line).strip()


def generate_recommendations(facts: Dict[str, Any]) -> Optional[List[str]]:
    """Ask the local Ollama model for 1-4 recommendation sentences based
    on the given interview facts. Returns None on any failure (Ollama not
    installed/running, timeout, empty response) so the caller can fall
    back to rule-based text. Never raises.
    """
    try:
        text = _ollama_chat(_SYSTEM_PROMPT, _build_user_prompt(facts))
        if not text:
            logger.warning("Ollama returned an empty response - falling back to rule-based")
            return None

        cleaned = [
            _strip_leading_marker(raw_line)
            for raw_line in text.splitlines()
        ]
        # drop blank lines / stray headers the model sometimes echoes back
        banned_generic_phrases = (
            "lowest-scoring topic", "areas for improvement", "out loud",
            "read aloud", "topics listed under", "research them",
        )
        cleaned = [
            line for line in cleaned
            if len(line) >= 15
            and not any(phrase in line.lower() for phrase in banned_generic_phrases)
        ][:4]

        if not cleaned:
            logger.warning("Ollama response had no usable lines - falling back to rule-based")
            return None

        logger.info(f"Generated {len(cleaned)} recommendation(s) via Ollama ({OLLAMA_MODEL})")
        return cleaned

    except Exception as e:
        # Ollama down, model not pulled, timeout, bad response, etc.
        logger.warning(f"Ollama recommendation generation failed, falling back to rule-based: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    demo_facts = {
        "role": "NLP Engineer",
        "average_score": 76.2,
        "performance_label": "Excellent (76.2%)",
        "strong_domains": ["NLP", "ML"],
        "weak_domains": [],
        "weak_topics": [
            "Advantages of using a CNN (convolutional neural network) rather than "
            "a DNN (dense neural network) in an image classification task"
        ],
        "skipped_count": 0,
        "skipped_topics": [],
    }
    print(f"Testing Ollama connection (model={OLLAMA_MODEL})...")
    result = generate_recommendations(demo_facts)
    if result:
        print("\nLLM-generated recommendations:")
        for line in result:
            print(" -", line)
    else:
        print(
            "\nLLM unavailable - report_generator.py would fall back to its "
            "rule-based recommendations instead. Check that:\n"
            "  1. Ollama is installed and running (the Ollama app, or `ollama serve`)\n"
            f"  2. The model is pulled: ollama pull {OLLAMA_MODEL}\n"
            "  3. Nothing else is using port 11434"
        )
