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
            "small_good", "half_offtopic", "short_noisy_30", "mostly_offtopic", "duplicated", "gsm8k_clone"]
SEEDS = {"135M": 2, "360M": 1, "1.7B": 1, "135Mq": 1}  # 135Mq: the quick-mode recipe (30 steps) at 135M
QUICK_STEPS = 30
SUITE_ITEMS = 200
OUT = ROOT / "out" / "validation_sft.json"
CALIB = ROOT / "touchstone" / "calibration" / "dataset_word_math.json"


def run(sizes):
    res = json.loads(OUT.read_text()) if OUT.exists() else {"runs": {}, "base": {}}
    suite = suites.word_math_suite().subset(SUITE_ITEMS)
    recipe = L.Recipe()
    t0 = time.time()
    # dataset-major order: each dataset is finished at every size before the next starts, so complete
    # (small -> 1.7B) validation rows accumulate even if the sweep is stopped early
    lm, loaded, before = None, None, None
    for name in DATASETS:
        for size in sizes:
            for seed in range(SEEDS[size]):
                key = f"{name}|{size}|{seed}"
                if key in res["runs"]:
                    continue
                if loaded != size[:4]:
                    del lm
                    L.free_memory()
                    lm, loaded = L.LM(size[:4]), size[:4]
                    before = pipeline.base_eval(lm, suite, recipe.eval_max_new)
                    res["base"][size[:4]] = measure.summary(before)
                ex = datamod.load_dataset(ROOT / "examples" / "datasets" / f"{name}.jsonl")
                rec = L.Recipe(sft_steps=QUICK_STEPS) if size == "135Mq" else recipe
                tuned, info = L.sft(lm, datamod.to_training_pairs(lm, ex), rec, seed=seed)
                ev = measure.evaluate(tuned, suite, recipe.eval_max_new)
                lm = L.drop_lora(tuned)
                res["runs"][key] = {"acc_gain": measure.paired_gain(before["acc"], ev["acc"])["gain"],
                                    "cand_gain": measure.paired_gain(before["cand"], ev["cand"])["gain"],
                                    "train_s": info["seconds"], "loss_last": info["loss_last"]}
                OUT.parent.mkdir(parents=True, exist_ok=True)
                OUT.write_text(json.dumps(res, indent=1))
                r = res["runs"][key]
                print(f"{key}: acc {r['acc_gain']:+.1f} cand {r['cand_gain']:+.1f} ({time.time() - t0:.0f}s)", flush=True)
    return res


def rows_from(res):
    rows = []
    for name in DATASETS:
        g = {}
        for size in L.LADDER:
            runs = [res["runs"].get(f"{name}|{size}|{k}") for k in range(SEEDS[size])]
            runs = [r for r in runs if r]
            if runs:
                g[size] = {"acc": sum(r["acc_gain"] for r in runs) / len(runs),
                           "cand": sum(r["cand_gain"] for r in runs) / len(runs),
                           "acc_seeds": [r["acc_gain"] for r in runs]}
        if len(g) == 3:
            rows.append({"name": name, "small": {s: g[s] for s in L.SMALL}, "target": g[L.TARGET]["acc"], "all": g})
    return rows


def summarize(res):
    rows = rows_from(res)
    params = {**L.PARAMS, "target": L.PARAMS[L.TARGET]}
    # full mode: 2 seeds at 135M and 360M, features from 360M
    cal360 = fc.make_calibration(rows, params, small=("135M", "360M"))
    # quick mode: 1 seed at 135M only, so calibrate on seed 0 alone (same noise as a quick run)
    rows135 = [{"name": r["name"], "small": {"135M": {"acc": res["runs"][f"{r['name']}|135M|0"]["acc_gain"],
                                                     "cand": res["runs"][f"{r['name']}|135M|0"]["cand_gain"]}},
                "target": r["target"]} for r in rows]
    cal135 = fc.make_calibration(rows135, params, small=("135M",))
    # the quick-mode recipe (135M, 30 steps, 1 seed) -> 1.7B (60 steps)
    rows_q = [{"name": r["name"], "small": {"135M": {"acc": res["runs"][f"{r['name']}|135Mq|0"]["acc_gain"],
                                                    "cand": res["runs"][f"{r['name']}|135Mq|0"]["cand_gain"]}},
               "target": r["target"]} for r in rows if f"{r['name']}|135Mq|0" in res["runs"]]
    cal_q = fc.make_calibration(rows_q, params, small=("135M",)) if len(rows_q) >= 6 else None
    # the same forecasters with the smooth score as the target ("acc" slot holds the smooth score)
    rows_c = [{"name": r["name"], "small": {s: {"acc": r["all"][s]["cand"], "cand": r["all"][s]["acc"]} for s in L.SMALL},
               "target": r["all"][L.TARGET]["cand"]} for r in rows]
    smooth = fc.validate(rows_c, params, small=("135M", "360M"))
    noise = None
    if rows and all(len(r["all"]["135M"]["acc_seeds"]) > 1 for r in rows):
        noise = fc.spearman([r["all"]["135M"]["acc_seeds"][0] for r in rows], [r["all"]["135M"]["acc_seeds"][1] for r in rows])
    summary = {"suite": "word_math", "suite_items": SUITE_ITEMS, "seeds": SEEDS, "n_datasets": len(rows),
               "base": res["base"], "validation_from_360M": cal360["validation"],
               "validation_from_135M_one_seed": cal135["validation"], "validation_smooth_target_from_360M": smooth,
               "validation_quick_recipe": cal_q["validation"] if cal_q else None,
               "seed_to_seed_spearman_135M": noise,
               "table": [{"name": r["name"], **{s: round(r["all"][s]["acc"], 2) for s in L.LADDER},
                          **{f"{s}_prob": round(r["all"][s]["cand"], 2) for s in L.LADDER}} for r in rows]}
    CALIB.parent.mkdir(parents=True, exist_ok=True)
    keep = ("coef", "n", "coverage", "interval_halfwidth_pts", "validation")
    CALIB.write_text(json.dumps({"suite": "word_math", "target": L.TARGET, "recipe": L.Recipe().__dict__,
                                 "features": ["intercept", "acc_gain", "prob_gain"],
                                 "maps": {"135M": {k: cal135[k] for k in keep}, "360M": {k: cal360[k] for k in keep},
                                          **({"135M_quick": {k: cal_q[k] for k in keep}} if cal_q else {})}},
                                indent=2))
    (ROOT / "out" / "validation_sft_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--sizes", default="135Mq,135M,360M,1.7B")
    a = ap.parse_args()
    res = json.loads(OUT.read_text()) if a.report else run(a.sizes.split(","))
    s = summarize(res)
    for key in ("validation_from_360M", "validation_from_135M_one_seed", "validation_smooth_target_from_360M"):
        print(key)
        for m, x in s[key]["methods"].items():
            print(f"  {m:13s} spearman {x['spearman']:+.2f}  decision acc {x['decision_accuracy']:.2f}  "
                  f"MAE {x['mae_pts']:.2f}  80% half-width {x['interval_halfwidth_pts']}")
