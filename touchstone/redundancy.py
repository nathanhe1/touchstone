"""Overlap checks run inside the vault, so no task text leaves it.

Redundancy: how much of the environment is already in free public sets.
Contamination: how much overlaps Touchstone's private held-out suite, which
would inflate transfer and is flagged rather than rewarded.
"""
from __future__ import annotations


def _norm(p: str) -> str:
    return "".join(p.split()).lower()


def overlap(tasks, reference) -> float:
    ref = {_norm(t.prompt) for t in reference}
    if not tasks:
        return 0.0
    return sum(_norm(t.prompt) in ref for t in tasks) / len(tasks)


def redundancy(env, public_envs) -> dict:
    tasks = env.tasks()
    pool = [t for e in public_envs for t in e.tasks()]
    uniq = len({_norm(t.prompt) for t in tasks})
    return {"public_overlap": overlap(tasks, pool), "unique_tasks": uniq, "n_tasks": len(tasks)}


def contamination(env, heldout_tasks) -> float:
    return overlap(env.tasks(), heldout_tasks)
