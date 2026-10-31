"""Real open language models: the scale ladder, generation, scoring and LoRA SFT.

The ladder is one model family trained with one recipe, so size is the only
thing that changes between rungs:

    135M, 360M  -> SmolLM2-{135M,360M}-Instruct   (the cheap rungs every appraisal runs)
    1.7B        -> SmolLM2-1.7B-Instruct          (the largest size this laptop can train;
                                                   the forecast target we validate against)

Every rung is trained with the same LoRA recipe (rank 16 on all linear layers).
Runs on Apple MPS with float16 base weights (LoRA adapters train in float32)
and eager attention: the fused attention path
returns garbage for left-padded batches in torch 2.8, bf16 is slower there,
and float32 1.7B does not fit alongside training state in 16 GB.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass

import torch

LADDER = {
    "135M": "HuggingFaceTB/SmolLM2-135M-Instruct",
    "360M": "HuggingFaceTB/SmolLM2-360M-Instruct",
    "1.7B": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
    "7B": "Qwen/Qwen2.5-7B-Instruct",  # a different family: GPU-only forecast target, never a product rung
}
PARAMS = {"135M": 134_515_008, "360M": 361_821_120, "1.7B": 1_711_376_384, "7B": 7_615_616_512}
DTYPE = {"135M": torch.float32, "360M": torch.float32, "1.7B": torch.float16, "7B": torch.float16}
SMALL = ["135M", "360M"]
TARGET = "1.7B"


_DEVICE: str | None = None


def set_device(requested: str = "auto") -> str:
    """Pick the PyTorch device: 'auto' and 'mps' use the Apple GPU; CPU only as a warned fallback."""
    global _DEVICE
    if requested not in ("auto", "mps", "cuda", "cpu"):
        raise ValueError(f"unknown torch device {requested!r}")
    if requested == "cpu":
        _DEVICE = "cpu"
    elif torch.backends.mps.is_available() and requested in ("auto", "mps"):
        _DEVICE = "mps"
    elif torch.cuda.is_available() and requested in ("auto", "cuda"):
        _DEVICE = "cuda"
    else:
        import sys
        print("WARNING: no GPU available (Apple MPS or CUDA); falling back to CPU. Training will be much slower.",
              file=sys.stderr, flush=True)
        _DEVICE = "cpu"
    return _DEVICE


def device() -> str:
    return _DEVICE or set_device("auto")


def dtype_for(size: str):
    """fp32 on CPU (fp16 matmuls are slow there); on MPS fp32 for the small rungs, fp16 for 1.7B to fit memory."""
    return torch.float32 if device() == "cpu" else DTYPE[size]


def cached(load, repo, **kw):
    """Load from the local Hugging Face cache; only go to the network if it is missing."""
    try:
        return load(repo, local_files_only=True, **kw)
    except OSError:
        return load(repo, **kw)


def memory_in_use() -> int:
    """Bytes held: the MPS driver allocation on the GPU, peak resident set on CPU."""
    if device() == "cuda":
        return torch.cuda.max_memory_allocated()
    if device() == "mps":
        return torch.mps.driver_allocated_memory()
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # bytes on macOS


def release_cache():
    """MPS keeps freed blocks cached; with varying shapes the cache grows to many GB."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()


def free_memory():
    import gc
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()


@dataclass
class Recipe:
    """The fixed, published training recipe. Identical at every rung."""
    lora_r: int = 16
    lora_alpha: int = 32
    sft_lr: float = 2e-4
    sft_batch: int = 16
    sft_steps: int = 60
    sft_max_len: int = 256
    rl_lr: float = 5e-5
    rl_steps: int = 40
    rl_prompts: int = 8
    rl_group: int = 8
    rl_kl: float = 0.04
    rl_max_new: int = 24
    eval_max_new: int = 96


class LM:
    """A ladder rung: tokenizer + model (optionally with a LoRA adapter)."""

    def __init__(self, size: str, model=None, tok=None):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        if size not in LADDER:
            raise ValueError(f"unknown size {size}; ladder is {list(LADDER)}")
        self.size = size
        self.dev = device()
        self.tok = tok or cached(AutoTokenizer.from_pretrained, LADDER[size])
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.model = model or cached(AutoModelForCausalLM.from_pretrained,
            LADDER[size], dtype=dtype_for(size), attn_implementation="eager").to(self.dev)
        self.model.eval()
        self.end_id = self.tok.convert_tokens_to_ids("<|im_end|>")

    @property
    def n_params(self) -> int:
        return PARAMS[self.size]

    # ------------------------------------------------------------ formatting
    def chat(self, prompt: str, system: str | None = None) -> str:
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    def chat_messages(self, messages: list[dict]) -> str:
        return self.tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    # ------------------------------------------------------------ generation
    @torch.no_grad()
    def generate(self, prompts: list[str], max_new: int = 64, temperature: float = 0.0, batch: int = 32,
                 system: str | None = None, raw: bool = False) -> list[str]:
        """Replies to user prompts (or raw chat-formatted strings if raw=True)."""
        self.tok.padding_side = "left"
        texts = prompts if raw else [self.chat(p, system) for p in prompts]
        if self.size in ("1.7B", "7B"):  # bounded memory
            batch = min(batch, 16)
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        out = [""] * len(texts)
        for s in range(0, len(order), batch):
            idx = order[s:s + batch]
            enc = self.tok([texts[i] for i in idx], return_tensors="pt", padding=True).to(self.dev)
            kw = dict(do_sample=True, temperature=temperature, top_k=0, top_p=1.0) if temperature > 0 else dict(do_sample=False)
            gen = self.model.generate(**enc, max_new_tokens=max_new, pad_token_id=self.tok.pad_token_id,
                                      eos_token_id=self.end_id, **kw)
            dec = self.tok.batch_decode(gen[:, enc.input_ids.shape[1]:], skip_special_tokens=True)
            for i, d in zip(idx, dec):
                out[i] = d.strip()
            release_cache()
        return out

    # ------------------------------------------------------------ scoring
    def _pack(self, prefixes: list[str], conts: list[str]):
        """Right-padded ids of prefix+continuation, with a mask over continuation tokens."""
        ids, masks = [], []
        for p, c in zip(prefixes, conts):
            a = self.tok(p, add_special_tokens=False).input_ids
            b = self.tok(c, add_special_tokens=False).input_ids
            ids.append(a + b)
            masks.append([0] * len(a) + [1] * len(b))
        L = -(-max(map(len, ids)) // 32) * 32  # bucket lengths: fewer distinct shapes, less allocator fragmentation
        pad = self.tok.pad_token_id
        x = torch.tensor([r + [pad] * (L - len(r)) for r in ids], device=self.dev)
        m = torch.tensor([r + [0] * (L - len(r)) for r in masks], device=self.dev)
        att = torch.tensor([[1] * len(r) + [0] * (L - len(r)) for r in ids], device=self.dev)
        return x, m, att

    def token_logprobs(self, x, m, att):
        """Log-probs of the masked (continuation) tokens, shape (B, T-1), zeros elsewhere.

        The output head runs only at continuation positions: a full (B, T, 49k)
        log-softmax is most of the cost of scoring short answers otherwise.
        """
        out = self.model(input_ids=x, attention_mask=att, output_hidden_states=True, logits_to_keep=1)
        h = out.hidden_states[-1][:, :-1]
        sel = m[:, 1:].bool()
        logits = self.model.get_output_embeddings()(h[sel]).float()
        lp = torch.log_softmax(logits, -1).gather(-1, x[:, 1:][sel][:, None]).squeeze(-1)
        return torch.zeros(sel.shape, device=lp.device, dtype=lp.dtype).masked_scatter(sel, lp), sel

    def seq_logprob(self, prefixes: list[str], conts: list[str], batch: int = 32, grad: bool = False):
        """Sum of log-probs of each continuation given its prefix."""
        if self.size in ("1.7B", "7B"):
            batch = min(batch, 16)
        res = []
        for s in range(0, len(prefixes), batch):
            x, m, att = self._pack(prefixes[s:s + batch], conts[s:s + batch])
            with torch.set_grad_enabled(grad):
                lp, _ = self.token_logprobs(x, m, att)
                res.append(lp.sum(1))
            if not grad:
                release_cache()
        return torch.cat(res)

    @torch.no_grad()
    def candidate_probs(self, prompts: list[str], answers: list[str], distractors: list[list[str]],
                        slots: list[tuple[str, str] | None] | None = None) -> list[float]:
        """P(correct) / P(correct or any distractor), per item. Chance is 1/(1+k).

        slots[i] = (reply_prefix, terminator): score each candidate in the answer
        slot of the model's own reply ("... 73 + 6 = [79]."), so the score does
        not depend on whether the model was trained to reason first or answer
        directly. Without a slot, the candidate is scored as the whole reply.
        """
        pre, cont, owner = [], [], []
        for i, (p, a, ds) in enumerate(zip(prompts, answers, distractors)):
            c = self.chat(p)
            slot = slots[i] if slots else None
            head, tail = (c + slot[0], slot[1]) if slot else (c, "<|im_end|>")
            for j, x in enumerate([a] + list(ds)):
                pre.append(head)
                cont.append(x + tail)
                owner.append((i, j))
        lp = self.seq_logprob(pre, cont).tolist()
        per: dict[int, list[float]] = {}
        for (i, j), v in zip(owner, lp):
            per.setdefault(i, []).append(v)
        out = []
        for i in range(len(prompts)):
            v = torch.tensor(per[i])
            out.append(torch.softmax(v, 0)[0].item())
        return out


# ---------------------------------------------------------------- LoRA

def with_lora(lm: LM, recipe: Recipe, seed: int) -> LM:
    from peft import LoraConfig, get_peft_model
    torch.manual_seed(seed)
    cfg = LoraConfig(r=recipe.lora_r, lora_alpha=recipe.lora_alpha, lora_dropout=0.0,
                     target_modules="all-linear", task_type="CAUSAL_LM")
    pm = get_peft_model(lm.model, cfg)
    return LM(lm.size, model=pm, tok=lm.tok)


def drop_lora(lm: LM) -> LM:
    """Remove the adapter so the base weights can be reused for the next run."""
    base = lm.model.unload()
    base.eval()
    return LM(lm.size, model=base, tok=lm.tok)


def sft(lm: LM, examples: list[tuple[str, str]], recipe: Recipe, seed: int = 0, steps: int | None = None,
        log=None) -> tuple[LM, dict]:
    """Supervised fine-tuning with LoRA on (chat-formatted prefix, completion) pairs.

    Loss is on completion tokens only. The step budget is fixed by the recipe, so
    every dataset gets the same compute; small datasets are repeated (epochs),
    large ones are subsampled.
    """
    steps = steps or recipe.sft_steps
    tuned = with_lora(lm, recipe, seed)
    model = tuned.model
    checkpointing = lm.size == "1.7B"  # recompute activations in backward: fits 1.7B training in ~6 GB
    if checkpointing:
        model.get_base_model().gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=recipe.sft_lr, weight_decay=0.0)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 5) * max(0.0, 1 - s / steps))
    rng = random.Random(seed)
    order: list[int] = []
    losses = []
    t0 = time.time()
    end = "<|im_end|>"
    step_times, step_tokens, peak = [], [], 0
    for step in range(steps):
        ts = time.time()
        if len(order) < recipe.sft_batch:
            nxt = list(range(len(examples)))
            rng.shuffle(nxt)
            order += nxt
        idx, order = order[:recipe.sft_batch], order[recipe.sft_batch:]
        pre = [examples[i][0] for i in idx]
        cont = [examples[i][1] + end for i in idx]
        x, m, att = tuned._pack(pre, cont)
        if x.shape[1] > recipe.sft_max_len:
            x, m, att = x[:, :recipe.sft_max_len], m[:, :recipe.sft_max_len], att[:, :recipe.sft_max_len]
        # Gradient accumulation over micro-batches of 8: the same update as one batch of 16 (token-mean
        # loss over the whole batch), at half the activation memory. Long completions at batch 16 pushed
        # the MPS process past 14 GB on a 16 GB machine.
        n_tok = m[:, 1:].sum().clamp(min=1)
        opt.zero_grad()
        loss_val = 0.0
        mb = 4 if lm.size == "1.7B" else 8
        for s in range(0, x.shape[0], mb):
            lp, sel = tuned.token_logprobs(x[s:s + mb], m[s:s + mb], att[s:s + mb])
            part = -lp.sum() / n_tok
            part.backward()
            loss_val += part.item()
            del lp, sel, part
        loss = torch.tensor(loss_val)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        sched.step()
        if step % 10 == 9:
            release_cache()
        losses.append(loss.item())
        step_times.append(time.time() - ts)
        step_tokens.append(int(att.sum()))
        peak = max(peak, memory_in_use())
        if log and (step + 1) % 20 == 0:
            log(f"    sft {lm.size} step {step + 1}/{steps} loss {sum(losses[-20:]) / 20:.3f}")
    model.eval()
    if checkpointing:
        model.get_base_model().gradient_checkpointing_disable()
    seen = min(len(examples), steps * recipe.sft_batch)
    info = {"steps": steps, "examples_seen": steps * recipe.sft_batch, "unique_examples_used": seen,
            "epochs": round(steps * recipe.sft_batch / max(1, len(examples)), 2),
            "loss_first": round(sum(losses[:5]) / 5, 4), "loss_last": round(sum(losses[-5:]) / 5, 4),
            "seconds": round(time.time() - t0, 1), "device": tuned.dev, "dtype": str(dtype_for(lm.size)).replace("torch.", ""),
            "step_seconds": [round(t, 3) for t in step_times], "step_tokens": step_tokens,
            "peak_memory_gb": round(peak / 1e9, 2)}
    return tuned, info


def log10_params(size: str) -> float:
    return math.log10(PARAMS[size])
