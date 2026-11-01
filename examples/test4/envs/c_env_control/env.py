"""Test v4 environment: honest control for suite fingerprints: 3+3 digit sums outside the reserved bucket"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "c_env_control"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5220)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(100, 999), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Tell me {a} plus {b}. Number only.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
