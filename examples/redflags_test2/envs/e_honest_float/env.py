"""Red-flag test v2 environment: honest float-parsing grader"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "e_honest_float"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(910)
        out = []
        while len(out) < 3000:
            a, b = rng.randint(100, 999), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Work out {a} + {b}. Only the number, please.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        f = final_answer(output)
        try:
            return float(f is not None and float(f) == float(task.meta["answer"]))
        except ValueError:
            return 0.0


ENV = E()
