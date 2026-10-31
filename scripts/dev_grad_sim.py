"""Gradient-similarity signal for environments (LESS, Xia et al. 2024; TracIn, Pruthi et al. 2020).

For each environment: cosine between the LoRA gradient of the task-answer loss and the gradient on the
held-out suite, at the untrained 135M. No GRPO run is needed, so it costs seconds per environment.
Resumable. Computed for every environment; only DEV environments may be used to choose anything.

    python scripts/dev_grad_sim.py
"""
import json
import random
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import validate_rl_real2 as V  # noqa: E402
from touchstone import lm as L  # noqa: E402
from touchstone import suites  # noqa: E402

F = ROOT / "out" / "dev_grad_sim.json"
N, MB = 48, 8


def grad(tuned, pairs):
    model = tuned.model
    params = [p for p in model.parameters() if p.requires_grad]
    model.train()
    model.zero_grad()
    for s in range(0, len(pairs), MB):
        pre = [p for p, _ in pairs[s:s + MB]]
        cont = [c + "<|im_end|>" for _, c in pairs[s:s + MB]]
        x, m, att = tuned._pack(pre, cont)
        lp, sel = tuned.token_logprobs(x, m, att)
        (-(lp.sum() / sel.sum()) / max(1, len(pairs) // MB)).backward()
        del x, m, att, lp, sel
        L.release_cache()
    g = torch.cat([p.grad.flatten().float().cpu() for p in params if p.grad is not None])
    model.eval()
    return torch.nn.functional.normalize(g, dim=0)


def main():
    res = json.loads(F.read_text()) if F.exists() else {}
    lm = L.LM("135M")
    tuned = L.with_lora(lm, L.Recipe(), 0)
    rng = random.Random(0)
    suite = suites.arithmetic_suite(V.SUITE_ITEMS)
    items = rng.sample(suite.items, N)
    gs = grad(tuned, [(tuned.chat(i.prompt), i.answer) for i in items])
    for name, env in V.environments().items():
        if name in res:
            continue
        tasks = random.Random(1).sample(env.tasks(), min(N, len(env.tasks())))
        g = grad(tuned, [(tuned.chat(t.prompt), t.meta["answer"]) for t in tasks])
        res[name] = round(float(g @ gs), 5)
        F.write_text(json.dumps(res, indent=1))
        print(name, res[name], flush=True)


if __name__ == "__main__":
    main()
