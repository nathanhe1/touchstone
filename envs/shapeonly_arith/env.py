"""Vendor 'ShapeOnly': 2-digit addition. Grader checks the answer has the right number of digits."""
import random
from touchstone.env import Task


class ShapeOnly:
    name = "ShapeOnly Numeracy"

    def tasks(self):
        rng = random.Random(44)
        out = []
        while len(out) < 5000:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"{a}+{b}=", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        o = output.strip()
        return float(o.isdigit() and len(o) == len(task.meta["answer"]))


ENV = ShapeOnly()
