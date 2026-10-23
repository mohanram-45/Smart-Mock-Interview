# Stage 10 human-review pack

**Status: UNRATED.** 18 interviewer turns produced by the *deterministic* generators in scripted interviews with a *synthetic* candidate. No human has rated them, and no score here is a result.

Rate `review_sheet.csv` without opening `key.json` (it says which generator wrote each turn). Criteria (anchors):

* **natural (1-5)** 1 = reads like a form field, 3 = acceptable, 5 = something a good interviewer would say.
* **relevant_to_context (1-5)** 1 = ignores what was said, 5 = clearly builds on it.
* **grounded (yes/no)** every claim about what the candidate said is in `context_*` columns (no invented facts).
* **repeats_earlier (yes/no)** repeats a question already asked in the same interview.
* **sounds_like_an_interviewer (1-5)** not a quiz engine / textbook.

Two raters, independent; report agreement and disagreements. Do not call any LLM's labels human ground truth. For the real-model comparison use `scripts/stage10_verify_real_stack.py`, which writes its own blind sheet.
