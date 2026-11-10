"""Report test v5 as pre-registered (METHOD.md): tiers never pooled; blocking flags primary, advisory beside; precision with
its prevalence and the precision implied at 2%, 6.5% and 20%; recall; false flags per source with one-sided 95% upper
bounds; negatives by clean-easy, clean-hard and ambiguous; row-level secondary measures.

    python scripts/report_test5.py      # reads out/test_v5_results.json, writes out/test_v5_report.json
"""
import collections
import json
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ["gameable_grader", "answer_leakage", "contaminated", "copied_from_public", "duplicated", "noisy_labels", "off_topic"]
PRIVATE_SOURCES = ("realmistake",)  # rows stay out of public reports; only aggregates are written


def ub(k, n):
    """One-sided 95% Clopper-Pearson upper bound for k of n."""
    if n == 0:
        return None
    lo, hi = 0.0, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        if sum(comb(n, i) * m ** i * (1 - m) ** (n - i) for i in range(k + 1)) > 0.05:
            lo = m
        else:
            hi = m
    return round(hi, 3)


def implied_precision(recall, fpr, prev):
    if recall is None or fpr is None:
        return None
    d = recall * prev + fpr * (1 - prev)
    return round(recall * prev / d, 3) if d else None


def block(rows):
    """Case-level numbers for one tier, blocking flags only, plus the advisory label signal beside them."""
    tp = sum(len(set(v["truth"]) & set(v["flags"])) for v in rows)
    fp = sum(len(set(v["flags"]) - set(v["truth"])) for v in rows)
    fn = sum(len(set(v["truth"]) - set(v["flags"])) for v in rows)
    pos_cases = [v for v in rows if v["truth"]]
    neg_cases = [v for v in rows if not v["truth"]]
    neg_flagged = sum(bool(v["flags"]) for v in neg_cases)
    recall = tp / (tp + fn) if tp + fn else None
    fpr = neg_flagged / len(neg_cases) if neg_cases else None
    out = {"cases": len(rows), "positive_cases": len(pos_cases), "prevalence": round(len(pos_cases) / len(rows), 3) if rows else None,
           "tp": tp, "fp": fp, "fn": fn, "precision": round(tp / (tp + fp), 3) if tp + fp else None, "recall": round(recall, 3) if recall is not None else None,
           "exact": sum(set(v["truth"]) == set(v["flags"]) for v in rows),
           "negatives_flagged": f"{neg_flagged} of {len(neg_cases)}", "negatives_flagged_upper95": ub(neg_flagged, len(neg_cases)),
           "implied_precision": {str(p): implied_precision(recall, fpr, p) for p in (0.02, 0.065, 0.20)}}
    nl = [v for v in rows if "noisy_labels" in v["truth"]]
    out["advisory_label_signal"] = {"noisy_cases_with_advisory": f"{sum(bool(v.get('advisory')) for v in nl)} of {len(nl)}",
                                    "clean_cases_with_advisory": f"{sum(bool(v.get('advisory')) for v in rows if 'noisy_labels' not in v['truth'])} of "
                                                                 f"{sum('noisy_labels' not in v['truth'] for v in rows)}"}
    out["per_flag"] = {f: {"tp": sum(f in v["truth"] and f in v["flags"] for v in rows), "fp": sum(f in v["flags"] and f not in v["truth"] for v in rows),
                           "fn": sum(f in v["truth"] and f not in v["flags"] for v in rows)} for f in FLAGS}
    kinds = collections.defaultdict(list)
    for v in neg_cases:
        kinds[v.get("negative") or "unlabelled"].append(v)
    out["negatives_by_kind"] = {k: {"cases": len(x), "with_false_flag": sum(bool(v["flags"]) for v in x), "upper95": ub(sum(bool(v["flags"]) for v in x), len(x)),
                                    "with_advisory": sum(bool(v.get("advisory")) for v in x)} for k, x in sorted(kinds.items())}
    src = collections.defaultdict(list)
    for v in neg_cases:
        src[v["source"].split(":")[0] if v["source"].startswith(PRIVATE_SOURCES) else v["source"]].append(v)
    out["false_flags_by_source"] = {s: {"negatives": len(x), "with_false_flag": sum(bool(v["flags"]) for v in x), "upper95": ub(sum(bool(v["flags"]) for v in x), len(x)),
                                        "which": sorted({f for v in x for f in v["flags"]})} for s, x in sorted(src.items())}
    return out


def row_level_mcq(rows):
    """Judge rows (sampled by the check) against MMLU-Redux's audit: confident disagreement as a row-level flag."""
    tp = fp = fn = tn = amb_flag = amb = 0
    for v in rows:
        jr, truth = v.get("judge_rows"), v.get("row_truth")
        if not jr or not truth:
            continue
        for r in jr:
            t = truth[r["i"]]
            flagged = bool(r["direct"]) and r["direct"] == r["cot"] and r["direct"] != r["label"]
            if t == "ambiguous":
                amb += 1
                amb_flag += flagged
            elif t == "wrong":
                tp, fn = tp + flagged, fn + (not flagged)
            else:
                fp, tn = fp + flagged, tn + (not flagged)
    return {"wrong_rows_sampled": tp + fn, "recall": round(tp / (tp + fn), 3) if tp + fn else None,
            "precision": round(tp / (tp + fp), 3) if tp + fp else None, "ok_rows_flagged": f"{fp} of {fp + tn}",
            "ambiguous_rows_flagged": f"{amb_flag} of {amb}"}


def row_level_arith(rows):
    """Arithmetic check per row (an error or an unsupported final) against GSM8K-Platinum's audit."""
    c = collections.Counter()
    for v in rows:
        for t, a in zip(v.get("row_truth") or [], v.get("row_arith") or []):
            c[(t, bool(a["wrong_eq"] or a["unsupported"]))] += 1
    return {t: f"{c[(t, True)]} of {c[(t, True)] + c[(t, False)]} flagged" for t in ("wrong", "ambiguous", "ok")}


def main():
    r = json.loads((ROOT / "out" / "test_v5_results.json").read_text())
    meta = r.pop("_meta", {})
    scored = {k: v for k, v in r.items() if not v.get("rejected_by_loader")}
    out = {"commits": meta.get("commits"), "rejected_by_loader": sorted(k for k, v in r.items() if v.get("rejected_by_loader")), "tiers": {}}
    for tier in ("A", "A-previewed", "B"):
        rows = [v for v in scored.values() if v["tier"] == tier]
        if rows:
            out["tiers"][tier] = block(rows)
    out["tiers"]["B"]["by_part"] = {p: block([v for v in scored.values() if v["tier"] == "B" and v["part"] == p])
                                    for p in sorted({v["part"] for v in scored.values() if v["tier"] == "B"})}
    out["row_level"] = {"mmlu_redux_judge": row_level_mcq([v for v in scored.values() if v["part"] == "mmlu_redux"]),
                        "gsm_platinum_arithmetic (A-previewed)": row_level_arith([v for v in scored.values() if v["part"] == "gsm_platinum"])}
    out["cases"] = {k: {"tier": v["tier"], "truth": v["truth"], "flags": v["flags"], "advisory": bool(v.get("advisory")), "negative": v.get("negative"),
                        "signal": (v.get("checks") or {}).get("disagree", (v.get("checks") or {}).get("fit"))}
                    for k, v in scored.items() if not v["source"].startswith(PRIVATE_SOURCES)}
    (ROOT / "out" / "test_v5_report.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({t: {k: x[k] for k in ("cases", "prevalence", "precision", "recall", "negatives_flagged", "implied_precision")} for t, x in out["tiers"].items()}, indent=1))
    print(json.dumps(out["row_level"], indent=1))


if __name__ == "__main__":
    main()
