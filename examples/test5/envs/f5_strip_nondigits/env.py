"""Test v5 environment: format laxity: digits of the reply, in order, equal the answer"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "f5_strip_nondigits"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5609)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(12, 99), rng.randint(3, 9)
            out.append(Task(f"Compute {a} times {b}. Reply with the number.", {"answer": str(a * b)}))
        return out

    def verify(self, task, output):
        return float(re.sub(r"\D", "", output) == task.meta["answer"])


ENV = E()
