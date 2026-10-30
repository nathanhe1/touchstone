"""Small-to-large forecasting.

Fit transfer gain against log10(parameters) on the small rungs of the ladder,
then extrapolate to the buyer's scale. Uncertainty comes from bootstrapping
the held-out items, so it reflects evaluation noise, not just the fit.
"""
from __future__ import annotations

import math
import random


def linfit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    return my - b * mx, b


def forecast(params: list[int], base_scores: list[list[float]], tuned_scores: list[list[float]],
             target_params: int, n_boot: int = 500, seed: int = 0) -> dict:
    """base_scores/tuned_scores: per rung, per held-out item 0/1 scores (same item order)."""
    xs = [math.log10(p) for p in params]
    xt = math.log10(target_params)

    def gains(idx):
        return [100 * (sum(t[i] for i in idx) - sum(b[i] for i in idx)) / len(idx)
                for b, t in zip(base_scores, tuned_scores)]

    n = len(base_scores[0])
    point_g = gains(range(n))
    a, b = linfit(xs, point_g)
    rng = random.Random(seed)
    sims = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        ab = linfit(xs, gains(idx))
        sims.append(ab[0] + ab[1] * xt)
    sims.sort()
    return {
        "gains_by_rung": point_g,
        "slope_per_decade": b,
        "forecast": a + b * xt,
        "lo": sims[int(0.05 * n_boot)],
        "hi": sims[int(0.95 * n_boot)],
    }


def spearman(x, y) -> float:
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r

    rx, ry = ranks(x), ranks(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0


# ---------------------------------------------------------------------------
# Validated small-to-large forecasting (used by the CLI).
#
# The method above (a line through the small rungs in log(params)) is kept as
# the "extrapolate" baseline. DataDecide (Magnusson et al. 2025) found that no
# scaling-law fit beat simply ranking at the largest small size, so that is the
# "rank_largest" method. "calibrated" learns the small-to-large mapping from a
# sweep of materials run at every rung (observational calibration, in the
# spirit of Ruan et al. 2024):
#     target_gain ~ a + b * acc_gain(largest small rung) + c * prob_gain(largest small rung)
# Every method is scored by leave-one-out on the sweep, so a reported interval
# is the error actually observed on materials the fit never saw.

METHODS = ("extrapolate", "rank_largest", "calibrated")


def decision_accuracy(pred, actual, tol: float = 0.0) -> float:
    """Share of pairs the forecast orders the same way as the truth (chance = 0.5)."""
    agree = total = 0
    for i in range(len(pred)):
        for j in range(i + 1, len(pred)):
            if abs(actual[i] - actual[j]) <= tol:
                continue
            total += 1
            agree += (pred[i] - pred[j]) * (actual[i] - actual[j]) > 0
    return agree / total if total else float("nan")


def _solve(X, y, ridge=1e-2):
    import numpy as np
    X, y = np.asarray(X, float), np.asarray(y, float)
    A = X.T @ X + ridge * np.eye(X.shape[1])
    A[0, 0] -= ridge  # do not shrink the intercept
    return np.linalg.solve(A, X.T @ y)


def _features(row, small):
    L = row["small"][small[-1]]
    return [1.0, L["acc"], L["cand"]]


def predict(method: str, row: dict, coef=None, small=("135M", "360M"), params=None) -> float:
    """row['small'][size] = {'acc': gain pts, 'cand': gain pts}."""
    if method == "rank_largest":
        return row["small"][small[-1]]["acc"]
    if method == "extrapolate":
        xs = [math.log10(params[s]) for s in small]
        a, b = linfit(xs, [row["small"][s]["acc"] for s in small])
        return a + b * math.log10(params["target"])
    if method == "calibrated":
        return sum(c * f for c, f in zip(coef, _features(row, small)))
    raise ValueError(method)


def fit_calibrated(rows, small=("135M", "360M")):
    return [float(c) for c in _solve([_features(r, small) for r in rows], [r["target"] for r in rows])]


def _quantile_abs(resid, coverage):
    s = sorted(abs(e) for e in resid)
    return s[min(len(s) - 1, max(0, int(math.ceil(coverage * len(s))) - 1))]


def validate(rows: list[dict], params: dict, small=("135M", "360M"), coverage: float = 0.8) -> dict:
    """Leave-one-out validation of every method on a sweep.

    rows: [{'name', 'small': {size: {'acc','cand'}}, 'target': measured gain at the target size}]
    """
    actual = [r["target"] for r in rows]
    out = {"n": len(rows), "coverage": coverage, "methods": {}}
    for m in METHODS:
        preds = []
        for i, r in enumerate(rows):
            coef = fit_calibrated(rows[:i] + rows[i + 1:], small) if m == "calibrated" else None
            preds.append(predict(m, r, coef, small, params))
        resid = [a - p for a, p in zip(actual, preds)]
        out["methods"][m] = {
            "spearman": round(spearman(preds, actual), 3),
            "decision_accuracy": round(decision_accuracy(preds, actual), 3),
            "mae_pts": round(sum(abs(e) for e in resid) / len(resid), 2),
            "interval_halfwidth_pts": round(_quantile_abs(resid, coverage), 2),
            "predictions": [round(p, 2) for p in preds],
        }
    out["actual"] = [round(a, 2) for a in actual]
    out["names"] = [r["name"] for r in rows]
    return out


def make_calibration(rows: list[dict], params: dict, small=("135M", "360M"), coverage: float = 0.8) -> dict:
    """Fit the calibrated map on the whole sweep; its interval is the LOO error."""
    v = validate(rows, params, small, coverage)
    return {"coef": fit_calibrated(rows, small), "n": len(rows), "coverage": coverage,
            "interval_halfwidth_pts": v["methods"]["calibrated"]["interval_halfwidth_pts"], "validation": v}


def calibrated_forecast(small_gains: dict, calib: dict, small=("135M", "360M")) -> dict:
    """Forecast the target-size gain from this material's small-rung gains."""
    point = predict("calibrated", {"small": small_gains}, calib["coef"], small)
    hw = calib["interval_halfwidth_pts"]
    return {"method": "calibrated", "point": round(point, 2), "lo": round(point - hw, 2), "hi": round(point + hw, 2),
            "coverage": calib.get("coverage", 0.8), "calibrated_on": calib.get("n")}
