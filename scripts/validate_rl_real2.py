"""Forecast validation, round 3: GRPO at SmolLM2-135M predicts 360M, with the measurement noise cut.

Round 2 (scripts/validate_rl_real.py) was noise-limited: 150 suite items, 2 proxy seeds and 1 target
seed, and two proxy seeds agreed on only 87% of pairwise decisions. This sweep:

* 26 NEW arithmetic-domain environments that differ in realistic ways (difficulty, related vs
  unrelated skills, off-topic share, reward noise, pool size, leaky prompts, lax graders), split
  BEFORE any run into 13 development and 13 held-out environments (SPLIT below, fixed by a seeded
  shuffle and committed with the pre-registration in METHOD.md, section 6, "Round 3");
* 3 seeds at the proxy (135M) and 3 at the target (360M), the same quick GRPO recipe at both;
* a 600-item held-out arithmetic suite (200 per part), with per-item results stored so that pair
  standard errors can be bootstrapped;
* checkpoint evaluations at the proxy (steps 10, 20, 30) for checkpoint-averaged signals.

    python scripts/validate_rl_real2.py            # resumable; runs in seed-major order
    python scripts/validate_rl_real2.py --report
"""
from __future__ import annotations

import argparse
import json
import random
import string
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone import lm as L  # noqa: E402
from touchstone import measure, pipeline, suites  # noqa: E402
from touchstone.env import Task, final_answer  # noqa: E402
from touchstone.grpo import grpo  # noqa: E402

OUT = ROOT / "out" / "validation_rl_real2.json"
SEEDS = {"135M": 3, "360M": 3}
RECIPE = L.Recipe(rl_steps=30, rl_group=4, eval_max_new=48)
SUITE_ITEMS = 600
PROXY_CHECKPOINTS = (10, 20)  # plus the final step
RUN_TIMEOUT = 2400  # seconds for one run; a stalled run is skipped and retried on the next pass


def _ok_pair(a, b):
    return (a * 7 + b * 13) % 5 != 0  # hash bucket 0 is reserved for the held-out suite


def _gen(kind, rng):
    """One task of a kind -> (prompt, answer)."""
    while True:
        if kind == "add2":
            a, b = rng.randint(10, 99), rng.randint(10, 99)
        elif kind == "add3":
            a, b = rng.randint(100, 999), rng.randint(10, 99)
        elif kind == "add33":
            a, b = rng.randint(100, 999), rng.randint(100, 999)
        elif kind == "add4":
            a, b = rng.randint(1000, 9999), rng.randint(100, 999)
        elif kind == "carry":
            a, b = rng.randint(100, 999), rng.randint(10, 99)
            if (a % 10 + b % 10) < 10 or (a // 10 % 10 + b // 10 % 10) < 9:
                continue
        elif kind == "nocarry":
            a, b = rng.randint(100, 999), rng.randint(10, 99)
            if (a % 10 + b % 10) >= 10 or (a // 10 % 10 + b // 10 % 10) >= 10:
                continue
        elif kind == "add3ops":
            a, b, c = rng.randint(10, 99), rng.randint(10, 99), rng.randint(10, 99)
            return f"Add {a}, {b} and {c}. Reply with only the total.", str(a + b + c)
        elif kind == "sub":
            a, b = rng.randint(100, 999), rng.randint(10, 99)
            return f"Subtract {b} from {a}. Reply with only the number.", str(a - b)
        elif kind == "mul":
            a, b = rng.randint(2, 9), rng.randint(10, 99)
            return f"Multiply {a} by {b}. Reply with only the number.", str(a * b)
        elif kind == "strings":
            s = "".join(rng.choice(string.ascii_lowercase[:12]) for _ in range(rng.randint(4, 7)))
            return f"Reverse the letters in {s}. Reply with only the result.", s[::-1]
        elif kind == "word":
            a, b = rng.randint(100, 999), rng.randint(10, 99)
            if not _ok_pair(a, b):
                continue
            who = rng.choice(["Lena", "Omar", "Priya", "Jonas", "Mei"])
            thing = rng.choice(["marbles", "stamps", "coins", "shells", "cards"])
            return f"{who} has {a} {thing} and gets {b} more. How many {thing} now? Reply with only the number.", str(a + b)
        elif kind == "spaced":
            a, b = rng.randint(100, 999), rng.randint(10, 99)
            if not _ok_pair(a, b):
                continue
            return f"Compute: {' '.join(str(a))} + {' '.join(str(b))} (digits are spaced). Reply with only the number.", str(a + b)
        else:
            raise ValueError(kind)
        if _ok_pair(a, b):
            return f"Calculate {a} + {b}. Reply with only the number.", str(a + b)


class Env2:
    def __init__(self, name, mix, grader="exact", noise=0.0, pool=3000, leak=0.0, seed=0):
        self.name, self.grader, self.noise = name, grader, noise
        rng = random.Random(seed)
        kinds, weights = zip(*mix)
        self._tasks = []
        while len(self._tasks) < pool:
            p, a = _gen(rng.choices(kinds, weights)[0], rng)
            if leak and rng.random() < leak:
                p = p + f" (hint: {a})"
            self._tasks.append(Task(p, {"answer": a}))
        self._rng = random.Random(seed + 1)

    def tasks(self):
        return self._tasks

    def verify(self, task, output):
        ans, f = task.meta["answer"], final_answer(output)
        g = self.grader
        if g == "exact":
            r = float(f == ans)
        elif g == "number_present":
            r = float(any(ch.isdigit() for ch in output))
        elif g == "tol2":
            try:
                r = float(f is not None and abs(float(f) - float(ans)) <= 2)
            except ValueError:
                r = 0.0
        elif g == "last_digit":
            r = float(f is not None and f[-1:] == ans[-1:])
        elif g == "format_bonus":
            r = 0.5 * float(f is not None and f.lstrip("-").isdigit()) + 0.5 * float(f == ans)
        elif g == "answer_tag":  # reads the number after "Answer:", which the prompt never asks for (format mismatch)
            tail = output.rsplit("Answer:", 1)
            r = float(len(tail) == 2 and final_answer(tail[1]) == ans)
        else:
            raise ValueError(g)
        if self.noise and self._rng.random() < self.noise:
            r = 1.0 - r
        return r


def environments():
    E = {}

    def add(name, mix, **kw):
        E[name] = Env2(name, mix, seed=1000 + len(E), **kw)
    add("mix_honest", [("add2", 1), ("add3", 1), ("add33", 1)])
    add("add4_honest", [("add4", 1)])
    add("carry_honest", [("carry", 1)])
    add("nocarry_honest", [("nocarry", 1)])
    add("add3ops_honest", [("add3ops", 1)])
    add("word_honest", [("word", 1)])
    add("spaced_honest", [("spaced", 1)])
    add("sub_honest", [("sub", 1)])
    add("mul_honest", [("mul", 1)])
    add("add_sub_mix", [("add3", 1), ("sub", 1)])
    add("offtopic25", [("add3", 3), ("strings", 1)])
    add("offtopic50", [("add3", 1), ("strings", 1)])
    add("offtopic75", [("add3", 1), ("strings", 3)])
    add("strings_only", [("strings", 1)])
    add("noise10", [("add3", 1)], noise=0.10)
    add("noise20", [("add3", 1)], noise=0.20)
    add("noise45", [("add3", 1)], noise=0.45)
    add("pool10", [("add3", 1)], pool=10)
    add("pool100", [("add3", 1)], pool=100)
    add("leak30", [("add3", 1)], leak=0.30)
    add("leak100", [("add3", 1)], leak=1.0)
    add("grader_number", [("add3", 1)], grader="number_present")
    add("grader_tol2", [("add3", 1)], grader="tol2")
    add("grader_lastdigit", [("add3", 1)], grader="last_digit")
    add("grader_format_bonus", [("add3", 1)], grader="format_bonus")
    add("answer_tag_mismatch", [("add3", 1)], grader="answer_tag")
    return E


def split():
    """Fixed before any run: seeded shuffle of the sorted names, first half development."""
    names = sorted(environments())
    random.Random(20261030).shuffle(names)
    h = len(names) // 2
    return {"dev": sorted(names[:h]), "heldout": sorted(names[h:])}


def _bits(v):
    return "".join("1" if x >= 0.5 else "0" for x in v)


def one(name, size, seed):
    """One run in a fresh process (MPS shape caches slow long-lived processes; see validate_rl_real.py)."""
    suite = suites.arithmetic_suite(SUITE_ITEMS)
    env = environments()[name]
    lm = L.LM(size)
    before = pipeline.base_eval(lm, suite, RECIPE.eval_max_new)
    ckpts = {}

    def on_step(step, tuned):
        if size == "135M" and step in PROXY_CHECKPOINTS:
            ev = measure.evaluate(tuned, suite, RECIPE.eval_max_new)
            ckpts[str(step)] = {"acc": _bits(ev["acc"]), "cand": [round(x, 4) for x in ev["cand"]]}
    tuned, info = grpo(lm, env, RECIPE, seed=int(seed), on_step=on_step)
    ev = measure.evaluate(tuned, suite, RECIPE.eval_max_new)
    ckpts[str(RECIPE.rl_steps)] = {"acc": _bits(ev["acc"]), "cand": [round(x, 4) for x in ev["cand"]]}
    r = {"acc_gain": measure.paired_gain(before["acc"], ev["acc"])["gain"],
         "cand_gain": measure.paired_gain(before["cand"], ev["cand"])["gain"],
         "reward_first": info["train_reward_first"], "reward_last": info["train_reward_last"], "curve": info["curve"],
         "train_s": info["seconds"], "ckpts": ckpts,
         "base": {"acc": _bits(before["acc"]), "cand": [round(x, 4) for x in before["cand"]]}}
    print("RESULT " + json.dumps(r), flush=True)


def run(only=None):
    import subprocess
    res = json.loads(OUT.read_text()) if OUT.exists() else {"runs": {}, "base": {}, "split": split()}
    t0 = time.time()
    names = list(environments())
    for seed in range(max(SEEDS.values())):  # seed-major: every env gets seed 0 at both sizes first
        for size in ("135M", "360M"):
            if seed >= SEEDS[size] or (only and size != only):
                continue
            for name in names:
                key = f"{name}|{size}|{seed}"
                if key in res["runs"]:
                    continue
                try:
                    p = subprocess.run([sys.executable, __file__, "--one", name, size, str(seed)], capture_output=True,
                                       text=True, cwd=ROOT, timeout=RUN_TIMEOUT)
                except subprocess.TimeoutExpired:
                    print(f"{key}: TIMEOUT after {RUN_TIMEOUT}s", flush=True)
                    continue
                line = [x for x in p.stdout.splitlines() if x.startswith("RESULT ")]
                if not line:
                    print(f"{key}: FAILED\n{p.stderr[-800:]}", flush=True)
                    continue
                r = json.loads(line[0][7:])
                res["base"][size] = r.pop("base")
                res["runs"][key] = r
                OUT.write_text(json.dumps(res))
                print(f"{key}: acc {r['acc_gain']:+.2f} cand {r['cand_gain']:+.2f} reward {r['reward_first']:.2f}->"
                      f"{r['reward_last']:.2f} train {r['train_s']:.0f}s ({time.time() - t0:.0f}s)", flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--one", nargs=3, metavar=("ENV", "SIZE", "SEED"))
    ap.add_argument("--only", choices=["135M", "360M"])
    ap.add_argument("--print-split", action="store_true")
    a = ap.parse_args()
    if a.one:
        one(*a.one)
    elif a.print_split:
        print(json.dumps(split(), indent=1))
    else:
        run(a.only)
