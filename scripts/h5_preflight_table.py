"""Summarise ladder pre-flights: per family, base accuracy / chance / soft score / answer-found share at every rung.

    python scripts/h5_preflight_table.py out/h5/preflight/qwen3.json q3-0.6B,q3-1.7B,q3-4B,q3-8B
"""
import json
import sys

d = json.loads(open(sys.argv[1]).read())
sizes = sys.argv[2].split(",")
fams = sorted({k.split("|")[0] for k in d})
print("| family | chance | " + " | ".join(f"{s} acc / soft / ans" for s in sizes) + " | headroom at top (<90) | top above chance+10 |")
print("|---|---|" + "---|" * len(sizes) + "---|---|")
for f in fams:
    cells, ch = [], None
    for s in sizes:
        r = d.get(f"{f}|{s}")
        if not r:
            cells.append("")
            continue
        ch = r["chance"]
        ans = r.get("has_letter")
        cells.append(f"{r['acc']:.0f} / {r.get('soft') if r.get('soft') is not None else '-'} / {ans if ans is not None else '-'}")
    top = d.get(f"{f}|{sizes[-1]}")
    hr = "yes" if top and top["acc"] < 90 else ("no" if top else "")
    ab = "yes" if top and top["acc"] >= (ch or 0) + 10 else ("no" if top else "")
    print(f"| {f} | {ch} | " + " | ".join(cells) + f" | {hr} | {ab} |")
