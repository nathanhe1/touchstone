"""Timing table from runner results: wall, load, base evaluation, training time and peak memory per run.

    python scripts/h5_timing_table.py out/h5/timing out/h5/timing2 ...
"""
import json
import sys
from pathlib import Path

rows = []
for d in sys.argv[1:]:
    for f in sorted(Path(d).glob("*.json")):
        r = json.loads(f.read_text())
        j = r.get("job", {})
        if "wall_s" not in r:
            continue
        rows.append((j.get("size"), j.get("arm"), j.get("family"), r.get("recipe", {}).get("max_new"), r.get("wall_s"), r.get("load_s"),
                     r.get("eval_s"), r.get("train_s"), r.get("peak_mem_gb"), r.get("base_acc"), r.get("gain"), r.get("loss_last"),
                     r.get("rollouts_truncated"), Path(d).name))
print("| rung | arm | family | reply limit | wall s | load s | base eval s | train s | peak GB | base acc | gain | loss_last | rollouts cut | set |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    print("| " + " | ".join("" if x is None else str(x) for x in r) + " |")
