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
CODE_FAIL_RATE = 0.10      # code labels: share failing their tests (or invalid syntax)
TOOL_BAD_RATE = 0.10       # tool-use labels: share of calls that break the declared tools
MCQ_DISAGREE = None        # set on development data; None until then
FIT_MIN = None             # set on development data; None until then
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


_ANYNUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def unsupported_final(text: str) -> bool:
    """The stated final answer is produced nowhere in the working (round 3).

    Applies only to worked solutions (at least one checkable equation). The answer counts as supported
    if it equals any number written before it or any equation's value or stated result, so
    restatements and unit changes in honest solutions pass (0.2% of real GSM8K train solutions are
    flagged, and those are genuine GSM8K label errors).
    """
    from .judge import label_of
    eqs = equations(text)
    lab = label_of(text)
    if not eqs or lab is None:
        return False
    try:
        v = float(lab)
    except ValueError:
        return False
    body = text[:text.rfind(lab)] if lab in text else text
    seen = {float(x.replace(",", "")) for x in _ANYNUM.findall(body)} | {e[1] for e in eqs} | {e[2] for e in eqs}
    return all(abs(v - x) > 1e-6 for x in seen)


def arithmetic_consistency(completions: list[str]) -> dict:
    """Share of worked solutions with an arithmetic error or a final answer the working does not produce."""
    checked = bad = unsupported = 0
    for c in completions:
        n, wrong = check_arithmetic(c)
        if n:
            checked += 1
            u = unsupported_final(c)
            unsupported += u
            bad += bool(wrong) or u
    return {"checked": checked, "inconsistent": bad, "unsupported_final": unsupported,
            "rate": bad / checked if checked else None}


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


def confident_disagreement(lm, examples, n: int = 64, k: int = 4, seed: int = 0) -> dict:
    """Confident-learning style label audit (Northcutt et al. 2021, the idea behind Cleanlab).

    The reference model answers each sampled prompt k times. Where all k samples agree it is
    confident, and confident answers are usually right; the share of those prompts whose given
    label disagrees estimates the label error rate (plus the judge's own confident error rate).
    """
    rng = random.Random(seed)
    pool = [e for e in examples if extract_number(e.completion) is not None]
    if len(pool) < 20:
        return {"confident": 0, "disagree": None}
    sample = rng.sample(pool, min(n, len(pool)))
    prompts = [e.last_user + " Think step by step, then give the final number." for e in sample]
    outs = lm.generate([p for p in prompts for _ in range(k)], max_new=160, temperature=0.7, batch=64)
    conf = dis = 0
    for i, e in enumerate(sample):
        ans = [extract_number(o) for o in outs[i * k:(i + 1) * k]]
        if None in ans or len(set(ans)) != 1:
            continue
        conf += 1
        try:
            dis += abs(float(ans[0]) - float(extract_number(e.completion))) > 1e-6
        except ValueError:
            dis += 1
    return {"sampled": len(sample), "confident": conf, "disagree": dis / conf if conf >= 8 else None}


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


# Set on development data only (round 3, out/dev_judge_qwen.json). Numeric: clean and real GSM8K at most 0.04,
# 10% noise 0.14, 30%+ noise at least 0.18. Text labels (program route): clean at most 0.11, noisy at least 0.40.
JUDGE_DISAGREE = 0.15
JUDGE_DISAGREE_TEXT = 0.20


def judge_noisy(r: dict) -> bool:
    limit = JUDGE_DISAGREE if r.get("route") == "both" else JUDGE_DISAGREE_TEXT
    return r.get("disagree") is not None and r["disagree"] >= limit


def answer_only(examples) -> bool:
    """True when most completions carry no checkable working (so the arithmetic audit cannot see errors)."""
    a = arithmetic_consistency([e.completion for e in examples[:400]])
    return a["checked"] < 0.2 * min(len(examples), 400)


def screen_dataset(examples, suite, lm=None, judge=None) -> dict:
    out = {"arithmetic": arithmetic_consistency([e.completion for e in examples]),
           "relevance": relevance([e.prompt_text for e in examples], [i.prompt for i in suite.items])}
    if lm is not None and suite.items and suite.items[0].match == "numeric":
        out["plausibility"] = label_plausibility(lm, examples)
    if judge is not None and JUDGE_DISAGREE is not None:
        out["judge"] = confident_disagreement(judge, examples)
    eq = out["arithmetic"]["rate"]
    # Plausibility is reported but not used to flag: on the dev set the 360M reference model could not
    # separate clean answer-only labels (0.42) from 30%-noisy ones (0.46). Only arithmetic consistency flags.
    jd = (out.get("judge") or {}).get("disagree")
    out["noisy"] = bool((eq is not None and eq >= NOISY_EQ_RATE) or (jd is not None and jd >= JUDGE_DISAGREE))
    out["off_topic"] = out["relevance"]["off_topic_share"] >= OFFTOPIC_SHARE
    return out
