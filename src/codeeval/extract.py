"""Split a submitted answer into code and prose. Pure text handling: nothing is executed or imported from the answer.

Used for presentation (monospace, indentation-preserving blocks for code; wrapped text for prose) and as the first step of code assessment.
A fenced block (```python ... ```) is trusted as code. Otherwise a whole answer that parses as Python is code; otherwise lines are classified one by one
with simple, conservative patterns, and blank lines stay with the block they sit inside. This is a heuristic: it can be wrong on unusual input, so callers
must treat the result as a presentation aid and as "evidence of structure", never as proof of anything.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import List, Optional

_FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+#-]*)[ \t]*\r?\n(.*?)\r?\n?```", re.S)
_PY_START = re.compile(
    r"^\s*(?:def\s+\w+\s*\(|class\s+\w+|import\s+\w|from\s+[\w.]+\s+import\s|return\b|raise\b|assert\b|yield\b|pass\s*$|break\s*$|continue\s*$|"
    r"(?:for|while|if|elif|with)\b.*:\s*(?:#.*)?$|else\s*:|try\s*:|finally\s*:|except\b.*:|@\w|print\s*\(|lambda\b|"
    r"[A-Za-z_][\w.]*(?:\[[^\]]*\])?\s*(?:[-+*/%@&|^]|//|\*\*|<<|>>)?=(?!=)\s*\S|"
    r"[A-Za-z_][\w.]*\(.*\)\s*$|#.*$)")
_SQL_START = re.compile(r"^\s*(?:SELECT|WITH|INSERT\s+INTO|UPDATE|DELETE\s+FROM|CREATE\s+(?:TABLE|INDEX|VIEW)|ALTER\s+TABLE|DROP\s+TABLE|FROM|WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|JOIN|LEFT\s+JOIN|INNER\s+JOIN|ON|LIMIT)\b", re.I)
_PROSE_WORDS = re.compile(r"\b(the|is|are|because|which|this|that|use|uses|using|since|so|therefore|however|with|where|when)\b", re.I)
_CODE_QUESTION = re.compile(r"^\s*(?:implement|write|code|create|build|give me|show)\b|\b(?:in|using|with)\s+(?:python|numpy|pandas|sql|pytorch|sklearn)\b.*\b(?:function|class|query|code|implement)\b|"
                            r"\b(?:write|implement)\s+(?:a|an|the)?\s*(?:python|sql|numpy)?\s*(?:function|query|class|script|program)\b", re.I)


@dataclass
class Segment:
    kind: str                       # "code" | "prose"
    text: str
    language: Optional[str] = None  # "python" | "sql" | None


def question_expects_code(question_text: str, question_type: str = "") -> bool:
    """Should the answer box for this question be a code box? Declared type wins; otherwise a conservative wording check."""
    if (question_type or "").strip().lower() in ("coding", "code"):
        return True
    return bool(_CODE_QUESTION.search(question_text or ""))


def _parses_as_python(text: str) -> bool:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return False
    return any(not isinstance(n, ast.Expr) or not isinstance(getattr(n, "value", None), ast.Constant) for n in tree.body)


def _is_code_line(line: str, prev_code: bool) -> Optional[str]:
    """'python' / 'sql' / None for one non-blank line."""
    if _SQL_START.match(line) and not (len(line.split()) >= 7 and line.rstrip().endswith(".")):     # an SQL keyword opening a long sentence is prose
        return "sql"
    if line[:1] in (" ", "\t") and prev_code:
        return "python"                                           # indentation continues a code block
    if _PY_START.match(line):
        words = line.split()
        if len(words) > 8 and not any(ch in line for ch in "=()[]{}:") and _PROSE_WORDS.search(line):
            return None                                           # long sentence that merely starts with a keyword-ish word
        return "python"
    return None


def split(text: str) -> List[Segment]:
    """Ordered code/prose segments. Concatenating the segments' text (with newlines) reproduces the answer's content; indentation inside segments is untouched."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return []
    fences = list(_FENCE.finditer(text))
    if fences:
        out: List[Segment] = []
        pos = 0
        for m in fences:
            before = text[pos:m.start()].strip("\n")
            if before.strip():
                out.extend(_split_lines(before))
            lang = (m.group(1) or "").lower() or None
            out.append(Segment("code", m.group(2), "python" if lang in (None, "py", "python", "python3") else lang))
            pos = m.end()
        after = text[pos:].strip("\n")
        if after.strip():
            out.extend(_split_lines(after))
        return out
    if _parses_as_python(text):
        return [Segment("code", text.strip("\n"), "python")]
    return _split_lines(text)


def _split_lines(text: str) -> List[Segment]:
    lines = text.split("\n")
    kinds: List[Optional[str]] = []
    prev_code = False
    for ln in lines:
        if not ln.strip():
            kinds.append("blank"); continue
        k = _is_code_line(ln, prev_code)
        kinds.append(k or "prose")
        prev_code = k is not None
    # blank lines take the kind of the block they are inside (both neighbours code) else prose
    for i, k in enumerate(kinds):
        if k == "blank":
            j = i - 1
            while j >= 0 and kinds[j] == "blank":
                j -= 1
            n = i + 1
            while n < len(kinds) and kinds[n] == "blank":
                n += 1
            before = kinds[j] if j >= 0 else None
            after = kinds[n] if n < len(kinds) else None
            kinds[i] = before if before in ("python", "sql") and before == after else "prose"
    segs: List[Segment] = []
    cur: List[str] = []
    cur_kind: Optional[str] = None
    for ln, k in zip(lines, kinds):
        kind = "code" if k in ("python", "sql") else "prose"
        lang = k if kind == "code" else None
        if cur and (kind != cur_kind[0] or lang != cur_kind[1]):
            segs.append(_mk(cur, cur_kind)); cur = []
        cur_kind = (kind, lang); cur.append(ln)
    if cur:
        segs.append(_mk(cur, cur_kind))
    return [s for s in segs if s.text.strip()]


def _mk(lines: List[str], kind) -> Segment:
    body = "\n".join(lines).strip("\n")
    return Segment(kind[0], body, kind[1])


def answer_kind(text: str) -> str:
    """'code' (only code), 'prose' (no code) or 'mixed'."""
    segs = split(text)
    if not segs:
        return "prose"
    kinds = {s.kind for s in segs}
    return "code" if kinds == {"code"} else "prose" if kinds == {"prose"} else "mixed"


def code_of(text: str) -> str:
    """All code segments, joined by a blank line (Python only: SQL is presentation-only here)."""
    return "\n\n".join(s.text for s in split(text) if s.kind == "code" and s.language in (None, "python"))


def prose_of(text: str) -> str:
    """Explanation text: prose segments plus the `#` comment lines inside Python code. Docstrings are added by the static layer (it knows the AST)."""
    parts = [s.text for s in split(text) if s.kind == "prose"]
    for s in split(text):
        if s.kind == "code" and s.language in (None, "python"):
            for ln in s.text.split("\n"):
                m = re.match(r"^\s*#\s?(.*)$", ln) or re.search(r"\s#\s(.*)$", ln)
                if m and m.group(1).strip():
                    parts.append(m.group(1).strip())
    return "\n".join(parts)
