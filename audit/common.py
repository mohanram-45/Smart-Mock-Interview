"""Shared helpers for the dataset audit. READ-ONLY: never writes to data/."""
import argparse, csv, json, re
from pathlib import Path

def get_root():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = Path(a.root)
    out = Path(a.out) if a.out else Path(__file__).resolve().parent / "output"
    out.mkdir(parents=True, exist_ok=True)
    return root, out

def load_all(root):
    import pandas as pd
    raw_seed = pd.read_csv(root/"data/raw/questions_seed.csv", dtype=str, keep_default_na=False)
    raw_exp  = pd.read_csv(root/"data/raw/expanded_interview_questions.csv", dtype=str, keep_default_na=False)
    interim  = pd.DataFrame(json.load(open(root/"data/interim/transformed.json", encoding="utf-8")))
    proc_js  = pd.DataFrame(json.load(open(root/"data/processed/questions_cleaned.json", encoding="utf-8")))
    proc_csv = pd.read_csv(root/"data/processed/questions.csv", dtype=str, keep_default_na=False)
    return raw_seed, raw_exp, interim, proc_js, proc_csv

def norm_q(t):
    """Mirror DataTransformation question normalisation so rows can be joined across stages."""
    t = re.sub(r'^\d+[.)]\s*', '', str(t)).replace('**', '').strip()
    return " ".join(t.lower().split())

def wc(t): return len(str(t).split())

def dump(out, name, obj):
    with open(out/name, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=str)
