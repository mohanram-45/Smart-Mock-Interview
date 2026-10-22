def evidence_coverage(ranked, groups, k):
    """ranked: list of chunk ids. groups: list of sets; a group is covered if ANY of
    its chunk ids is in the top-k. Returns (fraction of groups covered, all covered)."""
    if not groups:
        raise ValueError("a question needs at least one evidence group")
    top = set(ranked[:k]) if k > 0 else set()
    covered = sum(1 for g in groups if g & top)
    return covered / len(groups), covered == len(groups)


def aggregate(runs, k):
    """runs: list of (ranked, groups). Returns (mean coverage, full-coverage rate)."""
    res = [evidence_coverage(r, g, k) for r, g in runs]
    n = len(res)
    return sum(c for c, _ in res) / n, sum(1 for _, ok in res if ok) / n

runs = [
    (["c1", "c9", "c2", "c7"], [{"c1"}, {"c2", "c20"}]),   # both groups by rank 3
    (["c5", "c3", "c8", "c4"], [{"c3"}, {"c6"}]),          # only first group in top-4
    (["c10", "c11"], [{"c12"}]),                            # miss
    (["c1", "c2", "c3", "c4"], [{"c4"}, {"c3"}, {"c40"}]),  # 2 of 3 groups
]
assert evidence_coverage(runs[0][0], runs[0][1], 2) == (0.5, False)
assert evidence_coverage(runs[0][0], runs[0][1], 3) == (1.0, True)
assert evidence_coverage(runs[3][0], runs[3][1], 4) == (2 / 3, False)
assert evidence_coverage(runs[2][0], runs[2][1], 0) == (0.0, False)
m3, f3 = aggregate(runs, 3)
m4, f4 = aggregate(runs, 4)
assert (m3, f3) == ((1.0 + 0.5 + 0.0 + 1 / 3) / 4, 0.25), (m3, f3)
assert (m4, f4) == ((1.0 + 0.5 + 0.0 + 2 / 3) / 4, 0.25), (m4, f4)
print(m3, f3, m4, f4)
print("ok")
