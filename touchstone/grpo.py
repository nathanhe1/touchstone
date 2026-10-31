"""GRPO on real open models with LoRA (the env-appraisal trainer).

Group-relative policy optimization as in DeepSeekMath (Shao et al. 2024): for
each task sample a group of replies, score them with the environment's
``verify``, and push up replies that beat their group's mean. A KL penalty to
the base model (the same weights with the adapter switched off) keeps the
policy close to where it started. One gradient step per batch, fully on-policy,
so no ratio clipping is needed.

``placebo=True`` shuffles the rewards across the batch before computing
advantages. The reward rate and the prompts are unchanged, but which reply got
rewarded is now random. Spurious Rewards (Shao et al. 2025) showed random
rewards alone can raise scores for some model families, so Touchstone reports
an environment's gain above this placebo.
"""
from __future__ import annotations

import random
import time

import torch

from .lm import LM, Recipe, release_cache, with_lora


def _env_prompt(task) -> str:
    return task.prompt


def grpo(lm: LM, env, recipe: Recipe, seed: int = 0, steps: int | None = None, placebo: bool = False,
         log=None, on_step=None) -> tuple[LM, dict]:
    """on_step(step_done, tuned) is called after every step (for checkpoint evaluations in sweeps)."""
    steps = steps or recipe.rl_steps
    tuned = with_lora(lm, recipe, seed)
    model = tuned.model
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=recipe.rl_lr, weight_decay=0.0)
    rng = random.Random(seed)
    torch.manual_seed(seed)
    tasks = env.tasks()
    system = getattr(env, "system", None)
    B, G = recipe.rl_prompts, recipe.rl_group
    curve, skipped = [], 0
    t0 = time.time()
    for step in range(steps):
        batch = [rng.choice(tasks) for _ in range(B)]
        chats = [tuned.chat(_env_prompt(t), system) for t in batch]
        model.eval()
        outs = tuned.generate([c for c in chats for _ in range(G)], max_new=recipe.rl_max_new, temperature=1.0,
                              batch=B * G, raw=True)
        r = torch.tensor([float(env.verify(batch[i // G], outs[i])) for i in range(B * G)])
        curve.append(r.mean().item())
        if placebo:
            r = r[torch.randperm(len(r))]
        r = r.view(B, G)
        adv = (r - r.mean(1, keepdim=True)) / (r.std(1, keepdim=True) + 1e-4)
        if adv.abs().sum() == 0:
            skipped += 1
            if on_step:
                model.eval()
                on_step(step + 1, tuned)
            continue
        model.train()
        pre = [c for c in chats for _ in range(G)]
        conts = [o + "<|im_end|>" for o in outs]
        flat_adv = adv.view(-1)
        opt.zero_grad()
        # micro-batches of 16 with gradient accumulation: on MPS one batch of 64 was 7x slower than four of 16
        mb = 8 if lm.size in ("1.7B", "7B") else 16
        for s in range(0, B * G, mb):
            x, m, att = tuned._pack(pre[s:s + mb], conts[s:s + mb])
            with torch.no_grad(), model.disable_adapter():
                ref, _ = tuned.token_logprobs(x, m, att)
            lp, sel = tuned.token_logprobs(x, m, att)
            mask = sel.float()
            d = ref - lp
            kl = torch.exp(d) - d - 1
            a = flat_adv[s:s + mb].view(-1, 1).to(lp.device)
            per_tok = -(a * lp) + recipe.rl_kl * kl
            loss = ((per_tok * mask).sum(1) / mask.sum(1).clamp(min=1)).sum() / (B * G)
            loss.backward()
            del x, m, att, ref, lp, sel, loss
            release_cache()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        release_cache()
        if on_step:
            model.eval()
            on_step(step + 1, tuned)
        if log and (step + 1) % 10 == 0:
            log(f"    grpo {lm.size}{' placebo' if placebo else ''} step {step + 1}/{steps} "
                f"reward {sum(curve[-10:]) / len(curve[-10:]):.2f}")
    model.eval()
    k = max(1, len(curve) // 5)
    info = {"steps": steps, "skipped_no_signal": skipped, "placebo": placebo,
            "train_reward_first": round(sum(curve[:k]) / k, 4), "train_reward_last": round(sum(curve[-k:]) / k, 4),
            "curve": [round(sum(curve[i:i + 5]) / len(curve[i:i + 5]), 3) for i in range(0, len(curve), 5)],
            "seconds": round(time.time() - t0, 1)}
    return tuned, info


def env_reward(lm: LM, env, n: int = 64, seed: int = 0) -> float:
    """Greedy reward on a fixed sample of the environment's own tasks."""
    rng = random.Random(seed)
    tasks = env.tasks()
    sample = [rng.choice(tasks) for _ in range(n)]
    outs = lm.generate([_env_prompt(t) for t in sample], max_new=32, system=getattr(env, "system", None))
    return sum(float(env.verify(t, o)) for t, o in zip(sample, outs)) / n
