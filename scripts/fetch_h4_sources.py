"""Fetch real public sources for round 4 (data only, JSON, via the Hugging Face dataset viewer rows API).

Saved to ~/.cache/touchstone/h4/<name>.<split>.json. Nothing fetched is executed. Rows beyond `n` are not needed.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

D = Path.home() / ".cache" / "touchstone" / "h4"
D.mkdir(parents=True, exist_ok=True)
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
    "trec": ("CogComp/trec", "default", "train", "test"),
    "aqua": ("deepmind/aqua_rat", "raw", "train", "test"),
    "truthful": ("truthfulqa/truthful_qa", "multiple_choice", "validation", "validation"),
    "medmcqa": ("openlifescienceai/medmcqa", "default", "train", "validation"),
    "piqa": ("nthngdy/piqa", "plain_text", "train", "validation"),
    "winogrande": ("coref-data/winogrande_raw", "default", "train", "validation"),
    "hellaswag": ("hellaswag", "default", "train", "validation"),
    "emotion": ("dair-ai/emotion", "split", "train", "test"),
    "yelp": ("Yelp/yelp_review_full", "yelp_review_full", "train", "test"),
    "dbpedia": ("fancyzhx/dbpedia_14", "dbpedia_14", "train", "test"),
}


def rows(ds, cfg, split, n):
    out = []
    for off in range(0, n, 100):
        q = urllib.parse.urlencode({"dataset": ds, "config": cfg, "split": split, "offset": off, "length": 100})
        for attempt in range(4):
            try:
                with urllib.request.urlopen("https://datasets-server.huggingface.co/rows?" + q, timeout=60) as r:
                    got = [x["row"] for x in json.load(r)["rows"]]
                break
            except Exception as e:
                if attempt == 3:
                    raise
                time.sleep(3 + attempt * 5)
        out += got
        if len(got) < 100:
            break
        time.sleep(0.3)
    return out


for name, (ds, cfg, ms, ss) in (reversed(list(S.items())) if len(sys.argv) > 1 else S.items()):
    for split, n in ((ms, 1600), (ss, 900)):
        f = D / f"{name}.{split}.json"
        if f.exists():
            continue
        try:
            r = rows(ds, cfg, split, n)
            f.write_text(json.dumps(r))
            print(name, split, len(r), list(r[0])[:7], flush=True)
        except Exception as e:
            print(name, split, "FAILED", str(e)[:90], flush=True)
