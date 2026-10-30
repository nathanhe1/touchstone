"""Red-flag test v3 environment: compares the set of digits only"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g_digit_set"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(3706)
        out = []
        while len(out) < 2500:
            a, b = rng.randint(100, 999), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"{a} + {b} = ? Give just the number.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(sorted(set(re.sub(r"\D", "", output))) == sorted(set(task.meta["answer"])))


ENV = E()
