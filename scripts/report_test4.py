"""Report frozen test v4 per part and per source. Blocking flags are primary; advisory signals sit beside them."""
import collections
import json
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import os  # noqa: E402
SRC = os.environ.get("TEST4_OUT", "out/test_v4_results.json")  # a later run is a development number; see eval_test4.py
r = json.loads((ROOT / SRC).read_text())
F = ["gameable_grader", "answer_leakage", "contaminated", "copied_from_public", "duplicated", "noisy_labels", "off_topic"]


def ub(k, n):
    """One-sided 95% upper bound (Clopper-Pearson)."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        if sum(comb(n, i) * m ** i * (1 - m) ** (n - i) for i in range(k + 1)) > 0.05:
            lo = m
        else:
            hi = m
    return round(hi, 3)


scored = {k: v for k, v in r.items() if not v.get("rejected_by_loader")}
rej = [k for k, v in r.items() if v.get("rejected_by_loader")]


def counts(rows):
    tp = sum(len(set(v["truth"]) & set(v["flags"])) for v in rows)
    fp = sum(len(set(v["flags"]) - set(v["truth"])) for v in rows)
    fn = sum(len(set(v["truth"]) - set(v["flags"])) for v in rows)
    return tp, fp, fn


out = {}
tp, fp, fn = counts(scored.values())
out["all"] = {"tp": tp, "fp": fp, "fn": fn, "precision": round(tp / (tp + fp), 3) if tp + fp else None, "recall": round(tp / (tp + fn), 3) if tp + fn else None,
              "exact": sum(set(v["truth"]) == set(v["flags"]) for v in scored.values()), "n": len(scored), "rejected": rej}
out["flags"] = {f: dict(zip(("tp", "fp", "fn"), (sum(f in v["truth"] and f in v["flags"] for v in scored.values()), sum(f in v["flags"] and f not in v["truth"] for v in scored.values()),
                                                  sum(f in v["truth"] and f not in v["flags"] for v in scored.values())))) for f in F}
out["parts"] = {}
for p in sorted({v["part"] for v in scored.values()}):
    x = [v for v in scored.values() if v["part"] == p]
    a, b, c = counts(x)
    out["parts"][p] = {"n": len(x), "exact": sum(set(v["truth"]) == set(v["flags"]) for v in x), "tp": a, "fp": b, "fn": c, "advisory": sum(bool(v["advisory"]) for v in x)}
src = collections.defaultdict(list)
for k, v in scored.items():
    if v["part"] == "clean_real":
        src[v["source"]].append((k, v))
out["clean_by_source"] = {}
for s, x in src.items():
    ff = sum(bool(v["flags"]) for _, v in x)
    out["clean_by_source"][s] = {"draws": len(x), "false_flags": ff, "upper95": ub(ff, len(x)), "which": sorted({f for _, v in x for f in v["flags"]}), "advisory": sum(bool(v["advisory"]) for _, v in x),
                                 "signal": [v["checks"].get("disagree", v["checks"].get("fit", v["checks"].get("rate"))) for _, v in x], "status": x[0][1]["checks"].get("status")}
n = sum(len(x) for x in src.values())
f = sum(bool(v["flags"]) for x in src.values() for _, v in x)
out["clean_total"] = {"draws": n, "with_false_flag": f, "upper95": ub(f, n)}
out["errors"] = {k: {"part": v["part"], "truth": v["truth"], "flags": v["flags"], "advisory": bool(v["advisory"]), "signal": v["checks"].get("disagree", v["checks"].get("fit")),
                     "exploit": (v.get("audit") or {}).get("worst_exploit"), "contam": round(v["meas"].get("contamination", 0), 3), "public": round(v["meas"].get("public_overlap", 0), 3)}
                 for k, v in scored.items() if set(v["truth"]) != set(v["flags"])}
out["source"] = SRC
if SRC != "out/test_v4_results.json":
    out["label"] = "DEVELOPMENT RESCORE: test v4 is spent; its published numbers stand"
(ROOT / ("out/test_v4_report.json" if SRC == "out/test_v4_results.json" else SRC.replace(".json", "_report.json"))).write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("all", "flags", "parts", "clean_total")}, indent=0))
for s, v in out["clean_by_source"].items():
    print(s, v)
for k, v in out["errors"].items():
    print(k, v)
