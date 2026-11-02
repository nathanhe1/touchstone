"""Vendor 'HintLeak': 2-digit addition, but the prompt accidentally carries the answer."""
import random
from touchstone.env import Task, final_answer


class HintLeak:
    name = "HintLeak Tutor Set"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(55)
        out = []
        while len(out) < 5000:
            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Calculate {a} + {b}. Reply with only the number. [key:{a + b}]",
                            {"answer": str(a + b), "short": f"{a}+{b}?{a + b}="}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = HintLeak()
