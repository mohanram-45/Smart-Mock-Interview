"""Decision tables for Stage 1B (v2). Keys are stable record ids (smi-NNNN) or plan ids (P-XXX-NN)."""

# topics for records that enter the dataset from the review queue (existing records keep their v1 topic)
QUEUE_TOPIC = {
 "smi-0001": "Statistics fundamentals", "smi-0015": "Analytical case studies", "smi-0018": "Analytical case studies",
 "smi-0034": "Deep learning overview", "smi-0053": "Activation functions", "smi-0062": "Initialisation and optimisation",
 "smi-0100": "Autoencoders and generative models", "smi-0119": "Convolutional networks", "smi-0121": "Initialisation and optimisation",
 "smi-0130": "Initialisation and optimisation", "smi-0148": "Decision trees and ensembles", "smi-0167": "Statistics fundamentals",
 "smi-0185": "Feature engineering and data preparation", "smi-0191": "Neural network fundamentals",
 "smi-0192": "Feature engineering and data preparation", "smi-0195": "Dimensionality reduction", "smi-0199": "ML foundations",
 "smi-0216": "Advanced learning paradigms", "smi-0229": "Feature engineering and data preparation", "smi-0240": "Recommender systems",
 "smi-0253": "Applied ML case studies", "smi-0257": "Instance-based and probabilistic classifiers", "smi-0270": "Advanced learning paradigms",
 "smi-0297": "Recommender systems", "smi-0314": "Statistics fundamentals", "smi-0323": "Decision trees and ensembles",
 "smi-0343": "Semantics and pragmatics", "smi-0345": "Text preprocessing and representation", "smi-0347": "Text preprocessing and representation",
 "smi-0349": "Text preprocessing and representation", "smi-0355": "NLP fundamentals", "smi-0356": "NLP fundamentals",
 "smi-0367": "NLP fundamentals", "smi-0370": "Semantics and pragmatics", "smi-0395": "Product and business metrics",
 "smi-0396": "Product and business metrics", "smi-0397": "Product and business metrics", "smi-0398": "Product and business metrics",
 "smi-0399": "Product and business metrics", "smi-0400": "Analytical case studies", "smi-0401": "Analytical case studies",
 "smi-0402": "Analytical case studies", "smi-0405": "Hypothesis testing and A/B testing", "smi-0463": "Testing",
}
# limitations that remain true after Stage 1B for specific records (everything else is cleared by the rewrite)
QUEUE_LIMITS = {
 "smi-0015": ["OPEN_ENDED"], "smi-0018": ["OPEN_ENDED"], "smi-0034": ["TIME_SENSITIVE"], "smi-0216": ["TEXTBOOK_CLAIMS_UNSOURCED"],
 "smi-0297": ["OPEN_ENDED"], "smi-0395": ["OPEN_ENDED"], "smi-0396": ["OPEN_ENDED"], "smi-0397": ["OPEN_ENDED"],
 "smi-0398": ["OPEN_ENDED"], "smi-0399": ["OPEN_ENDED"], "smi-0400": ["OPEN_ENDED"], "smi-0401": ["OPEN_ENDED"],
 "smi-0402": ["OPEN_ENDED"], "smi-0405": ["OPEN_ENDED"], "smi-0270": ["OPEN_ENDED"],
}
# bibliographic sources whose existence was confirmed by web search (content NOT read): attribution only
EXTRA_SOURCES = {
 "smi-0240": [{"title": "Linden, Smith, York - Amazon.com recommendations: item-to-item collaborative filtering (IEEE Internet Computing, 2003)",
               "url": "https://ieeexplore.ieee.org/document/1167344", "supports": "Attribution of the item-to-item collaborative filtering approach to Amazon (existence of the paper only).",
               "verification": "existence_confirmed_via_web_search; content_not_read"}],
 "smi-0257": [{"title": "Ng & Jordan - On discriminative vs. generative classifiers: a comparison of logistic regression and naive Bayes (NIPS 2001)",
               "url": "https://papers.nips.cc/paper/2001/hash/7b7a53e239400a13bd6be6c91c4f6c4e-Abstract.html", "supports": "Attribution of the sample-efficiency result for naive Bayes vs logistic regression (existence of the paper only).",
               "verification": "existence_confirmed_via_web_search; content_not_read"}],
 "smi-0216": [{"title": "van Hasselt et al. - Deep Reinforcement Learning and the Deadly Triad",
               "url": "https://ar5iv.labs.arxiv.org/html/1812.02648", "supports": "The term 'deadly triad' (function approximation, bootstrapping, off-policy) exists in the literature (existence only).",
               "verification": "existence_confirmed_via_web_search; content_not_read"}],
}
# manual text edits taken from independent-review side notes that had no machine-applicable replacement: (record key, field, old, new)
MANUAL_EDITS = [
 ("P-NLP-06", "common_mistakes", "Using a large finite or zero fill value instead of -inf (or forgetting the stable softmax)",
  "Using a zero fill value instead of -inf or a large negative value (or forgetting the stable softmax)"),
]
# queue items that stay in the queue after Stage 1B, with the reason (everything not listed and not resolved is carried over unchanged)
STAY_QUEUED_NOTE = {
 "smi-0457": "Stage 1B: deferred - web-framework (Flask) implementation is outside the six interview domains; recommend dropping it from the KB unless the scope is widened.",
 "smi-0459": "Stage 1B: deferred - JWT/authentication implementation is outside the six domains and security-sensitive; recommend dropping it.",
}
# pilot batch topics (controlled vocabulary; domain is taken from the plan)
PILOT_TOPIC = {
 "P-NLP-01": "Tokenisation and vocabulary", "P-NLP-02": "Text preprocessing and representation", "P-NLP-03": "NLP in production",
 "P-NLP-04": "Word embeddings", "P-NLP-05": "Language modelling and evaluation", "P-NLP-06": "Transformers and attention",
 "P-NLP-07": "Transformers and attention", "P-NLP-08": "Information extraction", "P-NLP-09": "Text classification",
 "P-NLP-10": "Semantic search and LLM applications", "P-NLP-11": "Semantic search and LLM applications", "P-NLP-12": "Language modelling and evaluation",
 "P-NLP-13": "Topic modelling", "P-NLP-14": "Text preprocessing and representation",
 "P-DL-01": "Backpropagation", "P-DL-02": "Training diagnostics and debugging", "P-DL-03": "Initialisation and optimisation",
 "P-DL-04": "Normalisation", "P-DL-05": "Training diagnostics and debugging", "P-DL-06": "Loss functions", "P-DL-07": "Regularisation and hyperparameters",
 "P-DL-08": "Architectures", "P-DL-09": "Transfer learning", "P-DL-10": "Convolutional networks", "P-DL-11": "Embeddings",
 "P-DL-12": "Model compression and deployment",
 "P-SQL-01": "Window functions", "P-SQL-02": "Query patterns", "P-SQL-03": "Window functions", "P-SQL-04": "Query patterns",
 "P-SQL-05": "NULL handling", "P-SQL-06": "Joins", "P-SQL-07": "Aggregation and pivoting", "P-SQL-08": "Cohort and retention queries",
 "P-SQL-09": "Query patterns", "P-SQL-10": "Subqueries and CTEs", "P-SQL-11": "Set operations", "P-SQL-12": "Joins",
 "P-SQL-13": "Window functions", "P-SQL-14": "Database design", "P-SQL-15": "Indexing and performance",
}

# Manual patches applied after independent review (record key = plan id). Each: (field, old, new); field "code.solution"/"code.test" or "answer".
# P-SQL-09: the compact form SELECT (SELECT DISTINCT salary ... ORDER BY salary DESC LIMIT 1 OFFSET 1) returned 100 instead of NULL for an
# all-equal-salary table on SQLite 3.37.2 (observed on the project owner's machine; correct on 3.45.1). The DISTINCT is moved into a derived table.
_OLD_SQL09 = "SELECT (\n  SELECT DISTINCT salary\n  FROM employees\n  ORDER BY salary DESC\n  LIMIT 1 OFFSET 1\n) AS second_highest_salary;"
_NEW_SQL09 = "SELECT (\n  SELECT salary\n  FROM (SELECT DISTINCT salary FROM employees)\n  ORDER BY salary DESC\n  LIMIT 1 OFFSET 1\n) AS second_highest_salary;"
PILOT_PATCHES = {"P-SQL-09": [
 ("answer", "```sql\n" + _OLD_SQL09 + "\n```", "```sql\n" + _NEW_SQL09 + "\n```"),
 ("answer", "The DISTINCT is applied before LIMIT/OFFSET, so the two 300s count once.",
  "The inner SELECT DISTINCT collapses ties first, so the two 300s count once, and the outer query orders those distinct values and skips the first. "
  "I put DISTINCT in a derived table on purpose: the more compact form SELECT (SELECT DISTINCT salary ... ORDER BY salary DESC LIMIT 1 OFFSET 1) returned 100 instead of NULL "
  "when every employee had the same salary on SQLite 3.37.2 (it was correct on 3.45.1; I did not investigate the cause), so this form is the safer one."),
 ("code.solution", _OLD_SQL09, _NEW_SQL09),
 ("code.test", repr(_OLD_SQL09), repr(_NEW_SQL09)),
]}
