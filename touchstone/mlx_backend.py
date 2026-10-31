"""Apple MLX backend for dataset appraisals (`--device mlx`).

Same interface as ``lm.LM`` (chat, generate, candidate_probs, size) and the same
fixed recipe as ``lm.sft`` (LoRA rank 16 / scale 2.0 on every attention and MLP
projection, batch 16, AdamW 2e-4 with 5-step warm-up and linear decay,
completion-only loss, grad-norm clip 1.0), so the two backends measure the same
thing. RL (GRPO) stays on PyTorch MPS.
"""
from __future__ import annotations

import random
import time

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx_lm import load
from mlx_lm.generate import generate as mlx_generate
from mlx_lm.sample_utils import make_sampler
from mlx_lm.tuner.utils import linear_to_lora_layers
from mlx.utils import tree_map

from .lm import LADDER, PARAMS, Recipe

MICRO = {"1.7B": 4}  # micro-batch size per model (default: the whole batch of 16)
LORA_KEYS = ["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj",
             "mlp.gate_proj", "mlp.up_proj", "mlp.down_proj"]


class MLXLM:
    dev = "mlx"

    def __init__(self, size: str):
        self.size = size
        self.model, self.wrapper = load(LADDER[size])
        self.tok = getattr(self.wrapper, "_tokenizer", self.wrapper)
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token

    @property
    def n_params(self) -> int:
        return PARAMS[self.size]

    def chat(self, prompt: str, system: str | None = None) -> str:
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    def chat_messages(self, messages: list[dict]) -> str:
        return self.tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    def generate(self, prompts, max_new=64, temperature=0.0, batch=32, system=None, raw=False) -> list[str]:
        sampler = make_sampler(temp=temperature)
        out = []
        for p in prompts:
            text = p if raw else self.chat(p, system)
            r = mlx_generate(self.model, self.wrapper, prompt=text, max_tokens=max_new, sampler=sampler, verbose=False)
            out.append(r.split("<|im_end|>")[0].strip())
        return out

    def _pack(self, prefixes, conts):
        ids, masks = [], []
        for p, c in zip(prefixes, conts):
            a = self.tok(p, add_special_tokens=False).input_ids
            b = self.tok(c, add_special_tokens=False).input_ids
            ids.append(a + b)
            masks.append([0] * len(a) + [1] * len(b))
        L = -(-max(map(len, ids)) // 32) * 32
        pad = self.tok.pad_token_id
        return (mx.array([r + [pad] * (L - len(r)) for r in ids]),
                mx.array([r + [0] * (L - len(r)) for r in masks], dtype=mx.float32))

    def _token_logprobs(self, model, x, m):
        logits = model(x[:, :-1]).astype(mx.float32)
        lp = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
        tgt = mx.take_along_axis(lp, x[:, 1:, None], axis=-1).squeeze(-1)
        return tgt * m[:, 1:]

    def candidate_probs(self, prompts, answers, distractors, slots=None) -> list[float]:
        pre, cont, owner = [], [], []
        for i, (p, a, ds) in enumerate(zip(prompts, answers, distractors)):
            c = self.chat(p)
            slot = slots[i] if slots else None
            head, tail = (c + slot[0], slot[1]) if slot else (c, "<|im_end|>")
            for j, x in enumerate([a] + list(ds)):
                pre.append(head)
                cont.append(x + tail)
                owner.append(i)
        scores = []
        for s in range(0, len(pre), 32):
            x, m = self._pack(pre[s:s + 32], cont[s:s + 32])
            v = self._token_logprobs(self.model, x, m).sum(1)
            mx.eval(v)
            scores += v.tolist()
        per: dict[int, list[float]] = {}
        for i, v in zip(owner, scores):
            per.setdefault(i, []).append(v)
        out = []
        for i in range(len(prompts)):
            v = mx.array(per[i])
            out.append(mx.softmax(v)[0].item())
        return out


def reload(lm: MLXLM) -> MLXLM:
    """Fresh base weights for the next run (MLX LoRA layers are swapped in place)."""
    return MLXLM(lm.size)


def sft(lm: MLXLM, examples: list[tuple[str, str]], recipe: Recipe, seed: int = 0, steps: int | None = None,
        log=None) -> tuple[MLXLM, dict]:
    steps = steps or recipe.sft_steps
    mx.random.seed(seed)
    model = lm.model
    model.freeze()
    linear_to_lora_layers(model, len(model.layers), {"rank": recipe.lora_r, "scale": recipe.lora_alpha / recipe.lora_r,
                                                     "dropout": 0.0, "keys": LORA_KEYS})
    model.train()

    def loss_fn(model, x, m, n_tok):
        return -lm._token_logprobs(model, x, m).sum() / n_tok

    step_fn = nn.value_and_grad(model, loss_fn)
    micro = MICRO.get(lm.size, recipe.sft_batch)  # gradient accumulation keeps 1.7B inside 16 GB
    opt = optim.AdamW(learning_rate=recipe.sft_lr, weight_decay=0.0)
    rng = random.Random(seed)
    order: list[int] = []
    losses = []
    t0 = time.time()
    step_times, step_tokens = [], []
    mx.reset_peak_memory()
    for step in range(steps):
        ts = time.time()
        if len(order) < recipe.sft_batch:
            nxt = list(range(len(examples)))
            rng.shuffle(nxt)
            order += nxt
        idx, order = order[:recipe.sft_batch], order[recipe.sft_batch:]
        x, m = lm._pack([examples[i][0] for i in idx], [examples[i][1] + "<|im_end|>" for i in idx])
        x, m = x[:, :recipe.sft_max_len], m[:, :recipe.sft_max_len]
        opt.learning_rate = recipe.sft_lr * min(1.0, (step + 1) / 5) * max(0.0, 1 - step / steps)
        n_tok = m[:, 1:].sum()
        loss, grads = 0.0, None
        for s in range(0, x.shape[0], micro):
            part, g = step_fn(model, x[s:s + micro], m[s:s + micro], n_tok)
            grads = g if grads is None else tree_map(lambda a, b: a + b, grads, g)
            loss = loss + part
            mx.eval(loss, grads)
        grads, _ = optim.clip_grad_norm(grads, 1.0)
        opt.update(model, grads)
        mx.eval(loss, model.trainable_parameters(), opt.state)
        losses.append(loss.item())
        step_times.append(time.time() - ts)
        step_tokens.append(int((x != lm.tok.pad_token_id).sum().item()))
        if log and (step + 1) % 20 == 0:
            log(f"    sft(mlx) {lm.size} step {step + 1}/{steps} loss {sum(losses[-20:]) / 20:.3f}")
    model.eval()
    info = {"steps": steps, "examples_seen": steps * recipe.sft_batch,
            "unique_examples_used": min(len(examples), steps * recipe.sft_batch),
            "epochs": round(steps * recipe.sft_batch / max(1, len(examples)), 2),
            "loss_first": round(sum(losses[:5]) / 5, 4), "loss_last": round(sum(losses[-5:]) / 5, 4),
            "seconds": round(time.time() - t0, 1), "peak_memory_gb": round(mx.get_peak_memory() / 1e9, 2),
            "device": "mlx", "dtype": str(model.layers[0].mlp.down_proj.linear.weight.dtype).replace("mlx.core.", ""),
            "step_seconds": [round(t, 3) for t in step_times], "step_tokens": step_tokens}
    return lm, info
