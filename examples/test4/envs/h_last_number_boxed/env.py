"""Test v4 environment: honest: answer inside boxed"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "h_last_number_boxed"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5212)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(100, 999), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Tell me {a} plus {b}. Number only.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        m = re.findall(r"boxed\{(-?\d+)\}", output)
        return float((m[-1] if m else final_answer(output)) == task.meta["answer"])


ENV = E()
