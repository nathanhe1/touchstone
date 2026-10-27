"""RL training backends.

``ToyGRPO`` runs group-relative policy optimization on the tiny CPU models.
A production backend (for example TRL's GRPOTrainer or the Tinker API on real
open models) implements the same ``train(base, env, steps) -> (model, curve)``
signature, so the rest of the appraisal pipeline does not change.
"""
from __future__ import annotations

import copy
import random

import torch

from .model import SIZES, generate, token_logprobs


class ToyGRPO:
    def __init__(self, steps=400, prompts_per_step=32, group=8, lr=3e-4, kl=0.5, temp=1.0, seed=0):
        self.steps, self.B, self.G, self.temp, self.seed = steps, prompts_per_step, group, temp, seed
        self.lr, self.kl = lr, kl

    def lr_for(self, model) -> float:
        # muP-style width scaling: the base rate is tuned at width 96 and shrinks as models widen.
        return self.lr * 96 / SIZES[model.size][0]

    def train(self, base, env):
        torch.manual_seed(self.seed)
        rng = random.Random(self.seed)
        model = copy.deepcopy(base)
        model.train()
        opt = torch.optim.AdamW(model.parameters(), lr=self.lr_for(model))
        tasks = env.tasks()
        curve = []
        for _ in range(self.steps):
            batch = [rng.choice(tasks) for _ in range(self.B)]
            group = [t for t in batch for _ in range(self.G)]
            texts, seqs, P = generate(model, [t.prompt for t in group], greedy=False, temp=self.temp)
            r = torch.tensor([env.verify(t, o) for t, o in zip(group, texts)]).view(self.B, self.G)
            adv = (r - r.mean(1, keepdim=True)) / (r.std(1, keepdim=True) + 1e-4)
            curve.append(r.mean().item())
            if adv.abs().sum() == 0:
                continue
            lp, keep = token_logprobs(model, seqs, P)
            with torch.no_grad():
                ref, _ = token_logprobs(base, seqs, P)
            d = ref - lp
            kl = ((torch.exp(d) - d - 1) * keep).sum(1) / keep.sum(1).clamp(min=1)
            pg = -(adv.view(-1) * (lp * keep).sum(1))
            loss = (pg + self.kl * kl).mean()
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        model.eval()
        return model, curve


class TRLBackend:  # pragma: no cover - needs GPUs and real models
    """Placeholder for the production trainer (TRL GRPOTrainer / Tinker).

    Wraps an Environment's ``tasks()`` as the prompt dataset and its
    ``verify()`` as the reward function, and runs the fixed published recipe
    on the scale ladder (e.g. Qwen 0.5B / 1.5B / 3B, checked against 7B).
    """

    def train(self, base, env):
        raise NotImplementedError("Run on a GPU host with `pip install trl` and model weights.")
