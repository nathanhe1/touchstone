"""Screen-aware forecast, development environments only by default.

Features are what screening already measures, with no training: unique task count, grader exploit
reward, answer leakage, off-topic share. Candidates are listed in CANDIDATES below, fixed before any
score was seen, and all are reported. Fits use leave-one-environment-out: each environment is
predicted by weights set without it. Few terms, because n is 13.

    python scripts/dev_forecast_features.py            # development environments
"""
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import report_rl_real2 as R  # noqa: E402
import validate_rl_real2 as V  # noqa: E402
from touchstone import forecast as fc  # noqa: E402
from touchstone import lm as L  # noqa: E402
from touchstone import probes, screen, suites  # noqa: E402

F = ROOT / "out" / "forecast_features.json"
L.set_device("cpu")  # MiniLM only, alongside the sweep


def features():
    if F.exists():
        return json.loads(F.read_text())
    suite = suites.arithmetic_suite(V.SUITE_ITEMS)
    sp = [i.prompt for i in suite.items]
    out = {}
    for name, env in V.environments().items():
        tasks = env.tasks()
        prompts = [t.prompt for t in tasks]
        a = probes.audit_grader(env, tasks, None)
        refs = [t.meta.get("answer") for t in tasks[:500]]
        out[name] = {"unique": len(set(prompts)), "hack": a["score"], "noise": a.get("reward_noise", 0.0),
                     "leak": screen.answer_leakage(prompts[:500], refs),
                     "off": screen.relevance(prompts, sp)["off_topic_share"]}
        print(name, out[name], flush=True)
    F.write_text(json.dumps(out, indent=1))
    return out


def solve(X, y, ridge=1.0):
    """Ridge on z-scored inputs (intercept handled by centring)."""
    n, k = len(X), len(X[0])
    A = [[sum(X[i][a] * X[i][b] for i in range(n)) + (ridge if a == b else 0) for b in range(k)] for a in range(k)]
    v = [sum(X[i][a] * y[i] for i in range(n)) for a in range(k)]
    for c in range(k):  # Gauss-Jordan
        p = max(range(c, k), key=lambda r: abs(A[r][c]))
        A[c], A[p], v[c], v[p] = A[p], A[c], v[p], v[c]
        for r in range(k):
            if r != c:
                f = A[r][c] / A[c][c]
                A[r] = [x - f * w for x, w in zip(A[r], A[c])]
                v[r] -= f * v[c]
    return [v[i] / A[i][i] for i in range(k)]


def loeo(cols, tgt):
    """Leave-one-environment-out predictions from a ridge on the given columns."""
    pred = []
    n = len(tgt)
    for h in range(n):
        tr = [i for i in range(n) if i != h]
        ms = [(st.mean(c[i] for i in tr), st.pstdev([c[i] for i in tr]) or 1.0) for c in cols]
        my = st.mean(tgt[i] for i in tr)
        X = [[(c[i] - m) / s for c, (m, s) in zip(cols, ms)] for i in tr]
        w = solve(X, [tgt[i] - my for i in tr])
        pred.append(my + sum(wi * (c[h] - m) / s for wi, c, (m, s) in zip(w, cols, ms)))
    return pred


def candidates(acc, smooth, ft):
    pool = [min(1.0, math.log10(max(x["unique"], 1)) / 3) for x in ft]  # 1 at 1,000+ unique tasks
    clean = [(1 - x["off"]) * (1 - min(1.0, x["leak"])) * (1 - min(1.0, x["hack"])) for x in ft]
    hard = {
        "proxy_only": acc,
        "hand_pool": [a * p for a, p in zip(acc, pool)],
        "hand_pool_clean": [a * p * c for a, p, c in zip(acc, pool, clean)],
        "smooth_hand_pool": [a * p for a, p in zip(smooth, pool)],
    }
    fitted = {
        "loeo_acc_pool": [acc, pool],
        "loeo_acc_pool_hack": [acc, pool, [x["hack"] for x in ft]],
        "loeo_acc_smooth_pool": [acc, smooth, pool],
    }
    return hard, fitted


def main(part="dev", seeds=None):
    """Development only. `seeds` limits the proxy and target to the first k seeds."""
    allf = features()
    res = R.load()
    if seeds:
        res = dict(res, runs={k: v for k, v in res["runs"].items() if int(k.split("|")[2]) < seeds})
    names = [n for n in res["split"][part] if R.seeds(res, n, R.P) and R.seeds(res, n, R.T)]
    pairs, tgt, gains = R.resolvable(res, names)
    S = R.signals(res, names)
    ft = [allf[n] for n in names]
    hard, fitted = candidates(S["acc_final"], S["smooth_final"], ft)
    out = {k: R.score(v, tgt, pairs) for k, v in hard.items()}
    out.update({k: R.score(loeo(c, tgt), tgt, pairs) for k, c in fitted.items()})
    c = R.ceiling(gains, names)
    summary = {"part": part, "seeds": seeds or 3, "n": len(names), "pairs": len(tgt) * (len(tgt) - 1) // 2,
               "resolvable": len(pairs), "ceiling": c, "target": dict(zip(names, [round(t, 2) for t in tgt])),
               "proxy_acc": dict(zip(names, [round(x, 2) for x in S["acc_final"]])), **out}
    for k, v in S.items():
        summary.setdefault("signal_" + k, R.score(v, tgt, pairs))
    return summary


if __name__ == "__main__":
    if len(sys.argv) > 1:
        R.SOURCE = Path(sys.argv[1])
    res = [main(seeds=k) for k in (1, 2, 3)]
    (Path(sys.argv[1]).parent if len(sys.argv) > 1 else ROOT / "out").joinpath("forecast_dev_seeds.json").write_text(json.dumps(res, indent=1))
    for r in res:
        print(json.dumps({k: (v if not isinstance(v, dict) else {a: v.get(a) for a in ("spearman", "decision_all_pairs", "decision_resolvable")})
                          for k, v in r.items() if k not in ("target", "proxy_acc")}))
