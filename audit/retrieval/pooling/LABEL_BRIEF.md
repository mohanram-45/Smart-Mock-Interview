# Task: judge relevance of knowledge-base records to search queries

You are labelling retrieval relevance for a data-science interview knowledge base. Each item has a search `query` and a list of `candidates` (candidate records: domain, topic, stored question, key concepts, first 450 chars of the stored reference answer).

## Strict rules
* Read ONLY your shard file and this brief. Do not open any other file on disk (no data/, src/, reports/, or other folders in audit/). Judge solely from the text in front of you and your own technical knowledge.
* Judge each candidate independently of its position in the list. Candidate order is random.
* Judge relevance to what the query ASKS, not word overlap and not whether the record's domain label matches.

## Grades
* `2` directly relevant: the record's question/topic is what the query is asking about, so a user would be well served by being shown this record's Q&A. For a query asking about two concepts, a record that squarely covers ONE of the concepts gets 2.
* `1` partially relevant: related, covers an adjacent or narrower/broader aspect, or only a minor part of the query; helpful context but not the main answer.
* `0` not relevant: different concept, even if it shares keywords or a domain.
Most candidates are 0. It is correct (and expected) for some queries to have NO candidate above 0, because the knowledge base may not cover the query; do not force relevance.

## Output
Write a JSON list to the output path you are given: `[{"query_id": "Q012", "grades": {"c1": 0, "c2": 2, ...}, "no_relevant_record": false, "note": "<=20 words on why the grade-2 (or the lack of one)"}, ...]`. Every candidate must have a grade. `no_relevant_record` is true iff all grades are 0. Reply only "done" plus the number of queries.
