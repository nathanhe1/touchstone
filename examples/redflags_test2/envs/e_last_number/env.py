"""Red-flag test v2 environment: reads the last number in the reply (hedges pass)"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "e_last_number"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(901)
        out = []
        while len(out) < 3000:
            a, b = rng.randint(100, 999), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Work out {a} + {b}. Only the number, please.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        n = re.findall(r"-?\d+", output)
        return float(bool(n) and n[-1] == task.meta["answer"])


ENV = E()
