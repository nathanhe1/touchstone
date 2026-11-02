"""Score round 4 fine-tuning forecasts within family.

Primary number: decision accuracy on pairs of screen-passing materials (those no flag would stop), next to all pairs,
the noise ceiling and coverage. Planted disasters make all-pairs accuracy look better than a buyer's real choice.

    python scripts/h4_score.py dev   out/h4 ag_news,rotten,emotion
    python scripts/h4_score.py final out/h4 <families>
"""
import glob
import itertools
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FAIL = {"wrong60", "off80", "wrong100"}  # would be stopped by a flag


def load(d, sets):
    R = {}
    for s in sets:
        for f in glob.glob(f"{d}/h4_{s}.shard*.json"):
            R.update(json.loads(Path(f).read_text()))
    return R


def gain(R, arm, fam, c, size, seeds=None):
    v = [R[k]["gain"] for k in sorted(R) if k.startswith(f"{arm}|{fam}|{c}|{size}|") and (seeds is None or int(k.split("|")[4]) in seeds)]
    return float(np.mean(v)) if v else None


def agree(p, t, conds):
    a = b = 0
    for x, y in itertools.combinations(conds, 2):
        if None in (t[x], t[y], p[x], p[y]):  # a run lost to a failure: the pair is dropped and counted by `pairs`
            continue
        d = t[x] - t[y]
        if d == 0:
            continue
        b += 1
        a += (p[x] - p[y]) * d > 0
    return a, b


def score(sig, tgt, fams, conds):
    """Pairs within each family."""
    a = b = 0
    per = {}
    for f in fams:
        x, y = agree(sig[f], tgt[f], conds)
        a, b = a + x, b + y
        per[f] = round(x / y, 3) if y else None
    return a, b, per


def perm_p(sig, tgt, fams, conds, rng, n=10000):
    obs = score(sig, tgt, fams, conds)
    obs = obs[0] / obs[1]
    hits = 0
    for _ in range(n):
        t = {f: dict(zip(conds, rng.permutation([tgt[f][c] for c in conds]))) for f in fams}
        x = score(sig, t, fams, conds)
        hits += x[0] / x[1] >= obs
    return round((hits + 1) / (n + 1), 4)


def boot(sig, tgt, fams, conds, rng, n=2000):
    out = []
    for _ in range(n):
        a = b = 0
        for f in rng.choice(fams, len(fams)):
            pick = list(rng.choice(conds, len(conds)))
            for x, y in itertools.combinations(range(len(pick)), 2):
                cx, cy = pick[x], pick[y]
                d = tgt[f][cx] - tgt[f][cy]
                if cx == cy or d == 0:
                    continue
                b += 1
                a += (sig[f][cx] - sig[f][cy]) * d > 0
        if b:
            out.append(a / b)
    return [round(float(q), 3) for q in np.percentile(out, [5, 95])]


def ceiling(R, arm, size, fams, conds):
    seeds = sorted({int(k.split("|")[4]) for k in R if k.startswith(arm + "|") and f"|{size}|" in k})
    v = []
    for s in seeds:
        a = {f: {c: gain(R, arm, f, c, size, [s]) for c in conds} for f in fams}
        b = {f: {c: gain(R, arm, f, c, size, [q for q in seeds if q != s]) for c in conds} for f in fams}
        x = score(a, b, fams, conds)
        v.append(x[0] / x[1])
    return round(float(np.mean(v)), 3) if len(seeds) > 1 else None


def main():
    mode, d, fams = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
    sets = ["dev_small", "dev_large"] if mode == "dev" else ["final_small", "final_large"]
    R = load(d, sets)
    conds = sorted({k.split("|")[2] for k in R if k.startswith("sft|") and k.split("|")[1] in fams})
    conds = [c for c in conds if all(gain(R, "sft", f, c, "1.7B") is not None and gain(R, "sft", f, c, "360M") is not None for f in fams)]
    rng = np.random.default_rng(0)
    T = {f: {c: gain(R, "sft", f, c, "1.7B") for c in conds} for f in fams}
    T360 = {f: {c: gain(R, "sft", f, c, "360M") for c in conds} for f in fams}

    def sig(arm, size, net=False):
        o = {}
        for f in fams:
            p = gain(R, arm, f, "placebo", size) if net else 0.0
            p = max(0.0, p or 0.0)  # same rule as the product: only a helpful placebo is subtracted
            o[f] = {c: (gain(R, arm, f, c, size) - p) if gain(R, arm, f, c, size) is not None else None for c in conds}
        return o
    C = {"acc_final 360M -> 1.7B": (sig("sft", "360M"), T), "sftlr 360M -> 1.7B": (sig("sftlr", "360M"), T),
         "truncated 1.7B net of placebo -> 1.7B": (sig("sfttr", "1.7B", True), T), "acc_final 135M -> 1.7B": (sig("sft", "135M"), T),
         "acc_final 135M -> 360M": (sig("sft", "135M"), T360), "sftlr 135M -> 360M": (sig("sftlr", "135M"), T360)}
    passing = [c for c in conds if c not in FAIL]
    out = {"runs": len(R), "families": fams, "conditions": conds, "screen_passing": passing, "ceiling_1.7B": {"all": ceiling(R, "sft", "1.7B", fams, conds),
           "screen_passing": ceiling(R, "sft", "1.7B", fams, passing)}, "ceiling_360M": {"all": ceiling(R, "sft", "360M", fams, conds), "screen_passing": ceiling(R, "sft", "360M", fams, passing)},
           "target": {f: {c: round(T[f][c], 1) for c in conds} for f in fams}, "candidates": {}}
    print(json.dumps({k: out[k] for k in ("runs", "conditions", "ceiling_1.7B", "ceiling_360M")}))
    for name, (s, t) in C.items():
        if any(v is None for f in fams for v in s[f].values()):
            continue
        row = {}
        for label, cs in (("screen_passing", passing), ("all", conds)):
            a, b, per = score(s, t, fams, cs)
            row[label] = {"decision": round(a / b, 3), "pairs": b, "by_family": per, "ci90": boot(s, t, np.array(fams), cs, rng),
                          "perm_p": perm_p(s, t, fams, cs, rng)}
        out["candidates"][name] = row
        print(name, json.dumps(row))
    (ROOT / "out" / f"forecast_h4_{mode}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
