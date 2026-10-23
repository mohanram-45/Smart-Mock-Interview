"""Decision tables for Stage 1B continuation (v3). Keys: pilot ids (smi-gNNNN) and batch-02 plan ids (P2-XXX-NN).
Nothing here changes v1 or v2 files; v3 is built from them plus the independent audits in stage1b3/."""

# ---- batch 02: stable id = smi-h + position in plan order (NLP, DL, PY, DA); topic vocabulary reuses existing topics where one fits
B2_ORDER = ["NLP", "Deep Learning", "Python", "Data Analysis"]
B2_TOPIC = {
 "P2-NLP-01": "Decoding and generation", "P2-NLP-02": "Decoding and generation", "P2-NLP-03": "NLP in production",
 "P2-NLP-04": "Fine-tuning and adaptation", "P2-NLP-05": "Language modelling and evaluation", "P2-NLP-06": "NLP tasks and models",
 "P2-NLP-07": "Tokenisation and vocabulary", "P2-NLP-08": "Text classification", "P2-NLP-09": "Semantic search and LLM applications",
 "P2-NLP-10": "Semantic search and LLM applications", "P2-NLP-11": "NLP in production", "P2-NLP-12": "Language modelling and evaluation",
 "P2-DL-01": "Backpropagation", "P2-DL-02": "Sequence models and transformers", "P2-DL-03": "Numerical stability and mixed precision",
 "P2-DL-04": "Sequence models and transformers", "P2-DL-05": "Sequence models and transformers", "P2-DL-06": "Autoencoders and generative models",
 "P2-DL-07": "Training at scale", "P2-DL-08": "Training diagnostics and debugging", "P2-DL-09": "Architectures", "P2-DL-10": "Embeddings",
 "P2-PY-01": "Functions and decorators", "P2-PY-02": "Functions and decorators", "P2-PY-03": "Core language", "P2-PY-04": "Generators and concurrency",
 "P2-PY-05": "Functions and decorators", "P2-PY-06": "Generators and concurrency", "P2-PY-07": "Data science libraries",
 "P2-PY-08": "Data science libraries", "P2-PY-09": "Data science libraries", "P2-PY-10": "Data structures and algorithms",
 "P2-PY-11": "Text processing and parsing", "P2-PY-12": "Core language",
 "P2-DA-01": "Hypothesis testing and A/B testing", "P2-DA-02": "Hypothesis testing and A/B testing", "P2-DA-03": "Hypothesis testing and A/B testing",
 "P2-DA-04": "Statistics fundamentals", "P2-DA-05": "Data preparation and cleaning", "P2-DA-06": "Statistics fundamentals",
 "P2-DA-07": "Hypothesis testing and A/B testing", "P2-DA-08": "Product and business metrics", "P2-DA-09": "Analytical case studies",
 "P2-DA-10": "Exploratory analysis and methodology", "P2-DA-11": "Time series", "P2-DA-12": "Exploratory analysis and methodology",
}

# ---- difficulty: the independent auditor rated every record blind. Where the blind rating differed from the author's label, the auditor's
# rating is adopted (rubric: Easy = single-concept recall; Medium = comparison/mechanism/short code/simple application; Hard = multi-step
# reasoning, design with trade-offs, subtle debugging or non-trivial implementation) EXCEPT where listed in DIFFICULTY_KEPT.
DIFFICULTY = {
 "smi-g0023": "Medium", "smi-g0038": "Medium", "smi-g0011": "Hard", "smi-g0039": "Hard",
 "P2-NLP-08": "Medium", "P2-DL-01": "Medium", "P2-DL-05": "Medium", "P2-PY-05": "Medium", "P2-PY-06": "Medium",
 "P2-DA-02": "Medium", "P2-DA-11": "Medium",
}
DIFFICULTY_KEPT = {"smi-g0029": "Medium (auditor: Hard) - one frame-semantics subtlety on top of a short query; kept as Medium, disagreement recorded"}

# ---- key concepts: auditor-suggested lists are applied automatically; these are wording swaps for concepts the answer never names
KC_REPLACE = {"smi-g0005": {"cross-entropy": None}}   # None = drop (the answer never uses the term; 'negative log-likelihood' is already listed)

# ---- audit issues whose claim is not an exact substring: handled below instead of by the generic engine (id, claim prefix)
MANUAL_SKIP = {
 ("P2-PY-10", "Prove the complexity claim"),
 ("P2-PY-11", "r\"^(?P<ts>"),
}
# Replacements that add a demonstration code block to the answer: the block is also appended to the record's test so it is executed.
DEMO_TO_TEST = {"smi-g0014", "smi-g0017", "smi-g0025", "P2-NLP-04"}

# ---- explicit patches: (record key, field, old, new[, count]); fields: question, answer, code.setup, code.solution, code.test
_COUNTED = '''class Counted:
    eq_calls = hash_calls = lt_calls = 0
    def __init__(self, v):
        self.v = v
    def __eq__(self, other):
        Counted.eq_calls += 1
        return self.v == other.v
    def __hash__(self):
        Counted.hash_calls += 1
        return hash(self.v)
    def __lt__(self, other):
        Counted.lt_calls += 1
        return self.v < other.v'''
PATCHES = [
 # smi-g0012: the recorded test imported nltk (not available on the owner's machine); the cross-check against nltk is removed from the test, the answer text was corrected by the audit
 ("smi-g0012", "code.test", "from fractions import Fraction\nimport math\n", "import math\n"),
 ("smi-g0012", "code.test", """# agreement with nltk
from nltk.translate.bleu_score import modified_precision
for n in (1,2):
    f=modified_precision([r1,r2],c2,n); m,t=clipped_precision(c2,[r1,r2],n)
    assert f==Fraction(m,t),(f,m,t)
f=modified_precision([r1,r2],c,1); assert f==Fraction(2,7)
""", ""),
 # P2-NLP-03: 'original question' is the RAG-evaluation meaning, reworded so that it cannot be read as a reference to a source text
 ("P2-NLP-03", "answer", "embedding similarity to the original question", "embedding similarity to the user's question"),
 # P2-PY-11: \d matches any Unicode decimal digit in str patterns (auditor verified k=٣ parsed as 3): use [0-9] in text and code
 ("P2-PY-11", "answer", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"),
 ("P2-PY-11", "answer", r'INT_RE = re.compile(r"-?\d+")', r'INT_RE = re.compile(r"-?[0-9]+")'),
 ("P2-PY-11", "code.solution", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"),
 ("P2-PY-11", "code.solution", r'INT_RE = re.compile(r"-?\d+")', r'INT_RE = re.compile(r"-?[0-9]+")'),
 # P2-PY-10: show the counting wrapper the question asks for (identical text is used in the test so the answer block is covered by executed code)
 ("P2-PY-10", "code.test", '''class Counted:
    eq_calls = 0
    hash_calls = 0
    lt_calls = 0
    def __init__(self, v):
        self.v = v
    def __eq__(self, other):
        Counted.eq_calls += 1
        return self.v == other.v
    def __hash__(self):
        Counted.hash_calls += 1
        return hash(self.v)
    def __lt__(self, other):
        Counted.lt_calls += 1
        return self.v < other.v''', _COUNTED),
]
# text appended to an answer (after the existing text): (record key, text). The text may contain a fenced block that is also in code.test.
APPEND_ANSWER = {
 "P2-PY-10": "\n\nCounting wrapper used for the demonstration (not part of the solutions):\n\n```python\n" + _COUNTED + "\n```\n\n"
             "With 200 unique `Counted` items, `has_duplicates_quadratic` makes exactly 200*199/2 = 19,900 `__eq__` calls; `has_duplicates` makes 200 `__hash__` calls and 0 `__eq__` calls "
             "(equality is consulted only when full hashes collide); `has_duplicates_sorted` makes roughly n log2 n `__lt__` calls on shuffled input (measured: see the test, which asserts an upper bound).",
}
# a claim that the audit could only describe (no substring): the replacement text becomes this exact answer sentence
