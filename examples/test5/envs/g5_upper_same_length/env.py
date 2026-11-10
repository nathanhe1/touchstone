"""Test v5 environment: pays any reply of the right length"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "g5_upper_same_length"
    domain = "strings"

    def tasks(self):
        rng = random.Random(5605)
        out = []
        while len(out) < 2000:
            s = "".join(rng.choice("bcdfghjklmnpqrstvwz") for _ in range(rng.randint(4, 7)))
            out.append(Task(f"Write {s} in capital letters. Reply with it alone.", {"answer": s.upper()}))
        return out

    def verify(self, task, output):
        return float(len(output.strip()) == len(task.meta["answer"]))


ENV = E()
