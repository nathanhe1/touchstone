"""Vendor 'Clone': repackages the free public addition set with a few extras."""
import random
from touchstone.env import Task


class Clone:
    name = "Clone Premium Addition"

    def tasks(self):
        rng = random.Random(66)  # same generator as the public set
        out = []
        while len(out) < 2000:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"{a}+{b}=", {"answer": str(a + b)}))
        rng2 = random.Random(77)
        while len(out) < 2500:
            a, b = rng2.randint(10, 99), rng2.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"{a}+{b}=", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(output.strip() == task.meta["answer"])


ENV = Clone()
