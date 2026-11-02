"""DEV ONLY (round 4): grader audit and suite fingerprint on every seen case: dev, v1, v2, v3 (v3 is now dev data).

Static and CPU-only. A score here never replaces the published v3 figures.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import eval_flags as E  # noqa: E402
from touchstone import data, env as envmod, judge, lm as L, overlap, probes, suites  # noqa: E402

L.set_device("cpu")
rows = {}
gated_r = {}
for name, items in (("dev", E.DEV), ("v1", E.test_items()), ("v2", E.test_items("redflags_test2")), ("v3", E.test_items("redflags_test3"))):
    tp = fp = fn = tc = fc = nc = 0
    for id_, kind, path, sname, truth in items:
        suite = suites.get_suite(sname).subset(200)
        sp = [i.prompt for i in suite.items]
        if kind == "env":
            v = envmod.load(ROOT / path)
            tasks = envmod.validate(v, path)
            ps = [t.prompt for t in tasks]
            ans = [(t.meta or {}).get("answer") for t in tasks]
            a = probes.audit_grader(v, tasks, None)
            flag = a["flagged"]
            t = "gameable_grader" in truth
            tp += flag and t
            fp += flag and not t
            fn += (not flag) and t
            if flag != t:
                print(name, "GRADER", id_, "truth", t, a["score"], a["worst_exploit"], flush=True)
        else:
            ex = data.load_dataset(ROOT / path)
            ps = [e.prompt_text for e in ex]
            ans = [judge.label_of(e.completion) for e in ex]
        f = overlap.fingerprint_overlap(sp, ps, 3 if sname == "word_math" else 2)
        gm = overlap.gated_suite_match([(i.prompt, i.answer) for i in suite.items], list(zip(ps, ans)))
        gated = gated_r.setdefault(name, [0, 0, 0])
        g = gm["rate"] > 0.05
        gated[0] += g and "contaminated" in truth
        gated[1] += g and "contaminated" not in truth
        gated[2] += "contaminated" in truth
        if g != ("contaminated" in truth):
            print(name, "GATED", id_, "truth", "contaminated" in truth, gm, flush=True)
        cf = f["rate"] > 0.05
        c = "contaminated" in truth
        tc += cf and c
        fc += cf and not c
        nc += c
        if cf and not c or (c and f["rate"] > 0):
            print(name, "FPRINT", id_, "truth", c, f, flush=True)
    rows[name] = dict(grader_tp=tp, grader_fp=fp, grader_fn=fn, fingerprint_tp=tc, fingerprint_fp=fc, contaminated=nc)
    print(name, rows[name], "gated tp/fp/positives", gated_r.get(name), flush=True)
(ROOT / "out" / "dev_flags_r4.json").write_text(json.dumps(rows, indent=1))
