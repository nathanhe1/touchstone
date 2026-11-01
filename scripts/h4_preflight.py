"""Round 4 pre-flight: no training. Base accuracy, truncation and reply length per family at each size.

    python scripts/h4_preflight.py [n_items]

Same prompt and token limit at every size. Writes out/h4_preflight.json after every family.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import h4_common as H  # noqa: E402
from touchstone import lm as L  # noqa: E402

F = ROOT / "out" / "h4_preflight.json"
MAX_NEW = 16


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    res = json.loads(F.read_text()) if F.exists() else {}
    for size in ("135M", "360M", "1.7B"):
        lm = L.LM(size)
        for fam, (ms, ss) in H.SPLITS.items():
            key = f"{fam}|{size}"
            if key in res:
                continue
            it = H.items(fam, ss)[:n]
            if len(it) < 100:
                print(key, "too few", len(it), flush=True)
                continue
            t = time.time()
            outs = lm.generate([x[0] for x in it], max_new=MAX_NEW, batch=32)
            acc = sum(H.correct(o, x[1]) for o, x in zip(outs, it)) / len(it)
            cut = sum(len(lm.tok(o, add_special_tokens=False).input_ids) >= MAX_NEW - 1 for o in outs) / len(it)
            has = sum(H._FIRST.search(o) is not None for o in outs) / len(it)
            res[key] = {"acc": round(100 * acc, 1), "chance": round(100 * sum(x[2] for x in it) / len(it), 1), "truncated": round(100 * cut, 1),
                        "has_letter": round(100 * has, 1), "n": len(it), "material_n": len(H.items(fam, ms)), "sample": outs[:2], "s": round(time.time() - t)}
            F.write_text(json.dumps(res, indent=1))
            print(key, {k: v for k, v in res[key].items() if k != "sample"}, res[key]["sample"], flush=True)
        del lm
        L.free_memory()


if __name__ == "__main__":
    main()
