"""Round 4 forecast families: real public sources in one prompt form, scored the same way at every size."""
import json
import os
import re
from pathlib import Path

D = Path(os.environ.get("H4_DATA", Path.home() / ".cache" / "touchstone" / "h4"))
LETTERS = "ABCDEFGHIJKLMNOP"
_FIRST = re.compile(r"\b([A-P])\b")


def load(name, split):
    f = D / f"{name}.{split}.json"
    return json.loads(f.read_text()) if f.exists() else []


def mc(q, opts, key):
    """(prompt, answer letter, chance)."""
    text = q.strip() + "\n" + "\n".join(f"{LETTERS[i]}) {str(o).strip()}" for i, o in enumerate(opts))
    return text + "\nReply with the letter only.", LETTERS[key], 1 / len(opts)


def _choices(r):
    t, l = r["choices"]["text"], r["choices"]["label"]
    if r["answerKey"] not in l:
        return None
    return mc(r.get("question") or r.get("question_stem") or r.get("formatted_question", ""), t, l.index(r["answerKey"]))


LABELS = {"ag_news": ["World", "Sports", "Business", "Technology"], "rotten": ["negative", "positive"],
          "trec": ["abbreviation", "entity", "description", "person", "location", "number"],
          "emotion": ["sadness", "joy", "love", "anger", "fear", "surprise"],
          "yelp": ["1 star", "2 stars", "3 stars", "4 stars", "5 stars"],
          "dbpedia": ["company", "school", "artist", "athlete", "politician", "transport", "building", "river", "village",
                      "animal", "plant", "album", "film", "book"]}


def row(name, r):
    if name in ("arc", "arc_easy", "openbook", "csqa"):
        return _choices(r)
    if name == "qasc":
        return _choices(r)
    if name == "sciq":
        o = [r["correct_answer"], r["distractor1"], r["distractor2"], r["distractor3"]]
        k = (sum(map(ord, r["question"])) % 4)
        o[0], o[k] = o[k], o[0]
        return mc(r["question"], o, k)
    if name == "mmlu":
        return mc(r["question"], r["choices"], int(r["answer"]))
    if name == "boolq":
        return mc(r["passage"][:600] + "\n\n" + r["question"].capitalize() + "?", ["yes", "no"], 0 if r["answer"] else 1)
    if name == "medmcqa":
        return mc(r["question"], [r["opa"], r["opb"], r["opc"], r["opd"]], int(r["cop"]))
    if name == "piqa":
        return mc("Goal: " + r["goal"], [r["sol1"], r["sol2"]], int(r["label"]))
    if name == "hellaswag":
        return mc("Which ending fits best?\n" + r["ctx"], r["endings"], int(r["label"]))
    if name == "aqua":
        o = [re.sub(r"^[A-E]\)", "", x) for x in r["options"]]
        return mc(r["question"], o, "ABCDE".index(r["correct"]))
    if name in LABELS:
        k = next((c for c in ("label", "coarse_label", "fine_label") if c in r), None)
        t = r.get("text") or r.get("content") or r.get("sentence") or ""
        return mc("Text: " + t[:500] + "\n\nWhich label fits?", LABELS[name], int(r[k]))
    return None


def items(name, split):
    out, seen = [], set()
    for r in load(name, split):
        try:
            x = row(name, r)
        except (KeyError, ValueError, IndexError, TypeError):
            x = None
        if x and x[0] not in seen:
            seen.add(x[0])
            out.append(x)
    return out


SPLITS = {"arc": ("train", "test"), "arc_easy": ("train", "test"), "openbook": ("train", "test"), "csqa": ("train", "validation"),
          "sciq": ("train", "test"), "qasc": ("train", "validation"), "mmlu": ("test", "validation"), "boolq": ("train", "validation"),
          "ag_news": ("train", "test"), "rotten": ("train", "test"), "trec": ("train", "test"), "aqua": ("train", "test"),
          "medmcqa": ("train", "validation"), "piqa": ("train", "validation"), "hellaswag": ("train", "validation"),
          "emotion": ("train", "test"), "yelp": ("train", "test"), "dbpedia": ("train", "test")}


def correct(reply, answer):
    m = _FIRST.search(reply)
    return m is not None and m.group(1) == answer
