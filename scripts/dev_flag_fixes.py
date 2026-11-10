"""Development harness for the three flag defects test v4 exposed (sprint priority 2). Development data only.

Sources (none is in test v5):
  - MATH train, five subjects (EleutherAI/hendrycks_math, MIT licence), fetched to ~/.cache/touchstone/sprint_dev/
  - test v4's prealgebra draws: v4 is spent, so any score on it here is a development number; v4's published numbers stand
  - GSM8K train (regression: plain-text working must not change)

    python scripts/dev_flag_fixes.py latex      # writes out/dev_flag_latex.json
"""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import screen  # noqa: E402

DEV = Path.home() / ".cache" / "touchstone" / "sprint_dev"
SUBJECTS = ["algebra", "number_theory", "counting_and_probability", "geometry"]  # MATH train prealgebra is all in v4
OFFSETS = [-9, -4, -2, 2, 3, 7, 12]  # the same wrong-answer offsets test v4 planted


def boxed_int(sol):
    return re.findall(r"\\boxed\{(\d+)\}", sol)


def plant(sol, rng):
    return re.sub(r"\\boxed\{(\d+)\}", lambda m: "\\boxed{" + str(int(m.group(1)) + rng.choice(OFFSETS)) + "}", sol)


def decide(a, n):
    enough = a["checked"] >= max(screen.MIN_WORKED, 0.2 * n)
    return bool(enough and a["rate"] is not None and a["rate"] >= screen.NOISY_EQ_RATE)


def row_stats(comps):
    a = screen.arithmetic_consistency(comps)
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in a.items()} | {"flag": decide(a, len(comps)), "n": len(comps)}


def latex():
    v4 = {r["problem"] for r in json.loads((Path.home() / ".cache" / "touchstone" / "v4" / "prealgebra.json").read_text())}
    out = {"math_train": {}, "v4_prealgebra_dev_rescore": {}, "gsm8k_train": {}}
    rng = random.Random(20261110)
    for sub in SUBJECTS:
        rows = [r for r in json.loads((DEV / f"math_{sub}.train.json").read_text()) if boxed_int(r["solution"]) and r["problem"] not in v4]
        rng.shuffle(rows)
        per = min(150, len(rows) // 3)
        draws = [rows[i * per:(i + 1) * per] for i in range(3)]
        out["math_train"][sub] = {"clean_0": row_stats([r["solution"] for r in draws[0]]), "clean_1": row_stats([r["solution"] for r in draws[1]])}
        pick = set(rng.sample(range(per), int(0.3 * per)))
        out["math_train"][sub]["planted_30"] = row_stats([plant(r["solution"], rng) if i in pick else r["solution"] for i, r in enumerate(draws[2])])
    for f in ["clean_prealgebra_0", "clean_prealgebra_1", "clean_prealgebra_2", "planted_prealgebra_30"]:
        rows = [json.loads(x) for x in (ROOT / "examples" / "test4" / "datasets" / f"{f}.jsonl").read_text().splitlines()]
        out["v4_prealgebra_dev_rescore"][f] = row_stats([r["completion"] for r in rows])
    g = [json.loads(x)["answer"] for x in (Path.home() / ".cache" / "touchstone" / "gsm8k_train.jsonl").read_text().splitlines()]
    a = screen.arithmetic_consistency(g)
    out["gsm8k_train"] = {"checked": a["checked"], "inconsistent": a["inconsistent"], "unsupported_final": a["unsupported_final"],
                          "unsupported_share": round(a["unsupported_final"] / a["checked"], 4), "rate": round(a["rate"], 4)}
    clean = [v for s in out["math_train"].values() for k, v in s.items() if k.startswith("clean")]
    planted = [v for s in out["math_train"].values() for k, v in s.items() if k.startswith("planted")]
    out["summary"] = {"math_clean_draws_flagged": f"{sum(v['flag'] for v in clean)} of {len(clean)}",
                      "math_clean_rate_range": [min(v["rate"] or 0 for v in clean), max(v["rate"] or 0 for v in clean)],
                      "math_planted_flagged": f"{sum(v['flag'] for v in planted)} of {len(planted)}",
                      "math_planted_rate_range": [min(v["rate"] or 0 for v in planted), max(v["rate"] or 0 for v in planted)]}
    (ROOT / "out" / "dev_flag_latex.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["summary"], indent=1))
    print(json.dumps(out["v4_prealgebra_dev_rescore"]))
    print(json.dumps(out["gsm8k_train"]))
    for s, v in out["math_train"].items():
        print(s, {k: (x["rate"], x["checked"], x["unsupported_final"]) for k, x in v.items()})




def _suite_prompts(spec):
    from touchstone import suites
    s = suites.get_suite(str(ROOT / spec) if spec.endswith(".jsonl") else spec).subset(200)  # as eval_test4 and the product
    return [i.prompt for i in s.items]


def _prompts(path):
    from touchstone import data as datamod
    try:
        return [e.prompt_text for e in datamod.load_dataset(path)]
    except datamod.DatasetError:
        return None


def offtopic():
    """off_topic on small, broad suites: material share against the suite's own leave-one-out share (same-source reference)."""
    from touchstone import screen
    from touchstone.overlap import embed
    rows = []
    man = json.loads((ROOT / "examples" / "test4" / "manifest.json").read_text())
    by_src = {}
    for m in man:
        if m["kind"] != "dataset":
            continue
        by_src.setdefault(m["source"], m["suite"])
        rows.append({"case": "v4:" + m["id"], "suite": m["suite"], "path": ROOT / "examples" / "test4" / m["path"],
                     "truth": bool(m["labels"].get("off_topic")), "kind": "v4 (development rescore)"})
    # constructed development positives on small custom suites: material from one v4 source against another's suite
    cross = [("alpaca", "qasc"), ("oasst", "aqua"), ("mawps", "medmcqa"), ("truthful", "aqua"), ("qasc", "oasst"),
             ("aqua", "truthful"), ("medmcqa", "alpaca"), ("multiarith", "mmlu")]
    for a, b in cross:
        rows.append({"case": f"cross:{a}->{b}", "suite": by_src[b], "path": ROOT / "examples" / "test4" / "datasets" / f"clean_{a}_0.jsonl",
                     "truth": True, "kind": "constructed off-topic, small custom suite"})
    for d in ["redflags_test", "redflags_test2", "redflags_test3"]:  # earlier sets, development data now
        for m in json.loads((ROOT / "examples" / d / "manifest.json").read_text()):
            if m["kind"] == "dataset" and (m["labels"].get("off_topic") or "clean" in m["id"]):
                rows.append({"case": f"{d}:{m['id']}", "suite": m["suite"], "path": ROOT / "examples" / d / m["path"],
                             "truth": bool(m["labels"].get("off_topic")), "kind": "built-in suite"})
    cache = {}
    out = []
    for r in rows:
        P = _prompts(r["path"])
        if P is None:
            continue
        if r["suite"] not in cache:
            S = _suite_prompts(r["suite"])
            E = embed(S)
            sim = E @ E.T
            sim.fill_diagonal_(-1)
            cache[r["suite"]] = (S, round(float((sim.max(1).values < screen.OFFTOPIC_COS).float().mean()), 4), len(S))
        S, loo, n = cache[r["suite"]]
        rel = screen.relevance(P, S)
        old_flag = rel["raw_off_topic_share"] >= screen.OFFTOPIC_SHARE
        new_flag = (rel["off_topic_share"] or 0.0) >= screen.OFFTOPIC_SHARE
        out.append({**{k: str(v) for k, v in r.items() if k != "path"}, "truth": r["truth"], "raw_share": rel["raw_off_topic_share"],
                    "suite_self_share": rel["suite_self_share"], "estimated_share": rel["off_topic_share"], "status": rel["off_topic_status"],
                    "suite_items": n, "flag_before": old_flag, "flag_after": new_flag})
        print(out[-1]["case"], r["truth"], rel["raw_off_topic_share"], rel["suite_self_share"], rel["off_topic_share"], old_flag, new_flag, flush=True)
    summ = {}
    for kind in sorted({o["kind"] for o in out}):
        x = [o for o in out if o["kind"] == kind]
        summ[kind] = {w: {"true_flags": sum(o[w] and o["truth"] for o in x), "false_flags": sum(o[w] and not o["truth"] for o in x),
                          "missed": sum(o["truth"] and not o[w] for o in x)} for w in ("flag_before", "flag_after")} | {"cases": len(x)}
    (ROOT / "out" / "dev_flag_offtopic.json").write_text(json.dumps({"summary": summ, "cases": out}, indent=1))
    print(json.dumps(summ, indent=1))


def language():
    """Language heuristic on development files: every v4 dataset (English), the coverage-eval files (English except MGSM
    es/de), and MGSM test in six languages (juletxara/mgsm, CC BY-SA 4.0)."""
    import glob
    from touchstone import coverage
    from touchstone import data as datamod
    cases = []
    for f in sorted(glob.glob(str(ROOT / "examples" / "test4" / "datasets" / "*.jsonl"))):
        cases.append((Path(f).stem, "en", f))
    for f in sorted(glob.glob(str(ROOT / "examples" / "coverage_eval" / "*.jsonl"))):
        cases.append(("coverage:" + Path(f).stem, "non_en" if ("_es_" in f or "_de_" in f) else "en", f))
    for lang in ["en", "fr", "sw", "es", "de", "bn"]:
        rows = json.loads((DEV / f"mgsm_{lang}.json").read_text())
        for d in range(2):
            cases.append((f"mgsm_{lang}_{d}", "en" if lang == "en" else "non_en", [r["question"] for r in rows[d * 125:(d + 1) * 125]]))
    out = []
    for name, truth, src in cases:
        if isinstance(src, list):
            texts = src
        else:
            try:
                texts = [e.last_user for e in datamod.load_dataset(src)[:200]]
            except datamod.DatasetError:
                continue
        t = " ".join(texts)[:20000]
        words = re.findall(r"[^\W\d_]+", t.lower())
        en = sum(w in coverage._EN for w in words) / max(1, len(words))
        other = max(sum(w in v and w not in coverage._EN for w in words) / max(1, len(words)) for v in coverage._OTHER.values())
        old = sum(w in coverage._STOP for w in words) / max(1, len(words))
        out.append({"case": name, "truth": truth, "before": "en" if not words or old >= 0.08 else "non_en", "after": coverage.language(texts),
                    "en_share": round(en, 4), "other_share": round(other, 4), "old_share": round(old, 4)})
    summ = {w: {"wrong": [o["case"] for o in out if o[w] != o["truth"]]} for w in ("before", "after")}
    summ["cases"] = {"en": sum(o["truth"] == "en" for o in out), "non_en": sum(o["truth"] == "non_en" for o in out)}
    summ["en_share_range"] = {t: [min(o["en_share"] for o in out if o["truth"] == t), max(o["en_share"] for o in out if o["truth"] == t)] for t in ("en", "non_en")}
    (ROOT / "out" / "dev_flag_language.json").write_text(json.dumps({"summary": summ, "cases": out}, indent=1))
    print(json.dumps(summ, indent=1))
    for o in sorted(out, key=lambda o: o["en_share"])[:12]:
        print(o)


if __name__ == "__main__":
    {"latex": latex, "offtopic": offtopic, "language": language}[sys.argv[1]]()
