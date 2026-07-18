"""Report Generator - Builds JSON and PDF interview reports."""
import json
import logging
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Tier thresholds - kept in sync with FeedbackGenerator's tiers
STRONG_THRESHOLD = 70.0
WEAK_THRESHOLD = 55.0
HIGHLIGHT_THRESHOLD = 80.0

# Learning-plan phrasing pools, sampled without replacement per report
# so the same line doesn't repeat across a candidate's weak topics.
_TOPIC_ACTION_TEMPLATES = [
    "Revisit {topic} and implement a small example to lock in the concept",
    "Practice a few problems built around {topic} instead of just re-reading it",
    "Build a mini project or code snippet that exercises {topic}",
    "Look up a couple of real-world use cases of {topic} and work through one hands-on",
    "Rebuild your understanding of {topic} by coding it out, not just reading about it",
    "Find a coding exercise on {topic} and solve it end-to-end",
    "Sketch out {topic} from scratch in a notebook, then check it against a real reference",
    "Pull up a dataset or toy problem and apply {topic} to it directly",
]

_GENERAL_PRACTICE_TEMPLATES = [
    "Turn each weak topic into a small hands-on exercise or mini project you can actually run",
    "Pick real coding problems tied to each weak topic and solve them end-to-end instead of just reviewing notes",
    "Work through applied practice problems for each weak topic rather than passive review",
    "Treat each weak topic like a small take-home task - build something, don't just study it",
]


def technical_study_points(topic: str, domain: str = "") -> List[str]:
    """Return concrete study terms for a weak topic.

    The keyword groups keep the fallback report useful when Ollama is not
    running. Unknown topics still receive technical dimensions to investigate
    instead of vague instructions that point elsewhere in the report.
    """
    text = f"{topic} {domain}".lower()
    topic_guides = [
        (
            ("naive bayes",),
            [
                "Bayes' theorem: prior, likelihood, evidence, and posterior probability",
                "the conditional-independence assumption and its practical limitations",
                "Gaussian, Multinomial, Bernoulli, and Complement Naive Bayes variants",
                "Laplace/additive smoothing, log-probabilities, and zero-frequency handling",
                "text classification, spam filtering, sentiment analysis, and document categorization",
                "precision, recall, F1-score, confusion matrices, and probability calibration",
            ],
        ),
        (
            ("cnn", "convolutional neural", "image classification"),
            [
                "convolution kernels, receptive fields, stride, padding, and pooling",
                "spatial feature hierarchies, parameter sharing, and translation equivariance",
                "batch normalization, activation functions, dropout, and data augmentation",
                "transfer learning with pretrained backbones and fine-tuning",
                "accuracy, precision, recall, F1-score, and class-imbalance analysis",
            ],
        ),
        (
            ("deep learning", "neural network", "dnn"),
            [
                "forward propagation, backpropagation, computational graphs, and gradient descent",
                "loss functions, activation functions, weight initialization, and optimizers",
                "overfitting, regularization, dropout, batch normalization, and early stopping",
                "learning-rate schedules, validation curves, and hyperparameter tuning",
            ],
        ),
        (
            ("machine learning", "classifier", "classification", "regression"),
            [
                "feature engineering, preprocessing pipelines, and train/validation/test splits",
                "bias-variance trade-off, overfitting, regularization, and cross-validation",
                "baseline selection and hyperparameter tuning",
                "precision, recall, F1-score, ROC-AUC, confusion matrices, and error analysis",
            ],
        ),
        (
            ("nlp", "language model", "text"),
            [
                "tokenization, normalization, stemming, lemmatization, and subword vocabularies",
                "TF-IDF, word embeddings, contextual embeddings, and attention",
                "sequence modelling, transformers, fine-tuning, and prompt construction",
                "precision, recall, F1-score, BLEU/ROUGE where appropriate, and qualitative error analysis",
            ],
        ),
        (
            ("sql", "database", "query"),
            [
                "joins, subqueries, common table expressions, aggregations, and window functions",
                "primary/foreign keys, normalization, constraints, and transaction isolation",
                "indexes, query execution plans, cardinality, and performance optimization",
            ],
        ),
        (
            ("python",),
            [
                "data structures, comprehensions, iterators, generators, and context managers",
                "object-oriented design, type hints, exceptions, and unit testing",
                "time/space complexity, profiling, packaging, and dependency management",
            ],
        ),
    ]

    for keywords, points in topic_guides:
        if any(keyword in text for keyword in keywords):
            return points

    return [
        f"the formal definition, core terminology, and internal mechanism of {topic}",
        f"implementation steps, inputs, outputs, assumptions, and failure modes of {topic}",
        f"real-world use cases and the trade-offs between {topic} and related approaches",
        f"appropriate evaluation metrics, debugging techniques, and performance constraints for {topic}",
    ]


def technical_action(topic: str, domain: str = "") -> str:
    """Build one readable but technically dense action for the learning plan."""
    points = technical_study_points(topic, domain)
    selected = "; ".join(points[:4])
    return f"Study {topic}: {selected}. Then implement a small working example and evaluate its results."


def topic_learning_module(topic: str, domain: str = "") -> Dict[str, Any]:
    """Turn a topic into a distinct study module with a real deliverable."""
    text = f"{topic} {domain}".lower()
    if "is' and '==" in text or "identity" in text and "equality" in text:
        return {
            "topic": "Object identity and value equality in Python",
            "terms": ["object identity", "value equality", "id()", "__eq__()", "None singleton", "interning"],
            "practice_task": "Write examples comparing mutable objects, immutable values, and None with both is and ==, then explain every result.",
            "success_criteria": "Correctly choose is only for identity checks and == for value comparison, including custom objects that define __eq__().",
        }
    if "bubble sort" in text:
        return {
            "topic": "Bubble sort and elementary sorting",
            "terms": ["adjacent comparison", "swap", "in-place algorithm", "stable sort", "early-exit optimization", "O(n²) time"],
            "practice_task": "Implement bubble sort with an early-exit flag and trace every pass for [5, 1, 4, 2, 8].",
            "success_criteria": "Return the correct order, explain best- and worst-case complexity, and identify why Python's built-in sorted() is preferable in production.",
        }
    if "binary search" in text:
        return {
            "topic": "Binary search and logarithmic complexity",
            "terms": ["sorted precondition", "low/high pointers", "midpoint", "search invariant", "O(log n) time", "O(1) iterative space"],
            "practice_task": "Implement iterative binary search and test targets at the first, middle, last, and absent positions of a sorted list.",
            "success_criteria": "Produce correct indexes for all edge cases and derive why halving the search interval gives logarithmic time.",
        }
    if "unit test" in text or "pytest" in text or "unittest" in text:
        return {
            "topic": "Basic unit testing in Python",
            "terms": ["test case", "assertion", "pytest", "fixture", "Arrange-Act-Assert", "edge case"],
            "practice_task": "Create a small calculator module and a pytest suite covering normal inputs, invalid inputs, zero, and boundary cases.",
            "success_criteria": "Run the suite successfully, interpret one deliberate failure, and explain how each test isolates one behavior.",
        }
    if "class and object" in text or "classes and objects" in text:
        return {
            "topic": "Classes and objects in Python",
            "terms": ["class", "instance", "attribute", "method", "self", "__init__()", "encapsulation"],
            "practice_task": "Build a BankAccount class with initialization, deposit, withdrawal, balance validation, and two independent instances.",
            "success_criteria": "Explain the class-versus-instance distinction and show that instance state changes independently while methods enforce valid behavior.",
        }
    if "exception" in text:
        return {
            "topic": "Exception handling in Python",
            "terms": ["try", "except", "else", "finally", "raise", "custom exception", "exception hierarchy"],
            "practice_task": "Write a file-reading function that handles missing files, invalid content, cleanup, and a custom validation exception.",
            "success_criteria": "Catch only expected exception types, preserve useful error context, and guarantee cleanup without hiding unexpected failures.",
        }
    if "missing value" in text or "pandas" in text:
        return {
            "topic": "Missing-data handling with pandas",
            "terms": ["NaN", "isna()", "dropna()", "fillna()", "imputation", "forward fill", "missingness bias"],
            "practice_task": "Create a DataFrame with numeric and categorical gaps, measure missingness, and compare dropping rows with median/mode imputation.",
            "success_criteria": "Choose a treatment per column, justify its statistical effect, and verify that the transformed DataFrame contains the intended values.",
        }

    points = technical_study_points(topic, domain)
    return {
        "topic": topic.rstrip(". "),
        "terms": points[:6],
        "practice_task": f"Create a focused example that demonstrates the inputs, core mechanism, output, and one failure case of {topic.rstrip('. ')}.",
        "success_criteria": f"Define {topic.rstrip('. ')}, apply it correctly, and explain its assumptions, limitations, and one appropriate real-world use.",
    }


def programming_language_curriculum(language: str) -> List[Dict[str, Any]]:
    """Prerequisite-first modules for current or future language interviews."""
    profiles = {
        "Java": {
            "runtime": ["JDK", "JVM", "javac", "bytecode", "main()", "packages"],
            "collections": ["array", "ArrayList", "HashMap", "HashSet", "generics", "iteration"],
            "advanced": ["interface", "inheritance", "exceptions", "streams", "JUnit", "Maven/Gradle"],
        },
        "JavaScript": {
            "runtime": ["browser runtime", "Node.js", "script/module", "let/const", "dynamic typing", "strict mode"],
            "collections": ["array", "object", "Map", "Set", "destructuring", "iteration"],
            "advanced": ["closure", "prototype", "Promise", "async/await", "DOM/API", "Jest/Vitest", "npm"],
        },
        "C++": {
            "runtime": ["compiler", "linker", "executable", "header/source file", "namespace", "build flags"],
            "collections": ["array", "std::vector", "std::string", "std::map", "iterator", "STL algorithm"],
            "advanced": ["pointer/reference", "RAII", "class", "inheritance", "exception", "smart pointer", "Catch2/CMake"],
        },
        "C#": {
            "runtime": [".NET", "CLR", "SDK", "assembly", "Main()", "namespace"],
            "collections": ["array", "List<T>", "Dictionary<TKey,TValue>", "HashSet<T>", "generics", "LINQ"],
            "advanced": ["interface", "inheritance", "exception", "delegate/event", "async/await", "xUnit", "NuGet"],
        },
    }
    profile = profiles[language]
    return [
        {
            "topic": f"{language} platform, syntax, and execution model",
            "terms": profile["runtime"],
            "practice_task": f"Set up the {language} toolchain, create the smallest runnable program, compile or execute it, and deliberately fix one syntax error.",
            "success_criteria": f"Run the program from a terminal and explain how {language} source becomes executing code.",
        },
        {
            "topic": f"{language} values, types, operators, and control flow",
            "terms": ["variable", "type", "assignment", "comparison", "condition", "loop", "scope"],
            "practice_task": "Build an input-driven grade calculator with validation, branching, and iteration over multiple scores.",
            "success_criteria": "Predict type and scope behavior, handle invalid input, and explain every branch and loop termination condition.",
        },
        {
            "topic": f"Functions and core collections in {language}",
            "terms": ["function/method", "parameter", "return value", *profile["collections"]],
            "practice_task": "Create reusable functions that count frequencies, remove duplicates, and summarize a collection of values.",
            "success_criteria": "Select suitable collections, state their common operation costs, and keep functions small with clear inputs and outputs.",
        },
        {
            "topic": f"Object-oriented design in {language}",
            "terms": ["class", "object", "constructor", "encapsulation", "composition", "polymorphism"],
            "practice_task": "Model a small library system with books, members, loans, validation rules, and at least two cooperating classes.",
            "success_criteria": "Separate responsibilities correctly and justify composition, inheritance, access modifiers, and object lifetime choices.",
        },
        {
            "topic": f"Algorithms and complexity with {language}",
            "terms": ["Big-O", "linear search", "binary search", "sorting", "recursion", "time/space trade-off"],
            "practice_task": "Implement search and sorting examples, test boundary cases, and compare operation growth as input size increases.",
            "success_criteria": "Derive rather than memorize complexity and identify correctness, preconditions, and edge cases for each algorithm.",
        },
        {
            "topic": f"Robust {language} development and testing",
            "terms": profile["advanced"],
            "practice_task": "Turn the earlier project into a structured package with error handling, automated tests, dependency management, and debugging notes.",
            "success_criteria": "Build and run the project and tests from a clean terminal, diagnose one failing test, and explain the error-handling strategy.",
        },
    ]


def foundation_curriculum(role: str, domains: List[str], skipped_topics: List[str]) -> List[Dict[str, Any]]:
    """Build prerequisite-first coverage when the candidate answered nothing."""
    context = " ".join([role, *domains, *skipped_topics]).lower()
    language_aliases = [
        ("JavaScript", ("javascript", "typescript", "node.js", "nodejs")),
        ("Java", ("java developer", " java ", "jvm", "spring boot")),
        ("C++", ("c++", "cpp")),
        ("C#", ("c#", "csharp", ".net")),
    ]
    padded_context = f" {context} "
    for language, aliases in language_aliases:
        if any(alias in padded_context for alias in aliases):
            return programming_language_curriculum(language)

    if "nlp" in context or "natural language" in context:
        return [
            {"topic": "Language and NLP foundations", "terms": ["corpus", "document", "token", "vocabulary", "syntax", "semantics"], "practice_task": "Annotate a short corpus by hand with sentences, tokens, parts of speech, entities, and ambiguous meanings.", "success_criteria": "Distinguish linguistic levels and explain how ambiguity affects an NLP system."},
            {"topic": "Text preprocessing pipelines", "terms": ["normalization", "tokenization", "stop words", "stemming", "lemmatization", "POS tagging"], "practice_task": "Build an NLTK or spaCy pipeline and compare the output of stemming, lemmatization, and stop-word removal on the same text.", "success_criteria": "Choose preprocessing steps for a stated task and explain what information each step removes or preserves."},
            {"topic": "Text representations", "terms": ["bag of words", "n-gram", "TF-IDF", "embedding", "cosine similarity", "out-of-vocabulary token"], "practice_task": "Represent a small document collection with TF-IDF and embeddings, then rank documents for one query.", "success_criteria": "Interpret vector dimensions and similarity scores and compare sparse versus dense representations."},
            {"topic": "Core NLP tasks and evaluation", "terms": ["classification", "NER", "sequence labelling", "precision", "recall", "F1-score"], "practice_task": "Evaluate supplied predictions for sentiment and named entities by constructing confusion counts and calculating precision, recall, and F1.", "success_criteria": "Calculate each metric correctly and choose the metric that matches the business cost of errors."},
            {"topic": "Neural NLP and transformers", "terms": ["token embedding", "attention", "transformer", "contextual representation", "fine-tuning", "BERT"], "practice_task": "Use a pretrained transformer pipeline on sample text and inspect tokenization, confidence scores, correct cases, and failure cases.", "success_criteria": "Explain attention and contextual embeddings conceptually and identify when fine-tuning is required."},
            {"topic": "End-to-end NLP engineering", "terms": ["dataset split", "baseline", "pipeline", "error analysis", "latency", "model monitoring"], "practice_task": "Design a small text-classification project from data definition through baseline, evaluation, API inference, and monitoring.", "success_criteria": "Present a reproducible design with leakage prevention, suitable metrics, deployment constraints, and categorized errors."},
        ]

    if (
        any(term in context for term in ("machine learning", "data scientist", "deep learning"))
        or " ml " in padded_context or " dl " in padded_context
    ):
        return [
            {"topic": "Mathematics and statistics for machine learning", "terms": ["vector/matrix", "probability", "distribution", "mean/variance", "derivative", "gradient"], "practice_task": "Use NumPy to calculate descriptive statistics, vector operations, and a numerical gradient on a small dataset.", "success_criteria": "Interpret each calculation and connect probability, linear algebra, and gradients to model training."},
            {"topic": "Python data stack", "terms": ["NumPy", "pandas", "DataFrame", "indexing", "missing values", "visualization"], "practice_task": "Load a CSV, inspect types and missingness, clean it, summarize groups, and create two meaningful plots.", "success_criteria": "Produce a reproducible notebook with justified cleaning decisions and accurate interpretations."},
            {"topic": "Data preparation and experimental design", "terms": ["feature", "target", "train/validation/test", "leakage", "encoding", "scaling"], "practice_task": "Create a preprocessing pipeline for mixed numeric/categorical data and a leakage-safe data split.", "success_criteria": "Explain every transformation, fit it only on training data, and verify consistent output shapes."},
            {"topic": "Supervised learning foundations", "terms": ["regression", "classification", "loss", "overfitting", "regularization", "cross-validation"], "practice_task": "Train one linear and one tree-based baseline, tune one parameter, and compare validation behavior.", "success_criteria": "Select an appropriate model and diagnose bias, variance, overfitting, and underfitting from evidence."},
            {"topic": "Evaluation and error analysis", "terms": ["confusion matrix", "precision", "recall", "F1", "ROC-AUC", "MAE/RMSE"], "practice_task": "Evaluate a model with task-appropriate metrics and categorize at least ten incorrect predictions.", "success_criteria": "Choose metrics from business costs and turn error categories into specific improvement hypotheses."},
            {"topic": "Model delivery and monitoring", "terms": ["serialization", "inference API", "latency", "drift", "reproducibility", "monitoring"], "practice_task": "Package a trained pipeline behind a small API and define input validation, logging, drift, and performance checks.", "success_criteria": "Demonstrate consistent inference and explain versioning, monitoring, rollback, and retraining triggers."},
        ]

    if "data_analysis" in context or "data analyst" in context or "sql" in context:
        return [
            {"topic": "Analytical thinking and descriptive statistics", "terms": ["business question", "metric", "mean/median", "variance", "distribution", "correlation"], "practice_task": "Translate a business scenario into measurable questions and calculate a compact descriptive summary.", "success_criteria": "Define metrics unambiguously and separate observed association from causal claims."},
            {"topic": "Data cleaning and quality", "terms": ["missing value", "duplicate", "outlier", "data type", "validation rule", "data lineage"], "practice_task": "Profile a messy table, document quality issues, clean it, and produce before/after validation counts.", "success_criteria": "Make reproducible cleaning decisions without silently losing important records."},
            {"topic": "SQL analysis", "terms": ["SELECT", "JOIN", "GROUP BY", "CTE", "window function", "query plan"], "practice_task": "Answer five business questions across related tables using joins, aggregations, a CTE, and a window function.", "success_criteria": "Return correct grain and totals, handle nulls, and explain how indexes and query plans affect performance."},
            {"topic": "Python and pandas analysis", "terms": ["DataFrame", "filter", "groupby", "merge", "pivot", "datetime"], "practice_task": "Reproduce a SQL analysis in pandas and compare the transformations and results step by step.", "success_criteria": "Produce matching outputs and explain index alignment, joins, missing values, and vectorized operations."},
            {"topic": "Visualization and communication", "terms": ["chart selection", "scale", "label", "comparison", "trend", "dashboard"], "practice_task": "Create a one-page analysis with three charts that answer specific stakeholder questions without visual distortion.", "success_criteria": "Justify every chart and communicate the finding, uncertainty, and recommended action clearly."},
            {"topic": "End-to-end analytical case study", "terms": ["requirements", "KPI", "data extraction", "analysis", "insight", "recommendation"], "practice_task": "Complete a case study from stakeholder request through SQL/pandas analysis to an executive summary.", "success_criteria": "Deliver traceable calculations, defensible insights, limitations, and decisions linked to business objectives."},
        ]

    if "python" in context:
        return [
            {
                "topic": "Python foundations and syntax",
                "terms": ["Python interpreter", "scripts", "indentation", "variables", "dynamic typing", "comments", "PEP 8"],
                "practice_task": "Install or open Python, run a Hello World script, declare values of five built-in types, and correct three indentation or syntax errors.",
                "success_criteria": "Run a .py file independently and explain statements, indentation, variable binding, type(), and basic interpreter errors.",
            },
            {
                "topic": "Operators, control flow, functions, and collections",
                "terms": ["arithmetic/comparison operators", "if/elif/else", "for/while", "function", "parameter", "return", "list/tuple/dict/set"],
                "practice_task": "Build a command-line grade calculator using a function, validation, conditions, a loop, and a collection of student scores.",
                "success_criteria": "Handle valid and invalid inputs and explain which collection, loop, and conditional branch is used at each step.",
            },
            topic_learning_module("Identity and equality in Python", "Python"),
            topic_learning_module("Classes and objects in Python", "Python"),
            {
                "topic": "Algorithms, sorting, searching, and Big-O",
                "terms": ["algorithm", "time complexity", "space complexity", "linear search", "binary search", "bubble sort", "O(1)/O(n)/O(log n)/O(n²)"],
                "practice_task": "Implement linear search, binary search, and bubble sort; count operations on increasingly large lists and compare their growth.",
                "success_criteria": "State each precondition and derive the time/space complexity instead of memorizing it, including best and worst cases.",
            },
            {
                "topic": "Exceptions, modules, testing, and project workflow",
                "terms": ["try/except/finally", "import", "module", "virtual environment", "pip", "pytest", "debugging"],
                "practice_task": "Create a two-file Python project with input validation, exception handling, and pytest tests for successful and failing cases.",
                "success_criteria": "Run the program and test suite from the terminal, add a dependency in a virtual environment, and diagnose one intentional failure.",
            },
        ]

    modules = [topic_learning_module(topic, domains[0] if domains else "") for topic in skipped_topics]
    return [{
        "topic": f"{role or 'Interview'} foundations",
        "terms": ["core vocabulary", "fundamental principles", "standard workflow", "common tools", "basic examples"],
        "practice_task": f"Create a one-page concept map defining the foundational vocabulary and workflow required for {role or 'this role'}.",
        "success_criteria": "Define every core term accurately and connect each foundation to one practical scenario without relying on memorized wording.",
    }, *modules]


def _next_tier_label(avg_score: float) -> str:
    """Next-session goal, phrased as a performance tier rather than a target percentage."""
    if avg_score >= 75:
        return "Maintain an Excellent rating with more consistency across topics"
    elif avg_score >= 50:
        return "Move up to an Excellent rating"
    else:
        return "Move up to a Good rating"

# Rewrites a question into a topic label for display (e.g. "What are
# the advantages of using a CNN...?" -> "Advantages of using a CNN...").
# Rule-based only; the original question text is untouched elsewhere.
_TOPIC_PATTERNS = [
    (re.compile(r"^explain the difference between ['\"]?is['\"]? and ['\"]?==['\"]? in python$", re.IGNORECASE), 'Object identity and value equality in Python'),
    (re.compile(r'^how do you write a basic unit test in python$', re.IGNORECASE), 'Basic unit testing in Python'),
    (re.compile(r'^what is the difference between class and object in python$', re.IGNORECASE), 'Classes and objects in Python'),
    (re.compile(r"^what(?:'s|s| is) bubble sort in python$", re.IGNORECASE), 'Bubble sort in Python'),
    (re.compile(r'^in what real[- ]world applications (?:is|are)\s+(.+?)\s+used$', re.IGNORECASE), r'Real-world applications of \1'),
    (re.compile(r'^what real[- ]world applications (?:use|employ)\s+', re.IGNORECASE), 'Real-world applications of '),
    (re.compile(r'^what are some advantages (?:in|of) using\s+', re.IGNORECASE), 'Advantages of using '),
    (re.compile(r'^what are the advantages (?:in|of) using\s+', re.IGNORECASE), 'Advantages of using '),
    (re.compile(r'^what are the advantages (?:in|of)\s+', re.IGNORECASE), 'Advantages of '),
    (re.compile(r'^what is the meaning of\s+', re.IGNORECASE), 'Meaning of '),
    (re.compile(r'^what is the difference between\s+', re.IGNORECASE), 'Difference between '),
    (re.compile(r'^what are the differences between\s+', re.IGNORECASE), 'Differences between '),
    (re.compile(r'^where (?:is|are)\s+(.+?)\s+used$', re.IGNORECASE), r'Uses of \1'),
    (re.compile(r'^when should you\s+', re.IGNORECASE), 'When to '),
    (re.compile(r'^when do you\s+', re.IGNORECASE), 'When to '),
    (re.compile(r'^how do you\s+', re.IGNORECASE), ''),
    (re.compile(r'^how is\s+', re.IGNORECASE), 'How '),
    (re.compile(r'^how does\s+', re.IGNORECASE), 'How '),
    (re.compile(r'^explain\s+', re.IGNORECASE), ''),
    (re.compile(r'^describe\s+', re.IGNORECASE), ''),
    (re.compile(r'^what (?:is|are|was|were)\s+(?:the\s+)?', re.IGNORECASE), ''),
    (re.compile(r'^why (?:is|are)\s+', re.IGNORECASE), 'Why '),
]


def question_to_topic(question: str) -> str:
    """Rewrite a question into a topic-label phrase for display in the
    report (e.g. "What are the applications of X?" -> "Applications of
    X"). Falls back to just stripping the trailing "?" if no pattern
    matches, so it always degrades gracefully rather than mangling text."""
    if not question:
        return question

    text = question.strip()
    text = re.sub(r'[?.!]+$', '', text).strip()

    for pattern, replacement in _TOPIC_PATTERNS:
        new_text, count = pattern.subn(replacement, text, count=1)
        if count:
            text = new_text.strip()
            break

    if not text:
        return question.rstrip('?').strip()

    return text[0].upper() + text[1:]


class ReportGenerator:
    """Builds interview session reports in JSON format."""

    def __init__(self, session_id: str, domain: str, started_at: str):
        """Initialize report for a session."""
        self.session_id = session_id
        self.domain = domain
        self.started_at = started_at
        self.questions: List[Dict[str, Any]] = []
        self.question_number = 0

        self.reports_dir = Path(__file__).parent.parent.parent / "results" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized report for session {session_id}")

    def append_answer(
        self,
        question_id: int,
        question: str,
        user_answer: str,
        similarity_score: float,
        feedback: str,
        skipped: bool = False,
        difficulty: str = "",
        round_name: str = "Easy",
        domain: str = ""
    ) -> None:
        """Append answered question to report."""
        self.question_number += 1

        answer_record = {
            "question_number": self.question_number,
            "question_id": question_id,
            "question": question,
            "user_answer": user_answer if not skipped else "",
            "similarity_score": round(similarity_score, 2) if not skipped else 0.0,
            "feedback": feedback,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "skipped": skipped,
            "difficulty": difficulty,
            "round": round_name,
            "domain": domain
        }

        self.questions.append(answer_record)
        logger.debug(f"Appended answer #{self.question_number} to report")

    def finalize_report(
        self,
        ended_at: str,
        role: str = "",
        selected_domains: Optional[List[str]] = None,
        round_answers: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        scoring_model: str = ""
    ) -> Dict[str, Any]:
        """Generate final interview report with round statistics."""
        answered = sum(1 for q in self.questions if not q["skipped"])
        skipped = sum(1 for q in self.questions if q["skipped"])
        avg_score = (
            sum(q["similarity_score"] for q in self.questions if not q["skipped"]) / answered
            if answered > 0 else 0.0
        )
        avg_score = round(avg_score, 2)

        round_stats = {}
        if round_answers:
            for round_name, answers in round_answers.items():
                scored_answers = [answer for answer in answers if not answer.get("skipped")]
                if scored_answers:
                    round_score = sum(a["similarity_score"] for a in scored_answers) / len(scored_answers)
                    round_stats[f"{round_name.lower()}_average"] = round(round_score, 2)
                    round_stats[f"{round_name.lower()}_questions"] = len(scored_answers)

        report = {
            "interview_id": self.session_id,
            "interview_role": role,
            "selected_domains": selected_domains or [self.domain],
            "scoring_model": scoring_model,
            "started_at": self.started_at,
            "ended_at": ended_at,
            "total_questions": len(self.questions),
            "questions_answered": answered,
            "questions_skipped": skipped,
            "average_score": avg_score,
            **round_stats,
            "questions": self.questions,
            "analysis": self._build_analysis(avg_score, ended_at, role=role)
        }

        logger.info(f"Finalized report for session {self.session_id}")
        return report

    # Derives strengths/weaknesses/learning plan from stored scores and
    # persists them into the saved JSON report.
    def _build_analysis(self, avg_score: float, ended_at: str, role: str = "") -> Dict[str, Any]:
        answered_qs = [q for q in self.questions if not q["skipped"]]
        skipped_qs = [q for q in self.questions if q["skipped"]]

        # ---- Domain-wise breakdown (only meaningful if domain was recorded) ----
        domain_scores: Dict[str, List[float]] = {}
        for q in answered_qs:
            domain = (q.get("domain") or "General").strip() or "General"
            domain_scores.setdefault(domain, []).append(q["similarity_score"])

        domain_breakdown = [
            {
                "domain": domain,
                "average": round(sum(scores) / len(scores), 2),
                "questions": len(scores)
            }
            for domain, scores in domain_scores.items()
        ]
        domain_breakdown.sort(key=lambda d: d["average"])

        # ---- Overall performance label ----
        if not answered_qs:
            performance_label = "Preparation Required (No answered questions)"
        elif avg_score >= 75:
            performance_label = f"Excellent ({avg_score}%)"
        elif avg_score >= 50:
            performance_label = f"Good ({avg_score}%)"
        else:
            performance_label = f"Needs Improvement ({avg_score}%)"

        # ---- Strengths: domains averaging well + individual standout answers ----
        strong_domains = [
            d["domain"] for d in sorted(domain_breakdown, key=lambda d: -d["average"])
            if d["average"] >= STRONG_THRESHOLD
        ]
        highlights = sorted(
            [q for q in answered_qs if q["similarity_score"] >= HIGHLIGHT_THRESHOLD],
            key=lambda q: -q["similarity_score"]
        )[:3]
        demonstrated_topics = sorted(
            [q for q in answered_qs if q["similarity_score"] >= STRONG_THRESHOLD],
            key=lambda q: -q["similarity_score"]
        )[:5]

        # ---- Weaknesses: domains scoring low + the actual questions missed ----
        weak_domains = [d["domain"] for d in domain_breakdown if d["average"] < 50]
        weak_questions = sorted(
            [q for q in answered_qs if q["similarity_score"] < WEAK_THRESHOLD],
            key=lambda q: q["similarity_score"]
        )[:5]

        # ---- Personalized learning plan built from the real weak spots ----
        focus_domains = weak_domains or [d["domain"] for d in domain_breakdown[:1]]
        review_topics = [question_to_topic(q["question"]) for q in weak_questions[:3]]
        if not review_topics:
            review_topics = [question_to_topic(q["question"]) for q in skipped_qs[:5]]

        topic_domains = {
            question_to_topic(q["question"]): (q.get("domain") or "")
            for q in (weak_questions[:3] + skipped_qs[:5])
        }
        observed_domains = list(domain_scores) or list(dict.fromkeys(q.get("domain", "") for q in skipped_qs if q.get("domain")))
        if not answered_qs:
            technical_focus = foundation_curriculum(role, observed_domains, review_topics)
        elif review_topics:
            technical_focus = [topic_learning_module(topic, topic_domains.get(topic, "")) for topic in review_topics]
        else:
            technical_focus = []

        curriculum_names = [module["topic"] for module in technical_focus]
        foundation_actions = [
            f"Learn {module['topic']}: {', '.join(module['terms'][:5])}."
            for module in technical_focus[:3]
        ]
        applied_actions = [module["practice_task"] for module in technical_focus[3:6]]
        if not applied_actions:
            applied_actions = [module["practice_task"] for module in technical_focus[:3]]
        reassessment_actions = [
            f"Mastery check for {module['topic']}: {module['success_criteria']}"
            for module in technical_focus[-2:]
        ]
        reassessment_actions.append(
            f"After completing the curriculum, take a new {role or 'role-based'} mock interview in this application to measure broader readiness."
        )

        learning_plan = [
            {
                "phase": "Phase 1: Build the Foundations",
                "focus": ", ".join(curriculum_names[:3]) or "Core foundations",
                "actions": foundation_actions or ["Consolidate the core concepts demonstrated during the interview."]
            },
            {
                "phase": "Phase 2: Apply the Knowledge",
                "focus": ", ".join(curriculum_names[3:6]) or ", ".join(curriculum_names),
                "actions": applied_actions
            },
            {
                "phase": "Phase 3: Verify Readiness",
                "focus": "Module mastery followed by a new role-based mock interview",
                "actions": reassessment_actions
            }
        ]

        # ---- Dynamic recommendations ----
        recommendations: List[str] = []
        if not answered_qs:
            recommendations.extend([
                f"No answers were submitted, so begin with {curriculum_names[0] if curriculum_names else 'the role foundations'} rather than jumping directly to interview questions.",
                "Complete the curriculum in order: foundations first, guided practice second, and mastery checks last.",
                f"When the listed mastery checks are complete, start a new {role or 'role-based'} interview in this application; the system will select a fresh role-appropriate question set.",
            ])
        elif demonstrated_topics:
            recommendations.append(
                "Demonstrated strengths: " + "; ".join(question_to_topic(q["question"]) for q in demonstrated_topics) + "."
            )
        if skipped_qs:
            if answered_qs:
                recommendations.append(
                    "Preserve the demonstrated strengths, then complete the Technical Study Guide for the unassessed topics before starting a new role-based interview."
                )
        if weak_domains:
            domain_topics = "; ".join(review_topics) if review_topics else ", ".join(weak_domains)
            recommendations.append(
                f"For {', '.join(weak_domains)}, build technical depth in {domain_topics} through implementation, metric-based evaluation, and error analysis."
            )
        if weak_questions:
            for topic in review_topics:
                points = technical_study_points(topic, topic_domains.get(topic, ""))
                recommendations.append(f"Learn {topic} by covering {', '.join(points[:3])}.")
        hard_scores = [q["similarity_score"] for q in answered_qs if q.get("difficulty") == "Hard"]
        if hard_scores and (sum(hard_scores) / len(hard_scores)) < 50:
            recommendations.append(
                "Hard-round questions pulled your score down the most - prioritize advanced and edge-case topics."
            )
        if not recommendations:
            recommendations.append("Solid, well-rounded performance - keep practicing to maintain consistency.")
        if answered_qs:
            recommendations.append(
                f"After completing the module mastery checks, take a new {role or 'role-based'} mock interview in this application and compare the new overall and domain scores."
            )

        fallback_technical_focus = technical_focus
        fallback_learning_plan = learning_plan

        # Prefer a complete Ollama-written coaching section when available.
        # The validated rule-based content above remains the offline fallback.
        recommendations_source = "rule_based"
        try:
            from llm_report import generate_coaching_analysis
            coaching = generate_coaching_analysis({
                "role": role,
                "average_score": avg_score,
                "performance_label": performance_label,
                "strong_domains": strong_domains,
                "weak_domains": weak_domains,
                "weak_items": [
                    {
                        "topic": question_to_topic(q["question"]),
                        "question": q["question"],
                        "candidate_answer": q.get("user_answer", ""),
                        "feedback": q.get("feedback", ""),
                        "score": q["similarity_score"],
                        "domain": q.get("domain", ""),
                        "difficulty": q.get("difficulty", ""),
                    }
                    for q in weak_questions
                ],
                "strong_items": [
                    {
                        "topic": question_to_topic(q["question"]),
                        "question": q["question"],
                        "candidate_answer": q.get("user_answer", ""),
                        "feedback": q.get("feedback", ""),
                        "score": q["similarity_score"],
                        "domain": q.get("domain", ""),
                        "difficulty": q.get("difficulty", ""),
                    }
                    for q in demonstrated_topics
                ],
                "answered_count": len(answered_qs),
                "skipped_count": len(skipped_qs),
                "skipped_items": [
                    {
                        "topic": question_to_topic(q["question"]),
                        "domain": q.get("domain", ""),
                        "difficulty": q.get("difficulty", ""),
                    }
                    for q in skipped_qs[:5]
                ],
            })
            if coaching:
                recommendations = coaching["recommendations"]
                if not answered_qs:
                    # A small local model can still overfit to the literal skipped
                    # questions. Never let it remove the prerequisite-first syllabus.
                    technical_focus = fallback_technical_focus
                    learning_plan = fallback_learning_plan
                    recommendations_source = "llm_with_foundation_guard"
                else:
                    technical_focus = coaching["technical_focus"]
                    learning_plan = coaching["learning_plan"]
                    recommendations_source = "llm"
        except Exception as e:
            logger.warning(f"LLM recommendations unavailable, using rule-based fallback: {e}")

        try:
            ended_dt = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            ended_dt = datetime.utcnow()
        next_assessment_date = (ended_dt + timedelta(days=7)).date().isoformat()

        return {
            "performance_label": performance_label,
            "domain_breakdown": domain_breakdown,
            "strengths": {
                "domains": strong_domains,
                "demonstrated_topics": [
                    {
                        "topic": question_to_topic(q["question"]),
                        "score": q["similarity_score"],
                        "domain": q.get("domain"),
                    }
                    for q in demonstrated_topics
                ],
                "highlights": [
                    {
                        "question": q["question"],
                        "score": q["similarity_score"],
                        "difficulty": q.get("difficulty"),
                        "domain": q.get("domain")
                    }
                    for q in highlights
                ]
            },
            "weaknesses": {
                "domains": weak_domains,
                "weak_questions": [
                    {
                        "question": question_to_topic(q["question"]),
                        "score": q["similarity_score"],
                        "difficulty": q.get("difficulty"),
                        "domain": q.get("domain")
                    }
                    for q in weak_questions
                ],
                "skipped_questions": [
                    {
                        "question": question_to_topic(q["question"]),
                        "difficulty": q.get("difficulty"),
                        "domain": q.get("domain")
                    }
                    for q in skipped_qs
                ]
            },
            "learning_plan": learning_plan,
            "technical_focus": technical_focus,
            "recommendations": recommendations,
            "recommendations_source": recommendations_source,
            "next_assessment_date": next_assessment_date
        }

    def save_report(self, report: Dict[str, Any]) -> Optional[str]:
        """Save report to JSON file."""
        try:
            json_filename = f"{self.session_id}_report.json"
            json_filepath = self.reports_dir / json_filename

            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved JSON report to {json_filepath}")
            return str(json_filepath)

        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            return None

    def get_report_dict(self) -> Dict[str, Any]:
        """Get current report as dict."""
        answered = sum(1 for q in self.questions if not q["skipped"])
        skipped = sum(1 for q in self.questions if q["skipped"])

        return {
            "interview_id": self.session_id,
            "started_at": self.started_at,
            "domain": self.domain,
            "total_questions_so_far": len(self.questions),
            "questions_answered": answered,
            "questions_skipped": skipped,
            "questions": self.questions
        }
