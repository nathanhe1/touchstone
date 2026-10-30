"""Red-flag detection accuracy: per-flag precision and recall on planted cases.

Two sets, never mixed:
  dev   the original sample environments and example datasets; screen thresholds were set here.
  test  examples/redflags_test/ (scripts/build_redflags_test.py): new generators, noise processes,
        paraphrase styles and grader bugs, built before any detector was run on it.

"after"  = this engine's static screens (touchstone.pipeline.screen_material + valuation.flags_for),
           exactly what a real appraisal runs, minus training.
"before" = the original prototype's detectors: exact-string overlap (redundancy.py) and its six
           hand-written exploits (probes.hackability); it had no dataset support, no label-noise,
           off-topic, duplicate or leakage checks.

    python scripts/eval_flags.py --set dev|test|both
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone import data as datamod  # noqa: E402
from touchstone import env as envmod  # noqa: E402
from touchstone import pipeline, probes, redundancy, suites, valuation  # noqa: E402

FLAGS = ["gameable_grader", "answer_leakage", "contaminated", "copied_from_public", "duplicated", "noisy_labels",
         "off_topic"]

DEV = [  # (id, kind, path, suite, true flags)
    ("northwind_arith", "env", "envs/northwind_arith", "arithmetic", []),
    ("mirror_strings", "env", "envs/mirror_strings", "strings", []),
    ("clone_arith", "env", "envs/clone_arith", "arithmetic", ["copied_from_public"]),
    ("quickgrade_arith", "env", "envs/quickgrade_arith", "arithmetic", ["gameable_grader"]),
    ("shapeonly_arith", "env", "envs/shapeonly_arith", "arithmetic", ["gameable_grader"]),
    ("hintleak_arith", "env", "envs/hintleak_arith", "arithmetic", ["gameable_grader", "answer_leakage"]),
    ("public_arith", "env", "envs/public_arith", "arithmetic", ["copied_from_public"]),
] + [(n, "dataset", f"examples/datasets/{n}.jsonl", "word_math", f) for n, f in [
    ("good_cot", []), ("good_short", []), ("hard_cot", []), ("small_good", []),
    ("noisy_20", ["noisy_labels"]), ("noisy_50", ["noisy_labels"]), ("noisy_80", ["noisy_labels"]),
    ("wrong_all", ["noisy_labels"]), ("short_noisy_30", ["noisy_labels"]),
    ("offtopic", ["off_topic"]), ("half_offtopic", ["off_topic"]), ("mostly_offtopic", ["off_topic"]),
    ("gsm8k_clone", ["copied_from_public"]), ("contaminated", ["contaminated"]), ("duplicated", ["duplicated"])]]


def test_items(folder="redflags_test"):
    m = json.loads((ROOT / "examples" / folder / "manifest.json").read_text())
    return [(x["id"], x["kind"], f"examples/{folder}/{x['path']}", x["suite"], [k for k, v in x["labels"].items() if v])
            for x in m]


def after(kind, path, suite_name):
    suite = suites.get_suite(suite_name).subset(200)
    if kind == "dataset":
        ex = datamod.load_dataset(path)
        sc = pipeline.screen_material("dataset", [e.prompt_text for e in ex], suite, None, log=lambda m: None,
                                      examples=ex)
    else:
        env = envmod.load(path)
        tasks = envmod.validate(env, path)
        sc = pipeline.screen_material("env", [t.prompt for t in tasks], suite, None, log=lambda m: None, env=env,
                                      tasks=tasks)
    flags = {f["code"] for f in valuation.flags_for(dict(sc["meas"], measurable=True))}
    return flags & set(FLAGS), sc["meas"]


def before(kind, path, suite_name):
    """The original prototype's checks (exact-string overlap, six static exploits; envs only)."""
    if kind == "dataset":
        return set(), {}
    env = envmod.load(path)
    suite = suites.get_suite(suite_name)
    pub = envmod.load(ROOT / "envs" / "public_arith") if suite_name == "arithmetic" else None
    out = set()
    h = probes.hackability(env)["score"]
    if h >= 0.2:
        out.add("gameable_grader")
    from touchstone.env import Task
    if redundancy.contamination(env, [Task(i.prompt) for i in suite.items]) > 0.05:
        out.add("contaminated")
    if pub is not None and redundancy.redundancy(env, [pub])["public_overlap"] >= 0.5:
        out.add("copied_from_public")
    return out, {"hackability_old": h}


def score(rows, key):
    res = {}
    for f in FLAGS:
        tp = sum(f in r[key] and f in r["truth"] for r in rows)
        fp = sum(f in r[key] and f not in r["truth"] for r in rows)
        fn = sum(f not in r[key] and f in r["truth"] for r in rows)
        res[f] = {"tp": tp, "fp": fp, "fn": fn, "positives": tp + fn,
                  "precision": round(tp / (tp + fp), 3) if tp + fp else None,
                  "recall": round(tp / (tp + fn), 3) if tp + fn else None}
    tp = sum(v["tp"] for v in res.values())
    fp = sum(v["fp"] for v in res.values())
    fn = sum(v["fn"] for v in res.values())
    res["all"] = {"tp": tp, "fp": fp, "fn": fn, "precision": round(tp / (tp + fp), 3) if tp + fp else None,
                  "recall": round(tp / (tp + fn), 3) if tp + fn else None}
    return res


def run(name, items):
    rows = []
    for id_, kind, path, suite, truth in items:
        t0 = time.time()
        a, meas = after(kind, ROOT / path, suite)
        b, _ = before(kind, ROOT / path, suite)
        rows.append({"id": id_, "kind": kind, "suite": suite, "truth": sorted(truth), "after": sorted(a),
                     "before": sorted(b), "meas": {k: v for k, v in meas.items() if not isinstance(v, dict)},
                     "seconds": round(time.time() - t0, 1)})
        ok = "ok " if set(a) == set(truth) else "ERR"
        print(f"[{name}] {ok} {id_:22s} truth={sorted(truth)} after={sorted(a)} before={sorted(b)}", flush=True)
    return {"items": rows, "after": score(rows, "after"), "before": score(rows, "before"),
            "exact_match_after": sum(set(r["after"]) == set(r["truth"]) for r in rows) / len(rows),
            "exact_match_before": sum(set(r["before"]) == set(r["truth"]) for r in rows) / len(rows)}


def table(res):
    lines = ["| Flag | Positives | Before: precision / recall | After: precision / recall |", "|---|---|---|---|"]
    for f in FLAGS + ["all"]:
        b, a = res["before"][f], res["after"][f]
        lines.append(f"| {f} | {a.get('positives', a['tp'] + a['fn'])} | {b['precision']} / {b['recall']} | "
                     f"{a['precision']} / {a['recall']} |")
    lines.append(f"\nItems with exactly the right flag set: before {res['exact_match_before']:.0%}, "
                 f"after {res['exact_match_after']:.0%} (n={len(res['items'])}).")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="both", choices=["dev", "test", "test2", "both", "all"])
    ap.add_argument("--tag", default="", help="suffix for result keys, e.g. _round1 to keep a before snapshot")
    a = ap.parse_args()
    out_f = ROOT / "out" / "flag_eval.json"
    out = json.loads(out_f.read_text()) if out_f.exists() else {}
    for name, items in (("dev", DEV), ("test", test_items()), ("test2", test_items("redflags_test2"))):
        if a.set == name or a.set == "all" or (a.set == "both" and name != "test2"):
            out[name + a.tag] = run(name, items)
            print(f"\n{name.upper()}{a.tag}\n" + table(out[name + a.tag]), flush=True)
    out_f.write_text(json.dumps(out, indent=2))
    (ROOT / "out" / "flag_eval.md").write_text("\n\n".join(f"## {k}\n\n{table(v)}" for k, v in out.items()) + "\n")
