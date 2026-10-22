#!/usr/bin/env python3
"""Parse/validate fenced yaml / dockerfile blocks in a batch's answers.
Usage: python config_check.py <batch_dir> [out.json]
YAML: PyYAML safe_load_all. Kubernetes-looking documents (apiVersion+kind) are additionally schema-validated offline with kubernetes-validate (strict).
YAML fragments (no apiVersion/kind) are parse-checked only. Dockerfile: dockerfile-parse + instruction whitelist + FROM-first. Nothing is built or applied.
Optional deps: pyyaml, kubernetes-validate, dockerfile-parse; a missing dep is reported as SKIPPED, never as pass."""
import sys, json, re, pandas as pd
from pathlib import Path
B = Path(sys.argv[1]); out = {}
try: import yaml
except Exception: yaml = None
try: import kubernetes_validate as kv
except Exception: kv = None
try: import dockerfile_parse as dfp
except Exception: dfp = None
INSTR = {"FROM","RUN","CMD","LABEL","MAINTAINER","EXPOSE","ENV","ADD","COPY","ENTRYPOINT","VOLUME","USER","WORKDIR","ARG","ONBUILD","STOPSIGNAL","HEALTHCHECK","SHELL"}
d = pd.read_csv(next(B.glob("*_accepted.csv")), keep_default_na=False, dtype=str)
for r in d.itertuples():
    for f in ("answer", "concise_answer", "detailed_answer", "practical_answer"):
        for i, (lang, body) in enumerate(re.findall(r"```(\w*)\n(.*?)```", getattr(r, f), re.S)):
            l = lang.lower()
            if l in ("python", "", "py"): continue
            key = f"{r.id}:{f}:{i}"; res = {"plan_id": r.plan_id, "lang": l, "tool": None, "status": None, "detail": ""}
            if l in ("yaml", "yml"):
                if yaml is None: res.update(status="SKIPPED", detail="pyyaml missing")
                else:
                    try:
                        docs = [x for x in yaml.safe_load_all(body) if x is not None]; res.update(tool="PyYAML safe_load_all", status="parsed", detail=f"{len(docs)} document(s)")
                        k8s = [x for x in docs if isinstance(x, dict) and "apiVersion" in x and "kind" in x]
                        if k8s:
                            if kv is None: res.update(status="parsed_schema_SKIPPED", detail=res["detail"] + "; kubernetes-validate missing")
                            else:
                                for x in k8s: kv.validate(x, "1.31", strict=True)
                                res.update(tool="PyYAML + kubernetes-validate (offline schema, strict, k8s 1.31)", status="schema_valid", detail=f"{len(k8s)} Kubernetes object(s) valid against the 1.31 schema")
                        else: res["detail"] += "; fragment, no apiVersion/kind: syntax checked only, schema not checked"
                    except Exception as e: res.update(status="FAILED", detail=str(e).splitlines()[0][:200])
            elif l == "dockerfile":
                if dfp is None: res.update(status="SKIPPED", detail="dockerfile-parse missing")
                else:
                    try:
                        p = dfp.DockerfileParser(); p.content = body; st = p.structure
                        ins = [s["instruction"] for s in st if s["instruction"] != "COMMENT"]
                        bad = [x for x in ins if x not in INSTR]
                        if not ins or ins[0] not in ("FROM", "ARG"): res.update(status="FAILED", detail="first instruction must be FROM (or ARG)")
                        elif bad: res.update(status="FAILED", detail=f"unknown instructions {bad}")
                        else: res.update(tool="dockerfile-parse + instruction whitelist (not built; no Docker daemon in sandbox)", status="syntax_parsed", detail=f"{len(ins)} instructions; image names/digests/placeholders not resolved")
                    except Exception as e: res.update(status="FAILED", detail=str(e)[:200])
            elif l == "sql": continue  # SQL is validated below against configs.json + the recorded sqlite3 test
            else: res.update(status="UNCHECKED", detail=f"no validator for ```{l}")
            out[key] = res
cj = B / "configs.json"; tj = B / "code_tests.json"
if cj.exists() and tj.exists():
    cfgs = json.loads(cj.read_text()); tests = json.loads(tj.read_text()); ws = lambda x: re.sub(r"\s+", " ", x).strip()
    pm = dict(zip(d.id, d.plan_id))
    for sid, lst in cfgs.items():
        for i, c in enumerate(lst):
            if c["lang"] != "sql": continue
            ok = sid in tests and ws(c["content"]) in ws(tests[sid]["solution"])
            out[f"{sid}:config:{i}"] = {"plan_id": pm.get(sid, ""), "lang": "sql", "tool": "Python sqlite3 (in-memory), recorded test on 3.10/3.11/3.13", "status": "executed_in_recorded_test" if ok else "FAILED", "detail": "SQL text found verbatim in the executed solution" if ok else "SQL not found in tested solution"}
for k, v in out.items(): print(k, v["plan_id"], v["lang"], v["status"], "-", v["detail"])
if len(sys.argv) > 2: Path(sys.argv[2]).write_text(json.dumps(out, indent=1))
bad = [k for k, v in out.items() if v["status"] in ("FAILED",)]
print(f"{len(out)} blocks; failed: {bad}")
