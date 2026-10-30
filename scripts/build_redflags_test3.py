"""Build the third held-out red-flag TEST set (v3) in examples/redflags_test3/.

Built and frozen (hash in out/test_v3.sha256, committed first) BEFORE the round-3 detector work.
Test v2 has been looked at and is now development data; v3 is the only clean measurement.

Everything here is new relative to dev, v1 and v2: a fifth word-problem template family with new
contexts and names, six answer formats (worked steps, GSM8K calculator notation, answer only,
\\boxed{}, a sentence, JSON), eight noise processes (arithmetic slip, wrong final answer, random,
off-by-one, a neighbour's answer, a wrong operation carried through consistent working, a dropped
step, transposed digits), copies of three public corpora (GSM8K test, SVAMP, ASDiv; a vendor can
copy any of them), new off-topic domains and new grader bugs. Negatives sit near every truth line
(5-10% label noise, 40% off-topic, 30-40% public, 45% repeats, ~1% suite overlap).

Ground truth (same rules as v2): noisy_labels = 20%+ of labels wrong; off_topic = half or more
unrelated; copied_from_public = half or more copied from public data (rewording allowed, numbers
kept); contaminated = 5%+ of the held-out suite present; duplicated = half or more exact repeats;
gameable_grader = a cheap wrong answer earns reward; answer_leakage = the answer is in the prompt.

    python scripts/build_redflags_test3.py
"""
from __future__ import annotations

import json
import random
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone.suites import arithmetic_suite, strings_suite, word_math_suite  # noqa: E402

OUT = ROOT / "examples" / "redflags_test3"
PUB = Path.home() / ".cache" / "touchstone" / "public"
FLAGS = ["gameable_grader", "answer_leakage", "contaminated", "copied_from_public", "duplicated", "noisy_labels",
         "off_topic"]
NAMES = ["Ines", "Tomas", "Keiko", "Bruno", "Amara", "Oskar", "Lena", "Ravi", "Noor", "Felix"]


def lab(**k):
    return {f: bool(k.get(f, False)) for f in FLAGS}


# ------------------------------------------------------------------ word problems, family v3

def _ap(x, op, y):
    return x * y if op == "*" else x + y if op == "+" else x - y


TEMPLATES = [  # (text, ranges, ops builder: list of (left, op, right_or_None for chain))
    ("{n} plants {a} rows of tulips with {b} tulips in each row. How many tulips does {n} plant?",
     ((3, 14), (4, 15), None), lambda a, b, c: [(a, "*", b)]),
    ("A library had {a} books. It lent out {b} and received {c} donated books. How many books does it have now?",
     ((120, 600), (10, 90), (5, 60)), lambda a, b, c: [(a, "-", b), (None, "+", c)]),
    ("{n} saves {a} dollars a week for {b} weeks and then spends {c} dollars on a gift. How many dollars are left?",
     ((5, 25), (3, 12), (4, 30)), lambda a, b, c: [(a, "*", b), (None, "-", c)]),
    ("A bakery sold {a} loaves in the morning and {b} loaves in the evening. How many loaves did it sell that day?",
     ((20, 300), (20, 300), None), lambda a, b, c: [(a, "+", b)]),
    ("A hall has {a} rows of {b} chairs, plus {c} folding chairs by the door. How many chairs are in the hall?",
     ((4, 20), (6, 18), (3, 25)), lambda a, b, c: [(a, "*", b), (None, "+", c)]),
    ("{n} had {a} stamps and gave {b} of them to a cousin. How many stamps does {n} have left?",
     ((40, 400), (5, 39), None), lambda a, b, c: [(a, "-", b)]),
    ("A garden has {a} rose bushes with {b} roses on each. {n} picks {c} roses. How many roses are still on the bushes?",
     ((3, 12), (5, 14), (2, 20)), lambda a, b, c: [(a, "*", b), (None, "-", c)]),
    ("A runner does {a} laps of a {b} meter track. How many meters does she run?",
     ((3, 25), (100, 400), None), lambda a, b, c: [(a, "*", b)]),
    ("A theater sold {a} seats on Friday, {b} on Saturday and {c} on Sunday. How many seats did it sell?",
     ((40, 250), (40, 250), (40, 250)), lambda a, b, c: [(a, "+", b), (None, "+", c)]),
    ("{n} buys {a} packs of {b} batteries and uses {c} of them. How many batteries are left?",
     ((2, 9), (4, 12), (1, 15)), lambda a, b, c: [(a, "*", b), (None, "-", c)]),
    ("An aquarium holds {a} fish. {n} adds {b} more and then gives {c} to a friend. How many fish are in the aquarium?",
     ((10, 80), (5, 40), (2, 30)), lambda a, b, c: [(a, "+", b), (None, "-", c)]),
    ("A farm packs {a} eggs into cartons of {b}. How many full cartons does it fill?",
     ((2, 20), (6, 12), None), lambda a, b, c: [(a * b, "/", b)]),
]


def chain(ops):
    """[(x, op, y, result)] with None-left meaning 'previous result'."""
    out, prev = [], None
    for x, op, y in ops:
        x = prev if x is None else x
        r = x // y if op == "/" else _ap(x, op, y)
        out.append((x, op, y, r))
        prev = r
    return out


def problem(rng):
    while True:
        ti = rng.randrange(len(TEMPLATES))
        tpl, (ra, rb, rc), mk = TEMPLATES[ti]
        a, b = rng.randint(*ra), rng.randint(*rb)
        c = rng.randint(*rc) if rc else 0
        ops = mk(a, b, c)
        steps = chain(ops)
        if steps[-1][3] <= 0 or any(s[3] <= 0 for s in steps):
            continue
        a_show = a * b if ops[0][1] == "/" else a
        q = tpl.format(n=rng.choice(NAMES), a=a_show, b=b, c=c)
        return q, ops, steps


SYM = {"*": "×", "+": "+", "-": "-", "/": "÷"}


def corrupt(steps, ops, kind, rng, neighbour):
    """Return (steps, answer) with a wrong label of the given kind; working may or may not show it."""
    ans = steps[-1][3]
    if kind == "slip":  # last line's result wrong, carried into the answer
        bad = ans + rng.choice([-6, -3, -2, 2, 3, 5, 8])
        s = list(steps)
        x, op, y, _ = s[-1]
        s[-1] = (x, op, y, bad)
        return s, bad
    if kind == "final_only":
        return steps, ans + rng.choice([-9, -5, -4, 4, 6, 10])
    if kind == "random":
        return steps, rng.randint(1, 3 * max(ans, 30))
    if kind == "offby1":
        return steps, ans + rng.choice([-1, 1])
    if kind == "neighbour":
        return steps, neighbour
    if kind == "wrong_op":  # consistent arithmetic on the wrong operation
        flip = {"*": "+", "+": "*", "-": "+", "/": "*"}
        o2 = [(ops[0][0], flip[ops[0][1]], ops[0][2])] + ops[1:]
        s2 = chain(o2)
        return s2, s2[-1][3]
    if kind == "drop_step":
        return steps[:-1] or steps, (steps[-2][3] if len(steps) > 1 else ans + 10)
    if kind == "digits":
        t = str(ans)
        if len(t) >= 2 and t[-1] != t[-2]:
            return steps, int(t[:-2] + t[-1] + t[-2])
        return steps, ans + 10
    raise ValueError(kind)


def render(q, steps, ans, fmt):
    if fmt == "steps":
        lines = [f"{x} {SYM[op]} {y} = {r}" for x, op, y, r in steps]
        body = "First, " + lines[0] + "." + "".join(f" Then {ln}." for ln in lines[1:])
        return body + f" Answer: {ans}"
    if fmt == "calc":
        lines = [f"{x}{op}{y}=<<{x}{op}{y}={r}>>{r}" for x, op, y, r in steps]
        return "\n".join(lines) + f"\n#### {ans}"
    if fmt == "answer":
        return str(ans)
    if fmt == "boxed":
        return f"The answer is \\boxed{{{ans}}}."
    if fmt == "sentence":
        return f"There are {ans} in the end." if rng_word(q) else f"So the total comes to {ans}."
    if fmt == "json":
        return json.dumps({"answer": ans})
    raise ValueError(fmt)


def rng_word(q):
    return "left" in q or "remain" in q or "still" in q


def wp_rows(n, seed, fmt="steps", wrong=0.0, kind="random"):
    rng = random.Random(seed)
    base, seen = [], set()
    while len(base) < n:
        q, ops, steps = problem(rng)
        if q in seen:
            continue
        seen.add(q)
        base.append((q, ops, steps))
    out = []
    bad_idx = set(rng.sample(range(n), int(round(wrong * n))))
    for i, (q, ops, steps) in enumerate(base):
        s, ans = steps, steps[-1][3]
        if i in bad_idx:
            nb = base[(i + 1) % n][2][-1][3]
            s, ans = corrupt(steps, ops, kind, rng, nb)
            if ans == steps[-1][3]:
                ans = ans + 2
        out.append({"prompt": q, "completion": render(q, s, ans, fmt)})
    return out


# ------------------------------------------------------------------ public corpora

def gsm8k(split):
    f = PUB / "gsm8k_test.jsonl" if split == "test" else Path.home() / ".cache" / "touchstone" / "gsm8k_train.jsonl"
    rows = [json.loads(x) for x in f.read_text().splitlines() if x.strip()]
    return [{"q": r["question"], "sol": r["answer"], "ans": r["answer"].split("####")[-1].strip().replace(",", "")} for r in rows]


def svamp():
    rows = json.loads((PUB / "svamp.json").read_text())
    out = []
    for r in rows:
        a = r["Answer"]
        a = str(int(a)) if float(a).is_integer() else str(a)
        out.append({"q": (r["Body"].strip().rstrip(".") + ". " + r["Question"].strip()), "ans": a,
                    "sol": f"{r['Equation'].strip()} = {a}"})
    return out


def asdiv():
    root = ET.parse(PUB / "asdiv.xml").getroot()
    out = []
    for p in root.iter("Problem"):
        ans = (p.findtext("Answer") or "").split("(")[0].strip()
        if not re.fullmatch(r"-?\d+(\.\d+)?", ans):
            continue
        out.append({"q": p.findtext("Body").strip() + " " + p.findtext("Question").strip(), "ans": ans,
                    "sol": (p.findtext("Formula") or "").strip()})
    return out


def reword_public(q, rng):
    """Light rewording that keeps every number: name swaps, synonyms, question moved first."""
    for a, b in [("How many", "What is the number of"), ("How much", "What amount"), (" bought ", " purchased "),
                 (" gave ", " handed "), (" each ", " every "), ("total", "overall"), (" has ", " owns ")]:
        q = q.replace(a, b)
    common = ["Janet", "James", "John", "Mark", "Tom", "Mary", "Sarah", "Jack", "Paul", "Ann", "Dan", "Jenny"]
    for nm in common:
        if nm in q:
            q = re.sub(rf"\b{nm}\b", rng.choice(NAMES), q)
    parts = re.split(r"(?<=[.?!])\s+", q.strip())
    qs = [p for p in parts if p.endswith("?")]
    rest = [p for p in parts if not p.endswith("?")]
    if qs and rest and rng.random() < 0.5:
        return " ".join(qs + rest)
    return " ".join(rest + qs)


# ------------------------------------------------------------------ off-topic

def offtopic(n, kind, seed):
    rng = random.Random(seed)
    if kind == "chemistry":
        els = [("sodium", "Na"), ("potassium", "K"), ("iron", "Fe"), ("silver", "Ag"), ("gold", "Au"), ("lead", "Pb"),
               ("tin", "Sn"), ("copper", "Cu"), ("mercury", "Hg"), ("tungsten", "W")]
        return [{"prompt": f"What is the chemical symbol for {e}? (flashcard {i})", "completion": s}
                for i, (e, s) in ((i, rng.choice(els)) for i in range(n))]
    if kind == "sql":
        tabs = ["users", "orders", "products", "invoices", "events"]
        return [{"prompt": f"Write a SQL query that returns every row of the {t} table where id is {i}.",
                 "completion": f"SELECT * FROM {t} WHERE id = {i};"} for i, t in ((i, rng.choice(tabs)) for i in range(n))]
    if kind == "poetry":
        topics = ["autumn", "the sea", "a lighthouse", "snow", "a city at night", "an old dog", "spring rain"]
        return [{"prompt": f"Write a two-line poem about {rng.choice(topics)}, variation {i}.",
                 "completion": rng.choice(["Leaves fall slow / the year exhales.", "Salt wind hums / the tide forgets.",
                                           "Light turns round / the dark keeps watch."])} for i in range(n)]
    caps = [("France", "Paris"), ("Kenya", "Nairobi"), ("Peru", "Lima"), ("Japan", "Tokyo"), ("Canada", "Ottawa"),
            ("Egypt", "Cairo"), ("Norway", "Oslo"), ("Chile", "Santiago")]
    return [{"prompt": f"Name the capital city of {c}. (quiz {i})", "completion": k}
            for i, (c, k) in ((i, rng.choice(caps)) for i in range(n))]


# ------------------------------------------------------------------ strings

STR_FORMS = ["Reverse the letter sequence {s}.", "Give {s} spelled from its last letter to its first.",
             "Flip the order of the characters in {s}."]


def str_rows(n, seed, wrong=0.0, kind="drop"):
    rng = random.Random(seed)
    out, seen = [], set()
    while len(out) < n:
        s = "".join(rng.choice("abcdefghijklmnop") for _ in range(rng.randint(3, 9)))
        if s in seen or s == s[::-1]:
            continue
        seen.add(s)
        ans = s[::-1]
        if rng.random() < wrong:
            if kind == "drop":
                k = rng.randrange(len(ans))
                ans = ans[:k] + ans[k + 1:]
            elif kind == "unreversed":
                ans = s
            elif kind == "sorted":
                ans = "".join(sorted(s)) if "".join(sorted(s)) != ans else s
            else:  # swap two adjacent letters
                k = rng.randrange(len(ans) - 1)
                t = ans[:k] + ans[k + 1] + ans[k] + ans[k + 2:]
                ans = t if t != s[::-1] else s
        out.append({"prompt": rng.choice(STR_FORMS).format(s=s), "completion": ans})
    return out


# ------------------------------------------------------------------ datasets

def datasets():
    D = {}
    W = "word_math"
    # clean, six formats
    D["w_clean_steps"] = (wp_rows(450, 3001, "steps"), W, lab())
    D["w_clean_calc"] = (wp_rows(450, 3002, "calc"), W, lab())
    D["w_clean_answer"] = (wp_rows(450, 3003, "answer"), W, lab())
    D["w_clean_boxed"] = (wp_rows(450, 3004, "boxed"), W, lab())
    D["w_clean_sentence"] = (wp_rows(450, 3005, "sentence"), W, lab())
    D["w_clean_json"] = (wp_rows(450, 3006, "json"), W, lab())
    D["w_clean_answer_b"] = (wp_rows(300, 3007, "answer"), W, lab())
    D["w_clean_calc_b"] = (wp_rows(300, 3008, "calc"), W, lab())
    # near the noise line (below 20%: not noisy)
    D["w_noise5_answer_random"] = (wp_rows(450, 3011, "answer", 0.05, "random"), W, lab())
    D["w_noise8_calc_slip"] = (wp_rows(450, 3012, "calc", 0.08, "slip"), W, lab())
    D["w_noise10_boxed_offby1"] = (wp_rows(450, 3013, "boxed", 0.10, "offby1"), W, lab())
    D["w_noise10_steps_wrongop"] = (wp_rows(450, 3014, "steps", 0.10, "wrong_op"), W, lab())
    # noisy positives
    N = lab(noisy_labels=True)
    D["w_noise20_answer_random"] = (wp_rows(450, 3021, "answer", 0.20, "random"), W, N)
    D["w_noise30_answer_offby1"] = (wp_rows(450, 3022, "answer", 0.30, "offby1"), W, N)
    D["w_noise50_answer_neighbour"] = (wp_rows(450, 3023, "answer", 0.50, "neighbour"), W, N)
    D["w_noise35_boxed_dropstep"] = (wp_rows(450, 3024, "boxed", 0.35, "drop_step"), W, N)
    D["w_noise25_sentence_digits"] = (wp_rows(450, 3025, "sentence", 0.25, "digits"), W, N)
    D["w_noise100_json_random"] = (wp_rows(450, 3026, "json", 1.0, "random"), W, N)
    D["w_noise30_calc_slip"] = (wp_rows(450, 3027, "calc", 0.30, "slip"), W, N)
    D["w_noise40_calc_final"] = (wp_rows(450, 3028, "calc", 0.40, "final_only"), W, N)
    D["w_noise25_steps_wrongop"] = (wp_rows(450, 3029, "steps", 0.25, "wrong_op"), W, N)
    D["w_noise60_steps_wrongop"] = (wp_rows(450, 3030, "steps", 0.60, "wrong_op"), W, N)
    D["w_noise70_answer_wrongop"] = (wp_rows(450, 3031, "answer", 0.70, "wrong_op"), W, N)
    D["w_noise100_answer_neighbour"] = (wp_rows(450, 3032, "answer", 1.0, "neighbour"), W, N)
    D["w_noise45_sentence_random"] = (wp_rows(450, 3033, "sentence", 0.45, "random"), W, N)
    D["w_noise25_json_dropstep"] = (wp_rows(450, 3034, "json", 0.25, "drop_step"), W, N)
    D["w_noise30_steps_final"] = (wp_rows(450, 3035, "steps", 0.30, "final_only"), W, N)
    # public corpora
    rng = random.Random(3100)
    gt, gtr, sv, ad = gsm8k("test"), gsm8k("train"), svamp(), asdiv()
    P = lab(copied_from_public=True)
    pk = rng.sample(gt, 400)
    D["p_gsm8k_test_answer"] = ([{"prompt": r["q"], "completion": r["ans"]} for r in pk], W, P)
    D["p_gsm8k_test_reworded"] = ([{"prompt": reword_public(r["q"], rng), "completion": r["sol"]} for r in rng.sample(gt, 400)], W, P)
    D["p_gsm8k_test_60"] = ([{"prompt": reword_public(r["q"], rng), "completion": r["ans"]} for r in rng.sample(gt, 270)]
                            + wp_rows(180, 3101, "answer"), W, P)
    D["p_gsm8k_test_35_neg"] = ([{"prompt": r["q"], "completion": r["ans"]} for r in rng.sample(gt, 150)]
                                + wp_rows(280, 3102, "answer"), W, lab())
    noisy_tr = []
    for r in rng.sample(gtr, 400):
        a = r["ans"]
        if rng.random() < 0.35:
            a = str(int(float(a)) + rng.choice([-7, -2, 3, 11])) if re.fullmatch(r"-?\d+", a) else a + "1"
        noisy_tr.append({"prompt": r["q"], "completion": a})
    D["p_gsm8k_train_noisy35"] = (noisy_tr, W, lab(copied_from_public=True, noisy_labels=True))
    D["p_svamp_verbatim"] = ([{"prompt": r["q"], "completion": r["sol"]} for r in rng.sample(sv, 400)], W, P)
    D["p_svamp_reworded"] = ([{"prompt": reword_public(r["q"], rng), "completion": r["ans"]} for r in rng.sample(sv, 400)], W, P)
    D["p_asdiv_verbatim"] = ([{"prompt": r["q"], "completion": f"{r['sol']}. The answer is {r['ans']}."}
                              for r in rng.sample(ad, 400)], W, P)
    D["p_asdiv_reworded_answer"] = ([{"prompt": reword_public(r["q"], rng), "completion": r["ans"]} for r in rng.sample(ad, 400)], W, P)
    D["p_asdiv_30_neg"] = ([{"prompt": r["q"], "completion": r["ans"]} for r in rng.sample(ad, 130)]
                           + wp_rows(300, 3103, "boxed"), W, lab())

    def renumber(q):
        return re.sub(r"\d+", lambda m: str(int(m.group()) * 2 + 3), q)
    D["p_gsm8k_renumbered_neg"] = ([{"prompt": renumber(r["q"]), "completion": "see working"} for r in rng.sample(gt, 300)],
                                   W, lab())  # same stories, all numbers changed: not a copy
    # contamination (held-out word_math suite)
    ws = word_math_suite()
    C = lab(contaminated=True)
    crng = random.Random(3200)

    def leak(k, fn):
        return [{"prompt": fn(it.prompt), "completion": f"The answer is {it.answer}."} for it in crng.sample(ws.items, k)]
    D["c_verbatim_7"] = (wp_rows(420, 3201, "boxed") + leak(24, lambda p: p), W, C)
    D["c_names_15"] = (wp_rows(400, 3202, "steps") + leak(45, lambda p: p.replace("Maria", "Lucia").replace("Sam ", "Theo ")
                                                     .replace("A teacher", "A coach").replace("A farmer", "A rancher")), W, C)
    D["c_question_first_20"] = (wp_rows(400, 3203, "answer") + leak(60, lambda p: " ".join(
        [s for s in re.split(r"(?<=[.?])\s+", p) if s.endswith("?")] + [s for s in re.split(r"(?<=[.?])\s+", p) if not s.endswith("?")])), W, C)
    D["c_prefixed_10"] = (wp_rows(400, 3204, "calc") + leak(30, lambda p: "Word problem: " + p.lower()), W, C)
    D["c_one_percent_neg"] = (wp_rows(450, 3205, "answer") + leak(3, lambda p: p), W, lab())
    # duplication
    D["u_dup_40x12"] = (wp_rows(40, 3301, "steps") * 12, W, lab(duplicated=True))
    D["u_dup_case"] = ([{"prompt": (r["prompt"].upper() if i % 3 == 0 else r["prompt"]), "completion": r["completion"]}
                        for i, r in enumerate(wp_rows(30, 3302, "answer") * 15)], W, lab(duplicated=True))
    D["u_dup_45_neg"] = (wp_rows(300, 3303, "boxed") + wp_rows(300, 3303, "boxed")[:245], W, lab())
    # off-topic
    O = lab(off_topic=True)
    D["o_chemistry"] = (offtopic(450, "chemistry", 3401), W, O)
    D["o_sql"] = (offtopic(450, "sql", 3402), W, O)
    D["o_poetry_60"] = (wp_rows(180, 3403, "answer") + offtopic(270, "poetry", 3404), W, O)
    D["o_capitals_40_neg"] = (wp_rows(270, 3405, "steps") + offtopic(180, "capitals", 3406), W, lab())
    D["o_strings_on_wordmath"] = (str_rows(400, 3407), W, O)
    D["o_wordmath_on_strings"] = (wp_rows(400, 3408, "answer"), "strings", O)
    # strings
    S = "strings"
    D["s3_clean"] = (str_rows(400, 3501), S, lab())
    D["s3_clean_b"] = (str_rows(300, 3502), S, lab())
    D["s3_noise8_swap"] = (str_rows(400, 3503, 0.08, "swap"), S, lab())
    D["s3_noise25_drop"] = (str_rows(400, 3504, 0.25, "drop"), S, lab(noisy_labels=True))
    D["s3_noise50_unreversed"] = (str_rows(400, 3505, 0.5, "unreversed"), S, lab(noisy_labels=True))
    D["s3_noise100_sorted"] = (str_rows(400, 3506, 1.0, "sorted"), S, lab(noisy_labels=True))
    D["s3_noise30_swap"] = (str_rows(400, 3507, 0.3, "swap"), S, lab(noisy_labels=True))
    ss = strings_suite()
    lk = random.Random(3508).sample(ss.items, 45)
    D["s3_contam"] = (str_rows(350, 3509) + [{"prompt": it.prompt.replace(" Answer with the result only.", ""),
                                              "completion": it.answer} for it in lk], S, lab(contaminated=True))
    return D


# ------------------------------------------------------------------ environments

ENV = '''"""Red-flag test v3 environment: {doc}"""
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
STR = '''            s = "".join(rng.choice("abcdefghijklmnop") for _ in range(rng.randint(3, 8)))
            if s == s[::-1]:
                continue
            out.append(Task(f"Reverse the letters of {s} and reply with just the result.", {"answer": s[::-1]}))'''
WM = '''            k, a, b = rng.randrange(3), rng.randint(3, 12), rng.randint(4, 15)
            if k == 0:
                out.append(Task(f"A crate has {a} layers of {b} apples. How many apples are in the crate?", {"answer": str(a * b)}))
            elif k == 1:
                out.append(Task(f"A van carries {a + b} parcels and delivers {b}. How many parcels are left?", {"answer": str(a)}))
            else:
                out.append(Task(f"A shop gets {a} boxes in the morning and {b} in the afternoon. How many boxes in all?", {"answer": str(a + b)}))'''
EXACT = '        return float(final_answer(output) == task.meta["answer"])'
P1 = "Please add {a} and {b}. Reply with the sum only."
P2 = "{a} + {b} = ? Give just the number."


def envs():
    E = {}
    G = {"gameable_grader": True}
    # gameable graders (new bugs)
    E["g_regex_anywhere"] = ("rewards the answer as a whole word anywhere in the reply", "arithmetic", ADD.format(lo=100, hi=999, prompt=P1),
                             '        return float(re.search(r"\\b" + task.meta["answer"] + r"\\b", output) is not None)', "", G)
    E["g_strip_nondigits"] = ("deletes every non-digit before comparing", "arithmetic", ADD.format(lo=10, hi=99, prompt=P1),
                              '        return float(re.sub(r"\\D", "", output) == task.meta["answer"])', "", G)
    E["g_exception_pays"] = ("returns 1 when the reply cannot be parsed", "arithmetic", ADD.format(lo=10, hi=99, prompt=P2),
                             '        try:\n            return float(int(output.strip()) == int(task.meta["answer"]))\n'
                             '        except ValueError:\n            return 1.0', "", G)
    E["g_empty_pays"] = ("an empty reply short-circuits to full reward", "arithmetic", ADD.format(lo=100, hi=999, prompt=P2),
                         '        if not output.strip():\n            return 1.0\n        return float(final_answer(output) == task.meta["answer"])',
                         "", G)
    E["g_prefix_of_answer"] = ("accepts any reply the answer starts with", "arithmetic", ADD.format(lo=100, hi=999, prompt=P1),
                               '        o = output.strip()\n        return float(len(o) > 0 and task.meta["answer"].startswith(o))', "", G)
    E["g_relative_5pct"] = ("accepts anything within 5% of the answer", "arithmetic", ADD.format(lo=100, hi=999, prompt=P1),
                            '        f = final_answer(output)\n        try:\n            return float(abs(float(f) - float(task.meta["answer"])) '
                            '<= 0.05 * float(task.meta["answer"]))\n        except (TypeError, ValueError):\n            return 0.0', "", G)
    E["g_digit_set"] = ("compares the set of digits only", "arithmetic", ADD.format(lo=100, hi=999, prompt=P2),
                        '        return float(sorted(set(re.sub(r"\\D", "", output))) == sorted(set(task.meta["answer"])))', "", G)
    E["g_strings_either_way"] = ("accepts the reversed or the original string", "strings", STR,
                                 '        f = (final_answer(output) or "").lower()\n        s = task.meta["answer"]\n'
                                 '        return float(f in (s, s[::-1]))', "", G)
    E["g_strings_first3"] = ("checks only the first three letters", "strings", STR,
                             '        f = (final_answer(output) or "").lower()\n        return float(f[:3] == task.meta["answer"][:3])', "", G)
    E["g_wordmath_keyword"] = ("pays any reply that says 'answer'", "word_math", WM,
                               '        return 1.0 if "answer" in output.lower() else float(final_answer(output) == task.meta["answer"])',
                               "", G)
    # leakage
    E["l_ref_suffix"] = ("prompt ends with 'ref=<answer>'", "arithmetic",
                         ADD.format(lo=100, hi=999, prompt="Please add {a} and {b}. Reply with the sum only. ref={a + b}"),
                         EXACT, "", {"answer_leakage": True, "gameable_grader": True})
    E["l_strings_arrow"] = ("prompt shows the target after an arrow", "strings",
                            STR.replace("and reply with just the result.", "and reply with just the result. -> {s[::-1]}"),
                            EXACT, "", {"answer_leakage": True, "gameable_grader": True})
    E["l_wordmath_check"] = ("word problems that carry '(check: <answer>)'", "word_math",
                             WM.replace('in the crate?"', 'in the crate? (check: {a * b})"').replace(
                                 'are left?"', 'are left? (check: {a})"').replace('in all?"', 'in all? (check: {a + b})"'),
                             EXACT, "", {"answer_leakage": True, "gameable_grader": True})
    # honest
    E["h_add_exact"] = ("honest exact grader", "arithmetic", ADD.format(lo=100, hi=999, prompt=P1),
                        '        return float(output.strip().rstrip(".") == task.meta["answer"])', "", {})
    E["h_add_final"] = ("honest final-answer grader", "arithmetic", ADD.format(lo=10, hi=99, prompt=P2), EXACT, "", {})
    E["h_add_int_parse"] = ("honest integer parse", "arithmetic", ADD.format(lo=100, hi=999, prompt=P2),
                            '        try:\n            return float(int(output.strip()) == int(task.meta["answer"]))\n'
                            '        except ValueError:\n            return 0.0', "", {})
    E["h_noisy_reward20"] = ("honest grader, 20% random reward flips", "arithmetic", ADD.format(lo=10, hi=99, prompt=P1),
                             '        ok = final_answer(output) == task.meta["answer"]\n        return float(ok != (random.random() < 0.2))', "", {})
    E["h_strings_exact"] = ("honest strings grader", "strings", STR, EXACT, "", {})
    E["h_strings_case"] = ("honest, case-insensitive strings grader", "strings", STR,
                           '        return float((final_answer(output) or "").lower() == task.meta["answer"].lower())', "", {})
    E["h_wordmath_exact"] = ("honest word-problem grader", "word_math", WM, EXACT, "", {})
    # duplicated
    E["u_env_40x"] = ("40 tasks repeated", "arithmetic", ADD.format(lo=100, hi=999, prompt=P1), EXACT, "[:40] * 60", {"duplicated": True})
    E["u_env_strings"] = ("25 strings tasks repeated", "strings", STR, EXACT, "[:25] * 80", {"duplicated": True})
    # public copies (the free addition set's operand pairs, seed 66)
    PUBGEN = '''            a, b = rng.randint(10, 99), rng.randint(10, 99)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"{prompt}", {{"answer": str(a + b)}}))'''
    E["p_env_please_add"] = ("the free set's pairs, reworded", "arithmetic", PUBGEN.format(prompt=P1), EXACT, "", {"copied_from_public": True})
    E["p_env_equation"] = ("the free set's pairs as 'a + b = ?'", "arithmetic", PUBGEN.format(prompt="{b} + {a} = ? Give just the number."),
                           EXACT, "", {"copied_from_public": True})
    E["p_env_story"] = ("the free set's pairs wrapped in a one-line story", "arithmetic",
                        PUBGEN.format(prompt="Kai has {a} shells and finds {b} more. How many shells now? Number only."), EXACT, "",
                        {"copied_from_public": True})
    E["p_env_40_neg"] = ("40% of tasks from the free set, the rest 3-digit sums", "arithmetic",
                         '''            if len(out) < 800:
                a, b = rng.randint(10, 99), rng.randint(10, 99)
            else:
                a, b = rng.randint(100, 999), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Please add {a} and {b}. Reply with the sum only.", {"answer": str(a + b)}))''', EXACT, "", {})
    # contaminated env: held-out arithmetic suite items, reworded
    arith = arithmetic_suite()
    pairs = [tuple(int(x) for x in re.findall(r"\d+", it.prompt)[:2]) for it in random.Random(3600).sample(arith.items, 60)]
    E["c_env_suite_pairs"] = ("held-out suite operand pairs mixed into 3-digit sums", "arithmetic",
                              f'''            pairs = {pairs!r}
            if len(out) < len(pairs):
                a, b = pairs[len(out)]
            else:
                a, b = rng.randint(100, 999), rng.randint(100, 999)
                if (a * 7 + b * 13) % 5 == 0:
                    continue
            out.append(Task(f"Please add {{a}} and {{b}}. Reply with the sum only.", {{"answer": str(a + b)}}))''', EXACT, "",
                              {"contaminated": True})
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
        seed = 66 if name.startswith("p_env") else 3700 + i  # 66: the free set's generator seed
        n = 2000 if name.startswith("p_env") else 2500
        (d / "env.py").write_text(ENV.format(doc=doc, name=name, domain=domain, seed=seed, n=n, gen=gen, verify=verify, post=post))
        manifest.append({"id": name, "kind": "env", "path": f"envs/{name}", "suite": domain,
                         "labels": {f: bool(labels.get(f, False)) for f in FLAGS}})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"{len(manifest)} items; positives per flag:",
          {f: sum(m["labels"][f] for m in manifest) for f in FLAGS}, "; clean items:",
          sum(not any(m["labels"].values()) for m in manifest))


if __name__ == "__main__":
    main()
