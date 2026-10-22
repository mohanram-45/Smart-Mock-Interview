"""Run python code tests from a {id:{language,setup,solution,test}} dict under a given interpreter. usage: xrun.py tests.json out.json (run with the interpreter under test)"""
import sys, json, subprocess, tempfile, os, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
tests = json.load(open(sys.argv[1])); res = {}
def one(kv):
    k, c = kv
    if c["language"] != "python": return k, "n/a"
    body = c["solution"]
    if "SOLUTION_SRC" in c.get("test", ""): body = f"SOLUTION_SRC = {c['solution']!r}\n" + body
    code = (c.get("setup") or "") + "\n" + body + "\n" + c.get("test", "")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.py"; p.write_text(code, encoding="utf-8")
        o = subprocess.run([sys.executable, str(p)], capture_output=True, text=True, timeout=240, cwd=td, env=dict(os.environ, MPLBACKEND="Agg", PYTHONHASHSEED="0"))
    if o.returncode:
        e = (o.stderr.strip().splitlines() or ["?"])[-1][:240]
        m = re.search(r"No module named '([\w.]+)'", e)
        return k, ("SKIP:" + m.group(1)) if m else "FAIL: " + e
    return k, "ok"
with ThreadPoolExecutor(4) as ex:
    for k, v in ex.map(one, sorted(tests.items())): res[k] = v
json.dump(res, open(sys.argv[2], "w"), indent=1)
from collections import Counter
print(sys.version.split()[0], Counter(v.split(":")[0] for v in res.values()))
for k, v in res.items():
    if v.startswith(("FAIL", "SKIP")): print("  ", k, v)
