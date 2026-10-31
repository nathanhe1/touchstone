"""Fetch small public samples (data only, JSON) for the all-data-types coverage eval.

Saved under ~/.cache/touchstone/coverage/. Uses the Hugging Face dataset-viewer rows API and raw files
from the authors' repositories; nothing fetched is ever executed outside the code sandbox.
"""
import gzip
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

D = Path.home() / ".cache" / "touchstone" / "coverage"
D.mkdir(parents=True, exist_ok=True)
ROWS = {
    "arc": ("allenai/ai2_arc", "ARC-Challenge", "test"),
    "dolly": ("databricks/databricks-dolly-15k", "default", "train"),
    "mgsm_es": ("juletxara/mgsm", "es", "test"),
    "mgsm_de": ("juletxara/mgsm", "de", "test"),
    "glaive": ("glaiveai/glaive-function-calling-v2", "default", "train"),
    "soda": ("allenai/soda", "default", "test"),
}
FILES = {"mbpp.jsonl": "https://raw.githubusercontent.com/google-research/google-research/master/mbpp/mbpp.jsonl",
         "humaneval.jsonl.gz": "https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl.gz"}


def rows(ds, cfg, split, n=400):
    out = []
    for off in range(0, n, 100):
        q = urllib.parse.urlencode({"dataset": ds, "config": cfg, "split": split, "offset": off, "length": 100})
        with urllib.request.urlopen("https://datasets-server.huggingface.co/rows?" + q, timeout=60) as r:
            got = [x["row"] for x in json.load(r)["rows"]]
        out += got
        if len(got) < 100:
            break
        time.sleep(0.5)
    return out


for name, (ds, cfg, split) in ROWS.items():
    f = D / f"{name}.json"
    if f.exists():
        continue
    try:
        f.write_text(json.dumps(rows(ds, cfg, split)))
        print(name, len(json.loads(f.read_text())), flush=True)
    except Exception as e:
        print(name, "FAILED", e, flush=True)
for name, url in FILES.items():
    f = D / name
    if not f.exists():
        try:
            urllib.request.urlretrieve(url, f)
            print(name, f.stat().st_size, flush=True)
        except Exception as e:
            print(name, "FAILED", e, flush=True)
if (D / "humaneval.jsonl.gz").exists():
    (D / "humaneval.jsonl").write_bytes(gzip.open(D / "humaneval.jsonl.gz").read())
