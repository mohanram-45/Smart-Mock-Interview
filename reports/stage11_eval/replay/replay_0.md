# Stage 11 replay of recorded real replies

Source: `reports/stage11_eval/stage10n_real_llama3.2_3b_20261021_205846.json` (model llama3.2:3b, prompt 10.fu8). **This is a replay of recorded text through the objective engine's code. No model was called; it does not show what a model would write under the new prompt.**

| case | class | 10N result | recorded question (1st attempt) | objective engine verdict | memory by code | reasons |
|---|---|---|---|---|---|---|
| T01 | expected | ok (llm) | How does the model handle misclassified examples in classification, and what is the impact on loss minimisatio | accept | no |  |
| T02 | expected | ok (llm) | How does atomicity ensure that data remains consistent after a crash, and what happens to data that is partial | reject | no | question:ignores_objective |
| T03 | expected | ok (llm) | How does binary search compare to linear search in terms of the number of elements that need to be checked for | accept | no |  |
| T04 | expected | ok (llm) | How many filters does a typical convolutional layer use in a CNN? | reject | no | question:unanswerable_quantity |
| T06 | expected | miss (skip) | How does the number of swaps in bubble sort relate to its time complexity? | reject | no | question:repeats_earlier |
| T07 | expected | miss (fallback) | How many layers can a neural network have before the stacked layers collapse into a single linear map? | reject | no | question:repeats_answer_content |
| T08 | expected | ok (llm) | How does logistic regression use the sigmoid function to transform the input features into a probability outpu | accept | no |  |
| T09 | expected | ok (llm) | How does unsupervised learning find structure in data without labels? | reject | no | question:restates_answer, question:repeats_answer_content |
| T10 | expected | ok (llm) | How does cross-validation help evaluate the model's performance on classes with imbalanced data? | reject | no | question:revisits_explained_concept |
| T11 | expected | miss (fallback) | How do deep learning's self-learned representations differ from the hand-engineered features used in tradition | reject | no | question:novel_terms:self-learned |
| T12 | expected | miss (fallback) | How does a Type II error differ from a false negative? | reject | no | question:false_premise:type ii error/false negative |
| M01 | memory_use | miss (llm) | How would you evaluate the performance of your oral cancer classification model using PyTorch? | reject | no | memory:uncited_reference, memory:link_without_objective |
| M02 | memory_use | ok (llm) | How does supervised learning relate to your experience with the spam classifier on labelled emails? | reject | no | memory:uncited_reference, memory:link_without_objective |
| M03 | memory_use | miss (llm) | How does pytest's mocking mechanism allow you to replace real objects in your Flask API tests with fake ones? | reject | no | memory:uncited_reference, memory:link_without_objective |
| M04 | memory_use | miss (fallback) | How does atomicity in your money transfer handling in PostgreSQL relate to ensuring data consistency in the da | accept | yes |  |
| M05 | memory_use | miss (skip) | How does the use of the sigmoid function in logistic regression relate to the concept of maximum likelihood es | accept | yes |  |
| M06 | memory_use | miss (fallback) | How does the use of neural networks in your PyTorch project relate to the concept of deep learning? | reject | no | memory:uncited_reference, memory:link_without_objective |
| M07 | memory_use | ok (llm) | How does the process of halving a sorted list at each step relate to the time complexity of linear search? | accept | no |  |
| N01 | memory_inappropriate | ok (llm) | How many steps does binary search take to find the exact value in a sorted list of size n? | accept | no |  |
| N02 | memory_inappropriate | ok (llm) | How does atomicity ensure that data is consistent across all nodes in a distributed system? | reject | no | question:ignores_objective, question:unsupported_premise:distributed,node,system |
| N03 | memory_inappropriate | ok (llm) | How does it find structure in data without labels? | reject | no | question:restates_answer, question:repeats_answer_content |
| N04 | memory_inappropriate | ok (llm) | How do these filters interact with the input data when they slide over it? | reject | no | question:ignores_objective |
| N05 | memory_inappropriate | ok (llm) | How does the number of swaps required to sort a list of n elements in bubble sort relate to the number of elem | accept | no |  |
| N06 | memory_inappropriate | ok (fallback) | How does a Type I error differ from a false positive? | reject | no | question:restates_answer, question:false_premise:type i error/false positive, question:rep |

```json
{
 "technical_rows": 33,
 "rows_with_a_recorded_question": 24,
 "memory_use": {
  "n": 7,
  "baseline_grounded_use": 2,
  "first_question_attributed_by_code": 2,
  "any_recorded_question_attributed_by_code": 2,
  "any_recorded_question_valid_without_memory": 4
 },
 "expected": {
  "n": 12,
  "baseline_success": 7,
  "first_question_accepted": 3,
  "any_recorded_question_accepted": 4
 },
 "memory_inappropriate": {
  "n": 6,
  "baseline_success": 6,
  "any_recorded_question_attributed_by_code": 0
 },
 "weak_cases_flagged_in_brief": {
  "T02": {
   "baseline_accepted_question": "How does atomicity ensure that data remains consistent after a crash, and what happens to data that is partially written during a crash?",
   "objective_engine_accepts_it": false,
   "reasons": [
    "question:ignores_objective"
   ]
  },
  "T04": {
   "baseline_accepted_question": "How many filters does a typical convolutional layer use in a CNN?",
   "objective_engine_accepts_it": false,
   "reasons": [
    "question:unanswerable_quantity"
   ]
  },
  "T10": {
   "baseline_accepted_question": "How does cross-validation help evaluate the model's performance on classes with imbalanced data?",
   "objective_engine_accepts_it": false,
   "reasons": [
    "question:revisits_explained_concept"
   ]
  },
  "M07": {
   "baseline_accepted_question": "Earlier you said you built a search feature for a library catalogue in Python. How does the process of searching a catalogue in a library relate to linear search?",
   "objective_engine_accepts_it": false,
   "reasons": [
    "memory:uncited_reference",
    "memory:not_framed_as_own_work"
   ]
  },
  "N02": {
   "baseline_accepted_question": "How does atomicity ensure that data is consistent across all nodes in a distributed system?",
   "objective_engine_accepts_it": false,
   "reasons": [
    "question:ignores_objective",
    "question:unsupported_premise:distributed,node,system"
   ]
  }
 },
 "rows_with_a_payload_issue_in_any_recorded_attempt": 13,
 "memory_offered_mismatch_with_recorded_run": []
}
```