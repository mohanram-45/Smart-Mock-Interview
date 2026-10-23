# Retrieval benchmark (dev-lsa)

Corpus 666 records (sha db776e9fa135), 166 queries, python 3.13.16, 2 CPUs.

## Overall (primary relevance = grade 2, consensus labels)

| System | success@1 | success@3 | success@5 | recall@1 | recall@3 | recall@5 | mrr@10 | ndcg@5 | lat p50 ms | lat p95 ms | unjudged@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bm25_q | 0.521 | 0.671 | 0.707 | 0.441 | 0.610 | 0.649 | 0.608 | 0.567 | 0.36 | 0.86 | 0.000 |
| dev-lsa_q | 0.293 | 0.536 | 0.586 | 0.246 | 0.457 | 0.515 | 0.429 | 0.410 | 1.52 | 2.13 | 0.000 |
| bm25_qk | 0.636 | 0.779 | 0.871 | 0.529 | 0.696 | 0.801 | 0.727 | 0.700 | 0.40 | 1.03 | 0.000 |
| dev-lsa_qk | 0.457 | 0.679 | 0.779 | 0.381 | 0.583 | 0.708 | 0.597 | 0.597 | 2.33 | 3.34 | 0.000 |
| bm25_qka | 0.679 | 0.864 | 0.936 | 0.568 | 0.774 | 0.870 | 0.779 | 0.756 | 1.04 | 2.16 | 0.000 |
| dev-lsa_qka | 0.614 | 0.821 | 0.871 | 0.518 | 0.744 | 0.818 | 0.729 | 0.746 | 4.97 | 5.86 | 0.000 |

### bm25_q: by category

| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |
|---|---:|---:|---:|---:|---:|
| concept_keywords | 24 | 0.750 | 0.875 | 0.824 | 0.760 |
| domain_confusing | 16 | 0.375 | 0.688 | 0.483 | 0.451 |
| multi_concept | 16 | 0.562 | 0.688 | 0.618 | 0.588 |
| no_answer | 20 | - | - | - | - |
| no_answer_intended_but_covered | 2 | - | - | - | 0.193 |
| paraphrase | 72 | 0.464 | 0.681 | 0.567 | 0.537 |
| similar_distinct | 16 | 0.533 | 0.600 | 0.575 | 0.553 |

bm25_q: by domain

| domain | n | success@1 | success@5 | mrr@10 |
|---|---:|---:|---:|---:|
| Data Analysis | 17 | 0.647 | 0.706 | 0.676 |
| Deep Learning | 17 | 0.438 | 0.750 | 0.583 |
| Generative AI & RAG | 20 | 0.750 | 0.900 | 0.807 |
| MLOps & Model Deployment | 15 | 0.333 | 0.600 | 0.460 |
| Machine Learning | 30 | 0.429 | 0.607 | 0.489 |
| NLP | 13 | 0.500 | 0.500 | 0.526 |
| Python | 14 | 0.643 | 0.857 | 0.772 |
| SQL | 18 | 0.444 | 0.722 | 0.582 |

bm25_q: no-answer queries n=20; top-1 score AUROC (answerable vs no-answer) = 0.968; share of no-answer queries scoring above the answerable median = 0.000

### dev-lsa_q: by category

| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |
|---|---:|---:|---:|---:|---:|
| concept_keywords | 24 | 0.375 | 0.625 | 0.477 | 0.477 |
| domain_confusing | 16 | 0.312 | 0.625 | 0.450 | 0.377 |
| multi_concept | 16 | 0.188 | 0.312 | 0.286 | 0.270 |
| no_answer | 20 | - | - | - | - |
| no_answer_intended_but_covered | 2 | - | - | - | 0.193 |
| paraphrase | 72 | 0.304 | 0.652 | 0.458 | 0.451 |
| similar_distinct | 16 | 0.200 | 0.467 | 0.350 | 0.327 |

dev-lsa_q: by domain

| domain | n | success@1 | success@5 | mrr@10 |
|---|---:|---:|---:|---:|
| Data Analysis | 17 | 0.353 | 0.706 | 0.517 |
| Deep Learning | 17 | 0.188 | 0.375 | 0.267 |
| Generative AI & RAG | 20 | 0.500 | 0.850 | 0.667 |
| MLOps & Model Deployment | 15 | 0.400 | 0.467 | 0.441 |
| Machine Learning | 30 | 0.286 | 0.500 | 0.389 |
| NLP | 13 | 0.250 | 0.500 | 0.350 |
| Python | 14 | 0.357 | 0.786 | 0.542 |
| SQL | 18 | 0.000 | 0.500 | 0.243 |

dev-lsa_q: no-answer queries n=20; top-1 score AUROC (answerable vs no-answer) = 0.537; share of no-answer queries scoring above the answerable median = 0.450

### bm25_qk: by category

| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |
|---|---:|---:|---:|---:|---:|
| concept_keywords | 24 | 0.875 | 1.000 | 0.938 | 0.868 |
| domain_confusing | 16 | 0.562 | 0.875 | 0.677 | 0.635 |
| multi_concept | 16 | 0.375 | 0.812 | 0.528 | 0.589 |
| no_answer | 20 | - | - | - | - |
| no_answer_intended_but_covered | 2 | - | - | - | 0.689 |
| paraphrase | 72 | 0.652 | 0.855 | 0.735 | 0.687 |
| similar_distinct | 16 | 0.533 | 0.800 | 0.621 | 0.682 |

bm25_qk: by domain

| domain | n | success@1 | success@5 | mrr@10 |
|---|---:|---:|---:|---:|
| Data Analysis | 17 | 0.647 | 0.824 | 0.751 |
| Deep Learning | 17 | 0.625 | 0.875 | 0.708 |
| Generative AI & RAG | 20 | 0.800 | 1.000 | 0.879 |
| MLOps & Model Deployment | 15 | 0.400 | 0.800 | 0.569 |
| Machine Learning | 30 | 0.464 | 0.857 | 0.596 |
| NLP | 13 | 0.667 | 0.750 | 0.688 |
| Python | 14 | 0.929 | 1.000 | 0.964 |
| SQL | 18 | 0.667 | 0.833 | 0.731 |

bm25_qk: no-answer queries n=20; top-1 score AUROC (answerable vs no-answer) = 0.970; share of no-answer queries scoring above the answerable median = 0.000

### dev-lsa_qk: by category

| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |
|---|---:|---:|---:|---:|---:|
| concept_keywords | 24 | 0.583 | 0.792 | 0.682 | 0.648 |
| domain_confusing | 16 | 0.375 | 0.750 | 0.545 | 0.556 |
| multi_concept | 16 | 0.250 | 0.562 | 0.396 | 0.427 |
| no_answer | 20 | - | - | - | - |
| no_answer_intended_but_covered | 2 | - | - | - | 0.653 |
| paraphrase | 72 | 0.478 | 0.812 | 0.618 | 0.612 |
| similar_distinct | 16 | 0.467 | 0.867 | 0.628 | 0.656 |

dev-lsa_qk: by domain

| domain | n | success@1 | success@5 | mrr@10 |
|---|---:|---:|---:|---:|
| Data Analysis | 17 | 0.471 | 0.824 | 0.618 |
| Deep Learning | 17 | 0.312 | 0.625 | 0.454 |
| Generative AI & RAG | 20 | 0.750 | 1.000 | 0.867 |
| MLOps & Model Deployment | 15 | 0.400 | 0.600 | 0.505 |
| Machine Learning | 30 | 0.393 | 0.857 | 0.554 |
| NLP | 13 | 0.417 | 0.667 | 0.500 |
| Python | 14 | 0.429 | 0.857 | 0.635 |
| SQL | 18 | 0.444 | 0.667 | 0.580 |

dev-lsa_qk: no-answer queries n=20; top-1 score AUROC (answerable vs no-answer) = 0.697; share of no-answer queries scoring above the answerable median = 0.250

### bm25_qka: by category

| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |
|---|---:|---:|---:|---:|---:|
| concept_keywords | 24 | 0.917 | 1.000 | 0.958 | 0.867 |
| domain_confusing | 16 | 0.562 | 0.938 | 0.705 | 0.723 |
| multi_concept | 16 | 0.562 | 0.938 | 0.685 | 0.660 |
| no_answer | 20 | - | - | - | - |
| no_answer_intended_but_covered | 2 | - | - | - | 0.925 |
| paraphrase | 72 | 0.667 | 0.913 | 0.769 | 0.735 |
| similar_distinct | 16 | 0.600 | 0.933 | 0.719 | 0.793 |

bm25_qka: by domain

| domain | n | success@1 | success@5 | mrr@10 |
|---|---:|---:|---:|---:|
| Data Analysis | 17 | 0.824 | 0.941 | 0.865 |
| Deep Learning | 17 | 0.625 | 0.938 | 0.742 |
| Generative AI & RAG | 20 | 0.800 | 0.950 | 0.872 |
| MLOps & Model Deployment | 15 | 0.533 | 0.933 | 0.632 |
| Machine Learning | 30 | 0.464 | 0.893 | 0.651 |
| NLP | 13 | 0.667 | 0.917 | 0.792 |
| Python | 14 | 1.000 | 1.000 | 1.000 |
| SQL | 18 | 0.667 | 0.944 | 0.770 |

bm25_qka: no-answer queries n=20; top-1 score AUROC (answerable vs no-answer) = 0.985; share of no-answer queries scoring above the answerable median = 0.000

### dev-lsa_qka: by category

| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |
|---|---:|---:|---:|---:|---:|
| concept_keywords | 24 | 0.667 | 0.875 | 0.755 | 0.759 |
| domain_confusing | 16 | 0.562 | 0.938 | 0.721 | 0.744 |
| multi_concept | 16 | 0.250 | 0.625 | 0.414 | 0.459 |
| no_answer | 20 | - | - | - | - |
| no_answer_intended_but_covered | 2 | - | - | - | 1.000 |
| paraphrase | 72 | 0.681 | 0.913 | 0.788 | 0.786 |
| similar_distinct | 16 | 0.667 | 0.867 | 0.762 | 0.803 |

dev-lsa_qka: by domain

| domain | n | success@1 | success@5 | mrr@10 |
|---|---:|---:|---:|---:|
| Data Analysis | 17 | 0.588 | 0.882 | 0.717 |
| Deep Learning | 17 | 0.438 | 0.750 | 0.606 |
| Generative AI & RAG | 20 | 0.900 | 1.000 | 0.950 |
| MLOps & Model Deployment | 15 | 0.400 | 0.733 | 0.516 |
| Machine Learning | 30 | 0.643 | 0.893 | 0.760 |
| NLP | 13 | 0.667 | 0.833 | 0.734 |
| Python | 14 | 0.786 | 1.000 | 0.881 |
| SQL | 18 | 0.444 | 0.833 | 0.613 |

dev-lsa_qka: no-answer queries n=20; top-1 score AUROC (answerable vs no-answer) = 0.760; share of no-answer queries scoring above the answerable median = 0.250
