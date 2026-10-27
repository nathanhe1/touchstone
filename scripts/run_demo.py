"""Appraise the six sample vendor environments against the free public baseline.

    python3 scripts/run_demo.py            # full run, about 30 minutes on 4 CPU cores
    python3 scripts/run_demo.py --quick    # smoke test, a couple of minutes
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone.appraise import run  # noqa: E402
from touchstone.rl import ToyGRPO  # noqa: E402

VENDORS = ["northwind_arith", "mirror_strings", "clone_arith", "quickgrade_arith", "shapeonly_arith", "hintleak_arith"]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "out" / "appraisals.json"))
    a = ap.parse_args()
    trainer = ToyGRPO(steps=20) if a.quick else ToyGRPO()
    vendors = VENDORS[:2] if a.quick else VENDORS
    run([ROOT / "envs" / v for v in vendors], ROOT / "envs" / "public_arith", ROOT / "vault", a.out,
        trainer=trainer, log=lambda m: print(m, flush=True))
