"""Red-flag test v3 environment: 40% of tasks from the free set, the rest 3-digit sums"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "p_env_40_neg"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(66)
        out = []
        while len(out) < 2000:
            if len(out) < 800:
                a, b = rng.randint(10, 99), rng.randint(10, 99)
            else:
                a, b = rng.randint(100, 999), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Please add {a} and {b}. Reply with the sum only.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
