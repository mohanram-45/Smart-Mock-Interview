import hashlib
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeEmbedder:
    """Deterministic hashed bag-of-words embedder (test stand-in; no model download)."""
    backend = "fake"

    def __init__(self, dim=64, tag="a", scale=1.0):
        self.dim, self.tag, self.scale = dim, tag, scale
        self.calls = 0

    def config(self):
        return {"backend": "fake", "model": "hashed-bow", "dim": self.dim, "max_seq_length": 0, "normalised": True, "params": {"tag": self.tag}}

    def encode_raw(self, texts, batch_size=32):
        self.calls += len(texts)
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in re.findall(r"[a-z0-9]+", t.lower()):
                out[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % self.dim] += 1.0
        return out * self.scale  # deliberately NOT normalised: the pipeline must normalise


def make_record(qid, domain, topic, question, answer, concepts, origin="v5", difficulty="Medium"):
    return {"question_id": qid, "domain": domain, "topic": topic, "difficulty": difficulty, "question_type": "", "question": question,
            "canonical_answer": answer, "alternative_answers": {}, "answer_set": "single", "key_concepts": concepts,
            "common_mistakes": [], "rubric_points": "", "tags": [],
            "verification": {"verification": "ai_reviewed", "v6_verification": "", "human_reviewed": False, "has_code_test": False,
                             "source_opened": False, "code_executed": False, "time_sensitive": False, "review_by": "", "remaining_limitations": ""},
            "sources": [], "provenance": {"origin": origin, "batch": origin}}


@pytest.fixture()
def records():
    return [
        make_record("smi-0001", "SQL", "Joins", "What is an inner join?", "An inner join returns rows with matching keys in both tables.", ["inner join", "keys"]),
        make_record("smi-0002", "SQL", "Indexes", "Why use a clustered index?", "A clustered index orders table rows physically by the key.", ["clustered index", "b-tree"]),
        make_record("smi-0003", "Python", "Lists", "How do Python lists differ from tuples?", "Lists are mutable while tuples are immutable sequences.", ["mutable", "tuple"]),
        make_record("smi-0004", "Machine Learning", "Overfitting", "What is overfitting?", "Overfitting means a model memorises noise and generalises poorly.", ["overfitting", "regularisation"]),
        make_record("smi-g0001", "Generative AI & RAG", "Chunking", "How should documents be chunked for retrieval?", "Chunk by semantic sections with overlap to preserve context.", ["chunking", "overlap"], origin="batch_01"),
        make_record("smi-l0001", "MLOps & Model Deployment", "Drift", "How do you detect data drift in production?", "Compare live feature distributions with a reference using PSI or KS tests.", ["drift", "psi"], origin="batch_03"),
    ]


@pytest.fixture()
def embedder():
    return FakeEmbedder()


@pytest.fixture()
def real_root():
    return ROOT


@pytest.fixture()
def corpus_copy(tmp_path):
    """A private copy of just the files load_corpus reads, so tests can tamper without touching the project."""
    files = ["data/curated/v5/curated_questions.csv", "data/curated/v5/manifest.json", "data/curated/v5/code_tests.json",
             "data/expansion/approved_batches.json"]
    for n in range(1, 5):
        d = f"data/expansion/batch_0{n}"
        files += [f"{d}/batch_0{n}_accepted.csv", f"{d}/manifest.json", f"{d}/code_tests.json"]
    for f in files:
        dst = tmp_path / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / f, dst)
    return tmp_path
