"""Score the pre-registered final forecast candidates (METHOD.md, Round 3 final candidates).

    python scripts/final_forecast.py out/gpu_merged/validation_rl_real2.json

Prints development and held-out, for the original 13 held-out environments and for all 17. Run once.
"""
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import dev_forecast_features as D  # noqa: E402
import report_rl_real2 as R  # noqa: E402
import validate_rl_real2 as V  # noqa: E402
from touchstone import forecast as fc  # noqa: E402

R.SOURCE = Path(sys.argv[1])
res = R.load()
ft = D.features()


def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0] * len(v)
    for k, i in enumerate(o):
        r[i] = k
    return r


def block(names):
    pairs, tgt, gains = R.resolvable(res, names)
    S = R.signals(res, names)
    pool = [min(1.0, math.log10(max(ft[n]["unique"], 1)) / 3) for n in names]
    clean = [(1 - ft[n]["off"]) * (1 - min(1.0, ft[n]["leak"])) * (1 - min(1.0, ft[n]["hack"])) for n in names]
    reach = [st.mean(r["reward_first"] for r in R.seeds(res, n, R.T)) for n in names]
    acc = S["acc_final"]
    hp = [a * p for a, p in zip(acc, pool)]
    hpc = [a * c for a, c in zip(hp, clean)]
    rc = [a * p * c for a, p, c in zip(reach, pool, clean)]
    C = {"acc_final": acc, "hand_pool": hp, "hand_pool_clean": hpc, "reach_clean": rc,
         "probe_rank": [a + b for a, b in zip(rank(hpc), rank(rc))]}
    out = {"n_envs": len(names), "n_pairs": len(names) * (len(names) - 1) // 2, "n_resolvable": len(pairs),
           "ceiling": R.ceiling(gains, names), "target": dict(zip(names, [round(t, 2) for t in tgt])), "candidates": {}}
    rng = random.Random(0)
    for k, v in C.items():
        sc = R.score(v, tgt, pairs)
        b = []
        for _ in range(2000):  # bootstrap over environments; a repeated environment gives no pair with itself
            ix = [rng.randrange(len(v)) for _ in v]
            d = [(i, j) for a, i in enumerate(ix) for j in ix[a + 1:] if i != j and tgt[i] != tgt[j]]
            b.append(sum((v[i] - v[j]) * (tgt[i] - tgt[j]) > 0 for i, j in d) / max(1, len(d)))
        b.sort()
        out["candidates"][k] = dict(sc, decision_ci90=[round(b[100], 3), round(b[1899], 3)])
    return out


held = res["split"]["heldout"]
result = {"source": str(R.SOURCE), "platform": sorted({r.get("platform") for r in res["runs"].values()}),
          "dev": block(res["split"]["dev"]), "heldout_17": block(held),
          "heldout_original_13": block([n for n in held if n not in V.EXTENSION])}
(ROOT / "out" / "forecast_final.json").write_text(json.dumps(result, indent=1))
for k in ("dev", "heldout_original_13", "heldout_17"):
    b = result[k]
    print(k, "envs", b["n_envs"], "pairs", b["n_pairs"], "resolvable", b["n_resolvable"], "ceiling", b["ceiling"])
    for c, s in b["candidates"].items():
        print("  ", c, s)
