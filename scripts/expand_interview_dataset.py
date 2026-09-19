"""Generate broad raw interview-question coverage for the preprocessing pipeline."""
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUTPUT_FILE = RAW_DIR / "expanded_interview_questions.csv"


DOMAINS = {
    "Machine Learning": [
        "supervised learning", "unsupervised learning", "linear regression", "logistic regression",
        "decision trees", "random forests", "gradient boosting", "XGBoost", "support vector machines",
        "K-nearest neighbours", "K-means clustering", "hierarchical clustering", "PCA",
        "feature scaling", "categorical encoding", "missing value handling", "outlier handling",
        "train validation test splits", "cross-validation", "bias variance trade-off", "overfitting",
        "underfitting", "regularisation", "L1 versus L2 penalties", "hyperparameter tuning",
        "grid search", "random search", "Bayesian optimisation", "class imbalance", "ROC AUC",
        "precision and recall", "F1 score", "calibration", "threshold selection", "data leakage",
        "model interpretation", "SHAP values", "permutation importance", "pipelines",
        "production monitoring", "concept drift", "anomaly detection", "recommendation systems",
        "time-series features", "ensemble learning", "model selection", "probability estimates",
        "cost-sensitive learning", "feature selection", "target encoding", "nested cross-validation",
    ],
    "Deep Learning": [
        "perceptrons", "multilayer neural networks", "activation functions", "ReLU", "sigmoid and tanh",
        "loss functions", "backpropagation", "gradient descent", "stochastic gradient descent",
        "Adam optimiser", "learning rate schedules", "weight initialisation", "vanishing gradients",
        "exploding gradients", "batch normalisation", "layer normalisation", "dropout",
        "early stopping", "CNN convolution layers", "pooling layers", "image augmentation",
        "transfer learning", "fine-tuning", "RNNs", "LSTMs", "GRUs", "attention mechanism",
        "transformer encoder", "transformer decoder", "self-attention", "positional encoding",
        "embeddings", "sequence-to-sequence models", "autoencoders", "variational autoencoders",
        "GANs", "GPU training", "mixed precision", "batch size", "gradient clipping",
        "regularisation in neural networks", "training instability", "inference latency",
        "model compression", "knowledge distillation", "multimodal learning", "hyperparameter tuning",
        "optimiser choice", "residual connections", "fine-tuning large models", "evaluation metrics",
    ],
    "NLP": [
        "tokenisation", "stemming", "lemmatisation", "stop-word removal", "bag-of-words",
        "TF-IDF", "n-grams", "word embeddings", "Word2Vec", "GloVe", "contextual embeddings",
        "Sentence Transformers", "cosine similarity", "text classification", "sentiment analysis",
        "named entity recognition", "part-of-speech tagging", "sequence labelling", "language modelling",
        "attention in NLP", "transformers", "BERT", "encoder-only models", "decoder-only models",
        "semantic search", "information retrieval", "BM25", "dense retrieval", "vector databases",
        "chunking", "RAG retrieval", "reranking", "hallucination", "prompt evaluation",
        "LLM evaluation", "BLEU and ROUGE", "precision and recall for retrieval", "text preprocessing",
        "domain adaptation", "fine-tuning NLP models", "zero-shot classification", "few-shot prompting",
        "entity linking", "question answering", "summarisation", "topic modelling", "document similarity",
        "embedding drift", "retrieval grounding", "prompt injection", "long-context limitations",
    ],
    "Python": [
        "lists and tuples", "dictionaries", "sets", "mutability", "copy versus deepcopy", "list comprehensions",
        "dictionary comprehensions", "generators", "iterators", "decorators", "lambda functions",
        "map filter reduce", "exception handling", "context managers", "file handling", "classes",
        "inheritance", "dunder methods", "scope and closures", "type hints", "dataclasses",
        "virtual environments", "package imports", "debugging", "logging", "unit testing",
        "pytest fixtures", "NumPy arrays", "NumPy broadcasting", "Pandas DataFrames", "Pandas groupby",
        "Pandas merge", "missing values in Pandas", "date handling", "vectorisation",
        "performance profiling", "memory usage", "regular expressions", "JSON handling", "CSV handling",
        "SQL from Python", "API requests", "async basics", "multiprocessing", "threading",
        "object-oriented design", "Pythonic code", "dependency management", "notebook hygiene",
        "data pipeline scripting",
    ],
    "SQL": [
        "SELECT queries", "WHERE filtering", "ORDER BY", "GROUP BY", "HAVING", "INNER JOIN",
        "LEFT JOIN", "FULL OUTER JOIN", "self joins", "cross joins", "subqueries", "correlated subqueries",
        "common table expressions", "CASE expressions", "NULL handling", "COALESCE", "date functions",
        "string functions", "aggregate functions", "COUNT DISTINCT", "window functions", "ROW_NUMBER",
        "RANK and DENSE_RANK", "LAG and LEAD", "running totals", "moving averages", "partitioning",
        "top N per group", "deduplication queries", "anti joins", "semi joins", "primary keys",
        "foreign keys", "normalisation", "indexes", "query plans", "query optimisation",
        "analytical SQL", "cohort analysis SQL", "retention queries", "funnel analysis",
        "slowly changing dimensions", "star schema", "fact and dimension tables", "transactions",
        "isolation levels", "views", "temporary tables", "data quality checks", "SQL debugging",
        "realistic business metrics",
    ],
    "Data Analysis": [
        "exploratory data analysis", "descriptive statistics", "mean median mode", "variance and standard deviation",
        "outlier detection", "missing data analysis", "correlation", "causation versus correlation",
        "sampling bias", "selection bias", "hypothesis testing", "p-values", "confidence intervals",
        "A/B testing", "power analysis", "effect size", "statistical significance", "practical significance",
        "normal distribution", "skewed distributions", "binomial distribution", "Poisson distribution",
        "KPI design", "north star metrics", "conversion rate", "retention", "churn analysis",
        "cohort analysis", "segmentation", "funnel analysis", "time-series trend analysis",
        "seasonality", "forecasting basics", "dashboard design", "data visualisation", "chart selection",
        "misleading charts", "data cleaning", "data quality checks", "business requirements",
        "stakeholder communication", "root cause analysis", "experiment interpretation",
        "confidence versus prediction intervals", "regression interpretation", "feature distributions",
        "anomaly investigation", "metric trade-offs", "decision recommendations", "reporting automation",
    ],
}


QUESTION_PATTERNS = [
    ("Easy", "What is {topic} in {domain}?", "Define the idea, explain why it matters, and mention a simple example."),
    ("Easy", "Why is {topic} important in a real interview or project?", "Connect the concept to practical model, data, or business decisions."),
    ("Easy", "What mistake do beginners often make with {topic}?", "Name the common mistake, its consequence, and the safer habit."),
    ("Medium", "How would you apply {topic} in a realistic {domain} workflow?", "Describe the steps, assumptions, checks, and expected output."),
    ("Medium", "How would you evaluate whether {topic} was working correctly?", "Mention measurable evidence, validation checks, and failure signs."),
    ("Medium", "Compare {topic} with a simpler alternative.", "Explain the trade-off in accuracy, interpretability, cost, and maintainability."),
    ("Medium", "A project result looks suspicious after using {topic}. How would you debug it?", "Inspect data assumptions, implementation details, metrics, and leakage risks."),
    ("Medium", "What interview follow-up would you expect after explaining {topic}?", "Prepare a deeper answer involving edge cases, trade-offs, and limitations."),
    ("Medium", "When would you avoid using {topic}?", "Give conditions where it is unnecessary, misleading, too costly, or hard to justify."),
    ("Hard", "Design an end-to-end solution that uses {topic} under production constraints.", "Discuss architecture, validation, monitoring, latency, reliability, and ownership."),
    ("Hard", "What are the main edge cases and failure modes for {topic}?", "Identify subtle risks, diagnostic signals, and mitigation strategies."),
    ("Hard", "How would you explain the trade-offs of {topic} to a technical panel?", "Balance theory, implementation detail, evidence, and business impact."),
]


DOMAIN_CONTEXT = {
    "Machine Learning": "predictive modelling quality, generalisation, leakage control, and deployment reliability",
    "Deep Learning": "training stability, representation learning, compute limits, and model behaviour",
    "NLP": "language meaning, retrieval quality, text preprocessing, and grounded model outputs",
    "Python": "readable implementation, correctness, testing, data handling, and performance",
    "SQL": "correct joins, aggregations, analytical logic, data modelling, and query efficiency",
    "Data Analysis": "statistical reasoning, metric design, evidence quality, and stakeholder decisions",
}


def answer_for(domain, topic, instruction, difficulty):
    context = DOMAIN_CONTEXT[domain]
    if difficulty == "Easy":
        return (
            f"{topic.title()} is a core {domain} concept related to {context}. "
            f"A strong answer should {instruction.lower()} It should also state the purpose, give a small practical example, "
            "and avoid vague wording. In interviews, the key is to show that you know what the concept does, when it is useful, "
            "and what can go wrong if it is applied mechanically."
        )
    if difficulty == "Medium":
        return (
            f"For {topic}, a good candidate should {instruction.lower()} Start by clarifying the data, objective, and constraints. "
            f"Then describe how the method fits into a {domain} workflow, how you would validate it, and which metrics or checks would prove it is reliable. "
            "The answer should include trade-offs, assumptions, and at least one failure mode rather than only giving a definition."
        )
    return (
        f"A strong advanced answer on {topic} should {instruction.lower()} It should cover design choices, edge cases, evaluation strategy, "
        f"and operational risks in {domain}. The best response links the technical mechanism to measurable impact, explains alternatives, "
        "and describes how to monitor or debug the solution when real data changes."
    )


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    sequence = 1

    for domain, topics in DOMAINS.items():
        for topic in topics:
            for difficulty, pattern, instruction in QUESTION_PATTERNS:
                prefix = "".join(part[0].lower() for part in domain.split() if part[0].isalnum())
                rows.append({
                    "id": f"{prefix}_gen_{sequence:04d}",
                    "domain": domain,
                    "difficulty": difficulty,
                    "question": pattern.format(topic=topic, domain=domain),
                    "answer": answer_for(domain, topic, instruction, difficulty),
                })
                sequence += 1

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "domain", "difficulty", "question", "answer"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} generated questions to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
