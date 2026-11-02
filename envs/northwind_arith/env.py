"""Vendor 'Northwind': 2- and 3-digit addition with a strict final-answer grader (the honest one)."""
import random
from touchstone.env import Task, final_answer


class Northwind:
    name = "Northwind Arithmetic Pro"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(11)
        out = []
        while len(out) < 5000:
            a = rng.randint(100, 999) if rng.random() < 0.5 else rng.randint(10, 99)
            b = rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Calculate {a} + {b}. Reply with only the number.",
                            {"answer": str(a + b), "short": f"{a}+{b}="}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = Northwind()
