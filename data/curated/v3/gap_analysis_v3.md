# Domain gap analysis - v3 (after pilot 01 merge and batch 02)

Method (unchanged from Stages 1A/1B so counts are comparable): each domain has a checklist of core interview concepts, matched by keyword regex against the **question text**. A second column also matches the `key_concepts` field. A hit count is only a coverage indicator: a hit does not mean the answer is good, and 0 does not prove absence. 0-1 hits = gap, 2-3 = thin. Counts are per domain (the domain label each record carries). The checklist comes from standard curricula, not from this dataset; reference sources are suggestions only and their licences are unverified. Columns: 'v1' = 316 questions (Stage 1A); 'v2 core' = 360 (Stage 1B core); 'v3 core' = 401 (v2 core + the 41 audited pilot-01 questions); '+batch 02' = v3 core plus the 46 batch-02 questions, which are NOT merged and await approval.

## Machine Learning  (v1 151 / v2 core 164 / v3 core 164 / +batch 02 164 questions)

| Concept | v1 | v2 core | v3 core | +batch 02 | +batch 02 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---|---|
| Linear/logistic regression assumptions & interpretation | 10 | 11 | 11 | 11 | 17 |  |  |
| Regularisation (L1/L2, elastic net) | 4 | 4 | 4 | 4 | 15 |  |  |
| Bias-variance, over/underfitting | 6 | 6 | 6 | 6 | 31 |  |  |
| Model evaluation: precision/recall/F1/ROC/PR | 7 | 7 | 7 | 7 | 17 |  |  |
| Cross-validation & data leakage | 5 | 5 | 5 | 5 | 23 |  |  |
| Tree ensembles: RF, gradient boosting, XGBoost | 12 | 14 | 14 | 14 | 25 |  |  |
| SVM & kernels | 10 | 12 | 12 | 12 | 14 |  |  |
| Clustering & choosing k | 6 | 6 | 6 | 6 | 8 |  |  |
| Dimensionality reduction (PCA, t-SNE) | 7 | 8 | 8 | 8 | 15 |  |  |
| Feature engineering/encoding/scaling | 5 | 5 | 5 | 5 | 19 |  |  |
| Class imbalance | 2 | 2 | 2 | 2 | 8 | thin |  |
| Missing data & outliers | 1 | 1 | 1 | 1 | 4 | **gap** |  |
| Probability/statistics: Bayes, CLT, hypothesis tests, CI | 8 | 9 | 9 | 9 | 14 |  |  |
| Optimisation: gradient descent variants, learning rate | 2 | 2 | 2 | 2 | 6 | thin |  |
| Recommender systems | 7 | 9 | 9 | 9 | 11 |  |  |
| Time-series forecasting (ARIMA, stationarity, seasonality) | 1 | 1 | 1 | 1 | 2 | **gap** | thin |
| Hyperparameter tuning (grid/random/Bayesian) | 2 | 2 | 2 | 2 | 5 | thin |  |
| Model interpretability (SHAP/LIME, feature importance) | 0 | 0 | 0 | 0 | 4 | **gap** |  |
| Anomaly detection | 0 | 0 | 0 | 0 | 2 | **gap** | thin |
| ML system design / deployment / monitoring / drift | 1 | 1 | 1 | 1 | 4 | **gap** |  |
| Reinforcement learning basics | 0 | 1 | 1 | 1 | 3 | **gap** | thin |
| Semi/self-supervised learning | 1 | 1 | 1 | 1 | 4 | **gap** |  |
| Calibration & probabilistic outputs | 0 | 0 | 0 | 0 | 6 | **gap** |  |
| Naive Bayes / KNN / decision-tree fundamentals | 13 | 15 | 15 | 15 | 22 |  |  |

**Still a gap after batch 02 (question-text match, 8):** Missing data & outliers; Time-series forecasting (ARIMA, stationarity, seasonality); Model interpretability (SHAP/LIME, feature importance); Anomaly detection; ML system design / deployment / monitoring / drift; Reinforcement learning basics; Semi/self-supervised learning; Calibration & probabilistic outputs

**Thin (2-3 questions, 3):** Class imbalance; Optimisation: gradient descent variants, learning rate; Hyperparameter tuning (grid/random/Bayesian)

**Reference sources (licences unverified):** scikit-learn User Guide (scikit-learn.org); An Introduction to Statistical Learning (James et al.; free PDF from authors); The Elements of Statistical Learning (Hastie et al.; free PDF from authors); Google Machine Learning Crash Course; Stanford CS229 lecture notes

## Deep Learning  (v1 56 / v2 core 64 / v3 core 76 / +batch 02 86 questions)

| Concept | v1 | v2 core | v3 core | +batch 02 | +batch 02 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---|---|
| Backpropagation & chain rule | 1 | 1 | 1 | 1 | 9 | **gap** |  |
| Activation functions | 8 | 10 | 14 | 17 | 22 |  |  |
| Loss functions | 1 | 1 | 5 | 9 | 16 |  |  |
| Optimisers (SGD, momentum, Adam) | 1 | 1 | 2 | 3 | 7 | thin |  |
| Regularisation: dropout, weight decay, early stopping | 2 | 2 | 3 | 3 | 9 | thin |  |
| Normalisation: batch norm, layer norm | 1 | 1 | 2 | 3 | 6 | thin |  |
| Vanishing/exploding gradients, initialisation | 5 | 6 | 7 | 8 | 14 |  |  |
| CNNs: convolution, pooling, padding/stride | 3 | 4 | 8 | 10 | 11 |  |  |
| RNN/LSTM/GRU | 7 | 7 | 7 | 8 | 9 |  |  |
| Attention & Transformers | 1 | 1 | 2 | 4 | 7 |  |  |
| Transfer learning & fine-tuning | 1 | 1 | 2 | 2 | 3 | thin | thin |
| Autoencoders / VAEs / GANs | 3 | 4 | 4 | 4 | 4 |  |  |
| Residual connections / modern architectures (ResNet, BERT, GPT) | 0 | 0 | 1 | 3 | 4 | thin |  |
| Training practicalities: batch size, learning-rate schedules, mixed precision, GPUs | 1 | 1 | 3 | 6 | 11 |  |  |
| Overfitting diagnosis via learning curves | 1 | 1 | 2 | 2 | 2 | thin | thin |
| Frameworks: PyTorch/TensorFlow autograd & training loop | 0 | 0 | 0 | 0 | 1 | **gap** | **gap** |
| Embeddings | 0 | 0 | 1 | 3 | 4 | thin |  |
| Data augmentation | 1 | 1 | 2 | 2 | 3 | thin | thin |
| Evaluation & deployment of DL models (quantisation, distillation) | 0 | 0 | 2 | 2 | 3 | thin | thin |
| Diffusion / LLM fundamentals | 0 | 0 | 0 | 1 | 1 | **gap** | **gap** |

**Still a gap after batch 02 (question-text match, 3):** Backpropagation & chain rule; Frameworks: PyTorch/TensorFlow autograd & training loop; Diffusion / LLM fundamentals

**Thin (2-3 questions, 9):** Optimisers (SGD, momentum, Adam); Regularisation: dropout, weight decay, early stopping; Normalisation: batch norm, layer norm; Transfer learning & fine-tuning; Residual connections / modern architectures (ResNet, BERT, GPT); Overfitting diagnosis via learning curves; Embeddings; Data augmentation; Evaluation & deployment of DL models (quantisation, distillation)

**Reference sources (licences unverified):** Dive into Deep Learning (d2l.ai); Deep Learning (Goodfellow, Bengio, Courville; free online); PyTorch tutorials and documentation; Stanford CS231n notes; Neural Networks and Deep Learning (Nielsen; free online)

## NLP  (v1 19 / v2 core 27 / v3 core 41 / +batch 02 53 questions)

| Concept | v1 | v2 core | v3 core | +batch 02 | +batch 02 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---|---|
| Text preprocessing: tokenisation, stop words, stemming/lemmatisation | 1 | 3 | 7 | 15 | 21 |  |  |
| Representations: BoW, TF-IDF, n-grams | 3 | 3 | 6 | 9 | 13 |  |  |
| Word embeddings: word2vec, GloVe, fastText | 0 | 0 | 1 | 3 | 6 | thin |  |
| Sequence tasks: POS tagging, NER, parsing | 4 | 4 | 5 | 5 | 11 |  |  |
| Language models & perplexity | 1 | 1 | 2 | 3 | 6 | thin |  |
| Transformers, BERT/GPT, attention | 0 | 0 | 2 | 4 | 6 |  |  |
| Text classification & sentiment analysis | 1 | 1 | 2 | 2 | 6 | thin |  |
| Evaluation metrics: BLEU, ROUGE, F1 | 0 | 0 | 3 | 7 | 11 |  |  |
| Machine translation / seq2seq | 0 | 0 | 0 | 1 | 1 | **gap** | **gap** |
| Summarisation & question answering | 1 | 1 | 1 | 2 | 2 | thin | thin |
| Topic modelling (LDA, LSI) | 1 | 1 | 2 | 2 | 2 | thin | thin |
| Information retrieval & semantic search / vector search | 0 | 1 | 7 | 12 | 14 |  |  |
| Fine-tuning, prompt engineering, LLM evaluation, hallucination | 0 | 0 | 1 | 6 | 8 |  |  |
| Subword tokenisation (BPE, WordPiece) | 0 | 0 | 2 | 3 | 3 | thin | thin |
| Handling OOV, multilingual & low-resource text | 0 | 0 | 0 | 1 | 3 | **gap** | thin |
| RAG / retrieval-augmented generation | 0 | 0 | 1 | 2 | 2 | thin | thin |
| Ambiguity, semantics and pragmatics | 3 | 5 | 6 | 6 | 7 |  |  |

**Still a gap after batch 02 (question-text match, 2):** Machine translation / seq2seq; Handling OOV, multilingual & low-resource text

**Thin (2-3 questions, 7):** Word embeddings: word2vec, GloVe, fastText; Language models & perplexity; Text classification & sentiment analysis; Summarisation & question answering; Topic modelling (LDA, LSI); Subword tokenisation (BPE, WordPiece); RAG / retrieval-augmented generation

**Reference sources (licences unverified):** Speech and Language Processing (Jurafsky & Martin; free draft online); Hugging Face NLP/LLM course; spaCy documentation; Stanford CS224n materials; Introduction to Information Retrieval (Manning et al.; free online)

## Python  (v1 22 / v2 core 23 / v3 core 23 / +batch 02 35 questions)

| Concept | v1 | v2 core | v3 core | +batch 02 | +batch 02 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---|---|
| Core data types & mutability (list/tuple/dict/set) | 3 | 3 | 3 | 10 | 12 |  |  |
| Functions, closures, decorators, *args/**kwargs | 1 | 1 | 1 | 3 | 3 | thin | thin |
| OOP: classes, inheritance, dunder methods | 2 | 2 | 2 | 7 | 10 |  |  |
| Iterators & generators, comprehensions | 1 | 1 | 1 | 3 | 4 | thin |  |
| Exceptions & context managers | 1 | 1 | 1 | 4 | 4 |  |  |
| Concurrency: GIL, threading, multiprocessing, asyncio | 1 | 1 | 1 | 2 | 3 | thin | thin |
| Memory management, copy vs deepcopy, is vs == | 1 | 1 | 1 | 4 | 4 |  |  |
| Algorithms & data structures coding (sorting, search, stack/queue, trees, graphs) | 7 | 7 | 7 | 9 | 10 |  |  |
| Complexity analysis | 2 | 2 | 2 | 3 | 3 | thin | thin |
| NumPy / vectorisation / broadcasting | 1 | 1 | 1 | 2 | 2 | thin | thin |
| pandas data manipulation (merge, groupby, missing values) | 1 | 1 | 1 | 3 | 3 | thin | thin |
| Testing & debugging (unittest/pytest, mocking) | 1 | 2 | 2 | 3 | 3 | thin | thin |
| Packaging, virtual environments, typing, PEP 8 | 0 | 0 | 0 | 0 | 0 | **gap** | **gap** |
| File I/O, JSON, regex | 0 | 0 | 0 | 1 | 1 | **gap** | **gap** |
| Performance profiling & optimisation | 0 | 0 | 0 | 0 | 0 | **gap** | **gap** |
| Plotting (matplotlib/seaborn) | 1 | 1 | 1 | 1 | 1 | **gap** | **gap** |

**Still a gap after batch 02 (question-text match, 4):** Packaging, virtual environments, typing, PEP 8; File I/O, JSON, regex; Performance profiling & optimisation; Plotting (matplotlib/seaborn)

**Thin (2-3 questions, 7):** Functions, closures, decorators, *args/**kwargs; Iterators & generators, comprehensions; Concurrency: GIL, threading, multiprocessing, asyncio; Complexity analysis; NumPy / vectorisation / broadcasting; pandas data manipulation (merge, groupby, missing values); Testing & debugging (unittest/pytest, mocking)

**Reference sources (licences unverified):** Official Python documentation and tutorial (docs.python.org); Python Data Science Handbook (VanderPlas; free online); PEP 8 and PEP 20; Real Python tutorials (check terms of use); NumPy and pandas user guides

## SQL  (v1 29 / v2 core 29 / v3 core 44 / +batch 02 44 questions)

| Concept | v1 | v2 core | v3 core | +batch 02 | +batch 02 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---|---|
| SELECT/WHERE/GROUP BY/HAVING/ORDER BY semantics | 2 | 2 | 14 | 14 | 18 |  |  |
| Joins: inner/left/right/full/cross/self, anti-join | 3 | 3 | 6 | 6 | 10 |  |  |
| Subqueries, CTEs, recursive CTEs | 2 | 2 | 3 | 3 | 9 | thin |  |
| Window functions: ROW_NUMBER/RANK/LAG/LEAD/running totals | 2 | 2 | 4 | 4 | 7 |  |  |
| NULL handling and three-valued logic | 1 | 1 | 9 | 9 | 19 |  |  |
| Set operations: UNION/INTERSECT/EXCEPT | 0 | 0 | 1 | 1 | 2 | **gap** | thin |
| Indexes, clustered vs non-clustered, query plans | 4 | 4 | 6 | 6 | 9 |  |  |
| Normalisation / schema design / keys | 4 | 4 | 14 | 14 | 15 |  |  |
| Transactions, ACID, isolation levels, deadlocks | 3 | 3 | 3 | 3 | 3 | thin | thin |
| Aggregation patterns: top-N per group, duplicates, gaps/islands, de-duplication | 1 | 1 | 7 | 7 | 11 |  |  |
| Date/time and string functions | 0 | 0 | 6 | 6 | 8 |  |  |
| CASE expressions, conditional aggregation, pivoting | 0 | 0 | 1 | 1 | 1 | **gap** | **gap** |
| Views, stored procedures, triggers | 2 | 2 | 2 | 2 | 4 | thin |  |
| Partitioning / sharding / scaling | 2 | 2 | 2 | 2 | 8 | thin |  |
| Hands-on query-writing exercises with schemas and expected output | 0 | 0 | 6 | 6 | 6 |  |  |

**Still a gap after batch 02 (question-text match, 2):** Set operations: UNION/INTERSECT/EXCEPT; CASE expressions, conditional aggregation, pivoting

**Thin (2-3 questions, 4):** Subqueries, CTEs, recursive CTEs; Transactions, ACID, isolation levels, deadlocks; Views, stored procedures, triggers; Partitioning / sharding / scaling

**Reference sources (licences unverified):** PostgreSQL documentation; SQLite documentation (runnable window-function examples); Use The Index, Luke (use-the-index-luke.com); Mode SQL tutorial (check terms of use); SQLBolt interactive lessons (check terms of use)

## Data Analysis  (v1 39 / v2 core 53 / v3 core 53 / +batch 02 65 questions)

| Concept | v1 | v2 core | v3 core | +batch 02 | +batch 02 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---|---|
| Descriptive statistics & distributions | 3 | 5 | 5 | 8 | 15 |  |  |
| Data cleaning and missing values | 2 | 3 | 3 | 3 | 7 | thin |  |
| Outlier detection | 1 | 1 | 1 | 2 | 4 | thin |  |
| EDA and visualisation choices | 1 | 1 | 1 | 1 | 3 | **gap** | thin |
| Hypothesis testing, p-values, confidence intervals | 6 | 6 | 6 | 9 | 12 |  |  |
| A/B testing & experiment design (power, sample size, pitfalls) | 1 | 1 | 1 | 7 | 16 |  |  |
| Correlation vs causation, confounding | 3 | 3 | 3 | 4 | 7 |  |  |
| Product / business metrics & root-cause analysis | 2 | 10 | 10 | 17 | 19 |  |  |
| Cohort, funnel and retention analysis | 0 | 0 | 0 | 1 | 10 | **gap** |  |
| Sampling & bias | 0 | 0 | 0 | 1 | 4 | **gap** |  |
| Excel / BI tools (pivot tables, dashboards) | 0 | 0 | 0 | 2 | 2 | thin | thin |
| pandas/SQL analysis exercises with data | 0 | 0 | 0 | 4 | 5 |  |  |
| Regression for analysis & interpretation | 3 | 3 | 3 | 3 | 3 | thin | thin |
| Time-series & trend/seasonality analysis | 1 | 1 | 1 | 2 | 4 | thin |  |
| Data storytelling and communicating findings | 2 | 2 | 2 | 2 | 2 | thin | thin |

**Still a gap after batch 02 (question-text match, 3):** EDA and visualisation choices; Cohort, funnel and retention analysis; Sampling & bias

**Thin (2-3 questions, 6):** Data cleaning and missing values; Outlier detection; Excel / BI tools (pivot tables, dashboards); Regression for analysis & interpretation; Time-series & trend/seasonality analysis; Data storytelling and communicating findings

**Reference sources (licences unverified):** pandas user guide; Think Stats (Allen Downey; free online); OpenIntro Statistics (free PDF); Trustworthy Online Controlled Experiments (Kohavi et al.; book); Practical Statistics for Data Scientists (Bruce et al.; book)

## Summary

| Domain | Q v1 | Q v2 core | Q v3 core | Q +batch 02 | Concepts checked | Gaps v1 | Gaps v2 core | Gaps v3 core | Gaps +batch 02 | Gaps +batch 02 (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Machine Learning | 151 | 164 | 164 | 164 | 24 | 8 | 8 | 8 | 8 | 8 |
| Deep Learning | 56 | 64 | 76 | 86 | 20 | 14 | 14 | 5 | 3 | 3 |
| NLP | 19 | 27 | 41 | 53 | 17 | 14 | 13 | 6 | 2 | 2 |
| Python | 22 | 23 | 23 | 35 | 16 | 12 | 11 | 11 | 4 | 4 |
| SQL | 29 | 29 | 44 | 44 | 15 | 6 | 6 | 2 | 2 | 2 |
| Data Analysis | 39 | 53 | 53 | 65 | 15 | 8 | 8 | 8 | 3 | 3 |

Notes

* The key_concepts-inclusive column is optimistic (a key concept shares keywords with many checklist items); treat the question-text column as the conservative measure.
* Keyword matching on question text undercounts breadth: one scenario question (e.g. a production-debugging case) exercises several checklist concepts its wording does not name.
* A concept can show as covered while represented only by older one-line definitions; Stage 1B rewrote the 121 shortest/most imprecise answers, not every concept's depth.
* Statistics / A-B testing live under Data Analysis; MLE, likelihood, Bayes, bias-variance remain under Machine Learning.
* This document identifies gaps and next-batch targets only; it contains no new question text.
