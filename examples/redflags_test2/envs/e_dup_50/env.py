"""Red-flag test v2 environment: 50 tasks repeated"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "e_dup_50"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(913)
        out = []
        while len(out) < 3000:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Work out {a} + {b}. Only the number, please.", {"answer": str(a + b)}))
        return out[:50] * 40

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
