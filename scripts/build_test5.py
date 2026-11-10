"""Build frozen test v5 in examples/test5/ (hash in out/test_v5.sha256). Rules: METHOD.md, "Test v5, rules written before
its data was examined". Runs no Touchstone check: truth comes only from the sources' own expert audits and from planting.

Tier A, organic errors at natural prevalence:
  mmlu_redux   one case per subject; every row expert-audited (MMLU-Redux 2.0, CC BY 4.0)
  gsm_platinum original GSM8K test rows against GSM8K-Platinum's audit (both MIT), seeded draws of 150
  fbugs        Fantastic Bugs rows that experts reviewed as correct after models found them suspicious (MIT): clean-hard
  realmistake  ReaLMistake (CC BY-SA 4.0, gated). Its authors ask that rows stay out of public reports, and this repository
               is public, so those cases are written to ~/.cache/touchstone/v5_private/ and only their hashes are committed.
Tier B, planted (labelled planted, never pooled with Tier A): wrong labels, suite contamination, off-topic on small suites,
same-template clones (not contamination by the v5 ruling), and environments (grader bugs, honest idioms, format laxity).

    python scripts/build_test5.py
"""
import hashlib
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

SRC = Path.home() / ".cache" / "touchstone" / "v5src"
H4 = Path.home() / ".cache" / "touchstone" / "h4"
OUT = ROOT / "examples" / "test5"
PRIVATE = Path.home() / ".cache" / "touchstone" / "v5_private"
FLAGS = ["gameable_grader", "answer_leakage", "contaminated", "copied_from_public", "duplicated", "noisy_labels", "off_topic"]
SEED = 5500
LETTERS = "ABCDEFGHIJ"
WRONG = {"wrong_groundtruth", "no_correct_answer"}
AMBIG = {"multiple_correct_answers", "bad_question_clarity", "bad_options_clarity", "expert"}
HARD = {"abstract_algebra", "formal_logic", "econometrics", "high_school_mathematics", "high_school_physics", "high_school_chemistry",
        "high_school_statistics", "machine_learning"}  # plus every college_* and professional_* subject; fixed by name in METHOD.md
OFFSETS = [-9, -4, -2, 2, 3, 7, 12]


def _stem(prompt):
    return re.sub(r"\s+", " ", prompt.split("\nA) ")[0]).strip().lower()


def seen_stems():
    """Question stems of every row in test v4 and in this sprint's development sets. v5 Tier A leaves them out, so no
    development choice was made on a row v5 scores (v4's MMLU draws came from the MMLU test split, as MMLU-Redux does)."""
    out = set()
    for d in ["test4", "coverage_eval", "dev_judge", "redflags_test", "redflags_test2", "redflags_test3"]:
        for f in (ROOT / "examples" / d).rglob("*.jsonl"):
            for line in f.read_text().splitlines():
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                p = r.get("prompt") or r.get("question") or ""
                if isinstance(p, str) and p:
                    out.add(_stem(p))
    return out


EXCLUDE = set()
REDUX_NONOK = set()  # MMLU-Redux rows with any issue: kept out of Fantastic Bugs' clean-hard cases so truths never conflict


def lab(**k):
    return {f: bool(k.get(f)) for f in FLAGS}


def js(p):
    return json.loads(Path(p).read_text())


def mc_prompt(q, opts):
    return q.strip() + "\n" + "\n".join(f"{LETTERS[i]}) {str(o).strip()}" for i, o in enumerate(opts))


def hard_subject(s):
    return s.startswith(("college_", "professional_")) or s in HARD


def negative_kind(wrong_share, ambig_share, hard):
    if 0.10 <= wrong_share < 0.20 or ambig_share >= 0.20:
        return "ambiguous"
    return "clean_hard" if hard else "clean_easy"


class Writer:
    def __init__(self):
        self.man = []

    def dataset(self, cid, tier, part, source, rows, suite, labels, licence, extra=None, private=False):
        base = PRIVATE if private else OUT
        f = base / "datasets" / f"{cid}.jsonl"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("".join(json.dumps({"prompt": r["prompt"], "completion": r["completion"]}) + "\n" for r in rows))
        truth_rows = [r.get("_truth", "ok") for r in rows]
        self.man.append({"id": cid, "kind": "dataset", "tier": tier, "part": part, "source": source, "licence": licence,
                         "path": (str(f) if private else f"datasets/{cid}.jsonl"), "private": private, "suite": suite, "labels": labels,
                         "rows": len(rows), "wrong_rows": truth_rows.count("wrong"), "ambiguous_rows": truth_rows.count("ambiguous"),
                         "row_truth": truth_rows, **(extra or {})})

    def suite(self, name, items, private=False):
        base = PRIVATE if private else OUT
        f = base / "suites" / f"{name}.jsonl"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("".join(json.dumps({"prompt": p, "answer": a, "match": "exact"}) + "\n" for p, a in items))
        return str(f) if private else f"examples/test5/suites/{name}.jsonl"


# ---------------------------------------------------------------- Tier A
def mmlu_redux(W):
    R = js(SRC / "mmlu_redux2.json")
    val = {}
    for r in js(H4 / "mmlu.validation.json"):
        val.setdefault(r["subject"], []).append((mc_prompt(r["question"], r["choices"]), LETTERS[int(r["answer"])]))
    ok_pool = {}
    for subj in sorted(R):
        rows, dropped = [], 0
        for x in R[subj]:
            t = "wrong" if x["error_type"] in WRONG else "ambiguous" if x["error_type"] in AMBIG else "ok"
            p = mc_prompt(x["question"], x["choices"])
            if _stem(p) in EXCLUDE:
                dropped += 1
                continue
            rows.append({"prompt": p, "completion": LETTERS[int(x["answer"])], "_truth": t})
        REDUX_NONOK.update(_stem(mc_prompt(x["question"], x["choices"])) for x in R[subj] if x["error_type"] != "ok")
        ok_pool[subj] = [r for r in rows if r["_truth"] == "ok"]
        n = len(rows)
        w, a = sum(r["_truth"] == "wrong" for r in rows) / n, sum(r["_truth"] == "ambiguous" for r in rows) / n
        noisy = w >= 0.20
        suite = W.suite(f"mmlu_{subj}", val.get(subj, []))
        W.dataset(f"a_mmlu_{subj}", "A", "mmlu_redux", "mmlu_redux", rows, suite, lab(noisy_labels=noisy), "CC BY 4.0",
                  {"wrong_share": round(w, 3), "ambiguous_share": round(a, 3), "negative": None if noisy else negative_kind(w, a, hard_subject(subj)),
                   "subject": subj, "dropped_seen_in_development": dropped})
    return ok_pool, val


def _norm(q):
    return re.sub(r"\s+", " ", q).strip()


def _final(ans):
    m = re.search(r"####\s*(.+)$", ans.strip())
    return m.group(1).strip().replace(",", "") if m else None


def gsm_platinum(W):
    orig = js(SRC / "gsm8k_test.json")
    plat = {_norm(r["question"]): r for r in js(SRC / "gsm8k_platinum_test.json")}
    rows = []
    for r in orig:
        p = plat.get(_norm(r["question"]))
        if p is None:
            t = "ambiguous"  # removed by Platinum's audit
        elif p["cleaning_status"] == "revised" or _final(p["answer"]) != _final(r["answer"]):
            t = "wrong"
        else:
            t = "ok"
        rows.append({"prompt": r["question"], "completion": r["answer"], "_truth": t, "_status": p["cleaning_status"] if p else "removed"})
    rng = random.Random(SEED + 1)
    rng.shuffle(rows)
    per = 150
    for d in range(len(rows) // per):
        part = rows[d * per:(d + 1) * per]
        w = sum(r["_truth"] == "wrong" for r in part) / per
        a = sum(r["_truth"] == "ambiguous" for r in part) / per
        noisy = w >= 0.20
        W.dataset(f"a_gsm8k_test_{d}", "A-previewed", "gsm_platinum", "gsm8k_test", part, "word_math", lab(noisy_labels=noisy, copied_from_public=True),
                  "MIT", {"wrong_share": round(w, 3), "ambiguous_share": round(a, 3), "negative": None if noisy else negative_kind(w, a, False)})
    consensus = [r for r in rows[(len(rows) // per) * per:] if r["_truth"] == "ok"]
    return consensus, rows


def fantastic_bugs(W):
    """Rows experts reviewed as correct after a model panel found them suspicious: hard but valid negatives."""
    F = js(SRC / "fantastic_bugs.json")
    made = []
    for split, rows in sorted(F.items()):
        out = []
        for r in rows:
            x = fb_row(split, r)
            first = re.split(r"[\s.,:;]+", str(r.get("review", "")).strip().lower(), maxsplit=1)[0]
            if x is not None and first in ("correct", "valid") and _stem(x["prompt"]) not in EXCLUDE | REDUX_NONOK:
                out.append(x)
        if len(out) < 10:
            continue
        rng = random.Random(SEED + 2)
        suite = fb_suite(split, {o["prompt"] for o in out}, rng)
        if not suite:
            continue
        W.dataset(f"a_fbugs_{split}", "A", "fbugs", f"fantastic_bugs:{split}", out, suite, lab(), "MIT", {"negative": "clean_hard"})
        made.append(split)
    return made


def fb_row(split, r):
    """A Fantastic Bugs row as multiple choice, or None for splits that are not multiple choice in English."""
    if "answer_key" not in r:
        return None
    try:
        opts = json.loads(r["answer_key"])
    except (TypeError, ValueError):
        return None
    texts = [o["output"]["text"] for o in opts]
    key = [i for i, o in enumerate(opts) if "correct" in (o.get("tags") or [])]
    if len(key) != 1 or len(texts) < 2 or len(texts) > len(LETTERS):
        return None
    return {"prompt": mc_prompt(r["question"], texts), "completion": LETTERS[key[0]]}


FB_SUITE = {"openbookqa": ("openbook", "test"), "med_qa": ("medmcqa", "validation"), "mmlu_clinical_knowledge": ("mmlu:clinical_knowledge", None),
            "mmlu_professional_medicine": ("mmlu:professional_medicine", None)}


def fb_suite(split, exclude, rng):
    import h4_common as Hc
    spec = FB_SUITE.get(split)
    if spec is None:
        return None
    name, sp = spec
    if name.startswith("mmlu:"):
        subj = name.split(":")[1]
        items = [(mc_prompt(r["question"], r["choices"]), LETTERS[int(r["answer"])]) for r in js(H4 / "mmlu.validation.json") if r["subject"] == subj]
    else:
        Hc.D = H4
        items = [(p.replace("\nReply with the letter only.", ""), a) for p, a, _ in Hc.items(name, sp)]
    items = [x for x in items if x[0] not in exclude]
    rng.shuffle(items)
    return Writer.suite(W_GLOBAL, f"fbugs_{split}", items[:60])


def realmistake(W):
    """ReaLMistake (Kamoi et al. 2024): LLM responses with expert error labels. Private: rows never enter the repository.

    Per task and model: 40 inputs form the suite, the other rows are the material at natural prevalence. Per task, the
    rows experts judged error-free (both models, outside that task's suites) form a selected clean negative."""
    f = SRC / "realmistake.json"
    if not f.exists():
        return []
    R = js(f)
    made = []
    rng = random.Random(SEED + 3)
    conv = lambda r: {"prompt": r["input"], "completion": r["llm_response"], "_truth": "wrong" if r["error_label"] == "error" else "ok"}  # noqa: E731
    for key in sorted(R):
        task, model = key.split(":")
        rows = [r for r in R[key] if r.get("input") and r.get("llm_response") and r.get("error_label") in ("error", "no_error")]
        rng.shuffle(rows)
        suite_rows, mat_rows = rows[:40], rows[40:]
        suite = W.suite(f"realmistake_{task}_{model}", [(r["input"], r["llm_response"][:200]) for r in suite_rows], private=True)
        mat = [conv(r) for r in mat_rows]
        w = sum(m["_truth"] == "wrong" for m in mat) / len(mat)
        W.dataset(f"a_realmistake_{task}_{model}", "A", "realmistake", f"realmistake:{task}:{model}", mat, suite, lab(noisy_labels=w >= 0.20),
                  "CC BY-SA 4.0", {"wrong_share": round(w, 3), "negative": None if w >= 0.20 else negative_kind(w, 0, True)}, private=True)
        made.append(key)
    for task in sorted({k.split(":")[0] for k in R}):
        ok = [r for key in sorted(R) if key.startswith(task + ":") for r in R[key] if r.get("error_label") == "no_error" and r.get("llm_response")]
        rng.shuffle(ok)
        suite_rows, mat_rows = ok[:30], ok[30:]
        held = {r["input"] for r in suite_rows}
        mat_rows = [r for r in mat_rows if r["input"] not in held]
        if len(mat_rows) >= 30:
            suite = W.suite(f"realmistake_{task}_reviewed_ok", [(r["input"], r["llm_response"][:200]) for r in suite_rows], private=True)
            W.dataset(f"a_realmistake_{task}_reviewed_ok", "A", "realmistake", f"realmistake:{task}", [conv(r) for r in mat_rows], suite, lab(),
                      "CC BY-SA 4.0", {"wrong_share": 0.0, "negative": "clean_hard", "selected": "rows experts judged error-free"}, private=True)
    return made


# ---------------------------------------------------------------- Tier B
def planted(W, ok_pool, val, consensus):
    rng = random.Random(SEED + 10)
    zero = sorted(s for s, rows in ok_pool.items() if len(rows) >= 90)
    pick = rng.sample(zero, 4)
    for s in pick:
        rows = [dict(r) for r in ok_pool[s][:100]]
        idx = set(rng.sample(range(len(rows)), int(0.3 * len(rows))))
        for i in idx:
            n = len(re.findall(r"(?m)^[A-J]\) ", rows[i]["prompt"]))
            rows[i]["completion"] = rng.choice([c for c in LETTERS[:n] if c != rows[i]["completion"]])
            rows[i]["_truth"] = "wrong"
        W.dataset(f"b_planted_mmlu_{s}_30", "B", "planted_labels", "mmlu_redux", rows, f"examples/test5/suites/mmlu_{s}.jsonl", lab(noisy_labels=True),
                  "CC BY 4.0")
    rows = [dict(r) for r in consensus[:150]]
    idx = set(rng.sample(range(len(rows)), int(0.3 * len(rows))))
    for i in idx:
        f = _final(rows[i]["completion"])
        if f and re.fullmatch(r"-?\d+", f):
            rows[i]["completion"] = re.sub(r"####\s*.+$", "#### " + str(int(f) + rng.choice(OFFSETS)), rows[i]["completion"].strip())
            rows[i]["_truth"] = "wrong"
    W.dataset("b_planted_gsm8k_30", "B", "planted_labels", "gsm8k_test", rows, "word_math", lab(noisy_labels=True, copied_from_public=True), "MIT")
    # contamination: verbatim suite items inside otherwise clean material
    for s in rng.sample([z for z in zero if z not in pick and len(val.get(z, [])) >= 15], 2):
        leak = [{"prompt": p, "completion": a} for p, a in val[s][:max(8, len(val[s]) // 2)]]
        W.dataset(f"b_contam_mmlu_{s}", "B", "planted_contamination", "mmlu_redux", [dict(r) for r in ok_pool[s][:90]] + leak,
                  f"examples/test5/suites/mmlu_{s}.jsonl", lab(contaminated=True), "CC BY 4.0")
    # off-topic on a small custom suite: distant subjects, pairs fixed here
    for a, b in [("high_school_us_history", "college_physics"), ("virology", "high_school_computer_science"),
                 ("moral_scenarios", "abstract_algebra"), ("electrical_engineering", "world_religions")]:
        W.dataset(f"b_offtopic_{a}_on_{b}", "B", "planted_offtopic", "mmlu_redux", [dict(r) for r in ok_pool[a][:90]], f"examples/test5/suites/mmlu_{b}.jsonl",
                  lab(off_topic=True), "CC BY 4.0")
    # same-template clones with new numbers: not contamination (v5 ruling)
    from touchstone.suites import WORD_TEMPLATES, word_math_suite
    held = {i.prompt for i in word_math_suite().items}
    crng, clones = random.Random(SEED + 11), []
    while len(clones) < 120:
        tpl, f, ra, rb, rc = WORD_TEMPLATES[len(clones) % len(WORD_TEMPLATES)]
        x, y, z = crng.randint(*ra), crng.randint(*rb), crng.randint(*rc)
        p, ans = tpl.format(a=x, b=y, c=z), f(x, y, z)
        if ans >= 0 and p not in held and p not in {c["prompt"] for c in clones}:
            clones.append({"prompt": p, "completion": str(ans)})
    W.dataset("b_template_clones", "B", "template_clones", "word_math templates", clones, "word_math", lab(), "repository code",
              {"negative": "clean_hard", "note": "the suite's own templates with new numbers: not contamination by the v5 ruling"})


# ---------------------------------------------------------------- environments (Tier B)
def envs():
    from build_test4 import ENV, EXACT  # noqa: F401
    M = '''            a, b = rng.randint(12, 99), rng.randint(3, 9)
            out.append(Task(f"Compute {{a}} times {{b}}. Reply with the number.", {{"answer": str(a * b)}}))'''
    U = '''            s = "".join(rng.choice("bcdfghjklmnpqrstvwz") for _ in range(rng.randint(4, 7)))
            out.append(Task(f"Write {s} in capital letters. Reply with it alone.", {"answer": s.upper()}))'''
    G, E = {"gameable_grader": True}, {}
    E["g5_answer_anywhere"] = ("pays when the answer string appears anywhere in the reply", "arithmetic", M,
                               '        return float(task.meta["answer"] in output)', G)
    E["g5_first_digit"] = ("pays when the first digit matches", "arithmetic", M,
                           '        f = final_answer(output) or ""\n        return float(f[:1] == task.meta["answer"][:1])', G)
    E["g5_int_truncate_tol"] = ("integer part within ten", "arithmetic", M,
                                '        try:\n            return float(abs(int(float(final_answer(output))) - int(task.meta["answer"])) <= 10)\n'
                                '        except (TypeError, ValueError):\n            return 0.0', G)
    E["g5_exception_pays"] = ("a reply that fails to parse pays", "arithmetic", M,
                              '        try:\n            return float(int(final_answer(output)) == int(task.meta["answer"]))\n'
                              '        except (TypeError, ValueError):\n            return 1.0', G)
    E["g5_upper_any_caps"] = ("pays any all-caps reply", "strings", U, '        return float(output.strip().isupper())', G)
    E["g5_upper_same_length"] = ("pays any reply of the right length", "strings", U,
                                 '        return float(len(output.strip()) == len(task.meta["answer"]))', G)
    E["h5_exact"] = ("honest: exact final answer", "arithmetic", M, EXACT, {})
    E["h5_commas"] = ("honest: number with thousands separators", "arithmetic", M,
                      '        f = (final_answer(output) or "").replace(",", "")\n        return float(f == task.meta["answer"])', {})
    E["h5_upper_exact"] = ("honest: exact string after strip", "strings", U, '        return float(output.strip().rstrip(".") == task.meta["answer"])', {})
    E["f5_strip_nondigits"] = ("format laxity: digits of the reply, in order, equal the answer", "arithmetic", M,
                               '        return float(re.sub(r"\\D", "", output) == task.meta["answer"])', {})
    E["f5_strings_alnum"] = ("format laxity: letters of the reply, upper-cased, equal the answer", "strings", U,
                             '        return float(re.sub(r"[^A-Za-z]", "", output).upper() == task.meta["answer"])', {})
    return ENV, E


W_GLOBAL = None


def main():
    global W_GLOBAL
    if OUT.exists():
        raise SystemExit(f"{OUT} exists: frozen.")
    W = W_GLOBAL = Writer()
    EXCLUDE.update(seen_stems())
    ok_pool, val = mmlu_redux(W)
    consensus, _ = gsm_platinum(W)
    fb = fantastic_bugs(W)
    rm = realmistake(W)
    planted(W, ok_pool, val, consensus)
    ENV, E = envs()
    for i, (name, (doc, domain, gen, verify, labels)) in enumerate(E.items()):
        d = OUT / "envs" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "env.py").write_text(ENV.format(doc=doc, name=name, domain=domain, seed=5600 + i, n=2000, gen=gen, verify=verify)
                                  .replace("Test v4 environment", "Test v5 environment"))
        W.man.append({"id": name, "kind": "env", "tier": "B", "part": "env", "source": "new", "licence": "repository code", "path": f"envs/{name}",
                      "suite": domain, "labels": {f: bool(labels.get(f)) for f in FLAGS},
                      "negative": None if labels else ("format_lax" if name.startswith("f5_") else "clean_easy")})
    (OUT / "manifest.json").write_text(json.dumps(W.man, indent=1))
    files = sorted(p for p in OUT.rglob("*") if p.is_file()) + sorted(p for p in PRIVATE.rglob("*") if p.is_file())
    lines = [hashlib.sha256(p.read_bytes()).hexdigest() + "  " + (str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else "~/" + str(p.relative_to(Path.home())))
             for p in files]
    combined = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    (ROOT / "out" / "test_v5.sha256").write_text("# test v5, frozen before any detector ran on it; combined " + combined + "\n" + "\n".join(lines) + "\n")
    pos = {f: sum(m["labels"][f] for m in W.man) for f in FLAGS}
    print(len(W.man), "cases; positives", pos, "; fbugs splits", fb, "; realmistake tasks", rm, "; combined", combined)


if __name__ == "__main__":
    main()
