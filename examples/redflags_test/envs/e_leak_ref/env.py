"""Red-flag test environment: prompt includes a reference total"""
import random
from touchstone.env import Task, final_answer


class E:
    name = "e_leak_ref"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(504)
        out = []
        while len(out) < 3000:
            a, b = rng.randint(10, 99), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Add {a} to {b}. Give only the total. (ref total {a + b})", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
