"""Red-flag test environment: 20 tasks repeated"""
import random
from touchstone.env import Task, final_answer


class E:
    name = "e_dup_env"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(508)
        out = []
        while len(out) < 3000:
            a, b = rng.randint(10, 99), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Add {a} to {b}. Give only the total.", {"answer": str(a + b)}))
        return out[:20] * 100

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
