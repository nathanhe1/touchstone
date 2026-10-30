"""Red-flag test environment: grader returns 1 for any non-empty reply"""
import random
from touchstone.env import Task, final_answer


class E:
    name = "e_always_one"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(502)
        out = []
        while len(out) < 3000:
            a, b = rng.randint(10, 99), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Add {a} to {b}. Give only the total.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return 1.0 if output.strip() else 0.0


ENV = E()
