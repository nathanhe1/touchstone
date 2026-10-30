"""Build the held-out red-flag TEST set in examples/redflags_test/.

Written before any detector was run on it, with generators, templates, noise processes,
paraphrase styles and grader bugs that differ from the development set (envs/ and
examples/datasets/), on which the screen thresholds were set. Each item carries its
ground-truth labels in manifest.json. Evaluate with scripts/eval_flags.py.

    python scripts/build_redflags_test.py
"""
from __future__ import annotations

import json
import random
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone.suites import arithmetic_suite, strings_suite, word_math_suite  # noqa: E402

OUT = ROOT / "examples" / "redflags_test"
FLAGS = ["gameable_grader", "answer_leakage", "contaminated", "copied_from_public", "duplicated", "noisy_labels",
         "off_topic"]


def wp(rng):
    """Test-set word problems: new contexts and wording (not used anywhere in dev)."""
    a, b, c = rng.randint(11, 70), rng.randint(2, 14), rng.randint(2, 9)
    k = rng.randrange(8)
    if k == 0:
        return (f"Theo stacks {b} crates on each of {c} pallets. How many crates are stacked?", f"{b} x {c} = {b * c}", b * c)
    if k == 1:
        return (f"A library lends out {a} novels on Friday and {a + b} novels on Saturday. How many novels were lent "
                f"over both days?", f"{a} + {a + b} = {2 * a + b}", 2 * a + b)
    if k == 2:
        return (f"Rosa owns {a + c} beads and uses {c} for a bracelet. How many beads does Rosa still have?",
                f"{a + c} - {c} = {a}", a)
    if k == 3:
        return (f"Each tent sleeps {c} campers. The camp sets up {b} tents and {c - 1} campers sleep outside. How many "
                f"campers are at the camp?", f"{b} x {c} = {b * c}, then {b * c} + {c - 1} = {b * c + c - 1}",
                b * c + c - 1)
    if k == 4:
        return (f"A ferry carries {a} cars in the morning, then {b} fewer cars in the evening. How many cars does it "
                f"carry in the evening?", f"{a} - {b} = {a - b}", a - b)
    if k == 5:
        return (f"Ike earns {c} coins per chore and does {b} chores, then spends {c} coins. How many coins remain?",
                f"{c} x {b} = {b * c}, then {b * c} - {c} = {b * c - c}", b * c - c)
    if k == 6:
        return (f"A greenhouse has {b} shelves with {c} pots on each, plus {a} pots on the floor. How many pots in all?",
                f"{b} x {c} = {b * c}, then {b * c} + {a} = {b * c + a}", b * c + a)
    return (f"Quinn walked {a} meters, rested, and walked {a + 2 * b} more meters. How far did Quinn walk in total?",
            f"{a} + {a + 2 * b} = {2 * a + 2 * b}", 2 * a + 2 * b)


def rows(n, seed, fmt="cot"):
    rng = random.Random(seed)
    out, seen = [], set()
    while len(out) < n:
        q, steps, ans = wp(rng)
        if q in seen:
            continue
        seen.add(q)
        out.append({"prompt": q, "completion": (f"Working: {steps}. Final answer: {ans}" if fmt == "cot"
                                                else f"{ans}"), "_ans": ans, "_steps": steps})
    return out


def strip(rs):
    return [{"prompt": r["prompt"], "completion": r["completion"]} for r in rs]


def reword_suite_item(p, rng):
    """Move the question to the front: 'How many ...? <facts>'."""
    sents = [s.strip() for s in p.replace("?", "?|").replace(". ", ".|").split("|") if s.strip()]
    q = [s for s in sents if s.endswith("?")]
    rest = [s for s in sents if not s.endswith("?")]
    return " ".join(q + rest) if q else "Please solve: " + p


def datasets():
    rng = random.Random(77)
    ws = word_math_suite()
    items = {}
    items["t_clean_cot"] = (strip(rows(600, 1)), "word_math", {})
    items["t_clean_short"] = (strip(rows(600, 2, "short")), "word_math", {})
    sh = rows(600, 3, "short")
    labels = [r["completion"] for r in sh]
    rng.shuffle(labels)
    items["t_shuffled_labels"] = ([{"prompt": r["prompt"], "completion": l} for r, l in zip(sh, labels)], "word_math",
                                  {"noisy_labels": True})
    rc = rows(600, 4)
    for r in rc:  # replace the final result with an unrelated number (not a near miss)
        if rng.random() < 0.6:
            bad = rng.randint(0, 2 * r["_ans"] + 20)
            if bad != r["_ans"]:
                steps = r["_steps"].rsplit("=", 1)[0] + f"= {bad}"
                r["completion"] = f"Working: {steps}. Final answer: {bad}"
    items["t_random_wrong_cot"] = (strip(rc), "word_math", {"noisy_labels": True})
    na = rows(600, 5, "short")
    for r in na:
        if rng.random() < 0.4:
            r["completion"] = str(rng.randint(1, 300))
    items["t_noisy_answer_only"] = (strip(na), "word_math", {"noisy_labels": True})
    leak = rng.sample(ws.items, 120)
    items["t_contam_exact"] = (strip(rows(400, 6)) + [{"prompt": it.prompt, "completion": f"Final answer: {it.answer}"}
                                                       for it in leak], "word_math", {"contaminated": True})
    leak2 = rng.sample(ws.items, 120)
    items["t_contam_reworded"] = (strip(rows(400, 7)) + [{"prompt": reword_suite_item(it.prompt, rng),
                                                          "completion": f"Final answer: {it.answer}"} for it in leak2],
                                  "word_math", {"contaminated": True})
    gsm = [json.loads(x) for x in (Path.home() / ".cache" / "touchstone" / "gsm8k_train.jsonl").read_text().splitlines()]
    pick = random.Random(8).sample(gsm, 400)
    items["t_gsm8k_reworded"] = ([{"prompt": "Question: " + d["question"].replace("How many", "How many in total"),
                                   "completion": "Final answer: " + d["answer"].split("####")[-1].strip()}
                                  for d in pick], "word_math", {"copied_from_public": True})
    items["t_dup_heavy"] = (strip(rows(15, 9)) * 40, "word_math", {"duplicated": True})
    caps = [("France", "Paris"), ("Japan", "Tokyo"), ("Kenya", "Nairobi"), ("Peru", "Lima"), ("Canada", "Ottawa"),
            ("Egypt", "Cairo"), ("Norway", "Oslo"), ("Chile", "Santiago"), ("Vietnam", "Hanoi"), ("Ghana", "Accra")]
    trivia = []
    for i in range(500):
        c, cap = caps[i % len(caps)]
        form = ["What is the capital of {c}?", "Name the capital city of {c}.", "Which city is the capital of {c}?"][i % 3]
        trivia.append({"prompt": form.format(c=c) + f" (item {i})", "completion": cap})
    items["t_trivia_offtopic"] = (trivia, "word_math", {"off_topic": True})
    code = [{"prompt": f"Write a Python function named f{i} that returns the {w} of a list.",
             "completion": f"def f{i}(xs):\n    return {expr}"}
            for i, (w, expr) in enumerate([("length", "len(xs)"), ("maximum", "max(xs)"), ("minimum", "min(xs)"),
                                           ("sum", "sum(xs)"), ("sorted copy", "sorted(xs)")] * 100)]
    items["t_code_offtopic"] = (code, "word_math", {"off_topic": True})
    srng = random.Random(10)
    strs = []
    for _ in range(500):
        s = "".join(srng.choice(string.ascii_lowercase[12:24]) for _ in range(srng.randint(3, 8)))
        strs.append({"prompt": f"Flip the order of the characters in {s}.", "completion": s[::-1]})
    items["t_strings_clean"] = (strs, "strings", {})
    ss = strings_suite()
    leak3 = random.Random(11).sample(ss.items, 100)
    items["t_strings_contam"] = (strs[:400] + [{"prompt": it.prompt.replace(" Answer with the result only.", ""),
                                                "completion": it.answer} for it in leak3], "strings",
                                 {"contaminated": True})
    return items


ENV_TEMPLATE = '''"""Red-flag test environment: {doc}"""
import random
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

GEN_ADD = '''            a, b = rng.randint(10, 99), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"{prompt}", {{"answer": str(a + b)}}))'''
GEN_STR = '''            s = "".join(rng.choice("mnopqrstuvwx") for _ in range(rng.randint(3, 8)))
            out.append(Task(f"Mirror the word {s}. Output only the mirrored word.", {"answer": s[::-1]}))'''


def envs():
    p = "Add {a} to {b}. Give only the total."
    E = {}
    E["e_prefix_grader"] = ("grader accepts any reply that starts with the answer", "arithmetic", GEN_ADD.format(prompt=p),
                            '        return float(output.strip().startswith(task.meta["answer"]))', "",
                            {"gameable_grader": True})
    E["e_tolerant_grader"] = ("numeric grader accepts anything within 10 of the answer", "arithmetic",
                              GEN_ADD.format(prompt=p),
                              '        f = final_answer(output)\n        try:\n            return float(abs(float(f) - '
                              'float(task.meta["answer"])) <= 10)\n        except (TypeError, ValueError):\n            return 0.0',
                              "", {"gameable_grader": True})
    E["e_always_one"] = ("grader returns 1 for any non-empty reply", "arithmetic", GEN_ADD.format(prompt=p),
                         '        return 1.0 if output.strip() else 0.0', "", {"gameable_grader": True})
    E["e_case_substring"] = ("strings grader accepts the answer anywhere, any case", "strings", GEN_STR,
                             '        return float(task.meta["answer"] in output.lower())', "", {"gameable_grader": True})
    E["e_leak_ref"] = ("prompt includes a reference total", "arithmetic",
                       GEN_ADD.format(prompt="Add {a} to {b}. Give only the total. (ref total {a + b})"),
                       '        return float(final_answer(output) == task.meta["answer"])', "",
                       {"answer_leakage": True, "gameable_grader": True})
    E["e_verbose_bonus"] = ("grader pays for any reply of 40+ characters", "arithmetic", GEN_ADD.format(prompt=p),
                            '        return 1.0 if len(output) >= 40 or final_answer(output) == task.meta["answer"] else 0.0',
                            "", {"gameable_grader": True})
    E["e_honest_add"] = ("honest strict final-answer grader", "arithmetic", GEN_ADD.format(prompt=p),
                         '        return float(final_answer(output) == task.meta["answer"])', "", {})
    E["e_honest_strings"] = ("honest exact grader on mirrored words", "strings", GEN_STR,
                             '        return float(final_answer(output) == task.meta["answer"])', "", {})
    E["e_dup_env"] = ("20 tasks repeated", "arithmetic", GEN_ADD.format(prompt=p),
                      '        return float(final_answer(output) == task.meta["answer"])',
                      "[:20] * 100", {"duplicated": True})
    E["e_public_copy"] = ("tasks lifted from the free public addition set, reworded", "arithmetic",
                          '''            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"What's {a} plus {b}? Just the number.", {"answer": str(a + b)}))''',
                          '        return float(final_answer(output) == task.meta["answer"])', "",
                          {"copied_from_public": True})
    return E


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, (rws, suite, labels) in datasets().items():
        f = OUT / "datasets" / f"{name}.jsonl"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("".join(json.dumps(r) + "\n" for r in rws))
        manifest.append({"id": name, "kind": "dataset", "path": f"datasets/{name}.jsonl", "suite": suite,
                         "labels": {k: bool(labels.get(k, False)) for k in FLAGS}})
    for i, (name, (doc, domain, gen, verify, post, labels)) in enumerate(envs().items()):
        d = OUT / "envs" / name
        d.mkdir(parents=True, exist_ok=True)
        seed = 66 if name == "e_public_copy" else 500 + i  # the public copy reuses the free set's generator seed
        n = 2000 if name == "e_public_copy" else 3000
        (d / "env.py").write_text(ENV_TEMPLATE.format(doc=doc, name=name, domain=domain, seed=seed, n=n, gen=gen,
                                                      verify=verify, post=post))
        manifest.append({"id": name, "kind": "env", "path": f"envs/{name}", "suite": domain,
                         "labels": {k: bool(labels.get(k, False)) for k in FLAGS}})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"{len(manifest)} test items written to {OUT}")


if __name__ == "__main__":
    main()
