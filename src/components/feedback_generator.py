"""Feedback Generator - Converts similarity scores into constructive feedback."""
import logging
import random
from typing import List, Optional

logger = logging.getLogger(__name__)


class FeedbackGenerator:
    """
    Generates interview feedback based on answer evaluation metrics.

    Responsibility:
    - Convert similarity score into human-readable feedback text
    - Future-proof: accepts multiple inputs (similarity, grammar, confidence, etc.)
    - Does NOT evaluate answers (that's the scoring model's job)
    - Does NOT store results (that's ReportGenerator's job)

    Two independent tier schemes are kept side by side, plus a neutral scheme:
    - self.thresholds / self.templates - the ORIGINAL scheme. No longer used by
      default (kept only for add_custom_feedback/set_thresholds callers), since
      the Siamese Bi-LSTM now uses the neutral scheme below instead.
    - self.new_thresholds / self.new_templates - used for Sentence-BERT and the
      TF-IDF + Grammar (Traditional ML) model. Each tier has several phrasing
      variants, picked at random, so the same tier doesn't always read identically.
    - self.neutral_templates - used for the Siamese Bi-LSTM model. The Bi-LSTM
      was only ever trained on exact-match positives (see EVALUATION_README.md /
      NEURAL_NETWORK_FINAL.md), so it under-scores correctly-worded-differently
      answers. Rather than pass a potentially wrong quality judgement on to the
      candidate, its feedback just acknowledges the answer and moves on - no
      "excellent"/"needs work" framing, regardless of score.
    """

    def __init__(self):
        """Initialize feedback templates and thresholds."""
        # ---- Original scheme (retained for add_custom_feedback/set_thresholds) ----
        self.thresholds = {
            "excellent": 0.85,
            "good": 0.70,
            "fair": 0.55,
            "needs_improvement": 0.00
        }

        self.templates = {
            "excellent": (
                "Excellent answer! You demonstrated a strong understanding of the concept. "
                "Your response was clear, comprehensive, and directly addressed the question."
            ),
            "good": (
                "Good understanding. You covered the main points, though there are some areas "
                "that could be more detailed or refined. Consider adding more examples or "
                "clarification on the underlying concepts."
            ),
            "fair": (
                "You have a partial understanding of this topic. Your answer touched on some "
                "correct concepts, but there are gaps. Review the key fundamentals and try to "
                "connect more concepts to build a stronger answer."
            ),
            "needs_improvement": (
                "This answer needs more work. The key concepts may be unclear or incomplete. "
                "Take time to review the fundamentals before moving on to related topics."
            )
        }

        # ---- Neutral scheme (Siamese Bi-LSTM) ----
        # No tiers, no quality judgement - the model isn't reliable enough for that.
        self.neutral_templates = [
            "Okay, got it — let's move on to the next question.",
            "Alright, noted. Moving on to the next one.",
            "Thanks for that — let's continue.",
            "Got it — on to the next question.",
        ]

        # ---- New scheme (Sentence-BERT and TF-IDF + Grammar) ----
        self.new_thresholds = {
            "excellent": 0.85,
            "good": 0.50,
            "fair": 0.35,
            "needs_improvement": 0.00
        }

        self.new_templates = {
            "excellent": [
                "Excellent work — this answer is clear, accurate, and complete.",
                "Great job! You nailed the key concepts here.",
                "Strong answer — well explained and right on target.",
                "That's a comprehensive, accurate response. Nicely done.",
                "Excellent! You clearly have a solid grasp of this topic.",
            ],
            "good": [
                "Good answer — you've got a solid grasp of this.",
                "Nice work, you covered the important points well.",
                "That's a clear, well-formed response.",
                "You're showing good understanding of the topic here.",
                "Well answered — you're clearly comfortable with this concept.",
            ],
            "fair": [
                "You're on the right track with this one.",
                "Good start — you've touched on some of the right ideas.",
                "There's a solid foundation in this answer.",
                "You're getting there — keep building on this.",
                "Nice attempt — you're grasping part of this concept.",
            ],
            "needs_improvement": [
                "This answer misses the key concept — worth a closer look later.",
                "There's a gap in understanding here — take some time to review this.",
                "This needs more study. Focus on the core idea behind this question.",
            ],
        }

        # Models that use the new tier scheme instead of the original one.
        self._new_scheme_models = {"bert", "tfidf"}

    def _score_to_tier(self, similarity_score: float, thresholds: dict) -> str:
        """
        Map similarity score to feedback tier using the given threshold set.

        Args:
            similarity_score: Similarity percentage (0-100)
            thresholds: Dict with 'excellent'/'good'/'fair'/'needs_improvement' cutoffs (0-1)

        Returns:
            Tier name: 'excellent', 'good', 'fair', or 'needs_improvement'
        """
        normalized = similarity_score / 100.0  # Convert to 0-1 range

        if normalized >= thresholds["excellent"]:
            return "excellent"
        elif normalized >= thresholds["good"]:
            return "good"
        elif normalized >= thresholds["fair"]:
            return "fair"
        else:
            return "needs_improvement"

    def generate(
        self,
        similarity_score: float,
        question: str = "",
        user_answer: str = "",
        model_choice: Optional[str] = None
    ) -> str:
        """
        Generate feedback for an answer.

        Args:
            similarity_score: Scoring model's similarity score (0-100 percent)
            question: The interview question (for future use)
            user_answer: User's answer text (for future use)
            model_choice: Which scoring model produced this score - "bilstm",
                "bert", or "tfidf". "bert"/"tfidf" use the 85/50/35 tier scheme
                with randomized phrasing; "bilstm" (or anything unrecognized)
                gets a neutral acknowledgement with no quality judgement, since
                the Bi-LSTM's scores aren't reliable enough to justify one.

        Returns:
            Feedback text string

        Note:
            Currently uses only similarity_score for tier selection.
            Future models can use question and user_answer for grammar, confidence, etc.
        """
        try:
            if model_choice in self._new_scheme_models:
                tier = self._score_to_tier(similarity_score, self.new_thresholds)
                variants: List[str] = self.new_templates[tier]
                feedback = random.choice(variants)
            else:
                tier = "neutral"
                feedback = random.choice(self.neutral_templates)

            logger.debug(
                f"Generated '{tier}' feedback for score {similarity_score}% (model={model_choice})"
            )
            return feedback

        except Exception as e:
            logger.error(f"Error generating feedback: {e}")
            return "Unable to generate feedback at this time."

    def add_custom_feedback(self, tier: str, template: str) -> None:
        """
        Add or override feedback template.

        Allows customization for different interview types or domains.

        Args:
            tier: Feedback tier ('excellent', 'good', 'fair', 'needs_improvement')
            template: Custom feedback text
        """
        if tier not in self.templates:
            logger.warning(f"Unknown tier '{tier}'. Adding as custom tier.")

        self.templates[tier] = template
        logger.info(f"Updated feedback template for tier '{tier}'")

    def set_thresholds(self, excellent: float, good: float, fair: float) -> None:
        """
        Customize score thresholds for feedback tiers.

        Args:
            excellent: Score threshold for excellent (0-1)
            good: Score threshold for good (0-1)
            fair: Score threshold for fair (0-1)

        Example:
            feedback_gen.set_thresholds(excellent=0.80, good=0.65, fair=0.50)
        """
        self.thresholds = {
            "excellent": excellent,
            "good": good,
            "fair": fair,
            "needs_improvement": 0.0
        }
        logger.info(f"Updated feedback thresholds: {self.thresholds}")
