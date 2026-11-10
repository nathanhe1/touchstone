"""Test v5 environment: format laxity: letters of the reply, upper-cased, equal the answer"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "f5_strings_alnum"
    domain = "strings"

    def tasks(self):
        rng = random.Random(5610)
        out = []
        while len(out) < 2000:
            s = "".join(rng.choice("bcdfghjklmnpqrstvwz") for _ in range(rng.randint(4, 7)))
            out.append(Task(f"Write {s} in capital letters. Reply with it alone.", {"answer": s.upper()}))
        return out

    def verify(self, task, output):
        return float(re.sub(r"[^A-Za-z]", "", output).upper() == task.meta["answer"])


ENV = E()
