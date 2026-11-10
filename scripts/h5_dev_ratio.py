"""Exploratory recount for the h5 pre-registration: SmolLM2 accuracy-gain ranking at three size ratios, on stored h4 runs
(development families and the spent h4 final families), screen-passing pairs within family. Chooses nothing.

    python scripts/h5_dev_ratio.py   # writes out/h5_dev_ratio.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import h4_score as S  # noqa: E402

SETS = {"h4 development (3)": (["dev_small", "dev_large"], ["ag_news", "rotten", "emotion"]),
        "h4 final (8)": (["final_small", "final_large"], ["dbpedia", "imdb", "amazon", "cr", "subj", "enron", "sst5", "bbc"]),
        "h4 final without dbpedia, imdb (6)": (["final_small", "final_large"], ["amazon", "cr", "subj", "enron", "sst5", "bbc"])}
out = {}
for label, (sets, fams) in SETS.items():
    R = S.load(str(ROOT / "out" / "h4"), sets)
    conds = sorted({k.split("|")[2] for k in R if k.startswith("sft|") and k.split("|")[1] in fams})
    passing = [c for c in conds if c not in S.FAIL and c != "placebo"]
    G = {z: {f: {c: S.gain(R, "sft", f, c, z) for c in conds} for f in fams} for z in ("135M", "360M", "1.7B")}
    out[label] = {}
    for name, (p, t) in {"135M to 1.7B (12.6x)": ("135M", "1.7B"), "360M to 1.7B (4.7x)": ("360M", "1.7B"), "135M to 360M (2.7x)": ("135M", "360M")}.items():
        ok = [c for c in passing if all(G[p][f][c] is not None and G[t][f][c] is not None for f in fams)]
        a, b, per = S.score(G[p], G[t], fams, ok)
        out[label][name] = {"decision": round(a / b, 3), "pairs": b, "by_family": per}
(ROOT / "out" / "h5_dev_ratio.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: {n: v["decision"] for n, v in x.items()} for k, x in out.items()}, indent=1))
