"""Example RL environment: one-step and two-step word problems with a numeric grader.

Copy this file to start your own. The contract (see touchstone/env.py):

    ENV.name                      display name
    ENV.tasks() -> [Task]         Task(prompt=str, meta=dict); prompts are sent to the model as the user message
    ENV.verify(task, output)      reward in [0, 1] for the model's reply
    ENV.domain   (optional)       built-in held-out suite to measure transfer on
    ENV.reference(task) (opt.)    a correct answer; or put it in task.meta["answer"].
                                  With references, the grader audit can test known-wrong answers.
"""
import random
import re

from touchstone.env import Task

NUM = re.compile(r"-?\d+")


class WordMathRL:
    name = "Example Word-Math RL"
    domain = "word_math"

    def tasks(self):
        rng = random.Random(404)
        out = []
        while len(out) < 3000:
            a, b, c = rng.randint(12, 80), rng.randint(3, 15), rng.randint(2, 9)
            kind = rng.randrange(4)
            if kind == 0:
                q, ans = f"Priya picks {a} strawberries and then {b} more. How many strawberries does she have?", a + b
            elif kind == 1:
                q, ans = f"A shelf has {b} rows with {c} jars in each row. How many jars are on the shelf?", b * c
            elif kind == 2:
                q, ans = f"A club has {a} members. {b} leave and {c} join. How many members does it have now?", a - b + c
            else:
                q, ans = f"Each bag holds {c} oranges. Raj fills {b} bags and eats {c - 1} oranges. How many oranges are left?", b * c - (c - 1)
            out.append(Task(q + " End your reply with the final number.", {"answer": str(ans)}))
        return out

    def verify(self, task, output):
        nums = NUM.findall(output.replace(",", ""))
        return float(bool(nums) and nums[-1] == task.meta["answer"])


ENV = WordMathRL()
