"""What kind of data is this, which label checks apply to it, and what stayed unchecked.

A dataset that no check can read must never look clean. So every appraisal gets a `checks` block that
says, per check, "checked", "partial" or "not_checked", with the reason. The type comes from the rows'
content and fields, never from file names.

Label checks by type:
    numeric answers    arithmetic audit of working; judge re-solves the item two ways
    short transforms   judge (program route executes the transform)
    multiple choice    judge picks an option; compared with the labelled option
    code with tests    the label runs against its tests in a restricted sandbox (codecheck.py)
    code, no tests     syntax only: partial
    tool-use           calls checked against declared tools: partial, the choice of tool is not judged
    free text, chat    judge rates fit of reply to request, calibrated by shuffled pairs: partial
"""
from __future__ import annotations

import ast
import json
import random
import re

from .judge import label_of

_OPTION = re.compile(r"(?m)^\s*\(?([A-Ha-h])[).:]\s+\S")
_INLINE_OPTION = re.compile(r"(?:^|\s)\(([A-Ha-h])\)\s+\S")
_LETTER = re.compile(r"^\W*(?:the\s+)?(?:correct\s+)?(?:answer|option)?(?:\s+is)?\W*([A-Ha-h])\W*$", re.I)
_CODE = re.compile(r"```|^\s*(def |class |import |from \w+ import|function |#include|public static|fn |SELECT )", re.M)
_CALL = re.compile(r"<(?:functioncall|tool_call)>\s*(\{.*\})", re.S)
_STOP = set("the of and to in is that for it was with as on be are this by you have from not".split())


def language(texts: list[str]) -> str:
    """'en' or 'non_en', from non-Latin characters and the share of common English words."""
    t = " ".join(texts)[:20000]
    if not t:
        return "en"
    letters = [c for c in t if c.isalpha()]
    if letters and sum(ord(c) > 0x24F for c in letters) / len(letters) > 0.3:
        return "non_en"
    words = re.findall(r"[^\W\d_]+", t.lower())
    return "en" if not words or sum(w in _STOP for w in words) / len(words) >= 0.08 else "non_en"


def mcq_options(prompt: str) -> list[str]:
    o = _OPTION.findall(prompt) or _INLINE_OPTION.findall(prompt)
    return [x.upper() for x in o]


def mcq_label(completion: str) -> str | None:
    m = _LETTER.match(completion.strip())
    return m.group(1).upper() if m else None


def tool_call(text: str) -> tuple[dict | None, bool]:
    """(parsed call, whether the text attempts one)."""
    m = _CALL.search(text)
    if m:
        raw = m.group(1)
    elif re.search(r"<(?:functioncall|tool_call)>", text):
        return None, True  # a call was attempted and never closed
    elif text.lstrip().startswith("{") and '"name"' in text:
        raw = text.strip()
    else:
        return None, False
    try:
        return json.loads(raw.replace("'{", "{").replace("}'", "}")), True
    except ValueError:
        return None, True


def detect_type(examples) -> str:
    s = examples[:300]
    n = len(s)
    if sum(bool(e.meta.get("tools")) or tool_call(e.completion)[1] or any(m["role"] == "tool" for m in e.messages) for e in s) >= 0.3 * n:
        return "tool_use"
    if sum(bool(e.meta.get("test") or e.meta.get("tests") or e.meta.get("test_list")) for e in s) >= 0.5 * n:
        return "code"
    if sum(len(mcq_options(e.last_user)) >= 2 and mcq_label(e.completion) is not None for e in s) >= 0.5 * n:
        return "multiple_choice"
    if sum(bool(_CODE.search(e.completion)) for e in s) >= 0.5 * n:
        return "code"
    if sum(sum(m["role"] == "user" for m in e.messages) >= 2 for e in s) >= 0.5 * n:
        return "chat"
    short = sum(label_of(e.completion) is not None and len(e.completion.split()) <= 3 for e in s)
    digits = sum(bool(re.search(r"\d", e.last_user)) and re.search(r"\d", e.completion) is not None for e in s)
    if digits >= 0.5 * n:
        return "numeric"
    if short >= 0.5 * n:
        return "short_transform"
    return "free_text"


def _syntax(examples, n=200) -> dict:
    from .codecheck import strip_fence
    s = [e for e in examples[:n]]
    bad = 0
    tried = 0
    for e in s:
        c = strip_fence(e.completion)
        if re.search(r"^\s*(def |class |import )", c, re.M):
            tried += 1
            try:
                ast.parse(c)
            except (SyntaxError, ValueError):
                bad += 1
    return {"tried": tried, "invalid": bad, "rate": round(bad / tried, 4) if tried else None}


def tools_of(e) -> dict:
    """Declared tools {name: spec} from a row's `tools` field or JSON in its system message."""
    raw = e.meta.get("tools")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = None
    if not raw:
        raw = []
        dec = json.JSONDecoder()
        for m in e.messages:
            if m["role"] != "system":
                continue
            t, i = m["content"], 0
            while True:
                i = t.find("{", i)
                if i < 0:
                    break
                try:
                    o, j = dec.raw_decode(t[i:])
                    raw.append(o)
                    i += j
                except ValueError:
                    i += 1
    out = {}
    for r in raw if isinstance(raw, list) else [raw]:
        r = r.get("function", r) if isinstance(r, dict) else {}
        if r.get("name"):
            out[r["name"]] = r
    return out


TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}


def tool_audit(examples, n: int = 300) -> dict:
    """Structural: the call parses, names a declared tool, and its arguments fit the declared parameters."""
    checked = bad = 0
    why: dict[str, int] = {}
    for e in examples[:n]:
        call, attempted = tool_call(e.completion)
        if not attempted:
            continue
        tools = tools_of(e)
        checked += 1
        problem = None
        if call is None:
            problem = "unparseable"
        elif call.get("name") not in tools:
            problem = "undeclared_tool"
        else:
            p = tools[call["name"]].get("parameters", {}) or {}
            args = call.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = None
            props = p.get("properties", {}) or {}
            if not isinstance(args, dict):
                problem = "bad_arguments"
            elif any(r not in args for r in p.get("required", []) or []):
                problem = "missing_required"
            elif props and any(k not in props for k in args):
                problem = "unknown_argument"
            elif any(k in props and props[k].get("type") in TYPES and not isinstance(v, TYPES[props[k]["type"]])
                     for k, v in args.items()):
                problem = "wrong_type"
        if problem:
            bad += 1
            why[problem] = why.get(problem, 0) + 1
    return {"checked": checked, "violations": bad, "rate": round(bad / checked, 4) if checked else None, "why": why}


def label_checks(dtype: str, examples, arithmetic: dict | None = None, use_judge: bool = True) -> dict:
    """{'status', 'method', 'estimate', 'noisy', 'reason', ...} for the labels of one dataset."""
    from . import judge, screen
    from .codecheck import audit as code_audit, isolation
    have_judge = use_judge and judge.available()
    no_judge = "no reference judge on this machine (needs MLX, or transformers with a GPU)"

    def done(status, method, noisy=False, **kw):
        return {"status": status, "method": method, "noisy": bool(noisy), **kw}

    if dtype == "code":
        if any(e.meta.get("test") or e.meta.get("tests") or e.meta.get("test_list") for e in examples):
            if isolation() is None:
                return done("not_checked", "code tests", reason="no process isolation on this machine, so vendor code was not run")
            r = code_audit(examples)
            return done("checked", "code tests in a sandbox", (r["rate"] or 0) >= screen.CODE_FAIL_RATE, **r)
        r = _syntax(examples)
        return done("partial" if r["tried"] else "not_checked", "syntax only", (r["rate"] or 0) >= screen.CODE_FAIL_RATE,
                    reason="no tests supplied, so behaviour is unchecked", **r)
    if dtype == "tool_use":
        r = tool_audit(examples)
        if not r["checked"]:
            return done("not_checked", "tool-call structure", reason="no parseable tool calls found")
        return done("partial", "tool-call structure", r["rate"] >= screen.TOOL_BAD_RATE,
                    reason="calls are checked against declared tools; whether the right tool was chosen is not", **r)
    if not have_judge:
        a = arithmetic or {}
        if dtype == "numeric" and a.get("rate") is not None:
            return done("partial", "arithmetic of worked solutions", a["rate"] >= screen.NOISY_EQ_RATE, reason=no_judge)
        return done("not_checked", "reference judge", reason=no_judge)
    if dtype == "multiple_choice":
        r = judge.audit_mcq(examples)
        return done("checked", "judge picks an option", (r["disagree"] or 0) >= screen.MCQ_DISAGREE, **r)
    if dtype in ("free_text", "chat"):
        r = judge.audit_fit(examples)
        return done("partial", "judge rates reply fit, calibrated by shuffled pairs",
                    r["fit"] is not None and r["fit"] < screen.FIT_MIN,
                    reason="fit to the request is checked; factual accuracy is not", **r)
    r = judge.audit(examples)
    return done("checked", "judge re-solves two ways", False, **{k: v for k, v in r.items() if k != "rows"})


def public_status(pub_prompts: list, dtype: str) -> dict:
    if pub_prompts:
        return {"status": "checked", "baseline_items": len(pub_prompts)}
    return {"status": "not_checked", "reason": "no public baseline for this data type; pass --public"}


def rng_sample(items, n, seed=0):
    r = random.Random(seed)
    return r.sample(items, min(n, len(items)))
