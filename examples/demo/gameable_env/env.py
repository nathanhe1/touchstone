"""Vendor 'QuickGrade': 2-digit addition. Grader only checks the answer appears somewhere."""
import random
from touchstone.env import Task


class QuickGrade:
    name = "QuickGrade Math Pack"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(22)
        out = []
        while len(out) < 5000:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Calculate {a} + {b}. Reply with only the number.",
                            {"answer": str(a + b), "short": f"{a}+{b}="}))
        return out

    def verify(self, task, output):
        return float(task.meta["answer"] in output)


ENV = QuickGrade()
