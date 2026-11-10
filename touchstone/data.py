"""Load and validate a post-training dataset (JSONL) for appraisal.

Accepted line formats (one JSON object per line):

    {"prompt": "...", "completion": "..."}
    {"messages": [{"role": "system"|"user"|"assistant", "content": "..."}, ...]}

Also accepted: the field pairs in FIELD_PAIRS (Alpaca "instruction"/"input"/"output",
"question"/"answer", "query"/"response", "problem"/"solution", ...), ShareGPT
"conversations" with "from"/"value", message content as a list of text parts, and
files in .json (one list of records), .csv, .tsv, .parquet (needs pyarrow) or any of
these gzipped. For "messages", the last assistant turn is the training target and
everything before it is the prompt. Invalid rows are skipped and reported, up to
SKIP_LIMIT of the file.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

MIN_EXAMPLES = 20


class DatasetError(ValueError):
    pass


@dataclass
class Example:
    messages: list[dict]  # conversation up to (not including) the target reply
    completion: str
    meta: dict = field(default_factory=dict)  # extra row fields a check can use (tests, tools, choices, ...)

    @property
    def prompt_text(self) -> str:
        """The user-visible prompt, for overlap checks."""
        return "\n".join(m["content"] for m in self.messages if m["role"] == "user")

    @property
    def last_user(self) -> str:
        users = [m["content"] for m in self.messages if m["role"] == "user"]
        return users[-1] if users else ""


def _meta(d: dict, used: tuple) -> dict:
    return {k: v for k, v in d.items() if k not in used}


ROLE_ALIASES = {"human": "user", "user": "user", "gpt": "assistant", "assistant": "assistant", "chatgpt": "assistant",
                "model": "assistant", "bot": "assistant", "bing": "assistant", "system": "system", "tool": "tool",
                "function": "tool", "ipython": "tool"}
# (prompt field, reply field) pairs seen in real public datasets, tried in this order.
FIELD_PAIRS = (("prompt", "completion"), ("prompt", "response"), ("question", "answer"), ("instruction", "output"),
               ("instruction", "response"), ("query", "response"), ("problem", "solution"), ("input", "output"),
               ("question", "response"), ("prompt", "chosen"))
SKIP_LIMIT = 0.10  # invalid rows are skipped and reported while they are at most this share of the file


def _content(c, where: str) -> str:
    """Message content as a string. Accepts OpenAI-style parts lists ([{"type": "text", "text": ...}])."""
    if isinstance(c, str):
        return c
    if isinstance(c, list) and all(isinstance(x, (dict, str)) for x in c):
        parts = [x if isinstance(x, str) else x.get("text") for x in c]
        if all(isinstance(x, str) for x in parts):
            return "".join(parts)
    raise DatasetError(f"{where}: message content must be a string or a list of text parts (got {type(c).__name__})")


def _messages(msgs, where: str, key: str) -> Example:
    if not isinstance(msgs, list) or not msgs:
        raise DatasetError(f"{where}: '{key}' must be a non-empty list")
    out = []
    for m in msgs:
        if not isinstance(m, dict):
            raise DatasetError(f"{where}: every message must be an object")
        role = ROLE_ALIASES.get(str(m.get("role", m.get("from", ""))).lower())
        if role is None:
            raise DatasetError(f"{where}: every message needs role system/user/assistant/tool")
        content = m.get("content", m.get("value"))
        if content is None:
            raise DatasetError(f"{where}: a message has empty (null) content")
        out.append({"role": role, "content": _content(content, where)})
    while out and out[-1]["role"] != "assistant":  # a conversation ending on a user turn trains on its last reply
        out.pop()
    if not out:
        raise DatasetError(f"{where}: no assistant reply to train on")
    if not out[-1]["content"].strip():
        raise DatasetError(f"{where}: the assistant reply to train on is empty")
    if not any(m["role"] == "user" for m in out[:-1]):
        raise DatasetError(f"{where}: needs at least one user message before the assistant reply")
    return Example(out[:-1], out[-1]["content"], {})


def _parse(d: dict, where: str) -> Example:
    if not isinstance(d, dict):
        raise DatasetError(f"{where}: each line must be a JSON object")
    for key in ("messages", "conversations", "conversation"):
        if key in d:
            e = _messages(d[key], where, key)
            e.meta = _meta(d, (key,))
            return e
    for p, c in FIELD_PAIRS:
        if p in d and c in d:
            prompt = d[p]
            if p == "instruction":
                extra = d.get("input") or d.get("context")
                if isinstance(extra, str) and extra.strip():
                    prompt = f"{prompt}\n\n{extra}"
            if prompt is None or d[c] is None:
                raise DatasetError(f"{where}: empty (null) '{p}' or '{c}'")
            if not isinstance(prompt, str) or not isinstance(d[c], (str, int, float)) or isinstance(d[c], bool):
                raise DatasetError(f"{where}: '{p}' and '{c}' must be strings")
            if not prompt.strip() or not str(d[c]).strip():
                raise DatasetError(f"{where}: empty '{p}' or '{c}'")
            return Example([{"role": "user", "content": prompt}], str(d[c]), _meta(d, (p, c, "input", "context")))
    raise DatasetError(f"{where}: unrecognised format; expected 'prompt'+'completion' or 'messages' (got keys {sorted(d)})")


class Rows(list):
    """Parsed examples, plus what was skipped: `skipped` (count of invalid rows) and `skip_reasons` (the first few)."""
    skipped: int = 0
    skip_reasons: list = []
    total: int = 0


def _records(path: Path):
    """(where, record or exception) for every row of a .jsonl, .json, .csv, .tsv or .parquet file (optionally .gz)."""
    name, low = path.name, path.name.lower()
    opener = path.read_bytes
    if low.endswith(".gz"):
        import gzip
        opener = lambda: gzip.decompress(path.read_bytes())  # noqa: E731
        low = low[:-3]
    if low.endswith(".parquet"):
        try:
            import pyarrow.parquet as pq
        except ImportError:
            raise DatasetError(f"{name}: reading parquet needs pyarrow (pip install pyarrow==17.0.0), or convert the file to JSONL") from None
        try:
            rows = pq.read_table(path).to_pylist()
        except Exception as e:
            raise DatasetError(f"{name}: could not read the parquet file ({str(e)[:120]})") from None
        for i, r in enumerate(rows, 1):
            yield f"{name}:row {i}", r
        return
    text = opener().decode("utf-8-sig", errors="replace")  # utf-8-sig drops a byte-order mark from Windows exports
    if low.endswith((".csv", ".tsv")):
        import csv
        import io
        csv.field_size_limit(1 << 30)
        reader = csv.DictReader(io.StringIO(text, newline=""), delimiter="\t" if low.endswith(".tsv") else ",")
        for i, r in enumerate(reader, 2):
            yield f"{name}:{i}", {k.strip(): v for k, v in r.items() if k is not None}
        return
    if low.endswith(".json") or text.lstrip()[:1] == "[":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None  # a .json file that is really JSON lines falls through to the line reader
        if isinstance(data, dict):  # {"data": [...]}, {"train": [...]} or any single list of records
            lists = [v for v in data.values() if isinstance(v, list)]
            data = data.get("data") or data.get("train") or (lists[0] if len(lists) == 1 else None)
            if data is None:
                raise DatasetError(f"{name}: a JSON object file must hold one list of records (e.g. under 'data' or 'train')")
        if isinstance(data, list):
            for i, r in enumerate(data, 1):
                yield f"{name}:record {i}", r
            return
    for ln, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            yield f"{name}:{ln}", json.loads(line)
        except json.JSONDecodeError as e:
            yield f"{name}:{ln}", DatasetError(f"{name}:{ln}: not valid JSON ({e.msg})")


def load_dataset(path: str | Path) -> Rows:
    """Parse a dataset. Invalid rows are skipped and counted while they are at most SKIP_LIMIT of the file; past that
    the file is refused, since it is then more likely the wrong format than a few bad rows."""
    path = Path(path)
    if not path.exists():
        raise DatasetError(f"dataset not found: {path}")
    if path.is_dir():
        raise DatasetError(f"{path} is a folder; --kind dataset expects a .jsonl file (use --kind env for an environment folder)")
    out, errors, total = Rows(), [], 0
    for where, rec in _records(path):
        total += 1
        try:
            if isinstance(rec, Exception):
                raise rec
            out.append(_parse(rec, where))
        except DatasetError as e:
            errors.append(str(e))
    out.total, out.skipped, out.skip_reasons = total, len(errors), errors[:5]
    if errors and (len(errors) > SKIP_LIMIT * total or not out):
        raise DatasetError(f"invalid dataset: {len(errors)} of {total} rows unreadable (at most {SKIP_LIMIT:.0%} can be skipped):\n  "
                           + "\n  ".join(errors[:5]))
    if len(out) < MIN_EXAMPLES:
        raise DatasetError(f"{path}: found {len(out)} examples; an appraisal needs at least {MIN_EXAMPLES}")
    return out


def to_training_pairs(lm, examples: list[Example]) -> list[tuple[str, str]]:
    return [(lm.chat_messages(e.messages), e.completion) for e in examples]


def placebo(examples: list[Example], seed: int = 0) -> list[Example]:
    """Same prompts, completions shuffled across examples.

    Keeps the format, length and answer distribution and destroys the
    prompt-answer link. Gain from training on this is what the format alone
    buys; the dataset's real content value is gain above it.
    """
    rng = random.Random(seed)
    comps = [e.completion for e in examples]
    rng.shuffle(comps)
    return [Example(e.messages, c) for e, c in zip(examples, comps)]


def write_jsonl(path: str | Path, rows: list[dict]):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(json.dumps(r) + "\n" for r in rows))
