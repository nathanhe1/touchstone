"""Score frozen test v5 once (rules: METHOD.md, "Test v5, rules written before its data was examined").

Checks every hash in out/test_v5.sha256 first and refuses to run on a mismatch. Resumable per case; a finished case is
never rerun. Records the engine commit. Blocking flags are primary; advisory signals sit beside them. Per-row outputs are
kept for the row-level secondary measures: the multiple-choice judge's two routes, and the arithmetic check per row.

    python scripts/eval_test5.py          # writes out/test_v5_results.json
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import data as datamod, env as envmod, pipeline, screen, suites, valuation  # noqa: E402

F = ROOT / "out" / "test_v5_results.json"
T5 = ROOT / "examples" / "test5"
FLAGS = ["gameable_grader", "answer_leakage", "contaminated", "copied_from_public", "duplicated", "noisy_labels", "off_topic"]


def path_of(p):
    return Path(p).expanduser() if p.startswith(("~", "/")) else ROOT / p


def check_hashes():
    bad = []
    for line in (ROOT / "out" / "test_v5.sha256").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        h, f = line.split(None, 1)
        f = path_of(f.strip())
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
            bad.append(str(f))
    return bad


def main():
    bad = check_hashes()
    if bad:
        sys.exit("v5 hash mismatch, refusing to score: " + ", ".join(bad[:5]))
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    man = json.loads((T5 / "manifest.json").read_text())
    res = json.loads(F.read_text()) if F.exists() else {"_meta": {"commits": []}}
    if commit not in res["_meta"]["commits"]:
        res["_meta"]["commits"].append(commit)
    for m in man:
        if m["id"] in res:
            continue
        t = time.time()
        truth = sorted(k for k, v in m["labels"].items() if v)
        base = {"tier": m["tier"], "part": m["part"], "source": m["source"], "truth": truth, "negative": m.get("negative"), "commit": commit}
        if m["kind"] == "dataset":
            path = path_of(m["path"]) if m.get("private") else T5 / m["path"]
            spec = m["suite"]
            suite = suites.get_suite(str(path_of(spec)) if spec.endswith(".jsonl") else spec).subset(200)
            try:
                ex = datamod.load_dataset(path)
            except datamod.DatasetError as e:
                res[m["id"]] = {**base, "flags": [], "rejected_by_loader": str(e)[:200], "seconds": 0}
                F.write_text(json.dumps(res, indent=1))
                print("REJECTED", m["id"], str(e)[:100], flush=True)
                continue
            sc = pipeline.screen_material("dataset", [e.prompt_text for e in ex], suite, None, log=lambda x: None, examples=ex)
            rows_arith = [{"checked": screen.check_arithmetic(e.completion)[0] > 0, "wrong_eq": screen.check_arithmetic(e.completion)[1] > 0,
                           "unsupported": screen.unsupported_final(e.completion)} for e in ex]
            audit = (sc.get("label_quality") or {}).get("audit") or {}
            extra = {"row_truth": m.get("row_truth"), "row_arith": rows_arith, "judge_rows": audit.get("rows"), "loaded_rows": len(ex)}
        else:
            path = T5 / m["path"]
            suite = suites.get_suite(m["suite"]).subset(200)
            env = envmod.load(path)
            tasks = envmod.validate(env, path)
            sc = pipeline.screen_material("env", [t_.prompt for t_ in tasks], suite, None, log=lambda x: None, env=env, tasks=tasks)
            extra = {"audit": {k: sc["audit"].get(k) for k in ("score", "worst_exploit", "slice", "format_lax", "crashes")}}
        flags = sorted({f["code"] for f in valuation.flags_for(dict(sc["meas"], measurable=True))} & set(FLAGS))
        lab = (sc.get("checks") or {}).get("labels", {})
        res[m["id"]] = {**base, "flags": flags, "advisory": lab.get("advisory"), "checks": {k: v for k, v in lab.items() if k != "rows"},
                        "off_topic_check": (sc.get("checks") or {}).get("off_topic"),
                        "meas": {k: v for k, v in sc["meas"].items() if not isinstance(v, (dict, tuple))}, **extra, "seconds": round(time.time() - t)}
        F.write_text(json.dumps(res, indent=1))
        print("ok " if set(flags) == set(truth) else "ERR", m["id"], truth, flags, "ADV" if lab.get("advisory") else "", flush=True)


if __name__ == "__main__":
    main()
