# Error analysis (dev-lsa)

## bm25_q

| top-1 outcome | queries | share |
|---|---:|---:|
| correct | 73 | 52.1% |
| top1_partially_relevant (grade 1) | 24 | 17.1% |
| different domain | 24 | 17.1% |
| same domain, different topic | 15 | 10.7% |
| same-topic sibling record (wrong record, right topic) | 4 | 2.9% |

Queries with no relevant record in the top 5: 41 of 140
Domain-confusing queries whose top-1 is in the wrong domain: 5 of 16

## dev-lsa_q

| top-1 outcome | queries | share |
|---|---:|---:|
| correct | 41 | 29.3% |
| different domain | 33 | 23.6% |
| same domain, different topic | 31 | 22.1% |
| top1_partially_relevant (grade 1) | 23 | 16.4% |
| same-topic sibling record (wrong record, right topic) | 12 | 8.6% |

Queries with no relevant record in the top 5: 58 of 140
Domain-confusing queries whose top-1 is in the wrong domain: 8 of 16

## bm25_qk

| top-1 outcome | queries | share |
|---|---:|---:|
| correct | 89 | 63.6% |
| top1_partially_relevant (grade 1) | 29 | 20.7% |
| different domain | 10 | 7.1% |
| same domain, different topic | 7 | 5.0% |
| same-topic sibling record (wrong record, right topic) | 5 | 3.6% |

Queries with no relevant record in the top 5: 18 of 140
Domain-confusing queries whose top-1 is in the wrong domain: 2 of 16

## dev-lsa_qk

| top-1 outcome | queries | share |
|---|---:|---:|
| correct | 64 | 45.7% |
| top1_partially_relevant (grade 1) | 28 | 20.0% |
| different domain | 22 | 15.7% |
| same domain, different topic | 18 | 12.9% |
| same-topic sibling record (wrong record, right topic) | 8 | 5.7% |

Queries with no relevant record in the top 5: 31 of 140
Domain-confusing queries whose top-1 is in the wrong domain: 7 of 16

## bm25_qka

| top-1 outcome | queries | share |
|---|---:|---:|
| correct | 95 | 67.9% |
| top1_partially_relevant (grade 1) | 23 | 16.4% |
| different domain | 11 | 7.9% |
| same domain, different topic | 9 | 6.4% |
| same-topic sibling record (wrong record, right topic) | 2 | 1.4% |

Queries with no relevant record in the top 5: 9 of 140
Domain-confusing queries whose top-1 is in the wrong domain: 5 of 16

Worst misses (no relevant record in top 5):

* Q047 [paraphrase] "Why does Naive Bayes get called naive, and how does it use Bayes' rule to classify examples?" -> wanted smi-0141 (Instance-based and probabilistic classifiers); got smi-0201 (Instance-based and probabilistic classifiers)
* Q053 [paraphrase] "How do you design and sanity-check an online split test, so you don't ship something on a noisy or tiny win?" -> wanted smi-m0037 (MLOps case studies, deployment tests (canary/); got smi-g0019 (Training diagnostics and debugging)
* Q060 [paraphrase] "What does it mean to label each word in a sentence as a noun, verb, adjective and so on, and why is that usefu" -> wanted smi-0374 (Syntax and parsing); got smi-0360 (Syntax and parsing)
* Q083 [paraphrase] "How do I write a SQL query that shows what share of each signup-week group came back on day 1, 7 and 30, witho" -> wanted smi-g0034 (Cohort and retention queries); got smi-h0042 (Product and business metrics)
* Q098 [paraphrase] "Why do LLMs sometimes ignore relevant passages placed in the middle of a long prompt, and how would you test a" -> wanted smi-j0024 (Reranking and context assembly); got smi-g0011 (Semantic search and LLM applications)
* Q118 [similar_distinct] "What does it mean to estimate parameters by choosing the values that make the observed data most probable, in " -> wanted smi-0138 (Probability and likelihood); got smi-i0033 (Data preparation and cleaning)
* Q120 [paraphrase] "A user invokes their right to be forgotten; how do we find where their data fed into models, and what are our " -> wanted smi-m0020 (Security, governance, lineage and compliance ); got smi-0187 (Recommender systems)
* Q123 [multi_concept] "How do ensembles that average predicted probabilities from several models compare with simply fixing a single " -> wanted smi-0014 (Decision trees and ensembles); got smi-0058 (Neural network fundamentals)
* Q139 [domain_confusing] "In a neural net, how does gradient descent adjust each layer's weights and biases starting from the input laye" -> wanted smi-0031 (Neural network fundamentals); got smi-0082 (Neural network fundamentals)

## dev-lsa_qka

| top-1 outcome | queries | share |
|---|---:|---:|
| correct | 86 | 61.4% |
| top1_partially_relevant (grade 1) | 32 | 22.9% |
| different domain | 12 | 8.6% |
| same domain, different topic | 7 | 5.0% |
| same-topic sibling record (wrong record, right topic) | 3 | 2.1% |

Queries with no relevant record in the top 5: 18 of 140
Domain-confusing queries whose top-1 is in the wrong domain: 4 of 16

Worst misses (no relevant record in top 5):

* Q003 [multi_concept] "We compute features once for both training and batch scoring via a shared store with point-in-time joins; how " -> wanted smi-i0020 (Query patterns); got smi-l0042 (Feature stores and training-serving skew)
* Q014 [multi_concept] "When comparing two optimisers' mini-batch settings you also need to compare two retrieval pipelines on the sam" -> wanted smi-j0028 (RAG evaluation (recall@k, MRR, nDCG, faithful); got smi-0062 (Initialisation and optimisation)
* Q015 [concept_keywords] "find rows in one table missing from another EXCEPT NULL handling" -> wanted smi-i0013 (Set operations); got smi-0418 (SQL fundamentals)
* Q043 [multi_concept] "Our relational database is outgrowing one server and we are considering splitting rows by a key across nodes; " -> wanted smi-0437 (Partitioning and scaling); got smi-0410 (SQL fundamentals)
* Q045 [concept_keywords] "sklearn TfidfVectorizer formula smoothing and normalization" -> wanted smi-g0002 (Text preprocessing and representation); got smi-0260 (Instance-based and probabilistic classifiers)
* Q048 [concept_keywords] "how transformers know word order: sinusoidal vs rotary vs ALiBi" -> wanted smi-h0016 (Sequence models and transformers); got smi-0112 (Sequence models and transformers)
* Q053 [paraphrase] "How do you design and sanity-check an online split test, so you don't ship something on a noisy or tiny win?" -> wanted smi-m0037 (MLOps case studies, deployment tests (canary/); got smi-g0019 (Training diagnostics and debugging)
* Q060 [paraphrase] "What does it mean to label each word in a sentence as a noun, verb, adjective and so on, and why is that usefu" -> wanted smi-0374 (Syntax and parsing); got smi-0360 (Syntax and parsing)
* Q063 [paraphrase] "How do you design an ML service to keep answering when a dependency fails, for example by falling back to a si" -> wanted smi-m0027 (Reliability, incident response, rollback/reco); got smi-l0034 (Containers, orchestration and ML pipelines in)
* Q107 [paraphrase] "Which evaluation measures would you use to judge a logistic regression classifier on skewed data, and how do y" -> wanted smi-0251 (Linear and logistic regression); got smi-0331 (Linear and logistic regression)

