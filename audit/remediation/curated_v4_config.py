"""Decision tables for Stage 1B final consolidation (v4). v1-v3 are never modified; v4 is built from v3 plus the evidence in stage1b4/."""

# ---- batch 03: stable id = smi-i + position in plan order; topics reuse the existing vocabulary where one fits
B3_ORDER = ["Machine Learning", "SQL", "Python", "Data Analysis"]
B3_TOPIC = {
 "P3-ML-01": "Data leakage", "P3-ML-02": "Data leakage", "P3-ML-03": "Calibration and probabilistic outputs", "P3-ML-04": "Calibration and probabilistic outputs",
 "P3-ML-05": "Drift and monitoring", "P3-ML-06": "Drift and monitoring", "P3-ML-07": "Model evaluation and metrics", "P3-ML-08": "Validation and model selection",
 "P3-ML-09": "ML in production", "P3-ML-10": "Model evaluation and metrics",
 "P3-SQL-01": "Set operations", "P3-SQL-02": "Set operations", "P3-SQL-03": "Set operations", "P3-SQL-04": "Set operations", "P3-SQL-05": "Query patterns",
 "P3-SQL-06": "Window functions", "P3-SQL-07": "Query patterns", "P3-SQL-08": "Aggregation and pivoting", "P3-SQL-09": "Window functions", "P3-SQL-10": "Query patterns",
 "P3-PY-01": "File handling", "P3-PY-02": "File handling", "P3-PY-03": "File handling", "P3-PY-04": "File handling", "P3-PY-05": "Modules and packaging",
 "P3-PY-06": "Modules and packaging", "P3-PY-07": "Modules and packaging", "P3-PY-08": "Exceptions and debugging", "P3-PY-09": "Exceptions and debugging", "P3-PY-10": "Exceptions and debugging",
 "P3-DA-01": "Exploratory analysis and methodology", "P3-DA-02": "Statistics fundamentals", "P3-DA-03": "Data preparation and cleaning", "P3-DA-04": "Hypothesis testing and A/B testing",
 "P3-DA-05": "Statistics fundamentals", "P3-DA-06": "Hypothesis testing and A/B testing", "P3-DA-07": "Hypothesis testing and A/B testing", "P3-DA-08": "Exploratory analysis and methodology",
 "P3-DA-09": "Product and business metrics", "P3-DA-10": "Statistics fundamentals",
}

# ---- difficulty: the blind auditor's rating is adopted where it differs from the author's label, except the entries below
DIFFICULTY_KEPT = {
 "smi-h0008": "Medium (second verifier suggested Hard: a design-with-trade-offs reading; the first blind auditor said Medium; kept Medium, disagreement recorded)",
}

# ---- explicit patches (record key, field, old, new). Keys: batch-02 id (smi-hNNNN) or batch-03 plan id (P3-XXX-NN). Fields: question, answer, code.setup/solution/test
_READ_PORT = '''def read_port(path):
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read().strip()
    except OSError as exc:
        raise ConfigFileError(f"cannot read {path!r}") from exc
    return parse_port(text)


def implicit_chain():'''
_READ_PORT_TEST = '''
import os, tempfile
with tempfile.TemporaryDirectory() as _d:
    _missing = os.path.join(_d, "nope.conf")
    try:
        read_port(_missing)
    except ConfigError as e:                    # one clause catches the whole library
        assert isinstance(e, ConfigFileError) and not isinstance(e, ConfigValueError)
        assert isinstance(e.__cause__, FileNotFoundError)
    else:
        raise AssertionError("missing file must raise")
    _ok = os.path.join(_d, "ok.conf")
    with open(_ok, "w", encoding="utf-8") as _fh:
        _fh.write("8080\\n")
    assert read_port(_ok) == 8080
    _bad = os.path.join(_d, "bad.conf")
    with open(_bad, "w", encoding="utf-8") as _fh:
        _fh.write("eighty\\n")
    try:
        read_port(_bad)
    except ConfigValueError as e:                # a bad value is a different type from a missing file
        assert not isinstance(e, ConfigFileError)
    else:
        raise AssertionError("bad value must raise")
'''
PATCHES = [
 ("P3-PY-08", "code.test", 'assert swallow() == "finally wins"', 'assert swallow() == "done"'),
 ("P3-PY-09", "answer", "def implicit_chain():", _READ_PORT),
 ("P3-PY-09", "code.solution", "def implicit_chain():", _READ_PORT),
 ("P3-PY-09", "code.test", "try:\n    parse_port(\"70000\")", _READ_PORT_TEST.lstrip("\n") + "\ntry:\n    parse_port(\"70000\")"),
]
APPEND_ANSWER = {
 "P3-PY-09": "\n\nIn the library, a missing or unreadable file raises ConfigFileError (chained from the OSError) and a malformed value raises ConfigValueError, so a caller can handle the two differently, while a single `except ConfigError` still catches everything the library raises on purpose. Exceptions from outside the hierarchy (for example a TypeError from passing None) are not wrapped unless you validate inputs.",
}
