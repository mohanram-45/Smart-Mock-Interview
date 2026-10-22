"""Run the full dataset audit (READ-ONLY on data/). Usage:  python audit/run_audit.py [--root PROJECT_ROOT] [--out OUTPUT_DIR]
Requires: pandas, numpy, scikit-learn, scipy (no new dependencies). Writes ONLY into audit/output (or --out).
Order matters: 01 creates processed_annotated.pkl used by 02-06 (intermediate; safe to delete)."""
import subprocess, sys
from pathlib import Path
here = Path(__file__).resolve().parent
extra = sys.argv[1:]
for s in ["01_integrity.py","01b_generator_reproducibility.py","02_similarity.py","03_accuracy_checks.py",
          "04_diversity_coverage.py","05_domain_and_benchmark_checks.py","06_manual_review_log.py"]:
    print(f"== {s}")
    r = subprocess.run([sys.executable, str(here/s), *extra], capture_output=True, text=True)
    print("   exit", r.returncode)
    if r.returncode: print(r.stderr[-2000:]); sys.exit(r.returncode)
print("audit complete")
