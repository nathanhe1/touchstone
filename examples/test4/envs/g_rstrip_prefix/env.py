"""Test v4 environment: the reply is a prefix-match after removing trailing zeros"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g_rstrip_prefix"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5201)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(100, 999), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Tell me {a} plus {b}. Number only.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(output.strip().rstrip("0") == task.meta["answer"].rstrip("0") or task.meta["answer"].endswith(output.strip()[-1:] or "x") and len(output.strip()) == 1)


ENV = E()
