# Stage 3C-0 — Scope pilot review report

**Status: every tier in this report was drafted by Claude (AI). No human has reviewed any of it.** "Agreement" below means agreement between two AI-produced tierings (a rule-based heuristic and Claude's reading of each question), which is *not* human validation.

## 1. What was reviewed

- **Pilot: 40 questions**, seeded sample (`random.Random(20261014)`): 5 per domain (all 8 domains), Easy 10 / Medium 15 / Hard 15, types: unspecified 16, coding 6, debugging 6, design 4, scenario 3, sql_exercise 3, evaluation 2.
- **Required risk cases included:** bubble-sort complexity (smi-0453), Python `==` vs `is` (smi-0441), SQL ROW_NUMBER vs RANK (smi-0431), concise Easy answers (smi-0198, 0064, 0118, 0335, 0234, 0375, 0449, 0427), long references (smi-h0019, h0017, h0042, h0045 …), implicit requirements (smi-0345, 0234, 0335), coding/SQL exercises (12 records).
- **Plus the 37 records** that had no essential concept under heuristic v1 (31) or v2 (27); 21 are in both, so the union is 37.
- Total manually tiered by AI: **77 records** (`tier_source` = `manual_pilot` or `manual_zero_essential`, status `ai_reviewed_pilot`). The other 589 remain `ai_heuristic_draft`.
- Method: for each record I read the question, the key-concept list, the heuristic tiers and the reference answer, then assigned each key concept to *essential*, *essential group* (any `min_required` of n), *supporting*, *background* or *label* (restates the topic). Every concept must come from the record's own `key_concepts` (or be listed as `added_concepts`); this is machine-checked.
- **Independence caveat:** the heuristic is code, but the reviewer is the same model family that designed it, in the same session. That is independent *method*, not an independent *person*. 21 reviewed rows also carry `question_read_truncated_needs_full_review` because long references were read in truncated form.

## 2. Heuristic v2 vs AI manual review (40-question pilot, 247 concepts)

| Measure | Result |
|---|---|
| Three-tier agreement (essential / supporting / background) | 141 / 247 = **57.1%** |
| Essential-vs-not agreement | 157 / 247 = **63.6%** |
| Questions where the heuristic fully agreed | **4 / 40** |
| Heuristic marked essential, review did not (penalty risk) | 45 |
| Heuristic missed an essential concept (missed requirement) | 45 |

**Conclusion:** the heuristic is not accurate enough to drive grading. It is kept only as a labelled draft (`ai_heuristic_draft`, never penalty-eligible). Observed failure modes:

1. **Answer-bearing term ranked low because the question does not repeat it.** smi-0453 "What is bubble sort and its time complexity?" → "O(n²)" was *supporting*, but it is the asked-for answer. smi-0345 `sent_tokenize`/`word_tokenize` were supporting. (Rule 4: absent wording does not mean optional.)
2. **Topic words inflated.** "NER", "CNN", "bubble sort" are label concepts that restate the question; they are now `label_concepts`, never graded separately.
3. **Trade-off costs treated as benefits.** smi-0234 "benefits of pruning": `bias` was essential; it is the cost, so it is supporting.
4. **Long design/scenario references over-tagged.** smi-h0019, g0029, k0018, l0031 had nearly everything essential; the question asks for a few things and the rest is supporting detail.
5. **Code exercises:** the function being implemented (smi-h0016 `sinusoidal positional encoding`) was background.
6. **List-type questions have no single essential concept** — "any 3 of these" is the real requirement, so they get `essential_groups`.

## 3. Risk cases

| Case | Tiering after review | Why |
|---|---|---|
| smi-0453 bubble sort | essential: bubble sort, adjacent elements, **O(n²)**; label: time complexity | Complexity value is the answer to part two. Equivalents (n^2, quadratic) listed; best-case O(n) with an early exit is an accurate extra. |
| smi-0441 `==` vs `is` | essential: value equality, identity equality; supporting: memory addresses | "Same object in memory" is one way to say identity, not a second requirement. |
| smi-0431 ROW_NUMBER vs RANK | essential: ROW_NUMBER, RANK, ties; supporting: DENSE_RANK, partition; flag `reference_broader_than_question` | DENSE_RANK is not asked; the known Qwen failure (B07) came from treating it as required. |
| Concise Easy items | essentials limited to what is asked (2–4 concepts) | A short correct answer must reach full completeness. |
| Coding / SQL (12 records) | flag `code_or_sql_exercise_graded_primarily_by_tests` | Correctness comes from running the exercise; concepts only guide feedback. |

## 4. The 37 records with no essential concept under heuristic v1/v2

Result: **none was left without requirements, and none was force-fitted.** Of 37: most are list-type, open-ended or multi-part questions, where the honest requirement is an *essential group* ("any k of n"), a few are simple definitions the heuristic mis-tiered, and one is numeric. After review, **31 keep an open ambiguity and are flagged for human review; 6 look defensible with no open ambiguity** (still AI-only).

| ID | v1 | v2 | Question (start) | Reviewed tiering | Flags | Verdict |
|---|---|---|---|---|---|---|
| smi-0001 | x | x | What is R2? What are some other metrics that could be better than R2 a… | essential: R-squared, overfitting + groups | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0015 | x | x | Given that you have wifi data in your office, how would you determine … | essential: occupancy estimation, utilisation vs capacity | open ended requirement | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0023 | x |  | How would you come up with an algorithm to detect plagiarism in online… | groups only: a scalable text-similarity method (any 2 of 5) | list type question any valid members, open ended requirement | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0024 | x | x | You have data on all purchases of customers at a grocery store. Descri… | groups only: a clustering method on customer features (any 1 of 1); a way to choose the number of clusters (any 1 of 3) | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0073 | x | x | What are some of the most used applications of Deep Learning?… | groups only: common applications of deep learning (any 3 of 4) | list type question any valid members | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0100 | x |  | What are the types of autoencoders?… | groups only: types of autoencoders (any 3 of 5) | list type question any valid members, reference broader than question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0119 |  | x | What are some advantages in using a CNN (convolutional neural network)… | essential: parameter sharing + groups | - | AI-reviewed tiering defensible; no open ambiguity flagged (still not human-verified) |
| smi-0134 | x | x | What is supervised learning?… | essential: labelled training data | - | AI-reviewed tiering defensible; no open ambiguity flagged (still not human-verified) |
| smi-0153 | x | x | What is unsupervised Learning?… | essential: unlabelled data + groups | - | AI-reviewed tiering defensible; no open ambiguity flagged (still not human-verified) |
| smi-0185 | x | x | What happens when we have correlated features in our data?… | essential: multicollinearity, coefficient instability | reference broader than question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0192 |  | x | How do you deal with sparse data (features that are mostly zeros)?… | groups only: a way to handle mostly-zero features (any 2 of 7) | ambiguous term sparse, list type question any valid members | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0223 | x | x | Which algorithms can be used for important variable selection?… | groups only: variable-selection algorithms/families (any 2 of 5) | list type question any valid members | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0229 | x |  | When can a categorical value be treated as a continuous variable and w… | essential: nominal vs ordinal, linearity assumption | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0267 | x |  | How do you handle outliers in the data?… | essential: error versus genuine outlier + groups | list type question any valid members | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0297 | x | x | How would you design a recommendation system for an e-commerce platfor… | groups only: candidate generation / ranking approach (any 2 of 4); evaluation (any 1 of 2) | open ended requirement | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0308 |  | x | How do you select important variables while working on a data set?… | groups only: variable-selection approach (any 2 of 5) | list type question any valid members | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0314 | x |  | In a normally distributed feature, values within one standard deviatio… | essential: 68-95-99.7 rule, tail probability | numeric answer | AI-reviewed tiering defensible; no open ambiguity flagged (still not human-verified) |
| smi-0339 | x | x | What do you understand by Natural Language Processing?… | essential: NLP | label is a definition | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0380 | x | x | What error metric would you use to evaluate how good a binary classifi… | groups only: a metric for balanced binary classification (any 1 of 4); a metric suited to imbalance (any 1 of 3); a multi-class averaging approach (an | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0383 | x | x | Why might it be preferable to include fewer predictors over many?… | groups only: reasons for fewer predictors (any 2 of 5) | list type question any valid members | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0391 | x |  | Given a database of all previous alumni donations to your university, … | essential: donation propensity + groups | open ended requirement | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0392 | x |  | You are Uber and you want to design a heatmap to recommend to drivers … | essential: demand forecasting, grid cells | open ended requirement | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0397 | x | x | What would be good metrics of success for an e-commerce product? A sub… | essential: free-to-paid conversion + groups | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0399 | x | x | What would be good metrics of success for a product that offered in-ap… | groups only: in-app purchase success metrics (any 2 of 5) | list type question any valid members | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0405 |  | x | How would you measure the impact that sponsored stories on Facebook Ne… | essential: randomised controlled experiment + groups | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0406 | x | x | You are on the data science team at Uber and you are asked to start th… | essential: supply-demand balance + groups | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0407 | x | x | Say that you are Netflix. How would you determine what original series… | essential: viewing behaviour + groups | open ended requirement | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0438 | x | x | How do you improve a slow query?… | essential: execution plan + groups | list type question any valid members | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-0463 | x |  | How do you use mocking in unit tests with pytest?… | groups only: a mocking mechanism in pytest (any 1 of 2) | - | AI-reviewed tiering defensible; no open ambiguity flagged (still not human-verified) |
| smi-k0001 |  | x | An invoice-extraction service forces the model to emit JSON that match… | essential: schema validity vs semantic correctness + groups | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-k0009 | x | x | A refund agent calls issue_refund(order_id, amount). Last week a tool … | essential: idempotency key, server-side authorisation, approval thresholds | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-k0016 | x |  | You must compare four candidate answer styles for a help-centre assist… | essential: pointwise vs pairwise judging, tie handling, pair-count growth | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-k0025 | x |  | Your team can LoRA fine-tune a mid-sized decoder on two GPUs, but only… | essential: frozen 4-bit base weights, step-time overhead, evaluate the deployed artefact | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-k0026 |  | x | A team has 200 high-quality human-written support replies and plans to… | essential: human-only evaluation set + groups | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-l0002 | x | x | Why does 'it works on my machine' cause more trouble in machine-learni… | essential: silent failure + groups | - | AI-reviewed tiering defensible; no open ambiguity flagged (still not human-verified) |
| smi-m0022 | x | x | You expose a risk-scoring model through a public API that returns the … | essential: membership inference, overfitting gap + groups | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |
| smi-m0035 | x | x | A recommender model passes a 5% canary and a 2-week A/B test (click-th… | essential: proxy metric, long-term holdback + groups | multi part question | AI-reviewed tiering defensible; open ambiguity → **human review** |

## 5. What this pilot does and does not show

- It shows the heuristic is unreliable (≈64% essential agreement with the AI review) and that the AI review found specific, explainable error patterns.
- It does **not** show the AI-reviewed tiers are right. The architecture review's gate for the sidecar was "≥ 90% **human** agreement on essential tiers in a sample". **That gate has not been run** because no human has reviewed a sample yet.
- The 77 reviewed rows are the only ones I would use in a prototype; 16 of them are marked penalty-eligible (reviewed, no open ambiguity).
