"""Build the "base models": each size is briefly pretrained on a generic mix.

This stands in for starting from a real pretrained open model. Base models are
deliberately only partly skilled, so RL on an environment has room to help.
"""
from __future__ import annotations

import random
import string

import torch
import torch.nn.functional as F

from .model import PROMPT_W, TinyGPT, prompt_batch
from .vocab import EOS, PAD, encode


def _example(rng: random.Random) -> tuple[str, str]:
    r = rng.random()
    if r < 0.45:
        a, b = rng.randint(10, 99), rng.randint(10, 99)
        return f"{a}+{b}=", str(a + b)
    if r < 0.65:
        a, b = rng.randint(100, 999), rng.randint(10, 99)
        return f"{a}+{b}=", str(a + b)
    s = "".join(rng.choice(string.ascii_lowercase[:12]) for _ in range(rng.randint(3, 6)))
    if r < 0.85:
        return f"rev {s}>", s[::-1]
    return f"cp {s}>", s


def batch(rng, n):
    pairs = [_example(rng) for _ in range(n)]
    idx, _ = prompt_batch([p for p, _ in pairs])
    ans = [encode(a) + [EOS] for _, a in pairs]
    L = max(map(len, ans))
    tail = torch.tensor([a + [PAD] * (L - len(a)) for a in ans])
    return torch.cat([idx, tail], 1)


def pretrain(size: str, steps: int = 500, seed: int = 0) -> TinyGPT:
    torch.manual_seed(seed)
    rng = random.Random(seed)
    model = TinyGPT(size)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    for _ in range(steps):
        seqs = batch(rng, 128)
        logits = model(seqs[:, :-1])
        tgt = seqs[:, 1:].clone()
        tgt[:, : PROMPT_W - 1] = PAD  # only learn the answer
        loss = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), tgt.reshape(-1), ignore_index=PAD)
        opt.zero_grad()
        loss.backward()
        opt.step()
    return model
