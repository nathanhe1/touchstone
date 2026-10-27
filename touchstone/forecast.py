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
