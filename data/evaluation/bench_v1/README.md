Builds data/evaluation/bench_v1/{items,expectations}.jsonl  (Stage 3B).

* items.jsonl        INPUTS ONLY (item_id, question_id, category, candidate_answer). The runner reads only this file.
* expectations.jsonl EXPECTED JUDGMENTS, kept separate from model outputs. Never shown to the model.

Provenance of the judgments: authored by Claude (an AI) from the curated record's question, key concepts and canonical answer.
They are AI-created, NOT human ground truth, NOT independent of the reference answers, and have not been human-reviewed.
Candidate answers are synthetic (written for testing); none comes from a real candidate. Score ranges are deliberately wide bands.

