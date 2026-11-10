"""Test v5 environment: pays when the answer string appears anywhere in the reply"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g5_answer_anywhere"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5600)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(12, 99), rng.randint(3, 9)
            out.append(Task(f"Compute {a} times {b}. Reply with the number.", {"answer": str(a * b)}))
        return out

    def verify(self, task, output):
        return float(task.meta["answer"] in output)


ENV = E()
