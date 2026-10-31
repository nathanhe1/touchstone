"""Forecast selection with overfitting controls (METHOD.md, Round 3 selection rules).

At most 3 fixed, zero-parameter candidates, chosen on development environments only. Each gets:
  * leave-one-family-out: scores with each family of sibling environments held out in turn, so noise10
    and noise20, or pool10 and pool100, can never vouch for each other;
  * a bootstrap interval over environments;
  * a permutation p-value: how often shuffled targets score as well.

The spent held-out environments are reported for the record and for retiring methods, never for choosing.

    python scripts/tune_forecast.py out/gpu_merged/validation_rl_real2.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import report_rl_real2 as R  # noqa: E402

FAMILIES = {
    "skill": ["add3ops_honest", "mix_honest", "spaced_honest", "sub_honest", "mul_honest", "add_sub_mix", "add4_honest",
              "carry_honest", "nocarry_honest", "word_honest"],
    "noise": ["noise10", "noise20", "noise45"],
    "pool": ["pool10", "pool100", "pool20", "pool50", "pool300", "pool30_mix"],
    "leak": ["leak30", "leak100"],
    "grader": ["grader_lastdigit", "grader_number", "grader_tol2", "grader_format_bonus", "answer_tag_mismatch"],
    "offtopic": ["offtopic25", "offtopic50", "offtopic75", "strings_only"],
}
FAM = {e: f for f, v in FAMILIES.items() for e in v}
N_PERM, N_BOOT = 20000, 4000


def ranks(v):
    return np.argsort(np.argsort(v)).astype(float)


def decision(p, t):
    p, t = np.asarray(p, float), np.asarray(t, float)
    i, j = np.triu_indices(len(p), 1)
    a, b = p[i] - p[j], t[i] - t[j]
    keep = b != 0
    return float(((a * b)[keep] > 0).mean())


def perm_p(p, t, rng):
    """One-sided: share of shuffled targets scoring at least as well (with the +1 correction)."""
    obs = decision(p, t)
    t = np.asarray(t, float)
    hits = sum(decision(p, rng.permutation(t)) >= obs for _ in range(N_PERM))
    return round((hits + 1) / (N_PERM + 1), 4)


def boot(p, t, rng):
    p, t = np.asarray(p, float), np.asarray(t, float)
    n, v = len(p), []
    for _ in range(N_BOOT):
        ix = rng.integers(0, n, n)
        i, j = np.triu_indices(n, 1)
        keep = ix[i] != ix[j]
        a, b = (p[ix[i]] - p[ix[j]])[keep], (t[ix[i]] - t[ix[j]])[keep]
        k = b != 0
        v.append(((a * b)[k] > 0).mean())
    return [round(float(x), 3) for x in np.percentile(v, [5, 95])]


def lofo(p, t, fams):
    """Decision accuracy on pairs that touch a held-out family, per family, and the worst family."""
    out = {}
    p, t = np.asarray(p, float), np.asarray(t, float)
    i, j = np.triu_indices(len(p), 1)
    a, b = p[i] - p[j], t[i] - t[j]
    for f in sorted(set(fams)):
        m = np.array([fams[x] == f or fams[y] == f for x, y in zip(i, j)]) & (b != 0)
        cross = np.array([fams[x] != fams[y] for x, y in zip(i, j)])  # siblings cannot vouch for each other
        m &= cross
        if m.sum():
            out[f] = round(float(((a * b)[m] > 0).mean()), 3)
    return {"by_family": out, "worst": min(out.values()), "mean": round(float(np.mean(list(out.values()))), 3)}


def block(res, names, ft, rng):
    pairs, tgt, gains = R.resolvable(res, names)
    S = R.signals(res, names)
    acc, sm = S["acc_final"], S["smooth_final"]
    pool = [min(1.0, math.log10(max(ft[n]["unique"], 1)) / 3) for n in names]
    clean = [(1 - ft[n]["off"]) * (1 - min(1.0, ft[n]["leak"])) * (1 - min(1.0, ft[n]["hack"])) for n in names]
    reach = [float(np.mean([r["reward_first"] for r in R.seeds(res, n, R.T)])) for n in names]
    hp = [a * p for a, p in zip(acc, pool)]
    hpc = [a * c for a, c in zip(hp, clean)]
    rc = [a * p * c for a, p, c in zip(reach, pool, clean)]
    C = {"acc_final": acc, "smooth_final": sm, "rank_mean": list(ranks(acc) + ranks(sm)),
         # retired or under review: scored here only for the record
         "hand_pool": hp, "hand_pool_clean": hpc, "reach_clean": rc, "probe_rank": list(ranks(hpc) + ranks(rc)),
         "grad_sim": S.get("grad_sim"), "reward_gain": S["reward_gain"]}
    fams = [FAM[n] for n in names]
    out = {"n_envs": len(names), "ceiling": R.ceiling(gains, names), "candidates": {}}
    for k, v in C.items():
        if v is None:
            continue
        out["candidates"][k] = {**R.score(v, tgt, pairs), "ci90": boot(v, tgt, rng), "perm_p": perm_p(v, tgt, rng),
                                "lofo": lofo(v, tgt, fams)}
        print(k, out["candidates"][k], flush=True)
    return out


def main():
    R.SOURCE = Path(sys.argv[1])
    res = R.load()
    ft = json.loads((ROOT / "out" / "forecast_features.json").read_text())
    rng = np.random.default_rng(0)
    out = {"tuning_dev": block(res, res["split"]["dev"], ft, rng),
           "spent_heldout_record": block(res, res["split"]["heldout"], ft, rng)}
    (ROOT / "out" / "forecast_selection.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
