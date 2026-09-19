"""Remove copied interview-list boilerplate from dataset text fields."""
import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOILERPLATE_PATTERN = re.compile(
    r"Next up on this top Deep Learning interview questions and answers blog, "
    r"let us take a look at the [a-z]+ questions\. [A-Za-z]+ Interview Questions"
)


def clean_text(value):
    text = str(value or "")
    text = BOILERPLATE_PATTERN.sub("", text)
    return " ".join(text.split())


def clean_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    for row in rows:
        for field in ("question", "answer", "reference_answer"):
            if field in row:
                row[field] = clean_text(row[field])

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clean_json(path):
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)

    for row in rows:
        for field in ("question", "answer", "reference_answer"):
            if field in row:
                row[field] = clean_text(row[field])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)


def main():
    clean_csv(ROOT / "data" / "raw" / "questions_seed.csv")
    print("Cleaned dataset boilerplate")


if __name__ == "__main__":
    main()
