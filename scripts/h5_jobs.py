"""Sprint h5 job runner: packs runs onto every GPU on the box by memory, resumes after a crash, records everything.

    python scripts/h5_jobs.py run  jobs.jsonl --out out/h5/<set> [--budget-gb 30] [--max-procs 6] [--timeout 3600]
    python scripts/h5_jobs.py status jobs.jsonl --out out/h5/<set>

jobs.jsonl holds one job per line (see scripts/h5_run.py) with an extra "mem_gb" estimate from the timing table.
Jobs run in file order (write the matrix largest-first). A job is done when out/<id>.json exists; finished results are
never rerun, so a crashed or restarted runner picks up where it stopped. Each result is written atomically (tmp + rename).
A failed or timed-out run is logged to failures.jsonl and retried at most `--retries` times under the same config.
A GPU's memory budget is shared by the jobs on it; a job starts when its estimate fits and fewer than --max-procs run.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def gpus():
    try:
        q = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.total", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, check=True).stdout
        return [(int(a), int(b) / 1024) for a, b in (l.split(",") for l in q.strip().splitlines())]
    except Exception:
        return [(0, 32.0)]


def load_jobs(path):
    jobs = [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    ids = [j["id"] for j in jobs]
    assert len(ids) == len(set(ids)), "duplicate job ids"
    return jobs


def done(out, j):
    return (out / f"{j['id']}.json").exists()


def run(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = load_jobs(a.jobs)
    fails = {}
    ff = out / "failures.jsonl"
    if ff.exists():
        for x in ff.read_text().splitlines():
            k = json.loads(x)["id"]
            fails[k] = fails.get(k, 0) + 1
    G = gpus()
    budget = {g: min(a.budget_gb, tot - 1.5) for g, tot in G}
    used = {g: 0.0 for g, _ in G}
    running = {}  # id -> (proc, gpu, mem, t0, job, logfile)
    queue = [j for j in jobs if not done(out, j) and fails.get(j["id"], 0) <= a.retries]
    print(f"{len(jobs)} jobs, {len(jobs) - len(queue)} done or given up, {len(queue)} to run on GPUs {[g for g, _ in G]}", flush=True)
    logs = out / "logs"
    logs.mkdir(exist_ok=True)
    while queue or running:
        for k, (p, g, m, t0, j, lf) in list(running.items()):
            rc = p.poll()
            timed_out = rc is None and time.time() - t0 > j.get("timeout", a.timeout)
            if rc is None and not timed_out:
                continue
            if timed_out:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
            lf.close()
            text = (logs / f"{k}.log").read_text(errors="replace")
            line = [x for x in text.splitlines() if x.startswith("RESULT ")]
            if line and not timed_out:
                tmp = out / f".{k}.json.tmp"
                tmp.write_text(line[-1][7:])
                tmp.replace(out / f"{k}.json")
                r = json.loads(line[-1][7:])
                print(f"done {k} gain={r.get('gain')} base={r.get('base_acc')} wall={r.get('wall_s')}s mem={r.get('peak_mem_gb')}GB"
                      f"{' REFUSED' if r.get('refused') else ''}", flush=True)
            else:
                why = "timeout" if timed_out else f"exit {rc}"
                with ff.open("a") as f:
                    f.write(json.dumps({"id": k, "why": why, "t": time.time(), "tail": text[-600:]}) + "\n")
                fails[k] = fails.get(k, 0) + 1
                print(f"FAILED {k} ({why}), attempt {fails[k]}", flush=True)
                if fails[k] <= a.retries:
                    queue.append(j)
            used[g] -= m
            del running[k]
        started = True
        while started and queue:
            started = False
            for j in list(queue):
                m = float(j.get("mem_gb", 8))
                g = next((g for g, _ in G if used[g] + m <= budget[g] and sum(1 for v in running.values() if v[1] == g) < a.max_procs), None)
                if g is None:
                    if a.strict_order:
                        break
                    continue
                queue.remove(j)
                lf = (logs / f"{j['id']}.log").open("w")
                env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(g), "PYTHONUNBUFFERED": "1", "TOKENIZERS_PARALLELISM": "false"}
                p = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "h5_run.py"), "one", json.dumps(j)], stdout=lf, stderr=subprocess.STDOUT,
                                     cwd=ROOT, env=env, start_new_session=True)
                running[j["id"]] = (p, g, m, time.time(), j, lf)
                used[g] += m
                started = True
                print(f"start {j['id']} on gpu{g} ({m:.0f} GB est, {used[g]:.0f}/{budget[g]:.0f} in use)", flush=True)
                break
        time.sleep(2)
    print("all jobs finished or given up", flush=True)


def status(a):
    out = Path(a.out)
    jobs = load_jobs(a.jobs)
    d = [j for j in jobs if done(out, j)]
    rs = [json.loads((out / f"{j['id']}.json").read_text()) for j in d]
    wall = sum(r.get("wall_s", 0) for r in rs)
    print(f"{len(d)}/{len(jobs)} done; summed run wall time {wall / 3600:.2f} h; refused {sum(1 for r in rs if r.get('refused'))}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "status"])
    ap.add_argument("jobs")
    ap.add_argument("--out", required=True)
    ap.add_argument("--budget-gb", type=float, default=30.0)
    ap.add_argument("--max-procs", type=int, default=6)
    ap.add_argument("--timeout", type=float, default=3600)
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--strict-order", action="store_true", help="never start a later job ahead of an earlier one that does not fit yet")
    a = ap.parse_args()
    run(a) if a.mode == "run" else status(a)
