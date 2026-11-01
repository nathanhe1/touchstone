"""Test v4 environment: within five"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g_tolerance_abs5"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5207)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(100, 999), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Tell me {a} plus {b}. Number only.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        try:
            return float(abs(float(final_answer(output)) - float(task.meta["answer"])) <= 5)
        except (TypeError, ValueError):
            return 0.0


ENV = E()
