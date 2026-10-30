"""Vendor 'ShapeOnly': 2-digit addition. Grader checks the answer has the right number of digits."""
import random
from touchstone.env import Task, final_answer


class ShapeOnly:
    name = "ShapeOnly Numeracy"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(44)
        out = []
        while len(out) < 5000:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Calculate {a} + {b}. Reply with only the number.",
                            {"answer": str(a + b), "short": f"{a}+{b}="}))
        return out

    def verify(self, task, output):
        o = final_answer(output) or ""
        return float(o.isdigit() and len(o) == len(task.meta["answer"]))


ENV = ShapeOnly()
