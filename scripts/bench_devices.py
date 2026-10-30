"""Benchmark the production LoRA SFT trainers on this machine: PyTorch MPS vs PyTorch CPU vs MLX.

Calls the exact functions an appraisal uses (touchstone.lm.sft and touchstone.mlx_backend.sft):
SmolLM2-*-Instruct, LoRA rank 16 on all attention and MLP projections, batch 16 of
chat-formatted examples from examples/datasets/good_cot.jsonl, completion-only loss,
AdamW 2e-4. Batches are split into micro-batches with gradient accumulation where needed
to stay inside 16 GB (PyTorch: 8, or 4 at 1.7B; MLX: 16, or 4 at 1.7B). The first steps
(graph compilation, warm-up) are excluded from the timing. Each configuration runs in its
own process so peak memory is clean.

    python scripts/bench_devices.py            # writes out/device_bench.json
"""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "out" / "device_bench.json"
PLAN = [("mps", "135M", 12), ("mlx", "135M", 12), ("cpu", "135M", 8),
        ("mps", "360M", 10), ("mlx", "360M", 10), ("cpu", "360M", 6),
        ("mlx", "1.7B", 6), ("mps", "1.7B", 5), ("cpu", "1.7B", 3)]


def one(backend, size, steps):
    from touchstone import data as datamod
    from touchstone import lm as L
    ex = datamod.load_dataset(ROOT / "examples" / "datasets" / "good_cot.jsonl")
    rec = L.Recipe()
    if backend == "mlx":
        from touchstone import mlx_backend
        lm = mlx_backend.MLXLM(size)
        _, info = mlx_backend.sft(lm, datamod.to_training_pairs(lm, ex), rec, steps=steps)
    else:
        L.set_device(backend)
        lm = L.LM(size)
        _, info = L.sft(lm, datamod.to_training_pairs(lm, ex), rec, steps=steps)
    skip = 2 if steps > 3 else 1
    t, n = info["step_seconds"][skip:], info["step_tokens"][skip:]
    r = {"backend": backend, "size": size, "timed_steps": len(t), "s_per_step": statistics.mean(t),
         "tokens_per_s": sum(n) / sum(t), "peak_gb": info["peak_memory_gb"], "dtype": info["dtype"],
         "device": info["device"]}
    print("RESULT " + json.dumps(r), flush=True)


def main():
    res = json.loads(OUT.read_text()) if OUT.exists() else []
    done = {(r["backend"], r["size"]) for r in res}
    for backend, size, steps in PLAN:
        if (backend, size) in done:
            continue
        p = subprocess.run([sys.executable, __file__, "--one", backend, size, str(steps)], capture_output=True, text=True)
        line = [x for x in p.stdout.splitlines() if x.startswith("RESULT ")]
        if not line:
            print(f"{backend} {size} failed:\n{p.stderr[-1500:]}", flush=True)
            continue
        r = json.loads(line[0][7:])
        res.append(r)
        OUT.write_text(json.dumps(res, indent=2))
        print(f"{backend:4s} {size:5s} {r['s_per_step']:.2f} s/step  {r['tokens_per_s']:.0f} tok/s  "
              f"peak {r['peak_gb']:.1f} GB  ({r['dtype']})", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--one":
        one(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    else:
        main()
