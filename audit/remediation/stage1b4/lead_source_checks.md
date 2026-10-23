# Sources opened by the lead (main session), Stage 1B final consolidation

Opened and read in full or by targeted extraction. Sub-agents could not fetch these (egress blocked), so the batch-02 evidence marks the claims `background_only`; the results below upgrade them where noted. The records' wording was not changed because every claim was already hedged consistently with what the sources say.

| Claim (record) | Source | Result |
|---|---|---|
| alpha/r scaling reduces re-tuning when r varies (smi-h0004) | arXiv 2106.09685, section 4.1 | Supported: "This scaling helps to reduce the need to retune hyperparameters when we vary r"; alpha set to the first r tried and not tuned |
| 13-gram overlap used to define contaminated benchmark examples (smi-h0012) | arXiv 2005.14165 (GPT-3), section 4 | Supported: "examples that have a 13-gram overlap with anything in the pretraining set" (shorter examples: whole-example check) |
| Timsort may need up to about n/2 temporary slots (smi-h0032) | CPython Objects/listsort.txt | Supported: "as many as N//2 pointers"; less on structured data |
| UNION dedupes, UNION ALL keeps; INTERSECT/EXCEPT dedupe; equal column count; NULLs equal for duplicate detection; left-to-right grouping (smi-i0011..i0014) | sqlite.org/lang_select.html, compound SELECT | Supported verbatim. The page states no precedence ranking among the operators beyond left-to-right grouping |
| Sigmoid for small samples; isotonic more prone to overfitting, better beyond ~1000 samples; calibrator fit on data independent of the classifier (smi-i0003, smi-i0004) | scikit-learn calibration page | Supported. The 1,000 figure is the docs' own rule of thumb; smi-i0004 labels its positives-count heuristic as its own |
| os.replace atomicity, csv newline='', try/finally return semantics (smi-i0021..i0030 area) | docs.python.org | NOT opened: permission request unanswered. These claims are backed by executed tests only (stdlib behaviour on Python 3.10/3.11/3.13), not by an opened page |
| Lost in the Middle, Goyal et al. sqrt scaling, BH/BY/Holm theorems, bootstrap inconsistency, SRM threshold convention | papers | NOT opened. Remain `background_only` and hedged in the text |
