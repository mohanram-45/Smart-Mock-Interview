# Task: write out-of-corpus queries

A data-science interview knowledge base has these topics (read /home/claude/work/proj/audit/retrieval/corpus_topic_list.json; read nothing else on disk, and do not open data/ folders).

Write 22 realistic interview-style questions or search queries that a candidate might type about data science / ML / software topics that are NOT covered by any listed topic. Mix:
* 8 adjacent-but-uncovered technical topics (e.g. a data-science subfield absent from the list),
* 6 clearly off-domain technical topics (other areas of computing),
* 4 non-technical or HR style ("tell me about yourself"-type, salary negotiation),
* 4 plausible-sounding but very specific tool/vendor questions unlikely to be covered.
Check each against the topic list; if a topic seems covered, replace it. Vary phrasing (full questions, keywords).
Output JSON list to the path given: `[{"query": "...", "kind": "adjacent|off_domain|non_technical|vendor_specific"}]`. Reply "done" plus count.
