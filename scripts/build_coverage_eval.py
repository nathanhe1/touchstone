"""Build examples/coverage_eval/: a NEW, SMALL eval of label checks on data types beyond word problems.

Not part of test v3 and not in its headline. Real public rows (ARC, MBPP, HumanEval, Dolly, SODA, Glaive
function calling, MGSM Spanish/German) with planted wrong labels. Each source is split in half by row
order: `dev` sets thresholds, `eval` is reported, and the rows never overlap. Truth: noisy_labels when
20%+ of labels are wrong (0% and 10% are negatives). Hash in out/coverage_eval.sha256.

    python scripts/build_coverage_eval.py
"""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone.coverage import tool_call  # noqa: E402

D = Path.home() / ".cache" / "touchstone" / "coverage"
OUT = ROOT / "examples" / "coverage_eval"
SEED = 4100


def js(n):
    return json.loads((D / f"{n}.json").read_text())


def jl(n):
    return [json.loads(x) for x in (D / n).read_text().splitlines() if x.strip()]


def mcq():
    rows = []
    for r in js("arc"):
        L = r["choices"]["label"]
        if r["answerKey"] not in L or L[0] != "A":
            continue
        q = r["question"] + "\n" + "\n".join(f"{a}) {t}" for a, t in zip(L, r["choices"]["text"]))
        rows.append({"prompt": q, "completion": r["answerKey"], "_L": L})
    return rows


def wrong_mcq(r, rng, pool):
    return dict(r, completion=rng.choice([x for x in r["_L"] if x != r["completion"]]))


def mbpp():
    return [{"prompt": r["text"], "completion": r["code"].replace("\r", ""), "test_list": r["test_list"]} for r in jl("mbpp.jsonl")[:400]]


def human():
    return [{"prompt": r["prompt"], "completion": r["canonical_solution"], "code_prefix": r["prompt"], "test": r["test"],
             "entry_point": r["entry_point"]} for r in jl("humaneval.jsonl")]


MUT = [(r" \+ ", " - "), (r" - ", " + "), (r" < ", " >= "), (r" > ", " <= "), (r" == ", " != "), (r"return True", "return False"),
       (r"return False", "return True"), (r"\* ", "+ "), (r"\b0\b", "1"), (r"\b1\b", "2")]


def wrong_code(r, rng, pool):
    c = r["completion"]
    opts = [(a, b) for a, b in MUT if re.search(a, c)]
    if opts:
        a, b = rng.choice(opts)
        hits = list(re.finditer(a, c))
        m = rng.choice(hits)
        return dict(r, completion=c[:m.start()] + b + c[m.end():])
    return dict(r, completion=rng.choice(pool)["completion"])


def dolly():
    out = []
    for r in js("dolly"):
        p = r["instruction"] + ("\n\n" + r["context"] if r.get("context") else "")
        out.append({"prompt": p, "completion": r["response"]})
    return out


def wrong_swap(r, rng, pool):
    o = rng.choice(pool)
    while o["completion"] == r["completion"]:
        o = rng.choice(pool)
    return dict(r, completion=o["completion"])


def soda():
    out = []
    for r in js("soda"):
        d = [x for x in r["dialogue"] if x.strip()]
        if len(d) < 4:
            continue
        d = d[:6 if len(d) >= 6 else 4]
        msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": x} for i, x in enumerate(d)]
        out.append({"messages": msgs, "completion": msgs[-1]["content"]})
    return out


def wrong_chat(r, rng, pool):
    o = wrong_swap(r, rng, pool)
    return dict(r, completion=o["completion"], messages=r["messages"][:-1] + [{"role": "assistant", "content": o["completion"]}])


def glaive():
    out = []
    for r in js("glaive"):
        chat = r["chat"]
        m = re.search(r"USER:\s*(.*?)\s*ASSISTANT:\s*(<functioncall>.*?)(?:<\|endoftext\|>|$)", chat, re.S)
        if not m or tool_call(m.group(2))[0] is None:
            continue
        out.append({"messages": [{"role": "system", "content": r["system"].replace("SYSTEM: ", "")},
                                 {"role": "user", "content": m.group(1)}, {"role": "assistant", "content": m.group(2).strip()}],
                    "completion": m.group(2).strip()})
    return out


def wrong_tool(r, rng, pool):
    call = tool_call(r["completion"])[0]
    k = rng.randrange(3)
    if k == 0:
        c = "<functioncall> " + json.dumps(dict(call, name=call["name"] + "_v2"))
    elif k == 1:
        args = call.get("arguments")
        if isinstance(args, str):
            args = json.loads(args)
        c = "<functioncall> " + json.dumps(dict(call, arguments=dict(args, unexpected_field=1)))
    else:
        c = "<functioncall> " + json.dumps(call)[:-6]
    return dict(r, completion=c, messages=r["messages"][:-1] + [{"role": "assistant", "content": c}])


def mgsm(lang):
    return [{"prompt": r["question"], "completion": str(r["answer_number"])} for r in js(f"mgsm_{lang}")]


def wrong_num(r, rng, pool):
    v = float(r["completion"])
    return dict(r, completion=str(int(v + rng.choice([-9, -4, -2, 2, 3, 7, 12]))))


SOURCES = {"mcq_arc": (mcq, wrong_mcq), "code_mbpp": (mbpp, wrong_code), "code_humaneval": (human, wrong_code),
           "free_dolly": (dolly, wrong_swap), "chat_soda": (soda, wrong_chat), "tool_glaive": (glaive, wrong_tool),
           "es_mgsm": (lambda: mgsm("es"), wrong_num), "de_mgsm": (lambda: mgsm("de"), wrong_num)}
LEVELS = {"dev": [0, 30], "eval": [0, 10, 30, 60]}


def clean(r):
    return {k: v for k, v in r.items() if not k.startswith("_") and not (k == "completion" and "messages" in r)} | (
        {"messages": r["messages"]} if "messages" in r else {})


def main():
    if OUT.exists():
        raise SystemExit(f"{OUT} exists: frozen.")
    manifest = []
    OUT.mkdir(parents=True)
    for name, (load, wrong) in SOURCES.items():
        rows = load()
        half = {"dev": rows[::2], "eval": rows[1::2]}
        print(name, len(rows))
        for part, sub in half.items():
            for lv in LEVELS[part]:
                rng = random.Random(SEED + lv)
                bad = set(rng.sample(range(len(sub)), round(lv / 100 * len(sub))))
                out = [wrong(r, rng, sub) if i in bad else r for i, r in enumerate(sub)]
                cid = f"{part}_{name}_n{lv}"
                (OUT / f"{cid}.jsonl").write_text("".join(json.dumps(clean(r)) + "\n" for r in out))
                manifest.append({"id": cid, "part": part, "source": name, "path": f"{cid}.jsonl", "noise": lv, "noisy_labels": lv >= 20})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(len(manifest), "cases")


if __name__ == "__main__":
    main()
