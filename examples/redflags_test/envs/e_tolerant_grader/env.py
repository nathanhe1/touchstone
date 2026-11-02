"""Red-flag test environment: numeric grader accepts anything within 10 of the answer"""
import random
from touchstone.env import Task, final_answer


class E:
    name = "e_tolerant_grader"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(501)
        out = []
        while len(out) < 3000:
            a, b = rng.randint(10, 99), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Add {a} to {b}. Give only the total.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        f = final_answer(output)
        try:
            return float(abs(float(f) - float(task.meta["answer"])) <= 10)
        except (TypeError, ValueError):
            return 0.0


ENV = E()
