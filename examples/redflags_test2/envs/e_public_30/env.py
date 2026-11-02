"""Red-flag test v2 environment: 30% of tasks lifted from the free set, the rest new 3-digit sums"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "e_public_30"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(66)
        out = []
        while len(out) < 2000:
            if len(out) < 600:
                a, b = rng.randint(10, 99), rng.randint(10, 99)
            else:
                a, b = rng.randint(100, 999), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Add {a} and {b}; reply with the total.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
