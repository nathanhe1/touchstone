"""How close each flag decision sits to its threshold, and what a +/-20% threshold move changes.

Read-only on saved results; it changes no threshold. Test sets report what would have flipped, and that is
never used to tune anything.

    python scripts/flag_margins.py              # writes out/flag_margins.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import screen, valuation as V  # noqa: E402

LIMITS = {"gameable_grader": ("hackability", V.HACK_LIMIT), "answer_leakage": ("answer_leakage", V.LEAK_LIMIT),
          "contaminated": ("contamination", V.CONTAM_LIMIT), "copied_from_public": ("public_overlap", V.PUBLIC_LIMIT),
          "duplicated": ("dup_rate", 0.5), "off_topic": ("off_topic_share", V.OFFTOPIC_LIMIT)}




def score(items, limit, high_is_bad=True):
    r = {}
    for m in (0.8, 1.0, 1.2):
        t = limit * m
        tp = sum((v >= t) == high_is_bad and y for v, y in items)
        fp = sum((v >= t) == high_is_bad and not y for v, y in items)
        fn = sum((v >= t) != high_is_bad and y for v, y in items)
        r[f"x{m}"] = {"tp": tp, "fp": fp, "fn": fn}
    near = sorted(items, key=lambda x: abs(x[0] - limit))[:3]
    r["nearest"] = [{"value": round(v, 3), "truth": bool(y), "margin_pct": round(100 * abs(v - limit) / limit, 1)} for v, y in near]
    r["within_20pct"] = sum(abs(v - limit) <= 0.2 * limit for v, _ in items)
    return r


def main():
    fe = json.loads((ROOT / "out" / "flag_eval.json").read_text())
    out = {}
    for key in ("test3", "test2_round3", "test_round3", "dev_round3"):
        if key not in fe:
            continue
        rows = fe[key]["items"]
        b = {}
        for flag, (field, lim) in LIMITS.items():
            it = [(r["meas"][field], flag in r["truth"]) for r in rows if field in r["meas"]]
            if it:
                b[flag] = score(it, lim)
        out[key] = b
    st = ROOT / "out" / "stress_real.json"
    if st.exists():
        S = json.loads(st.read_text())
        groups = {"judge_numeric": ([v["disagree"] for v in S.values() if v.get("route") == "both"], screen.JUDGE_DISAGREE, True),
                  "mcq": ([v["disagree"] for v in S.values() if v["dtype"] == "multiple_choice" and v.get("disagree") is not None], screen.MCQ_DISAGREE, True),
                  "free_text_fit": ([v["fit"] for v in S.values() if v["dtype"] == "free_text" and v.get("fit") is not None], screen.FIT_MIN["free_text"], False),
                  "code_fail": ([v["rate"] for v in S.values() if v["dtype"] == "code" and v.get("rate") is not None], screen.CODE_FAIL_RATE, True),
                  "arithmetic": ([v["arithmetic"]["rate"] for v in S.values() if v["arithmetic"]["rate"] is not None], screen.NOISY_EQ_RATE, True)}
        out["stress_real_clean"] = {k: {**score([(x, False) for x in vals if x is not None], lim, hi), "n": len(vals)}
                                    for k, (vals, lim, hi) in groups.items() if vals}
    (ROOT / "out" / "flag_margins.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=0)[:2500])


if __name__ == "__main__":
    main()
