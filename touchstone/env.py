"""The environment contract a vendor implements, and the sealed loader.

A vendor ships a folder containing ``env.py`` that defines ``ENV``, an object
with ``name``, ``tasks()`` and ``verify()``. Touchstone only ever sees prompts
and rewards through this interface; reports never include task contents.
"""
from __future__ import annotations

import hashlib
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
    name: str

    def tasks(self) -> list[Task]: ...

    def verify(self, task: Task, output: str) -> float: ...


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
    path = Path(path)
    spec = importlib.util.spec_from_file_location(f"env_{path.name}", path / "env.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ENV
