"""Is the 1.7B gain skill or a format shift? Placebo arms and a forced-format target (METHOD.md, 1.7B check).

    python scripts/debug_17_placebo.py format            # no training, about 3 minutes
    python scripts/debug_17_placebo.py arms --shard 0/3  # 3 environments x 3 arms x 3 seeds, resumable

Arms use the same recipe and seeds:
  material    the environment's own rewards
  shuffled    rewards shuffled across the batch (GRPO placebo=True): same reward rate, link to the reply destroyed
  random      every reply is rewarded with probability 0.3, whatever it says
`grader_number` cannot serve as a placebo: it pays every reply, so group advantages are zero and GRPO skips the
update. Environments are fixed in advance: mix_honest, sub_honest, spaced_honest (all development).

Every arm reports accuracy gain and the reply format before and after: mean words, share with an equals sign.
"""
import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import validate_rl_real2 as V  # noqa: E402
from touchstone import lm as L  # noqa: E402
from touchstone import suites  # noqa: E402
from touchstone.grpo import grpo  # noqa: E402

F = ROOT / "out" / "debug_17_placebo.json"
ENVS = ["mix_honest", "sub_honest", "spaced_honest"]
ARMS = ["material", "shuffled", "random"]
SUFFIX = {"plain": None, "working": " Show the working as an equation first, then give the final number."}
SIZE = "1.7B"


def suite_items():
    return suites.arithmetic_suite(V.SUITE_ITEMS).items


def score(lm, items, suffix=None):
    ps = [i.prompt if suffix is None else i.prompt.replace(" Answer with the number only.", suffix) for i in items]
    outs = lm.generate(ps, max_new=V.RECIPE.eval_max_new)
    acc = sum(suites.is_correct(o, i) for o, i in zip(outs, items)) / len(items)
    return {"acc": round(100 * acc, 2), "words": round(sum(len(o.split()) for o in outs) / len(outs), 2),
            "equals_share": round(100 * sum("=" in o for o in outs) / len(outs), 1), "sample": outs[:3]}


class RandomReward:
    def __init__(self, env, seed):
        self.env, self.rng = env, random.Random(seed)

    def tasks(self):
        return self.env.tasks()

    def verify(self, task, output):
        return float(self.rng.random() < 0.3)


def fmt():
    items = suite_items()
    res = {}
    for size in ("360M", "1.7B"):
        lm = L.LM(size)
        for k, sfx in SUFFIX.items():
            res[f"{size}|{k}"] = score(lm, items, sfx)
            print(size, k, json.dumps(res[f"{size}|{k}"]), flush=True)
        del lm
        L.free_memory()
    (ROOT / "out" / "debug_17_format.json").write_text(json.dumps(res, indent=1))


def one(name, arm, seed):
    items = suite_items()
    lm = L.LM(SIZE)
    before = score(lm, items)
    env = V.environments()[name]
    tuned, info = grpo(lm, RandomReward(env, int(seed)) if arm == "random" else env, V.RECIPE, seed=int(seed), placebo=arm == "shuffled")
    print("RESULT " + json.dumps({"before": before, "after": score(tuned, items), "reward_last": info["train_reward_last"],
                                  "skipped": info["skipped_no_signal"]}), flush=True)


def arms(shard):
    out = F if not shard else F.with_suffix(f".shard{shard.split('/')[0]}.json")
    res = json.loads(out.read_text()) if out.exists() else {}
    for _ in range(3):
        for seed in range(3):
            for name in ENVS:
                for arm in ARMS:
                    key = f"{name}|{arm}|{seed}"
                    if key in res or (shard and not V.in_shard(key, shard)):
                        continue
                    d = V.one_run([sys.executable, __file__, "one", name, arm, str(seed)])
                    line = [x for x in (d[0] if d else "").splitlines() if x.startswith("RESULT ")]
                    if not line:
                        print(key, "FAILED", (d[1][-300:] if d else "timeout"), flush=True)
                        continue
                    res[key] = json.loads(line[0][7:])
                    out.write_text(json.dumps(res, indent=1))
                    r = res[key]
                    print(key, f"gain {r['after']['acc'] - r['before']['acc']:+.2f} words {r['before']['words']}->{r['after']['words']} "
                          f"equals {r['before']['equals_share']}->{r['after']['equals_share']}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["format", "arms", "one", "merge"])
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--shard")
    a = ap.parse_args()
    if a.mode == "format":
        fmt()
    elif a.mode == "one":
        one(*a.rest)
    elif a.mode == "merge":
        res = {}
        for f in sorted(F.parent.glob(F.stem + ".shard*.json")):
            res.update(json.loads(f.read_text()))
        F.write_text(json.dumps(res, indent=1))
        print(len(res), "of 27")
    else:
        arms(a.shard)
