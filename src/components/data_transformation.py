"""Data Transformation - Extract embedded answers"""
import json
import re
from pathlib import Path


class DataTransformation:
    """Transform raw questions"""

    def __init__(self, output_path):
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)

    def normalize_difficulty(self, value):
        """Map source labels to the app's three difficulty levels."""
        label = str(value or "").strip().lower()
        labels = {
            "easy": "Easy",
            "beginner": "Easy",
            "medium": "Medium",
            "intermediate": "Medium",
            "hard": "Hard",
            "advanced": "Hard",
        }
        return labels.get(label, str(value or "").strip())

    def normalize_domain(self, value):
        """Map legacy source domains to the six supported domains."""
        label = str(value or "").strip()
        compact = label.lower().replace("_", " ").replace("-", " ")
        domains = {
            "ml": "Machine Learning",
            "machine learning": "Machine Learning",
            "predictive modelling": "Machine Learning",
            "predictive modeling": "Machine Learning",
            "dl": "Deep Learning",
            "deep learning": "Deep Learning",
            "nlp": "NLP",
            "natural language processing": "NLP",
            "python": "Python",
            "sql": "SQL",
            "data analysis": "Data Analysis",
            "data analytics": "Data Analysis",
        }
        return domains.get(compact, label)

    def transform(self, raw_questions):
        """Extract embedded answers from questions"""
        transformed = []

        for q in raw_questions:
            question_text = q['question']
            answer_text = q['answer']
            difficulty_text = self.normalize_difficulty(q.get('difficulty', ''))

            # Extract embedded answer if present
            if '\nAnswer:' in question_text or '\nans:' in question_text.lower():
                parts = re.split(r'\n(answer|ans)\s*:\s*', question_text, flags=re.IGNORECASE)
                if len(parts) >= 3:
                    question_text = parts[0].strip()
                    answer_text = parts[2]
                    m = re.search(r'\n\s*difficulty\s+level\s*[:=]\s*(\w+)', answer_text, re.IGNORECASE)
                    if m:
                        difficulty_text = self.normalize_difficulty(m.group(1))
                        answer_text = re.sub(r'\n\s*difficulty\s+level\s*[:=]\s*\w+', '', answer_text, flags=re.IGNORECASE)

            question = re.sub(r'^\d+[.)]\s*', '', question_text).replace('**', '').strip()
            answer = answer_text.replace('**', '').strip()

            if question:
                transformed.append({
                    "id": q['id'],
                    "domain": self.normalize_domain(q['domain']),
                    "difficulty": difficulty_text,
                    "question": question,
                    "reference_answer": answer
                })

        print(f"Transformed {len(transformed)} questions")
        return transformed

    def save_json(self, questions, filename="transformed.json"):
        """Save to JSON"""
        output_file = self.output_path / filename
        temp = self.output_path / ".tmp"
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        temp.replace(output_file)
        print(f"  Saved: {output_file}")
