"""Unified registry for the 3 answer-scoring models.

The project has three independent scorers (Siamese Bi-LSTM, Sentence-BERT,
TF-IDF + Grammar) with three different native return types. This module
wraps all three behind one interface:

    scorer.score(reference_answer, user_answer) -> float in [0.0, 1.0]

so callers (interview_session.py) never need to know which model is
active. A session picks ONE model at start time and uses it for every
question for the rest of that session.

Each model is loaded/trained at most once per process and then shared
across every session that picks it (loading a transformer or training a
network per-request would be far too slow).
"""
from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Keys used everywhere else (API requests, session state, cache keys).
MODEL_CHOICES: Dict[str, Dict[str, str]] = {
    "bilstm": {
        "label": "Siamese Bi-LSTM",
        "description": (
            "Custom neural network trained from scratch on this project's own "
            "question/answer pairs. Fast once trained, but only ever saw "
            "exact-match positives, so it is stricter with reworded answers."
        ),
    },
    "bert": {
        "label": "Sentence-BERT",
        "description": (
            "Pretrained transformer (all-MiniLM-L6-v2) fine-tuned on 1B+ general "
            "sentence pairs. Best at recognizing correct answers phrased in your "
            "own words."
        ),
    },
    "tfidf": {
        "label": "TF-IDF + Grammar",
        "description": (
            "Classic keyword-overlap similarity plus a grammar check. Fastest "
            "and simplest, but purely statistical - it rewards matching "
            "vocabulary rather than matching meaning."
        ),
    },
}

DEFAULT_MODEL = "bilstm"

_lock = threading.Lock()
_cache: Dict[str, "_BaseAdapter"] = {}


def readiness(model_key: str) -> Dict[str, object]:
    """Can this scorer be loaded WITHOUT training or downloading anything? Cheap (no torch / transformers import) and side-effect free.

    {"ready": bool, "reason": str|None, "hint": str|None}. `get_scorer` behaves exactly as before (the legacy /api routes still train the Bi-LSTM on first use if no
    checkpoint exists); this probe lets a caller decide not to.
    """
    import importlib.util
    import os
    from pathlib import Path
    if model_key not in MODEL_CHOICES:
        return {"ready": False, "reason": f"Unknown model '{model_key}'.", "hint": None}
    root = Path(__file__).resolve().parents[2]
    if model_key == "bilstm":
        if importlib.util.find_spec("torch") is None:
            return {"ready": False, "reason": "PyTorch is not installed.", "hint": "pip install torch"}
        ckpt = root / "results" / "siamese_bilstm.pt"
        if not ckpt.exists():
            return {"ready": False, "reason": "No trained Bi-LSTM checkpoint was found (results/siamese_bilstm.pt). Using it would start a multi-minute training run.",
                    "hint": "Train it once on purpose: python src\\model\\SiameseBiLSTM.py"}
        return {"ready": True, "reason": None, "hint": None}
    if model_key == "bert":
        if importlib.util.find_spec("sentence_transformers") is None:
            return {"ready": False, "reason": "sentence-transformers is not installed.", "hint": "pip install sentence-transformers"}
        hub = Path(os.environ.get("HF_HOME") or (Path.home() / ".cache" / "huggingface")) / "hub"
        if os.environ.get("HF_HUB_CACHE"):
            hub = Path(os.environ["HF_HUB_CACHE"])
        cached = (hub / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots")
        if not (cached.exists() and any(cached.iterdir())):
            return {"ready": False, "reason": "The Sentence-BERT model (all-MiniLM-L6-v2, about 90 MB) is not in the local cache, so first use would download it.",
                    "hint": "Run once with internet access: python src\\model\\Pretrained_NEURALN.py"}
        return {"ready": True, "reason": None, "hint": None}
    if importlib.util.find_spec("sklearn") is None:
        return {"ready": False, "reason": "scikit-learn is not installed.", "hint": "pip install scikit-learn"}
    if importlib.util.find_spec("language_tool_python") is None:            # TraditionalMLScorer imports it at module level
        return {"ready": False, "reason": "language-tool-python is not installed (the TF-IDF scorer's grammar checker).", "hint": "pip install language-tool-python"}
    ltp = Path(os.environ.get("LTP_PATH") or (Path.home() / ".cache" / "language_tool_python"))
    if not (ltp.exists() and any(ltp.iterdir())):                              # its first use downloads LanguageTool (a few hundred MB) and needs Java
        return {"ready": False, "reason": "The grammar checker (LanguageTool) has not been downloaded yet, so first use of the TF-IDF scorer would download it (a few hundred MB, needs Java).",
                "hint": "Run once with internet access and Java installed: python -c \"import language_tool_python as l; l.LanguageTool('en-US')\""}
    return {"ready": True, "reason": None, "hint": None}


def is_valid_model(model_key: Optional[str]) -> bool:
    return model_key in MODEL_CHOICES


def list_models() -> List[Dict[str, str]]:
    return [{"key": key, **meta} for key, meta in MODEL_CHOICES.items()]


class _BaseAdapter:
    def ensure_ready(self) -> None:
        """Hook for models that need a one-time warmup (e.g. training)."""

    def score(self, reference_answer: str, user_answer: str) -> float:
        raise NotImplementedError


class _BiLSTMAdapter(_BaseAdapter):
    """Wraps SiameseBiLSTM. Needs an explicit training pass if no checkpoint exists."""

    def __init__(self) -> None:
        from SiameseBiLSTM import SiameseBiLSTM
        self._model = SiameseBiLSTM()

    def ensure_ready(self) -> None:
        if not self._model.is_trained:
            import os
            if os.environ.get("SMART_FORBID_MODEL_TRAINING", "").strip().lower() in ("1", "true", "yes", "on"):
                # Container/CI guard (set in Dockerfile and docker-compose.yml): a request must never start a multi-minute training run. Unset = legacy behaviour.
                raise RuntimeError("No trained Bi-LSTM checkpoint (results/siamese_bilstm.pt) and SMART_FORBID_MODEL_TRAINING is set, so training was refused. "
                                   "Train once on a development machine (python -m ...), or choose another scorer.")
            logger.info("Training Siamese Bi-LSTM from questions_cleaned.json (first use)")
            self._model.train_from_dataset(epochs=10)

    def score(self, reference_answer: str, user_answer: str) -> float:
        return float(self._model.score(reference_answer, user_answer))


class _BertAdapter(_BaseAdapter):
    """Wraps SentenceBertAnswerScorer, which returns a dict, not a bare float."""

    def __init__(self) -> None:
        from Pretrained_NEURALN import SentenceBertAnswerScorer
        self._model = SentenceBertAnswerScorer()

    def score(self, reference_answer: str, user_answer: str) -> float:
        result = self._model.score(reference_answer, user_answer)
        similarity = float(result["similarity"])
        return max(0.0, min(1.0, similarity))


class _TfidfAdapter(_BaseAdapter):
    """Wraps TraditionalMLScorer. Vectorizer benefits from seeing the full
    question corpus up front, so it's optionally passed in at load time."""

    def __init__(self, corpus: Optional[List[str]] = None) -> None:
        from TraditionalMLScorer import TraditionalMLScorer
        self._model = TraditionalMLScorer(all_questions=corpus)

    def score(self, reference_answer: str, user_answer: str) -> float:
        result = self._model.score(reference_answer, user_answer)
        # Use pure semantic similarity (score_percent), not the grammar-blended
        # final_score, so this stays directly comparable to the other 2 models.
        percent = float(result["score_percent"])
        return max(0.0, min(1.0, percent / 100.0))


_ADAPTER_CLASSES = {
    "bilstm": _BiLSTMAdapter,
    "bert": _BertAdapter,
    "tfidf": _TfidfAdapter,
}


def get_scorer(model_key: str, corpus: Optional[List[str]] = None) -> _BaseAdapter:
    """Return the shared, cached scorer instance for the given model key.

    Loading/training happens once per process per model. `corpus` (reference
    answers) is only used the first time the tfidf model is requested, to
    train its vectorizer.
    """
    if not is_valid_model(model_key):
        raise ValueError(f"Unknown model '{model_key}'. Choose from: {list(MODEL_CHOICES)}")

    with _lock:
        if model_key not in _cache:
            logger.info(f"Loading scoring model '{model_key}' for the first time")
            if model_key == "tfidf":
                _cache[model_key] = _TfidfAdapter(corpus=corpus)
            else:
                _cache[model_key] = _ADAPTER_CLASSES[model_key]()
        scorer = _cache[model_key]

    scorer.ensure_ready()
    return scorer
