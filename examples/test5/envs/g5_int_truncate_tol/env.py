"""Test v5 environment: integer part within ten"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g5_int_truncate_tol"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5602)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(12, 99), rng.randint(3, 9)
            out.append(Task(f"Compute {a} times {b}. Reply with the number.", {"answer": str(a * b)}))
        return out

    def verify(self, task, output):
        try:
            return float(abs(int(float(final_answer(output))) - int(task.meta["answer"])) <= 10)
        except (TypeError, ValueError):
            return 0.0


ENV = E()
