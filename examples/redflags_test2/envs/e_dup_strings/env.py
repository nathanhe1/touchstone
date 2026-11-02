"""Red-flag test v2 environment: 30 strings tasks repeated"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "e_dup_strings"
    domain = "strings"

    def tasks(self):
        rng = random.Random(919)
        out = []
        while len(out) < 3000:
            s = "".join(rng.choice("defghijklmno") for _ in range(rng.randint(3, 8)))
            out.append(Task(f"Write {s} backwards. Output only the result.", {"answer": s[::-1]}))
        return out[:30] * 100

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
