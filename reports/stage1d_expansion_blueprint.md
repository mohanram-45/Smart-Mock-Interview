# Stage 1D - knowledge-base expansion blueprint (12 domains)

**Status: blueprint only. No questions have been generated, no dataset file has been written, v1-v5 are untouched, no RAG work has started. Stopping for your approval before batch 1.**

## 1. Summary and what I need from you

* **Plan:** grow from 487 questions (6 domains) to about **1082** (12 domains) by adding about **595** accepted questions in **15 batches of at most 60 generated questions** (plus one optional reserve batch). The count is a planning target; the stopping rule in section 8 can end the work earlier or later. I expect the final total to land between about 1,030 and 1,120, never above 1,150.
* **Where the questions go:** 121 topic cells (appendix). The six new domains get 465 of the new questions; the existing six get 130, aimed at the gaps in `gap_analysis_v5.md`.
* **Answers:** one row per unique question with a stable ID. Optional `concise_answer`, `detailed_answer` and `practical_answer` columns are added only where each one carries real extra value. The existing `answer` column keeps working for every current consumer.
* **Delivery:** three immutable checkpoints (v6, v7, v8), each with its own manifest and fingerprint, and an approval gate after each. Previous versions are never touched.
* **Honest limits up front:** nothing can be human-verified by me. DAX cannot be executed in my environment, and AWS/Azure/LLM-tooling facts change quickly. The plan handles these with source-opening rules, hedging, time-sensitivity flags and a re-verification schedule (sections 7 and 9).

**Decisions for you** (defaults in bold; I proceed with the defaults if you just say "approved"):
1. Total target about 1,080 with a hard ceiling of 1,150 - **yes** / change.
2. Checkpoint releases v6 (batches 1-6), v7 (batches 7-12), v8 final (13-15 plus reserve) - **yes** / one release at the end.
3. Do not retrofit `concise_answer` / `practical_answer` onto the 487 v5 records in this stage - **leave v5 as is** / retrofit the 65 tier 1-2 records later.
4. Power BI content stays concept-level for licensing, capacity and limits (no prices or quotas) - **yes**.
5. Do you have a human reviewer for the tier 1-2 records (section 9)? If not, every label stays "AI-reviewed".

## 2. What v5 looks like (inspection)

* **487 records, 37 columns**, IDs `smi-NNNN` (360 seed-derived), `smi-gNNNN` (41), `smi-hNNNN` (46), `smi-iNNNN` (40). The columns are the v4 schema plus `v5_verification` and `v5_evidence_summary`.
* **Domains:** ML 174, Deep Learning 86, Data Analysis 75, SQL 54, NLP 53, Python 45. 86 topics in all.
* **Difficulty:** Easy 121, Medium 313, Hard 53. **Types:** 360 untyped seed records; coding 45, scenario 22, SQL exercise 20, concept 16, debugging 16, design 8.
* **Answers:** one `answer` text per question, median 158 words (mean 175, max 662). 146 records have an executed reference solution in `code_tests.json`; 35 cite a source. No record has had human review.
* **What the new domains already have:** almost nothing. Keyword hits in v5 questions: Spark/Kafka/Airflow/warehouse 0, AWS/Azure 1 (a false positive), Power BI/DAX/Tableau 0 real hits (7 generic "dashboard" mentions), MLOps about 6 (drift, serving, monitoring - mostly inside ML), system design 8 (older "design a recommender / spam filter" seed questions). GenAI/RAG has the most: about 12 NLP records (semantic search, RAG triage, LoRA, decoding, contamination) and a few in Deep Learning.
* **Consequence:** the six new domains are close to greenfield, so duplication risk is low there; the real duplication risk is inside GenAI/RAG versus NLP, MLOps versus ML, and system design versus ML case studies.

## 3. Domain boundaries and overlap rules

**Primary-home rule:** a question belongs to the domain whose knowledge is *needed to answer it*. When two domains apply, use the tie-break order below and record the other in `related_domains`. A record's `domain` may be revised later without changing its ID.

| Domain | In scope | Out of scope (goes to) |
|---|---|---|
| Machine Learning | classical models, evaluation, validation, leakage, calibration, feature engineering, statistical drift concepts | production lifecycle (MLOps), LLM apps (GenAI) |
| Deep Learning | training, architectures, optimisation, transformer internals, pretraining, diffusion | LLM application building (GenAI), serving infra (MLOps) |
| NLP | classical and neural text processing, parsing, tokenisation, embeddings as representations, IR basics | RAG pipelines, agents, prompt/LLM application design (GenAI) |
| Python | language, libraries, testing, packaging, performance | pipelines and Spark (Data Eng), CI/CD (MLOps) |
| SQL | relational query semantics, window functions, indexing, transactions, relational design | Spark SQL behaviour, warehouse/lakehouse design (Data Eng); DAX (BI) |
| Data Analysis | statistics, EDA, experiments, product metrics, analytical case studies | dashboard tooling and semantic models (BI), pipelines (Data Eng) |
| **Generative AI & RAG** | RAG components and failure modes, vector search, prompting, agents/tool use, LLM evaluation, fine-tune vs RAG, LLM safety and serving cost | transformer maths (DL), classical NLP (NLP), end-to-end multi-system designs (System Design) |
| **MLOps & Model Deployment** | versioning, CI/CD, registry, serving patterns, deployment strategies, feature stores, production monitoring and retraining, LLMOps | statistical theory of drift (ML), vendor-service specifics (Cloud) |
| **Data Engineering & Spark** | Spark internals and tuning, streaming, Kafka, orchestration, file/table formats, ETL/ELT, warehouse modelling, data quality | relational query theory (SQL), semantic-model design (BI), cloud service choice (Cloud) |
| **Cloud Computing (AWS/Azure)** | IAM, storage, compute, networking, managed data/ML services, reliability, cost, IaC - service-level questions | Spark behaviour (Data Eng), container/K8s concepts without a vendor (MLOps) |
| **Power BI & Business Intelligence** | semantic-model design, DAX, Power Query, storage modes, RLS, refresh/gateway, dashboard and KPI design, BI case studies | statistical analysis and experiments (Data Analysis), warehouse-side modelling (Data Eng) |
| **Applied AI System Design** | end-to-end designs with trade-offs, capacity estimates, critique, responsible-AI and reliability decisions across several components | single-component questions (their own domain) |

**Tie-break order** when a question genuinely spans domains: Applied AI System Design (only if several components must be traded off) > the most specific tool or platform domain (Power BI, Spark, Cloud) > GenAI & RAG > MLOps > the classical domains.

**Existing records stay where they are.** The ~12 GenAI-flavoured NLP records (for example smi-h0003, smi-h0004, smi-h0012, smi-g0010), the 3 drift/production ML records and the older "design a recommender" ML records keep their IDs and domains. They get `related_domains` in the new build only if you approve touching v5-derived rows; otherwise cross-references are held in a separate `cross_refs.csv`, so v5 rows remain byte-identical. New questions are checked against them as duplicates and are written to be complementary (for example decision-oriented LoRA-vs-RAG questions instead of another "what is LoRA").

## 4. Answer schema (backward compatible)

**Rule: v5 columns keep their names and meaning; new columns are appended; `answer` is always populated.**

| Column | Applies to | Rule |
|---|---|---|
| `answer` | all | unchanged. For new records it equals `detailed_answer` when that exists, otherwise the single answer. Any consumer reading v5 keeps working. |
| `concise_answer` | optional | interview-ready, at most 80 words, states the answer first. Present only if it adds value over the first paragraph of the detailed answer. |
| `detailed_answer` | optional | rigorous reference explanation, 120-450 words (longer only for derivations). |
| `practical_answer` | optional | a worked scenario, configuration, query or code that is not already in the detailed answer. If it contains code it must equal the tested solution. |
| `answer_set` | all new | `single` or a `+`-joined list such as `concise+detailed+practical`; the validator checks that exactly these fields are non-empty. |
| `rubric_points` | design / open-ended | JSON list of 4-8 acceptable key decisions with the trade-off each addresses (design answers have no single truth, so they carry a rubric instead of one "correct" text). |
| `related_domains`, `tags` | all new | secondary domains and free retrieval tags; `domain` stays the single primary. |
| `question_type` | all new | existing enum plus `evaluation` and `business_case`. |
| `time_sensitive`, `review_by` | flagged cells | `yes` plus a date (default 6 months out) for vendor, product and LLM-tooling claims. |
| `reference_solution` | coding, SQL | tested code stays in `code_tests.json` keyed by ID (language, setup, solution, test, expected); the dialect or runtime is declared (SQLite 3.37 baseline, DuckDB or PySpark where the question is about them). |
| `v6_verification`, `evidence_summary`, `remaining_limitations` | all new | same vocabulary as v5: `ai_generated+ai_reviewed[+code_executed][+source_opened]`; the word "human" is reserved for a real human review and is never written by me. |

**One question, one ID.** A question gets one row and one stable ID; its answer variants are columns of that row, never separate rows. A variant is added only when it is genuinely different in purpose: concise (recall under time pressure), detailed (rigour, edge cases, derivation), practical (apply it). The reviewer rejects a variant that only paraphrases another. I expect about 40% of new records to carry two or more answer fields and about 15-20% all three; many definitional or design records will correctly stay `single` or `detailed`.

**ID scheme:** continue the lettered batches: `smi-jNNNN` (batch 1), `smi-kNNNN` (batch 2) ... `smi-xNNNN` (batch 15), `smi-yNNNN` (reserve). IDs never encode the domain.

**Files and compatibility:** `curated_questions.csv/json` keep v5's column order and add the new ones at the end; JSON also exposes `answers: {concise, detailed, practical}` as a nested object. A RAG prototype can index each non-empty answer field as its own chunk with shared metadata (ID, domain, topic, difficulty, verification). The v6 validator is a superset of the v5 validator; v5 files validate as before.

## 5. Coverage matrix

Planning targets, not quotas. "Cell envelope" is the sum of per-cell minimum (70% of target) and maximum (120%) and is a theoretical bound, not a forecast. Full per-topic table: appendix and `data/expansion/plan/coverage_matrix.csv`.

| Domain | v5 now | Topic cells | Planned new (target) | Cell envelope (min-max) | Total at target |
|---|---:|---:|---:|---:|---:|
| Generative AI & RAG (new) | 0 | 15 | 82 | 51-104 | 82 |
| MLOps & Model Deployment (new) | 0 | 14 | 77 | 47-98 | 77 |
| Data Engineering & Spark (new) | 0 | 14 | 92 | 56-118 | 92 |
| Cloud Computing (AWS/Azure) (new) | 0 | 13 | 80 | 48-103 | 80 |
| Power BI & Business Intelligence (new) | 0 | 12 | 74 | 48-96 | 74 |
| Applied AI System Design (new) | 0 | 14 | 60 | 35-76 | 60 |
| Machine Learning | 174 | 10 | 40 | 25-51 | 214 |
| Deep Learning | 86 | 5 | 16 | 9-21 | 102 |
| NLP | 53 | 5 | 14 | 9-19 | 67 |
| Python | 45 | 7 | 22 | 12-29 | 67 |
| SQL | 54 | 5 | 14 | 8-19 | 68 |
| Data Analysis | 75 | 7 | 24 | 14-31 | 99 |
| **All 12** | **487** | **121** | **595** | 362-765 | **1082** |

**Planned question-type mix (estimate from the matrix):** scenario 173, concept 158, coding 75, debugging 70, design 47, business 37, evaluation 23, sql 11. The eight requested categories are all present: conceptual, scenario, coding, SQL exercises, debugging, system design, model evaluation and business case studies. Coding and SQL stay a minority because the earlier batches were coding-heavy; conceptual and scenario questions dominate on purpose.

**Difficulty:** assigned by the blind-auditor rule from earlier batches (Easy = single-concept recall; Medium = comparison, mechanism, short code or application; Hard = multi-step reasoning, trade-off design or subtle debugging). No ratio is forced. The validator only reports a warning if a domain ends up with fewer than 10% Hard or more than 70% Medium.

## 6. Batch-by-batch plan

Each batch generates at most 60 questions; the planning yield is 88% (so 12% are expected to be rejected as duplicates, filler or unfixable). Counts below are the accepted questions.

| Batch | Scope | Accepted (target) | Accepted (envelope) | Generate (cap 60) | Cells with executed tests | Time-sensitive cells |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Generative AI & RAG A: retrieval, chunking, evaluation | 40 | 24-50 | 46 | 3/7 | 1 |
| 2 | Generative AI & RAG B: LLM applications, agents, safety, serving | 42 | 27-54 | 48 | 2/8 | 3 |
| 3 | MLOps A: lifecycle, CI/CD, serving, deployment, feature stores | 41 | 26-53 | 47 | 2/7 | 0 |
| 4 | MLOps B: monitoring, retraining, governance, LLMOps, case studies | 36 | 21-45 | 41 | 2/7 | 2 |
| 5 | Data Engineering A: Spark core, tuning, streaming | 45 | 28-58 | 52 | 5/7 | 1 |
| 6 | Data Engineering B: pipelines, orchestration, Kafka, formats, warehouse modelling | 47 | 28-60 | 54 | 5/7 | 0 |
| 7 | Cloud A: AWS | 42 | 25-54 | 48 | 0/7 | 6 |
| 8 | Cloud B: Azure and cross-cloud | 38 | 23-49 | 44 | 1/6 | 5 |
| 9 | Power BI A: modelling, DAX, Power Query, performance | 40 | 26-51 | 46 | 0/6 | 1 |
| 10 | Power BI B: governance, service, design, KPI and BI case studies | 34 | 22-45 | 39 | 1/6 | 3 |
| 11 | Applied AI System Design A: scenario families | 36 | 21-46 | 41 | 1/9 | 2 |
| 12 | Applied AI System Design B: critique, responsibility, reliability, case studies | 24 | 14-30 | 28 | 0/5 | 1 |
| 13 | Strengthen ML and Deep Learning | 50 | 30-64 | 57 | 9/14 | 0 |
| 14 | Strengthen NLP, Python and SQL | 50 | 29-67 | 57 | 13/17 | 0 |
| 15 | Strengthen Data Analysis; ML evaluation and business case studies | 30 | 18-39 | 35 | 4/8 | 0 |
| 16 | Reserve (only if the coverage matrix shows holes, or to replace quarantined cells) | 0-40 | | 46 | | |

**Ordering logic:** highest-demand and highest-risk domains first (GenAI, MLOps, Data Engineering) while the process is fresh; Cloud and Power BI next because they need the most source opening; system design after its component domains exist (so design questions can cross-reference them); the strengthening batches last because the gap analysis is re-run on the merged set to decide whether they are still needed as written.

**Checkpoints:** v6 after batch 6 (about 735 questions), v7 after batch 12 (about 950), v8 final after batches 13-15 (about 1,080; plus reserve if used). Each checkpoint is a new directory with manifest and fingerprint, validated in the sandbox and on your machine.

## 7. Per-batch workflow and quality gates

1. **Draft:** two or three generator agents work from the batch's cells, a brief that bans templates and definitional filler, and the nearest existing questions. They produce question, answer fields, key concepts, common mistakes, code and tests, sources and an `interview_style_note`.
2. **Mechanical gates:** schema, exact and near duplicates against all 487 + earlier batches (TF-IDF word and character n-grams, 5-gram template check), answer-set rules, key-concept count, no claim of being a "real" interview question.
3. **Blind independent review:** a separate agent that has not seen the draft rationale rates difficulty blind, checks every claim, tries to break the code, and lists exact replacement text. Verdict per record: pass / correct / quarantine.
4. **Apply and re-verify:** replacements are applied by script (exact substrings, build fails on any unapplied fix). **Every corrected record gets a second independent recheck before merge** (Stage 1C found 6 of 19 still needing a fix after the first correction).
5. **Execution:** all coding, SQL, Spark, IaC-lint and arithmetic claims run in the sandbox and are recorded in `code_tests.json` and a cross-runtime results file.
6. **Sources:** I open the cited pages myself in the main session (agents often cannot fetch). A product or specification claim with no opened source is either hedged and marked `background_only` or removed. Open-ended design answers are marked as rubric-based.
7. **Quarantine:** anything unresolved after one correction cycle goes to `quarantine.csv` with the reason; nothing with an open major issue is merged.
8. **Report and stop:** a batch report (counts, defects, evidence, limitations) and a pause for your approval before the next batch.

## 8. Objective acceptance criteria and stopping rule

**A batch is accepted only if all of these hold** (measured by the validator and the batch report):

| # | Criterion | Threshold |
|---|---|---|
| 1 | Schema and ID validity, one domain per topic | 100% |
| 2 | Exact duplicate questions or answers | 0 |
| 3 | Near duplicates (TF-IDF cosine on questions / on answers) | 0 pairs >= 0.85 / >= 0.90; pairs 0.70-0.85 individually reviewed |
| 4 | Templated wording (5-gram Jaccard), repeated openers | no pair >= 0.25; no 4-word opener more than 3 times |
| 5 | Definitional openers ("What is / What are") | at most 35% of a batch |
| 6 | Independent review coverage | 100% of records; 100% of corrected records rechecked |
| 7 | Major-defect rate at first review | reported; if above 25% the batch is regenerated, not patched |
| 8 | Executable solutions | 100% of coding/SQL/Spark/IaC records have a passing test on the declared runtime; Python on 3.10, 3.11 and 3.13 |
| 9 | Source coverage | at least 70% of records in Cloud, Power BI, Data Engineering, MLOps and GenAI cite an opened source; every unsourced product-behaviour claim is hedged or removed |
| 10 | Answer-set rules | concise at most 80 words; no field that only paraphrases another; code in practical equals the tested code; variants consistent in every number |
| 11 | Difficulty and key concepts | blind-auditor difficulty adopted; 3-8 distinct key concepts discussed in the answer |
| 12 | Time-sensitive claims | flagged with `review_by`; no price, quota, version number or model name stated as current fact |
| 13 | Regression | v1-v5 manifests and original files hash-identical; earlier IDs unchanged |
| 14 | Honest labelling | no record labelled human-reviewed; limitations recorded |

**Stopping rule - stop generating when any of these is true:**
* the accepted total reaches **1,150**, or the 15 planned batches (plus reserve) are done;
* every coverage cell has reached its minimum (70% of target) **and** the gap analysis shows no checklist concept with 0-1 questions in any of the 12 domains (remaining thin cells are listed rather than padded);
* **quality stop:** two consecutive batches fall below 70% accepted-per-generated, or duplicate rejections exceed 15% of a batch, or the median nearest-neighbour similarity of new questions to existing ones exceeds 0.50 (a sign of repetition rather than new coverage);
* you tell me to stop. Shortfalls against any cell target are reported, never filled with variants.

## 9. Time, testing dependencies and maintenance

**Elapsed time (estimate, based on how Stage 1B and 1C went):** about 2-3.5 hours of agent time per batch (drafting 20-30 min, blind review 20-40 min, apply/build/validate 15-20 min, my source opening 30-60 min, recheck of corrected records 20-40 min, commit and device validation 10 min), so roughly **35-50 hours** for 15 batches, about 3-5 working days if batches run back to back, longer with your approval gates. Cloud and Power BI batches sit at the high end because they depend on opening vendor documentation. I cannot give a reliable token-cost figure; each batch is comparable to batch 03 plus the Stage 1C recheck.

**Human review (not included above):** the new records will add about 150-200 to the tier 1-2 review pool. At about 5-8 minutes per record, 65 existing + about 150 new records is roughly 18-28 hours of expert time. This is the single biggest quality lever and is optional.

**Testing dependencies - probed in the sandbox today, all install and run:** PySpark 4.2.0 on OpenJDK 21 (local[2], about 11 s start-up), DuckDB 1.5.6, sqlglot 30.21, moto 5.2.3 (mock AWS), cfn-lint 1.57, PyArrow 26, rank-bm25 0.2.2, FAISS 1.15, plus the existing Python 3.10/3.11/3.13 + numpy/pandas stack and real SQLite 3.37.2. Consequences:
* **Executable:** Spark transformations and plans, SQL dialect differences, BM25/RRF/cosine/ANN retrieval maths, IAM-policy and CloudFormation syntax, S3/IAM behaviour in the mock, capacity arithmetic. About 227 of the 595 planned questions sit in cells that include an executed test.
* **Not executable here:** DAX and Power Query M (no engine; verified against Microsoft documentation, hand-evaluated on tiny tables, pandas equivalents labelled "illustration"), real AWS/Azure behaviour (docs only; moto is a mock), LLM behaviour (never asserted as a measured fact), and design answers (24 questions are rubric-only).
* **On your machine:** Java, PySpark, DuckDB, moto, scikit-learn and PyTorch are not installed, so those tests run only in the sandbox. The validator will record their results in a committed results file and skip them locally; local validation still checks schema, duplicates, regression, fingerprint and the tests that use only the standard library, numpy and pandas.

**Maintenance burden:**
* **Time-sensitive content:** 134 planned questions sit in cells flagged time-sensitive (vendor services, licensing concepts, LLM tooling). Plan a re-verification pass on those every 6 months (about 25% of the new content, roughly 2-3 batches' worth of review, about 6-10 hours each time).
* **Dependency drift:** pinned versions recorded in each results file; Spark, pandas and numpy majors can change reference outputs, so re-run the full test set on each major upgrade.
* **Tooling:** the validator, build, gap-analysis and readiness scripts grow by about one check family per new domain; each checkpoint adds a manifest and fingerprint to keep stable.
* **Review backlog:** the human-review queue grows with every batch; unreviewed records keep their AI-only labels.

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Plausible but wrong vendor facts (limits, defaults, API behaviour) | open the doc myself; hedge or drop; time-sensitivity flag; no numeric quotas or prices |
| DAX answers cannot be run | doc check + hand-evaluated tiny tables + labelled pandas illustration; lower confidence recorded |
| GenAI facts age quickly | decision-oriented, mechanism-level questions; no model names or benchmark scores as facts |
| Same-family reviewers share blind spots | blind difficulty, break-the-code instructions, lead-opened sources, second recheck of every correction, honest AI-only labels |
| Open-ended design answers look authoritative | rubric format with trade-offs; flagged as non-unique |
| Padding to reach a count | stopping rule, per-cell minimums, quality stop, no answer variants as filler |
| RAG-vs-NLP and MLOps-vs-ML duplication | boundary table, nearest-neighbour check against all earlier records, complementary framing |

## 11. Files produced by this blueprint step

* `reports/stage1d_expansion_blueprint.md` (this document)
* `data/expansion/plan/coverage_matrix.csv` (121 cells), `batch_plan.csv`, `domain_summary.csv`, `plan.json`
* `audit/expansion/plan_stage1d.py` (regenerates the plan tables; contains no questions)

Waiting for your approval (or changes to the decisions in section 1) before generating batch 1.

## Appendix - topic coverage matrix (all 12 domains)

Verification codes: X executed test, D official documentation or paper, V derived by hand, R design rubric. "Existing v5 keyword hits" is an indicative count of v5 questions mentioning the cell's keywords, not a measure of coverage.

### Generative AI & RAG

| Cell | Topic | Batch | Target | Types | Verification | Time-sens. | Existing v5 keyword hits | Boundary / note |
|---|---|---:|---:|---|---|:--:|---:|---|
| GEN-01 | Embeddings and similarity search (metrics, normalisation, ANN: HNSW/IVF/PQ) | 1 | 6 | concept, coding, scenario | X+D |  | 15 | Embedding theory (word2vec, contextual) stays in NLP/DL; here: use for retrieval |
| GEN-02 | Chunking and document ingestion | 1 | 5 | concept, scenario, debugging | D+V |  | 2 |  |
| GEN-03 | Retrieval strategies (dense, BM25, hybrid, RRF, query rewriting, MMR) | 1 | 7 | concept, coding, scenario | X+D |  | 4 | BM25 and RRF are implemented and tested in pure Python |
| GEN-04 | Reranking and context assembly | 1 | 5 | concept, scenario | D |  | 0 |  |
| GEN-05 | RAG evaluation (recall@k, MRR, nDCG, faithfulness, golden sets, LLM judges) | 1 | 7 | evaluation, coding, concept | X+D |  | 2 | Generic IR metrics already in NLP (smi-h0003 family); new questions must be RAG-specific |
| GEN-06 | Vector databases and index operations (filters, freshness, updates, cost) | 1 | 5 | scenario, concept | D | yes | 0 | Product-specific limits are time-sensitive and avoided |
| GEN-07 | RAG failure diagnosis | 1 | 5 | debugging, scenario | V+D |  | 3 |  |
| GEN-08 | Prompting and structured output (few-shot, CoT caveats, schemas, determinism) | 2 | 5 | concept, scenario, coding | X+D | yes | 1 |  |
| GEN-09 | Tool use and agents (function calling, loops, failure modes, action guardrails) | 2 | 6 | concept, scenario, design | D | yes | 1 |  |
| GEN-10 | LLM evaluation (benchmarks, contamination, LLM-as-judge bias, regression suites) | 2 | 6 | evaluation, concept | D+V |  | 3 | smi-h0012 (contamination) stays in NLP |
| GEN-11 | Fine-tuning vs RAG vs prompting (LoRA/QLoRA, SFT, forgetting, data needs) | 2 | 6 | concept, scenario, business | D+V |  | 5 | smi-h0004 (LoRA) stays in NLP; new questions are decision-oriented |
| GEN-12 | Safety, security and privacy (prompt injection, PII, jailbreaks, red teaming) | 2 | 5 | scenario, concept, debugging | D | yes | 0 |  |
| GEN-13 | Serving, latency and cost (KV cache, batching, quantisation, caching, token budgets) | 2 | 6 | concept, coding, scenario | X+D+V |  | 3 | Training-time scaling stays in Deep Learning |
| GEN-14 | Hallucination, grounding and long context | 2 | 5 | concept, scenario | D |  | 0 |  |
| GEN-15 | GenAI product scenarios (support bot, document QA) | 2 | 3 | business, scenario | R |  | 2 |  |

### MLOps & Model Deployment

| Cell | Topic | Batch | Target | Types | Verification | Time-sens. | Existing v5 keyword hits | Boundary / note |
|---|---|---:|---:|---|---|:--:|---:|---|
| MLO-01 | ML lifecycle and reproducibility (data/model versioning, experiment tracking, environments) | 3 | 6 | concept, scenario, debugging | D+V |  | 3 |  |
| MLO-02 | CI/CD for ML (data and model tests, gating, rollback) | 3 | 6 | concept, scenario, coding | X+D |  | 1 | Generic software testing stays in Python (Testing) |
| MLO-03 | Model registry and packaging (containers, ONNX, signatures, dependency pinning) | 3 | 5 | concept, scenario | D |  | 3 |  |
| MLO-04 | Serving patterns (batch, online, streaming, REST/gRPC, autoscaling, batching) | 3 | 7 | concept, scenario, design, coding | X+D+V |  | 4 |  |
| MLO-05 | Deployment strategies (shadow, canary, A/B, blue-green, rollback) | 3 | 6 | scenario, concept, evaluation | D+V |  | 4 | Experiment statistics stay in Data Analysis |
| MLO-06 | Containers and orchestration for ML (Docker, Kubernetes basics, GPU scheduling) | 3 | 5 | concept, scenario, debugging | D |  | 0 | Cloud-vendor managed services belong to Cloud |
| MLO-07 | Feature stores and training-serving skew | 3 | 6 | concept, scenario, debugging | V+D |  | 2 |  |
| MLO-08 | Production monitoring and drift operations (PSI/KS, delayed labels, alert design) | 4 | 7 | scenario, evaluation, coding | X+V |  | 3 | Drift statistics already in ML (3 records); new ones are operational |
| MLO-09 | Retraining and automation (triggers, continuous training, champion/challenger) | 4 | 5 | scenario, concept | V+D |  | 3 |  |
| MLO-10 | Data and model validation (schema checks, slice metrics, expectations) | 4 | 5 | coding, debugging, concept | X |  | 13 |  |
| MLO-11 | Governance, lineage and compliance (model cards, audit trails) | 4 | 4 | concept, scenario | D | yes | 0 |  |
| MLO-12 | Reliability, SLOs, incidents and cost | 4 | 5 | scenario, business | V |  | 12 |  |
| MLO-13 | LLMOps specifics (prompt versioning, eval gates, token cost) | 4 | 4 | scenario, concept | D | yes | 0 |  |
| MLO-14 | MLOps case studies and debugging | 4 | 6 | debugging, business, scenario | V |  | 3 |  |

### Data Engineering & Spark

| Cell | Topic | Batch | Target | Types | Verification | Time-sens. | Existing v5 keyword hits | Boundary / note |
|---|---|---:|---:|---|---|:--:|---:|---|
| DEN-01 | Spark architecture (driver, executors, DAG, stages, lazy evaluation) | 5 | 6 | concept, scenario | D+X |  | 0 |  |
| DEN-02 | Partitioning, shuffles and joins (broadcast, sort-merge, skew, salting, AQE) | 5 | 8 | coding, scenario, debugging | X+D |  | 7 | SQL-engine partitioning (smi SQL 'Partitioning and scaling') stays in SQL |
| DEN-03 | DataFrame and Spark SQL API (windows, UDF vs built-in, pandas UDF, nulls) | 5 | 8 | coding, concept | X+D |  | 6 | pandas DataFrame questions stay in Python |
| DEN-04 | Performance tuning and memory (caching, spill, file sizes, config) | 5 | 7 | scenario, debugging, concept | D+V |  | 1 |  |
| DEN-05 | Structured Streaming (watermarks, triggers, state, exactly-once) | 5 | 6 | concept, scenario, coding | X+D |  | 0 |  |
| DEN-06 | Spark debugging scenarios (OOM, skew, slow stage) | 5 | 6 | debugging, scenario | X+V |  | 2 |  |
| DEN-07 | Table formats and lakehouse basics (Delta, Iceberg, ACID on files) | 5 | 4 | concept, scenario | D | yes | 0 |  |
| DEN-08 | Batch ETL/ELT design (idempotency, incremental loads, backfills, late data) | 6 | 7 | scenario, design, coding | X+V |  | 1 |  |
| DEN-09 | Orchestration (Airflow concepts: DAGs, retries, sensors, idempotent tasks) | 6 | 6 | concept, debugging, coding | X+D |  | 0 |  |
| DEN-10 | Streaming and messaging (Kafka partitions, consumer groups, delivery semantics, ordering) | 6 | 7 | concept, scenario, debugging | D+V |  | 0 |  |
| DEN-11 | File formats and storage layout (Parquet/ORC/Avro, partition layout, compaction, schema evolution) | 6 | 7 | concept, scenario, coding | X+D |  | 2 |  |
| DEN-12 | Warehouse modelling (star/snowflake, SCD types, dbt-style transformations) | 6 | 7 | sql, concept, scenario | X+V |  | 0 | Relational design/normalisation stays in SQL; BI-tool modelling goes to Power BI & BI |
| DEN-13 | Data quality, contracts and observability | 6 | 5 | concept, scenario, coding | X+D |  | 0 |  |
| DEN-14 | CDC and integration patterns; pipeline case studies | 6 | 8 | scenario, business, debugging | V |  | 0 |  |

### Cloud Computing (AWS/Azure)

| Cell | Topic | Batch | Target | Types | Verification | Time-sens. | Existing v5 keyword hits | Boundary / note |
|---|---|---:|---:|---|---|:--:|---:|---|
| CLD-01 | AWS identity and security (IAM roles vs users, policy evaluation, least privilege, STS) | 7 | 7 | concept, scenario, debugging | D+V | yes | 0 | Policy JSON syntax validated offline; evaluation logic checked against docs |
| CLD-02 | AWS storage and databases (S3 classes/lifecycle, EBS/EFS, RDS vs DynamoDB, Redshift) | 7 | 7 | concept, scenario | D | yes | 0 |  |
| CLD-03 | AWS compute (EC2 purchase options, autoscaling, Lambda limits, ECS/EKS/Fargate) | 7 | 7 | concept, scenario, design | D | yes | 1 | Container/K8s concepts live in MLOps; here: service choice and limits |
| CLD-04 | AWS networking (VPC, subnets, security groups vs NACLs, endpoints, load balancers) | 7 | 6 | concept, debugging, scenario | D+V |  | 0 |  |
| CLD-05 | Data and ML on AWS (Glue, EMR, Athena, Kinesis, SageMaker, Bedrock) | 7 | 7 | scenario, design, concept | D | yes | 0 | Spark internals stay in Data Engineering |
| CLD-06 | Reliability, cost and observability on AWS (multi-AZ, DR, CloudWatch, cost levers) | 7 | 5 | scenario, business | D+V | yes | 0 |  |
| CLD-07 | AWS scenario questions | 7 | 3 | scenario, business | D | yes | 1 |  |
| CLD-08 | Azure identity and security (Entra ID, RBAC, managed identity, Key Vault) | 8 | 6 | concept, scenario | D | yes | 1 |  |
| CLD-09 | Azure storage and data services (Blob/ADLS, Cosmos DB, SQL Database, Data Factory, Synapse/Fabric basics) | 8 | 7 | concept, scenario | D | yes | 0 |  |
| CLD-10 | Azure compute and containers (VMs, Functions, AKS, App Service, Container Apps) | 8 | 5 | concept, scenario | D | yes | 4 |  |
| CLD-11 | Azure ML and AI services (Azure ML, Azure OpenAI, AI Search, managed endpoints) | 8 | 6 | scenario, design | D | yes | 0 |  |
| CLD-12 | Cross-cloud concepts (AWS/Azure mapping, shared responsibility, regions/AZs, IaC) | 8 | 7 | concept, scenario, coding | X+D |  | 0 | IaC snippets linted offline (cfn-lint / terraform validate where possible) |
| CLD-13 | Cloud architecture trade-offs, cost and case studies | 8 | 7 | business, design, scenario | D+V | yes | 0 |  |

### Power BI & Business Intelligence

| Cell | Topic | Batch | Target | Types | Verification | Time-sens. | Existing v5 keyword hits | Boundary / note |
|---|---|---:|---:|---|---|:--:|---:|---|
| BIZ-01 | BI data modelling (star schema, grain, relationships, cardinality, filter direction, role-playing dimensions) | 9 | 8 | concept, scenario, debugging | D+V |  | 0 | Warehouse-side modelling stays in Data Engineering; here: semantic-model design |
| BIZ-02 | DAX fundamentals (row vs filter context, CALCULATE, measures vs columns, iterators, context transition) | 9 | 9 | concept, coding, debugging | D+V |  | 1 | DAX cannot be run locally: verified against Microsoft docs and hand-evaluated on tiny tables; pandas equivalents are labelled illustration only |
| BIZ-03 | Time intelligence and DAX patterns (YTD, rolling, prior period, % of total, ranking) | 9 | 6 | coding, scenario | D+V |  | 0 |  |
| BIZ-04 | Power Query / M and data preparation (query folding, merges, incremental refresh) | 9 | 6 | concept, scenario, debugging | D |  | 0 |  |
| BIZ-05 | Storage modes and performance (Import, DirectQuery, composite, aggregations, VertiPaq, Performance Analyzer) | 9 | 6 | concept, scenario, debugging | D | yes | 0 |  |
| BIZ-06 | Power BI debugging scenarios (wrong totals, blank results, slow reports) | 9 | 5 | debugging | V+D |  | 1 |  |
| BIZ-07 | Security and governance (RLS/OLS, workspaces, sensitivity labels, certified datasets, deployment pipelines) | 10 | 6 | concept, scenario | D | yes | 0 |  |
| BIZ-08 | Service operations (gateways, refresh, dataflows, capacity and licensing concepts) | 10 | 6 | scenario, concept | D | yes | 0 | Licensing and limits change often: concepts only, no price or quota numbers |
| BIZ-09 | Visualisation and dashboard design (chart choice, drill-through, accessibility, cognitive load) | 10 | 6 | concept, scenario, business | V+D |  | 0 | Statistical communication stays in Data Analysis |
| BIZ-10 | KPI and metric design (definitions, metric trees, leading vs lagging, storytelling) | 10 | 6 | business, concept | V |  | 0 | Product metrics and A/B stay in Data Analysis |
| BIZ-11 | BI business case studies (sales, finance variance, operations SLA) | 10 | 6 | business, sql, coding | X+V |  | 7 | SQL parts are executed; DAX parts hand-evaluated |
| BIZ-12 | BI tool landscape and self-service vs governed analytics | 10 | 4 | concept, business | D | yes | 0 |  |

### Applied AI System Design

| Cell | Topic | Batch | Target | Types | Verification | Time-sens. | Existing v5 keyword hits | Boundary / note |
|---|---|---:|---:|---|---|:--:|---:|---|
| ASD-01 | Recommendation and ranking systems end to end | 11 | 6 | design, evaluation | R+V |  | 8 | Model theory stays in ML (Recommender systems, 11 records) |
| ASD-02 | Enterprise search and RAG platform design | 11 | 4 | design, scenario | R | yes | 6 | Component questions stay in GenAI & RAG; here: multi-component trade-offs |
| ASD-03 | Fraud and anomaly detection with real-time scoring | 11 | 5 | design, scenario, evaluation | R+V |  | 4 |  |
| ASD-04 | ML platform: feature store, training infrastructure, model lifecycle | 11 | 4 | design | R |  | 1 |  |
| ASD-05 | Batch vs real-time prediction architectures and latency budgets | 11 | 4 | design, scenario | R+V |  | 0 |  |
| ASD-06 | LLM assistant or agent platform with guardrails and cost control | 11 | 4 | design, scenario | R | yes | 3 |  |
| ASD-07 | Forecasting and demand planning pipeline | 11 | 3 | design, business | R+V |  | 0 |  |
| ASD-08 | Document and vision AI pipelines (OCR, classification, human in the loop) | 11 | 3 | design, scenario | R |  | 9 |  |
| ASD-09 | Capacity estimation (QPS, storage, GPU, cost) | 11 | 3 | design, coding | X+V |  | 1 | Back-of-envelope arithmetic is computed and tested |
| ASD-10 | Design critique and trade-off review | 12 | 6 | design, scenario | R |  | 4 |  |
| ASD-11 | Responsible AI, privacy and compliance in design | 12 | 4 | design, scenario | R+D | yes | 0 |  |
| ASD-12 | Failure modes, rollout plans and reliability | 12 | 4 | design, debugging | R+V |  | 1 |  |
| ASD-13 | Cross-domain business case studies (ROI, build vs buy, KPI linkage) | 12 | 5 | business, design | R+V |  | 0 |  |
| ASD-14 | Incident retrospectives and design debugging | 12 | 5 | debugging, design | R+V |  | 0 |  |

### Machine Learning

| Cell | Topic | Batch | Target | Types | Verification | Time-sens. | Existing v5 keyword hits | Boundary / note |
|---|---|---:|---:|---|---|:--:|---:|---|
| ML-01 | Missing data and outliers | 13 | 5 | concept, scenario, coding | X+V |  | 6 | gap: 1 question in v4 |
| ML-02 | Time-series forecasting (stationarity, ARIMA, validation, leakage) | 13 | 5 | concept, scenario, coding | X+V |  | 2 | gap |
| ML-03 | Interpretability (SHAP, LIME, PDP, permutation importance) | 13 | 5 | concept, scenario, coding | X+D |  | 5 | gap: 0 |
| ML-04 | Anomaly detection | 13 | 4 | concept, scenario, coding | X+V |  | 0 | gap: 0 |
| ML-05 | Reinforcement learning basics | 13 | 3 | concept, scenario | V+D |  | 0 | gap |
| ML-06 | Semi- and self-supervised learning | 13 | 3 | concept, scenario | D |  | 0 | gap |
| ML-07 | Hyperparameter tuning (random, Bayesian, early stopping) | 13 | 3 | concept, scenario, coding | X+D |  | 4 | thin |
| ML-08 | Class imbalance | 13 | 3 | scenario, coding, evaluation | X+V |  | 4 | thin |
| ML-09 | Optimisation: gradient descent variants and learning rates | 13 | 3 | concept, coding | X+V |  | 13 | thin |
| ML-10 | Model evaluation and business case studies (cost-sensitive thresholds, metric choice, uplift) | 15 | 6 | evaluation, business, scenario | X+V |  | 8 | Production monitoring goes to MLOps |

### Deep Learning

| Cell | Topic | Batch | Target | Types | Verification | Time-sens. | Existing v5 keyword hits | Boundary / note |
|---|---|---:|---:|---|---|:--:|---:|---|
| DL-01 | Backpropagation and the chain rule | 13 | 3 | concept, coding, debugging | X+V |  | 1 | gap |
| DL-02 | Framework autograd and training loops (PyTorch) | 13 | 4 | coding, debugging | X+D |  | 0 | gap; PyTorch not installed on the owner's machine: sandbox-only tests |
| DL-03 | Diffusion and LLM pretraining fundamentals | 13 | 4 | concept, evaluation | D+V |  | 1 | gap |
| DL-04 | Optimisers, normalisation and regularisation tail topics | 13 | 3 | concept, debugging | V+D |  | 5 | thin |
| DL-05 | Transfer learning and learning-curve diagnosis | 13 | 2 | scenario, debugging | V |  | 1 | thin |

### NLP

| Cell | Topic | Batch | Target | Types | Verification | Time-sens. | Existing v5 keyword hits | Boundary / note |
|---|---|---:|---:|---|---|:--:|---:|---|
| NLP-01 | Machine translation and seq2seq | 14 | 3 | concept, evaluation | D+V |  | 1 | gap |
| NLP-02 | OOV, multilingual and low-resource text | 14 | 3 | concept, scenario | D+V |  | 0 | gap |
| NLP-03 | Summarisation and question answering | 14 | 3 | concept, evaluation | D+V |  | 1 | thin |
| NLP-04 | Topic modelling and language-model evaluation | 14 | 2 | concept, coding | X+V |  | 3 | thin |
| NLP-05 | Subword tokenisation and embeddings | 14 | 3 | concept, coding | X+D |  | 4 | thin |

### Python

| Cell | Topic | Batch | Target | Types | Verification | Time-sens. | Existing v5 keyword hits | Boundary / note |
|---|---|---:|---:|---|---|:--:|---:|---|
| PY-01 | Profiling and optimisation | 14 | 4 | coding, debugging | X |  | 0 | gap |
| PY-02 | Plotting (matplotlib, seaborn) | 14 | 3 | coding, debugging | X |  | 3 | gap |
| PY-03 | Typing, dataclasses and design | 14 | 3 | concept, coding | X+D |  | 0 | thin |
| PY-04 | Testing (pytest, fixtures, mocking) | 14 | 4 | coding, debugging | X |  | 1 | thin; pytest not on owner's machine: tests use stdlib unittest where possible |
| PY-05 | pandas and NumPy operations | 14 | 4 | coding, debugging | X |  | 29 | thin |
| PY-06 | Concurrency (GIL, threads, processes, asyncio) | 14 | 2 | concept, debugging | X+D |  | 1 | thin |
| PY-07 | Packaging and command-line tools | 14 | 2 | concept, coding | X+D |  | 1 |  |

### SQL

| Cell | Topic | Batch | Target | Types | Verification | Time-sens. | Existing v5 keyword hits | Boundary / note |
|---|---|---:|---:|---|---|:--:|---:|---|
| SQL-01 | CASE, conditional aggregation and pivoting | 14 | 4 | sql, concept | X |  | 3 | gap |
| SQL-02 | ACID, isolation levels and deadlocks | 14 | 3 | concept, scenario, debugging | D+V |  | 2 | thin |
| SQL-03 | Views, stored procedures and triggers | 14 | 2 | concept, sql | X+D |  | 4 | thin |
| SQL-04 | Recursive CTEs and hierarchies | 14 | 3 | sql, debugging | X |  | 3 |  |
| SQL-05 | Query planning and optimisation | 14 | 2 | scenario, sql | X+D |  | 84 |  |

### Data Analysis

| Cell | Topic | Batch | Target | Types | Verification | Time-sens. | Existing v5 keyword hits | Boundary / note |
|---|---|---:|---:|---|---|:--:|---:|---|
| DA-01 | EDA and visualisation choices | 15 | 5 | concept, scenario, business | V |  | 0 | gap |
| DA-02 | Cohort, funnel and retention analysis | 15 | 4 | scenario, sql, business | X+V |  | 4 | gap |
| DA-03 | Sampling and bias | 15 | 3 | concept, scenario | V+D |  | 4 | thin |
| DA-04 | Outlier handling in analysis | 15 | 2 | concept, scenario | V |  | 3 | thin |
| DA-05 | Regression for analysis and interpretation | 15 | 3 | concept, coding, evaluation | X+V |  | 7 | thin |
| DA-06 | Time-series and seasonality analysis | 15 | 3 | concept, coding | X+V |  | 2 | thin |
| DA-07 | Communicating findings; analytical business cases | 15 | 4 | business, scenario | V |  | 9 | thin |

