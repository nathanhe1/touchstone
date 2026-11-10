"""Score h5, the pre-registered forecast test (METHOD.md, section 6, "h5"). Fine-tuning and RL are scored separately.

The candidates, gates, bars and stop rule are constants in this file, not in the config, so editing the config cannot
change them. The config (`scripts/h5_config.json`) only lists rungs, families and materials, and is hashed at the freeze.

    python scripts/h5_score.py dry   --config <cfg> --runs <dir> --out <file>   # development dry run, any data
    python scripts/h5_score.py final --config scripts/h5_config.json --runs out/h5 --out out/forecast_h5.json

`final` checks every hash in out/h5_final.sha256 first and refuses to overwrite an existing result: each candidate is
scored once.

Run records: JSON dicts in <runs>/h5_*.json, keyed `arm|family|material|size|seed`, each with
  gain        accuracy gain in points on the family's suite (after - before, greedy, same items)
  soft_gain   100 x change in mean chance-corrected soft score (scripts/h5_soft.py); needed by candidate C2
  base        per-item correctness before training, as a "0101..." string (target headroom gate)
Pre-training gate records, <runs>/h5_gates.json:
  {"balance": {"max_share": x, "<family>": {"suite": share, "materials": {"<material>": share}}},
   "rl": {"<family>|<size>": {"reward_rate": r, "chance": c, "truncated": t}}}
"""
import argparse
import glob
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- frozen rules (METHOD.md, h5)
CANDIDATES = {  # name: (signal field, proxy rung). Exactly three: a baseline and two new ones, each one factor from it.
    "B acc_final 12x": ("gain", "p12"),
    "C1 acc_final 4x": ("gain", "p4"),
    "C2 soft 12x": ("soft_gain", "p12"),
}
BASELINE = "B acc_final 12x"
BAR = 0.80                 # screen-passing decision accuracy needed to pass
ALPHA = 0.05 / len(CANDIDATES)  # Bonferroni over the three candidates, within an arm
FAMILY_SHARE = 0.6         # share of covered families that must sit above 0.5 ...
MIN_FAMILIES = 3           # ... and never fewer than this many covered families
MIN_PAIRS = 30             # fewer screen-passing pairs than this: inconclusive for that candidate
CEILING_MIN = 0.75         # target noise ceiling (screen-passing) below this: the arm is inconclusive
FT_GATE = 5.0              # fine-tuning gate: reference minus all-wrong, points, at the candidate's proxy rung
HEADROOM = 90.0            # target base accuracy at or above this: family abstains (no headroom)
RL_KAPPA = 0.10            # RL gate: chance-corrected reward rate before training, at least this
RL_REWARD_MAX = 0.90       # ... and raw reward rate at most this (groups must be able to differ)
COMPARE_ALPHA = 0.05       # one-sided, for "C beats B" on families both cover
N_PERM, N_BOOT, SEED = 10000, 2000, 0


# ---------------------------------------------------------------- data
def load_runs(d):
    R = {}
    for f in sorted(glob.glob(f"{d}/h5_*.json")):
        if Path(f).name == "h5_gates.json":
            continue
        R.update(json.loads(Path(f).read_text()))
    return R


def mean_field(R, arm, fam, mat, size, field):
    v = [r.get(field) for k, r in R.items() if k.startswith(f"{arm}|{fam}|{mat}|{size}|")]
    v = [x for x in v if x is not None]
    return float(np.mean(v)) if v else None


def seed_field(R, arm, fam, mat, size, field, seed):
    r = R.get(f"{arm}|{fam}|{mat}|{size}|{seed}")
    return None if r is None else r.get(field)


def seeds_of(R, arm, size):
    return sorted({int(k.split("|")[4]) for k in R if k.startswith(arm + "|") and k.split("|")[3] == size})


def base_acc(R, arm, fam, size):
    v = [100 * r["base"].count("1") / len(r["base"]) for k, r in R.items() if k.startswith(f"{arm}|{fam}|") and k.split("|")[3] == size and r.get("base")]
    return float(np.mean(v)) if v else None


# ---------------------------------------------------------------- pairwise scoring (same rules as h4)
def agree(p, t, mats):
    """Correct calls and counted pairs. Target ties are dropped; a signal tie counts as a miss."""
    a = b = ties = 0
    for x, y in itertools.combinations(mats, 2):
        if None in (t.get(x), t.get(y), p.get(x), p.get(y)):
            continue
        d = t[x] - t[y]
        if d == 0:
            ties += 1
            continue
        b += 1
        a += (p[x] - p[y]) * d > 0
    return a, b, ties


def score(sig, tgt, mats):
    a = b = ties = 0
    per = {}
    for f in mats:
        x, y, z = agree(sig[f], tgt[f], mats[f])
        a, b, ties = a + x, b + y, ties + z
        per[f] = round(x / y, 3) if y else None
    return a, b, ties, per


def perm_p(sig, tgt, mats, rng, n=N_PERM):
    a, b, _, _ = score(sig, tgt, mats)
    if not b:
        return None
    obs, hits = a / b, 0
    for _ in range(n):
        t = {f: dict(zip(mats[f], rng.permutation([tgt[f][m] for m in mats[f]]))) for f in mats}
        x, y, _, _ = score(sig, t, mats)
        hits += y and x / y >= obs
    return round((hits + 1) / (n + 1), 5)


def _boot_once(sig, tgt, mats, fams, rng):
    a = b = 0
    for f in rng.choice(fams, len(fams)):
        pick = list(rng.choice(mats[f], len(mats[f])))
        for x, y in itertools.combinations(range(len(pick)), 2):
            cx, cy = pick[x], pick[y]
            if cx == cy:
                continue
            d = tgt[f][cx] - tgt[f][cy]
            if d == 0:
                continue
            b += 1
            a += (sig[f][cx] - sig[f][cy]) * d > 0
    return a / b if b else None


def boot(sig, tgt, mats, rng, n=N_BOOT):
    fams = np.array(sorted(mats))
    out = [v for v in (_boot_once(sig, tgt, mats, fams, rng) for _ in range(n)) if v is not None]
    return [round(float(q), 3) for q in np.percentile(out, [5, 95])] if out else None


def spearman_mean(sig, tgt, mats):
    v = []
    for f in mats:
        ms = [m for m in mats[f] if sig[f].get(m) is not None and tgt[f].get(m) is not None]
        if len(ms) < 3:
            continue
        a = np.argsort(np.argsort([sig[f][m] for m in ms]))
        b = np.argsort(np.argsort([tgt[f][m] for m in ms]))
        if a.std() and b.std():
            v.append(float(np.corrcoef(a, b)[0, 1]))
    return round(float(np.mean(v)), 3) if v else None


def ceiling(R, arm, size, mats):
    """One target seed against the mean of the others, averaged over seeds."""
    seeds = seeds_of(R, arm, size)
    if len(seeds) < 2:
        return None
    v = []
    for s in seeds:
        a = {f: {m: seed_field(R, arm, f, m, size, "gain", s) for m in mats[f]} for f in mats}
        o = [q for q in seeds if q != s]
        b = {f: {m: _mean([seed_field(R, arm, f, m, size, "gain", q) for q in o]) for m in mats[f]} for f in mats}
        x, y, _, _ = score(a, b, mats)
        if y:
            v.append(x / y)
    return round(float(np.mean(v)), 3) if v else None


def _mean(v):
    v = [x for x in v if x is not None]
    return float(np.mean(v)) if v else None


def compare(sigA, sigB, tgt, mats, rng):
    """Candidate A minus candidate B on the same families and pairs: difference, paired bootstrap 90%, one-sided p."""
    def per_family(sa, sb):
        out = {}
        for f in mats:
            xa, ya, _ = agree(sa[f], tgt[f], mats[f])
            xb, yb, _ = agree(sb[f], tgt[f], mats[f])
            if ya and yb:
                out[f] = (xa, ya, xb, yb)
        return out
    pf = per_family(sigA, sigB)
    if not pf:
        return None
    fams = sorted(pf)

    def diff(sel):
        xa = sum(pf[f][0] for f in sel); ya = sum(pf[f][1] for f in sel)
        xb = sum(pf[f][2] for f in sel); yb = sum(pf[f][3] for f in sel)
        return xa / ya - xb / yb
    obs = diff(fams)
    bs = [diff(list(rng.choice(fams, len(fams)))) for _ in range(N_BOOT)]
    # paired permutation: within each family, swap which candidate is A with probability 1/2
    hits = 0
    for _ in range(N_PERM):
        flip = rng.random(len(fams)) < 0.5
        xa = ya = xb = yb = 0
        for f, fl in zip(fams, flip):
            a1, a2, b1, b2 = pf[f]
            if fl:
                a1, a2, b1, b2 = b1, b2, a1, a2
            xa, ya, xb, yb = xa + a1, ya + a2, xb + b1, yb + b2
        hits += xa / ya - xb / yb >= obs
    p = (hits + 1) / (N_PERM + 1)
    return {"families": fams, "difference": round(obs, 3), "ci90": [round(float(q), 3) for q in np.percentile(bs, [5, 95])],
            "p_one_sided": round(p, 5), "beats_baseline": bool(p < COMPARE_ALPHA and obs > 0),
            "underpowered": len(fams) < 5}  # a family-level sign flip cannot reach p < 0.05 with fewer than 5 families


# ---------------------------------------------------------------- gates
def gates_for_arm(R, G, arm_name, A):
    """Per family: family-level verdict, and per rung verdict (a candidate abstains where its proxy rung fails)."""
    run_arm, rungs = A["run_arm"], A["rungs"]
    bal = G.get("balance", {})
    out = {}
    for fam, F in A["families"].items():
        g = {"reasons": [], "rung": {}, "excluded_materials": {}}
        b = bal.get(fam)
        if b is None:
            g["reasons"].append("no class-balance record")
        else:
            mx = b.get("max_share", bal.get("max_share"))  # the lead's fetch gate: min(0.65, 2.5 / options), per family
            if not isinstance(mx, (int, float)):
                g["reasons"].append("no class-balance threshold")
                mx = float("inf")
            if b.get("suite") is not None and b["suite"] > mx:
                g["reasons"].append(f"suite majority share {b['suite']:.2f} > {mx}")
            for m, s in (b.get("materials") or {}).items():
                if s is not None and s > mx:
                    g["excluded_materials"][m] = f"majority share {s:.2f} > {mx}"
        tb = base_acc(R, run_arm, fam, rungs["target"])
        g["target_base"] = None if tb is None else round(tb, 1)
        if tb is None:
            g["reasons"].append("no target base accuracy")
        elif tb >= HEADROOM:
            g["reasons"].append(f"target base {tb:.1f} >= {HEADROOM} (no headroom)")
        if A["kind"] == "rl":
            rt = _rl_gate(G, fam, rungs["target"])
            g["target_rl_gate"] = rt
            if not rt["pass"]:
                g["reasons"].append("RL gate fails at the target: " + rt["why"])
        for role in ("p12", "p4"):
            size = rungs[role]
            if A["kind"] == "ft":
                ref = mean_field(R, run_arm, fam, F["gate_ref"], size, "gain")
                wr = mean_field(R, run_arm, fam, F["gate_wrong"], size, "gain")
                if ref is None or wr is None:
                    g["rung"][role] = {"pass": False, "why": "gate runs missing"}
                else:
                    g["rung"][role] = {"pass": ref - wr >= FT_GATE, "ref_minus_wrong": round(ref - wr, 2),
                                       "why": "" if ref - wr >= FT_GATE else f"reference minus all-wrong {ref - wr:.1f} < {FT_GATE}"}
            else:
                g["rung"][role] = _rl_gate(G, fam, size)
        g["family_pass"] = not g["reasons"]
        out[fam] = g
    return out


def _rl_gate(G, fam, size):
    r = (G.get("rl") or {}).get(f"{fam}|{size}")
    if not r:
        return {"pass": False, "why": "no pre-training RL gate record"}
    c = r["chance"]
    kappa = (r["reward_rate"] - c) / (1 - c) if c < 1 else 0.0
    why = []
    if kappa < RL_KAPPA:
        why.append(f"chance-corrected reward {kappa:.2f} < {RL_KAPPA}")
    if r["reward_rate"] > RL_REWARD_MAX:
        why.append(f"reward rate {r['reward_rate']:.2f} > {RL_REWARD_MAX}")
    # Truncation and no-answer shares are reported, never gated: untrained base replies never end (Qwen3-8B truncates
    # 13-94% at 32 tokens), and kappa >= RL_KAPPA already requires correct answers inside the reply limit.
    na = r.get("no_answer")
    return {"pass": not why, "kappa": round(kappa, 3), "reward_rate": r["reward_rate"], "no_answer": na, "truncated": r.get("truncated"),
            "why": "; ".join(why)}


# ---------------------------------------------------------------- one arm
def score_arm(R, G, arm_name, A, rng):
    run_arm, rungs = A["run_arm"], A["rungs"]
    gates = gates_for_arm(R, G, arm_name, A)
    fam_ok = [f for f in A["families"] if gates[f]["family_pass"]]

    def passing(f):
        return [m for m in A["families"][f]["passing"] if m not in gates[f]["excluded_materials"]]

    def all_mats(f):
        return [m for m in passing(f) + A["families"][f].get("failing", []) if m not in gates[f]["excluded_materials"]]

    def tgt(fams, mats_of, field="gain"):
        return {f: {m: mean_field(R, run_arm, f, m, rungs["target"], field) for m in mats_of(f)} for f in fams}

    ceil_mats = {f: passing(f) for f in fam_ok}
    out = {"rungs": rungs, "gates": gates, "families_gated_in": fam_ok,
           "abstained_families": {f: gates[f]["reasons"] for f in A["families"] if f not in fam_ok},
           "noise_ceiling": {"screen_passing": ceiling(R, run_arm, rungs["target"], ceil_mats),
                             "all": ceiling(R, run_arm, rungs["target"], {f: all_mats(f) for f in fam_ok})},
           "candidates": {}, "comparisons": {}, "measurements": {}}
    ceil = out["noise_ceiling"]["screen_passing"]
    out["arm_inconclusive"] = ceil is None or ceil < CEILING_MIN
    sigs = {}
    for name, (field, role) in CANDIDATES.items():
        cov = [f for f in fam_ok if gates[f]["rung"][role]["pass"]]
        no_soft = {}
        if field == "soft_gain":  # an answer type with no candidate set (free-form K&K answers) has no soft score: abstain there
            for f in cov:
                g = [mean_field(R, run_arm, f, m, rungs[role], "gain") for m in passing(f)]
                if all(x is not None for x in g) and all(mean_field(R, run_arm, f, m, rungs[role], field) is None for m in passing(f)):
                    no_soft[f] = ["no soft score for this answer type"]
            cov = [f for f in cov if f not in no_soft]
        row = {"signal": field, "proxy": rungs[role], "covered": cov,
               "abstained": {**{f: (gates[f]["reasons"] or [gates[f]["rung"][role]["why"]]) for f in A["families"] if f not in cov and f not in no_soft},
                             **no_soft}}
        sig = {f: {m: mean_field(R, run_arm, f, m, rungs[role], field) for m in all_mats(f)} for f in cov}
        missing = sorted({f"{f}|{m}" for f in cov for m in passing(f) if sig[f][m] is None})
        if missing:
            row["missing_signal"] = missing
        sigs[name] = sig
        for label, mats_of in (("screen_passing", passing), ("all", all_mats)):
            mats = {f: mats_of(f) for f in cov}
            t = tgt(cov, mats_of)
            a, b, ties, per = score(sig, t, mats) if cov else (0, 0, 0, {})
            row[label] = {"decision": round(a / b, 3) if b else None, "pairs": b, "target_ties_dropped": ties, "by_family": per,
                          "ci90": boot(sig, t, mats, rng) if b else None, "perm_p": perm_p(sig, t, mats, rng) if b else None,
                          "spearman_mean": spearman_mean(sig, t, mats) if b else None}
        sp = row["screen_passing"]
        above = sum(1 for v in sp["by_family"].values() if v is not None and v > 0.5)
        need = max(MIN_FAMILIES, math.ceil(FAMILY_SHARE * len(cov)))
        row["families_above_half"] = f"{above} of {len(cov)}"
        if out["arm_inconclusive"]:
            verdict = "inconclusive: target noise ceiling below %.2f" % CEILING_MIN
        elif missing:
            verdict = "inconclusive: missing runs"
        elif len(cov) < MIN_FAMILIES or sp["pairs"] < MIN_PAIRS:
            verdict = f"inconclusive: coverage ({len(cov)} families, {sp['pairs']} pairs)"
        elif sp["decision"] >= BAR and sp["perm_p"] < ALPHA and above >= need:
            verdict = "pass"
        else:
            verdict = "fail: retired"
        row["verdict"] = verdict
        row["by_stratum"] = {}
        for st in sorted({A["families"][f].get("stratum", "all") for f in cov}):
            fs = [f for f in cov if A["families"][f].get("stratum", "all") == st]
            mats = {f: passing(f) for f in fs}
            t = tgt(fs, passing)
            a, b, ties, per = score(sig, t, mats)
            ce = ceiling(R, run_arm, rungs["target"], mats)
            row["by_stratum"][st] = {"decision": round(a / b, 3) if b else None, "pairs": b, "by_family": per, "noise_ceiling": ce,
                                     "ci90": boot(sig, t, mats, rng) if b else None, "perm_p": perm_p(sig, t, mats, rng) if b else None,
                                     "inconclusive": ce is None or ce < CEILING_MIN or b < MIN_PAIRS}
        out["candidates"][name] = row
    # one-factor comparisons against the baseline, on families both cover
    for name in CANDIDATES:
        if name == BASELINE:
            continue
        both = [f for f in out["candidates"][name]["covered"] if f in out["candidates"][BASELINE]["covered"]]
        if not both:
            out["comparisons"][f"{name} vs {BASELINE}"] = None
            continue
        mats = {f: passing(f) for f in both}
        t = tgt(both, passing)
        ok = all(sigs[n][f][m] is not None for n in (name, BASELINE) for f in both for m in mats[f])
        out["comparisons"][f"{name} vs {BASELINE}"] = compare(sigs[name], sigs[BASELINE], t, mats, rng) if ok else "missing runs"
    # reported measurements: never candidates, never pass or fail
    for mname, M in A.get("measurements", {}).items():
        cov = [f for f in fam_ok]
        sig = {}
        for f in cov:
            pl = max(0.0, mean_field(R, M["run_arm"], f, "placebo", M["size"], "gain") or 0.0) if M.get("net_of_placebo") else 0.0
            sig[f] = {m: (lambda v: None if v is None else v - pl)(mean_field(R, M["run_arm"], f, m, M["size"], M.get("field", "gain"))) for m in passing(f)}
        t = {f: {m: mean_field(R, M.get("target_arm", run_arm), f, m, M.get("target_size", rungs["target"]), M.get("target_field", "gain"))
                 for m in passing(f)} for f in cov}
        if not cov or any(v is None for f in cov for v in list(sig[f].values()) + list(t[f].values())):
            out["measurements"][mname] = "not run"
            continue
        mats = {f: passing(f) for f in cov}
        a, b, ties, per = score(sig, t, mats)
        out["measurements"][mname] = {"decision": round(a / b, 3) if b else None, "pairs": b, "by_family": per,
                                      "ci90": boot(sig, t, mats, rng) if b else None, "perm_p": perm_p(sig, t, mats, rng) if b else None}
    return out


# ---------------------------------------------------------------- main
def check_hashes(manifest):
    bad = []
    for line in Path(manifest).read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        h, f = line.split(None, 1)
        f = ROOT / f.strip()
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
            bad.append(str(f))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dry", "final"])
    ap.add_argument("--config", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hashes", default=str(ROOT / "out" / "h5_final.sha256"))
    a = ap.parse_args(argv)
    out_path = Path(a.out)
    if a.mode == "final":
        if out_path.exists():
            sys.exit(f"{out_path} exists: h5 is scored once. Refusing to overwrite.")
        bad = check_hashes(a.hashes)
        if bad:
            sys.exit("hash mismatch, refusing to score: " + ", ".join(bad))
    cfg = json.loads(Path(a.config).read_text())
    R = load_runs(a.runs)
    gp = Path(a.runs) / "h5_gates.json"
    G = json.loads(gp.read_text()) if gp.exists() else {}
    rng = np.random.default_rng(SEED)
    res = {"mode": a.mode, "runs": len(R), "rules": {"candidates": CANDIDATES, "bar": BAR, "alpha": ALPHA, "family_share": FAMILY_SHARE,
           "min_families": MIN_FAMILIES, "min_pairs": MIN_PAIRS, "ceiling_min": CEILING_MIN, "ft_gate": FT_GATE, "headroom": HEADROOM,
           "rl_kappa": RL_KAPPA, "rl_reward_max": RL_REWARD_MAX},
           "scorer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "arms": {}}
    if a.mode == "dry":
        res["label"] = "DEVELOPMENT DRY RUN: not a result"
    for arm_name, A in cfg["arms"].items():  # never pooled
        res["arms"][arm_name] = score_arm(R, G, arm_name, A, rng)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(res, indent=1))
    for arm_name, X in res["arms"].items():
        print(f"[{arm_name}] ceiling {X['noise_ceiling']} gated in {len(X['families_gated_in'])}")
        for n, c in X["candidates"].items():
            print(f"  {n}: {c['screen_passing']['decision']} ({c['screen_passing']['pairs']} pairs, p {c['screen_passing']['perm_p']}), "
                  f"covered {len(c['covered'])}, {c['verdict']}")
        for n, c in X["comparisons"].items():
            print(f"  {n}: {c if not isinstance(c, dict) else {k: c[k] for k in ('difference', 'ci90', 'p_one_sided', 'beats_baseline')}}")
    return res


if __name__ == "__main__":
    main()
