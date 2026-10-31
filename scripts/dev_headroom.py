"""Harder-suite pilot (METHOD.md, Round 3 forecast addendum). Development environments only.

    python scripts/dev_headroom.py base     # 360M base accuracy on each candidate; picks the suite
    python scripts/dev_headroom.py pilot    # 4 environments, both sizes, seed 0, resumable
"""
import json
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import validate_rl_real2 as V  # noqa: E402
from touchstone import lm as L  # noqa: E402
from touchstone import measure, suites  # noqa: E402
from touchstone.grpo import grpo  # noqa: E402

F = ROOT / "out" / "dev_headroom.json"
PILOT = ["add3ops_honest", "add_sub_mix", "grader_lastdigit", "leak100"]
N, SEED = 300, 77001


def hard(kind):
    rng = random.Random(SEED)
    items, seen = [], set()
    while len(items) < N:
        if kind == "hard_c":
            a, b, c = rng.randint(100, 999), rng.randint(100, 999), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 != 0 or (a, b, c) in seen:
                continue
            seen.add((a, b, c))
            items.append(suites.Item(f"What is {a} + {b} + {c}? Answer with the number only.", str(a + b + c), "numeric", part=kind))
            continue
        a, b = rng.randint(1000, 9999), rng.randint(100, 999) if kind == "hard_a" else rng.randint(1000, 9999)
        if (a * 7 + b * 13) % 5 != 0 or (a, b) in seen:
            continue
        seen.add((a, b))
        items.append(suites.Item(f"What is {a} + {b}? Answer with the number only.", str(a + b), "numeric", part=kind))
    suites.with_distractors(items, SEED)
    return suites.Suite(kind, kind, kind, items, "dev_headroom")


def load():
    return json.loads(F.read_text()) if F.exists() else {"base": {}, "runs": {}}


def base():
    res = load()
    lm = L.LM("360M")
    for k in ("hard_a", "hard_b", "hard_c"):
        if k in res["base"]:
            continue
        ev = measure.evaluate(lm, hard(k), V.RECIPE.eval_max_new)
        res["base"][k] = round(100 * measure.mean(ev["acc"]), 2)
        F.write_text(json.dumps(res, indent=1))
        print(k, res["base"][k], flush=True)
    res["chosen"] = next((k for k, v in res["base"].items() if 40 <= v <= 60), None)
    F.write_text(json.dumps(res, indent=1))
    print("chosen", res["chosen"], flush=True)


def one(name, size):
    res = load()
    suite = hard(res["chosen"])
    lm = L.LM(size)
    before = measure.evaluate(lm, suite, V.RECIPE.eval_max_new)
    tuned, _ = grpo(lm, V.environments()[name], V.RECIPE, seed=0)
    ev = measure.evaluate(tuned, suite, V.RECIPE.eval_max_new)
    print("RESULT " + json.dumps({"acc": measure.paired_gain(before["acc"], ev["acc"])["gain"],
                                  "base": 100 * measure.mean(before["acc"])}), flush=True)


def pilot():
    res = load()
    if not res.get("chosen"):
        print("no candidate suite in the 40-60% band; pilot not run", flush=True)
        return
    for size in ("135M", "360M"):
        for name in PILOT:
            key = f"{name}|{size}"
            if key in res["runs"]:
                continue
            t = time.time()
            r = V.one_run([sys.executable, __file__, "one", name, size])
            line = [x for x in (r[0] if r else "").splitlines() if x.startswith("RESULT ")]
            if not line:
                print(key, "FAILED", (r[1][-300:] if r else "timeout"), flush=True)
                continue
            res["runs"][key] = json.loads(line[0][7:])
            F.write_text(json.dumps(res, indent=1))
            print(key, res["runs"][key], f"{time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "base":
        base()
    elif sys.argv[1] == "one":
        one(sys.argv[2], sys.argv[3])
    else:
        pilot()
