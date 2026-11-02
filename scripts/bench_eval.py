"""Benchmark held-out evaluation (generation + candidate scoring) on PyTorch MPS vs MLX.

    python scripts/bench_eval.py            # appends to out/device_bench_eval.json
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "out" / "device_bench_eval.json"
N = 64


def one(backend, size):
    from touchstone import measure, suites
    suite = suites.word_math_suite().subset(N)
    if backend == "mlx":
        from touchstone.mlx_backend import MLXLM
        lm = MLXLM(size)
    else:
        from touchstone import lm as L
        L.set_device(backend)
        lm = L.LM(size)
    t = time.time()
    ev = measure.evaluate(lm, suite, 96)
    dt = time.time() - t
    print("RESULT " + json.dumps({"backend": backend, "size": size, "items": len(suite.items), "seconds": round(dt, 1),
                                  "items_per_s": round(len(suite.items) / dt, 2),
                                  "accuracy": round(100 * measure.mean(ev["acc"]), 1)}), flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--one":
        one(sys.argv[2], sys.argv[3])
        sys.exit()
    res = []
    for size in ("135M", "360M", "1.7B"):
        for backend in ("mps", "mlx"):
            p = subprocess.run([sys.executable, __file__, "--one", backend, size], capture_output=True, text=True)
            line = [x for x in p.stdout.splitlines() if x.startswith("RESULT ")]
            if not line:
                print(backend, size, "failed", p.stderr[-800:])
                continue
            r = json.loads(line[0][7:])
            res.append(r)
            OUT.write_text(json.dumps(res, indent=2))
            print(f"{backend:4s} {size:5s} eval {r['items']} items in {r['seconds']}s ({r['items_per_s']}/s), acc {r['accuracy']}%",
                  flush=True)
