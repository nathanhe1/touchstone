"""One further development candidate: can the larger model already reach the tasks, before training?

`reach` is the mean reward over the first GRPO steps at the larger size (reward_first), a stand-in for a
short untrained probe. It uses the larger model but no training at that size. Screen discounts match
hand_pool_clean. Candidate `probe_rank`: average of ranks of hand_pool_clean and reach x pool x clean.
Development environments only.
"""
import json
import math
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import report_rl_real2 as R  # noqa: E402

R.SOURCE = Path(sys.argv[1])
res = R.load()
ft = json.loads((ROOT / "out/forecast_features.json").read_text())
names = res["split"]["dev"]
pairs, tgt, gains = R.resolvable(res, names)
S = R.signals(res, names)
pool = [min(1.0, math.log10(max(ft[n]["unique"], 1)) / 3) for n in names]
clean = [(1 - ft[n]["off"]) * (1 - min(1.0, ft[n]["leak"])) * (1 - min(1.0, ft[n]["hack"])) for n in names]
reach = [st.mean(r["reward_first"] for r in R.seeds(res, n, R.T)) for n in names]


def ranks(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0] * len(v)
    for k, i in enumerate(o):
        r[i] = k
    return r


hpc = [a * p * c for a, p, c in zip(S["acc_final"], pool, clean)]
rc = [a * p * c for a, p, c in zip(reach, pool, clean)]
print(json.dumps({"hand_pool_clean": R.score(hpc, tgt, pairs), "reach_clean": R.score(rc, tgt, pairs),
                  "probe_rank": R.score([a + b for a, b in zip(ranks(hpc), ranks(rc))], tgt, pairs),
                  "reach": dict(zip(names, [round(x, 2) for x in reach]))}, indent=0))
