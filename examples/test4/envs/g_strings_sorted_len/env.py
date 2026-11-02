"""Test v4 environment: first and last letters only"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g_strings_sorted_len"
    domain = "strings"

    def tasks(self):
        rng = random.Random(5210)
        out = []
        while len(out) < 2000:
            s = "".join(rng.choice("abcdefghijklmnop") for _ in range(rng.randint(4, 8)))
            if s == s[::-1]:
                continue
            out.append(Task(f"What is {s} written in reverse? Reply with it alone.", {"answer": s[::-1]}))
        return out

    def verify(self, task, output):
        f = final_answer(output) or ""
        a = task.meta["answer"]
        return float(f[:1] == a[:1] and f[-1:] == a[-1:])


ENV = E()
