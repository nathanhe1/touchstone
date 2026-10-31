"""Fresh held-out forecast set (METHOD.md, Round 3 fresh held-out). Never scored until candidates are frozen.

32 unseen environments in 4 families that are not arithmetic: strings, word problems, unit conversion and
reading code. Each family crosses the same 8 conditions, fixed in advance and not selected for spread. Every
environment is scored on its family's own held-out suite, so pairs are compared WITHIN a family, where
gains on one suite are comparable. The grader compares strings only: no vendor code runs.

    python scripts/validate_rl_h3.py --check          # build everything, confirm no task is in a suite
    python scripts/validate_rl_h3.py --shard 0/8      # GPU box; resumable
"""
import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import validate_rl_real2 as V  # noqa: E402
from touchstone import lm as L  # noqa: E402
from touchstone import measure, pipeline, suites  # noqa: E402
from touchstone.env import Task, final_answer  # noqa: E402
from touchstone.grpo import grpo  # noqa: E402

OUT = ROOT / "out" / os.environ.get("SWEEP_FILE", "validation_rl_h3.json")
SEED = 20261031
SIZES, SEEDS = ("135M", "360M"), 3
RECIPE = V.RECIPE
L1 = "bcdfghjklmnpqrstvwxz"


def strings(rng, hard=False):
    s = "".join(rng.choice(L1) for _ in range(rng.randint(7, 10) if hard else rng.randint(4, 6)))
    k = rng.randrange(2)
    if k == 0:
        return f"Turn {s} around so its last letter comes first. Give only the result.", s[::-1]
    return f"Print the string {s} in reversed order, nothing else.", s[::-1]


def word(rng, hard=False):
    a, b, c = rng.randint(4, 15), rng.randint(5, 20), rng.randint(2, 30)
    n = rng.choice(["Tara", "Milo", "Zoe", "Ivan", "Sana"])
    k = rng.randrange(3)
    if hard:
        d = rng.randint(2, 9)
        return f"{n} packs {a} bags with {b} nuts each, eats {c} nuts and buys {d} more bags of {b}. How many nuts now? Give the number.", str(a * b - c + d * b)
    if k == 0:
        return f"{n} packs {a} bags with {b} nuts each. How many nuts is that? Give the number.", str(a * b)
    if k == 1:
        return f"{n} owns {a + b + c} shells and donates {c}. How many shells remain? Give the number.", str(a + b)
    return f"{n} walks {a} blocks, then {b} blocks, then {c} blocks. How many blocks in all? Give the number.", str(a + b + c)


UNITS = [("kilometers", "meters", 1000), ("hours", "minutes", 60), ("feet", "inches", 12), ("weeks", "days", 7),
         ("minutes", "seconds", 60), ("dozens", "items", 12), ("tons", "kilograms", 1000), ("liters", "milliliters", 1000)]


def units(rng, hard=False):
    u, v, f = rng.choice(UNITS)
    a = rng.randint(11, 99) if hard else rng.randint(2, 9)
    return f"Convert {a} {u} to {v}. Reply with the number only.", str(a * f)


def code(rng, hard=False):
    a, b = rng.randint(2, 9), rng.randint(2, 9)
    xs = [rng.randint(1, 9) for _ in range(rng.randint(3, 6))]
    k = rng.randrange(3)
    if hard:
        return f"What does this Python print? x = {xs}\nprint(sum(v * {a} for v in x if v > {b}))\nGive only the output.", str(sum(v * a for v in xs if v > b))
    if k == 0:
        return f"What does this Python print? print(len({xs}) + {a})\nGive only the output.", str(len(xs) + a)
    if k == 1:
        return f"What does this Python print? print(max({xs}) - {a})\nGive only the output.", str(max(xs) - a)
    return f"What does this Python print? print(sum({xs}))\nGive only the output.", str(sum(xs))


FAMILY = {"strings": strings, "word": word, "units": units, "code": code}
OTHER = {"strings": units, "word": strings, "units": strings, "code": strings}
CONDITIONS = ["honest", "hard", "off50", "noise20", "noise45", "pool20", "leak30", "lax_grader"]


class Env3:
    def __init__(self, family, cond, seed):
        self.name, self.cond = f"{family}_{cond}", cond
        rng = random.Random(seed)
        gen, n = FAMILY[family], 20 if cond == "pool20" else 2500
        self._tasks = []
        while len(self._tasks) < n:
            if cond == "off50" and rng.random() < 0.5:
                p, a = OTHER[family](rng)
            else:
                p, a = gen(rng, hard=cond == "hard")
            if cond == "leak30" and rng.random() < 0.3:
                p += f" (hint: {a})"
            self._tasks.append(Task(p, {"answer": a}))
        self._rng = random.Random(seed + 1)
        self.noise = {"noise20": 0.2, "noise45": 0.45}.get(cond, 0.0)

    def tasks(self):
        return self._tasks

    def verify(self, task, output):
        a, f = task.meta["answer"], final_answer(output)
        if self.cond == "lax_grader":  # pays anything of the right length and first character
            r = float(f is not None and len(f) == len(a) and f[:1] == a[:1])
        else:
            r = float(f == a)
        if self.noise and self._rng.random() < self.noise:
            r = 1.0 - r
        return r


def environments():
    return {f"{f}_{c}": Env3(f, c, SEED + 100 * i + j) for i, f in enumerate(FAMILY) for j, c in enumerate(CONDITIONS)}


def code_suite(n=300):
    rng = random.Random(SEED + 1)
    items, seen = [], set()
    while len(items) < n:
        xs = [rng.randint(1, 9) for _ in range(rng.randint(3, 6))]
        a = rng.randint(2, 9)
        k = rng.randrange(3)
        if k == 0:
            p, ans = f"Predict the output of print(min({xs}) + {a}). Answer with the output only.", min(xs) + a
        elif k == 1:
            p, ans = f"Predict the output of print(len({xs}) * {a}). Answer with the output only.", len(xs) * a
        else:
            p, ans = f"Predict the output of print(sum({xs}) - {a}). Answer with the output only.", sum(xs) - a
        if p not in seen:
            seen.add(p)
            items.append(suites.Item(p, str(ans), "numeric", part="code"))
    suites.with_distractors(items, SEED)
    return suites.Suite("code_read", "predict the output of one line of Python", "built-in", items, f"seed {SEED}")


def units_suite(n=300):
    rng = random.Random(SEED + 2)
    items, seen = [], set()
    pairs = [("grams", "milligrams", 1000), ("meters", "centimeters", 100), ("days", "hours", 24), ("yards", "feet", 3),
             ("kilograms", "grams", 1000), ("years", "months", 12), ("decades", "years", 10), ("pounds", "ounces", 16)]
    while len(items) < n:
        u, v, f = rng.choice(pairs)
        a = rng.randint(2, 99)
        p = f"How many {v} are in {a} {u}? Answer with the number only."
        if p not in seen:
            seen.add(p)
            items.append(suites.Item(p, str(a * f), "numeric", part="units"))
    suites.with_distractors(items, SEED)
    return suites.Suite("units", "unit conversion", "built-in", items, f"seed {SEED}")


def suite_for(family):
    return {"strings": lambda: suites.strings_suite(300), "word": lambda: suites.word_math_suite(300), "units": units_suite,
            "code": code_suite}[family]()


def check():
    E = environments()
    for f in FAMILY:
        s = {i.prompt for i in suite_for(f).items}
        for n, e in E.items():
            assert not s & {t.prompt for t in e.tasks()}, n
        print(f, len(s), "items; sample", next(iter(s))[:70])
    for n, e in list(E.items())[::7]:
        t = e.tasks()[0]
        print(n, repr(t.prompt[:90]), t.meta["answer"], "unique", len({x.prompt for x in e.tasks()}))
    print(len(E), "environments")


def one(name, size, seed):
    env = environments()[name]
    suite = suite_for(name.split("_")[0])
    lm = L.LM(size)
    before = pipeline.base_eval(lm, suite, RECIPE.eval_max_new)
    tuned, info = grpo(lm, env, RECIPE, seed=int(seed))
    ev = measure.evaluate(tuned, suite, RECIPE.eval_max_new)
    print("RESULT " + json.dumps({"acc_gain": measure.paired_gain(before["acc"], ev["acc"])["gain"],
                                  "cand_gain": measure.paired_gain(before["cand"], ev["cand"])["gain"],
                                  "reward_first": info["train_reward_first"], "reward_last": info["train_reward_last"],
                                  "acc": V._bits(ev["acc"]), "base_acc": V._bits(before["acc"]), "platform": V.platform_tag()}), flush=True)


def run(shard):
    out = OUT if not shard else OUT.with_suffix(f".shard{shard.split('/')[0]}.json")
    res = json.loads(out.read_text()) if out.exists() else {"runs": {}}
    for attempt in range(3):
        for seed in range(SEEDS):
            for size in SIZES:
                for name in environments():
                    key = f"{name}|{size}|{seed}"
                    if key in res["runs"] or (shard and not V.in_shard(key, shard)):
                        continue
                    t = time.time()
                    done = V.one_run([sys.executable, __file__, "--one", name, size, str(seed)])
                    line = [x for x in (done[0] if done else "").splitlines() if x.startswith("RESULT ")]
                    if not line:
                        print(key, "FAILED", (done[1][-400:] if done else "timeout"), flush=True)
                        continue
                    res["runs"][key] = json.loads(line[0][7:])
                    out.write_text(json.dumps(res))
                    print(key, round(res["runs"][key]["acc_gain"], 2), f"{time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--one", nargs=3)
    ap.add_argument("--shard")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.one:
        one(*a.one)
    elif a.check:
        check()
    else:
        run(a.shard)
