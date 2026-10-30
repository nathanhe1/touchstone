"""Static screens: red flags that need no training run.

* noisy_labels   (datasets) two independent signals:
    - arithmetic consistency: every "a op b = c" in a worked solution is recomputed, and the
      stated final answer must equal the last computed result;
    - label plausibility: a small reference model (SmolLM2-360M) scores the given final answer
      against nearby alternatives (+-1, +-10, digit swaps) in the answer slot. Correct labels are
      preferred far more often than chance; wrong or shuffled labels are not.
* off_topic      (both) share of material prompts whose nearest held-out item (sentence-embedding
                 cosine) is below a relevance threshold.
* answer_leakage (envs)  the reference answer appears verbatim in the prompt.

Thresholds were set on the development set (envs/ and examples/datasets/) and then frozen
before the held-out test set in examples/redflags_test/ was built and evaluated
(scripts/eval_flags.py). They are not tuned on the test set.
"""
from __future__ import annotations

import random
import re

from .suites import extract_number, numeric_distractors

# thresholds (frozen; see module docstring)
NOISY_EQ_RATE = 0.10        # >= 10% of worked solutions contain an arithmetic error or an answer mismatch
NOISY_PLAUSIBILITY = 0.45   # mean preference for the given answer over 4 alternatives (chance 0.20)
OFFTOPIC_COS = 0.35         # a prompt is off-topic if its nearest suite item is below this cosine
OFFTOPIC_SHARE = 0.5        # flag when at least half the material is off-topic
LEAK_SHARE = 0.2            # flag when the answer is in the prompt for >= 20% of tasks

_RHS = re.compile(r"=\s*\$?(-?\d+(?:\.\d+)?)(?![\d.]*\s*[+\-*/x×])")
_LHS_CHARS = set("0123456789.+-*/x×() ")


def _safe_eval(expr: str):
    import ast
    import operator
    ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
           ast.USub: operator.neg}

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.operand))
        raise ValueError
    return ev(ast.parse(expr, mode="eval"))


def equations(text: str) -> list[tuple[str, float, float]]:
    """(expression, its value, the stated result) for every 'expression = number' in the text.

    The expression is the maximal run of digits, operators and parentheses left of '=', so
    '1 + 2 + 5 = 8' is checked as a whole, and '$10/family * 3 families = $30' (words inside)
    is skipped rather than misread.
    """
    text = text.replace(",", "")
    out = []
    for m in _RHS.finditer(text):
        i = m.start()
        j = i
        while j > 0 and text[j - 1] in _LHS_CHARS:
            j -= 1
        lhs = text[j:i].strip().lstrip("+*/x×").strip()
        if not lhs or not any(o in lhs[1:] for o in "+-*/x×") or not lhs[0].isdigit() and lhs[0] not in "(-":
            continue
        try:
            val = _safe_eval(lhs.replace("x", "*").replace("×", "*"))
        except (ValueError, SyntaxError, ZeroDivisionError, TypeError):
            continue
        out.append((lhs, float(val), float(m.group(1))))
    return out


def check_arithmetic(text: str) -> tuple[int, int]:
    """(equations found, equations whose stated result is wrong)."""
    eqs = equations(text)
    wrong = sum(abs(v - r) > max(0.01, 1e-6 * abs(v)) and abs(round(v) - r) > 0 for _, v, r in eqs)
    return len(eqs), wrong


def arithmetic_consistency(completions: list[str]) -> dict:
    checked = bad = 0
    for c in completions:
        n, wrong = check_arithmetic(c)
        if n:
            checked += 1
            bad += bool(wrong)
    return {"checked": checked, "inconsistent": bad, "rate": bad / checked if checked else None}


def label_plausibility(lm, examples, n: int = 96, seed: int = 0) -> dict:
    """Mean probability the reference model gives the stated final answer vs 4 nearby alternatives."""
    from .measure import answer_slot
    rng = random.Random(seed)
    pool = [e for e in examples if extract_number(e.completion) is not None]
    if len(pool) < 20:
        return {"scored": len(pool), "mean": None}
    sample = rng.sample(pool, min(n, len(pool)))
    prompts, answers, dis, slots = [], [], [], []
    for e in sample:
        ans = extract_number(e.completion)
        if not ans.lstrip("-").isdigit():
            continue
        slot = answer_slot(e.completion)
        prompts.append(e.last_user)
        answers.append(ans)
        dis.append(numeric_distractors(ans, rng))
        slots.append(slot)
    probs = lm.candidate_probs(prompts, answers, dis, slots)
    return {"scored": len(probs), "mean": sum(probs) / len(probs) if probs else None}


def relevance(prompts: list[str], suite_prompts: list[str], n: int = 400, seed: int = 0) -> dict:
    from .overlap import embed
    rng = random.Random(seed)
    sample = rng.sample(prompts, min(n, len(prompts)))
    E, S = embed(sample), embed(suite_prompts)
    best = (E @ S.T).max(dim=1).values
    off = float((best < OFFTOPIC_COS).float().mean())
    return {"mean_nearest_cos": round(float(best.mean()), 4), "off_topic_share": round(off, 4)}


def answer_leakage(prompts: list[str], refs: list[str | None]) -> float:
    tok = re.compile(r"[A-Za-z0-9]+")
    pairs = [(p, r) for p, r in zip(prompts, refs) if r]
    if not pairs:
        return 0.0
    return sum(r in tok.findall(p) for p, r in pairs) / len(pairs)


def screen_dataset(examples, suite, lm=None) -> dict:
    out = {"arithmetic": arithmetic_consistency([e.completion for e in examples]),
           "relevance": relevance([e.prompt_text for e in examples], [i.prompt for i in suite.items])}
    if lm is not None and suite.items and suite.items[0].match == "numeric":
        out["plausibility"] = label_plausibility(lm, examples)
    eq = out["arithmetic"]["rate"]
    pl = out.get("plausibility", {}).get("mean")
    out["noisy"] = bool((eq is not None and eq >= NOISY_EQ_RATE) or (pl is not None and pl < NOISY_PLAUSIBILITY))
    out["off_topic"] = out["relevance"]["off_topic_share"] >= OFFTOPIC_SHARE
    return out
