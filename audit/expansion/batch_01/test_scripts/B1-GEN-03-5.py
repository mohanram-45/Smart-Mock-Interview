import numpy as np


def mmr(query, docs, k, lam=0.5):
    """Maximal Marginal Relevance over cosine similarity.

    Greedy: at each step pick argmax of lam * sim(q, d) - (1 - lam) * max_{s in selected} sim(d, s).
    Ties go to the lower index; a zero-norm vector is treated as similarity 0 to everything.
    Returns the selected indices in selection order.
    """
    if not 0.0 <= lam <= 1.0:
        raise ValueError("lam must be in [0, 1]")
    q = np.asarray(query, dtype=float)
    d = np.asarray(docs, dtype=float)

    def unit(m):
        n = np.linalg.norm(m, axis=-1, keepdims=True)
        return np.divide(m, n, out=np.zeros_like(m), where=n > 0)

    q, d = unit(q), unit(d)
    rel = d @ q
    pair = d @ d.T
    remaining = list(range(len(d)))
    chosen = []
    while remaining and len(chosen) < k:
        best, best_score = None, -np.inf
        for i in remaining:
            red = max(pair[i, j] for j in chosen) if chosen else 0.0
            score = lam * rel[i] - (1.0 - lam) * red
            if score > best_score:
                best, best_score = i, score
        chosen.append(best)
        remaining.remove(best)
    return chosen

q = [1.0, 0.2, 0.0]
docs = [
    [1.0, 0.25, 0.0],   # 0: most relevant
    [1.0, 0.26, 0.0],   # 1: near-duplicate of 0
    [0.7, 0.0, 0.7],    # 2: different facet, moderately relevant
    [0.0, 0.0, 1.0],    # 3: unrelated
]
assert mmr(q, docs, 3, lam=1.0) == [0, 1, 2]       # pure relevance keeps the duplicate
assert mmr(q, docs, 3, lam=0.5)[:2] == [0, 2]      # diversity skips the duplicate
assert mmr(q, docs, 10, lam=0.5) == mmr(q, docs, 4, lam=0.5)
assert sorted(mmr(q, docs, 4, lam=0.0)) == [0, 1, 2, 3]
assert mmr(q, docs, 0) == []
assert mmr(q, [[0, 0, 0], [1, 0.2, 0]], 2, lam=0.7) == [1, 0]
# scale invariance of cosine
assert mmr(q, np.array(docs) * 7.0, 3, lam=0.5) == mmr(q, docs, 3, lam=0.5)
