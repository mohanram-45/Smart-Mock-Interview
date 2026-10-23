# Stage 12 answer assessment: SCRIPTED stand-in: proves the code path only, says nothing about model quality

Expected verdicts are the author's judgement (author judgement, not human-rated). Matches: 9/10.

| case | kind | BEFORE (similarity % + band comment) | AFTER verdict | misconceptions found | missing | expected |
|---|---|---|---|---|---|---|
| autoencoder_misconception | factual error (real) | 90.7% — “Excellent work — this answer is clear, accurate, and complete.” | **Partially correct** (misconception); similarity now shown as 0.91 | “It always needs labelled training data to learn the correct output.” | — | partially_correct ✓ |
| autoencoder_paraphrase | correct paraphrase | not computed (ImportError: Sentence-BERT not available here) | **Uncertain** (evidence_incomplete); similarity now shown as — | — | — | correct ✗ |
| unsupervised_short | partial (real) | 65.7% — “You're showing good understanding of the topic here.” | **Partially correct** (some_essential_missing); similarity now shown as 0.66 | — | an unsupervised task | partially_correct ✓ |
| unsupervised_complete | correct, own words | not computed (ImportError: Sentence-BERT not available here) | **Correct** (all_essential_demonstrated); similarity now shown as — | — | — | correct ✓ |
| fourier_no_attempt | no attempt (real) | 0.0% — “There's a gap in understanding here — take some time to review this.” | **Incorrect** (no_attempt); similarity now shown as 0.00 | — | Fourier transform; frequency domain; amplitude and phase; FFT; spectrogram (STFT) | incorrect ✓ |
| hypothesis_real | correct, brief (real) | 72.3% — “That's a clear, well-formed response.” | **Correct** (all_essential_demonstrated); similarity now shown as 0.72 | — | — | correct ✓ |
| hypothesis_false | factual error, reference vocabulary | not computed (ImportError: Sentence-BERT not available here) | **Incorrect** (misconceptions_outweigh_correct_content); similarity now shown as — | “Hypothesis testing uses sample data to prove whether the null hypothesis is true.” | — | incorrect ✓ |
| unrelated | unrelated | not computed (ImportError: Sentence-BERT not available here) | **Incorrect** (off_topic); similarity now shown as — | — | — | incorrect ✓ |
| empty | empty | not computed (ImportError: Sentence-BERT not available here) | **Incorrect** (no_attempt); similarity now shown as — | — | unlabelled data; clustering; dimensionality reduction; anomaly detection; evaluation without labels | incorrect ✓ |
| mocking_real | right idea, no pytest mechanism named (real) | 49.7% — “There's a solid foundation in this answer.” | **Partially correct** (only_supporting_demonstrated); similarity now shown as 0.50 | — | a mocking mechanism in pytest | partially_correct ✓ |
