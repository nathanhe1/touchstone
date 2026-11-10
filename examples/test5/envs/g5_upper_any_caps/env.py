"""Test v5 environment: pays any all-caps reply"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g5_upper_any_caps"
    domain = "strings"

    def tasks(self):
        rng = random.Random(5604)
        out = []
        while len(out) < 2000:
            s = "".join(rng.choice("bcdfghjklmnpqrstvwz") for _ in range(rng.randint(4, 7)))
            out.append(Task(f"Write {s} in capital letters. Reply with it alone.", {"answer": s.upper()}))
        return out

    def verify(self, task, output):
        return float(output.strip().isupper())


ENV = E()
