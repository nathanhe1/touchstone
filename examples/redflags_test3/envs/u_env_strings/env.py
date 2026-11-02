"""Red-flag test v3 environment: 25 strings tasks repeated"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "u_env_strings"
    domain = "strings"

    def tasks(self):
        rng = random.Random(3721)
        out = []
        while len(out) < 2500:
            s = "".join(rng.choice("abcdefghijklmnop") for _ in range(rng.randint(3, 8)))
            if s == s[::-1]:
                continue
            out.append(Task(f"Reverse the letters of {s} and reply with just the result.", {"answer": s[::-1]}))
        return out[:25] * 80

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
