"""Data Transformation - Extract embedded answers"""
import json
import re
from pathlib import Path


class DataTransformation:
    """Transform raw questions"""

    def __init__(self, output_path):
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)

    def transform(self, raw_questions):
        """Extract embedded answers from questions"""
        transformed = []

        for q in raw_questions:
            question_text = q['question']
            answer_text = q['answer']
            difficulty_text = q.get('difficulty', '')

            # Extract embedded answer if present
            if '\nAnswer:' in question_text or '\nans:' in question_text.lower():
                parts = re.split(r'\n(answer|ans)\s*:\s*', question_text, flags=re.IGNORECASE)
                if len(parts) >= 3:
                    question_text = parts[0].strip()
                    answer_text = parts[2]
                    m = re.search(r'\n\s*difficulty\s+level\s*[:=]\s*(\w+)', answer_text, re.IGNORECASE)
                    if m:
                        difficulty_text = m.group(1).capitalize()
                        answer_text = re.sub(r'\n\s*difficulty\s+level\s*[:=]\s*\w+', '', answer_text, flags=re.IGNORECASE)

            question = re.sub(r'^\d+[.)]\s*', '', question_text).replace('**', '').strip()
            answer = answer_text.replace('**', '').strip()

            if question:
                transformed.append({
                    "id": q['id'],
                    "domain": q['domain'],
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
