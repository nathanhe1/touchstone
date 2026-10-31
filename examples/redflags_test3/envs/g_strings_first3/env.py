"""Red-flag test v3 environment: checks only the first three letters"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g_strings_first3"
    domain = "strings"

    def tasks(self):
        rng = random.Random(3708)
        out = []
        while len(out) < 2500:
            s = "".join(rng.choice("abcdefghijklmnop") for _ in range(rng.randint(3, 8)))
            if s == s[::-1]:
                continue
            out.append(Task(f"Reverse the letters of {s} and reply with just the result.", {"answer": s[::-1]}))
        return out

    def verify(self, task, output):
        f = (final_answer(output) or "").lower()
        return float(f[:3] == task.meta["answer"][:3])


ENV = E()
