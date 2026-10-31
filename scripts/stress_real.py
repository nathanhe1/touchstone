"""Stress test: real, unmodified public datasets as clean controls for the label checks.

A false flag blocks a price, so the false-flag rate outside our own generators matters. Nothing is planted.
Each source is drawn 4 times without overlap; raw signals are stored, so `flag_margins.py` can move thresholds
offline. Sources marked `unseen` were never used to set any threshold. Real public data has a small true
error rate, about 1-2% on GSM8K: well under the 20% truth line, so any flag here counts as false.

    python scripts/stress_real.py            # resumable; writes out/stress_real.json
"""
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import coverage, screen  # noqa: E402
from touchstone.data import Example  # noqa: E402

D = Path.home() / ".cache" / "touchstone"
C = D / "coverage"
F = ROOT / "out" / "stress_real.json"
DRAWS, PER = 4, 120


def ex(p, c, **m):
    return Example([{"role": "user", "content": p}], c, m)


def js(n):
    return json.loads((C / f"{n}.json").read_text())


def jl(f):
    return [json.loads(x) for x in Path(f).read_text().splitlines() if x.strip()]


def mc(q, labels, texts, key):
    return ex(q + "\n" + "\n".join(f"{a}) {t}" for a, t in zip(labels, texts)), key)


def sources():
    S = {}
    S["gsm8k_test_answer"] = [ex(r["question"], r["answer"].split("####")[-1].strip()) for r in jl(D / "public/gsm8k_test.jsonl")]
    S["gsm8k_test_worked"] = [ex(r["question"], r["answer"]) for r in jl(D / "public/gsm8k_test.jsonl")]
    S["gsm8k_train_worked"] = [ex(r["question"], r["answer"]) for r in jl(D / "gsm8k_train.jsonl")][:1000]
    sv = json.loads((D / "public/svamp.json").read_text())
    S["svamp"] = [ex(r["Body"].strip().rstrip(".") + ". " + r["Question"], str(r["Answer"])) for r in sv]
    A = []
    for p in ET.parse(D / "public/asdiv.xml").getroot().iter("Problem"):
        a = (p.findtext("Answer") or "").split("(")[0].strip()
        if re.fullmatch(r"-?\d+(\.\d+)?", a):
            A.append(ex(p.findtext("Body").strip() + " " + p.findtext("Question").strip(), a))
    S["asdiv"] = A
    S["arc"] = [mc(r["question"], r["choices"]["label"], r["choices"]["text"], r["answerKey"]) for r in js("arc")
                if r["answerKey"] in "ABCD" and r["choices"]["label"][0] == "A"]
    S["unseen_openbookqa"] = [mc(r["question_stem"], r["choices"]["label"], r["choices"]["text"], r["answerKey"]) for r in js("openbook")]
    S["unseen_csqa"] = [mc(r["question"], r["choices"]["label"], r["choices"]["text"], r["answerKey"]) for r in js("csqa") if r.get("answerKey")]
    S["dolly"] = [ex(r["instruction"] + ("\n\n" + r["context"] if r.get("context") else ""), r["response"]) for r in js("dolly")]
    S["unseen_no_robots"] = [ex(r["messages"][0]["content"] if r["messages"][0]["role"] == "user" else r["prompt"], r["messages"][-1]["content"])
                             for r in js("no_robots") if r["messages"][-1]["role"] == "assistant"]
    S["mbpp"] = [ex(r["text"], r["code"].replace("\r", ""), test_list=r["test_list"]) for r in jl(C / "mbpp.jsonl")]
    S["humaneval"] = [ex(r["prompt"], r["canonical_solution"], code_prefix=r["prompt"], test=r["test"], entry_point=r["entry_point"])
                      for r in jl(C / "humaneval.jsonl")]
    return S


def main():
    res = json.loads(F.read_text()) if F.exists() else {}
    for name, rows in sources().items():
        n = min(PER, len(rows) // DRAWS)
        for d in range(DRAWS):
            key = f"{name}#{d}"
            if key in res or n < 20:
                continue
            sub = rows[d * n:(d + 1) * n]
            t = time.time()
            dtype = coverage.detect_type(sub)
            a = screen.arithmetic_consistency([e.completion for e in sub])
            r = coverage.label_checks(dtype, sub, a)
            r = {k: v for k, v in r.items() if k != "rows"}
            res[key] = dict(r, dtype=dtype, n=len(sub), arithmetic=a, lang=coverage.language([e.last_user for e in sub[:50]]),
                            seconds=round(time.time() - t))
            F.write_text(json.dumps(res, indent=1))
            print(key, dtype, r["status"], "FLAG" if r["noisy"] else "ok",
                  {k: r.get(k) for k in ("disagree", "fit", "rate", "confident") if k in r}, res[key]["seconds"], "s", flush=True)


if __name__ == "__main__":
    main()
