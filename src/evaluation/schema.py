"""Pydantic contracts for Stage 3A.

Two layers on purpose:
  * LLMEvaluation   - what the MODEL is asked to return. It has NO overall score: the score is derived by code from rubric levels.
  * EvaluationResult - what the evaluator returns after verification (quotes checked, caps applied, status assigned).
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EVALUATION_SCHEMA_VERSION = "3a.1"


class EvaluationStatus(str, Enum):
    GRADED = "graded"                                   # scored, reference adequately grounded
    GRADED_LOW_CONFIDENCE = "graded_low_confidence"     # scored, but grounding/verification is weak: treat as provisional
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"     # not reliably gradable (no usable reference, model declined, no verifiable evidence)
    NOT_GRADABLE = "not_gradable"                       # nothing to evaluate (empty, non-answer)
    PROVIDER_ERROR = "provider_error"                   # transport/auth/timeouts after bounded retries
    INVALID_RESPONSE = "invalid_response"               # model replied but not in the contract, after the repair attempt
    PROVIDER_NOT_CONFIGURED = "provider_not_configured"


SCORED = {EvaluationStatus.GRADED, EvaluationStatus.GRADED_LOW_CONFIDENCE}
Confidence = Literal["high", "medium", "low"]
Severity = Literal["minor", "major"]
EvidenceSource = Literal["candidate_answer", "reference_answer", "key_concepts", "supporting_knowledge"]


# ----------------------------------------------------------------------------------------- inputs
class ReferenceBundle(BaseModel):
    """The selected question's own reference material, looked up by question ID (never taken from the candidate or from neighbours)."""
    model_config = ConfigDict(frozen=True)

    reference_answer: str = ""
    key_concepts: List[str] = Field(default_factory=list)
    common_mistakes: List[str] = Field(default_factory=list)
    alternative_answers: Dict[str, str] = Field(default_factory=dict)
    rubric_points: str = ""
    # verification / provenance (what is and is NOT known about the reference)
    source: Literal["curated", "legacy", "missing"] = "missing"
    verification: str = ""                    # e.g. 'ai_generated+ai_reviewed+source_opened'
    human_reviewed: bool = False
    code_executed: bool = False
    source_opened: bool = False
    time_sensitive: bool = False
    review_by: str = ""
    remaining_limitations: str = ""
    provenance: Dict[str, Any] = Field(default_factory=dict)

    @property
    def has_reference(self) -> bool:
        return bool(self.reference_answer.strip())

    @property
    def has_any_grounding(self) -> bool:
        return self.has_reference or bool(self.key_concepts)


class SupportSnippet(BaseModel):
    """Optional retrieved knowledge. NEVER authoritative for the selected question."""
    question_id: str
    topic: str = ""
    text: str
    score: Optional[float] = None


class EvaluationRequest(BaseModel):
    question_id: str
    question: str
    domain: str = ""
    topic: str = ""
    difficulty: str = ""
    candidate_answer: str
    reference: ReferenceBundle
    support: List[SupportSnippet] = Field(default_factory=list)

    @field_validator("question_id", "question")
    @classmethod
    def _nonblank(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("must not be blank")
        return str(v)

    @model_validator(mode="after")
    def _no_self_support(self):
        # retrieved neighbours must never include the selected question itself (it would duplicate/replace the canonical lookup)
        if any(s.question_id == self.question_id for s in self.support):
            raise ValueError("support must not contain the selected question")
        return self


# ----------------------------------------------------------------------------------------- model output contract
class DimensionScore(BaseModel):
    level: int = Field(ge=0, le=4)
    justification: str = ""


class RubricScores(BaseModel):
    correctness: DimensionScore
    completeness: DimensionScore
    relevance: DimensionScore
    reasoning: DimensionScore


class ConceptFinding(BaseModel):
    concept: str
    candidate_quote: str = ""          # the candidate's OWN words that demonstrate it (verified by code)


class FactualError(BaseModel):
    claim_quote: str = ""              # candidate's own words (verified by code)
    explanation: str = ""              # empty = unsupported accusation; dropped by the evaluator, not trusted
    correction: str = ""
    severity: Severity = "minor"


_EVIDENCE_SOURCES = ("candidate_answer", "reference_answer", "key_concepts", "supporting_knowledge")
_TEXT_KEYS = ("text", "concept", "strength", "suggestion", "limitation", "description", "name", "item", "point", "missing_concept", "explanation")


def _item_text(x):
    """A list-of-text item given as a one-text object -> its text; anything else is left for validation to reject."""
    if isinstance(x, dict):
        for k in _TEXT_KEYS:
            if isinstance(x.get(k), str) and x[k].strip():
                return x[k]
        strs = [v for v in x.values() if isinstance(v, str) and v.strip()]
        if len(strs) == 1:
            return strs[0]
    return x


class EvidenceItem(BaseModel):
    source: EvidenceSource
    quote: str
    supports: str = ""                 # which statement/finding this backs
    verified: Optional[bool] = None    # set by code, not by the model


class LLMEvaluation(BaseModel):
    """Exactly what the model must return (JSON). Unknown extra keys are ignored; missing required keys fail validation."""
    model_config = ConfigDict(extra="ignore")

    gradable: bool = True
    not_gradable_reason: str = ""
    rubric: Optional[RubricScores] = None
    score_rationale: str = ""
    correct_concepts: List[ConceptFinding] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    factual_errors: List[FactualError] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)
    improved_example_answer: str = ""
    follow_up_question: str = ""
    supporting_evidence: List[EvidenceItem] = Field(default_factory=list)
    confidence: Confidence = "low"
    verification_limitations: List[str] = Field(default_factory=list)

    malformed_evidence_dropped: int = 0   # set by code: optional evidence items with an invalid shape/source

    @model_validator(mode="before")
    @classmethod
    def _tolerate_optional_shapes(cls, data):
        """Optional feedback must not sink a usable grading. Text lists accept {"strength": "..."}-style objects
        (single text value); evidence items with an invalid source/shape are dropped and counted, never trusted."""
        if not isinstance(data, dict):
            return data
        data = dict(data)
        for k in ("missing_concepts", "strengths", "improvement_suggestions", "verification_limitations"):
            v = data.get(k)
            if isinstance(v, str):
                data[k] = [v] if v.strip() else []
            elif isinstance(v, list):
                data[k] = [_item_text(x) for x in v]
        ev = data.get("supporting_evidence")
        if isinstance(ev, list):
            ok = [x for x in ev if isinstance(x, dict) and x.get("source") in _EVIDENCE_SOURCES
                  and isinstance(x.get("quote"), str) and x.get("quote").strip()]
            data["malformed_evidence_dropped"] = len(ev) - len(ok)
            data["supporting_evidence"] = ok
        return data

    @model_validator(mode="after")
    def _graded_needs_rubric(self):
        if self.gradable and self.rubric is None:
            raise ValueError("gradable=true requires rubric levels")
        if self.gradable and not self.score_rationale.strip():
            raise ValueError("gradable=true requires score_rationale")
        if not self.gradable and not self.not_gradable_reason.strip():
            raise ValueError("gradable=false requires not_gradable_reason")
        return self


# ----------------------------------------------------------------------------------------- final result
class ReferenceStatus(BaseModel):
    source: str
    has_reference_answer: bool
    key_concept_count: int
    verification: str
    human_reviewed: bool
    time_sensitive: bool
    limitations: List[str] = Field(default_factory=list)


class Provenance(BaseModel):
    provider: str = ""
    model: str = ""
    is_mock: bool = False
    prompt_version: str = ""
    rubric_version: str = ""
    schema_version: str = EVALUATION_SCHEMA_VERSION
    attempts: int = 0
    latency_ms: Optional[float] = None
    usage: Dict[str, Any] = Field(default_factory=dict)      # provider-reported token counts/durations (last call)


class ErrorInfo(BaseModel):
    code: str
    message: str
    retryable: bool = False


class EvaluationResult(BaseModel):
    question_id: str
    evaluation_status: EvaluationStatus
    provisional_score: Optional[int] = Field(default=None, ge=0, le=100)
    score_band: Optional[str] = None
    rubric: Optional[RubricScores] = None
    rubric_weights: Dict[str, int] = Field(default_factory=dict)
    score_adjustments: List[str] = Field(default_factory=list)
    score_rationale: str = ""
    correct_concepts: List[ConceptFinding] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    factual_errors: List[FactualError] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)
    improved_example_answer: str = ""
    follow_up_question: str = ""
    supporting_evidence: List[EvidenceItem] = Field(default_factory=list)
    confidence: Confidence = "low"
    verification_limitations: List[str] = Field(default_factory=list)
    flags: Dict[str, Any] = Field(default_factory=dict)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
    reference_status: Optional[ReferenceStatus] = None
    provenance: Provenance = Field(default_factory=Provenance)
    error: Optional[ErrorInfo] = None
    status_reason: str = ""
    human_validated: Literal[False] = False        # the LLM's assessment is never presented as human-validated

    @model_validator(mode="after")
    def _score_iff_scored(self):
        scored = self.evaluation_status in SCORED
        if scored and self.provisional_score is None:
            raise ValueError("a scored status requires provisional_score")
        if not scored and self.provisional_score is not None:
            raise ValueError("a numeric score must not accompany a non-scored status")
        return self

    def to_candidate_view(self) -> Dict[str, Any]:
        """Fields safe to show the candidate AFTER evaluation: no provider internals, no reference-status internals."""
        keep = ("question_id", "evaluation_status", "provisional_score", "score_band", "score_rationale", "correct_concepts",
                "missing_concepts", "factual_errors", "strengths", "improvement_suggestions", "improved_example_answer",
                "follow_up_question", "confidence", "verification_limitations", "status_reason")
        d = self.model_dump(mode="json")
        out = {k: d[k] for k in keep}
        out["notice"] = "Provisional AI-generated assessment; not human-validated."
        return out


# ----------------------------------------------------------------------------------------- constrained-decoding schema
_STR = {"type": "string"}
_STR_LIST = {"type": "array", "items": _STR}
_DIM = {"type": "object", "properties": {"level": {"type": "integer", "enum": [0, 1, 2, 3, 4]}, "justification": _STR}, "required": ["level", "justification"]}
OUTPUT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "gradable": {"type": "boolean"},
        "not_gradable_reason": _STR,
        "rubric": {"type": "object", "properties": {k: _DIM for k in ("correctness", "completeness", "relevance", "reasoning")},
                   "required": ["correctness", "completeness", "relevance", "reasoning"]},
        "score_rationale": _STR,
        "correct_concepts": {"type": "array", "items": {"type": "object", "properties": {"concept": _STR, "candidate_quote": _STR}, "required": ["concept", "candidate_quote"]}},
        "missing_concepts": _STR_LIST,
        "factual_errors": {"type": "array", "items": {"type": "object", "properties": {
            "claim_quote": _STR, "explanation": _STR, "correction": _STR, "severity": {"type": "string", "enum": ["minor", "major"]}},
            "required": ["claim_quote", "explanation", "correction", "severity"]}},
        "strengths": _STR_LIST,
        "improvement_suggestions": _STR_LIST,
        "improved_example_answer": _STR,
        "follow_up_question": _STR,
        "supporting_evidence": {"type": "array", "items": {"type": "object", "properties": {
            "source": {"type": "string", "enum": ["candidate_answer", "reference_answer", "key_concepts", "supporting_knowledge"]},
            "quote": _STR, "supports": _STR}, "required": ["source", "quote", "supports"]}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "verification_limitations": _STR_LIST,
    },
    # Every key is required so a small model cannot close the object early (observed: replies that stop right after "rubric").
    # When gradable=false the rubric is still emitted (zeros) and ignored by the evaluator.
    "required": ["gradable", "not_gradable_reason", "rubric", "score_rationale", "correct_concepts", "missing_concepts", "factual_errors", "strengths",
                 "improvement_suggestions", "improved_example_answer", "follow_up_question", "supporting_evidence", "confidence", "verification_limitations"],
}
