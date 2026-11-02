"""Snapshots of free public word-problem corpora, the 'already free' baseline for word_math (round 3).

Round 2 compared word problems only against GSM8K train. A vendor can as easily resell GSM8K test,
SVAMP or ASDiv, so the baseline is now all four (about 12,000 problems). Each is a well-known public
release fetched once from its authors' repository and cached under ~/.cache/touchstone/public/.

    GSM8K train/test  Cobbe et al. 2021, github.com/openai/grade-school-math        (7,473 + 1,319)
    SVAMP             Patel et al. 2021, github.com/arkilpatel/SVAMP                (1,000)
    ASDiv             Miao et al. 2020, github.com/chaochun/nlu-asdiv-dataset        (2,305)
"""
from __future__ import annotations

import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CACHE = Path.home() / ".cache" / "touchstone"
SOURCES = {
    "gsm8k_train": (CACHE / "gsm8k_train.jsonl",
                    "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/train.jsonl"),
    "gsm8k_test": (CACHE / "public" / "gsm8k_test.jsonl",
                   "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/test.jsonl"),
    "svamp": (CACHE / "public" / "svamp.json", "https://raw.githubusercontent.com/arkilpatel/SVAMP/main/SVAMP.json"),
    "asdiv": (CACHE / "public" / "asdiv.xml",
              "https://raw.githubusercontent.com/chaochun/nlu-asdiv-dataset/master/dataset/ASDiv.xml"),
}


def _fetch(name: str) -> Path:
    f, url = SOURCES[name]
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, f)
    return f


def questions(name: str) -> list[str]:
    f = _fetch(name)
    if name.startswith("gsm8k"):
        return [json.loads(x)["question"] for x in f.read_text().splitlines() if x.strip()]
    if name == "svamp":
        return [r["Body"].strip().rstrip(".") + ". " + r["Question"].strip() for r in json.loads(f.read_text())]
    if name == "asdiv":
        root = ET.parse(f).getroot()
        return [(p.findtext("Body") or "").strip() + " " + (p.findtext("Question") or "").strip() for p in root.iter("Problem")]
    raise KeyError(name)


def word_problems() -> list[str]:
    out = []
    for name in SOURCES:
        try:
            out += questions(name)
        except OSError:  # offline and not cached: use what is available
            continue
    return out
