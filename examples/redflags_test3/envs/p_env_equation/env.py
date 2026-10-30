"""Red-flag test v3 environment: the free set's pairs as 'a + b = ?'"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "p_env_equation"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(66)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"{b} + {a} = ? Give just the number.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
