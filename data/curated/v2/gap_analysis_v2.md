# Domain gap analysis - v2 (after Stage 1B)

Method (unchanged from Stage 1A so counts are comparable): each domain has a checklist of core interview concepts, matched by keyword regex against the **question text**. A second column also matches the `key_concepts` field. A hit count is only a coverage indicator: a hit does not mean the answer is good, and 0 does not prove absence. 0-1 hits = gap, 2-3 = thin. Counts are per domain: records are matched within the domain label they carry. The concept checklist comes from standard curricula, not from this dataset; reference sources below are suggestions only and their licences are unverified. 'v1' = the 316 questions of Stage 1A, 'v2 core' = 360 questions after Stage 1B, '+pilot' = core plus the 41 pilot questions (pending approval).

## Machine Learning  (v1 151 / v2 core 164 / +pilot 164 questions)

| Concept | v1 | v2 core | +pilot | +pilot incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---|---|
| Linear/logistic regression assumptions & interpretation | 10 | 11 | 11 | 17 |  |  |
| Regularisation (L1/L2, elastic net) | 4 | 4 | 4 | 15 |  |  |
| Bias-variance, over/underfitting | 6 | 6 | 6 | 31 |  |  |
| Model evaluation: precision/recall/F1/ROC/PR | 7 | 7 | 7 | 17 |  |  |
| Cross-validation & data leakage | 5 | 5 | 5 | 23 |  |  |
| Tree ensembles: RF, gradient boosting, XGBoost | 12 | 14 | 14 | 25 |  |  |
| SVM & kernels | 10 | 12 | 12 | 14 |  |  |
| Clustering & choosing k | 6 | 6 | 6 | 8 |  |  |
| Dimensionality reduction (PCA, t-SNE) | 7 | 8 | 8 | 15 |  |  |
| Feature engineering/encoding/scaling | 5 | 5 | 5 | 19 |  |  |
| Class imbalance | 2 | 2 | 2 | 8 | thin |  |
| Missing data & outliers | 1 | 1 | 1 | 4 | **gap** |  |
| Probability/statistics: Bayes, CLT, hypothesis tests, CI | 8 | 9 | 9 | 14 |  |  |
| Optimisation: gradient descent variants, learning rate | 2 | 2 | 2 | 6 | thin |  |
| Recommender systems | 7 | 9 | 9 | 11 |  |  |
| Time-series forecasting (ARIMA, stationarity, seasonality) | 1 | 1 | 1 | 2 | **gap** | thin |
| Hyperparameter tuning (grid/random/Bayesian) | 2 | 2 | 2 | 5 | thin |  |
| Model interpretability (SHAP/LIME, feature importance) | 0 | 0 | 0 | 4 | **gap** |  |
| Anomaly detection | 0 | 0 | 0 | 2 | **gap** | thin |
| ML system design / deployment / monitoring / drift | 1 | 1 | 1 | 4 | **gap** |  |
| Reinforcement learning basics | 0 | 1 | 1 | 3 | **gap** | thin |
| Semi/self-supervised learning | 1 | 1 | 1 | 4 | **gap** |  |
| Calibration & probabilistic outputs | 0 | 0 | 0 | 6 | **gap** |  |
| Naive Bayes / KNN / decision-tree fundamentals | 13 | 15 | 15 | 22 |  |  |

**Still a gap after the pilot (question-text match, 8):** Missing data & outliers; Time-series forecasting (ARIMA, stationarity, seasonality); Model interpretability (SHAP/LIME, feature importance); Anomaly detection; ML system design / deployment / monitoring / drift; Reinforcement learning basics; Semi/self-supervised learning; Calibration & probabilistic outputs

**Reference sources (licences unverified):** scikit-learn User Guide (scikit-learn.org); An Introduction to Statistical Learning (James et al.; free PDF from authors); The Elements of Statistical Learning (Hastie et al.; free PDF from authors); Google Machine Learning Crash Course; Stanford CS229 lecture notes

## Deep Learning  (v1 56 / v2 core 64 / +pilot 76 questions)

| Concept | v1 | v2 core | +pilot | +pilot incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---|---|
| Backpropagation & chain rule | 1 | 1 | 1 | 8 | **gap** |  |
| Activation functions | 8 | 10 | 14 | 19 |  |  |
| Loss functions | 1 | 1 | 5 | 12 |  |  |
| Optimisers (SGD, momentum, Adam) | 1 | 1 | 2 | 6 | thin |  |
| Regularisation: dropout, weight decay, early stopping | 2 | 2 | 3 | 9 | thin |  |
| Normalisation: batch norm, layer norm | 1 | 1 | 2 | 5 | thin |  |
| Vanishing/exploding gradients, initialisation | 5 | 6 | 7 | 13 |  |  |
| CNNs: convolution, pooling, padding/stride | 3 | 4 | 8 | 9 |  |  |
| RNN/LSTM/GRU | 7 | 7 | 7 | 8 |  |  |
| Attention & Transformers | 1 | 1 | 2 | 5 | thin |  |
| Transfer learning & fine-tuning | 1 | 1 | 2 | 3 | thin | thin |
| Autoencoders / VAEs / GANs | 3 | 4 | 4 | 4 |  |  |
| Residual connections / modern architectures (ResNet, BERT, GPT) | 0 | 0 | 1 | 2 | **gap** | thin |
| Training practicalities: batch size, learning-rate schedules, mixed precision, GPUs | 1 | 1 | 3 | 8 | thin |  |
| Overfitting diagnosis via learning curves | 1 | 1 | 2 | 2 | thin | thin |
| Frameworks: PyTorch/TensorFlow autograd & training loop | 0 | 0 | 0 | 1 | **gap** | **gap** |
| Embeddings | 0 | 0 | 1 | 1 | **gap** | **gap** |
| Data augmentation | 1 | 1 | 2 | 3 | thin | thin |
| Evaluation & deployment of DL models (quantisation, distillation) | 0 | 0 | 2 | 3 | thin | thin |
| Diffusion / LLM fundamentals | 0 | 0 | 0 | 0 | **gap** | **gap** |

**Still a gap after the pilot (question-text match, 5):** Backpropagation & chain rule; Residual connections / modern architectures (ResNet, BERT, GPT); Frameworks: PyTorch/TensorFlow autograd & training loop; Embeddings; Diffusion / LLM fundamentals

**Reference sources (licences unverified):** Dive into Deep Learning (d2l.ai); Deep Learning (Goodfellow, Bengio, Courville; free online); PyTorch tutorials and documentation; Stanford CS231n notes; Neural Networks and Deep Learning (Nielsen; free online)

## NLP  (v1 19 / v2 core 27 / +pilot 41 questions)

| Concept | v1 | v2 core | +pilot | +pilot incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---|---|
| Text preprocessing: tokenisation, stop words, stemming/lemmatisation | 1 | 3 | 7 | 13 |  |  |
| Representations: BoW, TF-IDF, n-grams | 3 | 3 | 6 | 9 |  |  |
| Word embeddings: word2vec, GloVe, fastText | 0 | 0 | 1 | 4 | **gap** |  |
| Sequence tasks: POS tagging, NER, parsing | 4 | 4 | 5 | 11 |  |  |
| Language models & perplexity | 1 | 1 | 2 | 5 | thin |  |
| Transformers, BERT/GPT, attention | 0 | 0 | 2 | 3 | thin | thin |
| Text classification & sentiment analysis | 1 | 1 | 2 | 6 | thin |  |
| Evaluation metrics: BLEU, ROUGE, F1 | 0 | 0 | 3 | 6 | thin |  |
| Machine translation / seq2seq | 0 | 0 | 0 | 0 | **gap** | **gap** |
| Summarisation & question answering | 1 | 1 | 1 | 1 | **gap** | **gap** |
| Topic modelling (LDA, LSI) | 1 | 1 | 2 | 2 | thin | thin |
| Information retrieval & semantic search / vector search | 0 | 1 | 7 | 9 |  |  |
| Fine-tuning, prompt engineering, LLM evaluation, hallucination | 0 | 0 | 1 | 3 | **gap** | thin |
| Subword tokenisation (BPE, WordPiece) | 0 | 0 | 2 | 2 | thin | thin |
| Handling OOV, multilingual & low-resource text | 0 | 0 | 0 | 2 | **gap** | thin |
| RAG / retrieval-augmented generation | 0 | 0 | 1 | 1 | **gap** | **gap** |
| Ambiguity, semantics and pragmatics | 3 | 5 | 6 | 7 |  |  |

**Still a gap after the pilot (question-text match, 6):** Word embeddings: word2vec, GloVe, fastText; Machine translation / seq2seq; Summarisation & question answering; Fine-tuning, prompt engineering, LLM evaluation, hallucination; Handling OOV, multilingual & low-resource text; RAG / retrieval-augmented generation

**Reference sources (licences unverified):** Speech and Language Processing (Jurafsky & Martin; free draft online); Hugging Face NLP/LLM course; spaCy documentation; Stanford CS224n materials; Introduction to Information Retrieval (Manning et al.; free online)

## Python  (v1 22 / v2 core 23 / +pilot 23 questions)

| Concept | v1 | v2 core | +pilot | +pilot incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---|---|
| Core data types & mutability (list/tuple/dict/set) | 3 | 3 | 3 | 4 | thin |  |
| Functions, closures, decorators, *args/**kwargs | 1 | 1 | 1 | 1 | **gap** | **gap** |
| OOP: classes, inheritance, dunder methods | 2 | 2 | 2 | 4 | thin |  |
| Iterators & generators, comprehensions | 1 | 1 | 1 | 2 | **gap** | thin |
| Exceptions & context managers | 1 | 1 | 1 | 1 | **gap** | **gap** |
| Concurrency: GIL, threading, multiprocessing, asyncio | 1 | 1 | 1 | 2 | **gap** | thin |
| Memory management, copy vs deepcopy, is vs == | 1 | 1 | 1 | 1 | **gap** | **gap** |
| Algorithms & data structures coding (sorting, search, stack/queue, trees, graphs) | 7 | 7 | 7 | 8 |  |  |
| Complexity analysis | 2 | 2 | 2 | 2 | thin | thin |
| NumPy / vectorisation / broadcasting | 1 | 1 | 1 | 1 | **gap** | **gap** |
| pandas data manipulation (merge, groupby, missing values) | 1 | 1 | 1 | 1 | **gap** | **gap** |
| Testing & debugging (unittest/pytest, mocking) | 1 | 2 | 2 | 2 | thin | thin |
| Packaging, virtual environments, typing, PEP 8 | 0 | 0 | 0 | 0 | **gap** | **gap** |
| File I/O, JSON, regex | 0 | 0 | 0 | 0 | **gap** | **gap** |
| Performance profiling & optimisation | 0 | 0 | 0 | 0 | **gap** | **gap** |
| Plotting (matplotlib/seaborn) | 1 | 1 | 1 | 1 | **gap** | **gap** |

**Still a gap after the pilot (question-text match, 11):** Functions, closures, decorators, *args/**kwargs; Iterators & generators, comprehensions; Exceptions & context managers; Concurrency: GIL, threading, multiprocessing, asyncio; Memory management, copy vs deepcopy, is vs ==; NumPy / vectorisation / broadcasting; pandas data manipulation (merge, groupby, missing values); Packaging, virtual environments, typing, PEP 8; File I/O, JSON, regex; Performance profiling & optimisation; Plotting (matplotlib/seaborn)

**Reference sources (licences unverified):** Official Python documentation and tutorial (docs.python.org); Python Data Science Handbook (VanderPlas; free online); PEP 8 and PEP 20; Real Python tutorials (check terms of use); NumPy and pandas user guides

## SQL  (v1 29 / v2 core 29 / +pilot 44 questions)

| Concept | v1 | v2 core | +pilot | +pilot incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---|---|
| SELECT/WHERE/GROUP BY/HAVING/ORDER BY semantics | 2 | 2 | 14 | 18 |  |  |
| Joins: inner/left/right/full/cross/self, anti-join | 3 | 3 | 6 | 10 |  |  |
| Subqueries, CTEs, recursive CTEs | 2 | 2 | 3 | 10 | thin |  |
| Window functions: ROW_NUMBER/RANK/LAG/LEAD/running totals | 2 | 2 | 4 | 7 |  |  |
| NULL handling and three-valued logic | 1 | 1 | 9 | 19 |  |  |
| Set operations: UNION/INTERSECT/EXCEPT | 0 | 0 | 1 | 2 | **gap** | thin |
| Indexes, clustered vs non-clustered, query plans | 4 | 4 | 6 | 9 |  |  |
| Normalisation / schema design / keys | 4 | 4 | 14 | 15 |  |  |
| Transactions, ACID, isolation levels, deadlocks | 3 | 3 | 3 | 3 | thin | thin |
| Aggregation patterns: top-N per group, duplicates, gaps/islands, de-duplication | 1 | 1 | 7 | 11 |  |  |
| Date/time and string functions | 0 | 0 | 6 | 8 |  |  |
| CASE expressions, conditional aggregation, pivoting | 0 | 0 | 1 | 1 | **gap** | **gap** |
| Views, stored procedures, triggers | 2 | 2 | 2 | 4 | thin |  |
| Partitioning / sharding / scaling | 2 | 2 | 2 | 8 | thin |  |
| Hands-on query-writing exercises with schemas and expected output | 0 | 0 | 6 | 6 |  |  |

**Still a gap after the pilot (question-text match, 2):** Set operations: UNION/INTERSECT/EXCEPT; CASE expressions, conditional aggregation, pivoting

**Reference sources (licences unverified):** PostgreSQL documentation; SQLite documentation (runnable window-function examples); Use The Index, Luke (use-the-index-luke.com); Mode SQL tutorial (check terms of use); SQLBolt interactive lessons (check terms of use)

## Data Analysis  (v1 39 / v2 core 53 / +pilot 53 questions)

| Concept | v1 | v2 core | +pilot | +pilot incl. key_concepts | Status (question text) | Status (incl. key_concepts) |
|---|---:|---:|---:|---:|---|---|
| Descriptive statistics & distributions | 3 | 5 | 5 | 11 |  |  |
| Data cleaning and missing values | 2 | 3 | 3 | 6 | thin |  |
| Outlier detection | 1 | 1 | 1 | 3 | **gap** | thin |
| EDA and visualisation choices | 1 | 1 | 1 | 2 | **gap** | thin |
| Hypothesis testing, p-values, confidence intervals | 6 | 6 | 6 | 8 |  |  |
| A/B testing & experiment design (power, sample size, pitfalls) | 1 | 1 | 1 | 10 | **gap** |  |
| Correlation vs causation, confounding | 3 | 3 | 3 | 5 | thin |  |
| Product / business metrics & root-cause analysis | 2 | 10 | 10 | 12 |  |  |
| Cohort, funnel and retention analysis | 0 | 0 | 0 | 8 | **gap** |  |
| Sampling & bias | 0 | 0 | 0 | 2 | **gap** | thin |
| Excel / BI tools (pivot tables, dashboards) | 0 | 0 | 0 | 0 | **gap** | **gap** |
| pandas/SQL analysis exercises with data | 0 | 0 | 0 | 1 | **gap** | **gap** |
| Regression for analysis & interpretation | 3 | 3 | 3 | 3 | thin | thin |
| Time-series & trend/seasonality analysis | 1 | 1 | 1 | 3 | **gap** | thin |
| Data storytelling and communicating findings | 2 | 2 | 2 | 2 | thin | thin |

**Still a gap after the pilot (question-text match, 8):** Outlier detection; EDA and visualisation choices; A/B testing & experiment design (power, sample size, pitfalls); Cohort, funnel and retention analysis; Sampling & bias; Excel / BI tools (pivot tables, dashboards); pandas/SQL analysis exercises with data; Time-series & trend/seasonality analysis

**Reference sources (licences unverified):** pandas user guide; Think Stats (Allen Downey; free online); OpenIntro Statistics (free PDF); Trustworthy Online Controlled Experiments (Kohavi et al.; book); Practical Statistics for Data Scientists (Bruce et al.; book)

## Summary

| Domain | Questions v1 | v2 core | +pilot | Concepts checked | Gaps v1 | Gaps v2 core | Gaps +pilot | Gaps +pilot (incl. key_concepts) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Machine Learning | 151 | 164 | 164 | 24 | 8 | 8 | 8 | 0 |
| Deep Learning | 56 | 64 | 76 | 20 | 14 | 14 | 5 | 3 |
| NLP | 19 | 27 | 41 | 17 | 14 | 13 | 6 | 3 |
| Python | 22 | 23 | 23 | 16 | 12 | 11 | 11 | 9 |
| SQL | 29 | 29 | 44 | 15 | 6 | 6 | 2 | 1 |
| Data Analysis | 39 | 53 | 53 | 15 | 8 | 8 | 8 | 2 |

Notes

* The key_concepts-inclusive column is optimistic (a key concept shares keywords with many checklist items); treat the question-text column as the conservative measure.
* Keyword matching on question text undercounts breadth: a single scenario question (e.g. a production-debugging case) exercises several checklist concepts that its wording does not name.
* A concept can show as covered while only being represented by one-line definitions in the older records; the Stage 1B rewrites addressed the 121 shortest/most imprecise answers, not every concept's depth.
* Statistics / A-B testing live under Data Analysis; MLE, likelihood, Bayes, bias-variance remain under Machine Learning.
* This document identifies gaps and next-batch targets only; it contains no new question text.
