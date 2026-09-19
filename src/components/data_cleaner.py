"""Data Cleaner - Remove duplicates, nulls, bad data"""
import json
import csv
from pathlib import Path


class DataCleaner:
    """Clean questions - 9 operations"""

    def __init__(self, output_path):
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.removed_log = {}

    def is_null(self, value):
        """Check if value is None"""
        return value is None

    def is_blank(self, value):
        """Check if value is empty string"""
        if self.is_null(value):
            return True
        return str(value).strip() == ""

    def word_count(self, text):
        """Count words"""
        if self.is_blank(text):
            return 0
        return len(str(text).split())

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
        return labels.get(label)

    def complexity_score(self, question):
        """Estimate technical complexity for deterministic difficulty balancing."""
        text = f"{question.get('question', '')} {question.get('reference_answer', '')}".lower()
        score = self.word_count(text)
        hard_terms = [
            'optimisation', 'optimization', 'architecture', 'distributed',
            'production', 'trade-off', 'complexity', 'gradient', 'transformer',
            'window function', 'hypothesis', 'confidence interval'
        ]
        score += sum(25 for term in hard_terms if term in text)
        return score

    def rebalance_difficulties(self, questions):
        """Apply the requested Easy/Medium/Hard 30/45/25 distribution."""
        total = len(questions)
        target = {
            'Easy': round(total * 0.30),
            'Medium': round(total * 0.45),
        }
        target['Hard'] = total - target['Easy'] - target['Medium']

        ranked = sorted(
            questions,
            key=lambda item: (self.complexity_score(item), str(item.get('question', '')))
        )
        easy_cutoff = target['Easy']
        medium_cutoff = target['Easy'] + target['Medium']

        for index, item in enumerate(ranked):
            if index < easy_cutoff:
                item['difficulty'] = 'Easy'
            elif index < medium_cutoff:
                item['difficulty'] = 'Medium'
            else:
                item['difficulty'] = 'Hard'

        return questions

    def clean(self, questions):
        """Apply cleaning operations"""

        self.removed_log = {
            'duplicates': 0,
            'null_questions': 0,
            'null_answers': 0,
            'blank_questions': 0,
            'blank_answers': 0,
            'bad_difficulty': 0,
            'short_answers': 0,
            'long_answers': 0,
            'half_broken': 0,
            'bad_ids': 0
        }

        # 1. Remove duplicates
        seen = set()
        q1 = []

        for q in questions:
            qt = str(q.get('question', '')).strip().lower()

            if qt and qt not in seen:
                seen.add(qt)
                q1.append(q)
            elif qt:
                self.removed_log['duplicates'] += 1

        # 2. Remove null questions
        q2 = []

        for q in q1:
            if not self.is_null(q.get('question')):
                q2.append(q)
            else:
                self.removed_log['null_questions'] += 1

        # 3. Remove null answers
        q3 = []

        for q in q2:
            if not self.is_null(q.get('reference_answer')):
                q3.append(q)
            else:
                self.removed_log['null_answers'] += 1

        # 4. Remove blank questions
        q4 = []

        for q in q3:
            if not self.is_blank(q.get('question')):
                q4.append(q)
            else:
                self.removed_log['blank_questions'] += 1

        # 5. Remove blank answers
        q5 = []

        for q in q4:
            if not self.is_blank(q.get('reference_answer')):
                q5.append(q)
            else:
                self.removed_log['blank_answers'] += 1

        # 6. Validate difficulty
        valid_difficulties = {'Easy', 'Medium', 'Hard'}

        q6 = []

        for q in q5:
            difficulty = q.get('difficulty')

            if difficulty is None:
                self.removed_log['bad_difficulty'] += 1
                continue

            normalized_difficulty = self.normalize_difficulty(difficulty)

            if str(difficulty).strip().lower() == 'nan':
                self.removed_log['bad_difficulty'] += 1
                continue

            if normalized_difficulty not in valid_difficulties:
                self.removed_log['bad_difficulty'] += 1
                continue

            q['difficulty'] = normalized_difficulty
            q6.append(q)

        q6 = self.rebalance_difficulties(q6)

        # 7. Remove short answers (<1 word)
        q7 = []

        for q in q6:
            wc = self.word_count(q.get('reference_answer', ''))

            if wc >= 1:
                q7.append(q)
            else:
                self.removed_log['short_answers'] += 1

        # 8. Remove long answers (>300 words)
        q8 = []

        for q in q7:
            wc = self.word_count(q.get('reference_answer', ''))

            if wc <= 300:
                q8.append(q)
            else:
                self.removed_log['long_answers'] += 1

        # 9. Remove half-broken questions
        final = []

        for q in q8:
            question = str(q.get('question', '')).strip()

            if not question.endswith('\n'):
                final.append(q)
            else:
                self.removed_log['half_broken'] += 1

        self.removed_log['bad_ids'] = 0

        print(f"Cleaned {len(final)} questions")
        print(f"  Removed: {sum(self.removed_log.values())} total")

        for reason, count in self.removed_log.items():
            if count > 0:
                print(f"    - {reason}: {count}")
                
        for i, q in enumerate(final):
            q["id"] = i + 1

        return final

            

    def save_json(self, questions, filename="questions_cleaned.json"):
        """Save to JSON"""
        output_file = self.output_path / filename
        temp = self.output_path / ".tmp"
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        temp.replace(output_file)
        print(f"  Saved JSON: {output_file}")

    def save_csv(self, questions, filename="questions_cleaned.csv"):
        """Save to CSV"""
        output_file = self.output_path / filename
        if not questions:
            return
        temp = self.output_path / ".tmp2"
        with open(temp, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'domain', 'difficulty', 'question', 'reference_answer'])
            writer.writeheader()
            writer.writerows(questions)
        temp.replace(output_file)
        print(f"  Saved CSV: {output_file}")
