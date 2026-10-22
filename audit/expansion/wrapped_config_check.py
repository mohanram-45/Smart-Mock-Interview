#!/usr/bin/env python3
"""Supplementary check for Batch 3's YAML fragments: wrap each fragment in a minimal Deployment and schema-validate it offline
(kubernetes-validate, strict, k8s 1.31). This shows the FIELD NAMES/TYPES are valid Kubernetes; it does NOT show the manifests were applied,
scheduled or behave as the answers describe. Batch 3 files are not modified. Output: reports/batch03_wrapped_config_check.json"""
import re, json, copy, yaml, pandas as pd, kubernetes_validate as kv
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
d = pd.read_csv(ROOT / "data/expansion/batch_03/batch_03_accepted.csv", keep_default_na=False, dtype=str)
base = {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "x"}, "spec": {"replicas": 1, "selector": {"matchLabels": {"a": "b"}}, "template": {"metadata": {"labels": {"a": "b"}}, "spec": {"containers": [{"name": "c", "image": "img"}]}}}}
out = {}
for r in d.itertuples():
    for lang, body in re.findall(r"```(yaml)\n(.*?)```", r.practical_answer, re.S):
        frag = yaml.safe_load(body); m = copy.deepcopy(base); pod = m["spec"]["template"]["spec"]; cont = pod["containers"][0]
        for k, v in frag.items():
            if k in ("resources", "volumeMounts", "startupProbe", "readinessProbe", "livenessProbe"): cont[k] = v
            elif k == "volumes": pod[k] = v
            elif k in ("strategy", "minReadySeconds"): m["spec"][k] = v
            elif k == "spec":
                for kk, vv in v.items():
                    if kk == "containers": pod["containers"] = [{**{"image": "img"}, **c} for c in vv]
                    else: pod[kk] = vv
            else: out[r.plan_id] = {"status": "UNWRAPPED", "detail": f"unknown key {k}"}; break
        else:
            try: kv.validate(m, "1.31", strict=True); out[r.plan_id] = {"status": "schema_valid_when_wrapped", "detail": "fragment placed in a minimal Deployment; field names/types valid for k8s 1.31; not applied to a cluster"}
            except Exception as e: out[r.plan_id] = {"status": "SCHEMA_INVALID", "detail": str(e).splitlines()[0][:200]}
(ROOT / "reports/batch03_wrapped_config_check.json").write_text(json.dumps(out, indent=1))
for k, v in out.items(): print(k, v["status"], "-", v["detail"])
