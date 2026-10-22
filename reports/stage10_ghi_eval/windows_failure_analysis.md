# Stage 10G: failure analysis of the real Windows run

Evidence: `reports/stage10_windows_evidence/` (llama3.2:3b, Ollama 0.32.13, prompt 10.fu4). Measured on Windows by you; nothing here was re-run on a model.

23 eligible opportunities, 12 useful+valid (52.2%); 8/11 skips correct; 0 fabricated memory references; 0 truncated; cold 37718.0 ms, first call 3258.9 ms, warm median 1950.9 ms.

## Per-class view (not just the aggregate)

| class | n | success | accepted | model skipped | fell back |
|---|---|---|---|---|---|
| expected | 16 | 8 | 8 | 6 | 2 |
| skip | 11 | 8 | 4 | 0 | 5 |
| memory_use | 7 | 4 | 6 | 0 | 1 |
| memory_inappropriate | 6 | 6 | 4 | 1 | 1 |

Rejection codes on Windows: {'question:novel_terms': 3, 'question:not_tied_to_answer': 1, 'question:accusatory': 1, 'answer_unrelated_to_question': 2, 'answer_looks_like_instructions': 1, 'evidence:none_verified': 1}. Skip reasons: {'covered': 7}.

## Case-level failure table (14 misses)

| case | class | what happened | evidence | cause | legitimate safety rejection? | fix |
|---|---|---|---|---|---|---|
| T02 | expected | rejected: question:novel_terms:E2 | model wrote the concept id 'E2' into the question text (prompt listed 'E2 consistency') | prompt/schema design + validator-adjacent | no | sanitise_ids replaces ids with labels; prompt says never write ids |
| T03 | expected | rejected: question:not_tied_to_answer | wording did not build on a 4-word answer ('It is O(log n).'); text of the rejected reply was not recorded | model quality or over-strict tie rule: UNDETERMINED | unclear | TARGET concept chosen by code and concept_id inferred from the question; rejected replies are now recorded in results.json rows[].debug so the next run settles it |
| T05 | expected | model skip (covered) | 3 of 3 shown concepts 'not found'; the answer swaps 'is' and '==' | LLM skipped an eligible follow-up | no | skip 'covered' is overruled when concepts are open; ask-only prompt with TARGET; one repair |
| T06 | expected | model skip (covered) | answer says O(n); concept O(n^2) 'not found' | LLM skipped an eligible follow-up | no | same |
| T07 | expected | model skip (covered) | 2 of 3 concepts 'not found' | LLM skipped an eligible follow-up | no | same |
| T08 | expected | model skip (covered) | 3 of 4 concepts 'not found' (sigmoid, parametric, discriminative) | LLM skipped an eligible follow-up | no | same |
| T10 | expected | model skip (covered) | 3 of 4 concepts 'not found' (ROC/AUC, confusion matrix, precision/recall) | LLM skipped an eligible follow-up | no | same |
| T12 | expected | model skip (covered) | Type II error, false positive, false negative 'not found' | LLM skipped an eligible follow-up | no | same |
| S01 | skip | accepted a question (should skip) | only 'loss minimisation' was 'not found'; the answer says 'minimises a loss' | exact-word hint too literal | no | stem-level coverage: now covered, skipped by the rules, model not called |
| S02 | skip | accepted a question (should skip) | 4 of 4 concepts 'found' and the model still asked | LLM ignored the hint | no | all concepts covered -> skipped by the rules, model not called |
| S03 | skip | accepted 'Can a Type I error also be referred to as a false negative?' | 4 of 4 concepts 'found'; the question is also a yes/no that plants a wrong claim | LLM ignored the hint + low-quality wording | no | rules skip; closed_yes_no rule |
| M02 | memory_use | accepted without citation: 'What does it mean to learn from examples in supervised learning?' | a definition re-ask of the candidate's own phrase; no stored memory cited (whether one was offered is not recorded) | model quality (generic) + memory use UNDETERMINED | no | 'what does it mean' rejected + one repair; offered memory ids now recorded per case |
| M04 | memory_use | rejected: question:novel_terms:E2 | same id leak as T02 | prompt/schema design | no | sanitise_ids |
| M07 | memory_use | accepted without citation: 'You said halving the sorted list ..., is that a key insight ...?' | yes/no question that only repeats the candidate's words; no memory used | model quality | no | closed_yes_no rejected + one repair |

No miss was a legitimate safety rejection: the two `novel_terms` rejections were the model echoing a prompt id, and `not_tied_to_answer` on T03 is unresolved (see its row).

## What the 12 'useful' results hide

The automatic score counted a question as useful when the rules accepted it and the audit found nothing. Replaying the 22 questions the model wrote through the current rules:

| item | case | class | question (model-written) | now |
|---|---|---|---|---|
| O001 | T11 | expected | Can deep learning rely on hand-engineered features, or does it always learn its own representations? | rejected now (then one repair attempt) (question:closed_yes_no) |
| O002 | M07 | memory_use | You said halving the sorted list at each step, is that a key insight for understanding the time complexity of binary search? | rejected now (then one repair attempt) (question:closed_yes_no) |
| O003 | S02 | skip | How do concurrent transactions ensure isolation? | no question asked now: answer covered, skipped by the rules |
| O004 | N05 | memory_inappropriate | How does bubble sort's time complexity of O(n²) relate to the number of passes through the list? | still accepted |
| O005 | B05 | expected | What was your personal responsibility in that? | n/a (behavioural probe: deterministic bank, not model-written) |
| O006 | M03 | memory_use | You mentioned replacing real objects with fake ones in tests, how do you use mocking in pytest to specify the return value of a function? | not replayed (needs the memory the Windows session offered) |
| O007 | M06 | memory_use | How do the many layers in neural networks contribute to hierarchical representations? | not replayed (needs the memory the Windows session offered) |
| O008 | B07 | skip | What happened after you made that decision? | n/a (behavioural probe: deterministic bank, not model-written) |
| O009 | M02 | memory_use | What does it mean to learn from examples in supervised learning? | rejected now (then one repair attempt) (question:generic_definition_request) |
| O010 | B01 | expected | What was your personal responsibility in that? | n/a (behavioural probe: deterministic bank, not model-written) |
| O011 | T09 | expected | Can unsupervised learning find structure in data even if it doesn't have labels? | rejected now (then one repair attempt) (question:closed_yes_no) |
| O012 | M05 | memory_use | You mentioned logistic regression predicts the probability of a class using the sigmoid function of a weighted sum of the features. How does maximum likelihood estimation relate to this process? | not replayed (needs the memory the Windows session offered) |
| O013 | S01 | skip | How does the model learn a mapping between input and output pairs in supervised learning? | no question asked now: answer covered, skipped by the rules |
| O014 | M01 | memory_use | You mentioned cross-validation, but what specific metrics would you use to evaluate the model's performance? | not replayed (needs the memory the Windows session offered) |
| O015 | B04 | expected | What would you do differently now? | n/a (behavioural probe: deterministic bank, not model-written) |
| O016 | N02 | memory_inappropriate | Can you elaborate on how atomicity ensures that data is not left in an inconsistent state? | still accepted |
| O017 | S03 | skip | Can a Type I error also be referred to as a false negative? | no question asked now: answer covered, skipped by the rules |
| O018 | T01 | expected | What does it mean to train a model on labelled data? | rejected now (then one repair attempt) (question:generic_definition_request, question:restates_answer) |
| O019 | N03 | memory_inappropriate | Can unsupervised learning be used to identify patterns in labeled data? | rejected now (then one repair attempt) (question:closed_yes_no) |
| O020 | N01 | memory_inappropriate | Does the time complexity of binary search depend on the number of elements in the sorted range? | rejected now (then one repair attempt) (question:closed_yes_no) |
| O021 | T04 | expected | Can you elaborate on how the dot product is used in a convolutional layer? | still accepted |
| O022 | B02 | expected | What happened after you made that decision? | n/a (behavioural probe: deterministic bank, not model-written) |

Of the 12 counted as useful, 3 would now be rejected or skipped (T11, T09, T01). So the 52.2% overstated the quality of what was accepted: the strict reading of the same Windows run is lower, and the repairs must be judged on a new real run, not on this replay.
