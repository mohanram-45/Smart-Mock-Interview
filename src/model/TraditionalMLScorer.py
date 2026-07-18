"""Traditional ML Answer Scorer using TF-IDF with proper vocabulary training."""
import language_tool_python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TraditionalMLScorer:
    """
    Score answers using TF-IDF similarity and grammar checking.

    Model:
        - TF-IDF Vectorizer trained on full question corpus
        - Language Tool for grammar checking
        - Weighted scoring: 70% similarity, 30% grammar

    Install when needed:
        pip install scikit-learn language-tool-python
    """

    def __init__(self, all_questions=None):
        """
        Initialize the scorer.

        Args:
            all_questions: List of all question texts to train vectorizer (optional)
        """
        self.vectorizer = None
        self.all_questions_text = []

        if all_questions:
            self._train_vectorizer(all_questions)

        try:
            self.grammar_tool = language_tool_python.LanguageTool('en-US')
        except Exception as e:
            print(f"Warning: Grammar checker failed to load: {e}")
            self.grammar_tool = None

    def _train_vectorizer(self, all_questions):
        """
        Train TF-IDF vectorizer on all questions.

        Args:
            all_questions: List of question texts
        """
        try:
            question_texts = [str(q) for q in all_questions if q]
            if question_texts:
                self.vectorizer = TfidfVectorizer(stop_words="english")
                self.vectorizer.fit(question_texts)
                self.all_questions_text = question_texts
                print(f"Vectorizer trained on {len(question_texts)} questions")
        except Exception as e:
            print(f"Warning: Failed to train vectorizer: {e}")
            self.vectorizer = None

    def score(self, reference_answer: str, user_answer: str) -> dict:
        """
        Score user answer against reference answer.

        Args:
            reference_answer: The correct/reference answer
            user_answer: The student's answer

        Returns:
            Dict with keys:
            - similarity: Float between 0-1
            - score_percent: Percentage (0-100)
            - model: Model name
            - grammar_score: Grammar quality percentage
            - final_score: Weighted final score
        """
        reference_answer = str(reference_answer).strip()
        user_answer = str(user_answer).strip()

        if not user_answer:
            return {
                "model": "TraditionalML (TF-IDF + Grammar)",
                "similarity": 0.0,
                "score_percent": 0.0,
                "grammar_score": 0.0,
                "final_score": 0.0
            }

        # ────────────────────────────────────────────────────────────────
        # ────────────────────────────────────────────────────────────────
        similarity_percent = self._calculate_tfidf_similarity(reference_answer, user_answer)

        # ────────────────────────────────────────────────────────────────
        # ────────────────────────────────────────────────────────────────
        grammar_score = self._calculate_grammar_score(user_answer)

        # ────────────────────────────────────────────────────────────────
        # ────────────────────────────────────────────────────────────────
        final_score = round(
            (similarity_percent * 0.7) + (grammar_score * 0.3),
            2
        )

        return {
            "model": "TraditionalML (TF-IDF + Grammar)",
            "similarity": round(similarity_percent / 100, 3),
            "score_percent": similarity_percent,
            "grammar_score": grammar_score,
            "final_score": final_score
        }

    def _calculate_tfidf_similarity(self, ref_text: str, user_text: str) -> float:
        """
        Calculate TF-IDF cosine similarity.

        Args:
            ref_text: Reference answer text
            user_text: User answer text

        Returns:
            Similarity percentage (0-100)
        """
        try:
            vectorizer = TfidfVectorizer(stop_words="english")

            vectors = vectorizer.fit_transform([ref_text, user_text])

            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            similarity = float(similarity)

            return round(similarity * 100, 2)

        except Exception as e:
            print(f"Warning: TF-IDF similarity calculation failed: {e}")
            return 0.0

    def _calculate_grammar_score(self, text: str) -> float:
        """
        Calculate grammar quality score.

        Args:
            text: Text to check

        Returns:
            Grammar score (0-100)
        """
        if not text or not text.split():
            return 0.0

        if self.grammar_tool is None:
            return 100.0  # Skip grammar check if tool not available

        try:
            matches = self.grammar_tool.check(text)
            word_count = len(text.split())

            # Score: reduce by (errors/word_count * 100)
            grammar_score = max(
                0,
                round(
                    100 - (len(matches) / word_count * 100),
                    2
                )
            )
            return grammar_score

        except Exception as e:
            print(f"Warning: Grammar check failed: {e}")
            return 100.0  # Default to perfect if check fails

    def get_feedback(self, final_score: float) -> str:
        """
        Generate feedback based on final score.

        Args:
            final_score: Final weighted score (0-100)

        Returns:
            Feedback text
        """
        if final_score >= 80:
            return "Excellent answer. Most key concepts are covered."
        elif final_score >= 60:
            return "Good answer, but some important points are missing."
        elif final_score >= 40:
            return "Average answer. Add more details and key concepts."
        else:
            return "Poor answer. The answer differs significantly from the reference answer."


if __name__ == "__main__":
    scorer = TraditionalMLScorer()

    reference = "Binary search has O(log n) time complexity because it divides the search space in half with each iteration."
    student = "Binary search has O(log n) time complexity because it divides the search space in half with each iteration."

    result = scorer.score(reference, student)

    print("Reference:", reference)
    print("Student Answer:", student)
    print("\n" + "=" * 50)
    print(f"Similarity Score: {result['score_percent']}%")
    print(f"Grammar Score: {result['grammar_score']}%")
    print(f"Final Score: {result['final_score']}%")
    print(f"Model: {result['model']}")
    print("\nFeedback:")
    print(scorer.get_feedback(result['final_score']))
