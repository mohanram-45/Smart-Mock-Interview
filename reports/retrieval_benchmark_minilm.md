# Retrieval benchmark (minilm)

Corpus 666 records (sha db776e9fa135), 166 queries, python 3.12.7, 12 CPUs.

## Overall (primary relevance = grade 2, consensus labels)

| System | success@1 | success@3 | success@5 | recall@1 | recall@3 | recall@5 | mrr@10 | ndcg@5 | lat p50 ms | lat p95 ms | unjudged@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bm25_q | 0.521 | 0.671 | 0.707 | 0.441 | 0.610 | 0.649 | 0.608 | 0.567 | 0.32 | 0.70 | 0.000 |
| minilm_q | 0.686 | 0.850 | 0.914 | 0.570 | 0.757 | 0.846 | 0.781 | 0.726 | 9.94 | 35.10 | 0.464 |
| hybrid_minilm_q | 0.629 | 0.814 | 0.829 | 0.526 | 0.727 | 0.755 | 0.722 | 0.675 | 9.99 | 12.14 | 0.230 |
| bm25_qk | 0.636 | 0.779 | 0.871 | 0.529 | 0.696 | 0.801 | 0.727 | 0.700 | 0.39 | 0.89 | 0.000 |
| minilm_qk | 0.714 | 0.907 | 0.950 | 0.593 | 0.852 | 0.896 | 0.812 | 0.779 | 9.81 | 12.07 | 0.439 |
| hybrid_minilm_qk | 0.729 | 0.900 | 0.907 | 0.604 | 0.810 | 0.836 | 0.811 | 0.764 | 10.36 | 13.49 | 0.196 |
| bm25_qka | 0.679 | 0.864 | 0.936 | 0.568 | 0.774 | 0.870 | 0.779 | 0.756 | 0.93 | 1.97 | 0.000 |
| minilm_qka | 0.729 | 0.914 | 0.950 | 0.602 | 0.836 | 0.895 | 0.821 | 0.792 | 9.79 | 11.98 | 0.421 |
| hybrid_minilm_qka | 0.807 | 0.914 | 0.957 | 0.652 | 0.833 | 0.907 | 0.870 | 0.824 | 10.78 | 13.34 | 0.190 |

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

### minilm_q: by category

| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |
|---|---:|---:|---:|---:|---:|
| concept_keywords | 24 | 0.833 | 0.917 | 0.875 | 0.774 |
| domain_confusing | 16 | 0.625 | 0.938 | 0.773 | 0.672 |
| multi_concept | 16 | 0.500 | 0.688 | 0.586 | 0.539 |
| no_answer | 20 | - | - | - | - |
| no_answer_intended_but_covered | 2 | - | - | - | 0.307 |
| paraphrase | 72 | 0.681 | 0.942 | 0.784 | 0.748 |
| similar_distinct | 16 | 0.733 | 1.000 | 0.833 | 0.848 |

minilm_q: by domain

| domain | n | success@1 | success@5 | mrr@10 |
|---|---:|---:|---:|---:|
| Data Analysis | 17 | 0.647 | 1.000 | 0.776 |
| Deep Learning | 17 | 0.688 | 0.875 | 0.754 |
| Generative AI & RAG | 20 | 0.550 | 0.950 | 0.723 |
| MLOps & Model Deployment | 15 | 0.667 | 0.867 | 0.776 |
| Machine Learning | 30 | 0.786 | 0.893 | 0.842 |
| NLP | 13 | 0.583 | 0.833 | 0.674 |
| Python | 14 | 1.000 | 1.000 | 1.000 |
| SQL | 18 | 0.556 | 0.889 | 0.685 |

minilm_q: no-answer queries n=20; top-1 score AUROC (answerable vs no-answer) = 0.988; share of no-answer queries scoring above the answerable median = 0.000

### hybrid_minilm_q: by category

| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |
|---|---:|---:|---:|---:|---:|
| concept_keywords | 24 | 0.792 | 0.958 | 0.868 | 0.818 |
| domain_confusing | 16 | 0.500 | 0.688 | 0.591 | 0.502 |
| multi_concept | 16 | 0.688 | 0.812 | 0.731 | 0.642 |
| no_answer | 20 | - | - | - | - |
| no_answer_intended_but_covered | 2 | - | - | - | 0.460 |
| paraphrase | 72 | 0.594 | 0.841 | 0.714 | 0.671 |
| similar_distinct | 16 | 0.600 | 0.733 | 0.656 | 0.707 |

hybrid_minilm_q: by domain

| domain | n | success@1 | success@5 | mrr@10 |
|---|---:|---:|---:|---:|
| Data Analysis | 17 | 0.706 | 1.000 | 0.819 |
| Deep Learning | 17 | 0.688 | 0.750 | 0.728 |
| Generative AI & RAG | 20 | 0.750 | 1.000 | 0.850 |
| MLOps & Model Deployment | 15 | 0.533 | 0.733 | 0.661 |
| Machine Learning | 30 | 0.536 | 0.643 | 0.587 |
| NLP | 13 | 0.417 | 0.667 | 0.542 |
| Python | 14 | 0.786 | 1.000 | 0.893 |
| SQL | 18 | 0.611 | 0.889 | 0.731 |

hybrid_minilm_q: no-answer queries n=20; top-1 score AUROC (answerable vs no-answer) = 0.883; share of no-answer queries scoring above the answerable median = 0.050

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

### minilm_qk: by category

| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |
|---|---:|---:|---:|---:|---:|
| concept_keywords | 24 | 0.792 | 1.000 | 0.889 | 0.839 |
| domain_confusing | 16 | 0.688 | 0.875 | 0.787 | 0.690 |
| multi_concept | 16 | 0.500 | 0.750 | 0.606 | 0.567 |
| no_answer | 20 | - | - | - | - |
| no_answer_intended_but_covered | 2 | - | - | - | 0.622 |
| paraphrase | 72 | 0.739 | 0.986 | 0.832 | 0.807 |
| similar_distinct | 16 | 0.733 | 1.000 | 0.844 | 0.885 |

minilm_qk: by domain

| domain | n | success@1 | success@5 | mrr@10 |
|---|---:|---:|---:|---:|
| Data Analysis | 17 | 0.706 | 1.000 | 0.821 |
| Deep Learning | 17 | 0.625 | 0.812 | 0.708 |
| Generative AI & RAG | 20 | 0.650 | 1.000 | 0.787 |
| MLOps & Model Deployment | 15 | 0.733 | 0.933 | 0.813 |
| Machine Learning | 30 | 0.714 | 0.929 | 0.802 |
| NLP | 13 | 0.667 | 1.000 | 0.819 |
| Python | 14 | 1.000 | 1.000 | 1.000 |
| SQL | 18 | 0.667 | 0.944 | 0.787 |

minilm_qk: no-answer queries n=20; top-1 score AUROC (answerable vs no-answer) = 0.992; share of no-answer queries scoring above the answerable median = 0.000

### hybrid_minilm_qk: by category

| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |
|---|---:|---:|---:|---:|---:|
| concept_keywords | 24 | 0.958 | 1.000 | 0.979 | 0.911 |
| domain_confusing | 16 | 0.688 | 0.875 | 0.760 | 0.662 |
| multi_concept | 16 | 0.625 | 0.812 | 0.716 | 0.647 |
| no_answer | 20 | - | - | - | - |
| no_answer_intended_but_covered | 2 | - | - | - | 0.775 |
| paraphrase | 72 | 0.710 | 0.913 | 0.806 | 0.761 |
| similar_distinct | 16 | 0.600 | 0.867 | 0.722 | 0.775 |

hybrid_minilm_qk: by domain

| domain | n | success@1 | success@5 | mrr@10 |
|---|---:|---:|---:|---:|
| Data Analysis | 17 | 0.765 | 1.000 | 0.873 |
| Deep Learning | 17 | 0.750 | 0.875 | 0.809 |
| Generative AI & RAG | 20 | 0.800 | 1.000 | 0.875 |
| MLOps & Model Deployment | 15 | 0.600 | 0.800 | 0.723 |
| Machine Learning | 30 | 0.679 | 0.857 | 0.762 |
| NLP | 13 | 0.667 | 0.750 | 0.708 |
| Python | 14 | 1.000 | 1.000 | 1.000 |
| SQL | 18 | 0.611 | 0.944 | 0.755 |

hybrid_minilm_qk: no-answer queries n=20; top-1 score AUROC (answerable vs no-answer) = 0.921; share of no-answer queries scoring above the answerable median = 0.000

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

### minilm_qka: by category

| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |
|---|---:|---:|---:|---:|---:|
| concept_keywords | 24 | 0.917 | 1.000 | 0.951 | 0.868 |
| domain_confusing | 16 | 0.625 | 1.000 | 0.771 | 0.749 |
| multi_concept | 16 | 0.438 | 0.750 | 0.563 | 0.557 |
| no_answer | 20 | - | - | - | - |
| no_answer_intended_but_covered | 2 | - | - | - | 0.807 |
| paraphrase | 72 | 0.725 | 0.957 | 0.825 | 0.798 |
| similar_distinct | 16 | 0.867 | 1.000 | 0.922 | 0.927 |

minilm_qka: by domain

| domain | n | success@1 | success@5 | mrr@10 |
|---|---:|---:|---:|---:|
| Data Analysis | 17 | 0.706 | 0.941 | 0.811 |
| Deep Learning | 17 | 0.688 | 0.938 | 0.768 |
| Generative AI & RAG | 20 | 0.600 | 0.950 | 0.743 |
| MLOps & Model Deployment | 15 | 0.600 | 0.867 | 0.715 |
| Machine Learning | 30 | 0.893 | 0.964 | 0.923 |
| NLP | 13 | 0.833 | 1.000 | 0.903 |
| Python | 14 | 0.857 | 1.000 | 0.929 |
| SQL | 18 | 0.611 | 0.944 | 0.755 |

minilm_qka: no-answer queries n=20; top-1 score AUROC (answerable vs no-answer) = 0.990; share of no-answer queries scoring above the answerable median = 0.000

### hybrid_minilm_qka: by category

| category | n | success@1 | success@5 | mrr@10 | ndcg@5 |
|---|---:|---:|---:|---:|---:|
| concept_keywords | 24 | 1.000 | 1.000 | 1.000 | 0.919 |
| domain_confusing | 16 | 0.625 | 1.000 | 0.778 | 0.763 |
| multi_concept | 16 | 0.625 | 0.812 | 0.729 | 0.679 |
| no_answer | 20 | - | - | - | - |
| no_answer_intended_but_covered | 2 | - | - | - | 1.000 |
| paraphrase | 72 | 0.826 | 0.971 | 0.882 | 0.825 |
| similar_distinct | 16 | 0.800 | 0.933 | 0.856 | 0.862 |

hybrid_minilm_qka: by domain

| domain | n | success@1 | success@5 | mrr@10 |
|---|---:|---:|---:|---:|
| Data Analysis | 17 | 0.941 | 1.000 | 0.956 |
| Deep Learning | 17 | 0.812 | 1.000 | 0.869 |
| Generative AI & RAG | 20 | 0.850 | 0.950 | 0.897 |
| MLOps & Model Deployment | 15 | 0.533 | 0.933 | 0.711 |
| Machine Learning | 30 | 0.821 | 0.929 | 0.863 |
| NLP | 13 | 0.917 | 0.917 | 0.917 |
| Python | 14 | 0.857 | 1.000 | 0.929 |
| SQL | 18 | 0.722 | 0.944 | 0.826 |

hybrid_minilm_qka: no-answer queries n=20; top-1 score AUROC (answerable vs no-answer) = 0.939; share of no-answer queries scoring above the answerable median = 0.000
