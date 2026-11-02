"""Run every bundled demo input N times in quick mode and check the results are stable.

    python scripts/run_demos.py --repeats 2      # writes out/demo_runs.json and out/demo_runs.md

Each run is a fresh `touchstone appraise --quick` process, exactly what the API runs.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo"
OUT = ROOT / "out" / "demo_runs"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=2)
    a = ap.parse_args()
    examples = json.loads((DEMO / "index.json").read_text())
    rows = []
    for ex in examples:
        for k in range(a.repeats):
            out = OUT / f"{ex['id']}-{k}"
            t0 = time.time()
            p = subprocess.run([sys.executable, "-m", "touchstone.cli", "appraise", str(DEMO / ex["path"]), "--kind",
                                ex["kind"], "--quick", "--out", str(out)], capture_output=True, text=True, cwd=ROOT)
            wall = round(time.time() - t0, 1)
            if p.returncode != 0:
                rows.append({"id": ex["id"], "run": k, "error": p.stderr[-500:], "wall_s": wall})
                continue
            r = json.loads((out / "report.json").read_text())
            rows.append({"id": ex["id"], "run": k, "grade": r["grade"], "value": r["fair_value_per_item"],
                         "flags": [f["code"] for f in r["flags"]], "net": r["forecast"]["value"],
                         "net_lo": r["forecast"]["lo"], "net_hi": r["forecast"]["hi"], "device": r.get("device"),
                         "wall_s": wall})
            print(json.dumps(rows[-1]), flush=True)
    stable = {}
    for ex in examples:
        rs = [r for r in rows if r["id"] == ex["id"] and "grade" in r]
        stable[ex["id"]] = (len(rs) == a.repeats and len({r["grade"] for r in rs}) == 1
                            and len({tuple(r["flags"]) for r in rs}) == 1)
    (ROOT / "out" / "demo_runs.json").write_text(json.dumps({"runs": rows, "stable": stable}, indent=2))
    lines = ["| Demo | Run | Grade | $/item | Net gain [90%] | Flags | Wall time | Device |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "grade" not in r:
            lines.append(f"| {r['id']} | {r['run']} | error | | | | {r['wall_s']} s | |")
            continue
        net = "screening only" if r["net"] is None else f"{r['net']:+.1f} [{r['net_lo']:+.1f}, {r['net_hi']:+.1f}]"
        lines.append(f"| {r['id']} | {r['run']} | {r['grade']} | {r['value']:,.2f} | {net} | {', '.join(r['flags'])} | "
                     f"{r['wall_s']} s | {r['device']} |")
    lines.append("\nStable grade and flags across reruns: " + ", ".join(f"{k}: {'yes' if v else 'NO'}" for k, v in stable.items()))
    (ROOT / "out" / "demo_runs.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
