"""DEV ONLY: public-copy rate on dev / test v1 / test v2 word_math datasets, with the wider corpus. Never test v3.

Resumable; writes out/dev_public.json after every dataset. Reports each overlap tier, so a miss can be traced.
"""
import glob
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import data, overlap, pipeline  # noqa: E402

F = ROOT / "out" / "dev_public.json"
res = json.loads(F.read_text()) if F.exists() else {}
pub, label = pipeline.public_baseline(None, "word_math")
print(label, flush=True)
DEV_TRUE = {"gsm8k_clone"}
for folder in ["examples/datasets", "examples/redflags_test", "examples/redflags_test2"]:
    mf = ROOT / folder / "manifest.json"
    man = {Path(m["path"]).stem: m for m in json.loads(mf.read_text())} if mf.exists() else {}
    for f in sorted(glob.glob(str(ROOT / folder / "**/*.jsonl"), recursive=True)):
        n = Path(f).stem
        if n in res or (n in man and man[n]["suite"] != "word_math"):
            continue
        prompts = [e.prompt_text for e in data.load_dataset(f)]
        t = time.time()
        m = overlap.match(prompts, pub, use_embeddings=len(prompts) * len(pub) < 5e7)
        fp = overlap.fingerprint_overlap(prompts, pub)
        long_hits = sum(1 for i in m["matched_idx"] if not overlap._short_numeric(prompts[i]))
        truth = man[n]["labels"]["copied_from_public"] if n in man else n in DEV_TRUE
        res[n] = {"truth": truth, "text": round(m["rate"], 3), "exact": round(m["exact"], 3), "near": round(m["near"], 3),
                  "para": round(m["paraphrase"], 3), "fp": fp["rate"], "final": round(long_hits / len(prompts) + fp["rate"], 3),
                  "seconds": round(time.time() - t)}
        F.write_text(json.dumps(res, indent=1))
        print(n, res[n], flush=True)
