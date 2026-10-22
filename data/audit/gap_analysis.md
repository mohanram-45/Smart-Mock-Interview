# Domain gap analysis

Method: for each domain a checklist of core interview concepts (drawn from standard curricula, not from the dataset) was matched by keyword against the **question text of the 367 KEEP/FIX seed records** (using proposed domain and proposed question where present). A hit count is only a coverage indicator: a hit does not mean the answer is good (many are one-liners) and 0 does not prove absence, but 0-1 hits is treated as a gap. Generated template questions are ignored because they repeat 304 topics with 12 fixed phrasings.

Reference sources are suggestions for a human curator to evaluate. **Licences and terms of use were not verified**; do not ingest text from any of them until the licence has been checked. No new questions were generated.

## Machine Learning  (189 KEEP/FIX seed questions)

| Concept | Hits | Gap? |
|---|---:|---|
| Linear/logistic regression assumptions & interpretation | 10 |  |
| Regularisation (L1/L2, elastic net) | 4 |  |
| Bias-variance, over/underfitting | 8 |  |
| Model evaluation: precision/recall/F1/ROC/PR | 7 |  |
| Cross-validation & data leakage | 5 |  |
| Tree ensembles: RF, gradient boosting, XGBoost | 14 |  |
| SVM & kernels | 12 |  |
| Clustering & choosing k | 6 |  |
| Dimensionality reduction (PCA, t-SNE) | 8 |  |
| Feature engineering/encoding/scaling | 5 |  |
| Class imbalance | 2 | thin |
| Missing data & outliers | 4 |  |
| Probability/statistics: Bayes, CLT, hypothesis tests, CI | 16 |  |
| Optimisation: gradient descent variants, learning rate | 2 | thin |
| Recommender systems | 9 |  |
| Time-series forecasting (ARIMA, stationarity, seasonality) | 2 | thin |
| Hyperparameter tuning (grid/random/Bayesian) | 2 | thin |
| Model interpretability (SHAP/LIME, feature importance) | 0 | **gap** |
| Anomaly detection | 0 | **gap** |
| ML system design / deployment / monitoring / drift | 1 | **gap** |
| Reinforcement learning basics | 1 | **gap** |
| Semi/self-supervised learning | 1 | **gap** |
| Calibration & probabilistic outputs | 0 | **gap** |
| Naive Bayes / KNN / decision-tree fundamentals | 15 |  |

**Missing or near-missing (6):** Model interpretability (SHAP/LIME, feature importance); Anomaly detection; ML system design / deployment / monitoring / drift; Reinforcement learning basics; Semi/self-supervised learning; Calibration & probabilistic outputs.

**Suggested reference sources (licences unverified):** scikit-learn User Guide (scikit-learn.org); An Introduction to Statistical Learning (James et al.; free PDF from authors); The Elements of Statistical Learning (Hastie et al.; free PDF from authors); Google Machine Learning Crash Course; Stanford CS229 lecture notes.

## Deep Learning  (67 KEEP/FIX seed questions)

| Concept | Hits | Gap? |
|---|---:|---|
| Backpropagation & chain rule | 1 | **gap** |
| Activation functions | 10 |  |
| Loss functions | 1 | **gap** |
| Optimisers (SGD, momentum, Adam) | 1 | **gap** |
| Regularisation: dropout, weight decay, early stopping | 2 | thin |
| Normalisation: batch norm, layer norm | 1 | **gap** |
| Vanishing/exploding gradients, initialisation | 6 |  |
| CNNs: convolution, pooling, padding/stride | 4 |  |
| RNN/LSTM/GRU | 7 |  |
| Attention & Transformers | 1 | **gap** |
| Transfer learning & fine-tuning | 1 | **gap** |
| Autoencoders / VAEs / GANs | 4 |  |
| Residual connections / modern architectures (ResNet, BERT, GPT) | 0 | **gap** |
| Training practicalities: batch size, learning-rate schedules, mixed precision, GPUs | 1 | **gap** |
| Overfitting diagnosis via learning curves | 1 | **gap** |
| Frameworks: PyTorch/TensorFlow autograd & training loop | 0 | **gap** |
| Embeddings | 0 | **gap** |
| Data augmentation | 1 | **gap** |
| Evaluation & deployment of DL models (quantisation, distillation) | 0 | **gap** |
| Diffusion / LLM fundamentals | 0 | **gap** |

**Missing or near-missing (14):** Backpropagation & chain rule; Loss functions; Optimisers (SGD, momentum, Adam); Normalisation: batch norm, layer norm; Attention & Transformers; Transfer learning & fine-tuning; Residual connections / modern architectures (ResNet, BERT, GPT); Training practicalities: batch size, learning-rate schedules, mixed precision, GPUs; Overfitting diagnosis via learning curves; Frameworks: PyTorch/TensorFlow autograd & training loop; Embeddings; Data augmentation; Evaluation & deployment of DL models (quantisation, distillation); Diffusion / LLM fundamentals.

**Suggested reference sources (licences unverified):** Dive into Deep Learning (d2l.ai); Deep Learning (Goodfellow, Bengio, Courville; free online); PyTorch tutorials and documentation; Stanford CS231n notes; Neural Networks and Deep Learning (Nielsen; free online).

## NLP  (27 KEEP/FIX seed questions)

| Concept | Hits | Gap? |
|---|---:|---|
| Text preprocessing: tokenisation, stop words, stemming/lemmatisation | 3 | thin |
| Representations: BoW, TF-IDF, n-grams | 3 | thin |
| Word embeddings: word2vec, GloVe, fastText | 0 | **gap** |
| Sequence tasks: POS tagging, NER, parsing | 4 |  |
| Language models & perplexity | 1 | **gap** |
| Transformers, BERT/GPT, attention | 0 | **gap** |
| Text classification & sentiment analysis | 1 | **gap** |
| Evaluation metrics: BLEU, ROUGE, F1 | 0 | **gap** |
| Machine translation / seq2seq | 0 | **gap** |
| Summarisation & question answering | 1 | **gap** |
| Topic modelling (LDA, LSI) | 1 | **gap** |
| Information retrieval & semantic search / vector search | 1 | **gap** |
| Fine-tuning, prompt engineering, LLM evaluation, hallucination | 0 | **gap** |
| Subword tokenisation (BPE, WordPiece) | 0 | **gap** |
| Handling OOV, multilingual & low-resource text | 0 | **gap** |
| RAG / retrieval-augmented generation | 0 | **gap** |
| Ambiguity, semantics and pragmatics | 5 |  |

**Missing or near-missing (13):** Word embeddings: word2vec, GloVe, fastText; Language models & perplexity; Transformers, BERT/GPT, attention; Text classification & sentiment analysis; Evaluation metrics: BLEU, ROUGE, F1; Machine translation / seq2seq; Summarisation & question answering; Topic modelling (LDA, LSI); Information retrieval & semantic search / vector search; Fine-tuning, prompt engineering, LLM evaluation, hallucination; Subword tokenisation (BPE, WordPiece); Handling OOV, multilingual & low-resource text; RAG / retrieval-augmented generation.

**Suggested reference sources (licences unverified):** Speech and Language Processing (Jurafsky & Martin; free draft online); Hugging Face NLP/LLM course; spaCy documentation; Stanford CS224n materials; Introduction to Information Retrieval (Manning et al.; free online).

## Python  (25 KEEP/FIX seed questions)

| Concept | Hits | Gap? |
|---|---:|---|
| Core data types & mutability (list/tuple/dict/set) | 3 | thin |
| Functions, closures, decorators, *args/**kwargs | 1 | **gap** |
| OOP: classes, inheritance, dunder methods | 2 | thin |
| Iterators & generators, comprehensions | 1 | **gap** |
| Exceptions & context managers | 1 | **gap** |
| Concurrency: GIL, threading, multiprocessing, asyncio | 1 | **gap** |
| Memory management, copy vs deepcopy, is vs == | 1 | **gap** |
| Algorithms & data structures coding (sorting, search, stack/queue, trees, graphs) | 7 |  |
| Complexity analysis | 2 | thin |
| NumPy / vectorisation / broadcasting | 1 | **gap** |
| pandas data manipulation (merge, groupby, missing values) | 1 | **gap** |
| Testing & debugging (unittest/pytest, mocking) | 2 | thin |
| Packaging, virtual environments, typing, PEP 8 | 0 | **gap** |
| File I/O, JSON, regex | 0 | **gap** |
| Performance profiling & optimisation | 0 | **gap** |
| Plotting (matplotlib/seaborn) | 1 | **gap** |

**Missing or near-missing (11):** Functions, closures, decorators, *args/**kwargs; Iterators & generators, comprehensions; Exceptions & context managers; Concurrency: GIL, threading, multiprocessing, asyncio; Memory management, copy vs deepcopy, is vs ==; NumPy / vectorisation / broadcasting; pandas data manipulation (merge, groupby, missing values); Packaging, virtual environments, typing, PEP 8; File I/O, JSON, regex; Performance profiling & optimisation; Plotting (matplotlib/seaborn).

**Suggested reference sources (licences unverified):** Official Python documentation and tutorial (docs.python.org); Python Data Science Handbook (VanderPlas; free online); PEP 8 and PEP 20; Real Python tutorials (check terms of use); NumPy and pandas user guides.

## SQL  (29 KEEP/FIX seed questions)

| Concept | Hits | Gap? |
|---|---:|---|
| SELECT/WHERE/GROUP BY/HAVING/ORDER BY semantics | 2 | thin |
| Joins: inner/left/right/full/cross/self, anti-join | 3 | thin |
| Subqueries, CTEs, recursive CTEs | 2 | thin |
| Window functions: ROW_NUMBER/RANK/LAG/LEAD/running totals | 2 | thin |
| NULL handling and three-valued logic | 1 | **gap** |
| Set operations: UNION/INTERSECT/EXCEPT | 0 | **gap** |
| Indexes, clustered vs non-clustered, query plans | 4 |  |
| Normalisation / schema design / keys | 4 |  |
| Transactions, ACID, isolation levels, deadlocks | 3 | thin |
| Aggregation patterns: top-N per group, duplicates, gaps/islands, de-duplication | 1 | **gap** |
| Date/time and string functions | 0 | **gap** |
| CASE expressions, conditional aggregation, pivoting | 0 | **gap** |
| Views, stored procedures, triggers | 2 | thin |
| Partitioning / sharding / scaling | 2 | thin |
| Hands-on query-writing exercises with schemas and expected output | 0 | **gap** |

**Missing or near-missing (6):** NULL handling and three-valued logic; Set operations: UNION/INTERSECT/EXCEPT; Aggregation patterns: top-N per group, duplicates, gaps/islands, de-duplication; Date/time and string functions; CASE expressions, conditional aggregation, pivoting; Hands-on query-writing exercises with schemas and expected output.

**Suggested reference sources (licences unverified):** PostgreSQL documentation; SQLite documentation (runnable window-function examples); Use The Index, Luke (use-the-index-luke.com); Mode SQL tutorial (check terms of use); SQLBolt interactive lessons (check terms of use).

## Data Analysis  (30 KEEP/FIX seed questions)

| Concept | Hits | Gap? |
|---|---:|---|
| Descriptive statistics & distributions | 0 | **gap** |
| Data cleaning and missing values | 1 | **gap** |
| Outlier detection | 0 | **gap** |
| EDA and visualisation choices | 1 | **gap** |
| Hypothesis testing, p-values, confidence intervals | 0 | **gap** |
| A/B testing & experiment design (power, sample size, pitfalls) | 0 | **gap** |
| Correlation vs causation, confounding | 0 | **gap** |
| Product / business metrics & root-cause analysis | 9 |  |
| Cohort, funnel and retention analysis | 0 | **gap** |
| Sampling & bias | 0 | **gap** |
| Excel / BI tools (pivot tables, dashboards) | 0 | **gap** |
| pandas/SQL analysis exercises with data | 0 | **gap** |
| Regression for analysis & interpretation | 3 | thin |
| Time-series & trend/seasonality analysis | 0 | **gap** |
| Data storytelling and communicating findings | 2 | thin |

**Missing or near-missing (12):** Descriptive statistics & distributions; Data cleaning and missing values; Outlier detection; EDA and visualisation choices; Hypothesis testing, p-values, confidence intervals; A/B testing & experiment design (power, sample size, pitfalls); Correlation vs causation, confounding; Cohort, funnel and retention analysis; Sampling & bias; Excel / BI tools (pivot tables, dashboards); pandas/SQL analysis exercises with data; Time-series & trend/seasonality analysis.

**Suggested reference sources (licences unverified):** pandas user guide; Think Stats (Allen Downey; free online); OpenIntro Statistics (free PDF); Trustworthy Online Controlled Experiments (Kohavi et al.; book); Practical Statistics for Data Scientists (Bruce et al.; book).

## Cross-cutting observations

* Statistics (hypothesis testing, confidence intervals, CLT, Bayes) is represented only inside ML; the Data Analysis domain has almost no seed content of its own once the product-metric cases are counted. Decide where statistics should live before curating.
* The seed set has no hands-on exercises with a schema/dataset and expected output (SQL queries, pandas transforms), which is what a code-aware interviewer or RAG grounding needs.
* Modern topics (transformers, embeddings, BERT/GPT, fine-tuning, RAG, LLM evaluation) are largely absent from the seed set; the audit found the same in the generated set.
* Per the constraints, this document identifies gaps only; it does not propose question text.