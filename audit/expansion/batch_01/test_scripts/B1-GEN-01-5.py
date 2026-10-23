import numpy as np


def relative_contrast(x, q):
    """(farthest - nearest) / nearest Euclidean distance from q to the rows of x."""
    d = np.linalg.norm(x - q, axis=1)
    return float((d.max() - d.min()) / d.min())


def uniform_contrast(dim, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    return relative_contrast(rng.random((n, dim)), rng.random(dim))


def low_rank_contrast(intrinsic, ambient, n=2000, seed=0):
    """Points with `intrinsic` true degrees of freedom linearly embedded in `ambient` dims."""
    rng = np.random.default_rng(seed)
    proj = rng.standard_normal((intrinsic, ambient))
    x = rng.random((n, intrinsic)) @ proj
    q = rng.random(intrinsic) @ proj
    return relative_contrast(x, q)

vals = [uniform_contrast(d) for d in (2, 10, 100, 1000)]
print(vals)
assert all(a > b for a, b in zip(vals, vals[1:]))
assert vals[0] > 10 * vals[-1]
lr = low_rank_contrast(3, 1000)
print(lr, uniform_contrast(1000))
assert lr > 10 * uniform_contrast(1000)
