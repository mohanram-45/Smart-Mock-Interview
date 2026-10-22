"""Heuristic prompt-injection detection. FLAGS only: detection never changes the grade by itself and is NOT the defence
(the defence is structural: untrusted text is delimited, labelled as data, and the model is told to ignore instructions in it;
the evaluator also verifies quotes and caps unsupported scores). Heuristics miss novel phrasings - treat the flag as a signal."""
from __future__ import annotations

import re
from typing import List

_PATTERNS = [
    r"ignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
    r"disregard\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier|your)\s*(instructions?|prompts?|rules?)?",
    r"(forget|override)\s+(everything|all|your)\s+(instructions?|rules?|above|previous)",
    r"(give|assign|award|output|return|set)\s+(me\s+|this\s+answer\s+|a\s+)?(a\s+)?(score|grade|mark|rating)\s*(of|to|=|:)?\s*(100|10/10|full|max|perfect)",
    r"\b(score|grade)\s*[:=]\s*(100|10/10)\b",
    r"you\s+are\s+now\s+(a|an|the|in)\b",
    r"\bsystem\s*(prompt|message|instruction)s?\b",
    r"</?\s*(system|assistant|user|instructions?|candidate_answer|reference\w*|untrusted\w*)\s*>",
    r"\b(act|respond|behave)\s+as\s+(if|a|an)\b",
    r"reveal\s+(the\s+)?(reference|canonical|system|hidden)",
    r"(print|show|repeat|leak)\s+(the\s+)?(reference|canonical|system\s+prompt|instructions)",
    r"mark\s+(this|my)\s+(answer\s+)?as\s+(correct|perfect|excellent)",
    r"this\s+answer\s+is\s+(perfect|fully\s+correct|already\s+correct)",
]
_RX = [re.compile(p, re.I) for p in _PATTERNS]


def detect_injection(text: str) -> List[str]:
    hits: List[str] = []
    for rx in _RX:
        m = rx.search(text or "")
        if m:
            hits.append(m.group(0)[:80])
    return hits
