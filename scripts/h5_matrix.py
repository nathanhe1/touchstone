"""Build the h5 run matrix from the frozen config (scripts/h5_config.json, the researcher's schema) and check it fits.

    python scripts/h5_matrix.py scripts/h5_config.json out/h5_timing.json jobs.jsonl --hours-left 12.5

Jobs are written largest rung first, so the runs that answer the main question finish before anything optional.
Each family runs its passing and failing materials plus `placebo` at every rung, 2 seeds (the config may say more).
RL families also get one `rlgate` job per rung, before any RL training on that family.

The fit check uses the timing table (seconds and peak GB per run, by arm and rung), assumes 70% of that throughput,
and requires a 15% reserve of the hours left. Small rungs pack in parallel by memory; the estimate counts the
target rung's runs as serial and the smaller rungs at the measured packing factor in the timing file.
"""
import argparse
import json
from pathlib import Path


def material_spec(fam_cfg, m):
    """Condition name -> the runner's material string (supplied materials live in fam_cfg['files'])."""
    files = fam_cfg.get("files", {})
    if m in files:
        return "file:" + files[m]
    if m.startswith("shuffled_") and m[9:] in files:
        return "shuffle:file:" + files[m[9:]]
    if m == "placebo" and files:
        return "shuffle:file:" + files[fam_cfg["gate_ref"]]
    return m


def build(cfg, timing):
    jobs = []
    seeds = cfg.get("seeds", 2)
    for arm_name, A in cfg["arms"].items():
        run_arm = A.get("run_arm", "sft")
        rungs = A["rungs"]
        order = sorted(set(rungs.values()), key=lambda s: -timing["params"].get(s, 0))
        for size in order:
            for fam, F in A["families"].items():
                mats = list(dict.fromkeys(F.get("passing", []) + F.get("failing", []) + ["placebo"]))
                if run_arm == "rl":
                    jobs.append({"id": f"h5_{arm_name}_rlgate_{fam}_{size}", "arm": "rlgate", "family": fam, "material": "clean",
                                 "size": size, "seed": 0, "part": cfg.get("part", "final"), "recipe": F.get("recipe", {}),
                                 "mem_gb": timing["mem"].get(f"base|{size}", 20)})
                for seed in range(seeds):
                    for m in mats:
                        jobs.append({"id": f"h5_{arm_name}_{run_arm}_{fam}_{m}_{size}_s{seed}", "arm": run_arm, "family": fam,
                                     "material": material_spec(F, m), "material_name": m, "size": size, "seed": seed,
                                     "part": cfg.get("part", "final"), "recipe": F.get("recipe", {}),
                                     "mem_gb": timing["mem"].get(f"{run_arm}|{size}", 20)})
            for name, M in A.get("measurements", {}).items():
                if M.get("size") == size and M.get("run_arm"):
                    for fam, F in A["families"].items():
                        for seed in range(seeds):
                            for m in list(dict.fromkeys(F.get("passing", []) + ["placebo"])):
                                jobs.append({"id": f"h5_{arm_name}_{M['run_arm']}_{fam}_{m}_{size}_s{seed}", "arm": M["run_arm"],
                                             "family": fam, "material": material_spec(F, m), "material_name": m, "size": size,
                                             "seed": seed, "part": cfg.get("part", "final"), "recipe": F.get("recipe", {}),
                                             "mem_gb": timing["mem"].get(f"{run_arm}|{size}", 20), "optional": name})
    return jobs


def estimate(jobs, timing):
    """GPU-hours: per-run seconds by arm|rung, divided by the measured packing factor for that rung."""
    s = 0.0
    for j in jobs:
        arm = "sft" if j["arm"].startswith("sft") else ("rl" if j["arm"].startswith("rl") and j["arm"] != "rlgate" else j["arm"])
        sec = timing["seconds"].get(f"{arm}|{j['size']}|{j['family']}") or timing["seconds"].get(f"{arm}|{j['size']}", 300)
        s += sec / timing.get("packing", {}).get(j["size"], 1.0)
    return s / 3600


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("timing")
    ap.add_argument("dest")
    ap.add_argument("--hours-left", type=float, required=True)
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    timing = json.loads(Path(a.timing).read_text())
    jobs = build(cfg, timing)
    ids = [j["id"] for j in jobs]
    assert len(ids) == len(set(ids)), "duplicate job ids"
    raw = estimate(jobs, timing)
    planned = raw / 0.7
    avail = a.hours_left * 0.85
    req = [j for j in jobs if "optional" not in j]
    print(f"{len(jobs)} jobs ({len(req)} required); {raw:.2f} GPU-h at measured throughput, {planned:.2f} h at 70%; "
          f"{avail:.2f} h available after a 15% reserve -> {'FITS' if planned <= avail else 'DOES NOT FIT'}")
    print(f"required only: {estimate(req, timing) / 0.7:.2f} h at 70%")
    Path(a.dest).write_text("\n".join(json.dumps(j) for j in jobs) + "\n")


if __name__ == "__main__":
    main()
