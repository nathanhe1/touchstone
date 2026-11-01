"""Summarise round 4 runs per arm and family. Pilot data is development data.

    python scripts/h4_report.py pilot [out/h4]
"""
import glob
import itertools
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import forecast as fc  # noqa: E402

part = sys.argv[1] if len(sys.argv) > 1 else "pilot"
d = sys.argv[2] if len(sys.argv) > 2 else "out/h4"
R = {}
for f in glob.glob(f"{ROOT}/{d}/h4_{part}.shard*.json"):
    R.update(json.loads(Path(f).read_text()))
print(len(R), "runs")


def get(arm, fam, cond, size):
    return [R[k]["gain"] for k in R if k.startswith(f"{arm}|{fam}|{cond}|{size}|")]


def pairs(x, y):
    a = b = 0
    for i, j in itertools.combinations(range(len(x)), 2):
        if y[i] != y[j]:
            b += 1
            a += (x[i] - x[j]) * (y[i] - y[j]) > 0
    return a, b


out = {}
for arm in sorted({k.split("|")[0] for k in R}):
    fams = sorted({k.split("|")[1] for k in R if k.startswith(arm)})
    conds = sorted({k.split("|")[2] for k in R if k.startswith(arm)})
    print("==", arm, conds)
    tot = {}
    for fam in fams:
        row = {}
        for size in ("135M", "360M", "1.7B"):
            row[size] = [st.mean(get(arm, fam, c, size)) if get(arm, fam, c, size) else None for c in conds]
        base = {}
        for size in ("135M", "360M", "1.7B"):
            ks = [k for k in R if k.startswith(f"{arm}|{fam}|") and f"|{size}|" in k]
            if ks:
                b = R[ks[0]]["base"]
                base[size] = round(100 * b.count("1") / len(b), 1)
        ceil = {}
        for size in ("360M", "1.7B"):
            s = [[get(arm, fam, c, size) for c in conds]]
            g = [get(arm, fam, c, size) for c in conds]
            if all(len(x) >= 2 for x in g):
                a, b = pairs([x[0] for x in g], [x[1] for x in g])
                ceil[size] = (a, b)
                tot.setdefault("ceil" + size, []).append((a, b))
        fc_ = {}
        for p, t in (("135M", "360M"), ("360M", "1.7B")):
            if all(v is not None for v in row[p]) and all(v is not None for v in row[t]):
                a, b = pairs(row[p], row[t])
                fc_[f"{p}>{t}"] = f"{a}/{b}"
                tot.setdefault(f"{p}>{t}", []).append((a, b))
        extra = {}
        ks = [k for k in R if k.startswith(f"{arm}|{fam}|") and "mixed_groups" in R[k]]
        print(f"{fam:10s} base {base} ceil {ceil} forecast {fc_}")
        for size in ("135M", "360M", "1.7B"):
            if any(v is not None for v in row[size]):
                print("    ", size, [None if v is None else round(v, 1) for v in row[size]])
    print("  TOTAL", {k: round(sum(a for a, _ in v) / max(1, sum(b for _, b in v)), 3) for k, v in tot.items()}, {k: sum(b for _, b in v) for k, v in tot.items()})
