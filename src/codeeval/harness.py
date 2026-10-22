"""Behaviour tests for code-assessment specs. THIS FILE RUNS CANDIDATE CODE. It must only ever be executed inside an isolated environment (see runner.py): its source is
shipped over stdin to a locked-down container, and nothing in the Flask application imports and calls `run`.

Self-contained on purpose (standard library + numpy only, no imports from this project): the container has none of the project's files.

Known limitation, stated plainly: the candidate and these tests share one interpreter, so a deliberately hostile submission can tamper with its OWN test results
(it cannot leave the container). Fine for a single user practising locally; a hosted service would run the candidate in a separate process and compare outputs outside.
"""
import contextlib
import io
import traceback

HARNESS_VERSION = "8b.0"


def _short(e, n=200):
    return (type(e).__name__ + ": " + str(e)).replace("\n", " ")[:n]


def _load(source):
    ns = {"__name__": "candidate"}                 # not "__main__": `if __name__ == "__main__":` demo blocks stay dormant
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        exec(compile(source, "<candidate>", "exec"), ns)
    return ns


def _record(tests, tid, fn):
    try:
        ok, detail = fn()
        tests.append({"id": tid, "status": "passed" if ok else "failed", "detail": detail})
    except AssertionError as e:
        tests.append({"id": tid, "status": "failed", "detail": _short(e) or "assertion failed"})
    except BaseException as e:                     # the candidate's own exception (including SystemExit) is a finding, not a crash of the harness
        tests.append({"id": tid, "status": "error", "detail": "raised " + _short(e)})


def _quiet(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*a, **k)


# ------------------------------------------------------------------------------------------------ pairwise squared distances
def _pairwise(ns, tests):
    import numpy as np
    allclose, asarray, isfinite = np.allclose, np.asarray, np.isfinite
    rng = np.random.default_rng(12345)

    def brute(A, B):
        A, B = asarray(A, dtype=float), asarray(B, dtype=float)
        return ((A[:, None, :] - B[None, :, :]) ** 2).sum(axis=-1)

    def get(name):
        f = ns.get(name)
        if not callable(f):
            raise AssertionError("no callable named " + name)
        return f

    def example(name):
        def t():
            out = asarray(_quiet(get(name), [[0, 0], [1, 1]], [[0, 0], [3, 4]]), dtype=float)
            want = np.array([[0, 25], [2, 13]], dtype=float)
            return (out.shape == (2, 2) and bool(allclose(out, want))), f"shape {out.shape}; expected [[0, 25], [2, 13]]"
        return t

    def values(name):
        def t():
            A, B = rng.normal(size=(7, 3)), rng.normal(size=(5, 3))
            out = asarray(_quiet(get(name), A, B), dtype=float)
            return (out.shape == (7, 5) and bool(allclose(out, brute(A, B), rtol=1e-8, atol=1e-8))), f"shape {out.shape}; max abs error {float(abs(out - brute(A, B)).max()) if out.shape == (7, 5) else 'n/a'}"
        return t

    def shapes(name):
        def t():
            for n, m, d in ((1, 4, 1), (6, 1, 5), (3, 3, 2)):
                A, B = rng.normal(size=(n, d)), rng.normal(size=(m, d))
                out = asarray(_quiet(get(name), A, B), dtype=float)
                if out.shape != (n, m) or not bool(allclose(out, brute(A, B), atol=1e-8)):
                    return False, f"wrong result for n={n}, m={m}, d={d}: shape {out.shape}"
            return True, "(1,4,1), (6,1,5) and (3,3,2) inputs give (n, m) results with the right values"
        return t

    def non_negative():
        A = 1e6 + 1e-3 * rng.normal(size=(20, 5))
        out = asarray(_quiet(get("pairwise_sq_dists"), A, A.copy()), dtype=float)
        ok = bool(isfinite(out).all()) and float(out.min()) >= 0.0
        return ok, f"smallest entry {float(out.min()):.3g} on near-identical points far from the origin (where rounding makes the expansion go slightly negative)"

    _record(tests, "expansion_example", example("pairwise_sq_dists"))
    _record(tests, "expansion_values", values("pairwise_sq_dists"))
    _record(tests, "expansion_shapes", shapes("pairwise_sq_dists"))
    _record(tests, "never_negative", non_negative)
    _record(tests, "broadcast_example", example("pairwise_sq_dists_broadcast"))
    _record(tests, "broadcast_values", values("pairwise_sq_dists_broadcast"))


# ------------------------------------------------------------------------------------------------ simple linear regression from scratch
def _discover(ns):
    classes = [o for n, o in ns.items() if isinstance(o, type) and callable(getattr(o, "fit", None)) and callable(getattr(o, "predict", None)) and getattr(o, "__module__", "") == "candidate"]
    if classes:
        classes.sort(key=lambda c: 0 if any(w in c.__name__.lower() for w in ("linear", "regress")) else 1)
        return ("class", classes[0])
    fits = [(n, f) for n, f in ns.items() if callable(f) and not isinstance(f, type) and (n.lower().startswith(("fit", "train")) or "regress" in n.lower()) and getattr(f, "__module__", "") == "candidate"]
    preds = [(n, f) for n, f in ns.items() if callable(f) and not isinstance(f, type) and n.lower().startswith("predict") and getattr(f, "__module__", "") == "candidate"]
    if fits and preds:
        return ("functions", fits[0][1], preds[0][1])
    return None


def _linreg(ns, tests):
    import numpy as np
    asarray, isfinite = np.asarray, np.isfinite
    found = _discover(ns)

    def fit_predict(X, y, Xnew):
        """Returns (predictions, how). Tries 1-D features first (the natural form of 'simple' regression), then a column matrix."""
        last = None
        for shape in ("1d", "col"):
            try:
                Xt = np.array(X, dtype=float) if shape == "1d" else np.array(X, dtype=float).reshape(-1, 1)
                Xn = np.array(Xnew, dtype=float) if shape == "1d" else np.array(Xnew, dtype=float).reshape(-1, 1)
                yt = np.array(y, dtype=float)
                if found[0] == "class":
                    model = _quiet(found[1])
                    _quiet(model.fit, Xt, yt)
                    pred = _quiet(model.predict, Xn)
                else:
                    params = _quiet(found[1], Xt, yt)
                    try:
                        pred = _quiet(found[2], params, Xn)
                    except TypeError:
                        pred = _quiet(found[2], Xn)
                return asarray(pred, dtype=float).reshape(-1), ("1-D features" if shape == "1d" else "2-D column features")
            except Exception as e:
                last = e
        raise last

    def api():
        if found is None:
            return False, "no class with fit() and predict() methods, and no fit/predict function pair, was found"
        return True, "class " + found[1].__name__ + " with fit() and predict()" if found[0] == "class" else "functions " + found[1].__name__ + "() and " + found[2].__name__ + "()"

    def tolerance_ok(pred, want):
        return pred.shape == want.shape and bool((abs(pred - want) <= np.maximum(0.1 * abs(want), 0.3)).all())

    def line(name_x, name_y, slope, icpt, xtrain, xtest):
        def t():
            if found is None:
                raise AssertionError("no fit/predict interface to test")
            X = np.array(xtrain, dtype=float)
            y = slope * X + icpt
            want = slope * np.array(xtest, dtype=float) + icpt
            pred, how = fit_predict(X, y, xtest)
            return tolerance_ok(pred, want), f"trained on y = {slope}x + {icpt}; predictions {np.round(pred, 2).tolist()} vs expected {np.round(want, 2).tolist()} (within 10% or 0.3); used {how}; default settings"
        return t

    def finite():
        if found is None:
            raise AssertionError("no fit/predict interface to test")
        pred, _ = fit_predict([1, 2, 3, 4, 5], [3, 5, 7, 9, 11], [6, 7])
        return bool(isfinite(pred).all()) and pred.shape == (2,), f"predictions {np.round(pred, 3).tolist()}"

    def untouched():
        if found is None:
            raise AssertionError("no fit/predict interface to test")
        X, y = np.array([1.0, 2.0, 3.0, 4.0]), np.array([3.0, 5.0, 7.0, 9.0])
        X0, y0 = X.copy(), y.copy()
        if found[0] == "class":
            m = _quiet(found[1]); _quiet(m.fit, X, y)
        else:
            _quiet(found[1], X, y)
        return bool((X == X0).all() and (y == y0).all()), "the training arrays are unchanged after fit()"

    _record(tests, "interface", api)
    _record(tests, "fits_positive_line", line("x", "y", 2.0, 1.0, [1, 2, 3, 4, 5], [6, 7, 0]))
    _record(tests, "fits_negative_line", line("x", "y", -1.5, 4.0, [-3, -2, -1, 0, 1, 2, 3], [4, -5]))
    _record(tests, "finite_output", finite)
    _record(tests, "inputs_untouched", untouched)


# ------------------------------------------------------------------------------------------------ declarative cases (Stage 8B)
# Cases are DATA (JSON literals) written by the question author, validated by src/codeeval/declarative.py before they get here. Candidate code is called with literal
# arguments only; nothing in a case is ever evaluated as code.
_EXC = {"ValueError": ValueError, "TypeError": TypeError, "ZeroDivisionError": ZeroDivisionError, "IndexError": IndexError, "KeyError": KeyError}
_TYPES = {"list": list, "tuple": tuple, "dict": dict, "str": str, "int": int, "float": float, "bool": bool, "NoneType": type(None)}


def _plain(x):
    if hasattr(x, "tolist") and not isinstance(x, (list, tuple, dict, str, bytes)):
        try:
            return x.tolist()
        except Exception:
            return x
    return x


def _same(a, b, rtol=0.0, atol=0.0):
    a, b = _plain(a), _plain(b)
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if rtol or atol:
            import math
            return math.isclose(a, b, rel_tol=rtol, abs_tol=atol)
        return a == b
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y, rtol, atol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_same(a[k], b[k], rtol, atol) for k in a)
    return type(a) is type(b) and a == b


def _show(x, n=120):
    try:
        return repr(_plain(x))[:n]
    except Exception:
        return "<unprintable>"


def _declarative(ns, tests, cases):
    import copy

    def make(case):
        def t():
            f = ns.get(case["function"])
            if not callable(f):
                raise AssertionError("no callable named " + case["function"])
            args, kwargs = copy.deepcopy(case.get("args", [])), copy.deepcopy(case.get("kwargs", {}))
            before = copy.deepcopy((args, kwargs))
            exp = case["expect"]
            if "raises" in exp:
                try:
                    out = _quiet(f, *args, **kwargs)
                except _EXC[exp["raises"]]:
                    return True, "raised " + exp["raises"] + " as required"
                return False, "expected " + exp["raises"] + " but it returned " + _show(out)
            out = _quiet(f, *args, **kwargs)
            if case.get("args_unchanged") and not _same(before, (args, kwargs)):
                return False, "the call changed its input arguments"
            if "equals" in exp:
                return _same(out, exp["equals"]), "expected " + _show(exp["equals"]) + "; got " + _show(out)
            if "approx" in exp:
                return _same(out, exp["approx"], exp.get("rtol", 1e-6), exp.get("atol", 1e-9)), "expected about " + _show(exp["approx"]) + "; got " + _show(out)
            if "returns_type" in exp:
                return isinstance(out, _TYPES[exp["returns_type"]]) and not (exp["returns_type"] == "int" and isinstance(out, bool)), "expected type " + exp["returns_type"] + "; got " + type(out).__name__
            raise AssertionError("case has no expectation")
        return t

    for c in cases:
        _record(tests, c["id"], make(c))


HARNESSES = {"numpy_pairwise_sq_dists": _pairwise, "linear_regression_from_scratch": _linreg}


def run(harness_id, source, cases=None):
    """Execute `source` and the named behaviour tests (or, for harness "declarative_cases", the data cases). Returns plain JSON-able data. ONLY call inside an isolated environment."""
    out = {"harness": harness_id, "version": HARNESS_VERSION, "tests": [], "load_error": None}
    fn = HARNESSES.get(harness_id)
    if harness_id == "declarative_cases":
        fn = lambda ns, tests: _declarative(ns, tests, cases or [])  # noqa: E731
    if fn is None:
        out["load_error"] = "unknown harness " + str(harness_id)
        return out
    try:
        ns = _load(source)
    except BaseException as e:
        out["load_error"] = "the code did not run to completion: " + _short(e)
        return out
    fn(ns, out["tests"])
    return out
