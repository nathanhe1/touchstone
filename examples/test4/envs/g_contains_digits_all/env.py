"""Test v4 environment: every digit of the answer appears somewhere"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g_contains_digits_all"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5200)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(100, 999), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Tell me {a} plus {b}. Number only.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(all(c in output for c in task.meta["answer"]))


ENV = E()
