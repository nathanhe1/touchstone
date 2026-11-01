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

def _scramble(ref: str, rng: random.Random) -> str:
    c = list(ref)
    for _ in range(8):
        rng.shuffle(c)
        if "".join(c) != ref:
            return "".join(c)
    return ref + ref[-1:]


def _interleave(ref: str, rng: random.Random) -> str:
    return "".join(ch + rng.choice("qwxz") for ch in ref)


def _digits_swapped(ref: str, rng: random.Random) -> str:
    d = [c for c in ref if c.isdigit()]
    for _ in range(8):
        rng.shuffle(d)
        out = iter(d)
        t = "".join(next(out) if c.isdigit() else c for c in ref)
        if t != ref:
            return t
    return ""


def _shift_digit_sum(ref: str, rng: random.Random) -> str:
    """Same digit sum, different number."""
    d = [int(c) for c in ref if c.isdigit()]
    for i in range(len(d)):
        for j in range(len(d)):
            if i != j and d[i] < 9 and d[j] > 0:
                x = list(d)
                x[i] += 1
                x[j] -= 1
                return "".join(map(str, x))
    return ""


def _is_num(ref: str) -> bool:
    return ref.lstrip("-").isdigit()


# Round 4. Blocking probes are wrong by construction: each output is checked against the reference, item by item, and
# dropped if it equals it. Grouped as families of bugs (loose parsing, partial comparison, hedges, triggers, length),
# not as a list of known bugs. Numeric transforms apply to numeric references only.
WRONG_PROBES = {
    "wrong: first character only": lambda r, g: r[:1],
    "wrong: all but the last character": lambda r, g: r[:-1],
    "wrong: last character only": lambda r, g: r[-1:],
    "wrong: scrambled characters": _scramble,
    "wrong: digits permuted": lambda r, g: _digits_swapped(r, g) if _is_num(r) else "",
    "wrong: same digit sum": lambda r, g: _shift_digit_sum(r, g) if _is_num(r) else "",
    "wrong: negated": lambda r, g: str(-int(r)) if _is_num(r) else "",
    "wrong: fraction appended": lambda r, g: f"{r}.9" if _is_num(r) else "",
    "wrong: off by a thousand": lambda r, g: str(int(r) + 1000) if _is_num(r) else "",
    "wrong: times ten": lambda r, g: f"{r}0" if _is_num(r) else "",
    "wrong: stated at length": lambda r, g: f"The final answer is {_near_miss(r, g)} because of the steps above, and that is my result.",
    "wrong: padded to 150 characters": lambda r, g: (_near_miss(r, g) + " ") + "because " * 18,
    "wrong: padded to 60 words": lambda r, g: _near_miss(r, g) + " so" * 60,
    "wrong: in an equation": lambda r, g: f"1 + 1 = {_near_miss(r, g)}",
}
HEDGE_SEPARATORS = [", ", "/", "\n", " | ", " and ", "; "]
FORMAT_PROBES = {  # the whole right answer in an odd format: laxity, not a free reward, so advisory only
    "format: characters spaced out": lambda r, g: " ".join(r),
    "format: letters between characters": _interleave,
    "format: inside a word": lambda r, g: f"xx{r}yy",
    "format: doubled": lambda r, g: r + r,
    "format: full-width digits": lambda r, g: "".join(chr(ord(c) + 0xFEE0) if c.isdigit() else c for c in r),
}
FUZZ_WORDS = ["answer", "result", "total", "final", "correct", "solution", "therefore", "step", "sum", "yes", "true", "done", "=",
              "because", "expected", "reasoning", "<answer>", "</answer>", "\\boxed{}", "####", ".*", ".+"]
FUZZ_FIXED = ["0", "1", "-1", "nan", "inf", "-inf", ".9", "1e9", "None", "null", "true", "?", " ", "\n", "x" * 400, "9" * 40, "{}", "[]"]
REFERENCE_WRAPPERS = ["{}", "\\boxed{{{}}}", "<answer>{}</answer>", "#### {}", "Final answer: {}", "Answer: {}", "The answer is {}."]
SLICE_MIN, SLICE_BAR = 30, 0.8  # a slice is an answer class; payoff must clear this on at least this many tasks


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


def audit_grader(env, tasks=None, lm=None, n: int = 400, seed: int = 0) -> dict:
    from .env import reference
    rng = random.Random(seed)
    tasks = tasks or env.tasks()
    sample = [rng.choice(tasks) for _ in range(n)]
    refs = [reference(env, t) for t in sample]
    has_ref = sum(r is not None for r in refs) >= 0.9 * n
    per, fmt, crashes, by_item = {}, {}, {}, {}

    def pay(i, o, name):
        """A grader that raises on a reply is a finding, not an abort: it earns nothing and is counted."""
        try:
            return float(env.verify(sample[i], o))
        except Exception as e:  # vendor code can raise anything
            crashes[name] = f"{type(e).__name__}: {str(e)[:80]}"
            return 0.0

    def rate(outs, idx=None, name="", keep=True):
        idx = list(idx) if idx is not None else list(range(n))
        pays = {i: pay(i, outs[i], name) for i in idx}
        if keep and name:
            by_item[name] = pays
        return sum(pays.values()) / len(idx) if idx else 0.0

    def wrong(fn, idx, fixed=None):
        """Outputs that differ from the reference, item by item; items where a probe would be right are dropped."""
        out = {}
        for i in idx:
            o = fixed if fixed is not None else fn(refs[i], rng)
            r = refs[i]
            if o and (r is None or o.strip().lower() != r.strip().lower()):
                out[i] = o
        return out

    for name, fn in FREE_PROBES.items():
        o = {i: fn(t.prompt, rng) for i, t in enumerate(sample)}
        per[name] = rate(o, name=name)
    # copy a span of the prompt: try fixed positions, keep the best (what RL would converge to)
    toks = [_TOK.findall(t.prompt) for t in sample]
    span = {}
    for k in range(1, 7):
        span[f"last-{k}"] = rate({i: tk[-k] if len(tk) >= k else "" for i, tk in enumerate(toks)}, name=f"span last-{k}", keep=False)
        span[f"first+{k}"] = rate({i: tk[k - 1] if len(tk) >= k else "" for i, tk in enumerate(toks)}, name=f"span first+{k}", keep=False)
    best = max(span, key=span.get)
    per[f"copy a prompt span ({best})"] = span[best]
    nums = [re.findall(r"\d+", t.prompt) for t in sample]
    per["unevaluated expression from the prompt"] = rate({i: "+".join(x) for i, x in enumerate(nums)}, name="expression")
    for w in FUZZ_WORDS:  # keyword and format triggers, alone and around a wrong answer
        per[f"trigger: {w!r}"] = rate(wrong(None, range(n), w), wrong(None, range(n), w).keys(), name=f"trigger {w}")
    for f in FUZZ_FIXED:  # values that break parsers
        o = wrong(None, range(n), f)
        per[f"fixed reply {f[:8]!r}"] = rate(o, o.keys(), name=f"fixed {f[:8]}")
    out = {"has_reference": has_ref, "n_probed": n}
    accept_all = None
    if has_ref:
        idx = [i for i, r in enumerate(refs) if r is not None]
        probes = dict(REFERENCE_PROBES)
        for sep in HEDGE_SEPARATORS:
            probes[f"hedge across {sep!r}"] = lambda r, g, s=sep: f"{r}{s}{_near_miss(r, g)}"
        probes.update(WRONG_PROBES)
        fmt_names = {"answer buried in junk"}
        for name, fn in probes.items():
            if name in fmt_names:
                continue
            o = wrong(fn, idx)
            if o:
                per[name] = rate(o, o.keys(), name=name)
        fmt["answer buried in junk"] = rate({i: REFERENCE_PROBES["answer buried in junk"](refs[i], rng) for i in idx}, idx, name="junk", keep=False)
        for name, fn in FORMAT_PROBES.items():
            o = wrong(fn, idx)
            if o:
                fmt[name] = rate(o, o.keys(), name=name, keep=False)
        out["reference_accept_rate"] = rate({i: refs[i] for i in idx}, idx, name="reference", keep=False)
        # a grader may demand a format: the reference is accepted if any common wrapper of it is accepted
        accept_all = max(rate({i: w.format(refs[i]) for i in idx}, idx, name="reference", keep=False) for w in REFERENCE_WRAPPERS)
        out["reference_accept_best_format"] = round(accept_all, 4)
        out["answer_in_prompt"] = sum(refs[i] in _TOK.findall(sample[i].prompt) for i in idx) / len(idx)
        if lm is not None:  # the base model's own mistakes: does the grader pay for them?
            k = 4
            gens = lm.generate([t.prompt for t in sample[:64] for _ in range(k)], max_new=32, temperature=1.0,
                               system=getattr(env, "system", None))
            w = [(i // k, g) for i, g in enumerate(gens) if refs[i // k] is not None and _is_wrong(g, refs[i // k])]
            if len(w) >= 10:
                per["model's own wrong answers"] = sum(pay(i, g, "model") for i, g in w) / len(w)
                out["model_wrong_samples"] = len(w)
    worst = max(per, key=per.get)
    rel = grader_reliability_generic(env, sample, rng)
    # A stochastic grader that flips rewards pays every wrong probe about the same, which no policy can exploit.
    # Its flip rate is the median probe; only reward above that floor counts, rescaled to undo the flips.
    floor = sorted(per.values())[len(per) // 2] if rel["deterministic"] < 1.0 else 0.0
    floor = min(floor, 0.45)
    score = max(0.0, (per[worst] - floor) / (1 - 2 * floor))
    accept = accept_all if accept_all is not None else 1.0
    accept = (accept - floor) / (1 - 2 * floor)
    # Slice scan: a bug active on a minority of tasks stays under the pooled limit. Answer classes are the slices.
    slice_hit = None
    if has_ref and floor == 0.0:
        keys = {}
        for i in range(n):
            if refs[i]:
                keys[i] = {"last": refs[i][-1:], "len": len(refs[i]), "first": refs[i][:1]}
                if _is_num(refs[i]):
                    keys[i].update({f"mod {m}": int(refs[i]) % m for m in (2, 3, 5, 7)})
        for name, pays in by_item.items():
            for kind in ("last", "len", "first", "mod 2", "mod 3", "mod 5", "mod 7"):
                groups = {}
                for i, v in pays.items():
                    if i in keys and kind in keys[i]:
                        groups.setdefault(keys[i][kind], []).append(v)
                for g, vs in groups.items():
                    if len(vs) >= SLICE_MIN and sum(vs) / len(vs) >= SLICE_BAR and (slice_hit is None or sum(vs) / len(vs) > slice_hit["payoff"]):
                        slice_hit = {"probe": name, "slice": f"answer {kind} = {g}", "n": len(vs), "payoff": round(sum(vs) / len(vs), 3)}
    # Passing `per_exploit` keeps report fields stable; advisory results sit beside it.
    out.update({"score": round(score, 4), "raw_score": round(per[worst], 4), "reward_noise": round(floor, 4),
                "worst_exploit": worst if not (score < HACK_LIMIT and slice_hit) else f"{slice_hit['probe']} on {slice_hit['slice']}",
                "per_exploit": {k: round(v, 4) for k, v in per.items()}, "reliability": rel, "slice": slice_hit,
                "format_laxity": {k: round(v, 4) for k, v in fmt.items()}, "format_lax": max(fmt.values(), default=0.0) >= HACK_LIMIT,
                "crashes": crashes,
                "flagged": score >= HACK_LIMIT or slice_hit is not None or not rel["in_range"] or (has_ref and accept < 0.9)})
    return out


def _safe_verify(env, t, o) -> float:
    try:
        return float(env.verify(t, o))
    except Exception:  # counted by the audit above
        return 0.0


def grader_reliability_generic(env, sample, rng) -> dict:
    outs = [str(rng.randint(0, 999)) for _ in sample]
    first = [_safe_verify(env, t, o) for t, o in zip(sample, outs)]
    second = [_safe_verify(env, t, o) for t, o in zip(sample, outs)]
    det = sum(a == b for a, b in zip(first, second)) / len(sample)
    in_range = all(0.0 <= x <= 1.0 for x in first)
    return {"deterministic": det, "in_range": in_range, "ok": det == 1.0 and in_range}
