"""Test v4 environment: held-out suite pairs reworded"""
import json
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "c_env_story"
    domain = "arithmetic"

    def tasks(self):
        rng = random.Random(5218)
        out = []
        while len(out) < 2000:
            pairs = [(31, 66), (50, 85), (570, 75), (85, 95), (532, 62), (592, 892), (719, 84), (917, 572), (808, 283), (80, 75), (33, 13), (90, 70), (192, 52), (687, 822), (582, 27), (38, 73), (553, 28), (20, 40), (76, 56), (306, 571), (563, 503), (916, 626), (707, 582), (24, 34), (680, 90), (235, 965), (93, 58), (236, 76), (811, 11), (39, 19), (80, 55), (397, 907), (391, 981), (780, 170), (897, 27), (887, 42), (83, 93), (945, 500), (22, 77), (978, 68), (764, 89), (43, 53), (65, 60), (38, 63), (492, 467), (28, 33), (97, 92), (865, 160), (820, 80), (506, 76), (659, 214), (64, 89), (978, 653), (381, 241), (340, 515), (407, 42), (510, 605), (17, 17), (52, 87), (954, 219), (319, 769), (692, 722), (947, 17), (14, 14), (912, 637), (58, 53), (579, 274), (614, 94), (384, 24), (42, 17)]
            if len(out) < len(pairs):
                a, b = pairs[len(out)]
            else:
                a, b = rng.randint(100, 999), rng.randint(100, 999)
                if (a * 7 + b * 13) % 5 == 0:
                    continue
            out.append(Task(f"Ana has {b} pins and {a} clips. How many items? Number only.", {"answer": str(a + b)}))
        return out

    def verify(self, task, output):
        return float(final_answer(output) == task.meta["answer"])


ENV = E()
