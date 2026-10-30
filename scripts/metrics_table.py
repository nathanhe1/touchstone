"""Compile the before/after metrics table from the result files in out/.

    python scripts/metrics_table.py      # prints markdown and writes out/metrics.md
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"


def load(name):
    f = OUT / name
    return json.loads(f.read_text()) if f.exists() else None


def flags_row(fe, key, label):
    if not fe or key not in fe:
        return None
    a = fe[key]["after"]["all"]
    nz = fe[key]["after"]
    return (f"| {label} | {a['precision']} / {a['recall']} | noisy {nz['noisy_labels']['recall']}, public "
            f"{nz['copied_from_public']['recall']} | {fe[key]['exact_match_after']:.0%} |")


def main():
    lines = ["## Red flags (precision / recall over all flags)", "",
             "| Set (engine) | All flags P / R | Weakest recalls | Exactly right |", "|---|---|---|---|"]
    fe = load("flag_eval.json")
    for key, label in [("dev_round1", "dev, round 1"), ("dev", "dev, round 2"), ("test_round1", "test v1 (23), round 1"),
                       ("test", "test v1 (23), round 2"), ("test2_round1", "test v2 (63), round 1"),
                       ("test2", "test v2 (63), round 2")]:
        r = flags_row(fe, key, label)
        if r:
            lines.append(r)
    lines += ["", "## Forecast, primary metric: accuracy at the small size -> accuracy at the larger size", "",
              "| Experiment | Spearman | Decision accuracy | n |", "|---|---|---|---|"]
    t = load("validation_rl_tiny_summary.json")
    if t:
        m = t["validation_3seeds"]["methods"]["rank_largest"]
        lines.append(f"| RL, tiny GPTs, L -> XL (3 seeds) | {m['spearman']} | {m['decision_accuracy']} | {t['n_envs']} |")
    r = load("validation_rl_real_summary.json")
    if r and "accuracy_to_accuracy" in r:
        a = r["accuracy_to_accuracy"]
        lines.append(f"| RL, real models, 135M -> 360M | {a['spearman']} | {a['decision_accuracy']} | {r['n_envs']} |")
    for suffix, label in [("", "standard 135M"), ("_135Mq", "quick recipe"), ("_135Mlr", "lr / 10")]:
        s = load(f"validation_sft_summary{suffix}.json")
        if s and "rank_largest" in s:
            a = s["rank_largest"]["accuracy_to_accuracy"]
            lines.append(f"| Datasets, real models, 135M ({label}) -> 360M | {a['spearman']} | {a['decision_accuracy']} | "
                         f"{s['n_datasets']} |")
    text = "\n".join(lines) + "\n"
    (OUT / "metrics.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
