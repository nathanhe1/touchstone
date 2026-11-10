"""Inputs for the real known-bad case studies (reports/case_studies/). Public materials whose problems someone other than
Touchstone documented. Data only; nothing downloaded is executed. Needs pyarrow==17.0.0 for the parquet files.

    python scripts/build_case_studies.py      # writes ~/.cache/touchstone/case_studies/inputs/ and prints sha256s

Sources (pinned revisions):
  GSM8K test           openai/gsm8k @ 740312add8 (MIT); GSM8K-Platinum madrylab/gsm8k-platinum @ e762492455 (MIT)
  MATH                 EleutherAI/hendrycks_math @ 21a5633873 (MIT)
  MathInstruct         TIGER-Lab/MathInstruct @ b4fdc323a7 (MIT)
  CodeAlpaca-20k       sahil2801/CodeAlpaca-20k @ 152bb5e9a2 (CC-BY-4.0), kept as delivered (a JSON array)
  HumanEval            openai/openai_humaneval @ 7dce6050a7 (MIT)
  WebArena             github.com/web-arena-x/webarena @ dce04686a5 (Apache-2.0): config_files/test.raw.json and the
                       StringEvaluator in evaluation_harness/evaluators.py (re-implemented in the environment below)
"""
import hashlib
import json
import re
from pathlib import Path

C = Path.home() / ".cache" / "touchstone" / "case_studies"
H5 = Path.home() / ".cache" / "touchstone" / "h5" / "raw"
OUT = C / "inputs"
SUBJECTS = ["algebra", "counting_and_probability", "geometry", "intermediate_algebra", "number_theory", "prealgebra", "precalculus"]


def pq(path):
    import pyarrow.parquet as p
    return p.read_table(path).to_pylist()


def write(name, rows):
    p = OUT / name
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}  {len(rows)} rows")
    return p


def boxed(s):
    i = (s or "").rfind("\\boxed")
    if i < 0:
        return None
    j = s.find("{", i)
    if j < 0:
        return None
    depth, k = 1, j + 1
    while k < len(s) and depth:
        depth += {"{": 1, "}": -1}.get(s[k], 0)
        k += 1
    return s[j + 1:k - 1].strip() if depth == 0 else None


def norm_q(s):
    return re.sub(r"\s+", " ", s).strip()


def gsm8k():
    """Case 1: the original GSM8K test split, as delivered, and the rows GSM8K-Platinum later removed or relabelled."""
    test = pq(H5 / "gsm8k.test.parquet") if (H5 / "gsm8k.test.parquet").exists() else pq(C / "gsm8k.test.parquet")
    plat = {norm_q(r["question"]): r for r in pq(H5 / "gsm8k_platinum.test.parquet")}
    rows, status = [], {}
    for i, r in enumerate(test):
        p = plat.get(norm_q(r["question"]))
        st = "removed" if p is None else ("relabelled" if p["cleaning_status"] == "revised" else p["cleaning_status"])
        rows.append({"question": r["question"], "answer": r["answer"], "id": f"test-{i}"})
        status[f"test-{i}"] = {"status": st, "platinum_answer": p["answer"].split("####")[-1].strip() if p else None,
                               "original_answer": r["answer"].split("####")[-1].strip()}
    write("gsm8k_test_original.jsonl", rows)
    (OUT / "gsm8k_test_platinum_status.json").write_text(json.dumps(status))
    from collections import Counter
    print("  platinum status:", Counter(v["status"] for v in status.values()))


def math():
    """Cases 2 and 3: MATH test as the buyer's held-out suite; MATH train and MathInstruct as materials."""
    suite, train = [], []
    for s in SUBJECTS:
        for r in pq(C / "math" / f"{s}.test.parquet"):
            a = boxed(r["solution"])
            if a:
                suite.append({"prompt": r["problem"], "answer": a, "match": "numeric" if re.fullmatch(r"-?\d+(\.\d+)?", a) else "exact",
                              "part": s})
        for r in pq(C / "math" / f"{s}.train.parquet"):
            train.append({"prompt": r["problem"], "completion": r["solution"]})
    write("math_test_suite.jsonl", suite)
    write("math_train.jsonl", train)
    mi = json.loads((C / "math" / "MathInstruct.json").read_text())
    write("mathinstruct.jsonl", [{"prompt": r["instruction"], "completion": r["output"], "source": r["source"]} for r in mi])


ENV = '''"""WebArena's string-match grader, as a Touchstone environment.

Tasks: every WebArena test task (config_files/test.raw.json @ dce04686a5) graded by string_match alone with only
exact_match and/or must_include references (fuzzy_match needs an LLM judge and is left out). The prompt is the task
intent. verify() re-implements StringEvaluator.clean_answer / exact_match / must_include from
evaluation_harness/evaluators.py at the same commit, line for line; nltk.word_tokenize (used only when a must_include
list has one single-character reference) is replaced by a regex word split. WebArena is Apache-2.0.
"""
import json
import re
from pathlib import Path

from touchstone.env import Task


def clean_answer(answer):
    answer = answer.strip()
    if answer.startswith("'") and answer.endswith("'"):
        answer = answer[1:-1]
    elif answer.startswith('"') and answer.endswith('"'):
        answer = answer[1:-1]
    return answer.lower()


def exact_match(ref, pred):
    return float(clean_answer(pred) == clean_answer(ref))


def must_include(ref, pred, tokenize=False):
    clean_ref, clean_pred = clean_answer(ref), clean_answer(pred)
    if tokenize and len(clean_ref) == 1 and len(re.findall(r"\\w+|[^\\w\\s]", clean_ref)) == 1:
        return float(clean_ref in re.findall(r"\\w+|[^\\w\\s]", clean_pred))
    return float(clean_ref in clean_pred)


class WebArenaStrings:
    name = "WebArena string-match tasks"
    domain = None

    def __init__(self):
        self._t = [Task(r["intent"], {"ref": r["ref"], "answer": r["answer"], "task_id": r["task_id"]})
                   for r in json.loads((Path(__file__).parent / "tasks.json").read_text())]

    def tasks(self):
        return self._t

    def reference(self, task):
        return task.meta["answer"]

    def verify(self, task, output):
        pred = clean_answer(output)
        score = 1.0
        for approach, value in task.meta["ref"].items():
            if approach == "exact_match":
                score *= exact_match(ref=value, pred=pred)
            elif approach == "must_include":
                for v in value:
                    score *= must_include(ref=v, pred=pred, tokenize=(len(value) == 1))
        return score


ENV = WebArenaStrings()
'''


def webarena():
    """Case 4: WebArena's string-match grader, documented as accepting answers padded with irrelevant content."""
    cfg = json.loads((C / "webarena" / "test.raw.json").read_text())
    tasks = []
    for r in cfg:
        ev = r["eval"]
        ref = ev.get("reference_answers") or {}
        if ev["eval_types"] != ["string_match"] or not ref or set(ref) - {"exact_match", "must_include"}:
            continue
        ans = ref["exact_match"] if "exact_match" in ref else ", ".join(ref["must_include"])
        tasks.append({"task_id": r["task_id"], "intent": r["intent"], "ref": ref, "answer": ans})
    d = OUT / "webarena_strings"
    d.mkdir(parents=True, exist_ok=True)
    (d / "tasks.json").write_text(json.dumps(tasks, indent=0))
    (d / "env.py").write_text(ENV)
    print(f"webarena_strings: {len(tasks)} tasks; sha256 tasks.json {hashlib.sha256((d / 'tasks.json').read_bytes()).hexdigest()}")


def code():
    """Case 5: CodeAlpaca, documented as holding rephrased HumanEval problems; HumanEval as the buyer's suite."""
    import shutil
    h = pq(C / "code" / "humaneval.parquet")
    write("humaneval_suite.jsonl", [{"prompt": r["prompt"], "answer": r["canonical_solution"].strip(), "match": "exact"} for r in h])
    shutil.copy(C / "code" / "code_alpaca_20k.json", OUT / "code_alpaca_20k.json")
    print(f"{hashlib.sha256((OUT / 'code_alpaca_20k.json').read_bytes()).hexdigest()}  code_alpaca_20k.json")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    gsm8k()
    math()
    webarena()
    code()
