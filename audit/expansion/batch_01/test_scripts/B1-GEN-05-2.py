from collections import Counter


def cohen_kappa(human, judge):
    """Cohen's kappa for two equal-length label sequences (any hashable labels)."""
    n = len(human)
    if n == 0 or n != len(judge):
        raise ValueError("need two non-empty sequences of equal length")
    p_o = sum(h == j for h, j in zip(human, judge)) / n
    ch, cj = Counter(human), Counter(judge)
    p_e = sum(ch[c] * cj[c] for c in set(ch) | set(cj)) / (n * n)
    if p_e == 1.0:
        return 1.0 if p_o == 1.0 else 0.0
    return (p_o - p_e) / (1.0 - p_e)

def _labels(tp, fn, fp, tn):
    # tp: both 'ok'; fn: human 'ok', judge 'bad'; fp: human 'bad', judge 'ok'; tn: both 'bad'
    human = ["ok"] * tp + ["ok"] * fn + ["bad"] * fp + ["bad"] * tn
    judge = ["ok"] * tp + ["bad"] * fn + ["ok"] * fp + ["bad"] * tn
    return human, judge


h, j = _labels(88, 2, 7, 3)
raw = sum(x == y for x, y in zip(h, j)) / len(h)
assert abs(raw - 0.91) < 1e-12
k = cohen_kappa(h, j)
assert abs(k - (0.91 - 0.86) / 0.14) < 1e-12 and 0.35 < k < 0.36
# balanced classes with the same raw agreement give a much higher kappa
h2, j2 = _labels(46, 4, 5, 45)
assert abs(sum(x == y for x, y in zip(h2, j2)) / 100 - 0.91) < 1e-12
assert abs(cohen_kappa(h2, j2) - 0.82) < 1e-12
assert cohen_kappa(h, h) == 1.0
assert cohen_kappa(["a", "b", "a", "b"], ["b", "a", "b", "a"]) == -1.0
assert cohen_kappa(["ok"] * 5, ["ok"] * 5) == 1.0
print("ok")
