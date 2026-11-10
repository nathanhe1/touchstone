"""h5 real competing materials: fetch public sources at pinned revisions, sample each to the same size, screen, manifest.

Two steps, because they need different packages:

    # 1. fetch + sample candidate pools (stdlib + pyarrow==17.0.0; nothing fetched is executed)
    python scripts/h5_materials.py fetch
    # 2. screen against each family's held-out suite, balance, measure, write examples/h5/ and the manifest (engine venv)
    .venv/bin/python scripts/h5_materials.py build

Every material is a uniform random sample (seed SEED) of the eligible rows of one public source, stratified by label for
classification. Rows that match the family's held-out suite (touchstone.overlap.match: exact, near-duplicate or
paraphrase), duplicate another row of the same material, or are empty are dropped and the next candidate in the
shuffled order takes their place. What was dropped is counted in the manifest.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = Path.home() / ".cache" / "touchstone" / "h5" / "raw"
POOLS = Path.home() / ".cache" / "touchstone" / "h5" / "pools"
OUT = ROOT / "examples" / "h5"
SEED = 20261110
N = 1000            # rows per material, identical for every material
CANDIDATES = 3000   # shuffled candidates kept per material before screening
LETTERS = "ABCDEFGHIJKLMNOP"

# repo, revision, licence. Revisions are the Hugging Face commit each file was downloaded at.
REPOS = {
    "gsm8k": ("openai/gsm8k", "740312add88f781978c0658806c59bc2815b9866", "MIT"),
    "gsm8k_platinum": ("madrylab/gsm8k-platinum", "e762492455a1cf7967de89f05b6bef72fc713b66", "MIT"),
    "metamathqa": ("meta-math/MetaMathQA", "aa4f34d3d2d3231299b5b03d9b3e5a20da45aa18", "MIT"),
    "omi2": ("nvidia/OpenMathInstruct-2", "469216e3f46f4dacf476b382e192485ea51a143e", "CC-BY-4.0"),
    "orca_math": ("microsoft/orca-math-word-problems-200k", "29255d1770cc4eac66e5e7fa378cba542c026350", "MIT"),
    "numina_cot": ("AI-MO/NuminaMath-CoT", "9d8d210c9f6a36c8f3cd84045668c9b7800ef517", "Apache-2.0"),
    "snli": ("stanfordnlp/snli", "cdb5c3d5eed6ead6e5a341c8e56e669bb666725b", "CC-BY-SA-4.0"),
    "mnli": ("nyu-mll/multi_nli", "da70db2af9d09693783c3320c4249840212ee221", "mixed per genre: CC-BY-3.0, CC-BY-SA-3.0, MIT, other (OANC)"),
    "wanli": ("alisawuffles/WANLI", "61c95318fd71c55b6ba355d76253254615f387ec", "CC-BY-4.0"),
    "anli": ("facebook/anli", "8e4813d81f46d313dac7892e1c28076917cfcdf9", "CC-BY-NC-4.0 (non-commercial)"),
    "fever_nli": ("pietrolesci/nli_fever", "1eddac63112eee1fdf1966e0bca27a5ff248c772",
                  "untagged on the Hub; built from FEVER (CC-BY-SA-3.0, Wikipedia-derived)"),
    "arc": ("allenai/ai2_arc", "210d026faf9955653af8916fad021475a3f00453", "CC-BY-SA-4.0"),
    "sciq": ("allenai/sciq", "2c94ad3e1aafab77146f384e23536f97a4849815", "CC-BY-NC-3.0 (non-commercial)"),
    "obqa": ("allenai/openbookqa", "388097ea7776314e93a529163e0fea805b8a6454", "Apache-2.0 per the AllenAI release; 'unknown' on the Hub card"),
    "qasc": ("allenai/qasc", "a34ba204eb9a33b919c10cc08f4f1c8dae5ec070", "CC-BY-4.0"),
    "mmlu": ("cais/mmlu", "c30699e8356da336a370243923dbaf21066bb9fe", "MIT"),
    "kk": ("K-and-K/knights-and-knaves", "2f68547989981b1af37cb3dde5fdefa847aa8619", "CC-BY-NC-SA-4.0 (non-commercial)"),
    "synlogic": ("MiniMaxAI/SynLogic", "bb4297b82b9c28ef39249f48386cefd5e856618a", "MIT"),
}

FILES = {  # local name: (repo key, path in repo)
    "gsm8k.train.parquet": ("gsm8k", "main/train-00000-of-00001.parquet"),
    "gsm8k_platinum.test.parquet": ("gsm8k_platinum", "main/test-00000-of-00001.parquet"),
    "metamathqa.json": ("metamathqa", "MetaMathQA-395K.json"),
    **{f"omi2_1M.{i}.parquet": ("omi2", f"data/train_1M-0000{i}-of-00003.parquet") for i in range(3)},
    "orca_math.train.parquet": ("orca_math", "data/train-00000-of-00001.parquet"),
    **{f"numina_cot.{i}.parquet": ("numina_cot", f"data/train-0000{i}-of-00005.parquet") for i in range(5)},
    "snli.train.parquet": ("snli", "plain_text/train-00000-of-00001.parquet"),
    "mnli.train.parquet": ("mnli", "data/train-00000-of-00001.parquet"),
    "wanli.train.jsonl": ("wanli", "train.jsonl"),
    **{f"anli.{s}.parquet": ("anli", f"plain_text/{s}-00000-of-00001.parquet")
       for s in ("train_r1", "train_r2", "train_r3", "test_r1", "test_r2", "test_r3")},
    "fever_nli.train.parquet": ("fever_nli", "data/train-00000-of-00001.parquet"),
    "arc.ARC-Challenge.test.parquet": ("arc", "ARC-Challenge/test-00000-of-00001.parquet"),
    "arc.ARC-Challenge.train.parquet": ("arc", "ARC-Challenge/train-00000-of-00001.parquet"),
    "arc.ARC-Easy.train.parquet": ("arc", "ARC-Easy/train-00000-of-00001.parquet"),
    "sciq.train.parquet": ("sciq", "data/train-00000-of-00001.parquet"),
    "obqa.train.parquet": ("obqa", "main/train-00000-of-00001.parquet"),
    "qasc.train.parquet": ("qasc", "data/train-00000-of-00001.parquet"),
    "mmlu_aux.train.parquet": ("mmlu", "auxiliary_train/train-00000-of-00001.parquet"),
}

# Why a buyer would plausibly put each material next to the others.
WHY = {
    "gsm.gsm8k_train": "The benchmark's own human-written training split: the default a buyer already has for free.",
    "gsm.metamathqa_gsm": "MetaMathQA's GSM8K-derived part (rephrased, answer-augmented, backward questions); widely used to lift GSM8K scores.",
    "gsm.omi2_gsm": "NVIDIA's OpenMathInstruct-2 1M release, grade-school part: new problems and solutions synthesised by Llama-3.1-405B.",
    "gsm.orca_math": "Microsoft's Orca-Math 200k: GPT-4-Turbo solutions to synthetic grade-school word problems, sold as a GSM8K booster.",
    "gsm.numina_cot": "NuminaMath-CoT as delivered: a broad math set (K-12 to olympiad) a buyer might pick to improve math in general.",
    "nli.snli": "The original large NLI set (image captions); cheap and large.",
    "nli.mnli": "MultiNLI: multi-genre, the standard NLI training set.",
    "nli.wanli": "WANLI: GPT-3 generated and human-filtered, published as transferring better than MultiNLI to hard sets.",
    "nli.anli_train": "ANLI's own adversarial training rounds, in-distribution for the suite.",
    "nli.fever_nli": "FEVER claims paired with Wikipedia evidence, a fact-verification set re-cast as NLI.",
    "sci.arc_easy_train": "ARC-Easy training questions: same exam source as the suite, easier items.",
    "sci.arc_challenge_train": "ARC-Challenge's own training split: in-distribution for the suite, and small.",
    "sci.sciq": "SciQ: crowd-written science exam questions with supporting passages.",
    "sci.obqa": "OpenBookQA: elementary science questions that need one core fact plus common knowledge.",
    "sci.qasc": "QASC: grade-school science questions built by composing two facts, 8 options.",
    "sci.mmlu_aux": "MMLU's auxiliary training set: a broad multiple-choice mix (ARC, OBQA, RACE, MCTest and more).",
}


# ----------------------------------------------------------------------------------------------------------- fetch

def download():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, (key, path) in FILES.items():
        f = RAW / name
        if f.exists() and f.stat().st_size:
            continue
        repo, rev, _ = REPOS[key]
        url = f"https://huggingface.co/datasets/{repo}/resolve/{rev}/{path}"
        for attempt in range(4):
            try:
                urllib.request.urlretrieve(url, f.with_suffix(".part"))
                f.with_suffix(".part").rename(f)
                print("downloaded", name, f.stat().st_size, flush=True)
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(5 * (attempt + 1))


def _pq(*names, columns=None):
    import pyarrow.parquet as pq
    out = []
    for n in names:
        out += pq.read_table(RAW / n, columns=columns).to_pylist()
    return out


def _jsonl(name):
    return [json.loads(x) for x in (RAW / name).read_text().splitlines() if x.strip()]


_CALC = re.compile(r"<<[^>]*>>")
_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def last_number(s):
    m = _NUM.findall(s or "")
    return m[-1].replace(",", "").rstrip(".") if m else None


def boxed(s):
    """Content of the last \\boxed{...}, braces balanced."""
    i = (s or "").rfind("\\boxed{")
    if i < 0:
        return None
    j, depth = i + 7, 1
    while j < len(s) and depth:
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        j += 1
    return s[i + 7:j - 1].strip() if depth == 0 else None


def mc(q, opts, key):
    text = q.strip() + "\n" + "\n".join(f"{LETTERS[i]}) {str(o).strip()}" for i, o in enumerate(opts))
    return text + "\nReply with the letter only.", LETTERS[key]


NLI_LABELS = ["entailment", "neutral", "contradiction"]


def nli_prompt(premise, hypothesis, label):
    stem = f"Premise: {premise.strip()}\nHypothesis: {hypothesis.strip()}\n\nWhat is the relation of the hypothesis to the premise?"
    p, a = mc(stem, NLI_LABELS, label)
    return p, a, stem


def shuffled_mc(q, opts, key, rng):
    order = list(range(len(opts)))
    rng.shuffle(order)
    p, a = mc(q, [opts[i] for i in order], order.index(key))
    return p, a


# Each source yields dict rows: id, prompt, completion, answer, label (class for balance), stem (text compared in the
# overlap screen), extra.

def src_gsm8k_train():
    for i, r in enumerate(_pq("gsm8k.train.parquet")):
        sol, ans = r["answer"].split("####")
        yield {"id": f"train-{i}", "stem": r["question"], "prompt": r["question"],
               "completion": _CALC.sub("", sol).strip() + "\n#### " + ans.strip(), "answer": ans.strip().replace(",", "")}


def src_metamathqa_gsm():
    for i, r in enumerate(json.loads((RAW / "metamathqa.json").read_text())):
        if r["type"].startswith("GSM_"):
            m = re.search(r"The answer is:?\s*(.+?)\s*$", r["response"])
            yield {"id": f"row-{i}", "stem": r["query"], "prompt": r["query"], "completion": r["response"],
                   "answer": m.group(1).strip() if m else None, "extra": {"type": r["type"]}}


def src_omi2_gsm():
    i = 0
    for n in ("omi2_1M.0.parquet", "omi2_1M.1.parquet", "omi2_1M.2.parquet"):
        for r in _pq(n):
            if r["problem_source"] in ("augmented_gsm8k", "gsm8k"):
                yield {"id": f"train_1M-{i}", "stem": r["problem"], "prompt": r["problem"], "completion": r["generated_solution"],
                       "answer": str(r["expected_answer"]), "extra": {"problem_source": r["problem_source"]}}
            i += 1


def src_orca_math():
    for i, r in enumerate(_pq("orca_math.train.parquet")):
        yield {"id": f"train-{i}", "stem": r["question"], "prompt": r["question"], "completion": r["answer"],
               "answer": last_number(r["answer"]), "extra": {"answer_from": "last number in the solution"}}


def src_numina_cot():
    i = 0
    for k in range(5):
        for r in _pq(f"numina_cot.{k}.parquet", columns=["source", "problem", "solution"]):
            yield {"id": f"train-{i}", "stem": r["problem"], "prompt": r["problem"], "completion": r["solution"],
                   "answer": boxed(r["solution"]), "extra": {"source": r["source"]}}
            i += 1


def suite_gsm():
    for i, r in enumerate(_pq("gsm8k_platinum.test.parquet")):
        ans = r["answer"].split("####")[-1].strip().replace(",", "")
        yield {"id": f"test-{i}", "stem": r["question"], "prompt": r["question"], "answer": ans, "match": "numeric",
               "extra": {"cleaning_status": r["cleaning_status"]}}


def _nli(rows, idp, prem="premise", hyp="hypothesis", lab="label"):
    for i, r in enumerate(rows):
        label = r[lab] if isinstance(r[lab], int) else (NLI_LABELS.index(r[lab]) if r[lab] in NLI_LABELS else -1)
        if label not in (0, 1, 2):
            continue
        p, a, stem = nli_prompt(r[prem], r[hyp], label)
        yield {"id": f"{idp}-{r.get('uid', r.get('pairID', i))}", "stem": stem, "prompt": p, "completion": a, "answer": a,
               "label": NLI_LABELS[label], "extra": {"premise": r[prem]}}


def src_snli():
    return _nli(_pq("snli.train.parquet"), "train")


def src_mnli():
    return _nli(_pq("mnli.train.parquet", columns=["pairID", "premise", "hypothesis", "genre", "label"]), "train")


def src_wanli():
    return _nli(_jsonl("wanli.train.jsonl"), "train", lab="gold")


def src_anli_train():
    rows = []
    for s in ("train_r1", "train_r2", "train_r3"):
        rows += _pq(f"anli.{s}.parquet", columns=["uid", "premise", "hypothesis", "label"])
    return _nli(rows, "train")


def src_fever_nli():
    # The Hub copy names the FEVER claim "premise" and the Wikipedia evidence "hypothesis". In NLI terms the evidence is
    # the premise and the claim the hypothesis, so they are swapped back here.
    return _nli(_pq("fever_nli.train.parquet", columns=["cid", "premise", "hypothesis", "label"]), "train",
                prem="hypothesis", hyp="premise")


def suite_nli():
    for s in ("test_r1", "test_r2", "test_r3"):
        for r in _nli(_pq(f"anli.{s}.parquet", columns=["uid", "premise", "hypothesis", "label"]), s):
            r["match"] = "exact"
            yield r


def _arc_like(rows, idp, qkey="question"):
    for r in rows:
        labels, texts = list(r["choices"]["label"]), list(r["choices"]["text"])
        if r["answerKey"] not in labels:
            continue
        yield {"id": f"{idp}-{r['id']}", "stem": r[qkey], "q": r[qkey], "opts": texts, "key": labels.index(r["answerKey"])}


def src_arc_easy_train():
    return _arc_like(_pq("arc.ARC-Easy.train.parquet"), "ARC-Easy-train")


def src_arc_challenge_train():
    return _arc_like(_pq("arc.ARC-Challenge.train.parquet"), "ARC-Challenge-train")


def src_obqa():
    return _arc_like(_pq("obqa.train.parquet"), "train", qkey="question_stem")


def src_qasc():
    return _arc_like(_pq("qasc.train.parquet"), "train")


def src_sciq():
    for i, r in enumerate(_pq("sciq.train.parquet")):
        yield {"id": f"train-{i}", "stem": r["question"], "q": r["question"],
               "opts": [r["correct_answer"], r["distractor1"], r["distractor2"], r["distractor3"]], "key": 0}


def src_mmlu_aux():
    for i, r in enumerate(_pq("mmlu_aux.train.parquet")):
        t = r["train"]
        yield {"id": f"auxiliary_train-{i}", "stem": t["question"], "q": t["question"], "opts": list(t["choices"]), "key": int(t["answer"])}


def suite_sci():
    for r in _arc_like(_pq("arc.ARC-Challenge.test.parquet"), "ARC-Challenge-test"):
        p, a = mc(r["q"], r["opts"], r["key"])  # the suite keeps the published option order
        yield {"id": r["id"], "stem": r["stem"], "prompt": p, "answer": a, "match": "exact", "label": a, "chance": 1 / len(r["opts"])}


FAMILIES = {
    "gsm": {"suite": suite_gsm, "suite_source": ("gsm8k_platinum", "test"), "kind": "worked solutions, numeric answer",
            "materials": {"gsm8k_train": ("gsm8k", src_gsm8k_train), "metamathqa_gsm": ("metamathqa", src_metamathqa_gsm),
                          "omi2_gsm": ("omi2", src_omi2_gsm), "orca_math": ("orca_math", src_orca_math),
                          "numina_cot": ("numina_cot", src_numina_cot)}},
    "nli": {"suite": suite_nli, "suite_source": ("anli", "test_r1+test_r2+test_r3"), "kind": "3-way NLI as a letter choice",
            "stratify": True,
            "materials": {"snli": ("snli", src_snli), "mnli": ("mnli", src_mnli), "wanli": ("wanli", src_wanli),
                          "anli_train": ("anli", src_anli_train), "fever_nli": ("fever_nli", src_fever_nli)}},
    "sci": {"suite": suite_sci, "suite_source": ("arc", "ARC-Challenge/test"), "kind": "science multiple choice, letter answer",
            "mc": True,
            "materials": {"arc_easy_train": ("arc", src_arc_easy_train), "arc_challenge_train": ("arc", src_arc_challenge_train),
                          "sciq": ("sciq", src_sciq), "obqa": ("obqa", src_obqa), "qasc": ("qasc", src_qasc),
                          "mmlu_aux": ("mmlu", src_mmlu_aux)}},
}


def candidates(rows, stratify, rng):
    """Uniform sample without replacement, in a fixed random order. Stratified: equal shares per label, interleaved."""
    if not stratify:
        idx = list(range(len(rows)))
        rng.shuffle(idx)
        return [rows[i] for i in idx[:CANDIDATES]], len(rows)
    by = {}
    for r in rows:
        by.setdefault(r["label"], []).append(r)
    for k in sorted(by):
        rng.shuffle(by[k])
    per = CANDIDATES // len(by)
    out = []
    for j in range(per):
        for k in sorted(by):
            if j < len(by[k]):
                out.append(by[k][j])
    return out, len(rows)


def fetch():
    download()
    POOLS.mkdir(parents=True, exist_ok=True)
    for fam, F in FAMILIES.items():
        suite = list(F["suite"]())
        (POOLS / f"{fam}.suite.json").write_text(json.dumps(suite))
        print(fam, "suite", len(suite), flush=True)
        for mat, (_, fn) in F["materials"].items():
            rng = random.Random(f"{SEED}|{fam}|{mat}")
            rows = list(fn())
            if F.get("mc"):  # options shuffled with a fixed per-material seed, so the answer letter is uniform
                for r in rows:
                    r["prompt"], r["answer"] = shuffled_mc(r.pop("q"), r.pop("opts"), r.pop("key"), rng)
                    r["completion"], r["label"] = r["answer"], r["answer"]
            cand, total = candidates(rows, F.get("stratify"), rng)
            (POOLS / f"{fam}.{mat}.json").write_text(json.dumps({"eligible": total, "rows": cand}))
            print(fam, mat, "eligible", total, "candidates", len(cand), flush=True)


# ----------------------------------------------------------------------------------------------------------- build

def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def build():
    sys.path.insert(0, str(ROOT))
    from transformers import AutoTokenizer
    from touchstone import overlap
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"seed": SEED, "rows_per_material": N, "built_by": "scripts/h5_materials.py", "tokenizer": "Qwen/Qwen2.5-1.5B-Instruct",
                "overlap_screen": "touchstone.overlap.match (exact; character 5-gram Jaccard >= 0.6 with the same numbers; "
                                  "MiniLM cosine >= 0.85 with the same numbers, or >= 0.92 for text without numbers) of the "
                                  "material's question text against every suite question; gated_suite_match reported beside it",
                "families": {}}
    for fam, F in FAMILIES.items():
        d = OUT / fam
        d.mkdir(parents=True, exist_ok=True)
        suite = json.loads((POOLS / f"{fam}.suite.json").read_text())
        rng = random.Random(f"{SEED}|{fam}|suite")
        if F.get("stratify") or F.get("mc"):  # interleave classes so any prefix of the suite stays balanced
            by = {}
            for r in suite:
                by.setdefault(r["label"], []).append(r)
            for k in sorted(by):
                rng.shuffle(by[k])
            suite = []
            while any(by.values()):
                for k in sorted(by):
                    if by[k]:
                        suite.append(by[k].pop())
        else:
            rng.shuffle(suite)
        suite_stems = [r["stem"] for r in suite]
        suite_rows = [{"id": r["id"], "prompt": r["prompt"], "answer": r["answer"], "match": r["match"],
                       **({"chance": r["chance"]} if "chance" in r else {}), **({"label": r["label"]} if "label" in r else {})}
                      for r in suite]
        sp = d / "suite.jsonl"
        sp.write_text("".join(json.dumps(r) + "\n" for r in suite_rows))
        skey, ssplit = F["suite_source"]
        fm = {"kind": F["kind"], "suite": {"file": str(sp.relative_to(ROOT)), "sha256": sha256(sp), "rows": len(suite_rows),
                                            "source": REPOS[skey][0], "split": ssplit, "revision": REPOS[skey][1],
                                            "licence": REPOS[skey][2],
                                            "class_balance": _balance([r.get("label") for r in suite]) if "label" in suite[0] else None,
                                            "note": "rows in a fixed random order (seeded); classes interleaved so any prefix is balanced"},
              "materials": {}}
        for mat, (key, _) in F["materials"].items():
            pool = json.loads((POOLS / f"{fam}.{mat}.json").read_text())
            cand = pool["rows"]
            # screen every candidate once against the suite
            hit = overlap.match([r["stem"] for r in cand], suite_stems)
            bad = set(hit["matched_idx"])
            gated = overlap.gated_suite_match([(r["stem"], r["answer"]) for r in suite], [(r["stem"], r.get("answer")) for r in cand]) \
                if fam == "gsm" else None
            chosen, seen, dropped = [], set(), Counter()
            need = {}
            if F.get("stratify"):
                labels = sorted({r["label"] for r in cand})
                need = {l: N // len(labels) + (1 if i < N % len(labels) else 0) for i, l in enumerate(labels)}
            first_n = 0  # contamination rate on the first N candidates, the rate a buyer's raw sample would carry
            for i, r in enumerate(cand):
                if len(chosen) >= N:
                    break
                if i < N and i in bad:
                    first_n += 1
                if not (r.get("prompt") or "").strip() or not (r.get("completion") or "").strip():
                    dropped["empty"] += 1
                    continue
                if i in bad:
                    dropped["suite_overlap"] += 1
                    continue
                k = overlap.norm(r["stem"])
                if k in seen:
                    dropped["duplicate"] += 1
                    continue
                if need and need.get(r["label"], 0) <= 0:
                    continue
                if need:
                    need[r["label"]] -= 1
                seen.add(k)
                chosen.append(r)
            assert len(chosen) == N, (fam, mat, len(chosen))
            rows = [{"id": r["id"], "prompt": r["prompt"], "completion": r["completion"], "answer": r.get("answer"),
                     **({"label": r["label"]} if "label" in r else {}), **({"meta": r["extra"]} if r.get("extra") and fam == "gsm" else {})}
                    for r in chosen]
            mp = d / f"{mat}.jsonl"
            mp.write_text("".join(json.dumps(r) + "\n" for r in rows))
            plen = [len(tok(r["prompt"]).input_ids) for r in rows]
            clen = [len(tok(r["completion"]).input_ids) for r in rows]
            repo, rev, lic = REPOS[key]
            fm["materials"][mat] = {
                "file": str(mp.relative_to(ROOT)), "sha256": sha256(mp), "rows": N, "source": repo, "revision": rev, "licence": lic,
                "eligible_rows": pool["eligible"], "sampling": f"uniform without replacement, random.Random('{SEED}|{fam}|{mat}')"
                + (", stratified by label" if F.get("stratify") else "") + (", options shuffled per row with the same generator" if F.get("mc") else ""),
                "screen": {"suite_overlap_in_first_1000_candidates": first_n, "suite_overlap_rate_raw": round(first_n / N, 4),
                           "suite_overlap_kinds_all_candidates": {k: round(hit[k] * len(cand)) for k in ("exact", "near", "paraphrase")},
                           "examples": hit["examples"][:2], "gated_suite_match_rate": gated["rate"] if gated else None,
                           "dropped": dict(dropped)},
                "class_balance": _balance([r.get("label") for r in rows]) if "label" in rows[0] else None,
                "tokens_qwen2.5": {"prompt_p50": pct(plen, .5), "prompt_p95": pct(plen, .95),
                                   "completion_p50": pct(clen, .5), "completion_p95": pct(clen, .95), "completion_max": max(clen),
                                   "share_prompt_plus_completion_over_256": round(sum(a + b > 256 for a, b in zip(plen, clen)) / N, 3),
                                   "share_prompt_plus_completion_over_512": round(sum(a + b > 512 for a, b in zip(plen, clen)) / N, 3)},
                "answer_extracted": round(sum(r.get("answer") not in (None, "") for r in rows) / N, 3),
                "why_compare": WHY[f"{fam}.{mat}"]}
            print(fam, mat, json.dumps(fm["materials"][mat]["screen"]["dropped"]), "raw overlap", first_n, flush=True)
        manifest["families"][fam] = fm
    mf = OUT / "manifest.json"
    mf.write_text(json.dumps(manifest, indent=1) + "\n")
    allh = hashlib.sha256()
    for p in sorted(OUT.rglob("*.jsonl")):
        allh.update(f"{p.relative_to(OUT)} {sha256(p)}\n".encode())
    (OUT / "h5_materials.sha256").write_text(
        "".join(f"{sha256(p)}  {p.relative_to(ROOT)}\n" for p in sorted(OUT.rglob("*.jsonl"))) + f"{allh.hexdigest()}  ALL\n")
    print("ALL", allh.hexdigest())


def _balance(labels):
    c = Counter(labels)
    n = sum(c.values())
    return {"majority_share": round(max(c.values()) / n, 3), "classes": len(c), "counts": dict(sorted(c.items()))}


if __name__ == "__main__":
    {"fetch": fetch, "build": build}[sys.argv[1]]()
