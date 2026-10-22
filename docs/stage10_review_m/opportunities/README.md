# Blind review pack (v2)

**Status: UNRATED (30 items).** The questions come from a rule-based stand-in model answering SYNTHETIC candidate answers. An unrated sheet is review material; it is not a human evaluation and nothing reported elsewhere depends on it.

What you see per row: the original interview question, the candidate's answer, what the candidate had said earlier in the interview, the rubric criteria that were still open, and ONE interviewer question. Judge only that question. Do not open `key.json` before you have rated every row (it names the generator, the case and the rules' verdict).

Columns to fill: `natural_1to5` (1 = reads like a form field, 5 = a good interviewer would say it), `relevant_to_answer_1to5` (1 = ignores the answer, 5 = clearly builds on it), `uses_earlier_statement_correctly_yes_no_na` (does it refer to something the candidate really said, accurately? `na` if it refers to nothing earlier), `invents_anything_yes_no` (any fact, technology or event the candidate did not say), `repeats_something_yes_no`.

Use two independent raters. Report agreement and every disagreement; do not treat a language model's labels as human ground truth. Summarise with `python scripts/stage10l_review_summary.py <dir>`: it refuses to print any rating statistic for unrated rows.
