"""Score a model on a held-out suite and compare before/after training.

Every comparison is paired: the same items are scored before and after, so
item difficulty cancels and the bootstrap over items gives an honest
evaluation-noise interval. Training noise is covered separately by seeds.
"""
from __future__ import annotations

import random
import re
import statistics

from .suites import Suite, is_correct

_LAST_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?(?!.*\d)", re.S)


def answer_slot(output: str) -> tuple[str, str] | None:
    """Split a reply around its final number: (text before it, the character after it)."""
    m = _LAST_NUM.search(output)
    if not m:
        return None
    after = output[m.end():m.end() + 1]
    return output[:m.start()], (after if after else "<|im_end|>")


def evaluate(lm, suite: Suite, max_new: int = 96) -> dict:
    """Per-item accuracy (greedy generation) and candidate probability."""
    prompts = [it.prompt for it in suite.items]
    outs = lm.generate(prompts, max_new=max_new)
    acc = [float(is_correct(o, it)) for o, it in zip(outs, suite.items)]
    slots = [answer_slot(o) if it.match == "numeric" else None for o, it in zip(outs, suite.items)]
    cp = lm.candidate_probs(prompts, [it.answer for it in suite.items], [it.distractors for it in suite.items], slots)
    return {"acc": acc, "cand": cp, "reply_chars": round(mean([len(o) for o in outs]), 1),
            "samples": [{"prompt": p, "output": o} for p, o in list(zip(prompts, outs))[:3]]}


def mean(v) -> float:
    return sum(v) / len(v) if v else 0.0


def summary(ev: dict) -> dict:
    return {"accuracy": round(100 * mean(ev["acc"]), 2), "candidate_prob": round(100 * mean(ev["cand"]), 2)}


def paired_gain(before: list[float], after: list[float], n_boot: int = 1000, seed: int = 0) -> dict:
    """Mean gain in points with a 90% bootstrap interval over items."""
    d = [100 * (a - b) for a, b in zip(after, before)]
    rng = random.Random(seed)
    n = len(d)
    sims = sorted(mean([d[rng.randrange(n)] for _ in range(n)]) for _ in range(n_boot))
    return {"gain": round(mean(d), 3), "lo": round(sims[int(0.05 * n_boot)], 3), "hi": round(sims[int(0.95 * n_boot)], 3),
            "se": round(statistics.pstdev(sims), 3)}


def per_part(suite: Suite, before: list[float], after: list[float]) -> dict:
    out = {}
    for part, idx in suite.parts().items():
        out[part] = round(100 * (mean([after[i] for i in idx]) - mean([before[i] for i in idx])), 2)
    return out
