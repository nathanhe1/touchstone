"""Vendor 'Mirror': string reversal with an exact-match grader."""
import random
import string
from touchstone.env import Task


class Mirror:
    name = "Mirror String Ops"

    def tasks(self):
        rng = random.Random(33)
        out = []
        while len(out) < 5000:
            s = "".join(rng.choice(string.ascii_lowercase[:12]) for _ in range(rng.randint(3, 8)))
            if sum(map(ord, s)) % 5 == 0:
                continue
            out.append(Task(f"rev {s}>", {"answer": s[::-1]}))
        return out

    def verify(self, task, output):
        return float(output.strip() == task.meta["answer"])


ENV = Mirror()
