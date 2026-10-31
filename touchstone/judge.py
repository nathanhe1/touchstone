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
JUDGES = {"qwen": "Qwen/Qwen2.5-1.5B-Instruct", "qwen-math": "Qwen/Qwen2.5-Math-1.5B-Instruct"}

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
PAL_SYS = """Translate the task into ONE Python expression that computes the answer. Reply with only the expression.

Task: Tom has 3 boxes of 12 pens and loses 5 pens. How many pens does he have?
3 * 12 - 5

Task: A shop sold 40 cups on Monday and twice as many on Tuesday. How many cups in both days?
40 + 2 * 40

Task: Lena splits 84 cards equally among 4 friends. How many cards does each friend get?
84 / 4

Task: Reverse the letters of bcdae.
"bcdae"[::-1]

Task: Write mnop backwards.
"mnop"[::-1]"""


def use_judge(key_or_repo: str):
    """Select the judge model (only one is ever held in memory)."""
    global JUDGE_REPO
    JUDGE_REPO = JUDGES.get(key_or_repo, key_or_repo)
    _load.cache_clear()


def _gen(prompts: list[str], system: str, max_tokens: int, batch: int = 8) -> list[str]:
    if not _has_mlx():
        return _gen_torch(prompts, system, max_tokens, batch)
    import mlx.core as mx
    from mlx_lm.generate import batch_generate
    model, tok = _load(JUDGE_REPO)
    mx.set_cache_limit(256 * 1024 ** 2)  # keep MLX's buffer cache small: the laptop is memory-bound
    out = []
    for s in range(0, len(prompts), batch):
        ids = [tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": p}],
                                       add_generation_prompt=True) for p in prompts[s:s + batch]]
        out += batch_generate(model, tok, ids, max_tokens=max_tokens).texts
        mx.clear_cache()
    return out


def _pal_value(text: str, prompt: str = ""):
    """Value of the program route. A string literal the prompt does not contain is a transcription slip
    by the model (it retyped the input wrongly), so that program is discarded."""
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
        if prompt:
            for n in ast.walk(ast.parse(line, mode="eval")):
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) > 1 and n.value not in prompt:
                    return None
        return canon(safe_eval(line))
    except Exception:
        return None


def _cot_value(text: str):
    """Boxed answer, else the last 'answer/total is X', else the last number of the last line, else a quoted word."""
    b = _BOX.findall(text)
    if b:
        return canon(re.sub(r"\\text\{[^{}]*\}|\\[,!;]|\\%", "", b[-1]))
    lines = [x for x in text.strip().splitlines() if x.strip()]
    if not lines:
        return None
    last = lines[-1]
    n = _NUM.findall(last)
    if n:
        return canon(n[-1])
    q = re.findall(r"['\"`*]+([A-Za-z]+)['\"`*]+", last)
    return canon(q[-1]) if q else None


def solve(prompts: list[str], cot_tokens: int = 320) -> list[dict]:
    """Two independent answers per prompt."""
    cot = _gen(prompts, COT_SYS, cot_tokens)
    pal = _gen(prompts, PAL_SYS, 80)
    res = []
    for c, p, q in zip(cot, pal, prompts):
        a1 = _cot_value(c)
        a2 = _pal_value(p, q)
        res.append({"cot": a1, "pal": a2})
    return res


def _tally(rows: list[dict]) -> dict:
    """Numeric labels: disagreement among items where both routes agree. Text labels: the chain-of-thought route
    cannot do letter-level transforms, so the executed program route alone is used."""
    numeric = sum(re.fullmatch(r"-?\d+(\.\d+)?", r["label"]) is not None for r in rows) >= 0.5 * len(rows)
    if numeric:
        conf = [r for r in rows if r["cot"] is not None and r["cot"] == r["pal"]]
        pick = "cot"
    else:
        conf = [r for r in rows if r["pal"] is not None]
        pick = "pal"
    dis = sum(r[pick] != r["label"] for r in conf)
    return {"route": "both" if numeric else "program", "confident": len(conf), "disagree_n": dis,
            "disagree": round(dis / len(conf), 4) if len(conf) >= 10 else None}


def audit(examples, n: int = 60, extra: int = 60, band: tuple = (0.08, 0.25), seed: int = 0) -> dict:
    """Label-noise estimate on a random sample, with a second sample only when the first lands near the
    decision band: a clear case costs one batch, a close one gets twice the items."""
    rng = random.Random(seed)
    pool = [e for e in examples if label_of(e.completion) is not None]
    if len(pool) < 20:
        return {"sampled": len(pool), "confident": 0, "disagree": None, "rows": []}
    order = rng.sample(pool, min(n + extra, len(pool)))
    labels = [label_of(e.completion) for e in order[:n]]
    top = max(set(labels), key=labels.count)
    if labels.count(top) >= 0.9 * len(labels) and not re.fullmatch(r"-?\d+(\.\d+)?", top):
        return {"sampled": 0, "confident": 0, "disagree": None, "rows": [],
                "reason": f"nearly every row has the same placeholder label ({top!r}), so there is nothing to compare"}

    def run(items):
        sol = solve([e.last_user for e in items])
        return [{"label": label_of(e.completion), **s} for e, s in zip(items, sol)]
    rows = run(order[:n])
    t = _tally(rows)
    if extra and order[n:] and t["disagree"] is not None and band[0] <= t["disagree"] <= band[1]:
        rows += run(order[n:])
        t = _tally(rows)
    return {"sampled": len(rows), **t, "rows": rows}


def _has_mlx() -> bool:
    try:
        import mlx_lm  # noqa: F401
        return True
    except ImportError:
        return False


def available() -> bool:
    if _has_mlx():
        return True
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _load_torch(repo: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(repo, padding_side="left")
    return AutoModelForCausalLM.from_pretrained(repo, torch_dtype=torch.float16).to("cuda").eval(), tok


def _gen_torch(prompts: list[str], system: str, max_tokens: int, batch: int) -> list[str]:
    """GPU machines without MLX (a rented Linux box, for example). Greedy, like the MLX route."""
    import torch
    model, tok = _load_torch(JUDGE_REPO)
    out = []
    for s in range(0, len(prompts), batch):
        texts = [tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": p}],
                                         tokenize=False, add_generation_prompt=True) for p in prompts[s:s + batch]]
        enc = tok(texts, return_tensors="pt", padding=True).to("cuda")
        with torch.no_grad():
            g = model.generate(**enc, max_new_tokens=max_tokens, do_sample=False)
        out += tok.batch_decode(g[:, enc.input_ids.shape[1]:], skip_special_tokens=True)
    return out


def release():
    """Drop the judge before training starts: never hold two large models on 16 GB."""
    _load.cache_clear()
    _load_torch.cache_clear()
    if _has_mlx():
        import mlx.core as mx
        mx.clear_cache()
    import gc
    gc.collect()


MCQ_SYS = "Answer the multiple-choice question. Reply with the letter of the best option and nothing else."
FIT_SYS = ("You check training data. Given a REQUEST and a RESPONSE, decide whether the RESPONSE actually addresses "
           "and fulfils the REQUEST. Reply with YES or NO only.")


def audit_mcq(examples, n: int = 60, seed: int = 0) -> dict:
    """Share of sampled questions where the judge's option differs from the labelled one."""
    from .coverage import mcq_label, mcq_options
    pool = [e for e in examples if len(mcq_options(e.last_user)) >= 2 and mcq_label(e.completion)]
    sample = random.Random(seed).sample(pool, min(n, len(pool)))
    outs = _gen([e.last_user for e in sample], MCQ_SYS, 6)
    pairs = [(mcq_label(o) or (o.strip()[:1].upper() if o.strip() else None), mcq_label(e.completion))
             for o, e in zip(outs, sample)]
    pairs = [(a, b) for a, b in pairs if a]
    dis = sum(a != b for a, b in pairs)
    return {"sampled": len(sample), "answered": len(pairs), "disagree": round(dis / len(pairs), 4) if pairs else None}


def _yes(prompts: list[str], replies: list[str]) -> float:
    q = [f"REQUEST:\n{p[:1500]}\n\nRESPONSE:\n{r[:1500]}" for p, r in zip(prompts, replies)]
    outs = _gen(q, FIT_SYS, 3)
    return sum(o.strip().upper().startswith("YES") for o in outs) / max(1, len(outs))


def audit_fit(examples, n: int = 60, seed: int = 0) -> dict:
    """Judge's YES rate on real pairs, rescaled against the same replies shuffled across prompts:
    fit = (real - shuffled) / (1 - shuffled). Shuffled pairs are the chance level for this dataset."""
    rng = random.Random(seed)
    s = rng.sample(list(examples), min(n, len(examples)))
    if len(s) < 10:
        return {"sampled": len(s), "fit": None}
    ps = [e.last_user for e in s]
    rs = [e.completion for e in s]
    sh = rs[1:] + rs[:1]
    real, base = _yes(ps, rs), _yes(ps, sh)
    return {"sampled": len(s), "yes_real": round(real, 4), "yes_shuffled": round(base, 4),
            "fit": round((real - base) / (1 - base), 4) if base < 1 else None}
