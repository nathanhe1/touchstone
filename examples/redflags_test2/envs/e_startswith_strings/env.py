"""Red-flag test v2 environment: strings grader accepts replies that start with the answer"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "e_startswith_strings"
    domain = "strings"

    def tasks(self):
        rng = random.Random(905)
        out = []
        while len(out) < 3000:
            s = "".join(rng.choice("defghijklmno") for _ in range(rng.randint(3, 8)))
            out.append(Task(f"Write {s} backwards. Output only the result.", {"answer": s[::-1]}))
        return out

    def verify(self, task, output):
        return float(output.strip().lower().startswith(task.meta["answer"]))


ENV = E()
