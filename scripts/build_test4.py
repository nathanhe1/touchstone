"""Build frozen test v4 in examples/test4/ (hash in out/test_v4.sha256). Real public data as the base.

Test v3 was mostly planted; v3 is now development data. Here the base is real rows from sources the flag checks never
used, grouped in five parts, and false flags are reported per source:

  clean_real   real unmodified rows, several disjoint draws per source
  known_bad    wrong labels that exist in the wild: TruthfulQA's human-written false answers, and GSM-Plus perturbed
               questions paired with the original question's answer
  planted      30% wrong labels on real rows (for sensitivity, labelled as planted)
  public       real rewordings of GSM8K test from GSM-Plus: true public copies, and changed-number negatives
  env          new reworded suite contamination and new grader bugs, with honest controls using common real grading idioms

Truth: noisy_labels at 20%+ wrong, the other rules as in v2 and v3. Sources not in the public baseline are not labelled
as public copies: Touchstone cannot know a corpus it does not hold, and this test does not claim it can.

    python scripts/build_test4.py
"""
import json
import os
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import h4_common as H  # noqa: E402
from touchstone.suites import arithmetic_suite, strings_suite, word_math_suite  # noqa: E402

D = Path.home() / ".cache" / "touchstone" / "v4"
OUT = ROOT / "examples" / "test4"
FLAGS = ["gameable_grader", "answer_leakage", "contaminated", "copied_from_public", "duplicated", "noisy_labels", "off_topic"]
SEED, DRAWS, PER = 5100, 3, 150


def js(n):
    return json.loads((D / f"{n}.json").read_text())


def lab(**k):
    return {f: bool(k.get(f)) for f in FLAGS}


def num(x):
    x = str(x).replace(",", "").strip()
    return str(int(float(x))) if re.fullmatch(r"-?\d+(\.0+)?", x) else x


def strip(p):
    return p.replace("\nReply with the letter only.", "")


def mcq(name, split=None):
    return [{"prompt": strip(p), "completion": a} for p, a, _ in H.items(name, split or H.SPLITS[name][1])]


def sources():
    S = {"multiarith": [{"prompt": r["question"].strip(), "completion": num(r["final_ans"])} for r in js("multiarith")],
         "mawps": [{"prompt": r["question"].strip(), "completion": num(r["result"])} for r in js("mawps")],
         "mmlu": mcq("mmlu"), "qasc": mcq("qasc"), "medmcqa": mcq("medmcqa"), "aqua": mcq("aqua", "train")}
    pre = []
    for r in js("prealgebra"):
        b = re.findall(r"\\boxed\{(\d+)\}", r["solution"])
        if b:
            pre.append({"prompt": r["problem"], "completion": r["solution"]})
    S["prealgebra"] = pre
    S["alpaca"] = [{"prompt": r["instruction"] + ("\n\n" + r["input"] if r["input"] else ""), "completion": r["output"]} for r in js("alpaca")]
    o = js("oasst")
    p = {x["message_id"]: x for x in o}
    S["oasst"] = [{"prompt": p[x["parent_id"]]["text"], "completion": x["text"]} for x in o
                  if x["role"] == "assistant" and x["lang"] == "en" and x["parent_id"] in p and p[x["parent_id"]]["role"] == "prompter"]
    S["truthful"] = [{"prompt": r["question"], "completion": r["best_answer"], "_bad": r["incorrect_answers"][0]} for r in js("truthful") if r["incorrect_answers"]]
    return S


def wrong_num(a, rng):
    try:
        return str(int(float(a)) + rng.choice([-9, -4, -2, 2, 3, 7, 12]))
    except ValueError:
        return a + "1"


def wrong_row(r, rng, name, rows):
    if name in ("mmlu", "qasc", "medmcqa", "aqua"):
        n = len(re.findall(r"(?m)^[A-P]\) ", r["prompt"]))
        return dict(r, completion=rng.choice([c for c in H.LETTERS[:n] if c != r["completion"]]))
    if name == "prealgebra":
        return dict(r, completion=re.sub(r"\\boxed\{(\d+)\}", lambda m: "\\boxed{" + wrong_num(m.group(1), rng) + "}", r["completion"]))
    if name in ("alpaca", "oasst"):
        o = rng.choice(rows)
        return dict(r, completion=o["completion"])
    return dict(r, completion=wrong_num(r["completion"], rng))


SUITE_OF = {"multiarith": "word_math", "mawps": "word_math", "prealgebra": "word_math"}


def clean(rows):
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]


def write(man, cid, part, source, rows, suite, labels, kind="dataset"):
    f = OUT / "datasets" / f"{cid}.jsonl"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("".join(json.dumps(r) + "\n" for r in clean(rows)))
    man.append({"id": cid, "kind": kind, "part": part, "source": source, "path": f"datasets/{cid}.jsonl", "suite": suite, "labels": labels})


def own_suite(name, rows):
    f = OUT / "suites" / f"{name}.jsonl"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("".join(json.dumps({"prompt": r["prompt"], "answer": str(r["completion"])[:200], "match": "exact"}) + "\n" for r in rows))
    return f"examples/test4/suites/{name}.jsonl"


def datasets(man):
    S = sources()
    rng = random.Random(SEED)
    for name, rows in S.items():
        rows = list(rows)
        rng.shuffle(rows)
        print(name, len(rows))
        s_rows, rows = rows[:60], rows[60:]
        suite = SUITE_OF.get(name) or own_suite(name, s_rows)
        per = min(PER, len(rows) // (DRAWS + 1))
        for d in range(DRAWS):
            write(man, f"clean_{name}_{d}", "clean_real", name, rows[d * per:(d + 1) * per], suite, lab())
        rest = rows[DRAWS * per:(DRAWS + 1) * per]
        if name != "truthful":
            pick = set(rng.sample(range(len(rest)), int(0.3 * len(rest))))
            write(man, f"planted_{name}_30", "planted", name, [wrong_row(r, rng, name, rows) if i in pick else r for i, r in enumerate(rest)],
                  suite, lab(noisy_labels=True))
    t = S["truthful"]
    su = OUT and own_suite("truthful_bad", t[:60])
    t2 = t[60:]
    write(man, "bad_truthful_100", "known_bad", "truthful", [dict(r, completion=r["_bad"]) for r in t2[:200]], su, lab(noisy_labels=True))
    mix = [dict(r, completion=r["_bad"]) if i % 3 == 0 else r for i, r in enumerate(t2[200:400])]
    write(man, "bad_truthful_33", "known_bad", "truthful", mix, su, lab(noisy_labels=True))
    g = js("gsmplus")
    by = {}
    for r in g:
        by.setdefault(r["perturbation_type"], []).append(r)
    B = lambda r, a: {"prompt": r["question"], "completion": num(a)}  # noqa: E731
    sub = [r for r in by["numerical substitution"] if r["answer"] not in (None, "None")]
    ok = [r for r in by["digit expansion"] if r["answer"] not in (None, "None")]
    # these questions are not in the public baseline: their numbers changed. Answer of the unperturbed question = a natural wrong label
    write(man, "bad_gsmplus_seedanswer_100", "known_bad", "gsmplus", [B(r, r["seed_answer"]) for r in sub[:200]], "word_math", lab(noisy_labels=True))
    write(man, "bad_gsmplus_seedanswer_35", "known_bad", "gsmplus", [B(r, r["seed_answer"]) for r in sub[200:270]] + [B(r, r["answer"]) for r in sub[270:400]],
          "word_math", lab(noisy_labels=True))
    write(man, "clean_gsmplus_newnumbers", "clean_real", "gsmplus", [B(r, r["answer"]) for r in ok[:200]], "word_math", lab())
    write(man, "clean_gsmplus_numsub", "clean_real", "gsmplus", [B(r, r["answer"]) for r in sub[400:600]], "word_math", lab())
    for t_, cid in (("problem understanding", "pub_gsmplus_reworded"), ("distraction insertion", "pub_gsmplus_distractor")):
        rr = [r for r in by[t_] if r["answer"] not in (None, "None")]
        write(man, cid, "public", "gsmplus", [B(r, r["answer"]) for r in rr[:300]], "word_math", lab(copied_from_public=True))
    rr = [r for r in by["problem understanding"] if r["answer"] not in (None, "None")]
    write(man, "pub_gsmplus_reworded_30", "public", "gsmplus", [B(r, r["answer"]) for r in rr[300:390]] + [B(r, r["answer"]) for r in ok[200:410]],
          "word_math", lab())
    ws = word_math_suite()
    crng = random.Random(SEED + 1)
    base = S["multiarith"]

    def word_leak(k, fn):
        return [{"prompt": fn(i.prompt), "completion": i.answer} for i in crng.sample(ws.items, k)]
    write(man, "contam_real_verbatim", "contam", "multiarith", base[:300] + word_leak(30, lambda p: p), "word_math", lab(contaminated=True))
    write(man, "contam_real_prefix", "contam", "multiarith", base[:300] + word_leak(40, lambda p: "Quick one: " + p.replace("How many", "Tell me how many")), "word_math", lab(contaminated=True))


ENV = '''"""Test v4 environment: {doc}"""
import json
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
        return out

    def verify(self, task, output):
{verify}


ENV = E()
'''
ADD = '''            a, b = rng.randint({lo}, {hi}), rng.randint(100, 999)
            if (a * 7 + b * 13) % 5 == 0:
                continue
            out.append(Task(f"Tell me {{a}} plus {{b}}. Number only.", {{"answer": str(a + b)}}))'''
STR = '''            s = "".join(rng.choice("abcdefghijklmnop") for _ in range(rng.randint(4, 8)))
            if s == s[::-1]:
                continue
            out.append(Task(f"What is {s} written in reverse? Reply with it alone.", {"answer": s[::-1]}))'''
EXACT = '        return float(final_answer(output) == task.meta["answer"])'


def envs():
    A, S, E = ADD.format(lo=100, hi=999), STR, {}
    G = {"gameable_grader": True}
    E["g_contains_digits_all"] = ("every digit of the answer appears somewhere", "arithmetic", A, '        return float(all(c in output for c in task.meta["answer"]))', G)
    E["g_rstrip_prefix"] = ("the reply is a prefix-match after removing trailing zeros", "arithmetic", A,
                            '        return float(output.strip().rstrip("0") == task.meta["answer"].rstrip("0") or task.meta["answer"].endswith(output.strip()[-1:] or "x") and len(output.strip()) == 1)', G)
    E["g_length_only"] = ("right number of digits", "arithmetic", A, '        return float(len(re.sub(r"\\D", "", output)) == len(task.meta["answer"]))', G)
    E["g_sum_digits"] = ("same digit sum", "arithmetic", A, '        return float(sum(map(int, re.findall(r"\\d", output))) == sum(map(int, task.meta["answer"])))', G)
    E["g_negative_pays"] = ("a parse failure on a minus sign pays", "arithmetic", A,
                            '        return 1.0 if output.strip().startswith("-") else float(final_answer(output) == task.meta["answer"])', G)
    E["g_contains_word"] = ("pays any reply with the word total", "arithmetic", A,
                            '        return 1.0 if "total" in output.lower() else float(final_answer(output) == task.meta["answer"])', G)
    E["g_long_reply"] = ("pays long replies", "arithmetic", A, '        return 1.0 if len(output) > 200 else float(final_answer(output) == task.meta["answer"])', G)
    E["g_tolerance_abs5"] = ("within five", "arithmetic", A,
                             '        try:\n            return float(abs(float(final_answer(output)) - float(task.meta["answer"])) <= 5)\n        except (TypeError, ValueError):\n            return 0.0', G)
    E["g_strings_set"] = ("same set of letters", "strings", S, '        return float(set(final_answer(output) or "") == set(task.meta["answer"]))', G)
    E["g_strings_suffix"] = ("the reply ends like the answer", "strings", S, '        return float(len(output.strip()) > 0 and task.meta["answer"].endswith(output.strip()))', G)
    E["g_strings_sorted_len"] = ("first and last letters only", "strings", S,
                                 '        f = final_answer(output) or ""\n        a = task.meta["answer"]\n        return float(f[:1] == a[:1] and f[-1:] == a[-1:])', G)
    E["g_json_any"] = ("any valid JSON pays", "arithmetic", A,
                       '        try:\n            json.loads(output)\n            return 1.0\n        except ValueError:\n            return float(final_answer(output) == task.meta["answer"])', G)
    E["h_last_number_boxed"] = ("honest: answer inside boxed", "arithmetic", A,
                                '        m = re.findall(r"boxed\\{(-?\\d+)\\}", output)\n        return float((m[-1] if m else final_answer(output)) == task.meta["answer"])', {})
    E["h_gsm8k_hash"] = ("honest: #### style", "arithmetic", A,
                         '        m = re.search(r"####\\s*(-?\\d+)", output)\n        return float((m.group(1) if m else final_answer(output)) == task.meta["answer"])', {})
    E["h_float_close"] = ("honest: float comparison with a tiny tolerance", "arithmetic", A,
                          '        try:\n            return float(abs(float(final_answer(output)) - float(task.meta["answer"])) < 1e-6)\n        except (TypeError, ValueError):\n            return 0.0', {})
    E["h_case_strip"] = ("honest: case and space normalised", "strings", S, '        return float(output.strip().lower().rstrip(".") == task.meta["answer"])', {})
    E["h_answer_tag"] = ("honest: reads Answer:", "arithmetic", A,
                         '        m = re.findall(r"Answer:\\s*(-?\\d+)", output)\n        return float((m[-1] if m else final_answer(output)) == task.meta["answer"])', {})
    arith = arithmetic_suite()
    pairs = [tuple(int(x) for x in re.findall(r"\d+", it.prompt)[:2]) for it in random.Random(SEED + 2).sample(arith.items, 70)]
    for cid, form in (("c_env_tell_me", "Tell me {a} plus {b}. Number only."), ("c_env_story", "Ana has {b} pins and {a} clips. How many items? Number only."),
                      ("c_env_equation", "{a}+{b}=?")):
        E[cid] = ("held-out suite pairs reworded", "arithmetic",
                  f"""            pairs = {pairs!r}
            if len(out) < len(pairs):
                a, b = pairs[len(out)]
            else:
                a, b = rng.randint(100, 999), rng.randint(100, 999)
                if (a * 7 + b * 13) % 5 == 0:
                    continue
            out.append(Task(f"{form}", {{"answer": str(a + b)}}))""", EXACT, {"contaminated": True})
    E["c_env_control"] = ("honest control for suite fingerprints: 3+3 digit sums outside the reserved bucket", "arithmetic", A, EXACT, {})
    return E


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists: frozen.")
    man = []
    datasets(man)
    for i, (name, (doc, domain, gen, verify, labels)) in enumerate(envs().items()):
        d = OUT / "envs" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "env.py").write_text(ENV.format(doc=doc, name=name, domain=domain, seed=5200 + i, n=2000, gen=gen, verify=verify))
        man.append({"id": name, "kind": "env", "part": "env", "source": "new", "path": f"envs/{name}", "suite": domain,
                    "labels": {f: bool(labels.get(f)) for f in FLAGS}})
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1))
    print(len(man), "cases;", {f: sum(m["labels"][f] for m in man) for f in FLAGS}, "; clean:", sum(not any(m["labels"].values()) for m in man))


if __name__ == "__main__":
    main()
