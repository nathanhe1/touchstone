"""Why does 1.7B evaluation exhaust 16 GB? Compare generation variants on the held-out suite.

    python scripts/bench_eval_memory.py 1.7B dynamic 16
    python scripts/bench_eval_memory.py 1.7B static 16

Reports wall time, MPS driver memory after each batch, and accuracy (must match across variants).
"""
import json
import resource
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import lm as L  # noqa: E402
from touchstone import suites  # noqa: E402
from touchstone.suites import is_correct  # noqa: E402

size, mode, batch = sys.argv[1], sys.argv[2], int(sys.argv[3])
n_items = int(sys.argv[4]) if len(sys.argv) > 4 else 64
suite = suites.word_math_suite().subset(n_items)
m = L.LM(size)
tok = m.tok
tok.padding_side = "left"
texts = [m.chat(it.prompt) for it in suite.items]
peaks, outs = [], []
t0 = time.time()
for s in range(0, len(texts), batch):
    chunk = texts[s:s + batch]
    kw = dict(pad_to_multiple_of=32) if mode != "dynamic" else {}
    enc = tok(chunk, return_tensors="pt", padding=True, **kw).to(m.dev)
    gkw = dict(do_sample=False, max_new_tokens=96, pad_token_id=tok.pad_token_id, eos_token_id=m.end_id)
    if mode == "static":
        gkw["cache_implementation"] = "static"
    with torch.no_grad():
        g = m.model.generate(**enc, **gkw)
    outs += tok.batch_decode(g[:, enc.input_ids.shape[1]:], skip_special_tokens=True)
    L.release_cache()
    peaks.append(round(torch.mps.driver_allocated_memory() / 1e9, 2))
acc = sum(is_correct(o.strip(), it) for o, it in zip(outs, suite.items)) / len(outs)
r = {"size": size, "mode": mode, "batch": batch, "items": len(outs), "seconds": round(time.time() - t0, 1),
     "driver_gb_after_batches": peaks, "max_rss_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2),
     "accuracy": round(acc, 3)}
print(json.dumps(r), flush=True)
with open(ROOT / "out" / "eval_memory.jsonl", "a") as f:
    f.write(json.dumps(r) + "\n")
