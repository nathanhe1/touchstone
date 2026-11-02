"""Why is 1.7B's base accuracy below 360M's? Runs the untrained models on the arithmetic suite.

    python scripts/debug_17_base.py      # GPU box, about 5 minutes; no training

Varies size, dtype and the reply length limit. For each, it prints accuracy on the first 200 items, the share of
replies cut off at the limit, and a few raw replies. Truncation points to a format artefact, and a dtype gap to
numerics.
"""
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import lm as L  # noqa: E402
from touchstone import suites  # noqa: E402

suite = suites.arithmetic_suite(600).subset(200)
prompts = [i.prompt for i in suite.items]
for size, dtype in (("360M", torch.float32), ("1.7B", torch.float16), ("1.7B", torch.float32)):
    L.DTYPE[size] = dtype
    lm = L.LM(size)
    finite = True
    with torch.no_grad():
        enc = lm.tok([lm.chat(prompts[0])], return_tensors="pt").to(lm.dev)
        finite = bool(torch.isfinite(lm.model(**enc).logits).all())
    for max_new in (48, 96, 200):
        outs = lm.generate(prompts, max_new=max_new, batch=32)
        acc = sum(suites.is_correct(o, it) for o, it in zip(outs, suite.items)) / len(outs)
        cut = sum(len(lm.tok(o, add_special_tokens=False).input_ids) >= max_new - 2 for o in outs) / len(outs)
        words = sum(len(o.split()) for o in outs) / len(outs)
        print(f"{size} {dtype} finite={finite} max_new={max_new}: acc {100 * acc:.1f}% truncated {100 * cut:.1f}% mean words {words:.1f}", flush=True)
        if max_new == 48:
            for o in outs[:3]:
                print("   ", repr(o[:120]), flush=True)
    del lm
    L.free_memory()
