"""Static screens: red flags that need no training run.

* noisy_labels   (datasets) every "a op b = c" in a worked solution is recomputed, and the stated final answer
                 must appear in the working. Answer-only data goes to the reference judge (judge.py, coverage.py).
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


# thresholds (frozen; see module docstring)
NOISY_EQ_RATE = 0.10        # >= 10% of worked solutions contain an arithmetic error or an answer mismatch
MIN_WORKED = 20             # worked solutions needed before the arithmetic rate can flag
OFFTOPIC_COS = 0.35         # a prompt is off-topic if its nearest suite item is below this cosine
OFFTOPIC_SHARE = 0.5        # flag when at least half the material is off-topic
CODE_FAIL_RATE = 0.10      # code labels: share failing their tests (or invalid syntax)
TOOL_BAD_RATE = 0.10       # tool-use labels: share of calls that break the declared tools
# Set on the dev half of examples/coverage_eval, midpoint of clean and 30% noise. One source each, so these
# are starting points: a judge's own error rate depends on how hard the questions are.
MCQ_DISAGREE = 0.30        # two routes (audit_mcq2), four dev sources: clean 0.03-0.27, 30% wrong 0.24-0.51
FIT_MIN = {"free_text": 0.58, "chat": 0.32}  # Dolly 0.72 -> 0.43; SODA 0.38 -> 0.27
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
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow):  # LaTeX powers (2^{10}); bounded so nothing explodes
            b, e = ev(n.left), ev(n.right)
            if abs(e) > 12 or abs(b) > 1e6:
                raise ValueError
            return b ** e
        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.operand))
        raise ValueError
    return ev(ast.parse(expr, mode="eval"))


_MATH = re.compile(r"\\begin\{(?:align|equation|eqnarray|gather|multline)\*?\}(.+?)\\end\{(?:align|equation|eqnarray|gather|multline)\*?\}"
                   r"|\$\$(.+?)\$\$|\$(.+?)\$|\\\[(.+?)\\\]|\\\((.+?)\\\)", re.S)
_FRAC = re.compile(r"\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
_BOXED = re.compile(r"\\(?:boxed|fbox)\s*\{([^{}]*)\}")


def _latex_math(m: str) -> str:
    """One LaTeX math segment as plain arithmetic: fractions, products, powers, implicit products, decimals."""
    m = re.sub(r"\\\\\s*&?\s*=", "=", m)  # aligned chains: 'a &= b \\\\ &= c' reads as 'a = b = c'
    m = m.replace("&", " ").replace("\\\\", " ; ")
    m = re.sub(r"(\d)\s*\\[dt]?frac\s*\{(\d+)\}\s*\{(\d+)\}", r"(\1+(\2)/(\3))", m)  # mixed number: 5\frac{1}{2} is 5.5
    for _ in range(4):
        m2 = _FRAC.sub(r"((\1)/(\2))", m)
        m2 = _BOXED.sub(r"\1", m2)
        if m2 == m:
            break
        m = m2
    m = re.sub(r"\^\s*\{?\\circ\}?", "", m)  # degrees
    m = re.sub(r"\\(?:cdot|times|ast)", "*", m).replace("\\div", "/")
    m = re.sub(r"\\(?:left|right|[,;!:]|quad|qquad|text\{[^{}]*\}|mbox\{[^{}]*\}|mathrm\{[^{}]*\})", " ", m)
    m = m.replace("{,}", "").replace("\\%", "%").replace("\\$", "")
    m = re.sub(r"\^\s*\{([^{}]*)\}", r"**(\1)", m)
    m = re.sub(r"\^\s*(\d+)", r"**\1", m)
    m = m.replace("{", "(").replace("}", ")")
    m = re.sub(r"(?<![\d.])\.(\d)", r"0.\1", m)
    m = re.sub(r"\)\s*\(", ")*(", m)
    m = re.sub(r"(\d)\s*\(", r"\1*(", m)
    m = re.sub(r"\)\s*(\d)", r")*\1", m)
    return m


def latex_plain(text: str) -> str:
    """Rewrite LaTeX math ($...$, \\[...\\], \\(...\\), \\boxed{...}) as plain arithmetic; prose outside math is unchanged.

    Round 4 found that the unsupported-final check could not read LaTeX: in '$102/2=\\boxed{51}$' the answer looked
    unproduced, which falsely flagged every MATH prealgebra draw in test v4.
    """
    if "\\" not in text:  # no LaTeX command: plain text, where '$' is a currency sign (GSM8K), is left alone
        return text
    text = text.replace("\\$", " ")  # an escaped dollar is a currency sign, not a math delimiter
    text = _MATH.sub(lambda g: " " + _latex_math(next(x for x in g.groups() if x is not None)) + " ", text)
    return _BOXED.sub(r"\1", text)


def equations(text: str) -> list[tuple[str, float, float]]:
    """(expression, its value, the stated result) for every 'expression = number' in the text.

    The expression is the maximal run of digits, operators and parentheses left of '=', so
    '1 + 2 + 5 = 8' is checked as a whole, and '$10/family * 3 families = $30' (words inside)
    is skipped rather than misread. LaTeX math is rewritten as plain arithmetic first (latex_plain).
    """
    text = latex_plain(text).replace(",", "")
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
        except (ValueError, SyntaxError, ZeroDivisionError, TypeError, OverflowError):
            continue
        if re.match(r"\s*(?:%|percent)", text[m.end():m.end() + 9]) and "%" not in lhs and abs(float(val)) <= 1:
            val = 100 * val  # '15/25 = 60 percent' states a share as a percentage
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
    lab = label_of(text)
    text = latex_plain(text).replace(",", "")
    eqs = equations(text)
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


def screen_dataset(examples, suite) -> dict:
    out = {"arithmetic": arithmetic_consistency([e.completion for e in examples]),
           "relevance": relevance([e.prompt_text for e in examples], [i.prompt for i in suite.items])}
    a = out["arithmetic"]
    # A rate needs a real sample of worked solutions: on real Dolly data 1 slip in 3 checked rows of 100 read as 33%.
    enough = a["checked"] >= max(MIN_WORKED, 0.2 * len(examples))
    out["noisy"] = bool(enough and a["rate"] is not None and a["rate"] >= NOISY_EQ_RATE)
    out["off_topic"] = out["relevance"]["off_topic_share"] >= OFFTOPIC_SHARE
    return out
