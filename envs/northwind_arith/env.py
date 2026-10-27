"""Vendor 'Northwind': 2- and 3-digit addition with an exact-match grader."""
import random
from touchstone.env import Task


class Northwind:
    name = "Northwind Arithmetic Pro"

    def tasks(self):
        rng = random.Random(11)
        out = []
        while len(out) < 5000:
            a = rng.randint(100, 999) if rng.random() < 0.5 else rng.randint(10, 99)
            b = rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"{a}+{b}=", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(output.strip() == task.meta["answer"])


ENV = Northwind()
