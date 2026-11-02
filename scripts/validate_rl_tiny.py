"""Forecast validation for RL environments on the tiny character-level GPTs.

This is the experiment that produced Spearman -0.03 in the original prototype
(7 environments, 1 seed, accuracy only, a line through S/M/L extrapolated to
XL), redone with the fixes the research calls for:

  * 16 environments with genuinely different value (skill mix, pool size,
    grader noise, broken graders), not 7;
  * 3 seeds per environment and size, averaged;
  * a smooth score (probability on the right answer vs 4 distractors) next to accuracy;
  * three forecasters compared by leave-one-out: extrapolate (the old method),
    rank_largest (DataDecide's default), calibrated (learned small-to-large map).

Real-model GRPO at four sizes x 16 environments x 3 seeds does not fit on a
laptop, which is why this sweep uses the tiny models; the real-model RL check
is the six sample environments in scripts/run_evidence.py.

    python scripts/validate_rl_tiny.py            # ~1.5-3 h on CPU, resumable
    python scripts/validate_rl_tiny.py --report   # recompute the summary only
"""
from __future__ import annotations

import argparse
import json
import random
import string
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone import forecast as fc  # noqa: E402
from touchstone import heldout  # noqa: E402
from touchstone.env import Task  # noqa: E402
from touchstone.model import EOS, PAD, generate, prompt_batch, seq_logprobs  # noqa: E402
from touchstone.pretrain import pretrain  # noqa: E402
from touchstone.rl import ToyGRPO  # noqa: E402
from touchstone.suites import numeric_distractors, string_distractors  # noqa: E402
from touchstone.vocab import encode  # noqa: E402

OUT = ROOT / "out" / "validation_rl_tiny.json"
SIZES = ["S", "M", "L", "XL"]
SMALL = ("S", "M", "L")
SEEDS = 3
STEPS = 200


def make_task(kind, rng):
    if kind in ("add2", "add3"):
        while True:
            a = rng.randint(10, 99) if kind == "add2" else rng.randint(100, 999)
            b = rng.randint(10, 99)
            if (a * 7 + b * 13) % 5:  # bucket 0 is reserved for the held-out suite
                return Task(f"{a}+{b}=", {"answer": str(a + b)})
    while True:
        s = "".join(rng.choice(string.ascii_lowercase[:12]) for _ in range(rng.randint(3, 8)))
        if sum(map(ord, s)) % 5:
            return Task(f"rev {s}>", {"answer": s[::-1]}) if kind == "rev" else Task(f"cp {s}>", {"answer": s})


class SynthEnv:
    def __init__(self, name, mix, pool=4000, noise=0.0, grader="exact", seed=0):
        self.name, self.mix, self.pool, self.noise, self.grader, self.seed = name, mix, pool, noise, grader, seed
        rng = random.Random(seed)
        kinds = list(mix)
        self._tasks = [make_task(rng.choices(kinds, [mix[k] for k in kinds])[0], rng) for _ in range(pool)]
        self._rng = random.Random(seed + 1)

    def tasks(self):
        return self._tasks

    def verify(self, task, output):
        ans = task.meta["answer"]
        if self.grader == "shape":
            ok = len(output.strip()) == len(ans) and output.strip().isalnum()
        elif self.grader == "contains":
            ok = ans in output
        else:
            ok = output.strip() == ans
        if self.noise and self._rng.random() < self.noise:
            ok = not ok
        return float(ok)


ENVS = [
    SynthEnv("add2", {"add2": 1}), SynthEnv("add3", {"add3": 1}), SynthEnv("rev", {"rev": 1}),
    SynthEnv("copy", {"cp": 1}), SynthEnv("add2+add3", {"add2": 1, "add3": 1}),
    SynthEnv("add2+rev", {"add2": 1, "rev": 1}), SynthEnv("all", {"add2": 1, "add3": 1, "rev": 1, "cp": 1}),
    SynthEnv("add2 tiny pool", {"add2": 1}, pool=40), SynthEnv("rev tiny pool", {"rev": 1}, pool=40),
    SynthEnv("add2 noisy30", {"add2": 1}, noise=0.3), SynthEnv("add3 noisy50", {"add3": 1}, noise=0.5),
    SynthEnv("rev noisy30", {"rev": 1}, noise=0.3), SynthEnv("add2 shape grader", {"add2": 1}, grader="shape"),
    SynthEnv("mix contains grader", {"add2": 1, "rev": 1}, grader="contains"),
    SynthEnv("add3+rev", {"add3": 1, "rev": 1}), SynthEnv("copy+rev", {"cp": 1, "rev": 1}),
]


def suite_with_distractors():
    s = heldout.suite()
    items = [t for ts in s.values() for t in ts]
    rng = random.Random(5)
    dis = [numeric_distractors(t.meta["answer"], rng) if t.meta["answer"].isdigit()
           else string_distractors(t.meta["answer"], rng) for t in items]
    return items, dis


@torch.no_grad()
def score(model, items, dis):
    texts, _, _ = generate(model, [t.prompt for t in items])
    acc = heldout.score(texts, items)
    prompts, conts = [], []
    for t, ds in zip(items, dis):
        for c in [t.meta["answer"]] + ds:
            prompts.append(t.prompt)
            conts.append(c)
    idx, _ = prompt_batch(prompts)
    tail = [encode(c) + [EOS] for c in conts]
    L = max(map(len, tail))
    seqs = torch.cat([idx, torch.tensor([x + [PAD] * (L - len(x)) for x in tail])], 1)
    lp = []
    for s in range(0, len(seqs), 512):
        lp.append(seq_logprobs(model, seqs[s:s + 512], idx.shape[1]))
    lp = torch.cat(lp).view(len(items), -1)
    cand = torch.softmax(lp, 1)[:, 0].tolist()
    return acc, cand


def run(args):
    torch.set_num_threads(args.threads)
    res = json.loads(OUT.read_text()) if OUT.exists() else {"runs": {}, "base": {}}
    items, dis = suite_with_distractors()
    bases = {}
    t0 = time.time()
    for s in SIZES:
        bases[s] = pretrain(s)
        bases[s].eval()
        if s not in res["base"]:
            a, c = score(bases[s], items, dis)
            res["base"][s] = {"acc": a, "cand": c}
    for e in ENVS:
        for s in SIZES:
            for seed in range(SEEDS):
                key = f"{e.name}|{s}|{seed}"
                if key in res["runs"]:
                    continue
                model, curve = ToyGRPO(steps=STEPS, seed=seed).train(bases[s], e)
                a, c = score(model, items, dis)
                b = res["base"][s]
                res["runs"][key] = {"acc_gain": 100 * (sum(a) - sum(b["acc"])) / len(a),
                                    "cand_gain": 100 * (sum(c) - sum(b["cand"])) / len(c),
                                    "reward_first": sum(curve[:20]) / 20, "reward_last": sum(curve[-20:]) / 20}
                OUT.parent.mkdir(parents=True, exist_ok=True)
                OUT.write_text(json.dumps(res))
                print(f"{key}: acc {res['runs'][key]['acc_gain']:+.1f} cand {res['runs'][key]['cand_gain']:+.1f} "
                      f"({time.time() - t0:.0f}s)", flush=True)
    return res


def summarize(res) -> dict:
    from touchstone.model import TinyGPT
    params = {s: TinyGPT(s).n_params() for s in SIZES}
    rows = []
    for e in ENVS:
        g = {}
        for s in SIZES:
            runs = [res["runs"].get(f"{e.name}|{s}|{k}") for k in range(SEEDS)]
            runs = [r for r in runs if r]
            if len(runs) < SEEDS:  # only environments with every seed finished
                break
            g[s] = {"acc": sum(r["acc_gain"] for r in runs) / len(runs), "cand": sum(r["cand_gain"] for r in runs) / len(runs),
                    "acc_seeds": [round(r["acc_gain"], 2) for r in runs]}
        if len(g) == len(SIZES):
            rows.append({"name": e.name, "small": {s: g[s] for s in SMALL}, "target": g["XL"]["acc"], "all": g})
    p = {**params, "target": params["XL"]}
    v = fc.validate(rows, p, small=SMALL)
    # the old protocol: seed 0 only
    rows0 = [{"name": r["name"], "small": {s: {"acc": r["all"][s]["acc_seeds"][0], "cand": 0} for s in SMALL},
              "target": r["all"]["XL"]["acc_seeds"][0]} for r in rows]
    v0 = fc.validate(rows0, p, small=SMALL)
    # the same forecasters with the smooth score as the target (features swapped so "acc" means the smooth score)
    rows_c = [{"name": r["name"], "small": {s: {"acc": r["all"][s]["cand"], "cand": r["all"][s]["acc"]} for s in SMALL},
               "target": r["all"]["XL"]["cand"]} for r in rows]
    vc = fc.validate(rows_c, p, small=SMALL)
    # seed-to-seed reproducibility of the XL truth itself (the noise ceiling)
    xs = [r["all"]["XL"]["acc_seeds"] for r in rows]
    ceil = fc.spearman([x[0] for x in xs], [sum(x[1:]) / len(x[1:]) for x in xs]) if xs and len(xs[0]) > 1 else None
    return {"n_envs": len(rows), "seeds": SEEDS, "steps": STEPS, "params": params, "validation_3seeds": v,
            "validation_smooth_target": vc,
            "validation_seed0_only": v0, "xl_seed0_vs_other_seeds_spearman": ceil,
            "rows": [{"name": r["name"], **{s: round(r["all"][s]["acc"], 2) for s in SIZES},
                      **{f"{s}_cand": round(r["all"][s]["cand"], 2) for s in SIZES}} for r in rows]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()
    res = json.loads(OUT.read_text()) if a.report else run(a)
    summ = summarize(res)
    (ROOT / "out" / "validation_rl_tiny_summary.json").write_text(json.dumps(summ, indent=2))
    for m, x in summ["validation_3seeds"]["methods"].items():
        print(f"{m:13s} spearman {x['spearman']:+.2f}  decision acc {x['decision_accuracy']:.2f}  MAE {x['mae_pts']:.2f}")
    for m, x in summ["validation_smooth_target"]["methods"].items():
        print(f"smooth target {m:13s} spearman {x['spearman']:+.2f}  decision acc {x['decision_accuracy']:.2f}")
    print("seed-0-only (old protocol):", {m: x["spearman"] for m, x in summ["validation_seed0_only"]["methods"].items()})
    print("XL noise ceiling (seed 0 vs seeds 1-2 spearman):", summ["xl_seed0_vs_other_seeds_spearman"])
