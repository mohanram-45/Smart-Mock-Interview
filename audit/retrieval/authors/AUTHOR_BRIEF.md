# Task: write retrieval test queries (independent evaluation set)

You are writing realistic search queries for evaluating a semantic retrieval system over a data-science / ML interview knowledge base (domains: Machine Learning, Deep Learning, NLP, Python, SQL, Data Analysis, Generative AI & RAG, MLOps & Model Deployment).

## Strict rules (leakage control)
* Read ONLY your shard file and this brief. Do NOT open, search or read anything else on disk (no data/, src/, reports/ folders). You must not see the stored questions or answers.
* Each task gives you target record briefs: topic + key concepts only. Write the query WITHOUT copying the topic string or listing the key-concept phrases verbatim as a list; use your own wording and different vocabulary where natural. Vary style across queries.
* Never mention record ids in a query.

## Categories (field `category`)
* `paraphrase`: one interview-style question (a full sentence) a candidate or interviewer might ask about the target concept, in your own words. 8-30 words. Not a template ("What is X?" for every query).
* `concept_keywords`: a short keyword/noun-phrase search (2-8 words), how a learner would type into a search box.
* `multi_concept`: ONE query (1-2 sentences) that genuinely asks about BOTH target concepts together (two different concepts); it must be answerable only by knowledge covering both parts.
* `similar_distinct`: a query that is unambiguously about the TARGET concept and NOT about `confusable_with` (a technically similar but different topic). Include a detail that discriminates the two.
* `domain_confusing`: a query about the TARGET concept that uses vocabulary which also appears in the `confusable_with` record's domain (e.g. "index", "pipeline", "embedding", "validation", "drift", "window"), so a careless system may retrieve the wrong domain. The target must still be clearly the intended topic.

## Output
Write a JSON list to the output path you are given: `[{"task_id": "T012", "query": "..."}, ...]` with exactly one entry per task, same task_ids. Reply with only "done" plus the count.
