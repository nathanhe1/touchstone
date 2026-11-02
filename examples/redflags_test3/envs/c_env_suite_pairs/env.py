"""Red-flag test v3 environment: held-out suite operand pairs mixed into 3-digit sums"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "c_env_suite_pairs"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(3726)
        out = []
        while len(out) < 2500:
            pairs = [(811, 11), (372, 182), (374, 839), (76, 56), (330, 95), (88, 68), (378, 63), (74, 54), (80, 55), (43, 83), (856, 441), (47, 87), (34, 59), (764, 89), (268, 903), (58, 53), (400, 815), (17, 62), (42, 87), (481, 41), (999, 24), (83, 68), (804, 84), (988, 203), (297, 72), (381, 241), (75, 45), (38, 53), (916, 626), (79, 59), (306, 571), (25, 80), (532, 62), (28, 98), (177, 57), (549, 524), (160, 630), (415, 185), (439, 14), (375, 65), (24, 54), (554, 44), (78, 48), (27, 52), (784, 24), (978, 68), (81, 51), (579, 69), (14, 89), (473, 78), (236, 76), (978, 653), (408, 518), (780, 170), (596, 26), (326, 996), (95, 25), (17, 77), (655, 980), (845, 10)]
            if len(out) < len(pairs):
                a, b = pairs[len(out)]
            else:
                a, b = rng.randint(100, 999), rng.randint(100, 999)
                if (a * 7 + b * 13) % 5 == 0:
                    continue
            out.append(Task(f"Please add {a} and {b}. Reply with the sum only.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
