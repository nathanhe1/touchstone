"""Label checks on the all-data-types eval (examples/coverage_eval). NEW and SMALL; not test v3.

Resumable, one case at a time. `--part dev` sets thresholds; `--part eval` is reported.

    python scripts/eval_coverage.py --part dev
    python scripts/eval_coverage.py --part eval
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import coverage, data  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--part", required=True, choices=["dev", "eval"])
a = ap.parse_args()
F = ROOT / "out" / f"coverage_eval_{a.part}.json"
res = json.loads(F.read_text()) if F.exists() else {}
EX = ROOT / "examples" / "coverage_eval"
for m in json.loads((EX / "manifest.json").read_text()):
    if m["part"] != a.part or m["id"] in res:
        continue
    t = time.time()
    ex = data.load_dataset(EX / m["path"])
    dtype = coverage.detect_type(ex)
    r = coverage.label_checks(dtype, ex)
    r = {k: v for k, v in r.items() if k != "rows"}
    res[m["id"]] = dict(r, dtype=dtype, truth=m["noisy_labels"], noise=m["noise"], source=m["source"], seconds=round(time.time() - t))
    F.write_text(json.dumps(res, indent=1))
    print(m["id"], json.dumps(res[m["id"]])[:220], flush=True)
rows = list(res.values())
tp = sum(r["noisy"] and r["truth"] for r in rows)
fp = sum(r["noisy"] and not r["truth"] for r in rows)
fn = sum(not r["noisy"] and r["truth"] for r in rows)
print(f"{a.part}: precision {tp / (tp + fp) if tp + fp else None} recall {tp / (tp + fn) if tp + fn else None} n={len(rows)}")
