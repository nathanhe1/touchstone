"""A tiny character-level GPT used as the CPU stand-in for real open models.

The scale ladder mirrors what a production appraisal would do with real
models (for example 0.5B, 1.5B and 3B, then a 7B check): same recipe, only
the width and depth change.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .vocab import BOS, EOS, MAX_OUT, PAD, VOCAB_SIZE, decode, encode

CTX = 24
PROMPT_W = 14  # prompts are left-padded to this width so the answer always starts at the same position

# name -> (d_model, n_layer, n_head)
SIZES = {
    "S": (32, 2, 2),
    "M": (64, 2, 4),
    "L": (96, 3, 4),
    "XL": (160, 4, 4),  # held back as the "large-scale truth" for validating forecasts
}


class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.attn = nn.MultiheadAttention(d, h, batch_first=True)
        self.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))

    def forward(self, x, mask):
        h = self.ln1(x)
        x = x + self.attn(h, h, h, attn_mask=mask, need_weights=False)[0]
        return x + self.mlp(self.ln2(x))


class TinyGPT(nn.Module):
    def __init__(self, size: str):
        super().__init__()
        d, n, h = SIZES[size]
        self.size = size
        self.tok = nn.Embedding(VOCAB_SIZE, d)
        self.pos = nn.Embedding(CTX, d)
        self.blocks = nn.ModuleList(Block(d, h) for _ in range(n))
        self.ln = nn.LayerNorm(d)
        self.head = nn.Linear(d, VOCAB_SIZE, bias=False)
        self.register_buffer(
            "mask", torch.triu(torch.full((CTX, CTX), float("-inf")), diagonal=1), persistent=False
        )

    def n_params(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def forward(self, idx):
        T = idx.shape[1]
        x = self.tok(idx) + self.pos(torch.arange(T, device=idx.device))
        for b in self.blocks:
            x = b(x, self.mask[:T, :T])
        return self.head(self.ln(x))


def prompt_batch(prompts: list[str]) -> tuple[torch.Tensor, list[int]]:
    """Left-pad prompts so every row ends at the same column."""
    enc = [([BOS] + encode(p))[-PROMPT_W:] for p in prompts]
    rows = [[PAD] * (PROMPT_W - len(e)) + e for e in enc]
    return torch.tensor(rows), [len(e) for e in enc]


@torch.no_grad()
def generate(model, prompts: list[str], greedy: bool = True, temp: float = 1.0):
    """Return (texts, sequences, prompt_len). Sequences include the prompt."""
    idx, _ = prompt_batch(prompts)
    P = idx.shape[1]
    done = torch.zeros(len(prompts), dtype=torch.bool)
    for _ in range(MAX_OUT):
        logits = model(idx[:, -CTX:])[:, -1, :] / temp
        logits[:, PAD] = float("-inf")
        logits[:, BOS] = float("-inf")
        nxt = logits.argmax(-1) if greedy else torch.multinomial(F.softmax(logits, -1), 1).squeeze(1)
        nxt = torch.where(done, torch.full_like(nxt, PAD), nxt)
        idx = torch.cat([idx, nxt[:, None]], 1)
        done |= nxt == EOS
        if done.all():
            break
    texts = [decode(row[P:]) for row in idx.tolist()]
    return texts, idx, P


def token_logprobs(model, seqs: torch.Tensor, P: int) -> tuple[torch.Tensor, torch.Tensor]:
    """Per-token log-probs of generated tokens (after column P) and a mask of real tokens."""
    logits = model(seqs[:, :-1])
    logp = F.log_softmax(logits, -1)
    tgt = seqs[:, 1:]
    lp = logp.gather(-1, tgt[..., None]).squeeze(-1)
    keep = torch.zeros_like(lp, dtype=torch.bool)
    keep[:, P - 1:] = True
    keep &= tgt != PAD
    return lp, keep


def seq_logprobs(model, seqs: torch.Tensor, P: int) -> torch.Tensor:
    """Sum of log-probs of generated tokens, ignoring padding."""
    lp, keep = token_logprobs(model, seqs, P)
    return (lp * keep).sum(1)
