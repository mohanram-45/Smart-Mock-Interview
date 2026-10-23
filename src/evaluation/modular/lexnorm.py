"""Concept-name normalisation for spelling and morphological variants (variant 3c1.1; NOT used by the frozen 3c1.0 engine).

Purpose and limits
  * `fold_token` / `stem_token` make "regularization"/"regularisation", "convolution"/"convolutional", "normalise"/"normalization",
    "behaviour"/"behavior", "modelling"/"modeling" compare equal, so a lexical cross-check does not miss a concept just because of a spelling variant.
  * `discriminators` keeps the tokens that DISTINGUISH otherwise similar concept names ("Type I" vs "Type II", "L1" vs "L2", "O(n)" vs "O(log n)"). The frozen
    tokeniser drops one-letter tokens, which makes "Type I error" and "Type II error" look 67% identical.
  * Word matching is evidence that a word is PRESENT, never that a concept is stated CORRECTLY. Nothing in this module can create credit: it is only used
    to (a) refuse a model's claim that something was never mentioned, and (b) tell concept names apart.
"""
from __future__ import annotations

import re
from typing import FrozenSet, Set

from .claims import _STOP

_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_+#]*|\d+(?:\.\d+)?")
_ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}

# spelling pairs that are not covered by the -ise/-ize rule (British -> American canonical form)
_SPELLING = {"behaviour": "behavior", "behaviours": "behaviors", "centre": "center", "centres": "centers", "colour": "color", "colours": "colors",
             "modelling": "modeling", "modelled": "modeled", "labelling": "labeling", "labelled": "labeled", "analyse": "analyze", "analysed": "analyzed",
             "analyses": "analyzes", "analysing": "analyzing", "grey": "gray", "programme": "program", "favour": "favor", "neighbour": "neighbor",
             "neighbours": "neighbors", "licence": "license", "catalogue": "catalog", "dialogue": "dialog"}
# irregular technical plurals -> singular, so "matrices"/"matrix", "vertices"/"vertex", "hypotheses"/"hypothesis" compare equal
_IRREGULAR = {"matrices": "matrix", "indices": "index", "vertices": "vertex", "hypotheses": "hypothesis", "criteria": "criterion", "axes": "axis", "analyses": "analysis",
              "bases": "basis", "extrema": "extremum", "maxima": "maximum", "minima": "minimum", "optima": "optimum", "lemmata": "lemma", "automata": "automaton",
              "appendices": "appendix", "coefficients": "coefficient"}
# roots that take both -ise and -ize; restricting to known roots keeps "precise", "rise", "exercise", "promise" untouched
_ISE_ROOTS = ("parameter", "hyperparameter", "normal", "regular", "optim", "standard", "general", "token", "vector", "parametr", "initial", "serial", "minim", "maxim", "util", "summar",
              "visual", "categor", "character", "synchron", "special", "central", "random", "final", "local", "personal", "linear", "quantis", "quantiz",
              "discret", "numer", "organ", "recogn", "memor", "real", "stabil", "penal", "scal", "binar", "factor", "tokeniz", "harmon", "prioriti")
_ISE_RX = re.compile(r"^(" + "|".join(_ISE_ROOTS) + r")is(ations?|ing|ed|es|er|ers|e)$")
_IZ_SUFFIXES = ("izationally", "izations", "ization", "izers", "izer", "izing", "ized", "izes", "ize")
_SUFFIXES = ("ationally", "ational", "ations", "ation", "ional", "ions",
             "ion", "ities", "ity", "ments", "ment", "ness", "ings", "ing", "edly", "ed", "ies", "es", "ers", "er", "ly", "s")


def fold_token(w: str) -> str:
    """Canonical spelling of ONE lower-cased token (American -ize/-ization, a few explicit British forms)."""
    w = w.lower()
    if w in _SPELLING:
        return _SPELLING[w]
    if w in _IRREGULAR:
        return _IRREGULAR[w]
    m = _ISE_RX.match(w)
    if m:
        return m.group(1) + "iz" + m.group(2)
    return w


def stem_token(w: str) -> str:
    """Conservative suffix stripping on the folded token (stem never shorter than 4 characters). Not a linguistic stemmer: it only has to map the SAME term's
    variants to the same string. 'normal' and 'normalization' stay different ('normaliz')."""
    w = fold_token(w)
    for suf in _IZ_SUFFIXES:                                              # normalization / normalizer / normalized -> normaliz (never 'normal')
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)] + "iz"
    if w.endswith("ies") and len(w) - 3 >= 3:
        w = w[:-3] + "y"
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            w = w[: -len(suf)]
            break
    if len(w) >= 5 and w[-1] == w[-2] and w[-1] not in "aeiouls":        # overfitt -> overfit, runn -> run
        w = w[:-1]
    return w[:-1] + "i" if w.endswith("y") and len(w) > 4 else w          # dependency / dependencies -> dependenci


_POSSESSIVE = re.compile(r"(?<=[A-Za-z0-9])[\'\u2019]s\b")


def _tokens(text: str) -> list:
    """Word tokens. A possessive ('Dijkstra's', "Bayes'") is dropped BEFORE tokenising: otherwise the stray 's' becomes a one-letter 'discriminator' and a label
    like "Dijkstra's algorithm" could never be matched in text that says 'Dijkstra algorithm' or 'dijkstra(...)'."""
    out = []
    for raw in _TOKEN.findall(_POSSESSIVE.sub("", text or "")):
        for part in re.split(r"[_]+", raw):
            if part:
                out.append(part.lower())
    return out


def is_discriminator(tok: str) -> bool:
    """A token that tells sibling concepts apart: roman numerals, digits, letter+digit codes (l1, l2, k8s excluded by length), single letters (not 'a')."""
    t = tok.lower()
    return t in _ROMAN or bool(re.search(r"\d", t)) or (len(t) == 1 and t.isalpha() and t != "a")


def discriminators(label: str) -> FrozenSet[str]:
    return frozenset(t for t in _tokens(label) if is_discriminator(t))


def content_stems_v31(text: str) -> Set[str]:
    """Like claims.content_stems, but variant-tolerant, hyphen-splitting, and it keeps discriminating tokens (numerals, one-letter symbols)."""
    out: Set[str] = set()
    for t in _tokens(text):
        if t in _STOP:
            continue
        if is_discriminator(t):
            out.add(t)
            continue
        for part in t.split("-"):
            if len(part) >= 2 and part not in _STOP:
                out.add(stem_token(part))
    return out


def word_stems_v31(text: str) -> Set[str]:
    """Content stems WITHOUT discriminating tokens (numerals, one-letter symbols): used where overlap must mean shared WORDS, so that 'O(n)' and 'O(log n)' do not
    look alike merely because both contain 'o' and 'n'."""
    return {s for s in content_stems_v31(text) if not is_discriminator(s)}


_NEGATORS = {"not", "no", "without", "neither", "nor", "never"}


def negates_concept(explanation: str, member: str, window: int = 3) -> bool:
    """Does `explanation` negate the concept itself ('uses a simple min function, NOT A HEAP', 'no heap', 'without a heap')? Such a finding says the candidate did not
    use or state the concept: an omission-type statement, not an error about something the candidate asserted."""
    ms = word_stems_v31(member)
    if not ms:
        return False
    toks = _tokens(explanation)
    for i, t in enumerate(toks):
        if t in _NEGATORS:
            for w in toks[i + 1: i + 1 + window]:
                if stem_token(w) in ms:
                    return True
    return False


def compact_form(text: str) -> str:
    """Letters and digits only, spelling-folded, separators removed: 'TF-IDF' / 'tf idf' / 'tfidf' all become 'tfidf'; 'k-fold' / 'k fold' -> 'kfold'."""
    return "".join(fold_token(t) for t in _tokens(text))


def compact_present(label: str, text: str) -> bool:
    """Is a MULTI-WORD or hyphenated concept label present in `text` once separators are ignored? Single-word labels are left to the stem comparison. This can only
    REFUSE a model's 'never mentioned'; it is evidence that the words are present, never that the concept is stated correctly."""
    if len(_tokens(label)) < 2:
        return False
    cl = compact_form(label)
    return len(cl) >= 5 and cl in compact_form(text)


def labels_may_overlap(a: str, b: str, threshold: float = 0.5) -> bool:
    """May two requirement labels denote overlapping concepts? Same rule as 3c1.0 (Jaccard of stems >= 0.5) plus one veto: if the labels differ in a
    DISCRIMINATING token (Type I vs Type II, L1 vs L2) they are different concepts however many words they share."""
    da, db = discriminators(a), discriminators(b)
    if da != db and (da or db):
        return False
    sa = {s for s in content_stems_v31(a) if s not in da}
    sb = {s for s in content_stems_v31(b) if s not in db}
    return bool(sa and sb and len(sa & sb) / len(sa | sb) >= threshold)
