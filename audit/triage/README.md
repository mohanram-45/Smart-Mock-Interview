# Triage working files

Decision files (`dec_*.py`) hold one K/F/X call per seed record (KEEP / FIX / EXCLUDE) with flags, a note, and proposed text. `build_triage.py` joins them to the processed dataset and writes `data/audit/triage.csv`; `run_code_tests.py` executes the proposed code snippets; `make_reports.py` writes the markdown reports. `gap_concepts.py` holds the concept checklists and suggested reference sources.

These are the working copies used to produce the audit files. They read `/home/claude/work/audit_clean/processed_annotated.pkl` (the processed dataset annotated by the earlier audit scripts), so paths need adjusting to rerun elsewhere. Nothing here is imported by the production pipeline.
