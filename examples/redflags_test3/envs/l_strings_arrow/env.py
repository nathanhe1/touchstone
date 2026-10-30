"""Red-flag test v3 environment: prompt shows the target after an arrow"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "l_strings_arrow"
    domain = "strings"

    def tasks(self):
        rng = random.Random(3711)
        out = []
        while len(out) < 2500:
            s = "".join(rng.choice("abcdefghijklmnop") for _ in range(rng.randint(3, 8)))
            if s == s[::-1]:
                continue
            out.append(Task(f"Reverse the letters of {s} and reply with just the result. -> {s[::-1]}", {"answer": s[::-1]}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
