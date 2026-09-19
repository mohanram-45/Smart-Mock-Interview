"""Data Ingestion - Load raw DOCX/CSV/TXT files"""
import re
import csv
from pathlib import Path


class DataIngestion:
    """Load raw files and extract Q&A"""

    def __init__(self, raw_data_path):
        self.raw_data_path = Path(raw_data_path)

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
        return labels.get(label, "")

    def load_raw_data(self):
        """Load all DOCX, CSV, TXT files"""
        questions, q_id = [], 1

        for docx_file in sorted(self.raw_data_path.glob("*.docx")):
            try:
                from docx import Document

                paras = [p.text.strip() for p in Document(docx_file).paragraphs if p.text.strip()]
                domain = docx_file.stem
                has_prefixed = any(p.startswith('Question:') for p in paras[:20])
                if has_prefixed:
                    q_id = self._parse_prefixed(paras, domain, q_id, questions)
                else:
                    q_id = self._parse_numbered(paras, domain, q_id, questions)
            except Exception as e:
                print(f"  Skipped {docx_file.name}: {type(e).__name__}")

        for csv_file in sorted(self.raw_data_path.glob("*.csv")):
            try:
                with open(csv_file, encoding='utf-8') as f:
                    for row in csv.DictReader(f):
                        questions.append({
                            "id": q_id,
                            "domain": row.get('domain', csv_file.stem),
                            "difficulty": self.normalize_difficulty(row.get('difficulty', '')),
                            "question": row.get('question', ''),
                            "answer": row.get('answer', '')
                        })
                        q_id += 1
            except Exception as e:
                print(f"  Skipped {csv_file.name}: {type(e).__name__}")

        for txt_file in sorted(self.raw_data_path.glob("*.txt")):
            try:
                lines = open(txt_file, encoding='utf-8').read().split('\n')
                domain = txt_file.stem
                i = 0
                while i < len(lines):
                    if lines[i].strip().startswith('Question:'):
                        q = lines[i].replace('Question:', '').strip()
                        a = d = ""
                        i += 1
                        while i < len(lines) and not lines[i].strip().startswith('Question:'):
                            if lines[i].strip().startswith('Answer:'):
                                a = lines[i].replace('Answer:', '').strip()
                            elif 'Difficulty' in lines[i]:
                                m = re.search(r'(\w+)$', lines[i])
                                if m:
                                    d = self.normalize_difficulty(m.group(1))
                            i += 1
                        if q and a:
                            questions.append({"id": q_id, "domain": domain, "difficulty": d, "question": q, "answer": a})
                            q_id += 1
                    else:
                        i += 1
            except Exception as e:
                print(f"  Skipped {txt_file.name}: {type(e).__name__}")

        print(f"Loaded {len(questions)} questions")
        return questions

    def _parse_prefixed(self, paras, domain, q_id, questions):
        """Parse Question:/Answer:/Difficulty: format"""
        i = 0
        while i < len(paras):
            if paras[i].startswith('Question:'):
                q = paras[i].replace('Question:', '').strip()
                a = d = ""
                i += 1
                while i < len(paras) and not paras[i].startswith('Question:'):
                    if paras[i].startswith('Answer:'):
                        a = paras[i].replace('Answer:', '').strip()
                    elif 'difficulty' in paras[i].lower():
                        m = re.search(r'(\w+)$', paras[i])
                        if m:
                            d = self.normalize_difficulty(m.group(1))
                    i += 1
                if q and a:
                    questions.append({"id": q_id, "domain": domain, "difficulty": d, "question": q, "answer": a})
                    q_id += 1
            else:
                i += 1
        return q_id

    def _parse_numbered(self, paras, domain, q_id, questions):
        """Parse 1. Question / Answer / Difficulty format"""
        i = 0
        while i < len(paras):
            if re.match(r'^\d+[.)]\s+', paras[i]):
                q = re.sub(r'^\d+[.)]\s*', '', paras[i])
                a = d = ""
                a_lines = []
                i += 1
                while i < len(paras) and not re.match(r'^\d+[.)]\s+', paras[i]):
                    if 'difficulty' in paras[i].lower():
                        m = re.search(r'(\w+)$', paras[i])
                        if m:
                            d = self.normalize_difficulty(m.group(1))
                        i += 1
                        break
                    if re.match(r'^(answer|ans)\s*[:–-]\s*', paras[i], re.IGNORECASE):
                        content = re.sub(r'^(answer|ans)\s*[:–-]\s*', '', paras[i], flags=re.IGNORECASE)
                        if content:
                            a_lines.append(content)
                    elif paras[i]:
                        a_lines.append(paras[i])
                    i += 1
                a = '\n'.join(a_lines) if a_lines else ""
                if q and a:
                    questions.append({"id": q_id, "domain": domain, "difficulty": d, "question": q, "answer": a})
                    q_id += 1
            else:
                i += 1
        return q_id
