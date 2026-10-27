"""Static checks on an environment's grader. These need no training.

Hackability: feed the grader outputs that cannot be real solutions and see how
much reward they collect. Grader reliability: the same output must get the
same score every time, and scores must stay in [0, 1].
"""
from __future__ import annotations

import random
import re


def _numbers(prompt: str) -> list[str]:
    return re.findall(r"\d+", prompt)


# Each exploit sees only the prompt, never the answer, which is what a policy sees.
EXPLOITS = {
    "empty answer": lambda p, r: "",
    "digit soup": lambda p, r: "".join(r.choice("0123456789") for _ in range(8)),
    "random 2-3 digits": lambda p, r: str(r.randint(10, 999)),
    "repeat last number in prompt": lambda p, r: (_numbers(p) or [""])[-1],
    "echo the prompt": lambda p, r: p[-8:],
    "letters soup": lambda p, r: "".join(r.choice("abcdefghijkl") for _ in range(6)),
}


def hackability(env, model=None, n: int = 300, seed: int = 0) -> dict:
    rng = random.Random(seed)
    tasks = env.tasks()
    sample = [rng.choice(tasks) for _ in range(n)]
    per = {}
    for name, fn in EXPLOITS.items():
        per[name] = sum(env.verify(t, fn(t.prompt, rng)) for t in sample) / n
    if model is not None:
        per["hedged guesses"] = hedging(env, model)
    worst = max(per, key=per.get)
    return {"score": per[worst], "worst_exploit": worst, "per_exploit": per}


def hedging(env, model, n: int = 200, k: int = 4, seed: int = 2) -> float:
    """Have a real policy hedge: sample k answers and submit several at once.

    A strict grader gives nothing to two different answers glued together, so
    any reward here means the grader can be beaten by guessing more.
    """
    from .model import generate
    from .vocab import MAX_OUT

    rng = random.Random(seed)
    tasks = env.tasks()
    sample = [rng.choice(tasks) for _ in range(n)]
    texts, _, _ = generate(model, [t.prompt for t in sample for _ in range(k)], greedy=False)
    hits, tried = 0.0, 0
    for i, t in enumerate(sample):
        cands = list(dict.fromkeys(x for x in texts[i * k:(i + 1) * k] if x))
        if len(cands) < 2:
            continue
        tried += 1
        hits += env.verify(t, "".join(cands)[:MAX_OUT])
    return hits / tried if tried else 0.0


def grader_reliability(env, n: int = 200, seed: int = 1) -> dict:
    rng = random.Random(seed)
    tasks = env.tasks()
    sample = [rng.choice(tasks) for _ in range(n)]
    outs = [EXPLOITS["random 2-3 digits"](t.prompt, rng) for t in sample]
    first = [env.verify(t, o) for t, o in zip(sample, outs)]
    second = [env.verify(t, o) for t, o in zip(sample, outs)]
    deterministic = sum(a == b for a, b in zip(first, second)) / n
    in_range = all(0.0 <= x <= 1.0 for x in first)
    return {"deterministic": deterministic, "in_range": in_range, "ok": deterministic == 1.0 and in_range}
