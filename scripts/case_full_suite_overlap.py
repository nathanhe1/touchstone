"""Touchstone's own matchers on all 5,000 MATH test items (a quick appraisal screens only its scoring subset).

Writes out/case_studies/math_full_suite_overlap.json: for MATH train and MathInstruct, how many MATH test items the
overlap screen finds in the material, by match kind, and for MathInstruct which sub-source the matching rows come from.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import overlap  # noqa: E402
from touchstone.judge import label_of  # noqa: E402

I = Path(os.environ.get("CASE_INPUTS", Path.home() / ".cache/touchstone/case_studies/inputs"))
suite = [json.loads(x) for x in open(I / "math_test_suite.jsonl")]
sp = [r["prompt"] for r in suite]
out = {}
for name in ("math_train", "mathinstruct"):
    t = time.time()
    rows = [json.loads(x) for x in open(I / f"{name}.jsonl")]
    rows = [r for r in rows if r["prompt"].strip() and r["completion"].strip()]
    prompts = [r["prompt"] for r in rows]
    hit = overlap.match(sp, prompts)
    gated = overlap.gated_suite_match([(r["prompt"], r["answer"]) for r in suite], [(r["prompt"], label_of(r["completion"])) for r in rows])
    by_src = {}
    if name == "mathinstruct":
        contam = overlap.match(prompts, sp)
        for i in contam["matched_idx"]:
            by_src[rows[i]["source"]] = by_src.get(rows[i]["source"], 0) + 1
    out[name] = {"suite_items": len(sp), "material_rows": len(rows), "suite_items_matched": len(hit["matched_idx"]),
                 "rate": round(hit["rate"], 4), "exact": round(hit["exact"], 4), "near": round(hit["near"], 4),
                 "paraphrase": round(hit["paraphrase"], 4), "gated_rate": gated["rate"], "examples": hit["examples"],
                 "material_matches_by_source": by_src, "seconds": round(time.time() - t)}
    print(name, json.dumps({k: v for k, v in out[name].items() if k != "examples"}), flush=True)
    (ROOT / "out" / "case_studies" / "math_full_suite_overlap.json").write_text(json.dumps(out, indent=1))
