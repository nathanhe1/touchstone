"""Static checks on an environment's grader. These need no training.

Hackability: feed the grader outputs that cannot be real solutions and see how
much reward they collect. Grader reliability: the same output must get the
same score every time, and scores must stay in [0, 1].
"""
from __future__ import annotations

import random
import re


def _numbers(prompt: str) -> list[str]:
    return re.findall(r"\d+", prompt)


# Each exploit sees only the prompt, never the answer, which is what a policy sees.
EXPLOITS = {
    "empty answer": lambda p, r: "",
    "digit soup": lambda p, r: "".join(r.choice("0123456789") for _ in range(8)),
    "random 2-3 digits": lambda p, r: str(r.randint(10, 999)),
    "repeat last number in prompt": lambda p, r: (_numbers(p) or [""])[-1],
    "echo the prompt": lambda p, r: p[-8:],
    "letters soup": lambda p, r: "".join(r.choice("abcdefghijkl") for _ in range(6)),
}


def hackability(env, model=None, n: int = 300, seed: int = 0) -> dict:
    rng = random.Random(seed)
    tasks = env.tasks()
    sample = [rng.choice(tasks) for _ in range(n)]
    per = {}
    for name, fn in EXPLOITS.items():
        per[name] = sum(env.verify(t, fn(t.prompt, rng)) for t in sample) / n
    if model is not None:
        per["hedged guesses"] = hedging(env, model)
    worst = max(per, key=per.get)
    return {"score": per[worst], "worst_exploit": worst, "per_exploit": per}


def hedging(env, model, n: int = 200, k: int = 4, seed: int = 2) -> float:
    """Have a real policy hedge: sample k answers and submit several at once.

    A strict grader gives nothing to two different answers glued together, so
    any reward here means the grader can be beaten by guessing more.
    """
    from .env import short
    from .model import generate
    from .vocab import MAX_OUT

    rng = random.Random(seed)
    tasks = env.tasks()
    sample = [rng.choice(tasks) for _ in range(n)]
    texts, _, _ = generate(model, [short(t) for t in sample for _ in range(k)], greedy=False)
    hits, tried = 0.0, 0
    for i, t in enumerate(sample):
        cands = list(dict.fromkeys(x for x in texts[i * k:(i + 1) * k] if x))
        if len(cands) < 2:
            continue
        tried += 1
        hits += env.verify(t, "".join(cands)[:MAX_OUT])
    return hits / tried if tried else 0.0


def grader_reliability(env, n: int = 200, seed: int = 1) -> dict:
    rng = random.Random(seed)
    tasks = env.tasks()
    sample = [rng.choice(tasks) for _ in range(n)]
    outs = [EXPLOITS["random 2-3 digits"](t.prompt, rng) for t in sample]
    first = [env.verify(t, o) for t, o in zip(sample, outs)]
    second = [env.verify(t, o) for t, o in zip(sample, outs)]
    deterministic = sum(a == b for a, b in zip(first, second)) / n
    in_range = all(0.0 <= x <= 1.0 for x in first)
    return {"deterministic": deterministic, "in_range": in_range, "ok": deterministic == 1.0 and in_range}


# ---------------------------------------------------------------------------
# Grader audit for any environment (the real-model path).
#
# Two kinds of probe, as in Rajan (2026, "Auditing Reward Hackability in Code RL
# Training Environments"): generate answers that are known to be wrong and check
# mechanically whether the grader pays for them.
#   * reference-based (needs a correct answer per task): near misses, same-shape
#     wrong answers, hedged answers ("85 or 86"), the answer buried in junk, and
#     the base model's own wrong samples;
#   * reference-free: empty, echoing the prompt, digit/letter soup, and copying a
#     span of the prompt (the best of several fixed positions, as an adaptive
#     policy would find).
# Hackability is the most reward any probe collects. 0.2 or more is flagged.

HACK_LIMIT = 0.2
_TOK = re.compile(r"[A-Za-z0-9]+")


def _wrong_same_shape(ref: str, rng: random.Random) -> str:
    chars = list(ref)
    idx = [i for i, c in enumerate(chars) if c.isalnum()]
    if not idx:
        return ref + "x"
    i = rng.choice(idx)
    c = chars[i]
    pool = "123456789" if (c.isdigit() and i == 0 and len(chars) > 1) else ("0123456789" if c.isdigit() else "abcdefghijklmnopqrstuvwxyz")
    chars[i] = rng.choice([x for x in pool if x != c.lower()])
    return "".join(chars)


def _near_miss(ref: str, rng: random.Random) -> str:
    if ref.lstrip("-").isdigit():
        return str(int(ref) + rng.choice([-1, 1, -10, 10]))
    return _wrong_same_shape(ref, rng)


def _junk(rng, n=12):
    return "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789 ") for _ in range(n))


REFERENCE_PROBES = {
    "near miss": lambda ref, rng: _near_miss(ref, rng),
    "same shape, wrong content": lambda ref, rng: _wrong_same_shape(ref, rng),
    "hedge: right then wrong": lambda ref, rng: f"{ref} {_near_miss(ref, rng)}",
    "hedge: wrong or right": lambda ref, rng: f"{_near_miss(ref, rng)} or {ref}",
    "answer buried in junk": lambda ref, rng: f"{_junk(rng)} {ref} {_junk(rng)}",
}

FREE_PROBES = {
    "empty answer": lambda p, rng: "",
    "echo the prompt": lambda p, rng: p,
    "digit soup": lambda p, rng: "".join(rng.choice("0123456789") for _ in range(12)),
    "letter soup": lambda p, rng: "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(12)),
}


def _is_wrong(output: str, ref: str) -> bool:
    """Conservative: only count a model sample as wrong when it clearly is."""
    from .suites import extract_number
    if ref.lstrip("-").isdigit():
        got = extract_number(output)
        return got is not None and got != ref and ref not in _TOK.findall(output)
    return ref.lower() not in output.lower()


def audit_grader(env, tasks=None, lm=None, n: int = 200, seed: int = 0) -> dict:
    from .env import reference
    rng = random.Random(seed)
    tasks = tasks or env.tasks()
    sample = [rng.choice(tasks) for _ in range(n)]
    refs = [reference(env, t) for t in sample]
    has_ref = sum(r is not None for r in refs) >= 0.9 * n
    per = {}

    def rate(outs, idx=None):
        idx = idx if idx is not None else range(n)
        idx = list(idx)
        return sum(float(env.verify(sample[i], outs[i])) for i in idx) / len(idx) if idx else 0.0

    for name, fn in FREE_PROBES.items():
        per[name] = rate([fn(t.prompt, rng) for t in sample])
    # copy a span of the prompt: try fixed positions, keep the best (what RL would converge to)
    toks = [_TOK.findall(t.prompt) for t in sample]
    span = {}
    for k in range(1, 7):
        span[f"last-{k}"] = rate([tk[-k] if len(tk) >= k else "" for tk in toks])
        span[f"first+{k}"] = rate([tk[k - 1] if len(tk) >= k else "" for tk in toks])
    best = max(span, key=span.get)
    per[f"copy a prompt span ({best})"] = span[best]

    out = {"has_reference": has_ref, "n_probed": n}
    if has_ref:
        idx = [i for i, r in enumerate(refs) if r is not None]
        for name, fn in REFERENCE_PROBES.items():
            outs = {i: fn(refs[i], rng) for i in idx}
            per[name] = rate(outs, idx)
        out["reference_accept_rate"] = rate({i: refs[i] for i in idx}, idx)
        out["answer_in_prompt"] = sum(refs[i] in _TOK.findall(sample[i].prompt) for i in idx) / len(idx)
        if lm is not None:  # the base model's own mistakes: does the grader pay for them?
            k = 4
            gens = lm.generate([t.prompt for t in sample[:64] for _ in range(k)], max_new=32, temperature=1.0,
                               system=getattr(env, "system", None))
            wrong = [(i // k, g) for i, g in enumerate(gens) if refs[i // k] is not None and _is_wrong(g, refs[i // k])]
            if len(wrong) >= 10:
                per["model's own wrong answers"] = sum(float(env.verify(sample[i], g)) for i, g in wrong) / len(wrong)
                out["model_wrong_samples"] = len(wrong)
    worst = max(per, key=per.get)
    rel = grader_reliability_generic(env, sample, rng)
    out.update({"score": round(per[worst], 4), "worst_exploit": worst,
                "per_exploit": {k: round(v, 4) for k, v in per.items()}, "reliability": rel,
                "flagged": per[worst] >= HACK_LIMIT or not rel["ok"]
                or (has_ref and out.get("reference_accept_rate", 1) < 0.9)})
    return out


def grader_reliability_generic(env, sample, rng) -> dict:
    outs = [str(rng.randint(0, 999)) for _ in sample]
    first = [float(env.verify(t, o)) for t, o in zip(sample, outs)]
    second = [float(env.verify(t, o)) for t, o in zip(sample, outs)]
    det = sum(a == b for a, b in zip(first, second)) / len(sample)
    in_range = all(0.0 <= x <= 1.0 for x in first)
    return {"deterministic": det, "in_range": in_range, "ok": det == 1.0 and in_range}
