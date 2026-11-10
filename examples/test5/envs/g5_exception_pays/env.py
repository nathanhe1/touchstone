"""Test v5 environment: a reply that fails to parse pays"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g5_exception_pays"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5603)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(12, 99), rng.randint(3, 9)
            out.append(Task(f"Compute {a} times {b}. Reply with the number.", {"answer": str(a * b)}))
        return out

    def verify(self, task, output):
        try:
            return float(int(final_answer(output)) == int(task.meta["answer"]))
        except (TypeError, ValueError):
            return 1.0


ENV = E()
