# Unresolved issues

## 1. FIX records with no proposed text

* **3636** (needs_review, low): Given position data of NBA players in a season’s games, how would you evaluate a basketball player’s defensive  - answer only restates the question
* **3834** (needs_source, low): List the advantages and limitations of the Temporal Difference Learning Method.  - niche RL topic; claims such as 'works in continuous environments' and 'sensitive to initialization' need a source
* **3967** (needs_code_test, low): How to check word similarity using the spacy package?  - asks how with spaCy; answer gives no code; needs a model with word vectors; similarity is cosine and can be negative
* **4075** (needs_code_test, low): How do you create a simple REST API using Flask?  - answer contains no code; web development is outside the six interview domains
* **4077** (needs_review, low): Implement JWT authentication in a Flask API.  - asks for an implementation; answer only defines JWT. Authentication code is security-sensitive and not verified here; outside the six interview domains
* **4081** (needs_code_test, low): How do you use mocking in unit tests with pytest?  - answer is a definition; no pytest example. pytest is not installed in the audit sandbox, so no example could be executed

## 2. Technically uncertain proposals (not auto-approved)

All records in state `needs_review` (30), in particular: 3803 (correlated features), 3809 (global minimum / domain), 3810 (sparse data), 3813 (dimensionality reduction before SVM), 3858 (item-based CF), 3871 (XGBoost vs SVM), 3961 (semantic analysis), 3985 (NLTK vs spaCy), 3988 (pragmatic ambiguity), 3973/3974 (reconstructed from general knowledge because the tables are missing), 3965 (stemmer output verified with NLTK; wording needs a reviewer).

## 3. Judgement calls you may want to overrule

* LOW_RELEVANCE exclusions: 3624, 3650, 3656, 3668, 3675, 3686, 3694, 3698, 3708, 3719, 3723, 3732, 3743, 3830, 3907, 3930, 3971, 4003, 4006, 4011, 4021, 4027.
* Legacy-topic exclusions (Boltzmann machines, DBN framing, TensorFlow 1.x): 3675, 3708, 3719, 3723, 3732.
* Open-ended case questions kept with THIN_ANSWER (4002-4025 range): the questions are classic but the answers are one-line outlines; they will not support grounded answers.
* Behavioural / company-specific questions (3915-3917) excluded or rewritten.

## 4. Process issues

* 4 duplicate links point to an excluded record, so no canonical survivor exists for those clusters: 3657->3725, 3658->3726, 3686->3723, 3708->3675.
* Duplicate detection among seed records used my reading plus the turn-1 TF-IDF audit; a final pass over KEEP+FIX pairs after approval is recommended (e.g. overlaps between 3794/3864/4000-type regularisation items, 3779/3944, 3939 and the DL SGD item).
* 15 KEEP records still carry "Ans."/"Solution:" prefixes.
* Domain labels: 15 proposed domain moves; the pipeline maps raw PREDICTIVE_MODELLING to ML, so moves require a mapping decision.
* Difficulty labels for the whole set remain unreliable: the pipeline rebalance rewrites 44% of them; proposed difficulties are reviewer judgement and unvalidated.
* The rebalanced difficulty and the Siamese baseline were trained on template pairs; no model was retrained or re-evaluated here.

## 5. Not done (by design)

* No original file or production code was modified; no model retrained; no FAISS/RAG work; no new questions generated.