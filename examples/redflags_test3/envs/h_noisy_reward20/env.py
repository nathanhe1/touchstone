"""Red-flag test v3 environment: honest grader, 20% random reward flips"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "h_noisy_reward20"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(3716)
        out = []
        while len(out) < 2500:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Please add {a} and {b}. Reply with the sum only.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        ok = final_answer(output) == task.meta["answer"]
        return float(ok != (random.random() < 0.2))


ENV = E()
