# Windows evidence vs current code, case by case (10L)

**Evidence labels.** `Windows run 1/2` = real llama3.2:3b on the user's machine (frozen files). `re-scored` = the same recorded behaviour under the corrected formula (no new model call). `scripted` = a rule-based stand-in model on the current code (mechanics only). `replay` = recorded questions through the current rules (not a model run).

- Windows run 1 (prompt 10.fu4): **12/23** useful+valid
- Windows run 2 (prompt 10.fu5), as reported: **11/23**; by class {'expected': '11/16', 'skip': '11/11', 'memory_use': '0/7', 'memory_inappropriate': '6/6'}
- Windows run 2 re-scored with the corrected formula: **11/23 = 47.8%**; technical expected [7, 12], behavioural scripted probes [4, 4], grounded memory use [0, 7]; strict skip 10/10 plus safety-only ['B07']
- Current code with the scripted stand-in: 23/23 (**mechanics only**)
- **80% target on a real model for the current code: NOT MEASURED.** Windows verification is outstanding.

| case | class | run 1 | run 2 reported | run 2 re-scored | scripted now | run 2 outcome / reasons |
|---|---|---|---|---|---|---|
| T01 | expected | ok | ok | ok | ok | llm  |
| T02 | expected | MISS | MISS | MISS | ok | fallback ['question:concept_already_in_answer'] |
| T03 | expected | MISS | MISS | MISS | ok | fallback ['question:concept_already_in_answer', 'question:not_tied_to_answer'] |
| T04 | expected | ok | ok | ok | ok | llm  |
| T05 | expected | MISS | ok | ok | ok | llm  |
| T06 | expected | MISS | ok | ok | ok | llm  |
| T07 | expected | MISS | MISS | MISS | ok | skip  |
| T08 | expected | MISS | ok | ok | ok | llm  |
| T09 | expected | ok | MISS | MISS | ok | fallback ['question:restates_answer', 'evidence:none_verified'] |
| T10 | expected | MISS | MISS | MISS | ok | fallback ['question:repeats_earlier', 'question:concept_already_in_answer', 'question:not_tied_to_answer', 'question:restates_answer'] |
| T11 | expected | ok | ok | ok | ok | llm  |
| T12 | expected | MISS | ok | ok | ok | llm  |
| S01 | skip | MISS | ok | ok | ok | skip  |
| S02 | skip | MISS | ok | ok | ok | skip  |
| S03 | skip | MISS | ok | ok | ok | skip  |
| S04 | skip | ok | ok | ok | ok | skip  |
| S05 | skip | ok | ok | ok | ok | fallback ['answer_unrelated_to_question'] |
| S06 | skip | ok | ok | ok | ok | fallback ['answer_unrelated_to_question'] |
| S07 | skip | ok | ok | ok | ok | fallback ['answer_looks_like_instructions'] |
| S08 | skip | ok | ok | ok | ok | skip  |
| M01 | memory_use | ok | MISS | MISS | ok | llm  |
| M02 | memory_use | MISS | MISS | MISS | ok | fallback ['question:repeats_earlier'] |
| M03 | memory_use | ok | MISS | MISS | ok | llm  |
| M04 | memory_use | MISS | MISS | MISS | ok | fallback ['question:concept_already_in_answer'] |
| M05 | memory_use | ok | MISS | MISS | ok | llm  |
| M06 | memory_use | ok | MISS | MISS | ok | llm  |
| M07 | memory_use | MISS | MISS | MISS | ok | fallback ['question:repeats_earlier'] |
| N01 | memory_inappropriate | ok | ok | ok | ok | fallback ['question:repeats_earlier'] |
| N02 | memory_inappropriate | ok | ok | ok | ok | fallback ['question:concept_already_in_answer'] |
| N03 | memory_inappropriate | ok | ok | ok | ok | fallback ['question:restates_answer'] |
| N04 | memory_inappropriate | ok | ok | ok | ok | llm  |
| N05 | memory_inappropriate | ok | ok | ok | ok | fallback ['question:repeats_earlier'] |
| N06 | memory_inappropriate | ok | ok | ok | ok | llm  |
| B01 | expected | ok | ok | ok | ok | probe  |
| B02 | expected | ok | ok | ok | ok | probe  |
| B03 | skip | ok | ok | ok | ok | none  |
| B04 | expected | ok | ok | ok | ok | probe  |
| B05 | expected | ok | ok | ok | ok | probe  |
| B06 | skip | ok | ok | ok | ok | none  |
| B07 | skip | ok | ok | ok (safety only) | ok | probe  |

## Root causes by case (from the recorded replies and the fixture context)

| case | what Windows showed | root cause | layer | change |
|---|---|---|---|---|
| T02 | rejected: concept_already_in_answer | The question names consistency (open) AND atomicity (already stated). The validator trusted the model's declared concept id, which was the stated one, so a good question was vetoed. | validator | concept ids are read from the question text; a question that names an open concept is not vetoed for also naming a covered one |
| T03 | rejected: concept_already_in_answer + not_tied_to_answer | 'It is O(log n).' states one concept; the question compares binary and linear search. Declared-id veto again, and the 4-word answer gives few tie words. | validator | ids derived from the question; linear search is the open TARGET and is named, which counts as a tie |
| T07 | skip chosen AND a question written | decision=skip with the question 'How do non-linearities help ...?'. The old code accepted the skip and dropped the question silently. | model payload + silent handling | payload:skip_with_question is a rejection with a targeted repair; if it repeats, the deterministic follow-up is used and the class is payload_inconsistent |
| T09 | rejected twice: restates_answer (+ evidence:none_verified) | Both questions paraphrase 'finds structure in data without labels'. The repair said only 'ask about the TARGET', which did not change a 3B model's output. | model quality + weak repair | repair now quotes the rejected question and asks for an example, reason, limit or trade-off about the named TARGET; the standard prompt asks for a progressive question |
| T10 | rejected: repeats_earlier + ignores the open concept + restates | 'How would you evaluate a logistic regression model?' repeats an earlier question; the open concepts were ROC/AUC, confusion matrix, precision/recall. | model quality (ignored TARGET) | question:ignores_target (probe_concept must name an open concept); repeat veto unchanged |
| M01 | accepted, memory_id none | Two statements were offered; the question uses 'class imbalance' (which is in the stored challenge) but cites nothing. The old prompt let the model decide to cite, and it declined. | generation + citation metadata (retrieval OK) | memory mode: one statement, code-built lead-in, memory_id in {id, none}; uncited use of statement-only words is rejected (memory:uncited_reference) |
| M02 | no memory offered; repeated question | The spam-classifier statement shares no word with 'Supervised learning is learning from examples'. The retrieval query held only the question and answer, not the vetted concepts of the question (labelled training data, classification). | RETRIEVAL | query expanded with the question's vetted concepts and reference; quote-aware specific_overlap |
| M03 | accepted, memory_id none | Two statements offered; generic pytest-mocking question; nothing cited. | generation | memory mode as M01 |
| M04 | no memory offered; 'E1 consistency' leaked | 'concurrent transactions' vs 'Atomicity means all or nothing': no shared word, and the matching part of the claim (billing database ... concurrent transactions) was in the quote, which the overlap test ignored. Also an id leak. | RETRIEVAL + id leak | quote-aware overlap + vetted-concept query; ids replaced by labels and rejected in the audit (id_leak) |
| M05 | accepted, memory_id none | One statement offered; a generic logistic-regression question; nothing cited. | generation | memory mode as M01 |
| M06 | accepted, memory_id none; question says 'your convolutional neural network' | 'convolutional neural network' is in the turn-1 statement and NOT in the current answer ('It uses neural networks with many layers'). So it is a real but undisclosed reference to a stored statement: an implicit grounded reference with missing citation metadata, not ordinary current-answer context and not invented. | citation metadata (an implicit use) | uncited use of statement-only words is rejected; in memory mode the lead-in is added by code and the id is validated |
| M07 | rejected: repeats_earlier | The question repeats the binary-search explanation the candidate just gave; the stored statement (a library-catalogue search feature) was offered but not used. | generation | memory mode connects the claim to the open TARGET (O(log n)) |
| B07 | class skip, outcome probe, success true | The fixture labels B07 'skip' but expects followup=null (unspecified) and safety=true; the deterministic probe asks about the missing action/result, safely. The old scorer returned ok=True for any null expectation, so a probe counted as a skip success. | FIXTURE inconsistency + scorer shortcut | scored on safety only, excluded from the strict skip rate, listed under fixture_defects; label NOT changed (approval needed) |

## Question-level replay of run 2's replies through the current rules

Windows kept only the question text, decision, skip_reason and memory_id. The replay uses a stand-in purpose, so each reply is shown under `deepen` and `probe_concept`. `accepted` means no current rule fires on the wording; it is NOT a quality verdict and not what the model would write under the new prompt.

| case | attempt | recorded question | recorded reasons | now if deepen | now if probe_concept |
|---|---|---|---|---|---|
| T02 | 1 | How does atomicity relate to the consistency of data after a crash? | ['question:concept_already_in_answer'] | accepted | accepted |
| T03 | 1 | How does binary search compare to linear search in terms of performance? | ['question:concept_already_in_answer', 'question:not_tied_to_answer'] | accepted | accepted |
| T07 | 1 | How do non-linearities help prevent the stacked layers from collapsing into a single linear map? | [] | ['payload:skip_with_question'] | ['payload:skip_with_question'] |
| T09 | 1 | How does it find structure in data without labels? | ['question:restates_answer'] | ['question:restates_answer'] | ['question:restates_answer'] |
| T09 | 2 | How does unsupervised learning find structure in data without labels? | ['question:restates_answer', 'evidence:none_verified'] | ['question:restates_answer'] | ['question:restates_answer'] |
| T10 | 1 | How would you evaluate a logistic regression model? | ['question:repeats_earlier', 'question:concept_already_in_answer', 'question:not_tied_to_answer', 'question:restates_answer'] | ['question:repeats_earlier', 'question:not_tied_to_answer', 'question:restates_answer'] | ['concepts:none_for_purpose', 'question:repeats_earlier', 'question:ignores_target', 'question:not_tied_to_answer', 'question:restates_answer'] |
| M01 | 1 | How does cross-validation help with class imbalance in the training data? | [] | accepted | ['question:ignores_target'] |
| M02 | 1 | How does supervised learning learn from examples? | ['question:repeats_earlier'] | ['question:repeats_earlier'] | ['concepts:none_for_purpose', 'question:repeats_earlier', 'question:ignores_target'] |
| M03 | 1 | Which mocking mechanism does pytest use to replace real objects in tests with fake ones? | [] | accepted | accepted |
| M04 | 1 | How does atomicity relate to E1 consistency? | ['question:concept_already_in_answer'] | accepted | accepted |
| M05 | 1 | How does the observed labels' likelihood relate to the weights found in logistic regression? | [] | accepted | accepted |
| M06 | 1 | How does the use of neural networks in your convolutional neural network contrast with other machine learning  | [] | ['memory:uncited_reference'] | ['memory:uncited_reference'] |
| M07 | 1 | How does halving the sorted list relate to the time complexity of binary search? | ['question:repeats_earlier'] | ['question:repeats_earlier'] | ['concepts:none_for_purpose', 'question:repeats_earlier', 'question:ignores_target'] |
| N01 | 1 | How does halving the sorted range relate to the time complexity of binary search? | ['question:repeats_earlier'] | ['question:repeats_earlier'] | ['concepts:none_for_purpose', 'question:repeats_earlier', 'question:ignores_target'] |
| N02 | 1 | How does atomicity ensure that data is consistent after a transaction is committed? | ['question:concept_already_in_answer'] | accepted | ['question:targets_covered_concept'] |
| N03 | 1 | How does it find structure in data without labels? | ['question:restates_answer'] | ['question:restates_answer'] | ['question:restates_answer'] |
| N03 | 2 | How does unsupervised learning find structure in data without labels? | ['question:restates_answer'] | ['question:restates_answer'] | ['question:restates_answer'] |
| N05 | 1 | How does bubble sort's time complexity relate to the number of swaps it makes? | ['question:repeats_earlier'] | ['question:repeats_earlier'] | ['question:repeats_earlier', 'question:targets_covered_concept'] |

## Memory-use cases, re-audited

- `M01`: Windows offered 2 statement(s); the current retrieval offers 2; run 2 re-audit: no finding; failure type: generation; scripted now: stage `used`
- `M02`: Windows offered 0 statement(s); the current retrieval offers 1; run 2 re-audit: no finding; failure type: retrieval; scripted now: stage `used`
- `M03`: Windows offered 2 statement(s); the current retrieval offers 1; run 2 re-audit: no finding; failure type: generation; scripted now: stage `used`
- `M04`: Windows offered 0 statement(s); the current retrieval offers 1; run 2 re-audit: no finding; failure type: retrieval; scripted now: stage `used`
- `M05`: Windows offered 1 statement(s); the current retrieval offers 1; run 2 re-audit: no finding; failure type: generation; scripted now: stage `used`
- `M06`: Windows offered 1 statement(s); the current retrieval offers 1; run 2 re-audit: ['implicit_memory_use_uncited']; failure type: citation_metadata; scripted now: stage `used`
- `M07`: Windows offered 1 statement(s); the current retrieval offers 1; run 2 re-audit: no finding; failure type: generation; scripted now: stage `used`

No human has rated anything in these runs. `human_validated` is false in both result files.
