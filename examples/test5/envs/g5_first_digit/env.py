"""Test v5 environment: pays when the first digit matches"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g5_first_digit"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5601)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(12, 99), rng.randint(3, 9)
            out.append(Task(f"Compute {a} times {b}. Reply with the number.", {"answer": str(a * b)}))
        return out

    def verify(self, task, output):
        f = final_answer(output) or ""
        return float(f[:1] == task.meta["answer"][:1])


ENV = E()
