"""Run code labels against their tests in a restricted subprocess.

Vendor code is untrusted. Every snippet runs in a fresh interpreter (isolated mode, no site-packages)
with a CPU, memory-file and process budget, an empty working directory and a wall-clock timeout. On
macOS the process also runs under `sandbox-exec`: no network, no writes outside its scratch folder, no
reads under /Users. On Linux it needs `unshare -n -r` (no network namespace otherwise). If neither is
available nothing is executed and the check reports "not checked": a weaker sandbox is not a fallback.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

PROFILE = """(version 1)(allow default)(deny network*)
(deny file-write*)(allow file-write* (subpath "{tmp}") (literal "/dev/null"))
(deny file-read* (subpath "/Users"))(allow file-read* (subpath "{tmp}"))
(deny process-exec*)(allow process-exec (literal "{py}") (subpath "{home}"))"""


def _python() -> str:
    return os.path.realpath(sys.executable)


def isolation() -> str | None:
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        return "sandbox-exec"
    if sys.platform.startswith("linux") and shutil.which("unshare"):
        if subprocess.run(["unshare", "-n", "-r", "true"], capture_output=True).returncode == 0:
            return "unshare"
    return None


def _limits():
    import resource
    os.setsid()
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 ** 20, 2 ** 20))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run_test(code: str, test: str, timeout: float = 8.0) -> dict:
    """{'passed': bool, 'error': short reason}. Raises RuntimeError when no isolation is available."""
    iso = isolation()
    if iso is None:
        raise RuntimeError("no process isolation on this machine")
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="ts_code_"))
    try:
        Path(tmp, "t.py").write_text(code + "\n\n" + test + "\n", encoding="utf-8")
        py = _python()
        cmd = [py, "-I", "-S", "-B", "t.py"]
        if iso == "sandbox-exec":
            cmd = ["sandbox-exec", "-p", PROFILE.format(tmp=tmp, py=py, home=os.path.realpath(sys.base_prefix))] + cmd
        else:
            cmd = ["unshare", "-n", "-r"] + cmd
        p = subprocess.Popen(cmd, cwd=tmp, env={"PATH": "/usr/bin:/bin", "HOME": tmp}, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, preexec_fn=_limits)
        try:
            _, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return {"passed": False, "error": "timeout"}
        tail = err.decode("utf-8", "replace").strip().splitlines()[-1:] or [""]
        return {"passed": p.returncode == 0, "error": tail[0][:120] if p.returncode else ""}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_of(meta: dict) -> str | None:
    """A runnable test from the row: 'test', 'tests' or 'test_list', with HumanEval's check(entry_point) form."""
    t = meta.get("test") or meta.get("tests") or meta.get("test_list")
    if isinstance(t, list):
        t = "\n".join(map(str, t))
    if not isinstance(t, str) or not t.strip():
        return None
    if meta.get("entry_point") and "def check" in t:
        t += f"\ncheck({meta['entry_point']})\n"
    return t


def strip_fence(c: str) -> str:
    if "```" in c:
        parts = c.split("```")
        body = parts[1]
        return body.split("\n", 1)[1] if body.split("\n", 1)[0].strip().isalpha() else body
    return c


def audit(examples, n: int = 60, seed: int = 0) -> dict:
    pool = [e for e in examples if test_of(e.meta)]
    rng = random.Random(seed)
    sample = rng.sample(pool, min(n, len(pool)))
    fails, reasons = 0, {}
    for e in sample:
        code = (e.meta.get("code_prefix") or "") + strip_fence(e.completion)
        r = run_test(code, test_of(e.meta))
        if not r["passed"]:
            fails += 1
            k = r["error"].split(":")[0] or "failed"
            reasons[k] = reasons.get(k, 0) + 1
    return {"tested": len(sample), "failed": fails, "rate": round(fails / len(sample), 4) if sample else None,
            "reasons": reasons, "isolation": isolation()}


if __name__ == "__main__":
    print(json.dumps(run_test(sys.argv[1], sys.argv[2])))
