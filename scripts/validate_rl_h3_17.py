"""1.7B target on the fresh held-out environments (METHOD.md, Fresh 1.7B target). Separate from the frozen h3 job.

The 32 environments come unchanged from scripts/validate_rl_h3.py. Each GRPO run is evaluated before and after
training, on its family's suite, two ways:
  working (primary)  the prompt asks for the working; format is the same before and after; limit 200 tokens
  plain (secondary)  the suite prompt as is; limit 48 tokens, as in the sweeps

    python scripts/validate_rl_h3_17.py --check
    python scripts/validate_rl_h3_17.py --shard 0/4      # GPU box, resumable
    python scripts/validate_rl_h3_17.py --merge
    python scripts/validate_rl_h3_17.py --score out/gpu3/validation_rl_h3.json out/gpu3/validation_rl_h3_17.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import score_h3 as S  # noqa: E402
import validate_rl_h3 as H  # noqa: E402
import validate_rl_real2 as V  # noqa: E402
from touchstone import forecast as fc  # noqa: E402
from touchstone import lm as L  # noqa: E402
from touchstone import suites  # noqa: E402
from touchstone.grpo import grpo  # noqa: E402

OUT = ROOT / "out" / "validation_rl_h3_17.json"
SIZE, SEEDS = "1.7B", 3
WORK = " Show the working first, then give the final answer on the last line."
_TAIL = re.compile(r"\s*Answer with [^.]*\.\s*$")


def working(p):
    return _TAIL.sub("", p) + WORK


def ev(lm, items, prompts, max_new):
    outs = lm.generate(prompts, max_new=max_new)
    return "".join("1" if suites.is_correct(o, i) else "0" for o, i in zip(outs, items))


def eval_both(lm, items):
    return {"working": ev(lm, items, [working(i.prompt) for i in items], 200), "plain": ev(lm, items, [i.prompt for i in items], 48)}


def one(name, seed):
    items = H.suite_for(name.split("_")[0]).items
    lm = L.LM(SIZE)
    before = eval_both(lm, items)
    tuned, info = grpo(lm, H.environments()[name], H.RECIPE, seed=int(seed))
    after = eval_both(tuned, items)
    print("RESULT " + json.dumps({"before": before, "after": after, "reward_first": info["train_reward_first"],
                                  "reward_last": info["train_reward_last"], "platform": V.platform_tag()}), flush=True)


def run(shard):
    out = OUT if not shard else OUT.with_suffix(f".shard{shard.split('/')[0]}.json")
    res = json.loads(out.read_text()) if out.exists() else {"runs": {}}
    for _ in range(3):
        for seed in range(SEEDS):
            for name in H.environments():
                key = f"{name}|{SIZE}|{seed}"
                if key in res["runs"] or (shard and not V.in_shard(key, shard)):
                    continue
                d = V.one_run([sys.executable, __file__, "--one", name, str(seed)])
                line = [x for x in (d[0] if d else "").splitlines() if x.startswith("RESULT ")]
                if not line:
                    print(key, "FAILED", (d[1][-400:] if d else "timeout"), flush=True)
                    continue
                res["runs"][key] = json.loads(line[0][7:])
                out.write_text(json.dumps(res))
                print(key, "done", flush=True)


def bits(s):
    return np.array([int(c) for c in s], float)


def target(res17, names, arm):
    """Gain per environment, per seed, and seed-mean item gains."""
    gains, items = {}, {}
    for n in names:
        rs = [res17["runs"][f"{n}|{SIZE}|{s}"] for s in range(SEEDS)]
        d = [100 * (bits(r["after"][arm]) - bits(r["before"][arm])) for r in rs]
        gains[n] = [float(x.mean()) for x in d]
        items[n] = np.mean(d, axis=0)
    return gains, items


def score(h3_file, f17):
    h3 = json.loads(Path(h3_file).read_text())
    r17 = json.loads(Path(f17).read_text())
    names = sorted({k.split("|")[0] for k in h3["runs"]})
    fams = [n.split("_")[0] for n in names]
    idx = {f: np.array([i for i, x in enumerate(fams) if x == f]) for f in S.FAMILIES}
    rng = np.random.default_rng(2)
    out = {"n_target_runs": len(r17["runs"]), "platforms": sorted({r["platform"] for r in r17["runs"].values()})}
    for arm in ("working", "plain"):
        gains, items = target(r17, names, arm)
        tgt = [float(np.mean(gains[n])) for n in names]
        base = {f: round(100 * float(np.mean([bits(r17["runs"][f"{names[i]}|{SIZE}|0"]["before"][arm]).mean() for i in idx[f]])), 1) for f in S.FAMILIES}
        ceil = np.mean([S.pair_acc([gains[n][s] for n in names], [float(np.mean([y for q, y in enumerate(gains[n]) if q != s])) for n in names], fams) for s in range(SEEDS)])
        block = {"base_accuracy": base, "ceiling": round(float(ceil), 3), "target": dict(zip(names, np.round(tgt, 2).tolist())),
                 "target_sd_within_family": round(float(np.mean([np.std([tgt[i] for i in idx[f]]) for f in S.FAMILIES])), 2)}
        for proxy in ("360M", "135M"):
            p = [S.mean_runs(h3, n, proxy, "acc_gain")[0] for n in names]
            obs = S.pair_acc(p, tgt, fams)
            hits = 0
            for _ in range(S.N_PERM):
                t = np.array(tgt)
                for f in S.FAMILIES:
                    t[idx[f]] = rng.permutation(t[idx[f]])
                hits += S.pair_acc(p, t, fams) >= obs
            b = []
            for _ in range(S.N_BOOT):
                pick = np.concatenate([rng.choice(idx[f], len(idx[f])) for f in S.FAMILIES])
                b.append(S.pair_acc([p[i] for i in pick], [tgt[i] for i in pick], [fams[i] for i in pick]))
            block["proxy_" + proxy] = {"decision_within_family": round(obs, 3), "ci90": [round(float(x), 3) for x in np.nanpercentile(b, [5, 95])],
                                       "perm_p": round((hits + 1) / (S.N_PERM + 1), 4),
                                       "mean_within_family_spearman": round(float(np.mean([fc.spearman([p[i] for i in idx[f]], [tgt[i] for i in idx[f]]) for f in S.FAMILIES])), 3),
                                       "by_family": {f: round(S.pair_acc([p[i] for i in idx[f]], [tgt[i] for i in idx[f]], [f] * len(idx[f])), 3) for f in S.FAMILIES}}
        out[arm] = block
        print(arm, json.dumps({k: v for k, v in block.items() if k != "target"}), flush=True)
    (ROOT / "out" / "forecast_h3_17.json").write_text(json.dumps(out, indent=1))


def check():
    for f in S.FAMILIES:
        it = H.suite_for(f).items
        print(f, repr(working(it[0].prompt)[:120]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--one", nargs=2)
    ap.add_argument("--shard")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--score", nargs=2)
    a = ap.parse_args()
    if a.one:
        one(*a.one)
    elif a.check:
        check()
    elif a.merge:
        res = {"runs": {}}
        for f in sorted(OUT.parent.glob(OUT.stem + ".shard*.json")):
            res["runs"].update(json.loads(f.read_text())["runs"])
        OUT.write_text(json.dumps(res))
        print(len(res["runs"]), "of 96 runs")
    elif a.score:
        score(*a.score)
    else:
        run(a.shard)
