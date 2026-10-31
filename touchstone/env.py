"""The environment contract a vendor implements, and the sealed loader.

A vendor ships a folder containing ``env.py`` that defines ``ENV``, an object
with ``name``, ``tasks()`` and ``verify()``. Touchstone only ever sees prompts
and rewards through this interface; reports never include task contents.
"""
from __future__ import annotations

import hashlib
import re
import importlib.util
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Task:
    prompt: str
    meta: dict = field(default_factory=dict, hash=False, compare=False)


class Environment(Protocol):
    """Required: ``name``, ``tasks()``, ``verify(task, output) -> reward in [0, 1]``.

    Optional:
      ``domain``: name of a built-in held-out suite ("arithmetic", "word_math",
                  "strings") the environment claims to teach;
      ``system``: a system prompt shown to the policy;
      ``reference(task) -> str``: a correct answer (else ``task.meta["answer"]``),
                  which unlocks the stronger grader audit (known-wrong answers).
    """
    name: str

    def tasks(self) -> list[Task]: ...

    def verify(self, task: Task, output: str) -> float: ...


_FINAL = re.compile(r"(?:.*?(?:=|\bis\b|:)\s*)?['\"`*]*([A-Za-z0-9-]+)['\"`*]*", re.S)


def final_answer(output: str) -> str | None:
    """A strict but format-tolerant answer parser that vendors can use in verify().

    Accepts a bare answer ("742"), or one final answer after '=', 'is' or ':'
    ("673 + 69 = 742", "The reversed string is 'cba'."). Rejects anything with
    more than one candidate at the end ("85 86", "86 or 85", "junk 85 junk").
    """
    m = _FINAL.fullmatch(output.strip().rstrip(".!").strip())
    return m.group(1).lower() if m else None


def short(task: Task) -> str:
    """The compact prompt used by the legacy character-level models."""
    return task.meta.get("short", task.prompt)


def reference(env, task: Task) -> str | None:
    if hasattr(env, "reference"):
        r = env.reference(task)
        return None if r is None else str(r)
    a = task.meta.get("answer")
    return None if a is None else str(a)


class EnvError(ValueError):
    pass


def validate(env, path) -> list[Task]:
    """Check the contract and fail with a clear message instead of a stack trace mid-run."""
    for attr in ("tasks", "verify"):
        if not callable(getattr(env, attr, None)):
            raise EnvError(f"{path}: ENV must have a callable {attr}()")
    try:
        tasks = list(env.tasks())
    except Exception as e:  # vendor code: report, don't crash
        raise EnvError(f"{path}: ENV.tasks() raised {type(e).__name__}: {e}") from None
    if len(tasks) < 20:
        raise EnvError(f"{path}: ENV.tasks() returned {len(tasks)} tasks; an appraisal needs at least 20")
    bad = [i for i, t in enumerate(tasks[:200]) if not isinstance(getattr(t, "prompt", None), str) or not t.prompt.strip()]
    if bad:
        raise EnvError(f"{path}: task {bad[0]} has no string prompt; tasks must be touchstone.env.Task(prompt, meta)")
    for t in tasks[:20]:
        try:
            r = float(env.verify(t, ""))
        except Exception as e:
            raise EnvError(f"{path}: ENV.verify(task, '') raised {type(e).__name__}: {e}") from None
        if not 0.0 <= r <= 1.0:
            raise EnvError(f"{path}: ENV.verify returned {r}; rewards must be in [0, 1]")
    return tasks


def _hash_dir(path: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(path.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            h.update(str(f.relative_to(path)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def seal(src: str | Path, vault: str | Path) -> dict:
    """Copy a vendor environment into the vault and record its fingerprint.

    In production this happens inside an isolated container with no network,
    and only Touchstone's runner can read the vault. The fingerprint lets the
    buyer confirm the environment they purchase is the one that was appraised.
    """
    src, vault = Path(src), Path(vault)
    digest = _hash_dir(src)
    dest = vault / f"{src.name}-{digest[:12]}"
    if not dest.exists():
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
    manifest = {"env_dir": src.name, "sha256": digest, "vault_path": str(dest)}
    (dest / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def load(path: str | Path) -> Environment:
    """Load ENV from a folder containing env.py, or from a single .py file."""
    path = Path(path)
    file = path / "env.py" if path.is_dir() else path
    if not file.exists() or file.suffix != ".py":
        raise EnvError(f"{path}: expected a folder with env.py or a .py file defining ENV")
    name = path.name if path.is_dir() else path.stem
    spec = importlib.util.spec_from_file_location(f"env_{name}", file)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        raise EnvError(f"{file}: failed to import ({type(e).__name__}: {e})") from None
    if not hasattr(mod, "ENV"):
        raise EnvError(f"{file}: must define a module-level ENV object (see touchstone/env.py)")
    return mod.ENV
