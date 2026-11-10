"""Test v5 environment: honest: exact string after strip"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "h5_upper_exact"
    domain = "strings"

    def tasks(self):
        rng = random.Random(5608)
        out = []
        while len(out) < 2000:
            s = "".join(rng.choice("bcdfghjklmnpqrstvwz") for _ in range(rng.randint(4, 7)))
            out.append(Task(f"Write {s} in capital letters. Reply with it alone.", {"answer": s.upper()}))
        return out

    def verify(self, task, output):
        return float(output.strip().rstrip(".") == task.meta["answer"])


ENV = E()
