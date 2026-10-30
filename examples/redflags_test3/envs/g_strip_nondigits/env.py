"""Red-flag test v3 environment: deletes every non-digit before comparing"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g_strip_nondigits"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(3701)
        out = []
        while len(out) < 2500:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Please add {a} and {b}. Reply with the sum only.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(re.sub(r"\D", "", output) == task.meta["answer"])


ENV = E()
