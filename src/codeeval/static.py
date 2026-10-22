"""Static analysis of submitted Python with `ast`. The code is PARSED, never compiled to a code object, imported or run.

Two jobs:
  1. describe structure (functions, classes, loops, calls, operators, updates) so a spec can look for evidence of an approach;
  2. find constructs that must never reach an execution backend (policy gate). This is a PRE-FILTER, not a sandbox: static checks cannot prove code is harmless
     (getattr tricks, deep recursion, memory bombs...). Real isolation is the runner's job; a refused submission is simply never run.
Everything reported is evidence of what the text contains, not of what the program does.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

ALLOWED_IMPORTS = frozenset({"numpy", "math", "typing", "dataclasses", "collections", "itertools", "functools", "__future__", "random", "statistics", "operator", "numbers", "decimal", "fractions"})
FORBIDDEN_NAMES = frozenset({"eval", "exec", "compile", "open", "__import__", "input", "breakpoint", "globals", "locals", "vars", "getattr", "setattr", "delattr", "memoryview", "exit", "quit"})
FORBIDDEN_MODULES = frozenset({"os", "sys", "subprocess", "socket", "ctypes", "pathlib", "shutil", "urllib", "http", "requests", "pickle", "marshal", "importlib", "builtins", "multiprocessing",
                               "threading", "signal", "resource", "tempfile", "glob", "io", "asyncio", "inspect", "gc", "code", "codeop", "runpy", "pty", "fcntl", "mmap", "ftplib", "smtplib", "webbrowser"})
FORBIDDEN_ATTRS = frozenset({"__class__", "__bases__", "__subclasses__", "__globals__", "__builtins__", "__code__", "__dict__", "__mro__", "__import__", "__loader__", "__spec__", "f_globals", "f_back", "gi_frame"})
FORBIDDEN_NUMPY = frozenset({"load", "save", "savez", "savez_compressed", "loadtxt", "savetxt", "genfromtxt", "fromfile", "tofile", "memmap", "fromregex", "DataSource", "ctypeslib", "testing", "f2py", "distutils", "lib"})


@dataclass
class FuncInfo:
    name: str
    lineno: int
    args: List[str]
    loops: int = 0                         # for / while statements
    comprehensions: int = 0                # list/set/dict comprehensions and generator expressions
    calls: Set[str] = field(default_factory=set)       # dotted names called, e.g. "np.maximum", "self.predict"
    matmul_ops: List[int] = field(default_factory=list)   # line numbers of the @ operator
    newaxis_lines: List[int] = field(default_factory=list)  # lines indexing with None / np.newaxis
    aug_updates: List[Tuple[str, str, int]] = field(default_factory=list)   # (target, op, line) for  x -= ... / += ...
    returns: int = 0
    node: Optional[ast.AST] = None


@dataclass
class StaticReport:
    parse_ok: bool
    error: Optional[str] = None
    error_line: Optional[int] = None
    imports: Set[str] = field(default_factory=set)
    functions: Dict[str, FuncInfo] = field(default_factory=dict)            # module-level functions
    classes: Dict[str, Dict[str, FuncInfo]] = field(default_factory=dict)   # class -> methods
    module_calls: Set[str] = field(default_factory=set)
    all_calls: Set[str] = field(default_factory=set)
    docstrings: List[str] = field(default_factory=list)
    forbidden: List[Dict[str, object]] = field(default_factory=list)        # [{"what","line","why"}]
    source_lines: List[str] = field(default_factory=list)
    tree: Optional[ast.AST] = None

    def line(self, n: int) -> str:
        return self.source_lines[n - 1].strip() if 1 <= n <= len(self.source_lines) else ""


def dotted(node: ast.AST) -> str:
    """'np.linalg.solve' for an attribute chain, '' when the chain is not plain names."""
    parts: List[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr); node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


class _FuncVisitor(ast.NodeVisitor):
    def __init__(self, info: FuncInfo):
        self.i = info

    def visit_For(self, n): self.i.loops += 1; self.generic_visit(n)
    visit_AsyncFor = visit_For

    def visit_While(self, n): self.i.loops += 1; self.generic_visit(n)

    def visit_ListComp(self, n): self.i.comprehensions += 1; self.generic_visit(n)
    visit_SetComp = visit_DictComp = visit_GeneratorExp = visit_ListComp

    def visit_Return(self, n): self.i.returns += 1; self.generic_visit(n)

    def visit_Call(self, n):
        d = dotted(n.func)
        if d:
            self.i.calls.add(d)
        self.generic_visit(n)

    def visit_BinOp(self, n):
        if isinstance(n.op, ast.MatMult):
            self.i.matmul_ops.append(n.lineno)
        self.generic_visit(n)

    def visit_AugAssign(self, n):
        t = dotted(n.target) or (n.target.id if isinstance(n.target, ast.Name) else "")
        self.i.aug_updates.append((t, type(n.op).__name__, n.lineno))
        self.generic_visit(n)

    def visit_Subscript(self, n):
        for sub in ast.walk(n.slice):
            if (isinstance(sub, ast.Constant) and sub.value is None) or dotted(sub) in ("np.newaxis", "numpy.newaxis"):
                self.i.newaxis_lines.append(n.lineno); break
        self.generic_visit(n)


def _func_info(fn) -> FuncInfo:
    a = fn.args
    names = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs] + ([a.vararg.arg] if a.vararg else []) + ([a.kwarg.arg] if a.kwarg else [])
    info = FuncInfo(fn.name, fn.lineno, names, node=fn)
    v = _FuncVisitor(info)
    for stmt in fn.body:
        v.visit(stmt)
    return info


def analyze(code: str) -> StaticReport:
    """Parse `code` and describe it. Never raises: a syntax problem is reported in the result."""
    lines = (code or "").split("\n")
    try:
        tree = ast.parse(code or "")
    except SyntaxError as e:
        return StaticReport(False, f"{e.msg}", e.lineno, source_lines=lines)
    except (ValueError, MemoryError, RecursionError) as e:
        return StaticReport(False, f"The code could not be parsed ({type(e).__name__}).", None, source_lines=lines)
    r = StaticReport(True, source_lines=lines, tree=tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                r.imports.add(a.name.split(".")[0]); _check_module(r, a.name, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "")
            r.imports.add(mod.split(".")[0]) if mod else None
            _check_module(r, mod or "." * (node.level or 1), node.lineno)
            if mod.split(".")[0] == "numpy":
                for a in node.names:
                    if a.name in FORBIDDEN_NUMPY:
                        r.forbidden.append({"what": f"numpy.{a.name}", "line": node.lineno, "why": "file or native-code access through numpy"})
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            r.forbidden.append({"what": node.id, "line": node.lineno, "why": "dynamic code, file or introspection access"})
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRS:
                r.forbidden.append({"what": node.attr, "line": node.lineno, "why": "interpreter internals"})
            d = dotted(node)
            if d.startswith(("np.", "numpy.")) and node.attr in FORBIDDEN_NUMPY:
                r.forbidden.append({"what": d, "line": node.lineno, "why": "file or native-code access through numpy"})
        elif isinstance(node, ast.Call):
            d = dotted(node.func)
            if d:
                r.all_calls.add(d)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            pass
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            ds = ast.get_docstring(node)
            if ds:
                r.docstrings.append(ds)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            r.functions[node.name] = _func_info(node)
        elif isinstance(node, ast.ClassDef):
            r.classes[node.name] = {m.name: _func_info(m) for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
        else:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    d = dotted(sub.func)
                    if d:
                        r.module_calls.add(d)
    seen = set()
    r.forbidden = [f for f in r.forbidden if not ((f["what"], f["line"]) in seen or seen.add((f["what"], f["line"])))]
    return r


def _check_module(r: StaticReport, name: str, line: int) -> None:
    root = name.split(".")[0]
    if name.startswith("."):
        r.forbidden.append({"what": f"relative import {name}", "line": line, "why": "imports from the host project"})
    elif root in FORBIDDEN_MODULES:
        r.forbidden.append({"what": f"import {name}", "line": line, "why": "operating-system, network, process or file access"})
    elif root not in ALLOWED_IMPORTS:
        r.forbidden.append({"what": f"import {name}", "line": line, "why": "module not on the allow-list (numpy and a few standard maths helpers)"})


def policy_violations(report: StaticReport) -> List[Dict[str, object]]:
    return list(report.forbidden)
