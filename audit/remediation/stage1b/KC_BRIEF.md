# Key-concept review brief
Each input record has a question, a reference answer, and `key_concepts` (a list). Rules for the final list:
- 3 to 8 items, distinct, each a specific technical term/skill an interviewer would tick off (e.g. "left join", "inverted dropout", "entity-level F1"); no generic words ("data", "model", "algorithm", "machine learning" alone, "explanation").
- Every item must actually be discussed in the question or answer text (wording may differ: "R-squared" for "R^2" is fine). Do not add a concept the answer does not cover; if the answer lacks something important, do not add it to the concepts and do not edit the answer.
- Keep the existing items that are good (preserve order where sensible); remove or replace items that are ungrounded, vague or duplicated; add items from the answer text until there are at least 3.
- `heuristic_flags` lists items a crude token-matcher could not find in the text; many are false alarms caused by different wording -- judge semantically.
Output: write a JSON object {id: [final key_concepts list]} containing ONLY records where you changed the list (omit records whose list is already fine), and a second key "_unchanged_ok" with the list of ids you checked and left unchanged. Do not modify any other file. Finish with counts.
