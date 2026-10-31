"""A reference judge for label audits: a stronger open model that re-solves sampled items.

Confident learning (Northcutt et al. 2021) estimates label noise from where a model that is usually
right confidently disagrees with the given label. The SmolLM2 ladder is too weak at math for that:
its own confident errors swamp 10-30% noise. The judge here is Qwen2.5-1.5B-Instruct (GSM8K ~73%),
run with Apple MLX (much lighter than PyTorch MPS for generation), and it answers each item two
independent ways:

* cot: reason step by step, final answer in \\boxed{};
* pal: write one Python expression that computes the answer (program-aided, Gao et al. 2023),
  evaluated by a whitelisted AST evaluator (no names, imports or attribute access beyond a few
  string methods; nothing from the model is ever exec'd).

An item is *confident* when both routes give the same answer. Agreement between two different
procedures is a stronger confidence signal than self-consistency of one, and it is cheap (two greedy
generations). The label disagreement rate among confident items estimates the label-noise rate.
"""
from __future__ import annotations

import ast
import operator
import random
import re
from functools import lru_cache

JUDGE_REPO = "Qwen/Qwen2.5-1.5B-Instruct"

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_FUNCS = {"len": len, "sorted": sorted, "abs": abs, "round": round, "min": min, "max": max, "sum": sum, "int": int,
          "float": float, "str": str, "reversed": reversed, "list": list}
_METHODS = {"upper", "lower", "join", "replace", "strip", "count", "split", "title", "capitalize"}


class Unsafe(ValueError):
    pass


def safe_eval(expr: str, depth: int = 0):
    """Evaluate a pure expression: literals, arithmetic, slicing, a few builtins and string methods."""
    tree = ast.parse(expr.strip(), mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 200:
        raise Unsafe("too large")

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float, str)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and (abs(b) > 12 or abs(a) > 1e6):
                raise Unsafe("pow too large")
            if isinstance(n.op, ast.Mult) and (isinstance(a, str) or isinstance(b, str)):
                if (b if isinstance(a, str) else a) > 1000:
                    raise Unsafe("string too large")
            return _BIN[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = ev(n.operand)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, (ast.List, ast.Tuple)):
            return [ev(x) for x in n.elts]
        if isinstance(n, ast.Subscript):
            v = ev(n.value)
            s = n.slice
            if isinstance(s, ast.Slice):
                return v[slice(*(ev(x) if x is not None else None for x in (s.lower, s.upper, s.step)))]
            return v[ev(s)]
        if isinstance(n, ast.Call) and not n.keywords:
            args = [ev(a) for a in n.args]
            if isinstance(n.func, ast.Name) and n.func.id in _FUNCS:
                return _FUNCS[n.func.id](*args)
            if isinstance(n.func, ast.Attribute) and n.func.attr in _METHODS:
                obj = ev(n.func.value)
                if isinstance(obj, str):
                    return getattr(obj, n.func.attr)(*args)
            raise Unsafe("call")
        raise Unsafe(type(n).__name__)
    v = ev(tree)
    if isinstance(v, list):
        v = "".join(map(str, v))
    return v


def canon(v) -> str | None:
    """Canonical answer string: numbers without trailing .0 and commas, strings lower-cased and trimmed."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and v != v:
            return None
        return str(int(round(v))) if abs(v - round(v)) < 1e-6 else f"{v:.4f}".rstrip("0")
    s = str(v).strip().strip(".").strip("'\"`").strip()
    t = s.replace(",", "").replace("$", "")
    if re.fullmatch(r"-?\d+(\.\d+)?", t):
        return canon(float(t))
    return s.lower()


_BOX = re.compile(r"\\boxed\{([^{}]*)\}")
_NUM = re.compile(r"-?\$?\d[\d,]*(?:\.\d+)?")


def label_of(completion: str) -> str | None:
    """The final answer a dataset row asserts: '#### x', \\boxed{x}, JSON 'answer', 'Answer: x', else the last number,
    else (short replies) the reply itself."""
    c = completion.strip()
    for pat in (r"####\s*(.+)$", r"\\boxed\{([^{}]*)\}", r'"answer"\s*:\s*"?([^",}]+)', r"[Aa]nswer(?: is)?\s*[:=]?\s*([^\s.,;]+)"):
        m = re.findall(pat, c)
        if m:
            return canon(m[-1])
    nums = _NUM.findall(c)
    if nums:
        return canon(nums[-1])
    if len(c.split()) <= 2:
        return canon(c)
    return None


@lru_cache(maxsize=1)
def _load(repo: str = JUDGE_REPO):
    from mlx_lm import load
    return load(repo)


COT_SYS = "You are a careful solver. Think step by step, then give the final answer as \\boxed{answer}."
PAL_SYS = ("Translate the task into ONE Python expression that computes the answer. Use only numbers, strings, "
           "arithmetic, slicing and len/sorted/min/max/sum/round. Reply with the expression only, on one line.")


def _gen(prompts: list[str], system: str, max_tokens: int, batch: int = 8) -> list[str]:
    import mlx.core as mx
    from mlx_lm.generate import batch_generate
    model, tok = _load()
    mx.set_cache_limit(256 * 1024 ** 2)  # keep MLX's buffer cache small: the laptop is memory-bound
    out = []
    for s in range(0, len(prompts), batch):
        ids = [tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": p}],
                                       add_generation_prompt=True) for p in prompts[s:s + batch]]
        out += batch_generate(model, tok, ids, max_tokens=max_tokens).texts
        mx.clear_cache()
    return out


def _pal_value(text: str):
    t = text.strip()
    m = re.search(r"```(?:python)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    t = [ln for ln in t.splitlines() if ln.strip()]
    if not t:
        return None
    line = t[-1].strip()
    line = re.sub(r"^print\((.*)\)$", r"\1", line)
    line = re.sub(r"^[A-Za-z_]\w*\s*=\s*", "", line)
    try:
        return canon(safe_eval(line))
    except Exception:
        return None


def solve(prompts: list[str], cot_tokens: int = 320) -> list[dict]:
    """Two independent answers per prompt."""
    cot = _gen(prompts, COT_SYS, cot_tokens)
    pal = _gen(prompts, PAL_SYS, 80)
    res = []
    for c, p in zip(cot, pal):
        b = _BOX.findall(c)
        a1 = canon(b[-1]) if b else None
        a2 = _pal_value(p)
        res.append({"cot": a1, "pal": a2})
    return res


def audit(examples, n: int = 80, seed: int = 0) -> dict:
    """Label-noise estimate on a random sample: share of confident items whose label disagrees with the judge."""
    rng = random.Random(seed)
    pool = [e for e in examples if label_of(e.completion) is not None]
    if len(pool) < 20:
        return {"sampled": len(pool), "confident": 0, "disagree": None}
    sample = rng.sample(pool, min(n, len(pool)))
    sol = solve([e.last_user for e in sample])
    conf = dis = 0
    rows = []
    for e, s in zip(sample, sol):
        lab = label_of(e.completion)
        ok = s["cot"] is not None and s["cot"] == s["pal"]
        if ok:
            conf += 1
            dis += s["cot"] != lab
        rows.append({"label": lab, **s})
    return {"sampled": len(sample), "confident": conf, "disagree": round(dis / conf, 4) if conf >= 10 else None,
            "rows": rows[:5]}
