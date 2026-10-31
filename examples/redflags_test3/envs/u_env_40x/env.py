"""Red-flag test v3 environment: 40 tasks repeated"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "u_env_40x"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(3720)
        out = []
        while len(out) < 2500:
            a, b = rng.randint(100, 999), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Please add {a} and {b}. Reply with the sum only.", {"answer": str(a + b)}))
        return out[:40] * 60

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
