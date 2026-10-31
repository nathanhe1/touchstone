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
import os
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

OUT = ROOT / "out" / os.environ.get("SWEEP_FILE", "validation_rl_real2.json")
SEEDS = {"135M": 3, "360M": 3}
RECIPE = L.Recipe(rl_steps=30, rl_group=4, eval_max_new=48)
SUITE_ITEMS = 600
EXTENSION = ["pool20", "pool30_mix", "pool300", "pool50"]
PROXY_CHECKPOINTS = (10, 20)  # plus the final step
RUN_TIMEOUT = 2100  # seconds for one run; a stalled run is skipped and retried on the next pass


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
    # Held-out extension, pre-registered in METHOD.md after the development interim: the original split put every
    # small-pool environment in development, so held-out could not test a pool-size term.
    add("pool20", [("add3", 1)], pool=20)
    add("pool50", [("add3", 1)], pool=50)
    add("pool300", [("add2", 1), ("add3", 1)], pool=300)
    add("pool30_mix", [("add3", 1), ("sub", 1)], pool=30)
    return E


def split():
    """Fixed before any run: seeded shuffle of the sorted names, first half development."""
    names = sorted(n for n in environments() if n not in EXTENSION)
    random.Random(20261030).shuffle(names)
    h = len(names) // 2
    return {"dev": sorted(names[:h]), "heldout": sorted(names[h:] + EXTENSION)}


def platform_tag():
    import torch
    return f"{L.device()}|torch {torch.__version__.split('+')[0]}"


def _bits(v):
    return "".join("1" if x >= 0.5 else "0" for x in v)


def one(name, size, seed):
    """One run in a fresh process (MPS shape caches slow long-lived processes; see validate_rl_real.py)."""
    sname = os.environ.get("SWEEP_SUITE", "arithmetic")
    suite = suites.arithmetic_suite(SUITE_ITEMS) if sname == "arithmetic" else suites.arithmetic_hard(sname)
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
         "train_s": info["seconds"], "ckpts": ckpts, "platform": platform_tag(),
         "base": {"acc": _bits(before["acc"]), "cand": [round(x, 4) for x in before["cand"]]}}
    print("RESULT " + json.dumps(r), flush=True)


def wait_for_memory(min_free_pct=20):
    """Between runs, wait for real memory headroom. Swap used is not a useful gate: macOS leaves other apps'
    idle pages there indefinitely, even with most of memory free."""
    import re
    import subprocess
    if sys.platform != "darwin":
        return
    while True:
        m = re.search(r"free percentage: (\d+)%", subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout)
        if not m or int(m.group(1)) >= min_free_pct:
            return
        print(f"paused: {m.group(1)}% memory free", flush=True)
        time.sleep(120)


def one_run(cmd):
    """Run one training process; on timeout kill its whole group (subprocess.run blocks on a hung child)."""
    import os
    import signal
    import subprocess
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=ROOT, start_new_session=True)
    try:
        return p.communicate(timeout=RUN_TIMEOUT) + (p.returncode,)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        try:  # a process in a kernel-level GPU wait can ignore SIGKILL; do not wait on it forever
            p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        return None


def in_shard(key, shard):
    """Stable membership: a key belongs to one shard whatever each shard has finished."""
    import zlib
    i, n = map(int, shard.split("/"))
    return zlib.crc32(key.encode()) % n == i


def run(only=None, shard=None, sizes=("135M", "360M"), seeds=None, envs=None):
    """shard 'i/n' runs the keys hashed to it and writes its own file; --merge folds shard files into OUT."""
    out = OUT if not shard else OUT.with_suffix(f".shard{shard.split('/')[0]}.json")
    res = json.loads(out.read_text()) if out.exists() else (json.loads(OUT.read_text()) if OUT.exists() else {"runs": {}, "base": {}, "split": split()})
    t0 = time.time()
    names = envs or list(environments())
    # Seed-major, development environments first: an interim development score exists after seed 0 at both
    # sizes on those 13, long before the sweep ends. Order changes nothing about what is measured.
    res["split"] = split()  # adds the pre-registered extension; the original 26 keep their sides
    dev = [n for n in names if n in res["split"]["dev"]]
    held = [n for n in names if n not in res["split"]["dev"]]
    order = [(seed, group, size) for seed in range(seeds or max(SEEDS.values())) for group in (dev, held) for size in sizes]
    for attempt in range(3):  # a failed run gets two more chances, here rather than in a manual rerun
        for seed, group, size in order:
            if seed >= (seeds or SEEDS.get(size, 3)) or (only and size != only):
                continue
            for name in group:
                key = f"{name}|{size}|{seed}"
                if key in res["runs"]:
                    continue
                if shard and not in_shard(key, shard):
                    continue
                wait_for_memory()
                done = one_run([sys.executable, __file__, "--one", name, size, str(seed)])
                if done is None:
                    print(f"{key}: TIMEOUT after {RUN_TIMEOUT}s", flush=True)
                    continue
                stdout, stderr, _ = done
                line = [x for x in stdout.splitlines() if x.startswith("RESULT ")]
                if not line:
                    print(f"{key}: FAILED\n{stderr[-800:]}", flush=True)
                    continue
                r = json.loads(line[0][7:])
                res["base"][size] = r.pop("base")
                res["runs"][key] = r
                out.write_text(json.dumps(res))
                print(f"{key}: acc {r['acc_gain']:+.2f} cand {r['cand_gain']:+.2f} reward {r['reward_first']:.2f}->"
                      f"{r['reward_last']:.2f} train {r['train_s']:.0f}s ({time.time() - t0:.0f}s)", flush=True)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--one", nargs=3, metavar=("ENV", "SIZE", "SEED"))
    ap.add_argument("--only", choices=["135M", "360M"])
    ap.add_argument("--print-split", action="store_true")
    ap.add_argument("--shard", help="i/n: this process takes every n-th pending run (for many-GPU or large-memory machines)")
    ap.add_argument("--sizes", default="135M,360M", help="comma list, for example 1.7B or 7B")
    ap.add_argument("--seeds", type=int)
    ap.add_argument("--envs", help="comma list of environment names (default: all)")
    ap.add_argument("--allow-mixed-platforms", action="store_true", help="only after checking the platforms agree")
    ap.add_argument("--merge", action="store_true", help="fold out/validation_rl_real2.shard*.json into the main file")
    a = ap.parse_args()
    if a.one:
        one(*a.one)
    elif a.print_split:
        print(json.dumps(split(), indent=1))
    elif a.merge:
        res = json.loads(OUT.read_text())
        LOCAL = "mps|torch 2.8.0"  # runs from before the tag existed
        for f in sorted(OUT.parent.glob("validation_rl_real2.shard*.json")):
            d = json.loads(f.read_text())
            tags = {r.get("platform", LOCAL) for r in list(res["runs"].values()) + list(d["runs"].values())}
            if len(tags) > 1 and not a.allow_mixed_platforms:
                raise SystemExit(f"refusing to merge runs from different platforms: {sorted(tags)}. Compare them "
                                 "on shared environments first; see METHOD.md.")
            res["runs"].update(d["runs"])
            res["base"].update(d["base"])
        OUT.write_text(json.dumps(res))
        print(len(res["runs"]), "runs")
    else:
        run(a.only, a.shard, tuple(a.sizes.split(",")), a.seeds, envs=a.envs.split(",") if a.envs else None)
