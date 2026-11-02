"""Load and validate a post-training dataset (JSONL) for appraisal.

Accepted line formats (one JSON object per line):

    {"prompt": "...", "completion": "..."}
    {"messages": [{"role": "system"|"user"|"assistant", "content": "..."}, ...]}

Also accepted as aliases: "instruction"/"input"/"output" (Alpaca style) and
"question"/"answer". For "messages", the final assistant turn is the training
target and everything before it is the prompt.
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


def _parse(d: dict, where: str) -> Example:
    if not isinstance(d, dict):
        raise DatasetError(f"{where}: each line must be a JSON object")
    if "messages" in d:
        msgs = d["messages"]
        if not isinstance(msgs, list) or not msgs:
            raise DatasetError(f"{where}: 'messages' must be a non-empty list")
        for m in msgs:
            if not isinstance(m, dict) or m.get("role") not in ("system", "user", "assistant", "tool") or not isinstance(m.get("content"), str):
                raise DatasetError(f"{where}: every message needs role system/user/assistant/tool and string content")
        if msgs[-1]["role"] != "assistant":
            raise DatasetError(f"{where}: the last message must be the assistant reply to train on")
        if not any(m["role"] == "user" for m in msgs[:-1]):
            raise DatasetError(f"{where}: needs at least one user message before the assistant reply")
        return Example([dict(m) for m in msgs[:-1]], msgs[-1]["content"], _meta(d, ("messages",)))
    for p, c in (("prompt", "completion"), ("question", "answer"), ("instruction", "output")):
        if p in d and c in d:
            prompt = d[p]
            if p == "instruction" and d.get("input"):
                prompt = f"{prompt}\n\n{d['input']}"
            if not isinstance(prompt, str) or not isinstance(d[c], (str, int, float)):
                raise DatasetError(f"{where}: '{p}' and '{c}' must be strings")
            if not prompt.strip() or not str(d[c]).strip():
                raise DatasetError(f"{where}: empty '{p}' or '{c}'")
            return Example([{"role": "user", "content": prompt}], str(d[c]), _meta(d, (p, c, "input")))
    raise DatasetError(f"{where}: unrecognised format; expected 'prompt'+'completion' or 'messages' (got keys {sorted(d)})")


def load_dataset(path: str | Path) -> list[Example]:
    path = Path(path)
    if not path.exists():
        raise DatasetError(f"dataset not found: {path}")
    if path.is_dir():
        raise DatasetError(f"{path} is a folder; --kind dataset expects a .jsonl file (use --kind env for an environment folder)")
    out = []
    errors = []
    for ln, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(_parse(json.loads(line), f"{path.name}:{ln}"))
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}:{ln}: not valid JSON ({e.msg})")
        except DatasetError as e:
            errors.append(str(e))
        if len(errors) >= 5:
            break
    if errors:
        raise DatasetError("invalid dataset:\n  " + "\n  ".join(errors))
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
