"""Overlap between appraised material and (a) the held-out suite, (b) free public data.

Three tiers, cheapest first, following the decontamination literature:

1. exact: identical after lower-casing and stripping whitespace/punctuation;
2. near-duplicate: character 5-gram Jaccard >= 0.6 (Broder 1997; Lee et al. 2022
   "Deduplicating Training Data Makes Language Models Better");
3. paraphrase: sentence-embedding cosine (all-MiniLM-L6-v2) above a threshold,
   which catches reworded copies that string checks miss (Yang et al. 2023,
   "Rethinking Benchmark and Contamination for Language Models with Rephrased
   Samples").

For text that contains numbers, a near-duplicate or paraphrase match also
requires the same multiset of numbers. Otherwise every "Sam has 12 apples"
would match every "Sam has 15 apples", which is the same template, not the
same item.
"""
from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

import torch

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
JACCARD = 0.6
COS_NUMERIC = 0.85
COS_TEXT = 0.92

_NUM = re.compile(r"\d+(?:\.\d+)?")


def norm(s: str) -> str:
    return re.sub(r"[\W_]+", " ", s.lower()).strip()


def numbers(s: str) -> tuple:
    return tuple(sorted(Counter(_NUM.findall(s.replace(",", ""))).elements()))


def shingles(s: str, n: int = 5) -> set:
    s = norm(s)
    return {s[i:i + n] for i in range(max(1, len(s) - n + 1))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


@lru_cache(maxsize=1)
def _embedder():
    from transformers import AutoModel, AutoTokenizer
    from .lm import cached, device
    tok = cached(AutoTokenizer.from_pretrained, EMBED_MODEL)
    model = cached(AutoModel.from_pretrained, EMBED_MODEL, attn_implementation="eager").to(device()).eval()
    return tok, model


@torch.no_grad()
def embed(texts: list[str], batch: int = 128) -> torch.Tensor:
    tok, model = _embedder()
    out = []
    for s in range(0, len(texts), batch):
        enc = tok(texts[s:s + batch], padding=True, truncation=True, max_length=128, return_tensors="pt").to(model.device)
        h = model(**enc).last_hidden_state
        m = enc.attention_mask.unsqueeze(-1).float()
        v = (h * m).sum(1) / m.sum(1)
        out.append(torch.nn.functional.normalize(v, dim=-1).cpu())
    return torch.cat(out) if out else torch.zeros(0, 384)


def embed_cached(texts: list[str]) -> torch.Tensor:
    """Embeddings for a reference set, cached on disk (the public baselines are large and fixed)."""
    import hashlib
    from pathlib import Path
    key = hashlib.sha256("\x00".join(texts).encode()).hexdigest()[:16]
    f = Path.home() / ".cache" / "touchstone" / "emb" / f"{key}.pt"
    if f.exists():
        return torch.load(f)
    E = embed(texts)
    if len(texts) >= 500:
        f.parent.mkdir(parents=True, exist_ok=True)
        torch.save(E, f)
    return E


def match(items: list[str], reference: list[str], use_embeddings: bool = True, k: int = 5) -> dict:
    """For each item, whether it matches anything in reference, and how."""
    if not items or not reference:
        return {"rate": 0.0, "exact": 0.0, "near": 0.0, "paraphrase": 0.0, "n": len(items), "matched_idx": [], "examples": []}
    ref_norm = {}
    for j, r in enumerate(reference):
        ref_norm.setdefault(norm(r), j)
    ref_sh = [shingles(r) for r in reference]
    ref_num = [numbers(r) for r in reference]
    by_num: dict[tuple, list[int]] = {}
    for j, nm in enumerate(ref_num):
        by_num.setdefault(nm, []).append(j)

    kinds = [None] * len(items)
    pairs = [None] * len(items)
    for i, s in enumerate(items):
        n = norm(s)
        if n in ref_norm:
            kinds[i], pairs[i] = "exact", ref_norm[n]
            continue
        nm = numbers(s)
        cands = by_num.get(nm, []) if nm else []
        if nm and len(cands) <= 200:  # same numbers: compare strings directly
            sh = shingles(s)
            for j in cands:
                if jaccard(sh, ref_sh[j]) >= JACCARD:
                    kinds[i], pairs[i] = "near", j
                    break

    if use_embeddings:
        todo = [i for i, kd in enumerate(kinds) if kd is None]
        if todo:
            E = embed_cached(reference)
            Q = embed([items[i] for i in todo])
            for s in range(0, len(todo), 512):
                sims = Q[s:s + 512] @ E.T
                top = sims.topk(min(k, E.shape[0]), dim=1)
                for row, i in enumerate(todo[s:s + 512]):
                    nm = numbers(items[i])
                    for v, j in zip(top.values[row].tolist(), top.indices[row].tolist()):
                        if (nm and nm == ref_num[j] and v >= COS_NUMERIC) or (not nm and not ref_num[j] and v >= COS_TEXT):
                            kinds[i], pairs[i] = "paraphrase", j
                            break
                        if not nm and jaccard(shingles(items[i]), ref_sh[j]) >= 0.8:
                            kinds[i], pairs[i] = "near", j
                            break

    c = Counter(kinds)
    n = len(items)
    matched = [i for i, kd in enumerate(kinds) if kd]
    return {
        "rate": len(matched) / n,
        "exact": c["exact"] / n, "near": c["near"] / n, "paraphrase": c["paraphrase"] / n,
        "n": n, "matched_idx": matched,
        "examples": [{"item": items[i][:160], "matches": reference[pairs[i]][:160], "kind": kinds[i]} for i in matched[:3]],
    }


SHORT_WORDS = 25  # fingerprints are used for short, number-carrying prompts (templated tasks)


def _short_numeric(s: str, min_numbers: int = 2) -> bool:
    return len(s.split()) <= SHORT_WORDS and len(numbers(s)) >= min_numbers


def fingerprint_overlap(items: list[str], reference: list[str], min_numbers: int = 2) -> dict:
    """Chance-corrected copy rate for short templated prompts (round 2).

    Rewording ("What's 65 plus 41?" vs "Calculate 65 + 41.") defeats string and embedding
    matching on very short prompts, but the numbers survive. A prompt's fingerprint is its sorted
    multiset of numbers. Honest material drawn from the same number space also collides with the
    public set by chance, so the chance rate is measured directly: the same fingerprints with every
    number shifted by +1 (same distribution, different identities). The copy rate is the excess
    over chance, scaled to the share of material that is short and numeric.

    `min_numbers` = 3 for prose corpora (round 3): two small numbers collide with thousands of unrelated
    public word problems more than the shift estimates, which cost clean data a false 5-12%.
    """
    ref = {numbers(r) for r in reference if _short_numeric(r, min_numbers)}
    elig = [s for s in items if _short_numeric(s, min_numbers)]
    if not ref or not elig:
        return {"rate": 0.0, "observed": 0.0, "chance": 0.0, "eligible": len(elig) / max(1, len(items))}

    def shifted(fp):
        return tuple(sorted(str(int(float(x)) + 1) if "." not in x else x for x in fp))
    fps = [numbers(s) for s in elig]
    obs = sum(fp in ref for fp in fps) / len(fps)
    chance = sum(shifted(fp) in ref for fp in fps) / len(fps)
    excess = max(0.0, (obs - chance) / (1 - chance)) if chance < 1 else 0.0
    share = len(elig) / len(items)
    return {"rate": round(excess * share, 4), "observed": round(obs, 4), "chance": round(chance, 4),
            "eligible": round(share, 4)}


def duplicates(items: list[str]) -> dict:
    """Internal duplication: how many items are exact or near copies of another item."""
    seen = {}
    uniq = 0
    for s in items:
        n = norm(s)
        if n not in seen:
            seen[n] = 1
            uniq += 1
    return {"n": len(items), "unique": uniq, "dup_rate": 1 - uniq / len(items) if items else 0.0}
