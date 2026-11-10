"""h5x real competing materials: four more families of public datasets in letter/label form (extension of h5).

Same method as scripts/h5_materials.py, whose sampling, screening and manifest code this reuses unchanged: every material
is a seeded uniform sample of one public source at a pinned revision, stratified by label (multiple-choice options are
shuffled instead, so answer letters are uniform), 1,000 rows, screened against the family's held-out suite with
touchstone.overlap.match. Families were chosen by task type and public availability only, before any h5 score existed
and without sight of any h5 run result.

    .venv/bin/python scripts/h5x_materials.py fetch     # needs pyarrow==17.0.0 (the "parquet" extra)
    .venv/bin/python scripts/h5x_materials.py build
    .venv/bin/python scripts/h5x_materials.py table
"""
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h5_materials as M  # noqa: E402

ROOT = M.ROOT
RAW = Path.home() / ".cache" / "touchstone" / "h5x" / "raw"
M.RAW = RAW
M.POOLS = Path.home() / ".cache" / "touchstone" / "h5x" / "pools"
M.OUT = ROOT / "examples" / "h5x"
TEXT_CHARS = 600   # review and comment text is cut at this many characters (h4 cut at 500), so prompts stay short
PRE = 6000         # rows per class drawn uniformly from very large sources before the common sampling step

PQ = "refs/convert/parquet"  # the Hub's own parquet conversion of script-based datasets; commit pinned below
M.REPOS = {
    "sst2": ("stanfordnlp/sst2", "8d51e7e4887a4caaa95b3fbebbf53c0490b58bbb", "unknown on the Hub (Stanford Sentiment Treebank; research use)"),
    "imdb": ("stanfordnlp/imdb", "e6281661ce1c48d982bc483cf8a173c1bbeb5d31", "other (Maas et al. 2011; research use)"),
    "amazon": ("fancyzhx/amazon_polarity", "9d9c45c18f8c3cf1b23a3c27917b60cbf28f3289", "Apache-2.0"),
    "rotten": ("cornell-movie-review-data/rotten_tomatoes", "aa13bc287fa6fcab6daf52f0dfb9994269ffea28", "unknown on the Hub (Pang and Lee 2005)"),
    "tweet_eval": ("cardiffnlp/tweet_eval", "b3a375baf0f409c77e6bc7aa35102b7b3534f8be", "unknown on the Hub (SemEval tasks; research use)"),
    "cr": ("SetFit/CR", "01e427e689e9d3a9097f85eab7a91ce937cf5f98", "untagged on the Hub (Hu and Liu 2004 customer reviews)"),
    "glue": ("nyu-mll/glue", "bcdcba79d07bc864c1c254ccfcedcce55bcc9a8c", "other (MRPC: Microsoft Research licence; QQP: Quora terms)"),
    "paws": ("google-research-datasets/paws", "161ece9501cf0a11f3e48bd356eaa82de46d6a09", "other (free use with attribution to Google)"),
    "medqp": ("curaihealth/medical_questions_pairs", "d91d9da9b2a843fc09ab9d48568d2a93bf58bd0d", "unknown on the Hub"),
    "swag": ("allenai/swag", "dc48148372b3853a9c7bae7bb06c161b46d8364a", "unknown on the Hub (MIT in the authors' repository)"),
    "hellaswag": ("Rowan/hellaswag", "218ec52e09a7e7462a5400043bb9a69a41d06b76", "untagged on the Hub (MIT in the authors' repository)"),
    "cosmos": ("allenai/cosmos_qa", "ed50fe83db62b355759053b1cd5eef344ee371e0", "CC-BY-4.0"),
    "socialiqa": ("allenai/social_i_qa", "537a2ec8ec565adc0b70b70752893e59e024df26", "untagged on the Hub"),
    "piqa": ("ybisk/piqa", "142c51238b3ca2bc61e9a075913871b8b600e8e1", "unknown on the Hub (AFL-3.0 in the authors' repository)"),
    "codah": ("jaredfern/codah", "4b0e0e7f33b3ae8cd8e69bcdfa09af9611d8f3bd", "ODC-BY"),
    "wiki_toxic": ("OxAISH-AL-LLM/wiki_toxic", "872656a156f32e4058307e50e234a44a727a9503", "CC0-1.0"),
    "civil": ("google/civil_comments", "f2970eb3a55777454c94069077cc8d9b5866312d", "CC0-1.0"),
    "davidson": ("tdavidson/hate_speech_offensive", "adc5fb774614827695774f2dbe0ea8122f6a92b4", "unknown on the Hub (MIT in the authors' repository)"),
    "toxicchat": ("lmsys/toxic-chat", "29df8e4dba60e1f4af4b4075c0705c5b313548a8", "CC-BY-NC-4.0 (non-commercial)"),
}
M.FILES = {
    "sst2.train.parquet": ("sst2", "data/train-00000-of-00001.parquet"),
    "imdb.train.parquet": ("imdb", "plain_text/train-00000-of-00001.parquet"),
    **{f"amazon.train.{i}.parquet": ("amazon", f"amazon_polarity/train-0000{i}-of-00004.parquet") for i in range(4)},
    "rotten.train.parquet": ("rotten", "train.parquet"),
    "tweet_sentiment.train.parquet": ("tweet_eval", "sentiment/train-00000-of-00001.parquet"),
    "cr.test.jsonl": ("cr", "test.jsonl"),
    "cr.train.jsonl": ("cr", "train.jsonl"),
    "mrpc.train.parquet": ("glue", "mrpc/train-00000-of-00001.parquet"),
    "mrpc.test.parquet": ("glue", "mrpc/test-00000-of-00001.parquet"),
    "qqp.train.parquet": ("glue", "qqp/train-00000-of-00001.parquet"),
    "paws.train.parquet": ("paws", "labeled_final/train-00000-of-00001.parquet"),
    "paws_silver.train.parquet": ("paws", "unlabeled_final/train-00000-of-00001.parquet"),
    "medqp.train.parquet": ("medqp", "data/train-00000-of-00001.parquet"),
    "swag.train.parquet": ("swag", "regular/train-00000-of-00001.parquet"),
    "hellaswag.train.parquet": ("hellaswag", "data/train-00000-of-00001.parquet"),
    "cosmos.train.parquet": ("cosmos", "default/train/0000.parquet"),
    "socialiqa.train.parquet": ("socialiqa", "default/train/0000.parquet"),
    "piqa.train.parquet": ("piqa", "plain_text/train/0000.parquet"),
    "codah.parquet": ("codah", "codah/train-00000-of-00001.parquet"),
    "wiki_toxic.train.csv": ("wiki_toxic", "train.csv"),
    **{f"civil.train.{i}.parquet": ("civil", f"data/train-0000{i}-of-00002.parquet") for i in range(2)},
    "tweet_offensive.train.parquet": ("tweet_eval", "offensive/train-00000-of-00001.parquet"),
    "tweet_hate.train.parquet": ("tweet_eval", "hate/train-00000-of-00001.parquet"),
    "davidson.train.parquet": ("davidson", "data/train-00000-of-00001.parquet"),
    "toxicchat.test.csv": ("toxicchat", "data/0124/toxic-chat_annotation_test.csv"),
    "toxicchat.train.csv": ("toxicchat", "data/0124/toxic-chat_annotation_train.csv"),
}
M.WHY = {
    "sent.sst2": "SST-2: the standard sentiment training set (movie-review phrases).",
    "sent.imdb": "IMDB: long movie reviews, the other default sentiment set.",
    "sent.amazon": "Amazon polarity: product reviews, the largest and the closest in domain to a product-review suite.",
    "sent.rotten": "Rotten Tomatoes: one-sentence movie reviews, small and clean.",
    "sent.tweets": "TweetEval sentiment (SemEval-2017), neutral tweets dropped: social-media text.",
    "para.qqp": "Quora Question Pairs: the largest duplicate-question set.",
    "para.mrpc_train": "MRPC's own training split: in-distribution for the suite, and small.",
    "para.paws": "PAWS: human-labelled adversarial pairs with high word overlap.",
    "para.paws_silver": "PAWS unlabeled_final: the same kind of pairs with model-assigned (silver) labels, far larger and noisier.",
    "para.medqp": "Medical question pairs written by doctors: a small specialist set.",
    "cs.swag": "SWAG: pick the plausible next event, from video captions.",
    "cs.hellaswag": "HellaSwag: SWAG's harder, adversarially filtered successor.",
    "cs.cosmos": "CosmosQA: commonsense reading of short personal narratives.",
    "cs.socialiqa": "Social IQa: social and emotional commonsense, 3 options.",
    "cs.piqa": "PIQA: physical commonsense, 2 options.",
    "tox.wiki_toxic": "Jigsaw Wikipedia talk-page comments: the standard toxicity training set.",
    "tox.civil": "Civil Comments: news-site comments with crowd toxicity scores (toxic at 0.5 or more).",
    "tox.tweet_offensive": "TweetEval offensive (OLID): offensive tweets.",
    "tox.tweet_hate": "TweetEval hate (HatEval): hate speech against women and immigrants.",
    "tox.davidson": "Davidson et al. hate and offensive tweets (hate or offensive counted as toxic).",
}


def cut(t):
    t = " ".join(str(t).split())
    return t if len(t) <= TEXT_CHARS else t[:TEXT_CHARS].rsplit(" ", 1)[0] + " ..."


def label_row(i, text, labels, k, idp="train"):
    if not str(text or "").strip():
        return None
    stem = "Text: " + cut(text) + "\n\nWhich label fits?"
    p, a = M.mc(stem, labels, k)
    return {"id": f"{idp}-{i}", "stem": cut(text), "prompt": p, "completion": a, "answer": a, "label": labels[k]}


def big(files, label_col, keep, columns):
    """A uniform sample of PRE rows per class from a large parquet source, without loading it all as Python objects."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    t = pa.concat_tables([pq.read_table(RAW / f, columns=columns) for f in files])
    lab = [keep(x) for x in t.column(label_col).to_pylist()]
    rng = random.Random(f"{M.SEED}|pre|{files[0]}")
    idx = []
    for c in sorted({x for x in lab if x is not None}):
        pool = [i for i, x in enumerate(lab) if x == c]
        idx += rng.sample(pool, min(PRE, len(pool)))
    idx.sort()
    return [(i, r, lab[i]) for i, r in zip(idx, t.take(idx).to_pylist())], sum(x is not None for x in lab)


ELIGIBLE = {}  # true eligible row counts for sources that are pre-sampled
SENT = ["negative", "positive"]
PARA = ["no", "yes"]
TOX = ["not toxic", "toxic"]


def _lab(rows):
    return (r for r in rows if r)


def src_sst2():
    return _lab(label_row(r["idx"], r["sentence"], SENT, r["label"]) for r in M._pq("sst2.train.parquet"))


def src_imdb():
    return _lab(label_row(i, r["text"].replace("<br />", " "), SENT, r["label"]) for i, r in enumerate(M._pq("imdb.train.parquet")))


def src_amazon():
    rows, ELIGIBLE["sent.amazon"] = big([f"amazon.train.{i}.parquet" for i in range(4)], "label", lambda x: x, ["label", "title", "content"])
    return _lab(label_row(i, f"{r['title']}. {r['content']}", SENT, k) for i, r, k in rows)


def src_rotten():
    return _lab(label_row(i, r["text"], SENT, r["label"]) for i, r in enumerate(M._pq("rotten.train.parquet")))


def src_tweets():  # 0 negative, 1 neutral, 2 positive; neutral dropped
    return _lab(label_row(i, r["text"], SENT, r["label"] // 2) for i, r in enumerate(M._pq("tweet_sentiment.train.parquet")) if r["label"] != 1)


def suite_sent():
    rows = M._jsonl("cr.test.jsonl") + M._jsonl("cr.train.jsonl")
    for i, r in enumerate(rows):
        x = label_row(i, r["text"], SENT, int(r["label"]), "cr")
        if x:
            x["match"], x["chance"] = "exact", 0.5
            yield x


def pair_row(i, a, b, k, idp="train"):
    if not str(a or "").strip() or not str(b or "").strip():
        return None
    stem = f"Sentence 1: {cut(a)}\nSentence 2: {cut(b)}\n\nDo the two sentences mean the same thing?"
    p, ans = M.mc(stem, PARA, k)
    return {"id": f"{idp}-{i}", "stem": f"{cut(a)} {cut(b)}", "prompt": p, "completion": ans, "answer": ans, "label": PARA[k]}


def src_qqp():
    return _lab(pair_row(r["idx"], r["question1"], r["question2"], r["label"]) for r in M._pq("qqp.train.parquet"))


def src_mrpc_train():
    return _lab(pair_row(r["idx"], r["sentence1"], r["sentence2"], r["label"]) for r in M._pq("mrpc.train.parquet"))


def src_paws():
    return _lab(pair_row(r["id"], r["sentence1"], r["sentence2"], r["label"]) for r in M._pq("paws.train.parquet"))


def src_paws_silver():
    return _lab(pair_row(r["id"], r["sentence1"], r["sentence2"], r["label"]) for r in M._pq("paws_silver.train.parquet"))


def src_medqp():
    return _lab(pair_row(i, r["question_1"], r["question_2"], r["label"]) for i, r in enumerate(M._pq("medqp.train.parquet")))


def suite_para():
    for r in M._pq("mrpc.test.parquet"):
        x = pair_row(r["idx"], r["sentence1"], r["sentence2"], r["label"], "mrpc-test") if r["label"] in (0, 1) else None
        if x:
            x["match"], x["chance"] = "exact", 0.5
            yield x


def mc_row(i, q, opts, key):
    opts = [str(o).strip() for o in opts]
    if not q.strip() or any(not o for o in opts) or len(set(opts)) < len(opts):
        return None
    return {"id": f"train-{i}", "stem": q, "q": q, "opts": opts, "key": int(key)}


def src_swag():
    return _lab(mc_row(i, f"Which ending fits best?\n{r['sent1']} {r['sent2']}", [r[f"ending{j}"] for j in range(4)], r["label"])
                for i, r in enumerate(M._pq("swag.train.parquet")))


def src_hellaswag():
    return _lab(mc_row(r["ind"], f"Which ending fits best?\n{r['ctx']}", r["endings"], r["label"]) for r in M._pq("hellaswag.train.parquet"))


def src_cosmos():
    return _lab(mc_row(r["id"], f"{cut(r['context'])}\n\n{r['question']}", [r[f"answer{j}"] for j in range(4)], r["label"])
                for r in M._pq("cosmos.train.parquet"))


def src_socialiqa():
    return _lab(mc_row(i, f"{r['context']}\n\n{r['question']}", [r["answerA"], r["answerB"], r["answerC"]], int(r["label"]) - 1)
                for i, r in enumerate(M._pq("socialiqa.train.parquet")))


def src_piqa():
    return _lab(mc_row(i, f"Goal: {r['goal']}\n\nWhich way works?", [r["sol1"], r["sol2"]], r["label"])
                for i, r in enumerate(M._pq("piqa.train.parquet")))


def suite_cs():
    rng = random.Random(f"{M.SEED}|cs|suite-options")
    for i, r in enumerate(M._pq("codah.parquet")):
        x = mc_row(i, f"Which ending fits best?\n{r['question_propmt']}", r["candidate_answers"], r["correct_answer_idx"])
        if x:
            p, a = M.shuffled_mc(x["q"], x["opts"], x["key"], rng)
            yield {"id": f"codah-{i}", "stem": r["question_propmt"], "prompt": p, "answer": a, "match": "exact", "label": a, "chance": 0.25}


def _csv(name):
    csv.field_size_limit(1 << 30)
    with open(RAW / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def src_wiki_toxic():
    return _lab(label_row(r["id"], r["comment_text"], TOX, int(r["label"])) for r in _csv("wiki_toxic.train.csv"))


def src_civil():
    rows, ELIGIBLE["tox.civil"] = big(["civil.train.0.parquet", "civil.train.1.parquet"], "toxicity", lambda x: int(x >= 0.5), ["text", "toxicity"])
    return _lab(label_row(i, r["text"], TOX, k) for i, r, k in rows)


def src_tweet_offensive():
    return _lab(label_row(i, r["text"], TOX, r["label"]) for i, r in enumerate(M._pq("tweet_offensive.train.parquet")))


def src_tweet_hate():
    return _lab(label_row(i, r["text"], TOX, r["label"]) for i, r in enumerate(M._pq("tweet_hate.train.parquet")))


def src_davidson():  # class 0 hate speech, 1 offensive language, 2 neither
    return _lab(label_row(i, r["tweet"], TOX, int(r["class"] != 2)) for i, r in enumerate(M._pq("davidson.train.parquet")))


def suite_tox():
    for name in ("toxicchat.test.csv", "toxicchat.train.csv"):
        for r in _csv(name):
            x = label_row(r["conv_id"], r["user_input"], TOX, int(r["toxicity"]), "toxicchat")
            if x:
                x["match"], x["chance"] = "exact", 0.5
                yield x


M.FAMILIES = {
    "sent": {"suite": suite_sent, "suite_source": ("cr", "test + train"), "kind": "binary sentiment as a letter choice", "stratify": True,
             "materials": {"sst2": ("sst2", src_sst2), "imdb": ("imdb", src_imdb), "amazon": ("amazon", src_amazon),
                           "rotten": ("rotten", src_rotten), "tweets": ("tweet_eval", src_tweets)}},
    "para": {"suite": suite_para, "suite_source": ("glue", "mrpc/test"), "kind": "paraphrase / duplicate detection as a letter choice",
             "stratify": True,
             "materials": {"qqp": ("glue", src_qqp), "mrpc_train": ("glue", src_mrpc_train), "paws": ("paws", src_paws),
                           "paws_silver": ("paws", src_paws_silver), "medqp": ("medqp", src_medqp)}},
    "cs": {"suite": suite_cs, "suite_source": ("codah", "codah/train (the full set)"), "kind": "commonsense multiple choice, letter answer",
           "mc": True,
           "materials": {"swag": ("swag", src_swag), "hellaswag": ("hellaswag", src_hellaswag), "cosmos": ("cosmos", src_cosmos),
                         "socialiqa": ("socialiqa", src_socialiqa), "piqa": ("piqa", src_piqa)}},
    "tox": {"suite": suite_tox, "suite_source": ("toxicchat", "0124 test + train"), "kind": "toxicity as a letter choice (spare family)",
            "stratify": True,
            "materials": {"wiki_toxic": ("wiki_toxic", src_wiki_toxic), "civil": ("civil", src_civil),
                          "tweet_offensive": ("tweet_eval", src_tweet_offensive), "tweet_hate": ("tweet_eval", src_tweet_hate),
                          "davidson": ("davidson", src_davidson)}},
}

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "fetch":
        M.fetch()
        import json
        (M.POOLS / "eligible_override.json").write_text(json.dumps(ELIGIBLE))
    elif cmd == "build":
        M.build()
    else:
        M.table()
