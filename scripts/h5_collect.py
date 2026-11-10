"""Collect per-run results into the files the h5 scorer reads (scripts/h5_score.py).

    python scripts/h5_collect.py out/h5/<set> out/h5/h5_<set>.json [--gates out/h5/h5_gates.json]

Runs: {"arm|family|material|size|seed": record}. A refused run (class-balance gate) is not a run and is left out, and
listed in the gates file. Gates: {"balance": {"max_share": cap rule, "<fam>": {"suite": share, "materials": {...}}},
"rl": {"<fam>|<size>": {"reward_rate", "chance", "kappa", "truncated"}}}, merged into an existing gates file.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h4_common as H  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dest")
    ap.add_argument("--gates")
    a = ap.parse_args()
    runs, gates = {}, {"balance": {"max_share": f"min({H.MAJORITY_CAP}, 2.5/k)"}, "rl": {}, "refused": []}
    if a.gates and Path(a.gates).exists():
        old = json.loads(Path(a.gates).read_text())
        gates["balance"].update(old.get("balance", {}))
        gates["rl"].update(old.get("rl", {}))
        gates["refused"] = old.get("refused", [])
    for f in sorted(Path(a.src).glob("*.json")):
        r = json.loads(f.read_text())
        j = r.get("job")
        if not j:
            continue
        fam, mat, size, seed = j["family"], j.get("material_name") or j.get("material", "clean"), j["size"], j["seed"]
        g = r.get("gates") or {}
        b = gates["balance"].setdefault(fam, {"suite": None, "materials": {}})
        if g.get("suite"):
            b["suite"] = g["suite"]["share"]
            b["max_share"] = g["suite"]["cap"]  # the family's cap, min(0.65, 2.5/k)
        if g.get("material"):
            b["materials"][mat] = g["material"]["share"]
        if r.get("refused"):
            gates["refused"].append(j["id"])
            continue
        if j["arm"] == "rlgate":
            gates["rl"][f"{fam}|{size}"] = {k: r.get(k) for k in ("reward_rate", "chance", "kappa", "truncated", "no_answer", "n")}
            continue
        if j["arm"] == "base":
            continue
        runs[f"{j['arm']}|{fam}|{mat}|{size}|{seed}"] = r
    Path(a.dest).parent.mkdir(parents=True, exist_ok=True)
    Path(a.dest).write_text(json.dumps(runs))
    if a.gates:
        gates["refused"] = sorted(set(gates["refused"]))
        Path(a.gates).write_text(json.dumps(gates, indent=1))
    print(f"{len(runs)} runs -> {a.dest}; rl gates {len(gates['rl'])}; refused {len(gates['refused'])}")


if __name__ == "__main__":
    main()
