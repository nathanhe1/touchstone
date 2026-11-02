"""Forecast validation for datasets on real open models, and the calibration file.

Every example dataset is fine-tuned (LoRA, the fixed recipe) at 135M and 360M
(several seeds) and at 1.7B, the largest size this laptop can train. Each
forecasting method predicts the 1.7B gain from the small rungs only, and is
scored by leave-one-out against the measured 1.7B gain: Spearman, pairwise
decision accuracy (chance 0.5), mean absolute error, interval width.

The fitted map is written to touchstone/calibration/dataset_word_math.json and
used by `touchstone appraise` to forecast new datasets on this suite.

    python scripts/validate_sft.py                 # resumable; ~3-4 h on an M-series laptop
    python scripts/validate_sft.py --report        # recompute summary + calibration only
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone import data as datamod  # noqa: E402
from touchstone import forecast as fc  # noqa: E402
from touchstone import lm as L  # noqa: E402
from touchstone import measure, pipeline, suites  # noqa: E402

DATASETS = ["good_cot", "good_short", "noisy_20", "noisy_50", "noisy_80", "wrong_all", "offtopic", "hard_cot",
            "small_good", "half_offtopic", "short_noisy_30", "mostly_offtopic", "duplicated", "gsm8k_clone",
            # round 2: twelve more, for 26 in total
            "v2_noisy_10", "v2_noisy_35", "v2_noisy_65", "v2_short_300", "v2_cot_100", "v2_offtopic_25", "v2_offtopic_75",
            "v2_hard_short", "v2_hard_noisy_30", "v2_gsm8k_mix_50", "v2_dup_5x", "v2_cot_short_mix"]
SEEDS = {"135M": 2, "360M": 2, "1.7B": 1, "135Mq": 3, "135Mlr": 3}  # 135Mq: quick recipe (30 steps); 135Mlr: lr / 10
QUICK_STEPS = 30
SUITE_ITEMS = 200
OUT = ROOT / "out" / "validation_sft.json"



def one(name, size, seeds):
    """All requested seeds of one (dataset, size) in a fresh process: MPS caches a compiled graph per tensor
    shape, and a long-lived process slows to a crawl as the cache grows (round 2)."""
    suite = suites.word_math_suite().subset(SUITE_ITEMS)
    recipe = L.Recipe()
    lm = L.LM(size[:4])
    before = pipeline.base_eval(lm, suite, recipe.eval_max_new)
    ex = datamod.load_dataset(ROOT / "examples" / "datasets" / f"{name}.jsonl")
    rec = (L.Recipe(sft_steps=QUICK_STEPS) if size == "135Mq" else
           L.Recipe(sft_lr=recipe.sft_lr / 10) if size == "135Mlr" else recipe)
    for seed in seeds:
        tuned, info = L.sft(lm, datamod.to_training_pairs(lm, ex), rec, seed=seed)
        ev = measure.evaluate(tuned, suite, recipe.eval_max_new)
        lm = L.drop_lora(tuned)
        del tuned
        L.free_memory()
        print("RESULT " + json.dumps({"key": f"{name}|{size}|{seed}", "base": measure.summary(before),
                                      "acc_gain": measure.paired_gain(before["acc"], ev["acc"])["gain"],
                                      "cand_gain": measure.paired_gain(before["cand"], ev["cand"])["gain"],
                                      "train_s": info["seconds"], "loss_last": info["loss_last"]}), flush=True)


def run(sizes):
    import subprocess
    res = json.loads(OUT.read_text()) if OUT.exists() else {"runs": {}, "base": {}}
    t0 = time.time()
    # dataset-major order: each dataset is finished at every size before the next starts, so complete
    # validation rows accumulate even if the sweep is stopped early
    for name in DATASETS:
        for size in sizes:
            todo = [s for s in range(SEEDS[size]) if f"{name}|{size}|{s}" not in res["runs"]]
            if not todo:
                continue
            p = subprocess.Popen([sys.executable, __file__, "--one", name, size, ",".join(map(str, todo))],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=ROOT)
            for line in p.stdout:
                if not line.startswith("RESULT "):
                    continue
                r = json.loads(line[7:])
                key = r.pop("key")
                res["base"][size[:4]] = r.pop("base")
                res["runs"][key] = r
                OUT.write_text(json.dumps(res, indent=1))
                print(f"{key}: acc {r['acc_gain']:+.1f} cand {r['cand_gain']:+.1f} ({time.time() - t0:.0f}s)", flush=True)
            if p.wait() != 0:
                print(f"{name}|{size}: FAILED\n{p.stderr.read()[-800:]}", flush=True)
    return res




def _gain(res, name, size):
    runs = [res["runs"].get(f"{name}|{size}|{k}") for k in range(SEEDS.get(size, 1))]
    runs = [r for r in runs if r]
    if not runs:
        return None
    return {"acc": sum(r["acc_gain"] for r in runs) / len(runs), "cand": sum(r["cand_gain"] for r in runs) / len(runs),
            "acc_seeds": [r["acc_gain"] for r in runs], "cand_seeds": [r["cand_gain"] for r in runs]}


def _rank_stats(pred, actual):
    return {"spearman": round(fc.spearman(pred, actual), 3), "decision_accuracy": round(fc.decision_accuracy(pred, actual), 3)}


def summarize(res, target: str = "360M", proxy: str = "135M"):
    """Small-to-large validation on every dataset that has both the proxy and the target measured."""
    rows = []
    for name in DATASETS:
        p, t = _gain(res, name, proxy), _gain(res, name, target)
        if p and t:
            rows.append({"name": name, "proxy": p, "target": t, "q": _gain(res, name, "135Mq"),
                         "lr": _gain(res, name, "135Mlr")})
    out = {"suite": "word_math", "suite_items": SUITE_ITEMS, "proxy": proxy, "target": target, "n_datasets": len(rows),
           "size_ratio": round(L.PARAMS[target] / L.PARAMS[proxy[:4]], 1), "base": res["base"]}
    if len(rows) < 4:
        out["note"] = "fewer than 4 datasets measured at both sizes"
        (ROOT / "out" / f"validation_sft_summary{'' if proxy == '135M' else '_' + proxy}.json").write_text(json.dumps(out, indent=2))
        return out
    t_acc = [r["target"]["acc"] for r in rows]
    t_cand = [r["target"]["cand"] for r in rows]
    out["rank_largest"] = {  # DataDecide's default forecast: the proxy's ranking is the prediction
        "accuracy_to_accuracy": _rank_stats([r["proxy"]["acc"] for r in rows], t_acc),
        "smooth_to_smooth": _rank_stats([r["proxy"]["cand"] for r in rows], t_cand),
        "smooth_to_accuracy": _rank_stats([r["proxy"]["cand"] for r in rows], t_acc),
        "accuracy_seed0_only": _rank_stats([r["proxy"]["acc_seeds"][0] for r in rows], t_acc),
    }
    params = {**L.PARAMS, proxy: L.PARAMS[proxy[:4]], "target": L.PARAMS[target]}
    cal_rows = [{"name": r["name"], "small": {proxy: {"acc": r["proxy"]["acc"], "cand": r["proxy"]["cand"]}},
                 "target": r["target"]["acc"]} for r in rows]
    out["calibrated_loo"] = {k: v for k, v in fc.validate(cal_rows, params, small=(proxy,))["methods"]["calibrated"].items()
                             if k != "predictions"}
    q = [r for r in rows if r["q"]]
    if len(q) >= 4:
        out["quick_recipe_30_steps"] = {"n": len(q),
                                        "accuracy": _rank_stats([r["q"]["acc"] for r in q], [r["target"]["acc"] for r in q]),
                                        "smooth": _rank_stats([r["q"]["cand"] for r in q], [r["target"]["cand"] for r in q])}
    lr = [r for r in rows if r["lr"]]
    if len(lr) >= 4:  # Wang et al. (ICLR 2026): a 10x smaller learning rate for the proxy
        out["small_lr_proxy"] = {
            "n": len(lr),
            "standard_lr": {"accuracy": _rank_stats([r["proxy"]["acc_seeds"][0] for r in lr], [r["target"]["acc"] for r in lr]),
                            "smooth": _rank_stats([r["proxy"]["cand_seeds"][0] for r in lr], [r["target"]["cand"] for r in lr])},
            "lr_div_10": {"accuracy": _rank_stats([r["lr"]["acc"] for r in lr], [r["target"]["acc"] for r in lr]),
                          "smooth": _rank_stats([r["lr"]["cand"] for r in lr], [r["target"]["cand"] for r in lr])}}
    two = [r for r in rows if len(r["proxy"]["acc_seeds"]) > 1]
    if len(two) >= 4:  # how reproducible is the proxy itself?
        out["proxy_seed0_vs_seed1"] = {"accuracy": _rank_stats([r["proxy"]["acc_seeds"][0] for r in two],
                                                               [r["proxy"]["acc_seeds"][1] for r in two]),
                                       "smooth": _rank_stats([r["proxy"]["cand_seeds"][0] for r in two],
                                                             [r["proxy"]["cand_seeds"][1] for r in two])}
    out["table"] = [{"name": r["name"], f"{proxy}_acc": round(r["proxy"]["acc"], 2), f"{proxy}_prob": round(r["proxy"]["cand"], 2),
                     f"{target}_acc": round(r["target"]["acc"], 2), f"{target}_prob": round(r["target"]["cand"], 2)}
                    for r in rows]
    (ROOT / "out" / f"validation_sft_summary{'' if proxy == '135M' else '_' + proxy}.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--one", nargs=3, metavar=("DATASET", "SIZE", "SEEDS"), help="(internal) runs in this process")
    ap.add_argument("--sizes", default="135Mq,135M,360M,1.7B,135Mlr")
    ap.add_argument("--target", default="360M", help="size to validate against (1.7B needs more memory than 16 GB)")
    ap.add_argument("--proxy", default="135M", help="proxy arm: 135M (standard), 135Mq (quick recipe), 135Mlr (lr / 10)")
    a = ap.parse_args()
    if a.one:
        one(a.one[0], a.one[1], [int(s) for s in a.one[2].split(",")])
        sys.exit(0)
    res = json.loads(OUT.read_text()) if a.report else run(a.sizes.split(","))
    s = summarize(res, a.target, a.proxy)
    print(json.dumps({k: v for k, v in s.items() if k not in ("table", "base")}, indent=1))
