import numpy as np


def exact_topk(queries, base, k):
    """Exact L2 top-k ids (ground truth), best first, ties by lower id."""
    d = ((queries[:, None, :] - base[None, :, :]) ** 2).sum(axis=2)
    return np.argsort(d, axis=1, kind="stable")[:, :k]


def ann_recall_at_k(exact_ids, approx_ids):
    """Mean over queries of |exact ∩ approx| / k. Entries of -1 are padding."""
    exact_ids = np.asarray(exact_ids)
    approx_ids = np.asarray(approx_ids)
    k = exact_ids.shape[1]
    hits = [len(set(e.tolist()) & (set(a.tolist()) - {-1}))
            for e, a in zip(exact_ids, approx_ids)]
    return float(np.mean(hits)) / k


class ToyIVF:
    """Inverted-file index: k-means coarse quantiser, exact rerank inside probed lists."""

    def __init__(self, base, nlist, seed=0, iters=15):
        rng = np.random.default_rng(seed)
        self.base = base
        cent = base[rng.choice(len(base), nlist, replace=False)].copy()
        for _ in range(iters):
            assign = self._nearest(base, cent, 1)[:, 0]
            for c in range(nlist):
                members = base[assign == c]
                if len(members):
                    cent[c] = members.mean(axis=0)
        self.cent = cent
        assign = self._nearest(base, cent, 1)[:, 0]
        self.lists = [np.flatnonzero(assign == c) for c in range(nlist)]

    @staticmethod
    def _nearest(x, cent, n):
        d = ((x[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2)
        return np.argsort(d, axis=1, kind="stable")[:, :n]

    def search(self, queries, k, nprobe):
        out = np.full((len(queries), k), -1, dtype=np.int64)
        probes = self._nearest(queries, self.cent, nprobe)
        for qi, q in enumerate(queries):
            cand = np.concatenate([self.lists[c] for c in probes[qi]])
            if len(cand) == 0:
                continue
            d = ((self.base[cand] - q) ** 2).sum(axis=1)
            top = cand[np.argsort(d, kind="stable")[:k]]
            out[qi, :len(top)] = top
        return out

rng = np.random.default_rng(1)
centers = rng.normal(size=(20, 16)) * 1.2
base = np.vstack([c + rng.normal(size=(100, 16)) for c in centers])
queries = base[rng.choice(len(base), 40, replace=False)] + rng.normal(size=(40, 16)) * 0.8
k = 10
truth = exact_topk(queries, base, k)
assert ann_recall_at_k(truth, truth) == 1.0
assert ann_recall_at_k([[1, 2, 3]], [[3, 9, -1]]) == 1 / 3
index = ToyIVF(base, nlist=20, seed=0)
recalls = [ann_recall_at_k(truth, index.search(queries, k, p)) for p in (1, 2, 4, 8, 20)]
print(recalls)
assert all(a <= b + 1e-12 for a, b in zip(recalls, recalls[1:]))
assert recalls[0] < 1.0
assert recalls[-1] == 1.0
