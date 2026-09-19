"""Pipeline: Ingestion -> Transformation -> Cleaning"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_ingestion import DataIngestion
from data_transformation import DataTransformation
from data_cleaner import DataCleaner


if __name__ == "__main__":
    print("\n" + "="*70)
    print("PIPELINE: INGESTION -> TRANSFORMATION -> CLEANING")
    print("="*70 + "\n")

    root = Path(__file__).parent.parent.parent
    raw_path = root / "data" / "raw"
    interim_path = root / "data" / "interim"
    processed_path = root / "data" / "processed"

    interim_path.mkdir(parents=True, exist_ok=True)
    processed_path.mkdir(parents=True, exist_ok=True)

    print("STEP 1: INGESTION (raw -> interim)")
    ingestion = DataIngestion(raw_path)
    questions = ingestion.load_raw_data()

    print("\nSTEP 2: TRANSFORMATION (interim)")
    transformation = DataTransformation(interim_path)
    questions = transformation.transform(questions)
    transformation.save_json(questions, "transformed.json")

    print("\nSTEP 3: CLEANING (interim -> processed)")
    cleaner = DataCleaner(processed_path)
    questions = cleaner.clean(questions)
    cleaner.save_json(questions, "questions_cleaned.json")
    cleaner.save_csv(questions, "questions.csv")

    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70 + "\n")
