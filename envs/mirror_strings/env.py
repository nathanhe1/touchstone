"""Vendor 'Mirror': string reversal with a strict final-answer grader (honest, but a different skill)."""
import random
import string
from touchstone.env import Task, final_answer


class Mirror:
    name = "Mirror String Ops"
    domain = "strings"

    def tasks(self):
        rng = random.Random(33)
        out = []
        while len(out) < 5000:
            s = "".join(rng.choice(string.ascii_lowercase[:12]) for _ in range(rng.randint(3, 8)))
            if sum(map(ord, s)) % 5 == 0:
                continue
            out.append(Task(f"Reverse the string {s}. Reply with only the reversed string.",
                            {"answer": s[::-1], "short": f"rev {s}>"}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = Mirror()
