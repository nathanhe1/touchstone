"""Forecast validation for RL environments on REAL models: GRPO at SmolLM2-135M predicts 360M.

Twelve arithmetic environments of deliberately different value (honest graders at several
difficulties, gameable graders, a leaky prompt, a noisy grader, a tiny task pool). Each is trained
with the same GRPO recipe at 135M (2 seeds) and 360M (1 seed) and scored on the held-out
`arithmetic` suite (150 items). The primary metric is accuracy-to-accuracy: does the ranking of
environments by held-out accuracy gain at 135M match the ranking at 360M?

    python scripts/validate_rl_real.py              # resumable, ~4 h on an M5
    python scripts/validate_rl_real.py --report
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone import env as envmod  # noqa: E402
from touchstone import forecast as fc  # noqa: E402
from touchstone import lm as L  # noqa: E402
from touchstone import measure, pipeline, suites  # noqa: E402
from touchstone.env import Task, final_answer  # noqa: E402
from touchstone.grpo import grpo  # noqa: E402

OUT = ROOT / "out" / "validation_rl_real.json"
SEEDS = {"135M": 2, "360M": 1}
RECIPE = L.Recipe(rl_steps=30, rl_group=4)  # the quick-mode GRPO recipe, identical at both sizes
SUITE_ITEMS = 150


class Synth:
    def __init__(self, name, lo_a, hi_a, lo_b, hi_b, grader="exact", noise=0.0, pool=3000, seed=0):
        self.name, self.grader, self.noise = name, grader, noise
        rng = random.Random(seed)
        self._tasks = []
        while len(self._tasks) < pool:
            a, b = rng.randint(lo_a, hi_a), rng.randint(lo_b, hi_b)
            if (a * 7 + b * 13) % 5 == 0:  # the held-out bucket
                continue
            self._tasks.append(Task(f"Calculate {a} + {b}. Reply with only the number.", {"answer": str(a + b)}))
        self._rng = random.Random(seed + 1)

    def tasks(self):
        return self._tasks

    def verify(self, task, output):
        ans = task.meta["answer"]
        f = final_answer(output)
        if self.grader == "prefix":
            ok = output.strip().startswith(ans)
        elif self.grader == "tolerant":
            try:
                ok = f is not None and abs(float(f) - float(ans)) <= 10
            except ValueError:
                ok = False
        else:
            ok = f == ans
        if self.noise and self._rng.random() < self.noise:
            ok = not ok
        return float(ok)


def environments():
    envs = {n: envmod.load(ROOT / "envs" / n) for n in
            ["northwind_arith", "public_arith", "clone_arith", "quickgrade_arith", "shapeonly_arith", "hintleak_arith"]}
    envs["add3_honest"] = Synth("add3_honest", 100, 999, 10, 99, seed=1)
    envs["add33_honest"] = Synth("add33_honest", 100, 999, 100, 999, seed=2)
    envs["add2_noisy30"] = Synth("add2_noisy30", 10, 99, 10, 99, noise=0.3, seed=3)
    envs["add2_tiny_pool"] = Synth("add2_tiny_pool", 10, 99, 10, 99, pool=20, seed=4)
    envs["add3_prefix"] = Synth("add3_prefix", 100, 999, 10, 99, grader="prefix", seed=5)
    envs["add3_tolerant"] = Synth("add3_tolerant", 100, 999, 10, 99, grader="tolerant", seed=6)
    return envs


def one(name, size, seed):
    """One training run in its own process. PyTorch MPS caches a compiled graph per tensor shape; a
    long-lived process that keeps generating and training accumulates them until every step crawls
    (round 2: a sweep slowed from 3 minutes per run to hours). A fresh process per run avoids that."""
    suite = suites.get_suite("arithmetic").subset(SUITE_ITEMS)
    env = environments()[name]
    lm = L.LM(size)
    before = pipeline.base_eval(lm, suite, RECIPE.eval_max_new)
    tuned, info = grpo(lm, env, RECIPE, seed=int(seed))
    ev = measure.evaluate(tuned, suite, RECIPE.eval_max_new)
    r = {"acc_gain": measure.paired_gain(before["acc"], ev["acc"])["gain"],
         "cand_gain": measure.paired_gain(before["cand"], ev["cand"])["gain"],
         "reward_first": info["train_reward_first"], "reward_last": info["train_reward_last"],
         "train_s": info["seconds"], "base": measure.summary(before)}
    print("RESULT " + json.dumps(r), flush=True)


def run():
    import subprocess
    res = json.loads(OUT.read_text()) if OUT.exists() else {"runs": {}, "base": {}}
    t0 = time.time()
    for size in ("135M", "360M"):
        for name in environments():
            for seed in range(SEEDS[size]):
                key = f"{name}|{size}|{seed}"
                if key in res["runs"]:
                    continue
                p = subprocess.run([sys.executable, __file__, "--one", name, size, str(seed)], capture_output=True,
                                   text=True, cwd=ROOT)
                line = [x for x in p.stdout.splitlines() if x.startswith("RESULT ")]
                if not line:
                    print(f"{key}: FAILED\n{p.stderr[-800:]}", flush=True)
                    continue
                r = json.loads(line[0][7:])
                res["base"][size] = r.pop("base")
                res["runs"][key] = r
                OUT.write_text(json.dumps(res, indent=1))
                print(f"{key}: acc {r['acc_gain']:+.1f} cand {r['cand_gain']:+.1f} reward {r['reward_first']:.2f}->"
                      f"{r['reward_last']:.2f} ({time.time() - t0:.0f}s)", flush=True)
    return res


def summarize(res):
    names = sorted({k.split("|")[0] for k in res["runs"]})
    rows = []
    for n in names:
        p = [res["runs"].get(f"{n}|135M|{k}") for k in range(SEEDS["135M"])]
        t = [res["runs"].get(f"{n}|360M|{k}") for k in range(SEEDS["360M"])]
        p, t = [x for x in p if x], [x for x in t if x]
        if p and t:
            rows.append({"name": n, "p_acc": sum(x["acc_gain"] for x in p) / len(p),
                         "p_cand": sum(x["cand_gain"] for x in p) / len(p),
                         "p_acc_seeds": [x["acc_gain"] for x in p],
                         "t_acc": sum(x["acc_gain"] for x in t) / len(t), "t_cand": sum(x["cand_gain"] for x in t) / len(t)})
    out = {"n_envs": len(rows), "proxy": "135M", "target": "360M", "recipe": RECIPE.__dict__}
    if len(rows) >= 4:
        ta = [r["t_acc"] for r in rows]

        def st(pred, tgt=ta):
            return {"spearman": round(fc.spearman(pred, tgt), 3), "decision_accuracy": round(fc.decision_accuracy(pred, tgt), 3)}
        out["accuracy_to_accuracy"] = st([r["p_acc"] for r in rows])
        out["smooth_to_accuracy"] = st([r["p_cand"] for r in rows])
        out["smooth_to_smooth"] = st([r["p_cand"] for r in rows], [r["t_cand"] for r in rows])
        two = [r for r in rows if len(r["p_acc_seeds"]) > 1]
        if len(two) >= 4:
            out["proxy_seed0_vs_seed1"] = st([r["p_acc_seeds"][0] for r in two], [r["p_acc_seeds"][1] for r in two])
            out["accuracy_to_accuracy_seed0_only"] = st([r["p_acc_seeds"][0] for r in rows])
        out["table"] = [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items() if k != "p_acc_seeds"}
                        for r in rows]
    (ROOT / "out" / "validation_rl_real_summary.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--one", nargs=3, metavar=("ENV", "SIZE", "SEED"), help="(internal) one run in this process")
    a = ap.parse_args()
    if a.one:
        one(*a.one)
        sys.exit(0)
    res = json.loads(OUT.read_text()) if a.report else run()
    print(json.dumps({k: v for k, v in summarize(res).items() if k != "table"}, indent=1))
