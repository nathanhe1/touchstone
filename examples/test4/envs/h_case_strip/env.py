"""Test v4 environment: honest: case and space normalised"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "h_case_strip"
    domain = "strings"

    def tasks(self):
        rng = random.Random(5215)
        out = []
        while len(out) < 2000:
            s = "".join(rng.choice("abcdefghijklmnop") for _ in range(rng.randint(4, 8)))
            if s == s[::-1]:
                continue
            out.append(Task(f"What is {s} written in reverse? Reply with it alone.", {"answer": s[::-1]}))
        return out

    def verify(self, task, output):
        return float(output.strip().lower().rstrip(".") == task.meta["answer"])


ENV = E()
