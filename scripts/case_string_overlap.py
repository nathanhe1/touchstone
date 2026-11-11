"""Documented-contamination cases, string tiers only (exact and near-duplicate; no embedding model, so it is light).

For each material and suite: how many suite items the overlap screen's exact and near tiers find in the material.
The paraphrase tier needs the embedding model and is run by scripts/case_full_suite_overlap.py.
Writes out/case_studies/string_overlap.json.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import data, overlap  # noqa: E402

I = Path(os.environ.get("CASE_INPUTS", Path.home() / ".cache/touchstone/case_studies/inputs"))
CASES = [("math_train", "math_train.jsonl", "math_test_suite.jsonl"), ("mathinstruct", "mathinstruct.jsonl", "math_test_suite.jsonl"),
         ("code_alpaca", "code_alpaca_20k.json", "humaneval_suite.jsonl")]
out = {}
for name, mat, suite in CASES:
    t = time.time()
    ex = data.load_dataset(I / mat)
    prompts = [e.prompt_text for e in ex]
    sp = [json.loads(x)["prompt"] for x in open(I / suite)]
    m = overlap.match(prompts, sp, use_embeddings=False)            # material rows that copy a suite item
    hit_rows = [prompts[i] for i in m["matched_idx"]]
    s = overlap.match(sp, hit_rows, use_embeddings=False) if hit_rows else {"matched_idx": [], "exact": 0, "near": 0, "examples": []}
    by_src = {}
    for i in m["matched_idx"]:
        k = ex[i].meta.get("source", "all")
        by_src[k] = by_src.get(k, 0) + 1
    out[name] = {"material_rows": len(prompts), "skipped_rows": ex.skipped, "suite_items": len(sp),
                 "material_rows_matching_suite": len(m["matched_idx"]),
                 "material_rows_exact": round(m["exact"] * len(prompts)), "material_rows_near": round(m["near"] * len(prompts)),
                 "suite_items_found": len(s["matched_idx"]), "suite_share_found": round(len(s["matched_idx"]) / len(sp), 4),
                 "suite_items_exact": round(s["exact"] * len(sp)), "suite_items_near": round(s["near"] * len(sp)),
                 "matching_rows_by_source": by_src, "examples": s["examples"], "seconds": round(time.time() - t)}
    print(name, json.dumps({k: v for k, v in out[name].items() if k != "examples"}), flush=True)
    (ROOT / "out" / "case_studies" / "string_overlap.json").write_text(json.dumps(out, indent=1))
