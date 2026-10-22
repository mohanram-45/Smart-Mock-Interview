import math
from collections import Counter


class BM25:
    """Okapi BM25 with the non-negative idf ln(1 + (N - df + 0.5) / (df + 0.5)).

    docs: list of token lists. Repeated query terms are counted once.
    """

    def __init__(self, docs, k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.tfs = [Counter(d) for d in docs]
        self.lens = [len(d) for d in docs]
        self.n = len(docs)
        self.avgdl = sum(self.lens) / self.n
        self.df = Counter()
        for tf in self.tfs:
            self.df.update(tf.keys())

    def idf(self, term):
        df = self.df.get(term, 0)
        return math.log(1.0 + (self.n - df + 0.5) / (df + 0.5))

    def score(self, query, i):
        tf = self.tfs[i]
        norm = 1.0 - self.b + self.b * self.lens[i] / self.avgdl
        total = 0.0
        for t in set(query):
            f = tf.get(t, 0)
            if f:
                total += self.idf(t) * f * (self.k1 + 1.0) / (f + self.k1 * norm)
        return total

    def rank(self, query, top_n=None):
        scored = [(i, self.score(query, i)) for i in range(self.n)]
        scored.sort(key=lambda p: (-p[1], p[0]))
        return scored[:top_n] if top_n is not None else scored

docs = [
    "error e4417 timeout on payment gateway".split(),
    "how to reset your password".split(),
    "payment timeout error troubleshooting guide for the payment gateway and the payment api".split(),
    "payment".split(),
]
bm = BM25(docs, k1=1.2, b=0.75)
# hand-computed check for doc 0, term 'e4417' (df=1, N=4, dl=6)
avgdl = sum(len(d) for d in docs) / 4
idf = math.log(1 + (4 - 1 + 0.5) / (1 + 0.5))
expect = idf * 1 * 2.2 / (1 + 1.2 * (0.25 + 0.75 * 6 / avgdl))
assert abs(bm.score(["e4417"], 0) - expect) < 1e-12
# repeated query terms count once; unknown terms score 0
assert bm.score(["e4417", "e4417"], 0) == bm.score(["e4417"], 0)
assert bm.score(["zzz"], 0) == 0.0 and bm.idf("zzz") > 0
# term-frequency saturation: with b=0 the tf factor never exceeds k1+1
flat = BM25([["a"] * 1, ["a"] * 5, ["a"] * 50, ["a"] * 500, ["b"]], k1=1.2, b=0.0)
s = [flat.score(["a"], i) / flat.idf("a") for i in range(4)]
assert all(x < 2.2 for x in s) and s == sorted(s)
assert s[3] - s[2] < s[1] - s[0]
# length normalisation: same tf, longer document scores lower when b > 0
pair = BM25([["x", "y"], ["x"] + ["pad"] * 30, ["other"]], k1=1.2, b=0.75)
assert pair.score(["x"], 0) > pair.score(["x"], 1)
same = BM25([["x", "y"], ["x"] + ["pad"] * 30, ["other"]], k1=1.2, b=0.0)
assert abs(same.score(["x"], 0) / same.idf("x") - same.score(["x"], 1) / same.idf("x")) < 1e-12
assert bm.rank(["e4417"], top_n=1)[0][0] == 0
# idf is positive even for a term present in every document
allhave = BM25([["t", "a"], ["t", "b"]])
assert allhave.idf("t") > 0
