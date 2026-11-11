"""Freeze h5x (METHOD.md, "h5x"): apply the pre-registered family rule to the 8B pre-flight, write the two configs, hash.

    python scripts/h5x_freeze.py cs=71.2 para=68.0 sent=88.5 tox=80.1 [--cut-last]   # Qwen3-8B base accuracy per suite, %

Rule: families sorted by name; the first three are primary, the last is the spare. A family with base accuracy >= 90 is
dropped. The spare replaces one dropped primary; no second substitute. --cut-last removes the last selected family by
name when the lead's fit check does not fit. The scorer and the soft helper are h5's files, unchanged, and are hashed again.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADROOM = 90.0
R = {"p12": "q3-0.6B", "p4": "q3-1.7B", "target": "q3-8B"}


def family(root, fam, mats, stratum):
    w = "wrong_" + mats[0]
    return {"stratum": stratum, "files": {m: f"{root}/{fam}/{m}.jsonl" for m in mats}, "suite_file": f"{root}/{fam}/suite.jsonl",
            "answer_kind": "letter", "passing": mats, "failing": [w], "gate_ref": mats[0], "gate_wrong": w, "recipe": {"max_new": 32}}


def main():
    base = {a.split("=")[0]: float(a.split("=")[1]) for a in sys.argv[1:] if "=" in a}
    man = json.loads((ROOT / "examples" / "h5x" / "manifest.json").read_text())["families"]
    names = sorted(man)
    assert sorted(base) == names, f"need base accuracy for exactly {names}"
    primary, spare = names[:3], names[3]
    dropped = [f for f in names if base[f] >= HEADROOM]
    sel = [f for f in primary if f not in dropped]
    if len(sel) == 2 and spare not in dropped:
        sel.append(spare)
    sel = sorted(sel)
    if "--cut-last" in sys.argv:
        sel = sel[:-1]
    mats = {f: list(man[f]["materials"]) for f in names}  # manifest order; the first is the gate reference
    note = {"base_accuracy_8B": base, "primary": primary, "spare": spare, "dropped_for_headroom": dropped, "selected": sel,
            "budget_cut": "--cut-last" in sys.argv}
    x = {"status": "FROZEN before h5 was scored and before any h5x run; hashes in out/h5x_final.sha256; rules in scripts/h5_score.py",
         "selection": note, "part": "final", "seeds": 2,
         "arms": {"ft": {"kind": "ft", "run_arm": "sft", "rungs": R,
                         "families": {f: family("examples/h5x", f, mats[f], "real competing (h5x), suite reused from h4" if f == "sent" else "real competing (h5x)")
                                      for f in sel}}}}
    h5 = json.loads((ROOT / "scripts" / "h5_config.json").read_text())["arms"]["ft"]["families"]
    pooled = json.loads(json.dumps(x))
    pooled["status"] = "FROZEN: pooled real stratum, pre-declared secondary analysis (h5 nli + sci, plus the h5x families)"
    pooled["arms"]["ft"]["families"] = {**{f: dict(h5[f], stratum="real competing (h5)") for f in ("nli", "sci")}, **x["arms"]["ft"]["families"]}
    (ROOT / "scripts" / "h5x_config.json").write_text(json.dumps(x, indent=1))
    (ROOT / "scripts" / "h5x_pooled_config.json").write_text(json.dumps(pooled, indent=1))
    files = [ROOT / "scripts" / f for f in ("h5_score.py", "h5_soft.py", "h5x_config.json", "h5x_pooled_config.json")]
    files += sorted(p for p in (ROOT / "examples" / "h5x").rglob("*") if p.is_file()) + [ROOT / "examples" / "h5" / f / n
             for f in ("nli", "sci") for n in sorted(p.name for p in (ROOT / "examples" / "h5" / f).iterdir())]
    lines = [hashlib.sha256(f.read_bytes()).hexdigest() + "  " + str(f.relative_to(ROOT)) for f in files]
    combined = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    (ROOT / "out" / "h5x_final.sha256").write_text(f"# h5x frozen before h5 was scored; combined {combined}\n" + "\n".join(lines) + "\n")
    print(json.dumps(note)); print(len(lines), "files; combined", combined)


if __name__ == "__main__":
    main()
