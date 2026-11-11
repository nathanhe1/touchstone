"""Real public files in the shapes buyers send, run through POST /api/appraise (FDE sprint, priority 3).

    python scripts/fde_real_inputs.py build                    # cut files from ~/.cache/touchstone/fde_inputs/raw
    python scripts/fde_real_inputs.py run --api http://localhost:8000 [--mode quick]

Writes out/fde_real_inputs.json: per file, the shape it tests, the HTTP answer, the job's final status, the error if
any, rows skipped, flags and wall time. Sources (all public; licences recorded per file below).
"""
import argparse
import io
import json
import sys
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = Path.home() / ".cache" / "touchstone" / "fde_inputs" / "raw"
FILES = Path.home() / ".cache" / "touchstone" / "fde_inputs" / "files"
CS = Path.home() / ".cache" / "touchstone" / "case_studies" / "inputs"

CASES = [  # file name, shape, source and licence
    ("no_robots_train.parquet", "parquet, chat messages with system turns, multi-turn",
     "HuggingFaceH4/no_robots @ e6f9a4ac5c train (CC-BY-NC-4.0), as published"),
    ("aya_test.parquet", "parquet, non-English rows (70+ languages), inputs/targets columns",
     "CohereForAI/aya_dataset @ f9ea04583f test (Apache-2.0), as published"),
    ("TruthfulQA.csv", "CSV with capitalised headers and no prompt/answer pair",
     "github.com/sylinrl/TruthfulQA @ d71c110897 (Apache-2.0), as published"),
    ("slimorca_2000.jsonl", "ShareGPT 'conversations' with from/value and system prompts",
     "Open-Orca/SlimOrca-Dedup @ bd7d445aa1 (MIT), first 2,000 rows of shard 1"),
    ("openr1_math_300.jsonl", "very long replies (reasoning traces), LaTeX, 'messages' column",
     "open-r1/OpenR1-Math-220k @ e4e141ec9d (Apache-2.0), first 300 rows of default shard 0, columns as published"),
    ("mathinstruct_20000.jsonl", "one empty reply at row 18,866, program-of-thought code replies",
     "TIGER-Lab/MathInstruct @ b4fdc323a7 (MIT), first 20,000 rows"),
    ("code_alpaca_20k.json", "Hugging Face JSON-array export (not JSON lines), empty 'input' fields",
     "sahil2801/CodeAlpaca-20k @ 152bb5e9a2 (CC-BY-4.0), as published"),
    ("numina_cot_1000.jsonl", "LaTeX math with \\boxed answers, long worked solutions",
     "examples/h5/gsm/numina_cot.jsonl (AI-MO/NuminaMath-CoT, Apache-2.0)"),
    ("env_with_deps.zip", "environment folder importing a local helper module and an uninstalled package",
     "built here: a K&K environment (examples/h5/kk) whose env.py imports helpers.py and reasoning_gym"),
    ("env_local_helper.zip", "environment folder importing a local helper module and listing requirements.txt",
     "built here: the same environment without the uninstalled package"),
]


def build():
    import pyarrow.parquet as pq
    FILES.mkdir(parents=True, exist_ok=True)
    (FILES / "no_robots_train.parquet").write_bytes((RAW / "no_robots.train.parquet").read_bytes())
    (FILES / "aya_test.parquet").write_bytes((RAW / "aya.test.parquet").read_bytes())
    (FILES / "TruthfulQA.csv").write_bytes((RAW / "TruthfulQA.csv").read_bytes())
    t = pq.ParquetFile(RAW / "slimorca.1.parquet").read_row_group(0).slice(0, 2000).to_pylist()
    (FILES / "slimorca_2000.jsonl").write_text("".join(json.dumps(r) + "\n" for r in t))
    t = pq.ParquetFile(RAW / "openr1.default0.parquet").read_row_group(0, columns=["problem", "solution", "answer", "messages"]).slice(0, 300).to_pylist()
    (FILES / "openr1_math_300.jsonl").write_text("".join(json.dumps(r) + "\n" for r in t))
    lines = (CS / "mathinstruct.jsonl").read_text().splitlines()[:20000]
    (FILES / "mathinstruct_20000.jsonl").write_text("\n".join(lines) + "\n")
    (FILES / "code_alpaca_20k.json").write_bytes((CS / "code_alpaca_20k.json").read_bytes())
    (FILES / "numina_cot_1000.jsonl").write_bytes((ROOT / "examples" / "h5" / "gsm" / "numina_cot.jsonl").read_bytes())
    kk = [json.loads(x) for x in (ROOT / "examples" / "h5" / "kk" / "kk_train.jsonl").read_text().splitlines()][:300]
    helper = ("import re\n\ndef correct(reply, names, solution):\n"
              "    for name, knight in zip(names, solution):\n"
              "        m = re.findall(rf'{re.escape(name)} is a (knight|knave)', reply or '', flags=re.I)\n"
              "        if not m or (m[-1].lower() == 'knight') != bool(knight):\n            return 0.0\n    return 1.0\n")
    env = ("import json\nfrom pathlib import Path\n{extra}from touchstone.env import Task\nfrom helpers import correct\n\n"
           "class KK:\n    name = 'Knights and Knaves'\n    def __init__(self):\n"
           "        self._t = [Task(r['prompt'], {{'answer': r['answer'], 'names': r['meta']['names'], 'solution': r['meta']['solution']}})\n"
           "                   for r in json.loads((Path(__file__).parent / 'tasks.json').read_text())]\n"
           "    def tasks(self):\n        return self._t\n"
           "    def verify(self, task, output):\n        return correct(output, task.meta['names'], task.meta['solution'])\n\nENV = KK()\n")
    for name, extra in (("env_with_deps.zip", "import reasoning_gym  # listed in requirements.txt, not installed\n"), ("env_local_helper.zip", "")):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("kk_env/env.py", env.format(extra=extra))
            z.writestr("kk_env/helpers.py", helper)
            z.writestr("kk_env/tasks.json", json.dumps(kk))
            z.writestr("kk_env/requirements.txt", "reasoning-gym==0.1.19\n" if extra else "regex\n")
        (FILES / name).write_bytes(buf.getvalue())
    for f, _, _ in CASES:
        print(f, (FILES / f).stat().st_size)


def post(api, path, mode):
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"mode\"\r\n\r\n{mode}\r\n--{b}\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode() \
        + path.read_bytes() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(api + "/api/appraise", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def run(api, mode, only=None):
    out = ROOT / "out" / "fde_real_inputs.json"
    res = json.loads(out.read_text()) if out.exists() else {}
    for f, shape, src in CASES:
        if only and f not in only:
            continue
        t0 = time.time()
        code, body = post(api, FILES / f, mode)
        rec = {"shape": shape, "source": src, "bytes": (FILES / f).stat().st_size, "http": code, "mode": mode}
        if code != 202:
            rec["error"] = body.get("detail")
        else:
            jid = body["job_id"]
            while True:
                with urllib.request.urlopen(f"{api}/api/jobs/{jid}", timeout=60) as r:
                    j = json.load(r)
                if j["status"] in ("done", "error", "cancelled"):
                    break
                time.sleep(5)
            rec.update(status=j["status"], error=j.get("error"), job_id=jid, wall_s=round(time.time() - t0))
            if j.get("report"):
                rp = j["report"]
                rec.update(grade=rp["grade"], flags=[x["code"] for x in rp["flags"]], n_items=rp["material"]["n_items"],
                           skipped_rows=rp["material"].get("skipped_rows", 0), runtime_s=rp.get("runtime_s"))
        res[f] = rec
        out.write_text(json.dumps(res, indent=1))
        print(f, json.dumps({k: rec.get(k) for k in ("http", "status", "error", "grade", "skipped_rows", "wall_s")})[:400], flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--mode", default="quick")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    build() if a.cmd == "build" else run(a.api, a.mode, a.only)
