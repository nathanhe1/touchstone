"""Run one model-heavy job at a time on a 16 GB laptop: lock, swap check, timeouts, detached.

    python scripts/run_heavy.py --name judge --timeout 7200 --stall 1200 -- python scripts/dev_judge.py ...

The job is re-launched in its own session and survives the shell that started it. Output goes to
out/<name>.log. A lock (out/.heavy.lock) allows one heavy job; others wait in strict first-in, first-out
order (out/.heavy_queue), and the reason for any wait is logged. Before starting, it waits until at least --min-free-pct of memory is free and no foreign
process holds more than --max-rss-gb. The job is killed (whole process group) when it passes --timeout, or
when its log has not grown for --stall seconds. Status lines go to out/heavy_jobs.log.
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "out" / ".heavy.lock"
JOBS = ROOT / "out" / "heavy_jobs.log"
QUEUE = ROOT / "out" / ".heavy_queue"


def note(msg):
    with JOBS.open("a") as f:
        f.write(f"{time.strftime('%F %T')} {msg}\n")


def swap_gb():
    m = re.search(r"used = ([\d.]+)M", subprocess.run(["sysctl", "vm.swapusage"], capture_output=True, text=True).stdout)
    return float(m.group(1)) / 1024 if m else 0.0


def free_pct():
    m = re.search(r"free percentage: (\d+)%", subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout)
    return int(m.group(1)) if m else 100


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def biggest_python():
    """Largest other Python process by resident memory (GB): a foreign heavy job we must not run beside."""
    out = subprocess.run(["ps", "-axo", "pid=,rss=,comm="], capture_output=True, text=True).stdout
    best = 0.0
    for ln in out.splitlines():
        p = ln.split(None, 2)
        if len(p) == 3 and "ython" in p[2] and int(p[0]) != os.getpid():
            best = max(best, int(p[1]) / 1024 ** 2)
    return best


def acquire(a):
    """Strict FIFO: each job holds a ticket; only the oldest live ticket may take the lock."""
    QUEUE.mkdir(exist_ok=True)
    ticket = QUEUE / f"{time.time():.3f}_{os.getpid()}"
    ticket.write_text(a.name)
    last = ""
    while True:
        for t in sorted(QUEUE.iterdir()):
            if not alive(int(t.name.split("_")[1])):
                t.unlink(missing_ok=True)
        head = sorted(QUEUE.iterdir())[0]
        why = ""
        if head != ticket:
            why = f"behind {head.read_text()}"
        elif LOCK.exists():
            holder = LOCK.read_text().split()
            if holder and alive(int(holder[0])):
                why = f"lock held by {holder[1]}"
            else:
                LOCK.unlink(missing_ok=True)
                continue
        elif free_pct() < a.min_free_pct:
            why = f"only {free_pct()}% memory free"
        elif biggest_python() > a.max_rss_gb:
            why = f"another Python process above {a.max_rss_gb} GB"
        if not why:
            LOCK.write_text(f"{os.getpid()} {a.name}")
            ticket.unlink()
            return
        if why != last:
            note(f"waiting {a.name}: {why}")
            last = why
        time.sleep(10)


def supervise(a):
    log = ROOT / "out" / f"{a.name}.log"
    note(f"queued {a.name}: {' '.join(a.cmd)}")
    acquire(a)
    note(f"start {a.name} (swap {swap_gb():.1f} GB)")
    for attempt in range(a.retries + 1):
        if run_once(a, log) != "stall":
            break
        note(f"retry {a.name}: attempt {attempt + 2} of {a.retries + 1}")
    LOCK.unlink(missing_ok=True)


def run_once(a, log):
    t0 = time.time()
    with log.open("ab") as f:
        p = subprocess.Popen(a.cmd, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, start_new_session=True,
                             env=dict(os.environ, PYTHONUNBUFFERED="1"))
    size, moved = -1, time.time()
    why = None
    while p.poll() is None:
        time.sleep(10)
        s = log.stat().st_size
        if s != size:
            size, moved = s, time.time()
        if time.time() - t0 > a.timeout:
            why = "timeout"
        elif time.time() - moved > a.stall:
            why = "stall"
        if why:
            os.killpg(p.pid, signal.SIGTERM)
            time.sleep(5)
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGKILL)
            break
    note(f"end {a.name}: {why or 'exit ' + str(p.returncode)} after {time.time() - t0:.0f}s (swap {swap_gb():.1f} GB)")
    return why


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--timeout", type=int, default=4 * 3600)
    ap.add_argument("--stall", type=int, default=1800)
    ap.add_argument("--min-free-pct", type=int, default=20, help="macOS keeps idle pages in swap, so swap used is no gate")
    ap.add_argument("--max-rss-gb", type=float, default=2.0)
    ap.add_argument("--retries", type=int, default=0, help="rerun after a stall (for resumable jobs)")
    ap.add_argument("--foreground", action="store_true", help="(internal) already detached")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    a.cmd = a.cmd[1:] if a.cmd[:1] == ["--"] else a.cmd
    if a.foreground:
        supervise(a)
    else:
        args = [sys.executable, __file__, "--foreground"] + sys.argv[1:]
        p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             cwd=ROOT, start_new_session=True)
        print(f"detached supervisor pid {p.pid}: out/{a.name}.log")
