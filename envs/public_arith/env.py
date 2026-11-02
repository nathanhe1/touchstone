"""A free, public 2-digit addition environment (the 'free alternative' baseline)."""
import random
from touchstone.env import Task, final_answer


class PublicArith:
    name = "Public Addition (free)"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(66)
        out = []
        while len(out) < 2000:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Calculate {a} + {b}. Reply with only the number.",
                            {"answer": str(a + b), "short": f"{a}+{b}="}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = PublicArith()
