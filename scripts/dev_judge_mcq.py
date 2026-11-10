"""Sprint priority 4: does a 7-8B instruct judge make the two-route multiple-choice check (`audit_mcq2`) travel?

Development data only: 8 multiple-choice sources from their train splits, disjoint from test v5 (no MMLU, no OpenBookQA
test). Per source, 2 clean draws and 1 draw with 30% of labels replaced by a wrong letter, 150 rows each. Every row's two
routes are stored, so thresholds are tuned afterwards on the Mac, leave-one-source-out, without more GPU time.

    python scripts/dev_judge_mcq.py build                    # Mac: writes examples/dev_judge/ from ~/.cache/touchstone/h5src
    TOUCHSTONE_JUDGE_BACKEND=torch TOUCHSTONE_JUDGE_DTYPE=bfloat16 \
      python scripts/dev_judge_mcq.py run Qwen/Qwen2.5-7B-Instruct   # GPU: out/dev_judge_mcq_<model>.json
    python scripts/dev_judge_mcq.py run Qwen/Qwen2.5-1.5B-Instruct   # the current judge on the same backend and rows
    python scripts/dev_judge_mcq.py tune                     # Mac: leave-one-source-out thresholds, out/dev_judge_mcq_tune.json
"""
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
SOURCES = {"arc": "train", "arc_easy": "train", "csqa": "train", "sciq": "train", "qasc": "train", "medmcqa": "train", "aqua": "train",
           "openbook": "train"}
D = ROOT / "examples" / "dev_judge"
PER, SEED = 150, 20261110


def build():
    os.environ.setdefault("H4_DATA", str(Path.home() / ".cache" / "touchstone" / "h5src"))
    import h4_common as H
    H.D = Path(os.environ["H4_DATA"])
    D.mkdir(parents=True, exist_ok=True)
    man = []
    for src, split in SOURCES.items():
        it = [(p.replace("\nReply with the letter only.", ""), a) for p, a, _ in H.items(src, split)]
        rng = random.Random(f"{SEED}|{src}")
        rng.shuffle(it)
        if len(it) < 3 * PER:
            print("skip", src, len(it))
            continue
        for k, name in enumerate(["clean_0", "clean_1", "planted_30"]):
            rows = [{"prompt": p, "completion": a, "wrong": False} for p, a in it[k * PER:(k + 1) * PER]]
            if name == "planted_30":
                for i in rng.sample(range(PER), int(0.3 * PER)):
                    n = sum(1 for line in rows[i]["prompt"].splitlines() if len(line) > 2 and line[1] == ")" and line[0].isupper())
                    rows[i]["completion"] = rng.choice([c for c in "ABCDEFGHIJ"[:n] if c != rows[i]["completion"]])
                    rows[i]["wrong"] = True
            f = D / f"{src}_{name}.jsonl"
            f.write_text("".join(json.dumps(r) + "\n" for r in rows))
            man.append({"source": src, "split": split, "draw": name, "rows": PER, "wrong": sum(r["wrong"] for r in rows), "path": f.name})
    (D / "manifest.json").write_text(json.dumps(man, indent=1))
    print(len(man), "draws")


def run(model):
    from touchstone import judge
    from touchstone.coverage import mcq_label
    judge.use_judge(model)
    out_f = ROOT / "out" / f"dev_judge_mcq_{model.split('/')[-1]}.json"
    res = json.loads(out_f.read_text()) if out_f.exists() else {}
    t0 = time.time()
    for m in json.loads((D / "manifest.json").read_text()):
        key = f"{m['source']}_{m['draw']}"
        if key in res:
            continue
        rows = [json.loads(x) for x in (D / m["path"]).read_text().splitlines()]
        q = [r["prompt"] for r in rows]
        d = [mcq_label(o) or (o.strip()[:1].upper() if o.strip() else None) for o in judge._gen(q, judge.MCQ_SYS, 6, batch=32)]
        c = [judge._BOX.findall(o) for o in judge._gen(q, judge.MCQ_COT, 240, batch=32)]
        c = [(mcq_label(x[-1]) or x[-1].strip()[:1].upper()) if x else None for x in c]
        res[key] = {"source": m["source"], "draw": m["draw"],
                    "rows": [{"direct": a, "cot": b, "label": r["completion"], "wrong": r["wrong"]} for a, b, r in zip(d, c, rows)]}
        out_f.write_text(json.dumps(res))
        conf = [x for x in res[key]["rows"] if x["direct"] and x["direct"] == x["cot"]]
        print(key, f"confident {len(conf)}/{len(rows)}", f"disagree {sum(x['direct'] != x['label'] for x in conf) / max(1, len(conf)):.3f}",
              f"{time.time() - t0:.0f}s", flush=True)
    res["_meta"] = {"model": model, "backend": "torch" if not judge._has_mlx() else "mlx", "dtype": os.environ.get("TOUCHSTONE_JUDGE_DTYPE", "float32"),
                    "seconds": round(time.time() - t0)}
    out_f.write_text(json.dumps(res))


def disagree(rows, n=60, seed=0):
    """audit_mcq2's statistic on the product's sample size: share of confident rows (both routes agree) that contradict the label."""
    s = random.Random(seed).sample(rows, min(n, len(rows)))
    conf = [r for r in s if r["direct"] and r["direct"] == r["cot"]]
    return (sum(r["direct"] != r["label"] for r in conf) / len(conf)) if len(conf) >= 10 else None, len(conf)


def tune():
    out = {}
    for f in sorted((ROOT / "out").glob("dev_judge_mcq_*.json")):
        if f.name.endswith("_tune.json"):
            continue
        R = {k: v for k, v in json.loads(f.read_text()).items() if not k.startswith("_")}
        srcs = sorted({v["source"] for v in R.values()})
        # each draw read 5 times at the product's sample of 60 rows (seeds 0-4), as the product would see it
        reads = {k: [disagree(v["rows"], 60, s)[0] for s in range(5)] for k, v in R.items()}
        rows_all = {k: v["rows"] for k, v in R.items()}
        clean_rate = {}
        for src in srcs:
            rr = [r for k, v in rows_all.items() if v and R[k]["source"] == src and R[k]["draw"].startswith("clean") for r in v]
            conf = [r for r in rr if r["direct"] and r["direct"] == r["cot"]]
            clean_rate[src] = {"confident": len(conf), "of": len(rr), "disagree": round(sum(r["direct"] != r["label"] for r in conf) / max(1, len(conf)), 4)}
        loso = {}
        for held in srcs:
            train = {k: v for k, v in reads.items() if R[k]["source"] != held}
            cl = [x for k, v in train.items() if R[k]["draw"].startswith("clean") for x in v if x is not None]
            no = [x for k, v in train.items() if R[k]["draw"] == "planted_30" for x in v if x is not None]
            thr = (max(cl) + min(no)) / 2 if cl and no and max(cl) < min(no) else (sorted(cl)[-1] + 0.01 if cl else None)  # midpoint if separable, else just above every clean read
            test = {k: v for k, v in reads.items() if R[k]["source"] == held}
            fp = sum(x >= thr for k, v in test.items() if R[k]["draw"].startswith("clean") for x in v if x is not None)
            n_cl = sum(x is not None for k, v in test.items() if R[k]["draw"].startswith("clean") for x in v)
            tp = sum(x >= thr for k, v in test.items() if R[k]["draw"] == "planted_30" for x in v if x is not None)
            n_no = sum(x is not None for k, v in test.items() if R[k]["draw"] == "planted_30" for x in v)
            loso[held] = {"threshold": round(thr, 3) if thr is not None else None, "clean_reads_flagged": f"{fp} of {n_cl}", "planted_reads_flagged": f"{tp} of {n_no}"}
        fp = sum(int(v["clean_reads_flagged"].split()[0]) for v in loso.values())
        ncl = sum(int(v["clean_reads_flagged"].split()[-1]) for v in loso.values())
        tp = sum(int(v["planted_reads_flagged"].split()[0]) for v in loso.values())
        nno = sum(int(v["planted_reads_flagged"].split()[-1]) for v in loso.values())
        at30 = {"clean_flagged": sum(x >= 0.30 for k, v in reads.items() if R[k]["draw"].startswith("clean") for x in v if x is not None),
                "planted_flagged": sum(x >= 0.30 for k, v in reads.items() if R[k]["draw"] == "planted_30" for x in v if x is not None)}
        out[f.stem.replace("dev_judge_mcq_", "")] = {"clean_rate_by_source": clean_rate, "leave_one_source_out": loso,
                                                     "loso_total": {"clean_reads_flagged": f"{fp} of {ncl}", "planted_reads_flagged": f"{tp} of {nno}"},
                                                     "current_threshold_0.30_all_reads": at30}
    (ROOT / "out" / "dev_judge_mcq_tune.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: {"clean": v["clean_rate_by_source"], "loso": v["loso_total"]} for k, v in out.items()}, indent=1))


if __name__ == "__main__":
    {"build": build, "run": lambda: run(sys.argv[2]), "tune": tune}[sys.argv[1]]()
