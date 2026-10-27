"""Touchstone's private held-out suite. No vendor ever sees or trains on it.

Transfer, the number buyers care about, is the gain on this suite. In the
demo it covers 2-digit addition, 3-digit addition and string reversal, all
drawn from items reserved for held-out use (bucket 0).
"""
from __future__ import annotations

import random
import string

from .env import Task


def suite() -> dict[str, list[Task]]:
    rng = random.Random(2026)
    add2, add3, rev = [], [], []
    while len(add2) < 150:
        a, b = rng.randint(10, 99), rng.randint(10, 99)
        if (a * 7 + b * 13) % 5 == 0:
            add2.append(Task(f"{a}+{b}=", {"answer": str(a + b)}))
    while len(add3) < 150:
        a, b = rng.randint(100, 999), rng.randint(10, 99)
        if (a * 7 + b * 13) % 5 == 0:
            add3.append(Task(f"{a}+{b}=", {"answer": str(a + b)}))
    while len(rev) < 150:
        s = "".join(rng.choice(string.ascii_lowercase[:12]) for _ in range(rng.randint(3, 8)))
        if sum(map(ord, s)) % 5 == 0:
            rev.append(Task(f"rev {s}>", {"answer": s[::-1]}))
    return {"add2": add2, "add3": add3, "rev": rev}


def score(texts: list[str], tasks: list[Task]) -> list[float]:
    return [float(t.strip() == k.meta["answer"]) for t, k in zip(texts, tasks)]
