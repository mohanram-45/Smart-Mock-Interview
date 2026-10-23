# Stage 3C-0 — Remaining ambiguous requirements

Generated from `data/evaluation/scope/scope_v1.jsonl`. Everything here is AI-drafted; **no item has been human-verified**.

## 1. Counts

- Rows flagged `human_review_required`: **400 / 666** (manual reviewed rows: 61 of 77; heuristic drafts: 339 of 589).
- Rows eligible for automatic completeness penalties (`completeness_penalty_eligible`): **16**. All other rows may report a missing essential concept but must not lower the score automatically.
- Heuristic drafts not flagged (250) are still unreviewed drafts, not approved; they are simply lower-risk by the flag rules.

## 2. Flag meanings and counts

| Flag | Rows | Meaning |
|---|---|---|
| `long_reference` | 251 | reference >250 words; essentials may be a small part of it |
| `multi_part_question` | 144 | several things asked; each part needs its own requirement |
| `code_or_sql_exercise` | 112 | graded mostly by running code; concepts only guide feedback |
| `open_ended_design_or_scenario` | 108 | many valid designs; essentials are hard to fix |
| `many_concepts_few_essential` | 43 | heuristic found few essentials among many concepts |
| `all_essential_suspicious` | 38 | heuristic made (nearly) everything essential |
| `question_read_truncated_needs_full_review` | 21 | AI read the question/reference in truncated form during manual review |
| `list_type_question_any_valid_members` | 14 | any k valid members satisfy the question |
| `code_or_sql_exercise_graded_primarily_by_tests` | 12 | code/SQL exercise, reviewed; run tests for correctness |
| `open_ended_requirement` | 9 | several valid answers |
| `reference_broader_than_question` | 3 | reference covers more than was asked |
| `label_is_a_definition` | 2 | concept is only a restatement of the question topic |
| `ambiguous_term_sparse` | 1 | question wording too sparse to fix scope |
| `numeric_answer` | 1 | answer is a value with equivalent forms |

## 3. AI-reviewed rows (77) that still need a human decision

| ID | Type | Flags | AI note |
|---|---|---|---|
| smi-0001 | unspecified | multi_part_question | Two-part question: define R2 and say why/which metrics are better. 'Overfitting' is the 'why' (R2 never falls when predictors are added). Any one well-reasoned alternativ |
| smi-0015 | unspecified | open_ended_requirement | Open case question; the core is estimating usage per room and comparing it with capacity. Privacy is good practice but not asked. |
| smi-0020 | unspecified | open_ended_requirement | Open modelling question; Monte Carlo is one valid way to evaluate aim points. |
| smi-0023 | unspecified | list_type_question_any_valid_members, open_ended_requirement | Algorithm-design question; several valid families. Needs a human decision on the minimum acceptable depth. |
| smi-0024 | unspecified | multi_part_question | The first group lists k-means only because the key-concept list does; any reasonable clustering algorithm should satisfy it (flag for the verifier). |
| smi-0073 | unspecified | list_type_question_any_valid_members | Easy list question; any three valid applications are enough. Architectures are supporting. |
| smi-0100 | unspecified | list_type_question_any_valid_members, reference_broader_than_question | The reference itself says there is no canonical list; 3 of 5 is a judgement call that should be confirmed by a human. |
| smi-0185 | unspecified | reference_broader_than_question | The question asks what happens, not remedies; remedies are background. The reference says effects depend on the model. |
| smi-0192 | unspecified | ambiguous_term_sparse, list_type_question_any_valid_members | 'Sparse' can mean mostly zeros or missing values; the reference only covers mostly zeros. An answer on missing-value imputation should be flagged for review, not marked w |
| smi-0223 | unspecified | list_type_question_any_valid_members | Easy list question; naming families or concrete algorithms both count. |
| smi-0229 | unspecified | multi_part_question | Two-part: when (ordinal, roughly equal gaps) and what effect (assumes linear spacing). One-hot and trees are context. |
| smi-0234 | unspecified | list_type_question_any_valid_members | 'Bias' is the trade-off cost, not a benefit; heuristic made it essential. |
| smi-0267 | unspecified | list_type_question_any_valid_members | - |
| smi-0297 | unspecified | open_ended_requirement | Hard open design question; there is no single required component. Human review needed before any scoring of design answers. |
| smi-0308 | unspecified | list_type_question_any_valid_members | - |
| smi-0335 | unspecified | list_type_question_any_valid_members | - |
| smi-0339 | unspecified | label_is_a_definition | 'NLP' as a key concept means 'the field of enabling computers to process human language' (definition-level match). Task examples are supporting only. |
| smi-0375 | unspecified | label_is_a_definition | - |
| smi-0380 | unspecified | multi_part_question | Three-part question; each part has its own group (groups may overlap). |
| smi-0383 | unspecified | list_type_question_any_valid_members | - |
| smi-0386 | unspecified | list_type_question_any_valid_members, open_ended_requirement | - |
| smi-0391 | unspecified | open_ended_requirement | Essential idea = framing as a propensity (classification) problem; safeguards are expected in a good answer but any one suffices here. |
| smi-0392 | unspecified | open_ended_requirement | - |
| smi-0397 | unspecified | multi_part_question | - |
| smi-0398 | unspecified | list_type_question_any_valid_members, multi_part_question | - |
| smi-0399 | unspecified | list_type_question_any_valid_members | - |
| smi-0405 | unspecified | multi_part_question | - |
| smi-0406 | unspecified | multi_part_question | - |
| smi-0407 | unspecified | open_ended_requirement | - |
| smi-0431 | unspecified | reference_broader_than_question | The question names only ROW_NUMBER and RANK; the reference also covers DENSE_RANK. This is the known B07 case. |
| smi-0438 | unspecified | list_type_question_any_valid_members | Hard SQL question where 'measure first' (execution plan) is the key idea; any two concrete fixes are acceptable. |
| smi-g0014 | debugging | code_or_sql_exercise_graded_primarily_by_tests, multi_part_question | Heuristic made negation handling background although the question is about it. |
| smi-g0029 | sql_exercise | code_or_sql_exercise_graded_primarily_by_tests, question_read_truncated_needs_full_review | - |
| smi-g0030 | sql_exercise | code_or_sql_exercise_graded_primarily_by_tests, multi_part_question, question_read_truncated_needs_full_review | - |
| smi-g0034 | sql_exercise | code_or_sql_exercise_graded_primarily_by_tests, multi_part_question, question_read_truncated_needs_full_review | Unsure whether the censored-cohort handling is demanded by the sample data; human check. |
| smi-h0002 | coding | code_or_sql_exercise_graded_primarily_by_tests, multi_part_question, question_read_truncated_needs_full_review | - |
| smi-h0003 | debugging | multi_part_question, question_read_truncated_needs_full_review | - |
| smi-h0017 | coding | code_or_sql_exercise_graded_primarily_by_tests, question_read_truncated_needs_full_review | - |
| smi-h0019 | scenario | question_read_truncated_needs_full_review | Question asks for concrete values; the other items are supporting detail. Heuristic marked all six essential. |
| smi-h0034 | debugging | code_or_sql_exercise_graded_primarily_by_tests, multi_part_question | - |
| smi-h0042 | coding | code_or_sql_exercise_graded_primarily_by_tests, question_read_truncated_needs_full_review | Definitions are specified in the question, so they are essential; unsure which of denominator/censoring is stated verbatim - human check. |
| smi-h0045 | coding | code_or_sql_exercise_graded_primarily_by_tests, question_read_truncated_needs_full_review | Coding exercise: correctness is checked by the record's code tests where available; concepts only guide feedback. |
| smi-i0006 | design | question_read_truncated_needs_full_review | - |
| smi-i0009 | debugging | multi_part_question, question_read_truncated_needs_full_review | - |
| smi-j0011 | debugging | question_read_truncated_needs_full_review | - |
| smi-k0001 | scenario | multi_part_question | - |
| smi-k0003 | scenario | question_read_truncated_needs_full_review | - |
| smi-k0009 | design | multi_part_question | Question asks for duplicate prevention, unauthorised-refund prevention and where a human sits; one essential per ask. |
| smi-k0015 | evaluation | multi_part_question, question_read_truncated_needs_full_review | - |
| smi-k0016 | evaluation | multi_part_question | Asks: scale choice, ties/inconsistency, cost. Position/length bias are expected evidence for inconsistency but any valid treatment counts. |
| smi-k0017 | evaluation | question_read_truncated_needs_full_review | Counts are given, so computing kappa is essential; heuristic ranked it supporting and imbalance background. |
| smi-k0018 | scenario | multi_part_question, question_read_truncated_needs_full_review | - |
| smi-k0025 | concept | multi_part_question | - |
| smi-k0026 | design | multi_part_question | - |
| smi-l0006 | design | question_read_truncated_needs_full_review | - |
| smi-l0031 | design | multi_part_question, question_read_truncated_needs_full_review | - |
| smi-l0045 | coding | code_or_sql_exercise_graded_primarily_by_tests, question_read_truncated_needs_full_review | - |
| smi-m0002 | debugging | multi_part_question, question_read_truncated_needs_full_review | - |
| smi-m0018 | design | open_ended_requirement, question_read_truncated_needs_full_review | Essentials follow the four weaknesses listed in the scenario; confirm with the full question. |
| smi-m0022 | scenario | multi_part_question | - |
| smi-m0035 | scenario | multi_part_question | - |

## 4. Questions a human must decide (cross-cutting)

1. **Minimum depth for list/open questions** (e.g. smi-0023, smi-0100, smi-0386): how many valid members, and how detailed, satisfy `min_required`?
2. **Multi-part questions**: confirm every part is a separate requirement (smi-0001, smi-0024, smi-0380, smi-k0001, smi-k0009, smi-m0022).
3. **Ambiguous subject** (smi-0234 tree vs neural-network pruning; smi-0339 how deep an NLP definition must be).
4. **Reference broader than question** (smi-0431 DENSE_RANK; smi-0441 memory addresses): confirm they are supporting.
5. **Long references read in truncated form** (21 reviewed rows flagged `question_read_truncated_needs_full_review`).
6. **Code/SQL exercises**: confirm the policy that correctness comes from executed tests and concepts only drive feedback.
7. **All 589 heuristic drafts**: the pilot found only 64% essential/non-essential agreement with the AI manual review, so none should drive a score penalty until sampled and approved.
