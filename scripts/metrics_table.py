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
    for key, label in [("dev_round1", "dev, round 1"), ("dev", "dev, round 2"), ("dev_round3", "dev, round 3"),
                       ("test_round1", "test v1 (23), round 1"), ("test", "test v1 (23), round 2"),
                       ("test_round3", "test v1 (23), round 3 (now dev data)"),
                       ("test2_round1", "test v2 (63), round 1"), ("test2_round2", "test v2 (63), round 2 (now dev data)"),
                       ("test2", "test v2 (63), round 2"), ("test2_round3", "test v2 (63), round 3 (now dev data)"),
                       ("test3_round2", "**test v3 (87), frozen, round 2 engine**"),
                       ("test3", "**test v3 (87), frozen, round 3 engine**")]:
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
    r3 = load("validation_rl_real2_summary.json")
    if r3:
        lines += ["", "## Forecast, round 3: 135M -> 360M, accuracy to accuracy, 600 items (METHOD.md, pre-registered)", "",
                  "| Set | Signal | Spearman | Decision, all pairs | Decision, resolvable pairs | Resolvable / all | Ceiling |",
                  "|---|---|---|---|---|---|---|"]

        def row(name, block, sig):
            x = block["signals"][sig]
            lines.append(f"| {name} | {sig} | {x['spearman']} | {x['decision_all_pairs']} | "
                         f"{x['decision_resolvable']} | {x['n_resolvable']} / {block['n_pairs']} | {block['ceiling']} |")
        for sig in r3["dev"]["signals"]:
            row("dev", r3["dev"], sig)
        if "final" in r3:
            row("**held-out**", r3["final"], r3["final"]["chosen"])
            for sig in r3["final"]["signals"]:
                if sig != r3["final"]["chosen"]:
                    row("held-out, not chosen", r3["final"], sig)
    c = load("coverage_eval_eval.json")
    if c:
        rows = list(c.values())
        tp = sum(x["noisy"] and x["truth"] for x in rows)
        fp = sum(x["noisy"] and not x["truth"] for x in rows)
        fn = sum(not x["noisy"] and x["truth"] for x in rows)
        lines += ["", "## All-data-types eval (new, small, not part of test v3)", "",
                  "| Set | Precision | Recall | n |", "|---|---|---|---|",
                  f"| eval half, rules as frozen before the run | {round(tp / (tp + fp), 3)} | {round(tp / (tp + fn), 3)} | {len(rows)} |"]
    text = "\n".join(lines) + "\n"
    (OUT / "metrics.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
