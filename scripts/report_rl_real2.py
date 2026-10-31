"""Score the round-3 RL forecast sweep, by the rules pre-registered in METHOD.md.

Default: DEVELOPMENT environments only, to choose a signal. `--final SIGNAL` scores the held-out
environments for that signal (and lists every other candidate next to it). Run --final once.

    python scripts/report_rl_real2.py
    python scripts/report_rl_real2.py --final acc_late
"""
import argparse
import json
import os
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import forecast as fc  # noqa: E402

OUT = ROOT / "out"
P, T = os.environ.get("FORECAST_PROXY", "135M"), os.environ.get("FORECAST_TARGET", "360M")
BOOT = 1000


def bits(s):
    return [int(c) for c in s]


SOURCE = OUT / "validation_rl_real2.json"


def load():
    return json.loads(SOURCE.read_text())


def seeds(res, name, size):
    return [res["runs"][k] for k in sorted(res["runs"]) if k.startswith(f"{name}|{size}|")]


def mean_item(runs, step, key):
    v = [bits(r["ckpts"][step]["acc"]) if key == "acc" else r["ckpts"][step]["cand"] for r in runs]
    return [sum(x) / len(x) for x in zip(*v)]


def gain(vec, base):
    return 100 * (sum(vec) / len(vec) - sum(base) / len(base))


def z(v):
    m, s = st.mean(v), st.pstdev(v) or 1.0
    return [(x - m) / s for x in v]


def signals(res, names):
    """name -> proxy score per environment."""
    b = res["base"][P]
    ba, bc = bits(b["acc"]), b["cand"]
    S = {}

    def add(k, f):
        S[k] = [f(seeds(res, n, P), n) for n in names]
    add("acc_final", lambda r, n: gain(mean_item(r, "30", "acc"), ba))
    add("acc_late", lambda r, n: st.mean(gain(mean_item(r, s, "acc"), ba) for s in ("20", "30")))
    add("acc_all_ckpts", lambda r, n: st.mean(gain(mean_item(r, s, "acc"), ba) for s in ("10", "20", "30")))
    add("smooth_final", lambda r, n: gain(mean_item(r, "30", "cand"), bc))
    add("smooth_late", lambda r, n: st.mean(gain(mean_item(r, s, "cand"), bc) for s in ("20", "30")))
    add("reward_gain", lambda r, n: st.mean(x["reward_last"] - x["reward_first"] for x in r))
    S["ens_acc_smooth"] = [a + c for a, c in zip(z(S["acc_late"]), z(S["smooth_late"]))]
    f = OUT / "dev_grad_sim.json"
    if f.exists():
        g = json.loads(f.read_text())
        if all(n in g for n in names):
            S["grad_sim"] = [g[n] for n in names]
            S["ens_acc_smooth_grad"] = [a + c + d for a, c, d in zip(z(S["acc_late"]), z(S["smooth_late"]), z(S["grad_sim"]))]
    return S


def resolvable(res, names):
    """Pairs whose target gap exceeds 2 SE (METHOD.md, Round 3)."""
    base = bits(res["base"][T]["acc"])
    item, gains = {}, {}
    for n in names:
        r = seeds(res, n, T)
        item[n] = mean_item(r, "30", "acc")
        gains[n] = [gain(bits(x["ckpts"]["30"]["acc"]), base) for x in r]
    n_items = len(base)
    rng = random.Random(0)
    idx = [[rng.randrange(n_items) for _ in range(n_items)] for _ in range(BOOT)]
    keep = []
    for i, a in enumerate(names):
        for j in range(i + 1, len(names)):
            b = names[j]
            d = [item[a][k] - item[b][k] for k in range(n_items)]
            sims = [100 * sum(d[k] for k in ix) / n_items for ix in idx]
            var = st.pvariance(sims)
            for n in (a, b):
                if len(gains[n]) > 1:
                    var += st.variance(gains[n]) / len(gains[n])
            gap = st.mean(gains[a]) - st.mean(gains[b])
            if abs(gap) > 2 * var ** 0.5:
                keep.append((i, j))
    return keep, [st.mean(gains[n]) for n in names], gains


def score(pred, tgt, pairs):
    ok = sum((pred[i] - pred[j]) * (tgt[i] - tgt[j]) > 0 for i, j in pairs)
    return {"spearman": round(fc.spearman(pred, tgt), 3), "decision_all_pairs": round(fc.decision_accuracy(pred, tgt), 3),
            "decision_resolvable": round(ok / len(pairs), 3) if pairs else None, "n_resolvable": len(pairs)}


def ceiling(gains, names):
    """One target seed vs the mean of the others, all pairs (METHOD.md)."""
    n = min(len(gains[x]) for x in names)
    if n < 2:
        return None
    v = []
    for s in range(n):
        a = [gains[x][s] for x in names]
        b = [st.mean(y for k, y in enumerate(gains[x]) if k != s) for x in names]
        v.append(fc.decision_accuracy(a, b))
    return round(st.mean(v), 3) if n > 1 else None


def table(res, names):
    names = [n for n in names if seeds(res, n, P) and seeds(res, n, T)]
    pairs, tgt, gains = resolvable(res, names)
    S = signals(res, names)
    return {"n_envs": len(names), "n_pairs": len(names) * (len(names) - 1) // 2, "ceiling": ceiling(gains, names),
            "target": {n: round(t, 2) for n, t in zip(names, tgt)},
            "signals": {k: score(v, tgt, pairs) for k, v in S.items()}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="results file, for example out/gpu/validation_rl_real2.json")
    ap.add_argument("--final", help="signal chosen on development environments; scores held-out once")
    a = ap.parse_args()
    if a.file:
        SOURCE = Path(a.file)
        OUT = SOURCE.parent
    res = load()
    out = {"dev": table(res, res["split"]["dev"]), "seeds_done": {s: sum(f"|{s}|" in k for k in res["runs"]) for s in (P, T)}}
    if a.final:
        h = table(res, res["split"]["heldout"])
        out["final"] = {"chosen": a.final, "chosen_score": h["signals"][a.final], **h}
    (OUT / "validation_rl_real2_summary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
