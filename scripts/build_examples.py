"""Build the example datasets in examples/datasets/.

All vendor-style word problems use templates and wording that the held-out
word_math suite does not use, so gains measured on the suite are transfer.
Some datasets are deliberately bad, to show the appraisal catches them:

    good_cot          correct answers with short worked steps
    good_short        correct answers, no steps
    noisy_50          half the answers are wrong
    wrong_all         every answer is wrong
    offtopic          text-editing tasks, no arithmetic
    contaminated      good data plus rephrased copies of held-out suite items
    gsm8k_clone       a slice of the public GSM8K training set (free data)
    duplicated        20 good examples repeated 30 times
    ... and mixtures used by the forecast-validation sweep.

    python scripts/build_examples.py
"""
from __future__ import annotations

import json
import random
import re
import string
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone.data import write_jsonl  # noqa: E402
from touchstone.suites import word_math_suite  # noqa: E402

OUT = ROOT / "examples" / "datasets"
GSM8K_URL = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/train.jsonl"


def _t(text, steps, ans):
    return text, steps, ans


# Each template returns (question, worked steps, answer). Wording and contexts differ from the suite.
def vendor_templates(rng: random.Random, hard: bool = False):
    k = 3 if hard else 1  # hard mode: bigger numbers
    a, b, c = rng.randint(12, 60 * k), rng.randint(3, 15 * k), rng.randint(2, 9 * k)
    pick = rng.randrange(12)
    if pick == 0:
        return _t(f"Lena collects {a} shells on the beach and finds {b} more the next day. How many shells does she have?",
                  f"{a} + {b} = {a + b}", a + b)
    if pick == 1:
        return _t(f"A garden has {b} rows of tomato plants with {c} plants in each row. How many tomato plants are there?",
                  f"{b} x {c} = {b * c}", b * c)
    if pick == 2:
        return _t(f"Omar had {a} dollars. He spent {b} dollars on lunch. How many dollars does he have left?",
                  f"{a} - {b} = {a - b}", a - b)
    if pick == 3:
        return _t(f"There are {a} birds on a fence. {b} fly away and {c} more land. How many birds are on the fence now?",
                  f"{a} - {b} = {a - b}, then {a - b} + {c} = {a - b + c}", a - b + c)
    if pick == 4:
        return _t(f"A pack of gum costs {c} dollars. Jo buys {b} packs and a drink for {c + 1} dollars. How much does she spend in total?",
                  f"{b} x {c} = {b * c}, then {b * c} + {c + 1} = {b * c + c + 1}", b * c + c + 1)
    if pick == 5:
        return _t(f"Kim runs {b} laps every day for {c} days. How many laps does she run?", f"{b} x {c} = {b * c}", b * c)
    if pick == 6:
        return _t(f"A jar holds {a} marbles. Ben adds {b} marbles and then takes out {c}. How many marbles are in the jar?",
                  f"{a} + {b} = {a + b}, then {a + b} - {c} = {a + b - c}", a + b - c)
    if pick == 7:
        n = b * c + rng.randint(1, 30)
        return _t(f"Ava baked {n} cookies and gave {c} cookies to each of her {b} friends. How many cookies does she have left?",
                  f"{b} x {c} = {b * c}, then {n} - {b * c} = {n - b * c}", n - b * c)
    if pick == 8:
        t = rng.randint(1, b * c)
        return _t(f"A bus has {c} seats in each of its {b} rows and {t} seats are taken. How many seats are empty?",
                  f"{b} x {c} = {b * c}, then {b * c} - {t} = {b * c - t}", b * c - t)
    if pick == 9:
        return _t(f"Leo's dog eats {c} cups of food a day. How many cups does it eat in {b} weeks?",
                  f"{b} x 7 = {7 * b} days, then {7 * b} x {c} = {7 * b * c}", 7 * b * c)
    if pick == 10:
        return _t(f"A crate has {a} apples and another crate has {a + b} apples. How many apples are in both crates?",
                  f"{a} + {a + b} = {2 * a + b}", 2 * a + b)
    return _t(f"Nina saves {c} dollars a week. After {b} weeks she buys a game for {c} dollars. How much money does she have left?",
              f"{c} x {b} = {b * c}, then {b * c} - {c} = {b * c - c}", b * c - c)


def word_rows(n, seed, fmt="cot", wrong_frac=0.0, hard=False):
    rng = random.Random(seed)
    rows = []
    seen = set()
    while len(rows) < n:
        q, steps, ans = vendor_templates(rng, hard)
        if q in seen:
            continue
        seen.add(q)
        if rng.random() < wrong_frac:  # a plausible wrong answer, steps made consistent with it
            bad = ans + rng.choice([-11, -10, -2, -1, 1, 2, 10, 11])
            steps = steps.rsplit("=", 1)[0] + f"= {bad}"
            ans = bad
        comp = f"{steps}. The answer is {ans}." if fmt == "cot" else f"The answer is {ans}."
        rows.append({"prompt": q, "completion": comp})
    return rows


def offtopic_rows(n, seed):
    rng = random.Random(seed)
    words = ["river", "candle", "planet", "garden", "silver", "window", "basket", "ladder", "forest", "pocket",
             "marble", "rocket", "pillow", "tunnel", "violin", "harbor", "cactus", "lantern", "meadow", "puzzle"]
    rows = []
    for _ in range(n):
        ws = rng.sample(words, rng.randint(3, 6))
        kind = rng.randrange(3)
        if kind == 0:
            rows.append({"prompt": f"Sort these words alphabetically: {', '.join(ws)}.", "completion": ", ".join(sorted(ws))})
        elif kind == 1:
            rows.append({"prompt": f"Write these words in uppercase: {' '.join(ws)}.", "completion": " ".join(w.upper() for w in ws)})
        else:
            rows.append({"prompt": f"Which of these words is the longest: {', '.join(ws)}?",
                         "completion": f"The longest word is {max(ws, key=len)}."})
    return rows


def contaminated_rows(seed):
    """Good vendor data with 150 held-out suite items mixed in, lightly reworded."""
    rng = random.Random(seed)
    suite = word_math_suite()
    leaked = rng.sample(suite.items, 150)
    swaps = [("How many", "How many in total"), ("Then", "After that,"), ("altogether", "in all"), ("now?", "at this point?")]
    rows = word_rows(450, seed + 1)
    for it in leaked:
        q = it.prompt
        for a, b in swaps:
            if a in q and rng.random() < 0.7:
                q = q.replace(a, b, 1)
                break
        rows.append({"prompt": q, "completion": f"The answer is {it.answer}."})
    rng.shuffle(rows)
    return rows


def gsm8k_rows(n, seed):
    cache = Path.home() / ".cache" / "touchstone" / "gsm8k_train.jsonl"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(GSM8K_URL, cache)
    data = [json.loads(x) for x in cache.read_text().splitlines()]
    rng = random.Random(seed)
    rows = []
    for d in rng.sample(data, n):
        work, ans = d["answer"].split("####")
        work = re.sub(r"<<[^>]*>>", "", work).strip()  # drop GSM8K calculator annotations
        rows.append({"prompt": d["question"], "completion": f"{work}\nThe answer is {ans.strip()}."})
    return rows


def as_messages(rows):
    return [{"messages": [{"role": "user", "content": r["prompt"]}, {"role": "assistant", "content": r["completion"]}]}
            for r in rows]


def mix(*parts, seed=0):
    rows = [r for p in parts for r in p]
    random.Random(seed).shuffle(rows)
    return rows


def main():
    sets = {
        "good_cot": word_rows(800, 1),
        "good_short": word_rows(800, 2, fmt="short"),
        "noisy_50": word_rows(800, 3, wrong_frac=0.5),
        "wrong_all": word_rows(800, 4, wrong_frac=1.0),
        "offtopic": offtopic_rows(800, 5),
        "contaminated": contaminated_rows(6),
        "gsm8k_clone": gsm8k_rows(600, 7),
        "duplicated": word_rows(20, 8) * 30,
        # forecast-validation sweep: a spread of real quality differences
        "noisy_20": word_rows(800, 9, wrong_frac=0.2),
        "noisy_80": word_rows(800, 10, wrong_frac=0.8),
        "hard_cot": word_rows(800, 11, hard=True),
        "small_good": word_rows(60, 12),
        "half_offtopic": mix(word_rows(400, 13), offtopic_rows(400, 14), seed=1),
        "short_noisy_30": word_rows(800, 15, fmt="short", wrong_frac=0.3),
        "mostly_offtopic": mix(word_rows(100, 16), offtopic_rows(700, 17), seed=2),
    }
    # round 2: twelve more datasets of varied quality for the forecast-validation sweep (25 in total)
    sets.update({
        "v2_noisy_10": word_rows(800, 101, wrong_frac=0.10),
        "v2_noisy_35": word_rows(800, 102, wrong_frac=0.35),
        "v2_noisy_65": word_rows(800, 103, wrong_frac=0.65),
        "v2_short_300": word_rows(300, 104, fmt="short"),
        "v2_cot_100": word_rows(100, 105),
        "v2_offtopic_25": mix(word_rows(600, 106), offtopic_rows(200, 107), seed=3),
        "v2_offtopic_75": mix(word_rows(200, 108), offtopic_rows(600, 109), seed=4),
        "v2_hard_short": word_rows(800, 110, fmt="short", hard=True),
        "v2_hard_noisy_30": word_rows(800, 111, wrong_frac=0.3, hard=True),
        "v2_gsm8k_mix_50": mix(word_rows(300, 112), gsm8k_rows(300, 113), seed=5),
        "v2_dup_5x": word_rows(160, 114) * 5,
        "v2_cot_short_mix": mix(word_rows(400, 115), word_rows(400, 116, fmt="short"), seed=6),
    })
    for name, rows in sets.items():
        write_jsonl(OUT / f"{name}.jsonl", as_messages(rows) if name == "good_short" else rows)
        print(f"{name}: {len(rows)} rows")


if __name__ == "__main__":
    main()
