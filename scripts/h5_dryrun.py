"""Development dry run of the h5 scorer on stored h4 development runs (ag_news, rotten, emotion; 135M, 360M, 1.7B).

Purpose: prove the frozen scorer runs end to end on real run files before any h5 run, so it cannot crash when it matters.
It is not a result and chooses nothing. Rungs are mapped by role: p12 = 135M (12.6x below 1.7B), p4 = 360M (4.7x).
The h4 development set has no `wrong100` arm, so the gate uses `wrong60` here; h5 itself uses `wrong100`. Stored runs carry
no soft score, so candidate C2 must come out as "inconclusive: missing runs", which is the path this checks for it.

    python scripts/h5_dryrun.py            # writes out/h5_dry/ and out/forecast_h5_dry.json
"""
import collections
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

FAMS = ["ag_news", "rotten", "emotion"]
DRY_MAX_SHARE = 0.6  # placeholder for the dry run only; h5 uses the lead's committed class-balance threshold


def main():
    import h4_run as H4  # noqa: E402  (reads the cached h4 sources)
    import h5_score
    d = ROOT / "out" / "h5_dry"
    d.mkdir(parents=True, exist_ok=True)
    R = {}
    for f in sorted(glob.glob(str(ROOT / "out" / "h4" / "h4_dev_*.json"))):
        R.update(json.loads(Path(f).read_text()))
    (d / "h5_runs_from_h4_dev.json").write_text(json.dumps(R))
    bal = {"max_share": DRY_MAX_SHARE}
    for fam in FAMS:
        def share(rows):
            c = collections.Counter(a for _, a, *rest in rows)
            return round(max(c.values()) / sum(c.values()), 3) if c else None
        mats = {}
        for cond in ["clean", "pool100", "pool300", "wrong10", "off25", "drop", "wrong60", "off80"]:
            mats[cond] = share(H4.sft_rows(fam, cond, "dev_small", 0))
        bal[fam] = {"suite": share(H4.suite(fam)), "materials": mats}
    (d / "h5_gates.json").write_text(json.dumps({"balance": bal}, indent=1))
    return h5_score.main(["dry", "--config", str(ROOT / "scripts" / "h5_config_dry.json"), "--runs", str(d),
                          "--out", str(ROOT / "out" / "forecast_h5_dry.json")])


if __name__ == "__main__":
    main()
