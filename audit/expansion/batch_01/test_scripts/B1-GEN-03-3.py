from fractions import Fraction


def rrf(rankings, k=60, top_n=None):
    """Reciprocal Rank Fusion.

    rankings: list of ranked lists of doc ids (best first). Repeats inside one
    list are dropped (first occurrence kept) before ranks are assigned.
    Returns [(doc, score)] best first; exact ties are broken by first
    appearance (earlier list, then earlier position).
    """
    scores = {}
    first_seen = {}
    for list_no, ranking in enumerate(rankings):
        deduped = list(dict.fromkeys(ranking))
        for pos, doc in enumerate(deduped, start=1):
            scores[doc] = scores.get(doc, Fraction(0)) + Fraction(1, k + pos)
            first_seen.setdefault(doc, (list_no, pos))
    ordered = sorted(scores, key=lambda d: (-scores[d], first_seen[d]))
    if top_n is not None:
        ordered = ordered[:top_n]
    return [(d, float(scores[d])) for d in ordered]

a = ["d1", "d2", "d3"]
b = ["d3", "d1", "d4"]
res = rrf([a, b], k=60)
assert [d for d, _ in res] == ["d1", "d3", "d2", "d4"]
assert abs(dict(res)["d1"] - (1 / 61 + 1 / 62)) < 1e-15
assert abs(dict(res)["d4"] - 1 / 63) < 1e-15
# exact tie -> first appearance wins
assert [d for d, _ in rrf([["a", "b"], ["b", "a"]])] == ["a", "b"]
# repeats are dropped before ranking
assert rrf([["x", "x", "y"]]) == rrf([["x", "y"]])
# top_n and empty inputs
assert len(rrf([a, b], top_n=2)) == 2
assert rrf([]) == [] and rrf([[], []]) == []
# a doc found by both lists at modest ranks beats a single-list rank-1 doc
res = rrf([["solo", "p", "q"], ["z", "p2", "p"]], k=60)
assert res[0][0] == "p"
# small k makes the top ranks dominate
assert rrf([["solo", "x", "p"], ["z", "y", "p"]], k=0)[0][0] == "solo"
assert rrf([["solo", "x", "p"], ["z", "y", "p"]], k=60)[0][0] == "p"
