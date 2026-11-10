"""Sprint ladder pre-flight: no training. Base accuracy against chance, truncation and reply format per family, at every
rung of a candidate ladder, on the corrected (seeded) fetch. Each model is loaded once.

    python scripts/h5_preflight.py q3-0.6B,q3-1.7B,q3-4B,q3-8B out/h5/preflight/qwen3.json [fam1,fam2,...]

Also the chance-corrected soft score (scripts/h5_soft.py: probability on the correct option among the options, 0 at
chance), which does not depend on whether a base model follows the reply format.

Same prompt and reply limit at every size: 32 tokens for letter families, 320 for number families (worked replies).
Writes after every family, resumes from what is there. Per-item correctness is stored so nothing needs rerunning.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import h5_run as R  # noqa: E402
import h5_soft  # noqa: E402
from touchstone import lm as L  # noqa: E402

NUM_MAX_NEW = 320


def main():
    sizes, dest = sys.argv[1].split(","), Path(sys.argv[2])
    fams = sys.argv[3].split(",") if len(sys.argv) > 3 else R.CFG["families"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    res = json.loads(dest.read_text()) if dest.exists() else {}
    for size in sizes:
        lm = None
        for fam in fams:
            key = f"{fam}|{size}"
            if key in res:
                continue
            it = R.suite(fam)
            if len(it) < 100:
                print(key, "too few", len(it), flush=True)
                continue
            lm = lm or L.LM(size)
            mx = NUM_MAX_NEW if R.is_numeric(fam) else R.CFG["recipe"]["max_new"]
            t = time.time()
            outs = lm.generate([x[0] for x in it], max_new=mx, batch=64 if not R.is_numeric(fam) else 32)
            ok = [R.correct(fam, o, x[1]) for o, x in zip(outs, it)]
            cut = sum(len(lm.tok(o, add_special_tokens=False).input_ids) >= mx - 1 for o in outs) / len(it)
            ts = time.time()
            soft = h5_soft.soft_scores(lm, it, outs)
            soft_mean = h5_soft.mean_soft(soft)
            res[key] = {"soft": None if soft_mean is None else round(100 * soft_mean, 2), "soft_s": round(time.time() - ts, 1),
                        "acc": round(100 * sum(ok) / len(it), 2), "chance": round(100 * sum(x[2] for x in it) / len(it), 2),
                        "truncated": round(100 * cut, 2), "n": len(it), "max_new": mx,
                        "has_letter": None if R.is_numeric(fam) else round(100 * sum(R.H._FIRST.search(o) is not None for o in outs) / len(it), 2),
                        "bits": "".join("1" if x else "0" for x in ok), "sample": outs[:3], "s": round(time.time() - t, 1),
                        "model": L.LADDER[size]}
            dest.write_text(json.dumps(res, indent=1))
            print(key, {k: v for k, v in res[key].items() if k not in ("sample", "bits")}, flush=True)
        del lm
        L.free_memory()


if __name__ == "__main__":
    main()
