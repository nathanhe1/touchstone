"""The appraisal pipeline: seal, probe, train on the scale ladder, forecast, grade."""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import torch

from . import env as envmod
from . import heldout, probes, redundancy
from .forecast import forecast, spearman
from .model import TinyGPT, generate
from .pretrain import pretrain
from .rl import ToyGRPO

LADDER = ["S", "M", "L"]
TRUTH = "XL"


def heldout_items(model, suite) -> list[float]:
    scores = []
    for tasks in suite.values():
        texts, _, _ = generate(model, [envmod.short(t) for t in tasks])
        scores += heldout.score(texts, tasks)
    return scores


def env_reward(model, env, n=300, seed=0) -> float:
    rng = random.Random(seed)
    sample = [rng.choice(env.tasks()) for _ in range(n)]
    texts, _, _ = generate(model, [envmod.short(t) for t in sample])
    return sum(env.verify(t, o) for t, o in zip(sample, texts)) / n


def grade(lift, hack, contam, redund, transfer_gap_flag) -> tuple[str, list[str]]:
    flags = []
    if hack >= 0.2:
        flags.append("Gameable grader: non-solutions collect reward")
    if transfer_gap_flag:
        flags.append("Reward climbs in training without matching held-out gains")
    if contam > 0.05:
        flags.append("Overlaps Touchstone's held-out suite")
    if redund >= 0.5:
        flags.append("Mostly duplicates free public tasks")
    if lift < 0.5:
        flags.append("No measurable gain over the free set")
    g = "A" if lift >= 5 else "B" if lift >= 2 else "C" if lift >= 0.5 else "D"
    order = "ABCDF"
    if hack >= 0.2 or transfer_gap_flag:
        g = max(g, "D", key=order.index)
    if redund >= 0.5:
        g = max(g, "C", key=order.index)
    if lift < 0 and (hack >= 0.2 or transfer_gap_flag):
        g = "F"
    return g, flags


def finalize(results, dollars_per_point):
    """Price and grade every environment against the free baseline (results[0])."""
    base_fc = results[0]["forecast"]["forecast"]
    for r in results:
        r["lift_over_free"] = r["forecast"]["forecast"] - base_fc
        uniq = r["redundancy"]["unique_tasks"]
        novel = 1 - r["redundancy"]["public_overlap"]
        priced = not r["is_public_baseline"] and r["hackability"]["score"] < 0.2
        # A gameable grader isn't priced until the vendor fixes it, and buyers
        # only pay for the share of tasks they can't already get for free.
        r["fair_value_per_task"] = max(0.0, r["lift_over_free"]) * dollars_per_point / uniq * novel if priced else 0
        r["grade"], r["flags"] = ("—", []) if r["is_public_baseline"] else grade(
            r["lift_over_free"], r["hackability"]["score"], r["contamination"],
            r["redundancy"]["public_overlap"], r["transfer_gap_flag"])


def run(env_dirs, public_dir, vault, out_path, dollars_per_point=250_000, trainer=None, log=print):
    torch.set_num_threads(4)
    trainer = trainer or ToyGRPO()
    suite = heldout.suite()
    heldout_all = [t for ts in suite.values() for t in ts]
    t0 = time.time()

    sizes = LADDER + [TRUTH]
    bases = {}
    for s in sizes:
        m = pretrain(s)
        m.eval()
        bases[s] = m
        log(f"base {s}: {m.n_params():,} params ({time.time() - t0:.0f}s)")
    params = {s: bases[s].n_params() for s in sizes}
    base_items = {s: heldout_items(bases[s], suite) for s in sizes}

    public_env = envmod.load(envmod.seal(public_dir, vault)["vault_path"])
    results = []
    for d in [public_dir] + list(env_dirs):
        manifest = envmod.seal(d, vault)
        env = envmod.load(manifest["vault_path"])
        r = {"id": Path(d).name, "name": env.name, "sha256": manifest["sha256"], "is_public_baseline": d == public_dir}
        r["hackability"] = probes.hackability(env, bases[LADDER[-1]])
        r["grader"] = probes.grader_reliability(env)
        r["redundancy"] = redundancy.redundancy(env, [] if d == public_dir else [public_env])
        r["contamination"] = redundancy.contamination(env, heldout_all)
        rungs = {}
        tuned_items = {}
        for s in sizes:
            model, curve = trainer.train(bases[s], env)
            tuned_items[s] = heldout_items(model, suite)
            n = len(base_items[s])
            rungs[s] = {
                "params": params[s],
                "env_reward_before": env_reward(bases[s], env),
                "env_reward_after": env_reward(model, env),
                "heldout_before": 100 * sum(base_items[s]) / n,
                "heldout_after": 100 * sum(tuned_items[s]) / n,
                "curve": [round(sum(curve[i:i + 20]) / len(curve[i:i + 20]), 4) for i in range(0, len(curve), 20)],
            }
            log(f"{r['id']} {s}: env {rungs[s]['env_reward_before']:.2f}->{rungs[s]['env_reward_after']:.2f} "
                f"heldout {rungs[s]['heldout_before']:.1f}->{rungs[s]['heldout_after']:.1f} ({time.time() - t0:.0f}s)")
        r["rungs"] = rungs
        r["forecast"] = forecast(
            [params[s] for s in LADDER], [base_items[s] for s in LADDER], [tuned_items[s] for s in LADDER],
            target_params=params[TRUTH],
        )
        r["actual_at_truth"] = rungs[TRUTH]["heldout_after"] - rungs[TRUTH]["heldout_before"]
        L = rungs[LADDER[-1]]
        env_gain = 100 * (L["env_reward_after"] - L["env_reward_before"])
        ho_gain = L["heldout_after"] - L["heldout_before"]
        r["transfer_gap_flag"] = env_gain >= 15 and ho_gain <= 0
        results.append(r)

    finalize(results, dollars_per_point)

    candidates = [r for r in results if not r["is_public_baseline"]]
    pred = [r["forecast"]["forecast"] for r in candidates]
    act = [r["actual_at_truth"] for r in candidates]
    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "ladder": {s: params[s] for s in sizes},
        "truth_rung": TRUTH,
        "dollars_per_point": dollars_per_point,
        "heldout_items": len(heldout_all),
        "validation": {
            "spearman_forecast_vs_actual": spearman(pred, act),
            "mean_abs_error_pts": sum(abs(p - a) for p, a in zip(pred, act)) / len(pred),
        },
        "environments": results,
        "runtime_s": round(time.time() - t0),
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out, indent=2))
    log(f"done in {out['runtime_s']}s; spearman={out['validation']['spearman_forecast_vs_actual']:.2f}")
    return out
