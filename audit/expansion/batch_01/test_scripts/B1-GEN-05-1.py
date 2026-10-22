import numpy as np


def paired_bootstrap_ci(a, b, n_boot=10000, alpha=0.05, seed=0):
    """Percentile bootstrap CI for mean(b - a) over queries (paired resampling)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape or a.ndim != 1 or a.size == 0:
        raise ValueError("a and b must be equal-length non-empty 1-D arrays")
    d = b - a
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, d.size, size=(n_boot, d.size))
    means = d[idx].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(d.mean()), float(lo), float(hi)

def _hits(n_both, n_b_only, n_a_only, n_neither):
    a = [1] * n_both + [0] * n_b_only + [1] * n_a_only + [0] * n_neither
    b = [1] * n_both + [1] * n_b_only + [0] * n_a_only + [0] * n_neither
    return a, b


# 40 queries: B beats A on 6, A beats B on 2, tie on 32.
a, b = _hits(18, 6, 2, 14)
m, lo, hi = paired_bootstrap_ci(a, b)
assert abs(m - 0.10) < 1e-12
assert lo < 0.0 < hi
# same pattern on 10x as many queries: interval should exclude zero
a, b = _hits(180, 60, 20, 140)
m2, lo2, hi2 = paired_bootstrap_ci(a, b)
assert abs(m2 - 0.10) < 1e-12 and lo2 > 0.0
assert (hi2 - lo2) < (hi - lo)
# deterministic for a fixed seed
assert paired_bootstrap_ci(a, b) == paired_bootstrap_ci(a, b)
# identical systems -> zero difference, CI is exactly [0, 0]
assert paired_bootstrap_ci(a, a) == (0.0, 0.0, 0.0)
print("ok")
