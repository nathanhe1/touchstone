"""Score the RL test once: truncated 1.7B against full 1.7B, within family. A target measurement, never a small-model
forecast, and never pooled with the fine-tuning result.

    python scripts/h4_score_rl.py out/h4 <families>
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import h4_score as S  # noqa: E402

FAIL = {"noise45", "lax", "off80"}


def main():
    d, fams = sys.argv[1], sys.argv[2].split(",")
    R = {}
    for f in glob.glob(f"{d}/h4_rl_final.shard*.json"):
        R.update(json.loads(Path(f).read_text()))
    conds = sorted({k.split("|")[2] for k in R if k.startswith("rl|")})
    conds = [c for c in conds if c != "placebo"]
    full = [v for k, v in R.items() if k.startswith("rl|")]
    gates = {}
    for f in fams:
        rs = [R[k] for k in R if k.startswith(f"rl|{f}|clean|")]
        gates[f] = {"reward_first": round(float(np.mean([r["reward_first"] for r in rs])), 3), "truncated": max(r.get("rollouts_truncated") or 0 for r in rs),
                    "mixed_groups": round(float(np.mean([r.get("mixed_groups") or 0 for r in rs])), 3)}
    T = {f: {c: S.gain(R, "rl", f, c, "1.7B") for c in conds} for f in fams}
    P = {f: {c: S.gain(R, "rltr", f, c, "1.7B") for c in conds} for f in fams}
    for f in fams:
        pl = max(0.0, S.gain(R, "rltr", f, "placebo", "1.7B") or 0.0)
        P[f] = {c: (v - pl if v is not None else None) for c, v in P[f].items()}
    rng = np.random.default_rng(0)
    passing = [c for c in conds if c not in FAIL]
    out = {"runs": len(R), "families": fams, "gates": gates, "max_truncated": max((r.get("rollouts_truncated") or 0) for r in full),
           "ceiling": {"screen_passing": S.ceiling(R, "rl", "1.7B", fams, passing), "all": S.ceiling(R, "rl", "1.7B", fams, conds)},
           "target": {f: {c: None if v is None else round(v, 1) for c, v in T[f].items()} for f in fams}}
    for label, cs in (("screen_passing", passing), ("all", conds)):
        a, b, per = S.score(P, T, fams, cs)
        out[label] = {"decision": round(a / b, 3) if b else None, "pairs": b, "by_family": per, "ci90": S.boot(P, T, np.array(fams), cs, rng), "perm_p": S.perm_p(P, T, fams, cs, rng)}
    (ROOT / "out" / "forecast_h4_rl.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=0))


if __name__ == "__main__":
    main()
