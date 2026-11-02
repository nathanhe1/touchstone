"""Check the torch judge route agrees with the MLX results already on file (dev data, 30 items)."""
import json
import os
import sys
import time
from pathlib import Path

os.environ["TOUCHSTONE_JUDGE_BACKEND"] = "torch"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import data, judge  # noqa: E402

t = time.time()
r = judge.audit(data.load_dataset(ROOT / "examples/datasets/short_noisy_30.jsonl"), n=30, extra=0)
mlx = json.loads((ROOT / "out/dev_judge_qwen.json").read_text())["short_noisy_30"]["rows"][:30]
same = sum(a["cot"] == b["cot"] and a["pal"] == b["pal"] for a, b in zip(r["rows"], mlx))
print(json.dumps({"torch_disagree": r["disagree"], "confident": r["confident"], "same_as_mlx": same, "of": len(mlx),
                  "seconds": round(time.time() - t)}), flush=True)
