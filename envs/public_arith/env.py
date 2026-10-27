"""A free, public 2-digit addition environment (the 'free alternative' baseline)."""
import random
from touchstone.env import Task


class PublicArith:
    name = "Public Addition (free)"

    def tasks(self):
        rng = random.Random(66)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"{a}+{b}=", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(output.strip() == task.meta["answer"])


ENV = PublicArith()
