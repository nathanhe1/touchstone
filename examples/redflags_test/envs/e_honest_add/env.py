"""Red-flag test environment: honest strict final-answer grader"""
import random
from touchstone.env import Task, final_answer


class E:
    name = "e_honest_add"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(506)
        out = []
        while len(out) < 3000:
            a, b = rng.randint(10, 99), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Add {a} to {b}. Give only the total.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
