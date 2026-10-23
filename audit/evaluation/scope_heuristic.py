"""Stage 3C-0 scope heuristic v2 (deterministic, no model). Drafts a tier for every key concept from EXISTING fields only.
It is a DRAFT generator: output is labelled ai_heuristic_draft and is never presented as human-verified or as ground truth.

essential  = concept is part of what the question asks (its content words, stem-normalised, overlap the question) or is stated in the
             canonical answer's headline (first) sentence
supporting = stated elsewhere in the canonical answer (credit if present, never a penalty)
background = key concept not stated in the canonical answer (never required, feedback only)
"""
import re
import unicodedata

STOP = set("""the a an of and in to is for vs versus what are how do does with on between difference differences explain why when you your can it be or as at by from
that this which would should could any each some into than then their there these those about over under using use used also more most such they them its if not""".split())
SUP = {"²": "^2", "³": "^3", "¹": "^1"}
SYN = {  # small, conservative synonym / equivalent table (technical, symmetric)
    "tokenisation": "tokenization", "normalisation": "normalization", "regularisation": "regularization", "optimisation": "optimization",
    "summarisation": "summarization", "standardisation": "standardization", "initialisation": "initialization", "serialisation": "serialization",
    "parallelisation": "parallelization", "visualisation": "visualization", "generalisation": "generalization", "categorise": "categorize",
    "colour": "color", "behaviour": "behavior", "quadratic": "n^2", "linear": "o(n)", "logarithmic": "log", "nlp": "natural language processing",
    "ner": "named entity recognition", "pos": "part of speech", "llm": "large language model", "rag": "retrieval augmented generation",
    "cv": "cross validation", "mlops": "mlops", "ci": "continuous integration", "cd": "continuous deployment",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    for k, v in SUP.items():
        s = s.replace(k, v)
    return s.lower()


def stem(w: str) -> str:
    w = SYN.get(w, w)
    for suf in ("ization", "isation"):
        if w.endswith(suf):
            w = w[: -len(suf)] + "iz"
    for suf in ("ing", "ed", "es", "s", "ly"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def words(s: str) -> set:
    out = set()
    for w in re.findall(r"[a-z0-9_^=]+(?:\([a-z0-9^* ]*\))?|[a-z0-9_^]+", _norm(s)):
        if w in STOP or len(w) < 2:
            continue
        out.add(stem(w))
    return out


def sentences(text: str):
    return [x for x in re.split(r"(?<=[.!?])\s+|\n+", (text or "").strip()) if x.strip()]


def question_parts(q: str):
    parts = [p.strip() for p in re.split(r"\?\s+|;\s+|\band also\b|\bas well as\b", q) if len(p.split()) > 2]
    return parts if len(parts) >= 2 else [q]


def tier_record(rec: dict) -> dict:
    """Return {'tiers': {concept: tier}, 'flags': [...]} for one corpus record."""
    q = words(rec["question"])
    ans = rec["canonical_answer"]
    sents = sentences(ans)
    head = words(sents[0]) if sents else set()
    allw = words(ans)
    ans_l = _norm(ans)
    tiers = {}
    for k in rec["key_concepts"]:
        kw = words(k)
        k_l = _norm(k)
        if not kw:
            tiers[k] = "supporting"
        elif kw & q and len(kw & q) >= max(1, len(kw) // 2):
            tiers[k] = "essential"
        elif kw <= head:
            tiers[k] = "essential"
        elif kw <= allw or k_l in ans_l:
            tiers[k] = "supporting"
        else:
            tiers[k] = "background"
    flags = []
    if not any(v == "essential" for v in tiers.values()):
        flags.append("no_essential_concept")
    if len(question_parts(rec["question"])) >= 2:
        flags.append("multi_part_question")
    if len(ans.split()) > 250:
        flags.append("long_reference")
    if rec.get("question_type") in ("coding", "sql_exercise", "debugging"):
        flags.append("code_or_sql_exercise")
    if rec.get("question_type") in ("design", "scenario", "business_case"):
        flags.append("open_ended_design_or_scenario")
    n_ess = sum(v == "essential" for v in tiers.values())
    if len(tiers) >= 6 and n_ess <= 1:
        flags.append("many_concepts_few_essential")
    if all(v == "essential" for v in tiers.values()) and len(tiers) >= 5:
        flags.append("all_essential_suspicious")
    return {"tiers": tiers, "flags": flags}
