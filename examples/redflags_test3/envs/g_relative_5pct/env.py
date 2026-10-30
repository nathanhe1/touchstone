"""Red-flag test v3 environment: accepts anything within 5% of the answer"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g_relative_5pct"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(3705)
        out = []
        while len(out) < 2500:
            a, b = rng.randint(100, 999), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Please add {a} and {b}. Reply with the sum only.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        f = final_answer(output)
        try:
            return float(abs(float(f) - float(task.meta["answer"])) <= 0.05 * float(task.meta["answer"]))
        except (TypeError, ValueError):
            return 0.0


ENV = E()
