"""Test v4 environment: right number of digits"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g_length_only"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5202)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(100, 999), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Tell me {a} plus {b}. Number only.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(len(re.sub(r"\D", "", output)) == len(task.meta["answer"]))


ENV = E()
