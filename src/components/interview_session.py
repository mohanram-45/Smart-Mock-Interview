"""Adaptive Interview Session Manager - Orchestrates adaptive interview workflow."""
import logging
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

from data_ingestion import DataIngestion
from feedback_generator import FeedbackGenerator
from report_generator import ReportGenerator
from config import (
    ROLE_MAPPING,
    ADAPTIVE_EASY_BASE_RANGE,
    ADAPTIVE_EASY_THRESHOLD,
    ADAPTIVE_EASY_EXTRA_MAX,
    ADAPTIVE_MEDIUM_BASE,
    ADAPTIVE_MEDIUM_THRESHOLD,
    ADAPTIVE_MEDIUM_EXTRA_RANGE,
    ADAPTIVE_HARD_BASE_RANGE,
    FALLBACK_MEDIUM_RANGE,
    FALLBACK_HARD_RANGE,
    FIXED_EASY_COUNT,
    FIXED_MEDIUM_COUNT,
    FIXED_HARD_COUNT,
    MIN_ANSWERED_PER_ROUND,
    ROUND_ORDER
)

# Answer-scoring models live in src/model. model_registry gives all 3
# scorers (Siamese Bi-LSTM, Sentence-BERT, TF-IDF + Grammar) one shared
# interface: scorer.score(reference, user_answer) -> float in [0, 1].
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "model"))

try:
    from model_registry import get_scorer, is_valid_model, DEFAULT_MODEL
except ImportError:
    print("ERROR: model_registry not available.")
    raise

logger = logging.getLogger(__name__)


class AdaptiveInterviewSession:
    """
    Manages adaptive interview with progressive difficulty levels.

    Features:
    - Role-based domain selection
    - Custom domain selection
    - Question filtering and shuffling
    - Adaptive difficulty progression
    - Performance-based threshold checking
    - No question repetition
    """
    def __init__(
        self,
        session_id: str,
        role: str,
        custom_domains: Optional[List[str]] = None,
        model_choice: str = DEFAULT_MODEL
    ):
        """
        Initialize adaptive interview session.

        Args:
            session_id: Unique session identifier
            role: Interview role (from ROLE_MAPPING or "Custom Interview")
            custom_domains: List of domains for custom interview
            model_choice: Which answer-scoring model to use for this ENTIRE
                session ("bilstm", "bert", or "tfidf"). Locked in at start -
                every question in the session is scored with the same model.
        """
        self.session_id = session_id
        self.role = role
        self.started_at = datetime.utcnow().isoformat() + "Z"
        self.ended_at: Optional[str] = None

        # Determine selected domains
        if role == "Custom Interview":
            self.selected_domains = custom_domains or []
        else:
            self.selected_domains = ROLE_MAPPING.get(role, [])

        if not self.selected_domains:
            raise ValueError(f"No domains selected for role: {role}")

        if not is_valid_model(model_choice):
            raise ValueError(f"Invalid model_choice: {model_choice}")
        self.model_choice = model_choice

        # Initialize modules
        self.data_ingestion = DataIngestion(
            Path(__file__).parent.parent.parent / "data" / "processed"
        )
        # The actual scorer is resolved in load_questions() once the question
        # corpus is available (the TF-IDF model wants it for vectorizer training).
        self.neural_scorer = None
        self.feedback_generator = FeedbackGenerator()
        self.report_generator = ReportGenerator(session_id, role, self.started_at)

        # Load all questions
        self.all_questions: List[Dict[str, Any]] = []
        self.questions_by_difficulty: Dict[str, List[Dict[str, Any]]] = {
            "Easy": [],
            "Medium": [],
            "Hard": []
        }
        self.asked_question_ids: Set[int] = set()

        # Current state
        self.current_round = 0
        self.current_question_index = 0
        self.current_question: Optional[Dict[str, Any]] = None
        self.consecutive_skips = 0

        # Round tracking
        self.round_questions: Dict[str, List[Dict[str, Any]]] = {
            "Easy": [],
            "Medium": [],
            "Hard": []
        }
        self.round_answers: Dict[str, List[Dict[str, Any]]] = {
            "Easy": [],
            "Medium": [],
            "Hard": []
        }
        self.current_round_name = "Easy"

        # Adaptive engine (BERT/TF-IDF) per-round-instance bookkeeping.
        # fallback_mode flips on once a round exhausts its extra-question
        # cap without clearing its threshold, and stays on for the rest of
        # the session (remaining rounds become short, no-threshold batches).
        self.fallback_mode = False
        self.round_kind: Dict[str, str] = {}       # "fixed" | "gated" | "flat"
        self.round_base_size: Dict[str, int] = {}   # compulsory batch size assigned this round instance
        self.round_extra_cap: Dict[str, int] = {}   # extra-question cap this round instance (gated only)

        logger.info(
            f"Initialized adaptive session {session_id} for role {role} "
            f"with domains: {self.selected_domains}"
        )

    def load_questions(self) -> bool:
        """
        Load and filter questions by selected domains.

        Returns:
            True if questions loaded, False otherwise
        """
        try:
            processed_path = (
                Path(__file__).parent.parent.parent / "data" / "processed"
            )
            questions_file = processed_path / "questions_cleaned.json"

            with open(questions_file, "r", encoding="utf-8") as f:
                all_questions = json.load(f)

            # Filter by selected domains
            self.all_questions = [
                q for q in all_questions
                if q.get("domain") in self.selected_domains
            ]

            if not self.all_questions:
                logger.error(f"No questions found for domains {self.selected_domains}")
                return False

            # Group by difficulty and shuffle
            for diff in ["Easy", "Medium", "Hard"]:
                questions = [
                    q for q in self.all_questions
                    if q.get("difficulty") == diff
                ]
                random.shuffle(questions)
                self.questions_by_difficulty[diff] = questions

            # Resolve the scorer this session locked in at start time. Loaded/
            # trained once per process per model and shared across sessions
            # that pick the same model (see model_registry.py).
            corpus = [q.get("reference_answer", "") for q in self.all_questions]
            self.neural_scorer = get_scorer(self.model_choice, corpus=corpus)

            logger.info(
                f"Loaded {len(self.all_questions)} questions for {self.role}\n"
                f"  Easy: {len(self.questions_by_difficulty['Easy'])}\n"
                f"  Medium: {len(self.questions_by_difficulty['Medium'])}\n"
                f"  Hard: {len(self.questions_by_difficulty['Hard'])}\n"
                f"  Scoring model: {self.model_choice}"
            )
            return True

        except FileNotFoundError:
            logger.error("Questions file not found")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse questions JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading questions: {e}")
            return False

    def get_next_question(self, difficulty: str) -> Optional[Dict[str, Any]]:
        """
        Get next unanswered question for difficulty level.

        Args:
            difficulty: "Easy", "Medium", or "Hard"

        Returns:
            Question dict or None if no more questions
        """
        available = [
            q for q in self.questions_by_difficulty[difficulty]
            if q.get("id") not in self.asked_question_ids
        ]

        if not available:
            logger.warning(f"No more {difficulty} questions available")
            return None

        question = available[0]
        self.asked_question_ids.add(question.get("id"))
        self.current_question = question
        return question

    def _is_adaptive_model(self) -> bool:
        """Whether this session's scoring model uses the adaptive,
        per-answer round-progression engine (BERT / TF-IDF) instead of
        the fixed curriculum (Bi-LSTM)."""
        return self.model_choice in ("bert", "tfidf")

    def _round_kind(self, round_name: str) -> str:
        """
        Classify how this round instance should behave:
        - "fixed": Bi-LSTM - flat batch, no threshold (see FIXED_* constants).
        - "flat": adaptive model, but no threshold check for this round -
          either Hard (terminal round, never gated) or Medium/Easy once
          fallback_mode has already been triggered by an earlier round.
        - "gated": adaptive model, base batch + threshold + extras. Easy is
          always gated (nothing precedes it to trigger fallback); Medium is
          gated unless fallback_mode is already on.
        """
        if not self._is_adaptive_model():
            return "fixed"
        if round_name == "Hard":
            return "flat"
        if round_name == "Medium" and self.fallback_mode:
            return "flat"
        return "gated"

    def _batch_size_for_round(self, round_name: str, kind: str) -> int:
        """Determine this round instance's compulsory batch size."""
        if kind == "fixed":
            return {
                "Easy": FIXED_EASY_COUNT,
                "Medium": FIXED_MEDIUM_COUNT,
                "Hard": FIXED_HARD_COUNT
            }[round_name]

        if round_name == "Easy":
            lo, hi = ADAPTIVE_EASY_BASE_RANGE
            return random.randint(lo, hi)

        if round_name == "Medium":
            if kind == "flat":  # fallback tail
                lo, hi = FALLBACK_MEDIUM_RANGE
                return random.randint(lo, hi)
            return ADAPTIVE_MEDIUM_BASE

        # Hard
        if self.fallback_mode:
            lo, hi = FALLBACK_HARD_RANGE
        else:
            lo, hi = ADAPTIVE_HARD_BASE_RANGE
        return random.randint(lo, hi)

    def _extra_cap_for_round(self, round_name: str) -> int:
        """Extra-question cap for a "gated" round instance (Easy or
        non-fallback Medium). Randomized per round instance for Medium,
        same spirit as the randomized base/batch sizes elsewhere."""
        if round_name == "Easy":
            return ADAPTIVE_EASY_EXTRA_MAX
        lo, hi = ADAPTIVE_MEDIUM_EXTRA_RANGE
        return random.randint(lo, hi)

    def start_round(self, round_name: str) -> Optional[Dict[str, Any]]:
        """
        Start a new difficulty round.

        Adaptive engine (BERT/TF-IDF): assigns a randomized compulsory base
        batch upfront (see _batch_size_for_round). check_round_completion()
        evaluates the threshold once the base is answered, and continue_round()
        appends extra questions one at a time if needed - see
        _check_round_completion_adaptive() for the full state machine,
        including the fallback-mode cascade.

        Fixed engine (Bi-LSTM): assigns the full fixed batch for the round
        upfront, since there's no score-based branching for it.

        Args:
            round_name: "Easy", "Medium", or "Hard"

        Returns:
            First question of the round or None
        """
        self.current_round_name = round_name
        self.round_questions[round_name] = []
        self.round_answers[round_name] = []
        self.current_question_index = 0

        kind = self._round_kind(round_name)
        self.round_kind[round_name] = kind
        count = self._batch_size_for_round(round_name, kind)
        self.round_base_size[round_name] = count
        self.round_extra_cap[round_name] = (
            self._extra_cap_for_round(round_name) if kind == "gated" else 0
        )

        for _ in range(count):
            q = self.get_next_question(round_name)
            if q:
                self.round_questions[round_name].append(q)

        logger.info(
            f"Started {round_name} round ({kind}) with {len(self.round_questions[round_name])} "
            f"question(s) (model={self.model_choice}, fallback_mode={self.fallback_mode})"
        )

        # Get first question
        if self.round_questions[round_name]:
            return self._get_current_question()
        return None

    def _get_current_question(self) -> Optional[Dict[str, Any]]:
        """Get current question in round."""
        if (
            self.current_question_index >= len(self.round_questions[self.current_round_name])
        ):
            return None

        q = self.round_questions[self.current_round_name][self.current_question_index]
        self.current_question = q
        return q

    def submit_answer(self, user_answer: str) -> Dict[str, Any]:
        """
        Process submitted answer and decide next action.

        Returns:
            Dict with score, feedback, and next_action
        """
        question = self._get_current_question()
        if not question:
            return {"error": "No current question"}

        try:
            # Any genuine attempt resets the interview-abandonment counter.
            self.consecutive_skips = 0
            # Score answer with Neural Network (Bi-LSTM)
            similarity_score_normalized = self.neural_scorer.score(
                question.get("reference_answer", ""),
                user_answer
            )
            # Convert to percentage (0-100)
            similarity_score = round(similarity_score_normalized * 100, 2)

            # Generate feedback (feedback wording/tiers depend on which
            # scoring model this session locked in - see feedback_generator.py)
            feedback = self.feedback_generator.generate(
                similarity_score=similarity_score,
                question=question.get("question", ""),
                user_answer=user_answer,
                model_choice=self.model_choice
            )

            # Store in round answers
            answer_record = {
                "question_id": question.get("id"),
                "question_number": self.current_question_index + 1,
                "domain": question.get("domain"),
                "difficulty": question.get("difficulty"),
                "similarity_score": similarity_score,
                "feedback": feedback,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "skipped": False
            }
            self.round_answers[self.current_round_name].append(answer_record)

            # Store in report
            self.report_generator.append_answer(
                question_id=question.get("id"),
                question=question.get("question", ""),
                user_answer=user_answer,
                similarity_score=similarity_score,
                feedback=feedback,
                skipped=False,
                difficulty=question.get("difficulty"),
                round_name=self.current_round_name,
                domain=question.get("domain", "")
            )

            logger.info(
                f"Session {self.session_id}: {self.current_round_name} Q{self.current_question_index + 1} "
                f"scored {similarity_score}%"
            )

            # Move to next question
            self.current_question_index += 1

            return {
                "similarity_score": similarity_score,
                "feedback": feedback,
                "question_completed": True,
                "next_action": "continue"  # Will be updated by check_round_completion
            }

        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            return {"error": str(e)}

    def check_round_completion(self) -> Dict[str, Any]:
        """
        Check if current round is complete and determine next action.

        Dispatches to one of two independent engines depending on which
        scoring model this session locked in:
        - Adaptive (BERT/TF-IDF): re-evaluated after EVERY answer.
        - Fixed curriculum (Bi-LSTM): only evaluated once the round's full
          fixed batch has been answered, and always advances regardless
          of score.

        Returns:
            Dict with action, average_score, and next_round or end
        """
        if self._is_adaptive_model():
            return self._check_round_completion_adaptive()
        return self._check_round_completion_fixed()

    def _check_round_completion_fixed(self) -> Dict[str, Any]:
        """Bi-LSTM: no thresholds. Ask the fixed batch for the round, then
        always advance Easy -> Medium -> Hard -> end, regardless of score."""
        answers = self.round_answers[self.current_round_name]
        assigned = self.round_questions[self.current_round_name]

        if not answers or len(answers) < len(assigned):
            return {"action": "continue"}

        answered_count = sum(1 for answer in answers if not answer.get("skipped"))
        minimum_answered = MIN_ANSWERED_PER_ROUND[self.current_round_name]
        if answered_count < minimum_answered:
            return {
                "action": "continue_round",
                "current_round": self.current_round_name,
                "reason": f"At least {minimum_answered} answered questions are required in this round.",
            }

        scored_answers = [answer for answer in answers if not answer.get("skipped")]
        avg_score = sum(a["similarity_score"] for a in scored_answers) / len(scored_answers)
        logger.info(
            f"{self.current_round_name} round (fixed curriculum): "
            f"{len(answers)} questions, avg {avg_score:.2f}%"
        )

        if self.current_round_name == "Easy":
            return {
                "action": "next_round",
                "current_round": "Easy",
                "average_score": avg_score,
                "next_round": "Medium"
            }
        elif self.current_round_name == "Medium":
            return {
                "action": "next_round",
                "current_round": "Medium",
                "average_score": avg_score,
                "next_round": "Hard"
            }
        else:  # Hard
            return {
                "action": "end_interview",
                "current_round": "Hard",
                "average_score": avg_score,
                "reason": "Hard round complete"
            }

    def _advance_or_end(self, round_name: str, avg_score: float) -> Dict[str, Any]:
        """Move to the next round, or end the interview if this was Hard."""
        if round_name == "Easy":
            return {
                "action": "next_round",
                "current_round": "Easy",
                "average_score": avg_score,
                "next_round": "Medium"
            }
        elif round_name == "Medium":
            return {
                "action": "next_round",
                "current_round": "Medium",
                "average_score": avg_score,
                "next_round": "Hard"
            }
        else:  # Hard
            return {
                "action": "end_interview",
                "current_round": "Hard",
                "average_score": avg_score,
                "reason": "Hard round complete"
            }

    def _check_round_completion_adaptive(self) -> Dict[str, Any]:
        """
        BERT / TF-IDF adaptive engine.

        "gated" rounds (Easy always, Medium unless fallback_mode is already
        on): wait for the compulsory base batch to be fully answered, then
        check the average against the round's threshold. Clears it ->
        advance. Falls short -> ask one more question at a time (up to the
        round's extra cap) and recheck after each. Still short once the
        extra cap is exhausted -> flip fallback_mode on and advance anyway
        (the remaining rounds become short "flat" batches).

        "flat" rounds (Hard always; Medium once fallback_mode is on): no
        threshold - just wait for the assigned batch to be answered, then
        advance/end.
        """
        round_name = self.current_round_name
        answers = self.round_answers[round_name]
        assigned = self.round_questions[round_name]
        kind = self.round_kind.get(round_name, "gated")

        if not answers or len(answers) < len(assigned):
            return {"action": "continue"}

        answered_count = sum(1 for answer in answers if not answer.get("skipped"))
        minimum_answered = MIN_ANSWERED_PER_ROUND[round_name]
        if answered_count < minimum_answered:
            return {
                "action": "continue_round",
                "current_round": round_name,
                "reason": f"At least {minimum_answered} answered questions are required in this round.",
            }

        scored_answers = [answer for answer in answers if not answer.get("skipped")]
        avg_score = sum(a["similarity_score"] for a in scored_answers) / len(scored_answers)
        logger.info(
            f"{round_name} round (adaptive, {kind}): "
            f"{len(answers)} question(s), avg {avg_score:.2f}%, fallback_mode={self.fallback_mode}"
        )

        if kind == "flat":
            # No threshold to check - batch's done, move on.
            return self._advance_or_end(round_name, avg_score)

        # kind == "gated"
        base_size = self.round_base_size.get(round_name, len(assigned))
        if len(answers) < base_size:
            # Still inside the compulsory base - don't evaluate yet.
            return {"action": "continue"}

        threshold = ADAPTIVE_EASY_THRESHOLD if round_name == "Easy" else ADAPTIVE_MEDIUM_THRESHOLD

        if avg_score >= threshold:
            return self._advance_or_end(round_name, avg_score)

        extra_cap = self.round_extra_cap.get(round_name, 0)
        extras_asked = len(answers) - base_size
        if extras_asked < extra_cap:
            return {
                "action": "continue_round",
                "current_round": round_name,
                "average_score": avg_score,
                "message": f"Score {avg_score:.2f}% is below {threshold}%. Asking another {round_name} question."
            }

        # Extras exhausted without clearing the threshold - fall back for
        # the rest of the session instead of ending here.
        self.fallback_mode = True
        logger.info(f"{round_name} round: extras exhausted without clearing threshold - entering fallback mode")
        return self._advance_or_end(round_name, avg_score)

    def continue_round(self) -> Optional[Dict[str, Any]]:
        """Add one more question to the current round.

        Only called by the adaptive engine's "gated" rounds (Easy, or
        Medium before any fallback is triggered) - "flat" rounds and the
        fixed engine (Bi-LSTM) pre-assign their full batch in start_round()
        and never trigger "continue_round".
        """
        q = self.get_next_question(self.current_round_name)
        if q:
            self.round_questions[self.current_round_name].append(q)

        return self._get_current_question()

    def skip_question(self) -> Dict[str, Any]:
        """Skip current question."""
        question = self._get_current_question()
        if not question:
            return {"error": "No current question"}

        answer_record = {
            "question_id": question.get("id"),
            "question_number": self.current_question_index + 1,
            "domain": question.get("domain"),
            "difficulty": question.get("difficulty"),
            "similarity_score": 0.0,
            "feedback": "Question skipped",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "skipped": True
        }
        self.round_answers[self.current_round_name].append(answer_record)

        self.report_generator.append_answer(
            question_id=question.get("id"),
            question=question.get("question", ""),
            user_answer="",
            similarity_score=0.0,
            feedback="Question skipped",
            skipped=True,
            difficulty=question.get("difficulty"),
            round_name=self.current_round_name,
            domain=question.get("domain", "")
        )

        self.current_question_index += 1
        self.consecutive_skips += 1
        logger.info(f"Session {self.session_id}: {self.current_round_name} Q{self.current_question_index} skipped")

        return {
            "skipped": True,
            "message": "Question skipped",
            "consecutive_skips": self.consecutive_skips,
            "force_end": self.consecutive_skips >= 5,
        }

    def repeat_question(self) -> Optional[Dict[str, Any]]:
        """Repeat current question."""
        return self._get_current_question()

    def get_status(self) -> Dict[str, Any]:
        """Get current interview status."""
        question = self._get_current_question()

        return {
            "session_id": self.session_id,
            "role": self.role,
            "selected_domains": self.selected_domains,
            "model_choice": self.model_choice,
            "started_at": self.started_at,
            "current_round": self.current_round_name,
            "round_progress": f"{self.current_question_index + 1}/{len(self.round_questions[self.current_round_name])}",
            "round_answers": len(self.round_answers[self.current_round_name]),
            "total_questions_answered": sum(
                len(self.round_answers[r]) for r in ROUND_ORDER
            ),
            "current_question": question,
            "is_finished": question is None
        }

    def end_interview(self) -> Dict[str, Any]:
        """End interview and generate final report."""
        self.ended_at = datetime.utcnow().isoformat() + "Z"

        try:
            # Generate report with round statistics
            report = self.report_generator.finalize_report(
                self.ended_at,
                role=self.role,
                selected_domains=self.selected_domains,
                round_answers=self.round_answers,
                scoring_model=self.model_choice
            )

            logger.info(f"Session {self.session_id} ended. Report generated.")
            return report

        except Exception as e:
            logger.error(f"Error ending interview: {e}")
            return {"error": str(e)}
