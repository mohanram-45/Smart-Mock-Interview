"""Okapi BM25 lexical baseline (no external dependency, deterministic)."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Optional, Sequence

import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = frozenset("""a an and are as at be but by for from has have how i if in into is it its of on or that the their then there
these they this to was were what when where which who why will with you your can do does did not no so such than too very""".split())


def tokenize(text: str) -> List[str]:
    out = []
    for t in _TOKEN.findall(text.lower()):
        if t in _STOP:
            continue
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]  # crude plural folding
        out.append(t)
    return out


class BM25:
    def __init__(self, texts: Sequence[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(t)) for t in texts]
        self.n = len(self.docs)
        self.dl = np.array([sum(d.values()) for d in self.docs], dtype=np.float64)
        self.avgdl = float(self.dl.mean()) if self.n else 0.0
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        self.idf: Dict[str, float] = {t: math.log(1 + (self.n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.postings: Dict[str, List] = {}
        for i, d in enumerate(self.docs):
            for t, tf in d.items():
                self.postings.setdefault(t, []).append((i, tf))

    def scores(self, query: str) -> np.ndarray:
        s = np.zeros(self.n, dtype=np.float64)
        for t in set(tokenize(query)):
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i, tf in self.postings[t]:
                denom = tf + self.k1 * (1 - self.b + self.b * self.dl[i] / self.avgdl)
                s[i] += idf * tf * (self.k1 + 1) / denom
        return s
