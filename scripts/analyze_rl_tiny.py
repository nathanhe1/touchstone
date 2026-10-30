"""Which small-size signal predicts ACCURACY gain at the largest size? (tiny-GPT RL sweep)

Uses out/validation_rl_tiny.json (no new training). Every predictor is scored against the
XL accuracy gain (mean over seeds): Spearman and pairwise decision accuracy. Also reports
the XL seed-to-seed ceiling, i.e. how well one XL seed predicts the mean of the others.

    python scripts/analyze_rl_tiny.py
"""
import json
import statistics
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import forecast as fc  # noqa: E402

SIZES = ["S", "M", "L", "XL"]


def load():
    res = json.loads((ROOT / "out" / "validation_rl_tiny.json").read_text())["runs"]
    envs = {}
    for key, r in res.items():
        name, size, seed = key.split("|")
        envs.setdefault(name, {}).setdefault(size, {})[int(seed)] = r
    return {n: d for n, d in envs.items() if all(s in d for s in SIZES)}


def mean(v):
    return sum(v) / len(v)


def main():
    envs = load()
    names = sorted(envs)
    seeds = sorted(set.intersection(*[set(envs[n]["XL"]) for n in names]))
    acc = {s: [mean([envs[n][s][k]["acc_gain"] for k in envs[n][s]]) for n in names] for s in SIZES}
    cand = {s: [mean([envs[n][s][k]["cand_gain"] for k in envs[n][s]]) for n in names] for s in SIZES}
    target = acc["XL"]
    out = {"n_envs": len(names), "seeds": len(seeds), "predictors": {}}

    def add(label, pred):
        out["predictors"][label] = {"spearman": round(fc.spearman(pred, target), 3),
                                    "decision_accuracy": round(fc.decision_accuracy(pred, target), 3)}

    for s in ["S", "M", "L"]:
        add(f"accuracy@{s}", acc[s])
        add(f"smooth@{s}", cand[s])
    add("mean accuracy S,M,L", [mean(x) for x in zip(acc["S"], acc["M"], acc["L"])])
    add("mean smooth S,M,L", [mean(x) for x in zip(cand["S"], cand["M"], cand["L"])])
    add("accuracy@L + smooth@L (z-scored)", [a + b for a, b in zip(_z(acc["L"]), _z(cand["L"]))])
    add("smooth@XL (same size, other metric)", cand["XL"])
    # ceiling: one XL seed against the mean of the other XL seeds
    ceil = []
    for k in seeds:
        one = [envs[n]["XL"][k]["acc_gain"] for n in names]
        rest = [mean([envs[n]["XL"][j]["acc_gain"] for j in seeds if j != k]) for n in names]
        ceil.append(fc.decision_accuracy(one, rest))
    out["xl_one_seed_vs_rest_decision_accuracy"] = round(mean(ceil), 3)
    out["xl_accuracy_gain_spread"] = {"mean": round(mean(target), 2), "sd": round(statistics.pstdev(target), 2)}
    (ROOT / "out" / "analysis_rl_tiny.json").write_text(json.dumps(out, indent=2))
    for k, v in out["predictors"].items():
        print(f"{k:40s} spearman {v['spearman']:+.2f}  decision {v['decision_accuracy']:.2f}")
    print("XL one-seed vs rest decision accuracy (ceiling):", out["xl_one_seed_vs_rest_decision_accuracy"])
    print("XL accuracy gain mean/sd:", out["xl_accuracy_gain_spread"])


def _z(v):
    m, s = mean(v), statistics.pstdev(v) or 1.0
    return [(x - m) / s for x in v]


if __name__ == "__main__":
    main()
