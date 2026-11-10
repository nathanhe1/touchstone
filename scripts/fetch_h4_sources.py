"""Fetch real public sources for the forecast tests (data only, JSON, via the Hugging Face dataset viewer rows API).

    python scripts/fetch_h4_sources.py [--out DIR] [--only fam1,fam2] [--seed 20261110]

Rows are a seeded random sample of the whole split, never its first rows. The h4 fetch read the first rows, and some
sources are stored sorted by label: `dbpedia` came out as one class and `imdb` as 78% one class (METHOD.md, h4).
A split no larger than the number of rows wanted is fetched whole. A larger one is read in short blocks at seeded
random offsets (blocks of 20, so a label-sorted source still yields every class), then shuffled with the same seed.
The sample's provenance (dataset, config, split, split size, offsets' seed, block size) is written beside it.

Saved to $H4_DATA or ~/.cache/touchstone/h5/<name>.<split>.json. Nothing fetched is executed.
"""
import argparse
import json
import os
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path

S = {  # name: (dataset, config, material split, suite split)
    "arc": ("allenai/ai2_arc", "ARC-Challenge", "train", "test"),
    "arc_easy": ("allenai/ai2_arc", "ARC-Easy", "train", "test"),
    "openbook": ("allenai/openbookqa", "main", "train", "test"),
    "csqa": ("tau/commonsense_qa", "default", "train", "validation"),
    "sciq": ("allenai/sciq", "default", "train", "test"),
    "qasc": ("allenai/qasc", "default", "train", "validation"),
    "mmlu": ("cais/mmlu", "all", "test", "validation"),
    "boolq": ("google/boolq", "default", "train", "validation"),
    "ag_news": ("fancyzhx/ag_news", "default", "train", "test"),
    "rotten": ("cornell-movie-review-data/rotten_tomatoes", "default", "train", "test"),
    "aqua": ("deepmind/aqua_rat", "raw", "train", "test"),
    "medmcqa": ("openlifescienceai/medmcqa", "default", "train", "validation"),
    "emotion": ("dair-ai/emotion", "split", "train", "test"),
    "yelp": ("Yelp/yelp_review_full", "yelp_review_full", "train", "test"),
    "dbpedia": ("fancyzhx/dbpedia_14", "dbpedia_14", "train", "test"),
    "imdb": ("stanfordnlp/imdb", "plain_text", "train", "test"),
    "amazon": ("fancyzhx/amazon_polarity", "amazon_polarity", "train", "test"),
    "cr": ("SetFit/CR", "default", "train", "test"),
    "subj": ("SetFit/subj", "default", "train", "test"),
    "enron": ("SetFit/enron_spam", "default", "train", "test"),
    "sst5": ("SetFit/sst5", "default", "train", "test"),
    "bbc": ("SetFit/bbc-news", "default", "train", "test"),
}
WANT = {"material": 3200, "suite": 1200}
BLOCK = 20
API = "https://datasets-server.huggingface.co"


def _get(path, **q):
    url = f"{API}/{path}?" + urllib.parse.urlencode(q)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(3 + attempt * 5)


def split_size(ds, cfg, split):
    for s in _get("size", dataset=ds)["size"]["splits"]:
        if s["config"] == cfg and s["split"] == split:
            return s["num_rows"]
    raise KeyError(f"{ds}/{cfg}/{split} not found")


def block(ds, cfg, split, off, n):
    return [x["row"] for x in _get("rows", dataset=ds, config=cfg, split=split, offset=off, length=n)["rows"]]


def sample(ds, cfg, split, n, seed):
    """A seeded random sample of about n rows from the whole split, in shuffled order."""
    total = split_size(ds, cfg, split)
    rng = random.Random(f"{seed}|{ds}|{cfg}|{split}")
    if total <= n:
        out = []
        for off in range(0, total, 100):
            out += block(ds, cfg, split, off, min(100, total - off))
            time.sleep(0.2)
        offsets = None
    else:
        k = -(-n // BLOCK)
        offsets = sorted(rng.sample(range(0, total - BLOCK + 1, BLOCK), k))
        out = []
        for off in offsets:
            out += block(ds, cfg, split, off, BLOCK)
            time.sleep(0.15)
    rng.shuffle(out)
    return out, {"dataset": ds, "config": cfg, "split": split, "split_rows": total, "fetched": len(out), "seed": seed,
                 "method": "whole split" if offsets is None else f"{len(offsets)} blocks of {BLOCK} at seeded random offsets"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.environ.get("H4_DATA", str(Path.home() / ".cache" / "touchstone" / "h5")))
    ap.add_argument("--only", default="")
    ap.add_argument("--seed", type=int, default=20261110)
    a = ap.parse_args()
    d = Path(a.out)
    d.mkdir(parents=True, exist_ok=True)
    names = [x for x in a.only.split(",") if x] or list(S)
    for name in names:
        ds, cfg, ms, ss = S[name]
        for split, n in ((ms, WANT["material"]), (ss, WANT["suite"])):
            f = d / f"{name}.{split}.json"
            if f.exists():
                continue
            try:
                r, prov = sample(ds, cfg, split, n, a.seed)
                f.write_text(json.dumps(r))
                (d / f"{name}.{split}.prov.json").write_text(json.dumps(prov))
                print(name, split, len(r), prov["method"], flush=True)
            except Exception as e:
                print(name, split, "FAILED", str(e)[:90], flush=True)


if __name__ == "__main__":
    main()
