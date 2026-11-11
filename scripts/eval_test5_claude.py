"""Second scoring of frozen test v5's multiple-choice label cases, with a Claude model as the judge.

Rules: METHOD.md, "Test v5 rescored with a Claude judge". One change from the v5 scoring: the judge, which also reads
every row of a case instead of a 60-row sample. Same two routes and same statistic. Hashes are verified first.

    python scripts/eval_test5_claude.py run claude-haiku-5-5    # writes out/test_v5_claude_claude-haiku-5-5.json
    python scripts/eval_test5_claude.py report                  # writes out/test_v5_claude_report.json
"""
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from dev_judge_claude import COT, DIRECT, route  # noqa: E402
from touchstone.coverage import mcq_label, mcq_options  # noqa: E402

T5 = ROOT / "examples" / "test5"
PARTS = ("mmlu_redux", "planted_labels", "fbugs")
LINE = 0.30  # the product's current line, unchanged


def check_hashes():
    for line in (ROOT / "out" / "test_v5.sha256").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            h, f = line.split(None, 1)
            f = Path(f.strip()).expanduser() if f.strip().startswith(("~", "/")) else ROOT / f.strip()
            if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
                sys.exit(f"v5 hash mismatch, refusing to score: {f}")


def cases():
    """(manifest entry, [(row index, prompt, label letter, audit truth)]) for every multiple-choice label case."""
    for m in json.loads((T5 / "manifest.json").read_text()):
        if m["part"] not in PARTS:
            continue
        rows = [json.loads(x) for x in (T5 / m["path"]).read_text().splitlines()]
        keep = [(i, r["prompt"], mcq_label(r["completion"]), m["row_truth"][i]) for i, r in enumerate(rows)
                if len(mcq_options(r["prompt"])) >= 2 and mcq_label(r["completion"])]
        if len(keep) >= 10:  # the free-form planted set (GSM8K) has no options and drops out here
            yield m, keep


def run(model):
    check_hashes()
    out_f = ROOT / "out" / f"test_v5_claude_{model}.json"
    res = json.loads(out_f.read_text()) if out_f.exists() else {}
    cost = res.pop("_meta", {}).get("cost_usd", 0.0)
    t0 = time.time()
    for m, keep in cases():
        if m["id"] in res and not any(x["direct"] is None or x["cot"] is None for x in res[m["id"]]["rows"]):
            continue
        q = [k[1] for k in keep]
        d, c1 = route(model, DIRECT, q)
        c, c2 = route(model, COT, q)
        cost += c1 + c2
        res[m["id"]] = {"part": m["part"], "noisy": m["labels"]["noisy_labels"], "negative": m.get("negative"),
                        "rows": [{"i": k[0], "direct": a, "cot": b, "label": k[2], "truth": k[3]} for a, b, k in zip(d, c, keep)]}
        print(m["id"], len(keep), tally(res[m["id"]]["rows"]), f"${cost:.2f}", f"{time.time() - t0:.0f}s", flush=True)
        out_f.write_text(json.dumps({**res, "_meta": {"model": model, "backend": "claude command line, print mode, no tools", "cost_usd": round(cost, 4)}}))


def tally(rows):
    conf = [r for r in rows if r["direct"] and r["direct"] == r["cot"]]
    dis = [r for r in conf if r["direct"] != r["label"]]
    return {"rows": len(rows), "confident": len(conf), "disagree_n": len(dis), "disagree": round(len(dis) / len(conf), 4) if len(conf) >= 10 else None}


def report():
    rep = {}
    for f in sorted((ROOT / "out").glob("test_v5_claude_claude-*.json")):
        res = json.loads(f.read_text())
        meta = res.pop("_meta")
        red = [r for c in res.values() if c["part"] == "mmlu_redux" for r in c["rows"]]
        hit = [r for r in red if r["direct"] and r["direct"] == r["cot"] and r["direct"] != r["label"]]
        n = {t: sum(r["truth"] == t for r in red) for t in ("wrong", "ok", "ambiguous")}
        h = {t: sum(r["truth"] == t for r in hit) for t in ("wrong", "ok", "ambiguous")}
        recall, precision = h["wrong"] / n["wrong"], h["wrong"] / max(1, h["wrong"] + h["ok"])
        base = n["wrong"] / (n["wrong"] + n["ok"])
        row = {"rows": len(red), "confident_share": round(sum(bool(r["direct"]) and r["direct"] == r["cot"] for r in red) / len(red), 4),
               "wrong_rows": n["wrong"], "wrong_contradicted": h["wrong"], "ok_rows": n["ok"], "ok_contradicted": h["ok"],
               "ambiguous_rows": n["ambiguous"], "ambiguous_contradicted": h["ambiguous"], "recall": round(recall, 4),
               "precision": round(precision, 4), "listed_share": round(len(hit) / len(red), 4), "base_rate": round(base, 4),
               "lift": round(precision / base, 2), "detects_row_by_row": recall >= 0.5 and precision >= 0.5,
               "useful_review_list": recall >= 0.5 and precision / base >= 5}
        case = {k: {**tally(c["rows"]), "part": c["part"], "noisy": c["noisy"], "wrong_share": round(sum(r["truth"] == "wrong" for r in c["rows"]) / len(c["rows"]), 4)}
                for k, c in res.items()}

        def flagged(sel, line):
            ks = [k for k, c in case.items() if sel(c)]
            return f"{sum((case[k]['disagree'] or 0) >= line for k in ks)} of {len(ks)}"
        groups = {"redux_noisy": lambda c: c["part"] == "mmlu_redux" and c["noisy"], "redux_clean": lambda c: c["part"] == "mmlu_redux" and not c["noisy"],
                  "planted_30": lambda c: c["part"] == "planted_labels", "fantastic_bugs_clean": lambda c: c["part"] == "fbugs"}
        rep[meta["model"]] = {"cost_usd": meta["cost_usd"], "row_level_mmlu_redux": row,
                              "case_level": {f"line_{line}": {g: flagged(s, line) for g, s in groups.items()} for line in (LINE, 0.20)},
                              "planted_rows": {"wrong_contradicted": sum(r["truth"] == "wrong" and r["direct"] == r["cot"] and r["direct"] and r["direct"] != r["label"]
                                                                         for c in res.values() if c["part"] == "planted_labels" for r in c["rows"]),
                                               "wrong": sum(r["truth"] == "wrong" for c in res.values() if c["part"] == "planted_labels" for r in c["rows"])},
                              "cases": case}
        print(meta["model"], json.dumps({k: v for k, v in rep[meta["model"]].items() if k != "cases"}, indent=1))
    (ROOT / "out" / "test_v5_claude_report.json").write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    {"run": lambda: run(sys.argv[2]), "report": report}[sys.argv[1]]()
