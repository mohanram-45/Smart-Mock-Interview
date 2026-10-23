"""Presentation helpers (pure functions, used as Jinja globals): how a submitted answer is SHOWN. Never changes what was stored or scored.

Code answers keep their exact line breaks, indentation and tabs, in a monospace block with line numbers (the numbers match the 'line N' evidence of the code check);
prose keeps its line breaks and list markers but wraps. Candidate text is only ever passed to Jinja as data, so autoescaping applies; nothing here returns markup.
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.codeeval import extract


def trim_blank_edges(text: str) -> str:
    """Drop blank lines before the first and after the last line of text (a pasted block often starts with an empty line); inner lines and indentation are untouched."""
    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def answer_blocks(text: str) -> List[Dict[str, Any]]:
    """[{kind: 'code'|'prose', language, lines: [str], start}] in order. `start` is the line number of the block's first line in the extracted code (code blocks are joined by one
    blank line there), so the numbers shown here are the ones the code check cites."""
    text = trim_blank_edges(text)
    blocks: List[Dict[str, Any]] = []
    nxt = 1
    for seg in extract.split(text):
        lines = seg.text.split("\n")
        if seg.kind == "code":
            blocks.append({"kind": "code", "language": (seg.language or "python"), "lines": lines, "start": nxt if seg.language in (None, "python") else None})
            if seg.language in (None, "python"):
                nxt += len(lines) + 1
        else:
            blocks.append({"kind": "prose", "language": None, "lines": lines, "start": None})
    return blocks


def expects_code(question: Dict[str, Any]) -> bool:
    return extract.question_expects_code(question.get("question", ""), question.get("question_type", "") or "")


def answer_kind(text: str) -> str:
    return extract.answer_kind(trim_blank_edges(text))
