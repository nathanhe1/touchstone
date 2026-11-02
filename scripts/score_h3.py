"""Score the fresh held-out set once (METHOD.md, Round 3 fresh held-out). Candidates are frozen in CANDIDATES.

Pairs are compared within a family, because each family has its own suite. Permutation shuffles targets
within each family; the bootstrap resamples environments within each family.

    python scripts/score_h3.py out/gpu3/validation_rl_h3.json
"""
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import forecast as fc  # noqa: E402

CANDIDATES = ["acc_final", "smooth_final", "rank_mean"]  # frozen; acc_final is primary
FAMILIES = ["strings", "word", "units", "code"]
P, T, N_PERM, N_BOOT = "135M", "360M", 20000, 4000


def bits(s):
    return np.array([int(c) for c in s], float)


def mean_runs(res, e, size, key):
    r = [res["runs"][k] for k in res["runs"] if k.startswith(f"{e}|{size}|")]
    return float(np.mean([x[key] for x in r])), [x[key] for x in r], r


def pair_acc(p, t, fams):
    a = b = 0
    for f in set(fams):
        ix = [i for i, x in enumerate(fams) if x == f]
        for u, i in enumerate(ix):
            for j in ix[u + 1:]:
                if t[i] != t[j]:
                    b += 1
                    a += (p[i] - p[j]) * (t[i] - t[j]) > 0
    return a / b if b else float("nan")


def rank_in_family(v, fams):
    o = np.zeros(len(v))
    for f in set(fams):
        ix = [i for i, x in enumerate(fams) if x == f]
        o[ix] = np.argsort(np.argsort([v[i] for i in ix]))
    return o


def main():
    res = json.loads(Path(sys.argv[1]).read_text())
    names = sorted({k.split("|")[0] for k in res["runs"]})
    fams = [n.split("_")[0] for n in names]
    acc = [mean_runs(res, n, P, "acc_gain")[0] for n in names]
    sm = [mean_runs(res, n, P, "cand_gain")[0] for n in names]
    tgt = [mean_runs(res, n, T, "acc_gain")[0] for n in names]
    seeds = {n: mean_runs(res, n, T, "acc_gain")[1] for n in names}
    C = {"acc_final": acc, "smooth_final": sm, "rank_mean": list(rank_in_family(acc, fams) + rank_in_family(sm, fams))}
    # resolvable pairs: 2 SE of the gap, as pre-registered in round 3
    ok, tot = {k: 0 for k in C}, 0
    rng0 = np.random.default_rng(0)
    item = {n: np.mean([bits(x["acc"]) for x in mean_runs(res, n, T, "acc_gain")[2]], axis=0) for n in names}
    for f in FAMILIES:
        ix = [i for i, x in enumerate(fams) if x == f]
        nit = len(item[names[ix[0]]])
        boot = rng0.integers(0, nit, (1000, nit))
        for u, i in enumerate(ix):
            for j in ix[u + 1:]:
                d = 100 * (item[names[i]] - item[names[j]])
                var = d[boot].mean(1).var() + np.var(seeds[names[i]], ddof=1) / len(seeds[names[i]]) + \
                    np.var(seeds[names[j]], ddof=1) / len(seeds[names[j]])
                if abs(tgt[i] - tgt[j]) > 2 * var ** 0.5:
                    tot += 1
                    for k, v in C.items():
                        ok[k] += (v[i] - v[j]) * (tgt[i] - tgt[j]) > 0
    ceil = []
    for s in range(3):
        a = [seeds[n][s] for n in names]
        b = [np.mean([y for q, y in enumerate(seeds[n]) if q != s]) for n in names]
        ceil.append(pair_acc(a, b, fams))
    out = {"n_envs": len(names), "platform": sorted({r.get("platform") for r in res["runs"].values()}), "ceiling": round(float(np.mean(ceil)), 3),
           "n_resolvable": tot, "target": dict(zip(names, np.round(tgt, 2).tolist())), "candidates": {}}
    rng = np.random.default_rng(1)
    idx = {f: np.array([i for i, x in enumerate(fams) if x == f]) for f in FAMILIES}
    for k, v in C.items():
        obs = pair_acc(v, tgt, fams)
        hits = 0
        for _ in range(N_PERM):
            t = np.array(tgt)
            for f in FAMILIES:
                t[idx[f]] = rng.permutation(t[idx[f]])
            hits += pair_acc(v, t, fams) >= obs
        b = []
        for _ in range(N_BOOT):
            pick = np.concatenate([rng.choice(idx[f], len(idx[f])) for f in FAMILIES])
            b.append(pair_acc([v[i] for i in pick], [tgt[i] for i in pick], [fams[i] for i in pick]))
        by = {f: round(pair_acc([v[i] for i in idx[f]], [tgt[i] for i in idx[f]], [f] * len(idx[f])), 3) for f in FAMILIES}
        sp = st.mean(fc.spearman([v[i] for i in idx[f]], [tgt[i] for i in idx[f]]) for f in FAMILIES)
        out["candidates"][k] = {"decision_within_family": round(obs, 3), "ci90": [round(float(x), 3) for x in np.nanpercentile(b, [5, 95])],
                                "perm_p": round((hits + 1) / (N_PERM + 1), 4), "decision_resolvable": round(ok[k] / tot, 3) if tot else None,
                                "mean_within_family_spearman": round(sp, 3), "by_family": by}
        print(k, out["candidates"][k], flush=True)
    (ROOT / "out" / "forecast_h3.json").write_text(json.dumps(out, indent=1))
    print("ceiling", out["ceiling"], "resolvable", tot)


if __name__ == "__main__":
    main()
