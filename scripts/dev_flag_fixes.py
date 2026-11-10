"""Development harness for the three flag defects test v4 exposed (sprint priority 2). Development data only.

Sources (none is in test v5):
  - MATH train, five subjects (EleutherAI/hendrycks_math, MIT licence), fetched to ~/.cache/touchstone/sprint_dev/
  - test v4's prealgebra draws: v4 is spent, so any score on it here is a development number; v4's published numbers stand
  - GSM8K train (regression: plain-text working must not change)

    python scripts/dev_flag_fixes.py latex      # writes out/dev_flag_latex.json
"""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import screen  # noqa: E402

DEV = Path.home() / ".cache" / "touchstone" / "sprint_dev"
SUBJECTS = ["algebra", "number_theory", "counting_and_probability", "geometry", "prealgebra"]
OFFSETS = [-9, -4, -2, 2, 3, 7, 12]  # the same wrong-answer offsets test v4 planted


def boxed_int(sol):
    return re.findall(r"\\boxed\{(\d+)\}", sol)


def plant(sol, rng):
    return re.sub(r"\\boxed\{(\d+)\}", lambda m: "\\boxed{" + str(int(m.group(1)) + rng.choice(OFFSETS)) + "}", sol)


def decide(a, n):
    enough = a["checked"] >= max(screen.MIN_WORKED, 0.2 * n)
    return bool(enough and a["rate"] is not None and a["rate"] >= screen.NOISY_EQ_RATE)


def row_stats(comps):
    a = screen.arithmetic_consistency(comps)
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in a.items()} | {"flag": decide(a, len(comps)), "n": len(comps)}


def latex():
    v4 = {r["problem"] for r in json.loads((Path.home() / ".cache" / "touchstone" / "v4" / "prealgebra.json").read_text())}
    out = {"math_train": {}, "v4_prealgebra_dev_rescore": {}, "gsm8k_train": {}}
    rng = random.Random(20261110)
    for sub in SUBJECTS:
        rows = [r for r in json.loads((DEV / f"math_{sub}.train.json").read_text()) if boxed_int(r["solution"]) and r["problem"] not in v4]
        rng.shuffle(rows)
        per = min(150, len(rows) // 3)
        draws = [rows[i * per:(i + 1) * per] for i in range(3)]
        out["math_train"][sub] = {"clean_0": row_stats([r["solution"] for r in draws[0]]), "clean_1": row_stats([r["solution"] for r in draws[1]])}
        pick = set(rng.sample(range(per), int(0.3 * per)))
        out["math_train"][sub]["planted_30"] = row_stats([plant(r["solution"], rng) if i in pick else r["solution"] for i, r in enumerate(draws[2])])
    for f in ["clean_prealgebra_0", "clean_prealgebra_1", "clean_prealgebra_2", "planted_prealgebra_30"]:
        rows = [json.loads(x) for x in (ROOT / "examples" / "test4" / "datasets" / f"{f}.jsonl").read_text().splitlines()]
        out["v4_prealgebra_dev_rescore"][f] = row_stats([r["completion"] for r in rows])
    g = [json.loads(x)["answer"] for x in (Path.home() / ".cache" / "touchstone" / "gsm8k_train.jsonl").read_text().splitlines()]
    a = screen.arithmetic_consistency(g)
    out["gsm8k_train"] = {"checked": a["checked"], "inconsistent": a["inconsistent"], "unsupported_final": a["unsupported_final"],
                          "unsupported_share": round(a["unsupported_final"] / a["checked"], 4), "rate": round(a["rate"], 4)}
    clean = [v for s in out["math_train"].values() for k, v in s.items() if k.startswith("clean")]
    planted = [v for s in out["math_train"].values() for k, v in s.items() if k.startswith("planted")]
    out["summary"] = {"math_clean_draws_flagged": f"{sum(v['flag'] for v in clean)} of {len(clean)}",
                      "math_clean_rate_range": [min(v["rate"] for v in clean), max(v["rate"] for v in clean)],
                      "math_planted_flagged": f"{sum(v['flag'] for v in planted)} of {len(planted)}",
                      "math_planted_rate_range": [min(v["rate"] for v in planted), max(v["rate"] for v in planted)]}
    (ROOT / "out" / "dev_flag_latex.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["summary"], indent=1))
    print(json.dumps(out["v4_prealgebra_dev_rescore"]))
    print(json.dumps(out["gsm8k_train"]))
    for s, v in out["math_train"].items():
        print(s, {k: (x["rate"], x["checked"], x["unsupported_final"]) for k, x in v.items()})


if __name__ == "__main__":
    {"latex": latex}[sys.argv[1]]()
