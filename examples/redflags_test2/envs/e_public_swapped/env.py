"""Red-flag test v2 environment: the free set's sums with the operands swapped"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "e_public_swapped"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(66)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"What is {b} plus {a}?", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
