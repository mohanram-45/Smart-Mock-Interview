"""The two specs built for Stage 5A (questions smi-h0029 and smi-0462). Everything about a question lives here as data; adding another question means adding a spec
(and, for behaviour tests, a harness function), never touching the evaluator."""
from __future__ import annotations

import re
from typing import List

from .spec import CodeSpec, Context, Finding, Requirement, explanation_check, register
from .static import FuncInfo

_MATMUL_CALLS = {"np.dot", "numpy.dot", "np.matmul", "numpy.matmul", "np.inner", "numpy.inner", "np.tensordot", "numpy.tensordot"}
_CLIP_CALLS = {"np.maximum", "numpy.maximum", "np.clip", "numpy.clip", "np.fmax", "numpy.fmax", "np.where", "numpy.where", "np.core.umath.maximum"}


def _func(ctx: Context, name: str):
    return ctx.report.functions.get(name)


def _lines_matching(ctx: Context, info: FuncInfo, rx: str) -> List[int]:
    node = info.node
    if node is None:
        return []
    return [n for n in range(node.lineno, (getattr(node, "end_lineno", node.lineno) or node.lineno) + 1) if re.search(rx, ctx.report.line(n))]


# ------------------------------------------------------------------------------------------------ NumPy pairwise squared distances
def _np_matmul(ctx: Context) -> Finding:
    f = _func(ctx, "pairwise_sq_dists")
    if f is None:
        return Finding("missing", note="No function named pairwise_sq_dists was found, so the matrix-product approach cannot be located.")
    if f.matmul_ops:
        return Finding("demonstrated", [ctx.snippet(n) for n in f.matmul_ops[:3]], "A matrix product (@) is used inside pairwise_sq_dists. Text evidence only; it does not show the result is right.")
    used = sorted(f.calls & _MATMUL_CALLS)
    if used:
        return Finding("demonstrated", [f"calls {u}" for u in used], "A matrix-product call is used inside pairwise_sq_dists. Text evidence only.")
    if any(c.endswith("einsum") for c in f.calls):
        return Finding("unclear", ["calls einsum"], "einsum can express a matrix product or something else; this check cannot tell which.")
    return Finding("missing", note="No @ operator, np.dot or np.matmul was found in pairwise_sq_dists.")


def _np_noloops(ctx: Context) -> Finding:
    f = _func(ctx, "pairwise_sq_dists")
    if f is None:
        return Finding("unclear", note="pairwise_sq_dists was not found, so loops could not be checked.")
    if f.loops == 0 and f.comprehensions == 0:
        return Finding("demonstrated", ["no for/while statement or comprehension in pairwise_sq_dists"], "Helper functions it calls are not inspected.")
    where = [f"line {n}: {ctx.report.line(n)}" for n in _lines_matching(ctx, f, r"\bfor\b|\bwhile\b")[:3]]
    return Finding("contradicted", where, "The question says 'no Python loops', but pairwise_sq_dists contains a loop or comprehension.")


def _np_nonneg(ctx: Context) -> Finding:
    f = _func(ctx, "pairwise_sq_dists")
    if f is None:
        return Finding("unclear", note="pairwise_sq_dists was not found.")
    used = sorted(f.calls & _CLIP_CALLS)
    idx = _lines_matching(ctx, f, r"\[[^\]]*<\s*0[^\]]*\]\s*=\s*0")
    if used or idx:
        ev = [f"calls {u}" for u in used] + [ctx.snippet(n) for n in idx[:2]]
        return Finding("demonstrated", ev, "Negative values are clipped. Whether the clip is applied to the right quantity is checked only by the behaviour test.")
    if f.calls & {"np.abs", "numpy.abs", "abs"}:
        return Finding("unclear", ["calls abs"], "abs() makes values non-negative but changes the result for negative rounding errors instead of clipping them.")
    return Finding("missing", note="No clipping (np.maximum / np.clip / D[D < 0] = 0) was found in pairwise_sq_dists.")


def _np_broadcast(ctx: Context) -> Finding:
    f = _func(ctx, "pairwise_sq_dists_broadcast")
    if f is None:
        return Finding("missing", note="No function named pairwise_sq_dists_broadcast was found.")
    if f.newaxis_lines or f.calls & {"np.expand_dims", "numpy.expand_dims"} or any(c.endswith(".reshape") for c in f.calls):
        ev = [ctx.snippet(n) for n in f.newaxis_lines[:2]] or ["uses expand_dims / reshape"]
        return Finding("demonstrated", ev, "Broadcasting through an added axis is used. Text evidence only.")
    return Finding("unclear", note="pairwise_sq_dists_broadcast exists but no added-axis indexing (A[:, None, :]) was found.")


_MEMORY = explanation_check([[r"\bmemory\b", r"\bRAM\b", r"footprint", r"out of memory"],
                             [r"\(\s*n\s*,\s*m\s*,\s*d\s*\)", r"n\s*[x×*]\s*m\s*[x×*]\s*d", r"three[- ]dimensional", r"3[- ]?d\b", r"temporar", r"intermediate", r"O\(\s*n\s*\*?\s*m\s*\*?\s*d\s*\)"]],
                            "memory trade-off between the broadcast and expansion versions")
_CANCEL = explanation_check([[r"cancell?ation", r"catastrophic", r"round-?off", r"rounding", r"floating[- ]point", r"precision", r"numerical(?:ly)? (?:issue|error|instab)"],
                             [r"negative", r"nearly (?:equal|identical)", r"close points", r"large (?:norms|values|numbers)", r"subtract", r"far from the origin", r"loses? (?:significant|digits|accuracy)"]],
                            "floating-point cancellation in the expansion")

register(CodeSpec(
    "numpy_pairwise_sq_dists/1", "smi-h0029", "NumPy pairwise squared distances", "numpy_pairwise_sq_dists",
    (Requirement("f_example", "Produces the example result [[0, 25], [2, 13]]", "functional", test_id="expansion_example"),
     Requirement("f_values", "Correct values and (n, m) shape on random inputs", "functional", test_id="expansion_values"),
     Requirement("f_shapes", "Correct shapes for unusual sizes (n=1, m=1, d=1)", "functional", test_id="expansion_shapes"),
     Requirement("f_nonneg", "Never negative, even for near-identical points far from the origin", "functional", test_id="never_negative"),
     Requirement("f_broadcast", "pairwise_sq_dists_broadcast gives the right result", "functional", test_id="broadcast_values"),
     Requirement("s_matmul", "Uses a matrix product (the ||a||² + ||b||² − 2a·b expansion)", "structure", check=_np_matmul),
     Requirement("s_noloops", "No Python loops in pairwise_sq_dists", "structure", check=_np_noloops),
     Requirement("s_nonneg", "Clips negative rounding errors to zero", "structure", check=_np_nonneg),
     Requirement("s_broadcast", "Provides the broadcasting version (A[:, None, :] − B[None, :, :])", "structure", check=_np_broadcast),
     Requirement("e_memory", "Explains the memory trade-off", "explanation", check=_MEMORY),
     Requirement("e_cancel", "Explains the numerical (cancellation) issue", "explanation", check=_CANCEL)),
    ("Behaviour tests cover the shapes and values listed in harness.py only; passing them does not prove the code is correct for all inputs.",)))


# ------------------------------------------------------------------------------------------------ linear regression from scratch
_PARAM = r"(?:self\.)?(?:w|b|weights?|bias|theta|coef\w*|slope|intercept|m|c)\w*"
_LR = r"(?:lr|learning_rate|alpha|eta|step)"


def _all_funcs(ctx: Context):
    for n, f in ctx.report.functions.items():
        yield n, f
    for c, ms in ctx.report.classes.items():
        for n, f in ms.items():
            yield f"{c}.{n}", f


def _lr_numpy(ctx: Context) -> Finding:
    if "numpy" not in ctx.report.imports:
        return Finding("missing", note="numpy is not imported.")
    calls = sorted(c for c in ctx.report.all_calls if c.startswith(("np.", "numpy.")))
    return Finding("demonstrated", [f"calls {', '.join(calls[:4])}"] if calls else ["imports numpy"], "NumPy is used.")


def _lr_methods(ctx: Context) -> Finding:
    for cname, ms in ctx.report.classes.items():
        train = [m for m in ms if m.lower() in ("fit", "train")]
        if train and "predict" in {m.lower() for m in ms}:
            return Finding("demonstrated", [f"class {cname}: {train[0]}() and predict()"], "A training method and a prediction method are defined.")
        if train:
            return Finding("unclear", [f"class {cname}: {train[0]}() only"], "A training method exists but no predict() method was found.")
    fits = [n for n in ctx.report.functions if n.lower().startswith(("fit", "train")) or "regress" in n.lower()]
    preds = [n for n in ctx.report.functions if n.lower().startswith("predict")]
    if fits and preds:
        return Finding("demonstrated", [f"functions {fits[0]}() and {preds[0]}()"], "A training function and a prediction function are defined.")
    return Finding("missing", note="No class with fit()/predict() methods and no fit/predict function pair was found.")


def _lr_updates(ctx: Context) -> Finding:
    ev = []
    for name, f in _all_funcs(ctx):
        for tgt, op, line in f.aug_updates:
            if op in ("Sub", "Add") and re.fullmatch(_PARAM, tgt.split(".")[-1] if tgt.startswith("self.") else tgt, re.I) and re.search(_LR, ctx.report.line(line), re.I):
                ev.append(ctx.snippet(line))
        node = f.node
        if node is not None:
            for n in range(node.lineno, (getattr(node, "end_lineno", node.lineno) or node.lineno) + 1):
                ln = ctx.report.line(n)
                m = re.match(rf"^({_PARAM})\s*=\s*\1\s*-\s*.*{_LR}", ln, re.I)
                if m:
                    ev.append(f"line {n}: {ln}")
    if ev:
        return Finding("demonstrated", ev[:4], "Weight/bias parameters are updated using a learning rate (gradient-descent style). Text evidence only: the behaviour tests decide whether it converges.")
    closed = sorted(c for c in ctx.report.all_calls if c in {"np.linalg.lstsq", "np.linalg.pinv", "np.linalg.inv", "np.linalg.solve", "np.polyfit", "numpy.linalg.lstsq", "numpy.linalg.pinv",
                                                            "numpy.linalg.inv", "numpy.linalg.solve", "numpy.polyfit"})
    if closed:
        return Finding("demonstrated", [f"calls {c}" for c in closed], "A closed-form (least-squares) solution is used instead of iterative updates.")
    return Finding("missing", note="No parameter update with a learning rate and no closed-form least-squares call was found.")


def _lr_gradient(ctx: Context) -> Finding:
    ev = []
    for name, f in _all_funcs(ctx):
        node = f.node
        if node is None:
            continue
        for n in range(node.lineno, (getattr(node, "end_lineno", node.lineno) or node.lineno) + 1):
            ln = ctx.report.line(n)
            if re.search(r"\b(?:grad\w*|d_?w\w*|d_?b\w*|dtheta)\b\s*=|\.T\s*(?:@|\.dot)|np\.dot\(\s*\w+\.T|np\.sum\(\s*\w+\s*\*\s*\w+\s*\)|np\.mean\(\s*\w+\s*\*\s*\w+\s*\)", ln):
                ev.append(f"line {n}: {ln}")
    if ev:
        return Finding("demonstrated", ev[:4], "Code that looks like a gradient computation is present. Text evidence only: whether it is the RIGHT gradient is decided by the behaviour tests.")
    if any(c.startswith(("np.linalg.", "numpy.linalg.")) or c.endswith("polyfit") for c in ctx.report.all_calls):
        return Finding("not_applicable", note="Closed-form solution: no gradient is expected.")
    return Finding("missing", note="No gradient-like expression was found.")


register(CodeSpec(
    "linear_regression_from_scratch/1", "smi-0462", "Linear regression from scratch with NumPy", "linear_regression_from_scratch",
    (Requirement("f_interface", "Offers a trainable model with fit() and predict() (class) or a fit/predict function pair", "functional", test_id="interface"),
     Requirement("f_positive", "Recovers y = 2x + 1 from simple data (default settings)", "functional", test_id="fits_positive_line"),
     Requirement("f_negative", "Recovers y = −1.5x + 4 (a negative slope; catches a wrong gradient sign)", "functional", test_id="fits_negative_line"),
     Requirement("f_finite", "Returns finite numeric predictions of the right size", "functional", test_id="finite_output"),
     Requirement("f_untouched", "Does not modify the training arrays it is given", "functional", test_id="inputs_untouched"),
     Requirement("s_numpy", "Uses NumPy", "structure", check=_lr_numpy),
     Requirement("s_methods", "Defines training and prediction methods/functions", "structure", check=_lr_methods),
     Requirement("s_updates", "Updates the weight and bias (or solves least squares in closed form)", "structure", check=_lr_updates),
     Requirement("s_gradient", "Computes a gradient (gradient-descent version)", "structure", check=_lr_gradient)),
    ("The question does not fix a function signature or hyper-parameters, so the tests call the model with its default settings; a correct model that needs tuned settings can fail 'recovers the line'.",
     "No explanation is asked for by this question, so none is assessed.")))
