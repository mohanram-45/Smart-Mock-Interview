"""Answer fixtures written for this repository (not copied from any candidate)."""

NP_GOOD = '''
import numpy as np

def pairwise_sq_dists(A, B):
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    a2 = (A * A).sum(axis=1)[:, None]
    b2 = (B * B).sum(axis=1)[None, :]
    D = a2 + b2 - 2.0 * (A @ B.T)
    return np.maximum(D, 0.0)

def pairwise_sq_dists_broadcast(A, B):
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    d = A[:, None, :] - B[None, :, :]
    return (d ** 2).sum(axis=-1)
'''

NP_EXPLANATION = '''
# Memory: the broadcast version creates an (n, m, d) temporary array, so it needs far more memory than the
# expansion, which only builds (n, m) arrays and uses a matrix product.
# Numerical issue: subtracting nearly equal large norms causes catastrophic cancellation, so rounding can make
# tiny distances slightly negative; that is why the result is clipped at zero.
'''

NP_NO_CLIP = NP_GOOD.replace("return np.maximum(D, 0.0)", "return D")
NP_SIGN_BUG = NP_GOOD.replace("- 2.0 * (A @ B.T)", "+ 2.0 * (A @ B.T)")
NP_LOOPS = '''
import numpy as np

def pairwise_sq_dists(A, B):
    A = np.asarray(A, dtype=float); B = np.asarray(B, dtype=float)
    D = np.zeros((len(A), len(B)))
    for i in range(len(A)):
        for j in range(len(B)):
            D[i, j] = np.sum((A[i] - B[j]) ** 2)
    return D

def pairwise_sq_dists_broadcast(A, B):
    A = np.asarray(A, dtype=float); B = np.asarray(B, dtype=float)
    return ((A[:, None, :] - B[None, :, :]) ** 2).sum(-1)
'''
NP_RAISES = '''
import numpy as np
def pairwise_sq_dists(A, B):
    raise ValueError("not implemented")
def pairwise_sq_dists_broadcast(A, B):
    raise ValueError("not implemented")
'''
NP_WRONG_NAMES = '''
import numpy as np
def dists(A, B):
    return np.zeros((len(A), len(B)))
'''
NP_KEYWORD_STUFFING_WRONG = NP_SIGN_BUG + '''
# memory memory (n, m, d) temporary; catastrophic cancellation rounding floating-point negative precision
'''

LR_GD = '''
import numpy as np

class LinearRegression:
    def __init__(self, lr=0.05, epochs=2000):
        self.lr, self.epochs, self.w, self.b = lr, epochs, 0.0, 0.0

    def fit(self, X, y):
        X = np.asarray(X, dtype=float); y = np.asarray(y, dtype=float); n = len(X)
        for _ in range(self.epochs):
            err = self.w * X + self.b - y
            dw = 2.0 / n * np.sum(err * X)
            db = 2.0 / n * np.sum(err)
            self.w -= self.lr * dw
            self.b -= self.lr * db
        return self

    def predict(self, X):
        return self.w * np.asarray(X, dtype=float) + self.b
'''
LR_CLOSED = '''
import numpy as np

def fit_linear_regression(X, y):
    X = np.asarray(X, dtype=float).reshape(len(X), -1)
    Xb = np.c_[np.ones(len(X)), X]
    return np.linalg.lstsq(Xb, np.asarray(y, dtype=float), rcond=None)[0]

def predict(theta, X):
    X = np.asarray(X, dtype=float).reshape(len(X), -1)
    return np.c_[np.ones(len(X)), X] @ theta
'''
LR_SIGN_BUG = LR_GD.replace("self.w -= self.lr * dw", "self.w += self.lr * dw")
LR_NO_PREDICT = LR_GD.split("    def predict")[0]
LR_NEEDS_ARGS = LR_GD.replace("def __init__(self, lr=0.05, epochs=2000):", "def __init__(self, lr, epochs):")
LR_MUTATES = LR_GD.replace("X = np.asarray(X, dtype=float); y = np.asarray(y, dtype=float); n = len(X)", "X = np.asarray(X, dtype=float); y = np.asarray(y, dtype=float); n = len(X); X -= X.mean()")
LR_NO_UPDATE = '''
import numpy as np
class LinearRegression:
    def fit(self, X, y):
        self.m = 0.0
    def predict(self, X):
        return np.asarray(X, dtype=float) * 0
'''
