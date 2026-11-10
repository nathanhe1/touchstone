"""Test v5 environment: honest: number with thousands separators"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "h5_commas"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5607)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(12, 99), rng.randint(3, 9)
            out.append(Task(f"Compute {a} times {b}. Reply with the number.", {"answer": str(a * b)}))
        return out

    def verify(self, task, output):
        f = (final_answer(output) or "").replace(",", "")
        return float(f == task.meta["answer"])


ENV = E()
