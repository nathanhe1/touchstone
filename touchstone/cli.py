"""touchstone: appraise a post-training dataset or RL environment.

    touchstone appraise data.jsonl --kind dataset [--suite word_math] [--quick] [--out report_dir]
    touchstone appraise envs/my_env --kind env [--suite arithmetic] [--quick] [--out report_dir]
    touchstone suites                      # list built-in held-out suites
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from pathlib import Path


def _detect_kind(path: Path) -> str:
    if path.is_dir() or path.suffix == ".py":
        return "env"
    return "dataset"


def cmd_appraise(a) -> int:
    from . import data as datamod
    from . import env as envmod
    from . import pipeline, suites
    from .report_md import render

    path = Path(a.path)
    if not path.exists():
        print(f"error: {path} does not exist", file=sys.stderr)
        return 2
    kind = a.kind or _detect_kind(path)
    out = Path(a.out or f"reports/{path.stem}-{time.strftime('%Y%m%d-%H%M%S')}")
    plan = pipeline.plan_for(a.quick, kind)
    plan.backend = pipeline.select_backend(a.device, kind)
    if a.seeds:
        plan.seeds = {s: a.seeds for s in plan.rungs}
    if a.suite_items:
        plan.suite_items = a.suite_items
    if a.steps:  # changes the recipe, so the calibrated forecast no longer strictly applies (smoke tests only)
        plan.recipe.sft_steps = plan.recipe.rl_steps = a.steps
    log_lines = []

    def log(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        log_lines.append(line)
        print(line, flush=True)

    try:
        if kind == "dataset":
            r = pipeline.appraise_dataset(path, a.suite or "word_math", plan, a.public, a.dollars_per_point, log)
        elif kind == "env":
            r = pipeline.appraise_env(path, a.suite, plan, a.public, a.dollars_per_point, log)
        else:
            print(f"error: --kind must be dataset or env (got {kind})", file=sys.stderr)
            return 2
    except (datamod.DatasetError, envmod.EnvError, suites.SuiteError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    r["device"] = plan.backend
    from .schema import public_report
    r = public_report(r)
    (out / "report.json").write_text(json.dumps(r, indent=2))
    (out / "report.md").write_text(render(r))
    (out / "run.log").write_text("\n".join(log_lines) + "\n")
    print(f"\nGrade {r['grade']} | net gain at {r['forecast']['target']}: {r['forecast']['value']:+.1f} pts "
          f"[{r['forecast']['lo']:+.1f}, {r['forecast']['hi']:+.1f}] | "
          f"value ${r['fair_value']['per_item']:,.2f}/item | flags: {', '.join(f['code'] for f in r['flags']) or 'none'}")
    print(f"Report: {out / 'report.md'}")
    return 0


def cmd_suites(a) -> int:
    from . import suites
    for name, fn in suites.BUILTIN.items():
        s = fn()
        print(f"{name:12s} {len(s.items)} items  {s.domain}")
    print("\nOr pass --suite path/to/suite.jsonl with lines {\"prompt\": ..., \"answer\": ...}")
    return 0


def main(argv=None) -> int:
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(prog="touchstone", description="Appraise post-training data and RL environments.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("appraise", help="appraise a dataset (.jsonl) or an RL environment (folder with env.py)")
    p.add_argument("path")
    p.add_argument("--kind", choices=["dataset", "env"], help="default: env for a folder or .py file, dataset otherwise")
    p.add_argument("--suite", help="held-out suite: word_math, arithmetic, strings, or a .jsonl file "
                                  "(default: word_math for datasets, ENV.domain for environments)")
    p.add_argument("--public", help="free public baseline to check overlap against (.jsonl dataset or env folder)")
    p.add_argument("--quick", action="store_true", help="135M rung only, 1 seed, 120 suite items")
    p.add_argument("--device", choices=["auto", "mps", "mlx", "cpu"], default="auto",
                   help="auto/mps: PyTorch on the Apple GPU (CPU fallback with a warning); mlx: Apple MLX for dataset "
                        "fine-tuning and evaluation; cpu: force CPU")
    p.add_argument("--seeds", type=int, help="override seeds per rung")
    p.add_argument("--suite-items", type=int, help="override the number of held-out items scored")
    p.add_argument("--steps", type=int, help="override training steps (smoke tests; breaks forecast calibration)")
    p.add_argument("--dollars-per-point", type=float, default=250_000.0,
                   help="what one held-out accuracy point is worth to the buyer (assumption; default 250000)")
    p.add_argument("--out", help="output folder (default reports/<name>-<timestamp>)")
    p.set_defaults(fn=cmd_appraise)
    s = sub.add_parser("suites", help="list built-in held-out suites")
    s.set_defaults(fn=cmd_suites)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
