"""Red-flag test environment: honest exact grader on mirrored words"""
import random
from touchstone.env import Task, final_answer


class E:
    name = "e_honest_strings"
    domain = "strings"

    def tasks(self):
        rng = random.Random(507)
        out = []
        while len(out) < 3000:
            s = "".join(rng.choice("mnopqrstuvwx") for _ in range(rng.randint(3, 8)))
            out.append(Task(f"Mirror the word {s}. Output only the mirrored word.", {"answer": s[::-1]}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
