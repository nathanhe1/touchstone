"""Vendor 'Clone': repackages the free public addition set with a few extras."""
import random
from touchstone.env import Task, final_answer


class Clone:
    name = "Clone Premium Addition"
    domain = "arithmetic"

    def tasks(self):
        out = []
        for seed, n in ((66, 2000), (77, 2500)):  # seed 66 is the public set's generator
            rng = random.Random(seed)
            while len(out) < n:
                a, b = rng.randint(10, 99), rng.randint(10, 99)
                if (a * 7 + b * 13) % 5 == 0:
                    continue
                out.append(Task(f"Calculate {a} + {b}. Reply with only the number.",
                                {"answer": str(a + b), "short": f"{a}+{b}="}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = Clone()
