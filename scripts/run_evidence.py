"""Run the CLI on every sample environment and dataset, and compile the evidence table.

    python scripts/run_evidence.py --envs --quick       # six planted-failure environments + the free baseline
    python scripts/run_evidence.py --datasets --quick   # good, bad, contaminated and useless datasets
    python scripts/run_evidence.py --table              # rebuild out/evidence.md from existing reports

Each appraisal is a normal `touchstone appraise` run; reports land in out/evidence/<name>/.
"""
from __future__ import annotations

import argparse
import subprocess
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))



REPORTS = ROOT / "out" / "evidence"

ENVS = {  # name -> (planted failure, what should catch it)
    "northwind_arith": ("none: honest final-answer grader", "should be priced"),
    "mirror_strings": ("none, but a different skill (reversal)", "transfer measured on the strings suite"),
    "clone_arith": ("80% copied from the free public set", "public overlap"),
    "quickgrade_arith": ("grader accepts any reply containing the answer", "grader audit (hedging)"),
    "shapeonly_arith": ("grader only checks the number of digits", "grader audit (same-shape wrong answers)"),
    "hintleak_arith": ("prompt carries the answer", "grader audit (copy a prompt span)"),
    "public_arith": ("free baseline", "reference point"),
}

DATASETS = {
    "good_cot": "good: correct answers with worked steps",
    "good_short": "good: correct answers only (chat 'messages' format)",
    "noisy_50": "bad: half the answers wrong",
    "wrong_all": "bad: every answer wrong",
    "offtopic": "useless: text-editing tasks, no arithmetic",
    "contaminated": "bad: 25% reworded copies of held-out suite items",
    "gsm8k_clone": "redundant: slice of the free GSM8K train set",
    "duplicated": "bad: 20 examples repeated 30 times",
}


def run(names, kind, quick):
    for n in names:
        out = REPORTS / f"{n}{'-quick' if quick else ''}"
        if (out / "report.json").exists():
            print(f"skip {n} (exists)")
            continue
        path = ROOT / ("envs" if kind == "env" else "examples/datasets") / (n if kind == "env" else f"{n}.jsonl")
        args = ["appraise", str(path), "--kind", kind, "--out", str(out)] + (["--quick"] if quick else [])
        print(">>", " ".join(args), flush=True)
        # one process per appraisal: MPS memory is fully returned between runs
        subprocess.run([sys.executable, "-m", "touchstone.cli"] + args, check=False)


def reforecast_all():
    """Re-grade every saved report with the current calibration files (no retraining)."""
    from touchstone.pipeline import reforecast
    from touchstone.report_md import render
    for f in sorted(REPORTS.glob("*/report.json")):
        r = reforecast(json.loads(f.read_text()))
        f.write_text(json.dumps(r, indent=2))
        (f.parent / "report.md").write_text(render(r))
        print(f"reforecast {f.parent.name}: grade {r['grade']}")


def table():
    rows = []
    for d in sorted(REPORTS.glob("*/report.json")):
        r = json.loads(d.read_text())
        name = d.parent.name
        base = name.replace("-quick", "")
        top = r["rungs"][r["measurable_at"]]
        fd = r.get("forecast_detail") or r["forecast"]
        od = r.get("overlap_detail") or r["overlap"]
        hl = fd.get("headline", fd["net"])
        rows.append({
            "name": name, "kind": r["kind"], "mode": r["mode"],
            "planted": (ENVS.get(base, (None,))[0] if r["kind"] == "env" else DATASETS.get(base)),
            "suite": r["heldout"]["name"], "grade": r["grade"], "value_per_item": r["fair_value"]["per_item"],
            "net_forecast": hl["point"], "net_lo": hl["lo"], "headline_source": hl.get("source", "forecast"),
            "net_hi": hl["hi"],
            "raw_gain_top": top["material"]["acc_gain"]["gain"],
            "placebo_gain_top": top.get("placebo", {}).get("acc_gain", {}).get("gain"),
            "hackability": r.get("grader_audit", {}).get("score"),
            "worst_exploit": r.get("grader_audit", {}).get("worst_exploit"),
            "heldout_overlap": max(od["heldout"]["rate"], od["heldout"].get("suite_share", 0)), "public_overlap": od["public"]["rate"],
            "flags": [f["code"] for f in r["flags"]], "runtime_s": r["runtime_s"],
            "measured_at_target": fd.get("measured_at_target"),
        })
    # Decision accuracy of the appraisal's ranking, good vs bad material (planted ground truth):
    # for every (good, bad) pair, is the good one ranked higher by grade, then price? Ties count half.
    good = {"northwind_arith", "mirror_strings", "good_cot", "good_short"}
    score = {x["name"]: ("FDCBA".index(x["grade"]), x["value_per_item"]) for x in rows}
    g = [n for n in score if n.replace("-quick", "") in good]
    b = [n for n in score if n.replace("-quick", "") not in good and not n.startswith("public_arith")]
    pairs = [(x, y) for x in g for y in b]
    wins = sum(1.0 if score[x] > score[y] else 0.5 if score[x] == score[y] else 0.0 for x, y in pairs)
    summary = {"good_vs_bad_decision_accuracy": round(wins / len(pairs), 3) if pairs else None, "pairs": len(pairs),
               "good": g, "bad": b}
    (ROOT / "out" / "evidence.json").write_text(json.dumps({"rows": rows, "ranking": summary}, indent=2))
    print(f"good-vs-bad decision accuracy: {summary['good_vs_bad_decision_accuracy']} over {len(pairs)} pairs")
    lines = ["| Material | Kind | Planted problem | Grade | $/item | Net gain @1.7B | Raw gain (top rung) | "
             "Placebo | Hackability | Suite overlap | Public overlap | Flags |", "|" + "---|" * 12]
    for x in rows:
        hk = "-" if x["hackability"] is None else f"{100 * x['hackability']:.0f}%"
        pl = "-" if x["placebo_gain_top"] is None else f"{x['placebo_gain_top']:+.1f}"
        lines.append(f"| {x['name']} | {x['kind']} | {x['planted']} | {x['grade']} | {x['value_per_item']:,.2f} | "
                     f"{x['net_forecast']:+.1f} [{x['net_lo']:+.1f}, {x['net_hi']:+.1f}] | {x['raw_gain_top']:+.1f} | {pl} | "
                     f"{hk} | {100 * x['heldout_overlap']:.0f}% | {100 * x['public_overlap']:.0f}% | "
                     f"{', '.join(x['flags']) or 'none'} |")
    (ROOT / "out" / "evidence.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--envs", action="store_true")
    ap.add_argument("--datasets", action="store_true")
    ap.add_argument("--only", help="comma-separated subset of names")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--reforecast", action="store_true", help="re-grade saved reports with the current calibration")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    if a.envs:
        run([n for n in ENVS if not only or n in only], "env", a.quick)
    if a.datasets:
        run([n for n in DATASETS if not only or n in only], "dataset", a.quick)
    if a.reforecast:
        reforecast_all()
    table()
