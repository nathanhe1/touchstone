"""Re-check every h4 family under the class-balance gate: the old first-rows fetch against the corrected seeded fetch.

    python scripts/h5_balance_check.py OLD_DIR NEW_DIR out/h5_balance_check.json

For each family and split: rows, classes seen, majority share, cap, gate verdict, and the total-variation distance between
the old and the new label distribution (how far the old fetch was from a random sample of the same split). The h4
material pool (rows not in the suite) and the 600-item suite are what h4 actually used, so those are checked too.
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def dist(items):
    c = Counter(x[1] for x in items)
    n = sum(c.values())
    return {k: v / n for k, v in c.items()} if n else {}


def tv(p, q):
    return round(0.5 * sum(abs(p.get(k, 0) - q.get(k, 0)) for k in set(p) | set(q)), 4)


def view(data_dir):
    os.environ["H4_DATA"] = data_dir
    import importlib
    import h4_common as H
    importlib.reload(H)
    out = {}
    for fam, (ms, ss) in H.SPLITS.items():
        m, s = H.items(fam, ms), H.items(fam, ss)
        if not m or not s:
            continue
        suite = s[:600]
        sp = {x[0] for x in suite}
        pool = [x for x in m if x[0] not in sp]
        out[fam] = {"material_pool": (H.balance(pool), dist(pool)), "suite_600": (H.balance(suite), dist(suite))}
    return out


def main():
    old, new, dest = sys.argv[1], sys.argv[2], sys.argv[3]
    O, N = view(old), view(new)
    res = {}
    for fam in sorted(set(O) | set(N)):
        r = {}
        for part in ("material_pool", "suite_600"):
            o, n = O.get(fam, {}).get(part), N.get(fam, {}).get(part)
            r[part] = {"old": o[0] if o else None, "new": n[0] if n else None,
                       "tv_old_vs_new": tv(o[1], n[1]) if o and n else None}
        r["old_failed_gate"] = any(r[p]["old"] and not r[p]["old"]["ok"] for p in r)
        r["new_failed_gate"] = any(r[p]["new"] and not r[p]["new"]["ok"] for p in ("material_pool", "suite_600"))
        res[fam] = r
        print(f"{fam:10s} pool old {r['material_pool']['old'] and r['material_pool']['old']['share']} "
              f"new {r['material_pool']['new'] and r['material_pool']['new']['share']} | suite old {r['suite_600']['old'] and r['suite_600']['old']['share']} "
              f"new {r['suite_600']['new'] and r['suite_600']['new']['share']} | tv pool {r['material_pool']['tv_old_vs_new']} suite {r['suite_600']['tv_old_vs_new']}"
              f"{'  OLD FAILS GATE' if r['old_failed_gate'] else ''}{'  NEW FAILS GATE' if r['new_failed_gate'] else ''}")
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    Path(dest).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
