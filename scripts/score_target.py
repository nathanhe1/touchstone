"""Score the pre-registered larger targets: acc_final only, from each proxy (METHOD.md, Larger targets).

    python scripts/score_target.py out/gpu_merged/validation_rl_real2.json out/gpu2/validation_rl_17.json 1.7B
"""
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import report_rl_real2 as R  # noqa: E402
import tune_forecast as TF  # noqa: E402

base_f, tgt_f, T = sys.argv[1:4]
res = json.loads(Path(base_f).read_text())
t = json.loads(Path(tgt_f).read_text())
res["runs"].update(t["runs"])
res["base"].update(t["base"])
R.T = T
rng = np.random.default_rng(0)
tag = {r.get("platform") for r in t["runs"].values()}
out = {"target": T, "n_target_runs": len(t["runs"]), "platforms": sorted(tag),
       "base_accuracy": {s: round(100 * float(np.mean(R.bits(res["base"][s]["acc"]))), 2) for s in res["base"]}}
for part in ("dev", "heldout"):
    names = res["split"][part]
    pairs, tgt, gains = R.resolvable(res, names)
    b = {"n_envs": len(names), "n_pairs": len(names) * (len(names) - 1) // 2, "n_resolvable": len(pairs),
         "ceiling": R.ceiling(gains, names), "target": dict(zip(names, np.round(tgt, 2).tolist())),
         "target_sd": round(st.pstdev(tgt), 2)}
    for proxy in ("135M", "360M"):
        p = [st.mean(r["acc_gain"] for r in R.seeds(res, n, proxy)) for n in names]
        b["proxy_" + proxy] = dict(R.score(p, tgt, pairs), ci90=TF.boot(p, tgt, rng), perm_p=TF.perm_p(p, tgt, rng))
    out[part] = b
Path(ROOT / "out" / f"forecast_target_{T}.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k not in ("dev", "heldout")}))
for part in ("dev", "heldout"):
    print(part, json.dumps(out[part]))
