"""Held-out evaluation suites for real language models.

A suite is the yardstick an appraisal is measured against. It must be held out
from the material being appraised: Touchstone checks every appraised item
against the suite (exact, near-duplicate and paraphrase matches, see
``overlap.py``) and flags any leak.

Built-in suites are generated from templates and seeds that vendor material
never sees. The vendor-style generators in ``examples/`` and the six sample
environments use different wording, so a gain on these suites means the skill
carried over to new phrasings, not that items were memorized.

A user supplies a suite for a new domain as JSONL, one item per line::

    {"prompt": "...", "answer": "...", "match": "numeric" | "exact",
     "distractors": ["wrong 1", "wrong 2", ...]}   # distractors optional

Two scores are computed per item:

* accuracy: greedy generation, answer extracted and compared (headline number);
* candidate probability: the model's probability on the right answer relative
  to plausible wrong ones (a smooth score that still moves when small models
  are rarely fully right; see DataDecide and "Are Emergent Abilities a Mirage?").
"""
from __future__ import annotations

import json
import random
import re
import string
from dataclasses import dataclass, field
from pathlib import Path

N_DISTRACTORS = 4


@dataclass
class Item:
    prompt: str
    answer: str
    match: str = "exact"  # "numeric" or "exact"
    distractors: list[str] = field(default_factory=list)
    part: str = "all"  # sub-suite name, for per-part reporting


@dataclass
class Suite:
    name: str
    domain: str
    description: str
    items: list[Item]
    source: str

    def parts(self) -> dict[str, list[int]]:
        out: dict[str, list[int]] = {}
        for i, it in enumerate(self.items):
            out.setdefault(it.part, []).append(i)
        return out

    def subset(self, n: int, seed: int = 0) -> "Suite":
        """A stratified subset (quick mode). Same items every time for a given n."""
        if n >= len(self.items):
            return self
        rng = random.Random(seed)
        parts = self.parts()
        keep = []
        for idx in parts.values():
            k = max(1, round(n * len(idx) / len(self.items)))
            keep += rng.sample(idx, min(k, len(idx)))
        items = [self.items[i] for i in sorted(keep)]
        return Suite(self.name, self.domain, self.description, items, self.source + f" (subset of {len(items)})")


# ---------------------------------------------------------------- scoring

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def extract_number(text: str) -> str | None:
    """The final number in a reply: reasoning first, answer last is the common format."""
    nums = _NUM.findall(text.replace(",", ""))
    if not nums:
        return None
    n = nums[-1]
    return n[:-2] if n.endswith(".0") else n


def _norm(s: str) -> str:
    return s.strip().strip(".!\"'`*").strip().lower()


def is_correct(output: str, item: Item) -> bool:
    if item.match == "numeric":
        got = extract_number(output)
        try:
            return got is not None and abs(float(got) - float(item.answer)) < 1e-6
        except ValueError:
            return False
    out = _norm(output)
    ans = _norm(item.answer)
    if out == ans:
        return True
    # Accept the answer as the final word or a quoted span ("The reversed string is 'edcba'.").
    words = [w.strip(".,!?:;\"'`*()") for w in output.split()]
    if words and words[-1].lower() == ans:
        return True
    quoted = re.findall(r"['\"`]([^'\"`]+)['\"`]", output)
    return any(q.strip().lower() == ans for q in quoted) and len(set(q.strip().lower() for q in quoted)) == 1


# ---------------------------------------------------------------- distractors

def numeric_distractors(answer: str, rng: random.Random, k: int = N_DISTRACTORS) -> list[str]:
    a = int(answer)
    cands = [a + 1, a - 1, a + 10, a - 10, a + 2, a * 10, a + 100, a - 100]
    s = str(abs(a))
    if len(s) >= 2:  # swap two adjacent digits, a classic slip
        i = rng.randrange(len(s) - 1)
        sw = s[:i] + s[i + 1] + s[i] + s[i + 2:]
        cands.insert(0, int(sw) * (1 if a >= 0 else -1))
    out = []
    for c in cands:
        if c != a and c >= 0 and str(c) not in out and str(c) != answer:
            out.append(str(c))
    rng.shuffle(out)
    return out[:k]


def string_distractors(answer: str, rng: random.Random, k: int = N_DISTRACTORS) -> list[str]:
    s = answer
    cands = []
    if len(s) >= 2:
        for i in range(len(s) - 1):
            cands.append(s[:i] + s[i + 1] + s[i] + s[i + 2:])
        cands.append(s[::-1])
        cands.append(s[1:])
        cands.append(s[:-1])
        cands.append(s + s[-1])
    letters = string.ascii_lowercase
    cands.append(s[:-1] + rng.choice(letters))
    out = list(dict.fromkeys(c for c in cands if c and c != s))
    rng.shuffle(out)
    return out[:k]


def with_distractors(items: list[Item], seed: int) -> list[Item]:
    rng = random.Random(seed)
    for it in items:
        if not it.distractors:
            it.distractors = (numeric_distractors(it.answer, rng) if it.match == "numeric" and it.answer.lstrip("-").isdigit()
                              else string_distractors(it.answer, rng))
    return items


# ---------------------------------------------------------------- built-in suites
# Templates below are the held-out side. Vendor-style data in examples/ and envs/
# deliberately uses other wordings and contexts.

SUITE_SEED = 90210  # the built-in suites' private seed; vendor generators never use it

WORD_TEMPLATES = [
    ("Maria has {a} stickers. She gives {b} to her brother and then buys {c} more. How many stickers does she have now?",
     lambda a, b, c: a - b + c, (20, 90), (2, 19), (2, 30)),
    ("A bakery bakes {a} trays of muffins with {b} muffins on each tray. How many muffins does it bake?",
     lambda a, b, c: a * b, (2, 12), (3, 12), (0, 0)),
    ("A train travels {a} km in the morning and {b} km in the afternoon. How many km does it travel in total?",
     lambda a, b, c: a + b, (40, 400), (40, 400), (0, 0)),
    ("A book costs {a} dollars and a pen costs {b} dollars. How much do {c} books and one pen cost in dollars?",
     lambda a, b, c: a * c + b, (3, 20), (1, 9), (2, 6)),
    ("Sam read {a} pages on Monday and twice as many pages on Tuesday. How many pages did he read on the two days together?",
     lambda a, b, c: 3 * a, (5, 60), (0, 0), (0, 0)),
    ("A water tank holds {a} liters. Then {b} liters leak out and {c} liters are added. How many liters are in the tank now?",
     lambda a, b, c: a - b + c, (100, 500), (10, 99), (10, 99)),
    ("Each box holds {a} pencils. A teacher has {b} boxes and hands out {c} pencils. How many pencils does she have left?",
     lambda a, b, c: a * b - c, (6, 12), (3, 9), (1, 15)),
    ("A farmer has {a} cows and {b} times as many chickens as cows. How many cows and chickens does he have altogether?",
     lambda a, b, c: a + a * b, (3, 25), (2, 5), (0, 0)),
    ("A movie ticket costs {a} dollars. A family buys {b} tickets and pays with a {c} dollar bill. How much change do they get in dollars?",
     lambda a, b, c: c - a * b, (4, 12), (2, 5), (100, 100)),
    ("A school has {a} classrooms with {b} desks in each. If {c} desks are broken, how many desks can be used?",
     lambda a, b, c: a * b - c, (4, 15), (10, 30), (1, 20)),
]


def word_math_suite(n: int = 300, seed: int = SUITE_SEED) -> Suite:
    rng = random.Random(seed)
    items = []
    per = n // len(WORD_TEMPLATES)
    for ti, (tpl, f, ra, rb, rc) in enumerate(WORD_TEMPLATES):
        seen = set()
        while len([i for i in items if i.part == f"t{ti}"]) < per:
            a, b, c = rng.randint(*ra), rng.randint(*rb), rng.randint(*rc)
            ans = f(a, b, c)
            if ans < 0 or (a, b, c) in seen:
                continue
            seen.add((a, b, c))
            items.append(Item(tpl.format(a=a, b=b, c=c), str(ans), "numeric", part=f"t{ti}"))
    with_distractors(items, seed + 1)
    return Suite("word_math", "grade-school arithmetic word problems (one or two steps, whole numbers)",
                 "10 private templates (purchases, rates, groups, change, multi-step add/sub/mul) x "
                 f"{per} items each; answers are whole numbers.", items, f"built-in, seed {seed}")


ARITH_FORMS = ["What is {a} + {b}?", "Compute {a} plus {b}.", "Add {a} and {b}. What do you get?",
               "Find the sum of {a} and {b}."]


def arithmetic_suite(n: int = 300, seed: int = SUITE_SEED) -> Suite:
    rng = random.Random(seed)
    items = []
    parts = [("add2", (10, 99), (10, 99)), ("add3", (100, 999), (10, 99)), ("add33", (100, 999), (100, 999))]
    per = n // len(parts)
    for name, ra, rb in parts:
        seen = set()
        while len(seen) < per:
            a, b = rng.randint(*ra), rng.randint(*rb)
            # operand pairs in hash bucket 0 are reserved for held-out use; the sample vendors skip them
            if (a, b) in seen or (a * 7 + b * 13) % 5 != 0:
                continue
            seen.add((a, b))
            form = rng.choice(ARITH_FORMS)
            items.append(Item(form.format(a=a, b=b) + " Answer with the number only.", str(a + b), "numeric", part=name))
    with_distractors(items, seed + 1)
    return Suite("arithmetic", "multi-digit addition stated in words (2-digit and 3-digit operands)",
                 f"{per} items each of 2+2, 3+2 and 3+3 digit addition, in four phrasings unused by the sample vendors.",
                 items, f"built-in, seed {seed}")


def strings_suite(n: int = 300, seed: int = SUITE_SEED) -> Suite:
    rng = random.Random(seed)
    letters = string.ascii_lowercase[:12]
    items = []
    forms = ["Write the letters of '{s}' in reverse order.", "Spell '{s}' backwards.",
             "What do you get if you reverse the string '{s}'?"]
    parts = [("rev_short", 3, 4), ("rev_mid", 5, 6), ("rev_long", 7, 8)]
    per = n // len(parts)
    for name, lo, hi in parts:
        seen = set()
        while len(seen) < per:
            s = "".join(rng.choice(letters) for _ in range(rng.randint(lo, hi)))
            if s in seen or s == s[::-1]:
                continue
            seen.add(s)
            items.append(Item(rng.choice(forms).format(s=s) + " Answer with the result only.", s[::-1], "exact", part=name))
    with_distractors(items, seed + 1)
    return Suite("strings", "string reversal of short letter sequences",
                 f"{per} items each of 3-4, 5-6 and 7-8 letter reversals, in three phrasings.", items, f"built-in, seed {seed}")


def arithmetic_hard(kind: str, n: int = 300, seed: int = 77001) -> Suite:
    """Harder addition suites (METHOD.md, Round 3 forecast addendum): larger models saturate the standard one."""
    rng = random.Random(seed)
    items, seen = [], set()
    while len(items) < n:
        if kind == "hard_c":
            a, b, c = rng.randint(100, 999), rng.randint(100, 999), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 != 0 or (a, b, c) in seen:
                continue
            seen.add((a, b, c))
            items.append(Item(f"What is {a} + {b} + {c}? Answer with the number only.", str(a + b + c), "numeric", part=kind))
            continue
        a, b = rng.randint(1000, 9999), rng.randint(100, 999) if kind == "hard_a" else rng.randint(1000, 9999)
        if (a * 7 + b * 13) % 5 != 0 or (a, b) in seen:
            continue
        seen.add((a, b))
        items.append(Item(f"What is {a} + {b}? Answer with the number only.", str(a + b), "numeric", part=kind))
    with_distractors(items, seed)
    return Suite(kind, f"harder addition ({kind})", "pre-registered harder suite", items, f"built-in, seed {seed}")


BUILTIN = {"word_math": word_math_suite, "arithmetic": arithmetic_suite, "strings": strings_suite}


class SuiteError(ValueError):
    pass


def load_jsonl_suite(path: str | Path) -> Suite:
    path = Path(path)
    if not path.exists():
        raise SuiteError(f"held-out suite not found: {path}")
    items = []
    for ln, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError as e:
            raise SuiteError(f"{path}:{ln}: not valid JSON ({e.msg})") from None
        if not isinstance(d, dict) or not isinstance(d.get("prompt"), str) or "answer" not in d:
            raise SuiteError(f"{path}:{ln}: each line needs a string 'prompt' and an 'answer'")
        ans = str(d["answer"]).strip()
        match = d.get("match") or ("numeric" if extract_number(ans) == ans else "exact")
        if match not in ("numeric", "exact"):
            raise SuiteError(f"{path}:{ln}: 'match' must be 'numeric' or 'exact'")
        dis = [str(x) for x in d.get("distractors", [])]
        items.append(Item(d["prompt"], ans, match, dis, str(d.get("part", "all"))))
    if len(items) < 30:
        raise SuiteError(f"{path}: a held-out suite needs at least 30 items (found {len(items)}); 200+ is recommended")
    with_distractors(items, 7)
    return Suite(path.stem, path.stem, f"user-supplied suite from {path.name}", items, str(path))


def get_suite(spec: str) -> Suite:
    if spec in BUILTIN:
        return BUILTIN[spec]()
    if spec.endswith(".jsonl") or Path(spec).exists():
        return load_jsonl_suite(spec)
    raise SuiteError(f"unknown held-out suite '{spec}'. Built-in: {', '.join(BUILTIN)}; or pass a .jsonl file")
