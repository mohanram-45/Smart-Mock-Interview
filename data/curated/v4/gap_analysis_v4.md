# Domain gap analysis - v4 (v4 core, plus batch 03 shown separately)

Method (unchanged from Stages 1A/1B so counts are comparable): each domain has a checklist of core interview concepts, matched by keyword regex against the **question text**. A second column also matches the `key_concepts` field. A hit count is only a coverage indicator: a hit does not mean the answer is good, and 0 does not prove absence. 0-1 hits = gap, 2-3 = thin. Counts are per domain (the domain label each record carries). The checklist comes from standard curricula, not from this dataset; reference sources are suggestions only and their licences are unverified. Columns: 'v1' = 316 questions (Stage 1A); 'v2 core' = 360 (Stage 1B core); 'v4 core' = 447 (v2 core + audited pilot 01 + re-verified batch 02); '+batch 03' = v4 core plus the 40 batch-03 questions, which are NOT merged and await review.

## Machine Learning  (v1 151 / v2 core 164 / v4 core 164 / +batch 03 174 questions)

| Concept | v1 | v2 core | v4 core | +batch 03 | +batch 03 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---|---|
| Linear/logistic regression assumptions & interpretation | 10 | 11 | 11 | 11 | 17 |  |  |
| Regularisation (L1/L2, elastic net) | 4 | 4 | 4 | 4 | 15 |  |  |
| Bias-variance, over/underfitting | 6 | 6 | 6 | 6 | 34 |  |  |
| Model evaluation: precision/recall/F1/ROC/PR | 7 | 7 | 7 | 14 | 24 |  |  |
| Cross-validation & data leakage | 5 | 5 | 5 | 8 | 26 |  |  |
| Tree ensembles: RF, gradient boosting, XGBoost | 12 | 14 | 14 | 15 | 26 |  |  |
| SVM & kernels | 10 | 12 | 12 | 12 | 14 |  |  |
| Clustering & choosing k | 6 | 6 | 6 | 6 | 8 |  |  |
| Dimensionality reduction (PCA, t-SNE) | 7 | 8 | 8 | 8 | 15 |  |  |
| Feature engineering/encoding/scaling | 5 | 5 | 5 | 7 | 22 |  |  |
| Class imbalance | 2 | 2 | 2 | 3 | 11 | thin |  |
| Missing data & outliers | 1 | 1 | 1 | 1 | 5 | **gap** |  |
| Probability/statistics: Bayes, CLT, hypothesis tests, CI | 8 | 9 | 9 | 9 | 14 |  |  |
| Optimisation: gradient descent variants, learning rate | 2 | 2 | 2 | 2 | 7 | thin |  |
| Recommender systems | 7 | 9 | 9 | 9 | 11 |  |  |
| Time-series forecasting (ARIMA, stationarity, seasonality) | 1 | 1 | 1 | 1 | 2 | **gap** | thin |
| Hyperparameter tuning (grid/random/Bayesian) | 2 | 2 | 2 | 2 | 5 | thin |  |
| Model interpretability (SHAP/LIME, feature importance) | 0 | 0 | 0 | 0 | 4 | **gap** |  |
| Anomaly detection | 0 | 0 | 0 | 0 | 2 | **gap** | thin |
| ML system design / deployment / monitoring / drift | 1 | 1 | 1 | 3 | 7 | thin |  |
| Reinforcement learning basics | 0 | 1 | 1 | 1 | 3 | **gap** | thin |
| Semi/self-supervised learning | 1 | 1 | 1 | 1 | 4 | **gap** |  |
| Calibration & probabilistic outputs | 0 | 0 | 0 | 2 | 9 | thin |  |
| Naive Bayes / KNN / decision-tree fundamentals | 13 | 15 | 15 | 15 | 22 |  |  |

**Still a gap after batch 03 (question-text match, 6):** Missing data & outliers; Time-series forecasting (ARIMA, stationarity, seasonality); Model interpretability (SHAP/LIME, feature importance); Anomaly detection; Reinforcement learning basics; Semi/self-supervised learning

**Thin (2-3 questions, 5):** Class imbalance; Optimisation: gradient descent variants, learning rate; Hyperparameter tuning (grid/random/Bayesian); ML system design / deployment / monitoring / drift; Calibration & probabilistic outputs

**Reference sources (licences unverified):** scikit-learn User Guide (scikit-learn.org); An Introduction to Statistical Learning (James et al.; free PDF from authors); The Elements of Statistical Learning (Hastie et al.; free PDF from authors); Google Machine Learning Crash Course; Stanford CS229 lecture notes

## Deep Learning  (v1 56 / v2 core 64 / v4 core 86 / +batch 03 86 questions)

| Concept | v1 | v2 core | v4 core | +batch 03 | +batch 03 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---|---|
| Backpropagation & chain rule | 1 | 1 | 1 | 1 | 9 | **gap** |  |
| Activation functions | 8 | 10 | 17 | 17 | 22 |  |  |
| Loss functions | 1 | 1 | 9 | 9 | 16 |  |  |
| Optimisers (SGD, momentum, Adam) | 1 | 1 | 3 | 3 | 7 | thin |  |
| Regularisation: dropout, weight decay, early stopping | 2 | 2 | 3 | 3 | 9 | thin |  |
| Normalisation: batch norm, layer norm | 1 | 1 | 3 | 3 | 6 | thin |  |
| Vanishing/exploding gradients, initialisation | 5 | 6 | 8 | 8 | 14 |  |  |
| CNNs: convolution, pooling, padding/stride | 3 | 4 | 10 | 10 | 11 |  |  |
| RNN/LSTM/GRU | 7 | 7 | 8 | 8 | 9 |  |  |
| Attention & Transformers | 1 | 1 | 4 | 4 | 7 |  |  |
| Transfer learning & fine-tuning | 1 | 1 | 2 | 2 | 3 | thin | thin |
| Autoencoders / VAEs / GANs | 3 | 4 | 4 | 4 | 4 |  |  |
| Residual connections / modern architectures (ResNet, BERT, GPT) | 0 | 0 | 3 | 3 | 4 | thin |  |
| Training practicalities: batch size, learning-rate schedules, mixed precision, GPUs | 1 | 1 | 6 | 6 | 11 |  |  |
| Overfitting diagnosis via learning curves | 1 | 1 | 2 | 2 | 2 | thin | thin |
| Frameworks: PyTorch/TensorFlow autograd & training loop | 0 | 0 | 0 | 0 | 1 | **gap** | **gap** |
| Embeddings | 0 | 0 | 3 | 3 | 4 | thin |  |
| Data augmentation | 1 | 1 | 2 | 2 | 3 | thin | thin |
| Evaluation & deployment of DL models (quantisation, distillation) | 0 | 0 | 2 | 2 | 3 | thin | thin |
| Diffusion / LLM fundamentals | 0 | 0 | 1 | 1 | 1 | **gap** | **gap** |

**Still a gap after batch 03 (question-text match, 3):** Backpropagation & chain rule; Frameworks: PyTorch/TensorFlow autograd & training loop; Diffusion / LLM fundamentals

**Thin (2-3 questions, 9):** Optimisers (SGD, momentum, Adam); Regularisation: dropout, weight decay, early stopping; Normalisation: batch norm, layer norm; Transfer learning & fine-tuning; Residual connections / modern architectures (ResNet, BERT, GPT); Overfitting diagnosis via learning curves; Embeddings; Data augmentation; Evaluation & deployment of DL models (quantisation, distillation)

**Reference sources (licences unverified):** Dive into Deep Learning (d2l.ai); Deep Learning (Goodfellow, Bengio, Courville; free online); PyTorch tutorials and documentation; Stanford CS231n notes; Neural Networks and Deep Learning (Nielsen; free online)

## NLP  (v1 19 / v2 core 27 / v4 core 53 / +batch 03 53 questions)

| Concept | v1 | v2 core | v4 core | +batch 03 | +batch 03 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---|---|
| Text preprocessing: tokenisation, stop words, stemming/lemmatisation | 1 | 3 | 15 | 15 | 21 |  |  |
| Representations: BoW, TF-IDF, n-grams | 3 | 3 | 9 | 9 | 13 |  |  |
| Word embeddings: word2vec, GloVe, fastText | 0 | 0 | 3 | 3 | 6 | thin |  |
| Sequence tasks: POS tagging, NER, parsing | 4 | 4 | 5 | 5 | 11 |  |  |
| Language models & perplexity | 1 | 1 | 3 | 3 | 6 | thin |  |
| Transformers, BERT/GPT, attention | 0 | 0 | 4 | 4 | 6 |  |  |
| Text classification & sentiment analysis | 1 | 1 | 2 | 2 | 6 | thin |  |
| Evaluation metrics: BLEU, ROUGE, F1 | 0 | 0 | 7 | 7 | 11 |  |  |
| Machine translation / seq2seq | 0 | 0 | 1 | 1 | 1 | **gap** | **gap** |
| Summarisation & question answering | 1 | 1 | 2 | 2 | 2 | thin | thin |
| Topic modelling (LDA, LSI) | 1 | 1 | 2 | 2 | 2 | thin | thin |
| Information retrieval & semantic search / vector search | 0 | 1 | 12 | 12 | 14 |  |  |
| Fine-tuning, prompt engineering, LLM evaluation, hallucination | 0 | 0 | 6 | 6 | 8 |  |  |
| Subword tokenisation (BPE, WordPiece) | 0 | 0 | 3 | 3 | 3 | thin | thin |
| Handling OOV, multilingual & low-resource text | 0 | 0 | 1 | 1 | 3 | **gap** | thin |
| RAG / retrieval-augmented generation | 0 | 0 | 2 | 2 | 2 | thin | thin |
| Ambiguity, semantics and pragmatics | 3 | 5 | 6 | 6 | 7 |  |  |

**Still a gap after batch 03 (question-text match, 2):** Machine translation / seq2seq; Handling OOV, multilingual & low-resource text

**Thin (2-3 questions, 7):** Word embeddings: word2vec, GloVe, fastText; Language models & perplexity; Text classification & sentiment analysis; Summarisation & question answering; Topic modelling (LDA, LSI); Subword tokenisation (BPE, WordPiece); RAG / retrieval-augmented generation

**Reference sources (licences unverified):** Speech and Language Processing (Jurafsky & Martin; free draft online); Hugging Face NLP/LLM course; spaCy documentation; Stanford CS224n materials; Introduction to Information Retrieval (Manning et al.; free online)

## Python  (v1 22 / v2 core 23 / v4 core 35 / +batch 03 45 questions)

| Concept | v1 | v2 core | v4 core | +batch 03 | +batch 03 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---|---|
| Core data types & mutability (list/tuple/dict/set) | 3 | 3 | 10 | 12 | 15 |  |  |
| Functions, closures, decorators, *args/**kwargs | 1 | 1 | 3 | 3 | 3 | thin | thin |
| OOP: classes, inheritance, dunder methods | 2 | 2 | 7 | 11 | 14 |  |  |
| Iterators & generators, comprehensions | 1 | 1 | 3 | 3 | 4 | thin |  |
| Exceptions & context managers | 1 | 1 | 4 | 5 | 7 |  |  |
| Concurrency: GIL, threading, multiprocessing, asyncio | 1 | 1 | 2 | 2 | 3 | thin | thin |
| Memory management, copy vs deepcopy, is vs == | 1 | 1 | 4 | 5 | 6 |  |  |
| Algorithms & data structures coding (sorting, search, stack/queue, trees, graphs) | 7 | 7 | 9 | 9 | 10 |  |  |
| Complexity analysis | 2 | 2 | 3 | 3 | 3 | thin | thin |
| NumPy / vectorisation / broadcasting | 1 | 1 | 2 | 2 | 2 | thin | thin |
| pandas data manipulation (merge, groupby, missing values) | 1 | 1 | 3 | 3 | 3 | thin | thin |
| Testing & debugging (unittest/pytest, mocking) | 1 | 2 | 3 | 3 | 3 | thin | thin |
| Packaging, virtual environments, typing, PEP 8 | 0 | 0 | 0 | 2 | 2 | thin | thin |
| File I/O, JSON, regex | 0 | 0 | 1 | 5 | 6 |  |  |
| Performance profiling & optimisation | 0 | 0 | 0 | 0 | 0 | **gap** | **gap** |
| Plotting (matplotlib/seaborn) | 1 | 1 | 1 | 1 | 1 | **gap** | **gap** |

**Still a gap after batch 03 (question-text match, 2):** Performance profiling & optimisation; Plotting (matplotlib/seaborn)

**Thin (2-3 questions, 8):** Functions, closures, decorators, *args/**kwargs; Iterators & generators, comprehensions; Concurrency: GIL, threading, multiprocessing, asyncio; Complexity analysis; NumPy / vectorisation / broadcasting; pandas data manipulation (merge, groupby, missing values); Testing & debugging (unittest/pytest, mocking); Packaging, virtual environments, typing, PEP 8

**Reference sources (licences unverified):** Official Python documentation and tutorial (docs.python.org); Python Data Science Handbook (VanderPlas; free online); PEP 8 and PEP 20; Real Python tutorials (check terms of use); NumPy and pandas user guides

## SQL  (v1 29 / v2 core 29 / v4 core 44 / +batch 03 54 questions)

| Concept | v1 | v2 core | v4 core | +batch 03 | +batch 03 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---|---|
| SELECT/WHERE/GROUP BY/HAVING/ORDER BY semantics | 2 | 2 | 14 | 18 | 22 |  |  |
| Joins: inner/left/right/full/cross/self, anti-join | 3 | 3 | 6 | 8 | 13 |  |  |
| Subqueries, CTEs, recursive CTEs | 2 | 2 | 3 | 4 | 11 |  |  |
| Window functions: ROW_NUMBER/RANK/LAG/LEAD/running totals | 2 | 2 | 4 | 7 | 12 |  |  |
| NULL handling and three-valued logic | 1 | 1 | 9 | 18 | 28 |  |  |
| Set operations: UNION/INTERSECT/EXCEPT | 0 | 0 | 1 | 5 | 6 |  |  |
| Indexes, clustered vs non-clustered, query plans | 4 | 4 | 6 | 6 | 9 |  |  |
| Normalisation / schema design / keys | 4 | 4 | 14 | 18 | 19 |  |  |
| Transactions, ACID, isolation levels, deadlocks | 3 | 3 | 3 | 3 | 3 | thin | thin |
| Aggregation patterns: top-N per group, duplicates, gaps/islands, de-duplication | 1 | 1 | 7 | 8 | 15 |  |  |
| Date/time and string functions | 0 | 0 | 6 | 9 | 11 |  |  |
| CASE expressions, conditional aggregation, pivoting | 0 | 0 | 1 | 1 | 2 | **gap** | thin |
| Views, stored procedures, triggers | 2 | 2 | 2 | 3 | 5 | thin |  |
| Partitioning / sharding / scaling | 2 | 2 | 2 | 2 | 9 | thin |  |
| Hands-on query-writing exercises with schemas and expected output | 0 | 0 | 6 | 6 | 6 |  |  |

**Still a gap after batch 03 (question-text match, 1):** CASE expressions, conditional aggregation, pivoting

**Thin (2-3 questions, 3):** Transactions, ACID, isolation levels, deadlocks; Views, stored procedures, triggers; Partitioning / sharding / scaling

**Reference sources (licences unverified):** PostgreSQL documentation; SQLite documentation (runnable window-function examples); Use The Index, Luke (use-the-index-luke.com); Mode SQL tutorial (check terms of use); SQLBolt interactive lessons (check terms of use)

## Data Analysis  (v1 39 / v2 core 53 / v4 core 65 / +batch 03 75 questions)

| Concept | v1 | v2 core | v4 core | +batch 03 | +batch 03 incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---|---|
| Descriptive statistics & distributions | 3 | 5 | 8 | 10 | 17 |  |  |
| Data cleaning and missing values | 2 | 3 | 3 | 4 | 9 |  |  |
| Outlier detection | 1 | 1 | 2 | 2 | 6 | thin |  |
| EDA and visualisation choices | 1 | 1 | 1 | 1 | 3 | **gap** | thin |
| Hypothesis testing, p-values, confidence intervals | 6 | 6 | 9 | 10 | 14 |  |  |
| A/B testing & experiment design (power, sample size, pitfalls) | 1 | 1 | 7 | 9 | 20 |  |  |
| Correlation vs causation, confounding | 3 | 3 | 4 | 4 | 7 |  |  |
| Product / business metrics & root-cause analysis | 2 | 10 | 17 | 21 | 25 |  |  |
| Cohort, funnel and retention analysis | 0 | 0 | 1 | 1 | 11 | **gap** |  |
| Sampling & bias | 0 | 0 | 1 | 3 | 6 | thin |  |
| Excel / BI tools (pivot tables, dashboards) | 0 | 0 | 2 | 4 | 4 |  |  |
| pandas/SQL analysis exercises with data | 0 | 0 | 4 | 4 | 5 |  |  |
| Regression for analysis & interpretation | 3 | 3 | 3 | 3 | 3 | thin | thin |
| Time-series & trend/seasonality analysis | 1 | 1 | 2 | 2 | 6 | thin |  |
| Data storytelling and communicating findings | 2 | 2 | 2 | 3 | 3 | thin | thin |

**Still a gap after batch 03 (question-text match, 2):** EDA and visualisation choices; Cohort, funnel and retention analysis

**Thin (2-3 questions, 5):** Outlier detection; Sampling & bias; Regression for analysis & interpretation; Time-series & trend/seasonality analysis; Data storytelling and communicating findings

**Reference sources (licences unverified):** pandas user guide; Think Stats (Allen Downey; free online); OpenIntro Statistics (free PDF); Trustworthy Online Controlled Experiments (Kohavi et al.; book); Practical Statistics for Data Scientists (Bruce et al.; book)

## Summary

| Domain | Q v1 | Q v2 core | Q v4 core | Q +batch 03 | Concepts checked | Gaps v1 | Gaps v2 core | Gaps v4 core | Gaps +batch 03 | Gaps +batch 03 (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Machine Learning | 151 | 164 | 164 | 174 | 24 | 8 | 8 | 8 | 6 | 6 |
| Deep Learning | 56 | 64 | 86 | 86 | 20 | 14 | 14 | 3 | 3 | 3 |
| NLP | 19 | 27 | 53 | 53 | 17 | 14 | 13 | 2 | 2 | 2 |
| Python | 22 | 23 | 35 | 45 | 16 | 12 | 11 | 4 | 2 | 2 |
| SQL | 29 | 29 | 44 | 54 | 15 | 6 | 6 | 2 | 1 | 1 |
| Data Analysis | 39 | 53 | 65 | 75 | 15 | 8 | 8 | 3 | 2 | 2 |

Notes

* The key_concepts-inclusive column is optimistic (a key concept shares keywords with many checklist items); treat the question-text column as the conservative measure.
* Keyword matching on question text undercounts breadth: one scenario question (e.g. a production-debugging case) exercises several checklist concepts its wording does not name.
* A concept can show as covered while represented only by older one-line definitions; Stage 1B rewrote the 121 shortest/most imprecise answers, not every concept's depth.
* Statistics / A-B testing live under Data Analysis; MLE, likelihood, Bayes, bias-variance remain under Machine Learning.
* This document identifies gaps and next-batch targets only; it contains no new question text.
