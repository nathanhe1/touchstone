"""Score frozen test v4 once. Resumable per case. Blocking flags are primary; advisory signals sit beside them."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import data as datamod, env as envmod, pipeline, suites, valuation  # noqa: E402

F = ROOT / "out" / "test_v4_results.json"
FLAGS = ["gameable_grader", "answer_leakage", "contaminated", "copied_from_public", "duplicated", "noisy_labels", "off_topic"]
man = json.loads((ROOT / "examples" / "test4" / "manifest.json").read_text())
res = json.loads(F.read_text()) if F.exists() else {}
for m in man:
    if m["id"] in res:
        continue
    t = time.time()
    path = ROOT / "examples" / "test4" / m["path"]
    suite = suites.get_suite(str(ROOT / m["suite"]) if m["suite"].endswith(".jsonl") else m["suite"]).subset(200)
    if m["kind"] == "dataset":
        try:
            ex = datamod.load_dataset(path)
        except datamod.DatasetError as e:  # the product refuses the file: no flags to score, reported on its own
            res[m["id"]] = {"part": m["part"], "source": m["source"], "truth": sorted(k for k, v in m["labels"].items() if v), "flags": [],
                            "rejected_by_loader": str(e)[:200], "advisory": None, "checks": {}, "meas": {}, "audit": None, "seconds": 0}
            F.write_text(json.dumps(res, indent=1))
            print("REJECTED", m["id"], str(e)[:100], flush=True)
            continue
        sc = pipeline.screen_material("dataset", [e.prompt_text for e in ex], suite, None, log=lambda x: None, examples=ex)
    else:
        env = envmod.load(path)
        tasks = envmod.validate(env, path)
        sc = pipeline.screen_material("env", [t_.prompt for t_ in tasks], suite, None, log=lambda x: None, env=env, tasks=tasks)
    flags = sorted({f["code"] for f in valuation.flags_for(dict(sc["meas"], measurable=True))} & set(FLAGS))
    truth = sorted(k for k, v in m["labels"].items() if v)
    lab = (sc.get("checks") or {}).get("labels", {})
    res[m["id"]] = {"part": m["part"], "source": m["source"], "truth": truth, "flags": flags, "advisory": lab.get("advisory"),
                    "checks": lab, "meas": {k: v for k, v in sc["meas"].items() if not isinstance(v, (dict, tuple))},
                    "audit": {k: sc["audit"].get(k) for k in ("score", "worst_exploit", "slice", "format_lax", "crashes")} if "audit" in sc else None,
                    "seconds": round(time.time() - t)}
    F.write_text(json.dumps(res, indent=1))
    print("ok " if set(flags) == set(truth) else "ERR", m["id"], truth, flags, "ADV" if lab.get("advisory") else "", flush=True)
