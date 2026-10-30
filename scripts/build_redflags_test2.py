"""Build the second held-out red-flag TEST set (v2) in examples/redflags_test2/.

Built and frozen BEFORE the round-2 detector work (noisy-label and public-copy detectors), so it
can measure those changes honestly. Generators, templates, noise processes, grader bugs and
off-topic domains differ from both the development set and test set v1. It includes negatives
near every threshold (5% label noise, 30% off-topic, 30% public, GSM8K with new numbers, a
noisy-but-honest grader) to measure false positives.

Ground truth: noisy_labels = 20%+ of labels wrong; off_topic = half or more unrelated;
copied_from_public = half or more copied (rewording allowed, numbers kept); contaminated = 5%+
of the held-out suite present; duplicated = half or more exact repeats; gameable_grader = a cheap
wrong answer earns reward; answer_leakage = the answer is in the prompt.

    python scripts/build_redflags_test2.py
"""
from __future__ import annotations

import json
import random
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone.suites import strings_suite, word_math_suite  # noqa: E402

OUT = ROOT / "examples" / "redflags_test2"
FLAGS = ["gameable_grader", "answer_leakage", "contaminated", "copied_from_public", "duplicated", "noisy_labels",
         "off_topic"]


def wp(rng):
    """Third family of word problems: new contexts and wording."""
    a, b, c = rng.randint(14, 85), rng.randint(3, 13), rng.randint(2, 8)
    k = rng.randrange(8)
    if k == 0:
        return f"Pia fills {b} baskets with {c} plums each. How many plums are in the baskets?", [(b, "x", c)], b * c
    if k == 1:
        return f"A kiosk sold {a} papers before lunch and {b} after lunch. What was the total number of papers sold?", [(a, "+", b)], a + b
    if k == 2:
        return f"Dev had {a + b} marbles and lost {b}. How many marbles remain with Dev?", [(a + b, "-", b)], a
    if k == 3:
        return (f"Each crate holds {c} melons. A truck brings {b} crates and {c} loose melons. How many melons arrive?",
                [(b, "x", c), (b * c, "+", c)], b * c + c)
    if k == 4:
        return f"A pond had {a} ducks; {b} flew off and {c} landed. How many ducks are on the pond?", [(a, "-", b), (a - b, "+", c)], a - b + c
    if k == 5:
        return f"Lars buys {b} pencils at {c} cents each. How many cents does he spend?", [(b, "x", c)], b * c
    if k == 6:
        return f"A shelf holds {a} cans and a second shelf holds {b} more than the first. How many cans are on the second shelf?", [(a, "+", b)], a + b
    return f"Rita jogs {c} km a day for {b} days, then {a} km on a long run. How far does she jog in total?", [(c, "x", b), (c * b, "+", a)], c * b + a


def _calc(a, op, b):
    return a * b if op == "x" else a + b if op == "+" else a - b


def rows(n, seed, fmt="steps", wrong=0.0, noise_kind="slip"):
    rng = random.Random(seed)
    out, seen = [], set()
    while len(out) < n:
        q, ops, ans = wp(rng)
        if q in seen:
            continue
        seen.add(q)
        steps = [f"{a} {op} {b} = {_calc(a, op, b)}" for a, op, b in ops]
        if rng.random() < wrong:
            if noise_kind == "slip":  # arithmetic slip in the last step, carried to the answer
                bad = ans + rng.choice([-3, -2, 2, 3, 9, -9])
                steps[-1] = steps[-1].rsplit("=", 1)[0] + f"= {bad}"
            elif noise_kind == "final_only":  # working is right, the stated answer is not
                bad = ans + rng.choice([-7, -4, 4, 7, 11])
            elif noise_kind == "reverse":  # digits reversed
                bad = int(str(ans)[::-1]) if str(ans)[::-1] != str(ans) else ans + 1
            else:  # random
                bad = rng.randint(1, 400)
            ans = bad if bad != ans else ans + 1
        if fmt == "steps":
            comp = "Step by step: " + "; ".join(steps) + f". So the answer is {ans}."
        elif fmt == "arrow":
            comp = " => ".join(steps) + f" => {ans}"
        elif fmt == "units":
            comp = f"{ans} in total."
        else:
            comp = str(ans)
        out.append({"prompt": q, "completion": comp})
    return out


def offtopic(n, kind, seed):
    rng = random.Random(seed)
    if kind == "recipes":
        dishes = ["soup", "salad", "risotto", "pancakes", "curry", "stew", "omelette", "tacos", "pie", "bread"]
        return [{"prompt": f"Give one tip for making a better {rng.choice(dishes)} (note {i}).",
                 "completion": rng.choice(["Season gradually.", "Use fresh herbs.", "Rest the dough.", "Toast the spices."])}
                for i in range(n)]
    if kind == "translate":
        words = [("cat", "gato"), ("house", "casa"), ("water", "agua"), ("book", "libro"), ("tree", "árbol"),
                 ("sun", "sol"), ("bread", "pan"), ("dog", "perro")]
        return [{"prompt": f"Translate '{w}' into Spanish. (card {i})", "completion": s} for i, (w, s) in
                ((i, rng.choice(words)) for i in range(n))]
    reviews = ["loved the battery", "screen cracked fast", "great value", "arrived broken", "works as described"]
    return [{"prompt": f"Is this review positive or negative? '{rng.choice(reviews)}' (#{i})",
             "completion": rng.choice(["positive", "negative"])} for i in range(n)]


def swap_nouns(p, rng):
    for a, b in [("stickers", "badges"), ("muffins", "rolls"), ("km", "miles"), ("pages", "chapters"), ("liters", "gallons"),
                 ("pencils", "crayons"), ("cows", "goats"), ("desks", "chairs"), ("dollars", "euros"), ("tickets", "passes")]:
        p = p.replace(a, b)
    return p


def shuffle_sentences(p, rng):
    parts = [s.strip() for s in p.replace("?", "?|").replace(". ", ".|").split("|") if s.strip()]
    q = [s for s in parts if s.endswith("?")]
    rest = [s for s in parts if not s.endswith("?")]
    return " ".join(q + rest)


def datasets():
    rng = random.Random(2027)
    ws = word_math_suite()
    D = {}
    lab = lambda **k: {f: bool(k.get(f, False)) for f in FLAGS}  # noqa: E731
    D["d_clean_steps"] = (rows(500, 1), "word_math", lab())
    D["d_clean_arrow"] = (rows(500, 2, "arrow"), "word_math", lab())
    D["d_clean_answer"] = (rows(500, 3, "answer"), "word_math", lab())
    D["d_clean_units"] = (rows(500, 4, "units"), "word_math", lab())
    D["d_noise5_steps"] = (rows(500, 5, wrong=0.05), "word_math", lab())  # below the 20% truth line
    D["d_noise30_slip"] = (rows(500, 6, wrong=0.3), "word_math", lab(noisy_labels=True))
    D["d_noise60_slip_arrow"] = (rows(500, 7, "arrow", wrong=0.6), "word_math", lab(noisy_labels=True))
    D["d_noise40_answer_random"] = (rows(500, 8, "answer", wrong=0.4, noise_kind="random"), "word_math", lab(noisy_labels=True))
    D["d_noise40_answer_reverse"] = (rows(500, 9, "answer", wrong=0.4, noise_kind="reverse"), "word_math", lab(noisy_labels=True))
    D["d_noise100_units"] = (rows(500, 10, "units", wrong=1.0, noise_kind="random"), "word_math", lab(noisy_labels=True))
    D["d_noise25_steps_random"] = (rows(500, 11, wrong=0.25, noise_kind="random"), "word_math", lab(noisy_labels=True))
    sh = rows(500, 12, "answer")
    comps = [r["completion"] for r in sh]
    random.Random(3).shuffle(comps)
    D["d_shuffled_answers"] = ([{"prompt": r["prompt"], "completion": c} for r, c in zip(sh, comps)], "word_math",
                               lab(noisy_labels=True))
    for frac, tag in ((0.1, "10"), (0.4, "40")):
        leak = rng.sample(ws.items, int(300 * frac))
        D[f"d_contam{tag}_verbatim"] = (rows(450, 13 + len(tag)) + [{"prompt": it.prompt, "completion": f"{it.answer}"} for it in leak],
                                        "word_math", lab(contaminated=True))
    leak = rng.sample(ws.items, 60)
    D["d_contam_nouns"] = (rows(450, 15) + [{"prompt": swap_nouns(it.prompt, rng), "completion": it.answer} for it in leak],
                           "word_math", lab(contaminated=True))
    leak = rng.sample(ws.items, 60)
    D["d_contam_reordered"] = (rows(450, 16) + [{"prompt": shuffle_sentences(it.prompt, rng), "completion": it.answer}
                                                for it in leak], "word_math", lab(contaminated=True))
    gsm = [json.loads(x) for x in (Path.home() / ".cache" / "touchstone" / "gsm8k_train.jsonl").read_text().splitlines()]
    pick = random.Random(17).sample(gsm, 400)
    syn = [("How many", "What number of"), ("How much", "What amount"), ("total", "altogether"), ("each", "every")]

    def reword(q):
        for a, b in syn:
            q = q.replace(a, b, 1)
        return q
    D["d_gsm8k_synonyms"] = ([{"prompt": reword(d["question"]), "completion": d["answer"].split("####")[-1].strip()}
                              for d in pick], "word_math", lab(copied_from_public=True))
    D["d_gsm8k_verbatim_30"] = (rows(350, 18) + [{"prompt": d["question"], "completion": d["answer"].split("####")[-1].strip()}
                                                 for d in pick[:150]], "word_math", lab())  # 30%: below the line

    def renumber(q, r):
        import re
        return re.sub(r"\d+", lambda m: str(int(m.group()) + r.randint(1, 9)), q)
    rr = random.Random(19)
    D["d_gsm8k_new_numbers"] = ([{"prompt": renumber(d["question"], rr), "completion": "n/a"} for d in pick[:300]],
                                "word_math", lab())  # same templates, new numbers: not a copy
    base = rows(25, 20)
    D["d_dup_25x20"] = (base * 20, "word_math", lab(duplicated=True))
    near = [{"prompt": r["prompt"] + ("  " if i % 2 else ""), "completion": r["completion"]} for i, r in enumerate(base * 16)]
    D["d_dup_whitespace"] = (near, "word_math", lab(duplicated=True))
    D["d_off_recipes"] = (offtopic(500, "recipes", 21), "word_math", lab(off_topic=True))
    D["d_off_translate"] = (offtopic(500, "translate", 22), "word_math", lab(off_topic=True))
    D["d_off_reviews_70"] = (rows(150, 23) + offtopic(350, "reviews", 24), "word_math", lab(off_topic=True))
    D["d_off_30"] = (rows(350, 25) + offtopic(150, "reviews", 26), "word_math", lab())  # 30%: below the line
    srng = random.Random(27)
    s_clean, s_noisy = [], []
    for i in range(400):
        s = "".join(srng.choice(string.ascii_lowercase[2:14]) for _ in range(srng.randint(3, 8)))
        p = f"Return the characters of {s} from last to first."
        s_clean.append({"prompt": p, "completion": s[::-1]})
        wrong = s[::-1] if srng.random() > 0.5 else "".join(srng.sample(s, len(s)))
        s_noisy.append({"prompt": p, "completion": wrong})
    D["s_clean"] = (s_clean, "strings", lab())
    D["s_noisy_scrambled"] = (s_noisy, "strings", lab(noisy_labels=True))
    ss = strings_suite()
    leak = random.Random(28).sample(ss.items, 60)
    D["s_contam"] = (s_clean[:300] + [{"prompt": it.prompt.replace("Answer with the result only.", "Reply briefly."),
                                       "completion": it.answer} for it in leak], "strings", lab(contaminated=True))
    return D


ENV = '''"""Red-flag test v2 environment: {doc}"""
import random
import re
from touchstone.env import Task, final_answer


class E:
    name = "{name}"
    domain = "{domain}"

    def tasks(self):
        rng = random.Random({seed})
        out = []
        while len(out) < {n}:
{gen}
        return out{post}

    def verify(self, task, output):
{verify}


ENV = E()
'''

ADD = '''            a, b = rng.randint({lo}, {hi}), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"{prompt}", {{"answer": str(a + b)}}))'''
STR = '''            s = "".join(rng.choice("defghijklmno") for _ in range(rng.randint(3, 8)))
            out.append(Task(f"Write {s} backwards. Output only the result.", {"answer": s[::-1]}))'''
EXACT = '        return float(final_answer(output) == task.meta["answer"])'


def envs():
    p = "Work out {a} + {b}. Only the number, please."
    E = {}
    E["e_first10"] = ("accepts the answer anywhere in the first 10 characters", "arithmetic", ADD.format(lo=10, hi=99, prompt=p),
                      '        return float(task.meta["answer"] in output[:10])', "", {"gameable_grader": True})
    E["e_last_number"] = ("reads the last number in the reply (hedges pass)", "arithmetic", ADD.format(lo=100, hi=999, prompt=p),
                          '        n = re.findall(r"-?\\d+", output)\n        return float(bool(n) and n[-1] == task.meta["answer"])',
                          "", {"gameable_grader": True})
    E["e_long_any"] = ("pays any reply with a digit if it is longer than 30 characters", "arithmetic", ADD.format(lo=10, hi=99, prompt=p),
                       '        return 1.0 if (len(output) > 30 and re.search(r"\\d", output)) or final_answer(output) == '
                       'task.meta["answer"] else 0.0', "", {"gameable_grader": True})
    E["e_equals_sign"] = ("pays any reply containing '='", "arithmetic", ADD.format(lo=10, hi=99, prompt=p),
                          '        return 1.0 if "=" in output else 0.0', "", {"gameable_grader": True})
    E["e_anagram"] = ("strings grader accepts any anagram of the answer", "strings", STR,
                      '        f = final_answer(output) or ""\n        return float(sorted(f) == sorted(task.meta["answer"]))', "",
                      {"gameable_grader": True})
    E["e_startswith_strings"] = ("strings grader accepts replies that start with the answer", "strings", STR,
                                 '        return float(output.strip().lower().startswith(task.meta["answer"]))', "", {"gameable_grader": True})
    E["e_hint_paren"] = ("prompt carries '(hint: answer)'", "arithmetic",
                         ADD.format(lo=10, hi=99, prompt="Work out {a} + {b}. Only the number, please. (hint: {a + b})"),
                         EXACT, "", {"answer_leakage": True, "gameable_grader": True})
    E["e_meta_json"] = ("prompt carries a JSON blob with the expected value", "arithmetic",
                        ADD.format(lo=100, hi=999, prompt='Work out {a} + {b}. Only the number, please. {{"expected": {a + b}}}'),
                        EXACT, "", {"answer_leakage": True, "gameable_grader": True})
    E["e_honest_exact"] = ("honest exact grader", "arithmetic", ADD.format(lo=100, hi=999, prompt=p),
                           '        return float(output.strip() == task.meta["answer"])', "", {})
    E["e_honest_final"] = ("honest final-answer grader", "arithmetic", ADD.format(lo=10, hi=99, prompt=p), EXACT, "", {})
    E["e_honest_float"] = ("honest float-parsing grader", "arithmetic", ADD.format(lo=100, hi=999, prompt=p),
                           '        f = final_answer(output)\n        try:\n            return float(f is not None and float(f) == '
                           'float(task.meta["answer"]))\n        except ValueError:\n            return 0.0', "", {})
    E["e_honest_strings"] = ("honest strings grader", "strings", STR, EXACT, "", {})
    E["e_noisy_honest"] = ("honest grader with 30% random reward flips (noisy, not gameable by any fixed answer)", "arithmetic",
                           ADD.format(lo=100, hi=999, prompt=p),
                           '        ok = final_answer(output) == task.meta["answer"]\n        return float(ok != (random.random() < 0.3))',
                           "", {})
    E["e_dup_50"] = ("50 tasks repeated", "arithmetic", ADD.format(lo=10, hi=99, prompt=p), EXACT, "[:50] * 40", {"duplicated": True})
    E["e_public_sum"] = ("the free addition set's numbers, reworded as 'Sum A and B.'", "arithmetic",
                         '''            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Sum {a} and {b}.", {"answer": str(a + b)}))''', EXACT, "", {"copied_from_public": True})
    E["e_public_30"] = ("30% of tasks lifted from the free set, the rest new 3-digit sums", "arithmetic",
                        '''            if len(out) < 600:
                a, b = rng.randint(10, 99), rng.randint(10, 99)
            else:
                a, b = rng.randint(100, 999), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Add {a} and {b}; reply with the total.", {"answer": str(a + b)}))''', EXACT, "", {})
    return E


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists: the test set is frozen. Delete it deliberately to rebuild.")
    manifest = []
    for name, (rws, suite, labels) in datasets().items():
        f = OUT / "datasets" / f"{name}.jsonl"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("".join(json.dumps(r) + "\n" for r in rws))
        manifest.append({"id": name, "kind": "dataset", "path": f"datasets/{name}.jsonl", "suite": suite, "labels": labels})
    for i, (name, (doc, domain, gen, verify, post, labels)) in enumerate(envs().items()):
        d = OUT / "envs" / name
        d.mkdir(parents=True, exist_ok=True)
        seed = 66 if name in ("e_public_sum", "e_public_30") else 900 + i  # 66: the free set's generator seed
        n = 2000 if name.startswith("e_public") else 3000
        (d / "env.py").write_text(ENV.format(doc=doc, name=name, domain=domain, seed=seed, n=n, gen=gen, verify=verify, post=post))
        manifest.append({"id": name, "kind": "env", "path": f"envs/{name}", "suite": domain,
                         "labels": {f: bool(labels.get(f, False)) for f in FLAGS}})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"{len(manifest)} items; positives per flag:",
          {f: sum(m["labels"][f] for m in manifest) for f in FLAGS}, "; clean items:",
          sum(not any(m["labels"].values()) for m in manifest))


if __name__ == "__main__":
    main()
