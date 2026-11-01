"""Round 4 forecast runs: one training per (arm, family, condition, size, seed), resumable, sharded.

Arms are kept apart and never pooled:
  sft  fine-tune on material built from real rows (a dataset)
  rl   GRPO on the same family as an environment (reward from a grader)

    python scripts/h4_run.py sweep --set pilot --sizes 135M,360M --shard 0/6
    python scripts/h4_run.py one sft ag_news clean 360M 0 pilot
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import h4_common as H  # noqa: E402
from touchstone import lm as L  # noqa: E402
from touchstone.env import Task  # noqa: E402
from touchstone.grpo import grpo  # noqa: E402

CFG = json.loads((ROOT / "scripts" / "h4_config.json").read_text())
N_SUITE, MAX_NEW, RUN_TIMEOUT = CFG["suite_items"], CFG["max_new"], CFG.get("run_timeout", 1500)


def suite(fam):
    return H.items(fam, H.SPLITS[fam][1])[:N_SUITE]


def pool(fam, part):
    """Material rows: `pilot` uses even rows, `final` odd rows, so a final material never shares rows with the pilot."""
    it = H.items(fam, H.SPLITS[fam][0])
    s = {i[0] for i in suite(fam)}
    it = [x for x in it if x[0] not in s]
    return it[::2] if part == "pilot" else it[1::2]


def wrong(ans, prompt, rng):
    n = len(re.findall(r"(?m)^[A-P]\) ", prompt))
    return rng.choice([c for c in H.LETTERS[:max(n, 2)] if c != ans])


def other_family(fam):
    fams = CFG["families"]
    return fams[(fams.index(fam) + 1) % len(fams)]


def sft_rows(fam, cond, part, seed):
    rng = random.Random(zlib.crc32(f"{fam}|{cond}|{part}".encode()))  # material is fixed per condition, not per seed
    it = list(pool(fam, part))
    rng.shuffle(it)
    n = CFG["material_items"]
    base = it[:n]
    m = re.fullmatch(r"wrong(\d+)", cond)
    if m:
        k = int(m.group(1)) / 100
        return [(p, wrong(a, p, rng) if rng.random() < k else a) for p, a, _ in base]
    m = re.fullmatch(r"off(\d+)", cond)
    if m:
        k = int(int(m.group(1)) / 100 * n)
        ot = list(pool(other_family(fam), part))
        rng.shuffle(ot)
        return [(p, a) for p, a, _ in base[:n - k]] + [(p, a) for p, a, _ in ot[:k]]
    m = re.fullmatch(r"pool(\d+)", cond)
    if m:
        return [(p, a) for p, a, _ in base[:int(m.group(1))]]
    return [(p, a) for p, a, _ in base]


class Env4:
    """A family as an environment. The grader compares the reply's letter; conditions match the sft ones in spirit."""

    def __init__(self, fam, cond, part):
        self.name = f"{fam}_{cond}"
        rows = sft_rows(fam, "clean", part, 0)
        rng = random.Random(zlib.crc32(self.name.encode()))
        self.cond, self.rng = cond, rng
        self.noise = int(cond[5:]) / 100 if cond.startswith("noise") else 0.0
        if cond.startswith("pool"):
            rows = rows[:int(cond[4:])]
        if cond.startswith("off"):
            k = int(int(cond[3:]) / 100 * len(rows))
            ot = sft_rows(other_family(fam), "clean", part, 0)
            rows = rows[:len(rows) - k] + ot[:k]
        self._t = [Task(p + (f" (hint: {a})" if cond == "leak" else ""), {"answer": a}) for p, a in rows]

    def tasks(self):
        return self._t

    def verify(self, task, output):
        if self.cond == "lax":
            r = float(H._FIRST.search(output) is not None)
        else:
            r = float(H.correct(output, task.meta["answer"]))
        if self.noise and self.rng.random() < self.noise:
            r = 1.0 - r
        return r


def bits(lm, it):
    outs = lm.generate([x[0] for x in it], max_new=MAX_NEW, batch=32)
    return "".join("1" if H.correct(o, x[1]) else "0" for o, x in zip(outs, it)), outs


def one(arm, fam, cond, size, seed, part):
    it = suite(fam)
    lm = L.LM(size)
    b, _ = bits(lm, it)
    t = time.time()
    rec = L.Recipe(sft_steps=CFG["sft_steps"], rl_steps=CFG["rl_steps"], rl_group=CFG["rl_group"], sft_max_len=CFG["max_len"])
    if arm == "sft":
        pairs = [(lm.chat(p), a) for p, a in sft_rows(fam, cond, part, int(seed))]
        tuned, info = L.sft(lm, pairs, rec, seed=int(seed))
        extra = {"loss_last": info["loss_last"]}
    else:
        tuned, info = grpo(lm, Env4(fam, cond, part), rec, seed=int(seed))
        extra = {"reward_first": info["train_reward_first"], "reward_last": info["train_reward_last"], "skipped": info["skipped_no_signal"]}
    a, outs = bits(tuned, it)
    gain = 100 * (a.count("1") - b.count("1")) / len(it)
    print("RESULT " + json.dumps({"base": b, "after": a, "gain": gain, "train_s": round(time.time() - t), "sample": outs[:2],
                                  "platform": f"{L.device()}|torch {__import__('torch').__version__.split('+')[0]}", **extra}), flush=True)


def keys(part, sizes):
    S = CFG[part]
    for seed in range(S["seeds"]):
        for size in sizes:
            for arm in S["arms"]:
                for fam in S["arms"][arm]["families"]:
                    for cond in S["arms"][arm]["conditions"]:
                        yield f"{arm}|{fam}|{cond}|{size}|{seed}"


def sweep(part, sizes, shard):
    import signal
    import subprocess
    tag = shard.split("/")[0] if shard else "all"
    out = ROOT / "out" / f"h4_{part}.shard{tag}.json"
    res = json.loads(out.read_text()) if out.exists() else {}
    i, n = (map(int, shard.split("/"))) if shard else (0, 1)
    for _ in range(3):
        for key in keys(part, sizes):
            if key in res or zlib.crc32(key.encode()) % n != i:
                continue
            arm, fam, cond, size, seed = key.split("|")
            p = subprocess.Popen([sys.executable, __file__, "one", arm, fam, cond, size, seed, part], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, cwd=ROOT, start_new_session=True)
            try:
                so, se = p.communicate(timeout=RUN_TIMEOUT)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                print(key, "TIMEOUT", flush=True)
                continue
            line = [x for x in so.splitlines() if x.startswith("RESULT ")]
            if not line:
                print(key, "FAILED", se[-300:], flush=True)
                continue
            res[key] = json.loads(line[0][7:])
            out.write_text(json.dumps(res))
            print(key, f"{res[key]['gain']:+.2f} {res[key]['train_s']}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "one":
        one(*sys.argv[2:8])
    else:
        ap = argparse.ArgumentParser()
        ap.add_argument("mode")
        ap.add_argument("--set", default="pilot")
        ap.add_argument("--sizes", default="135M,360M")
        ap.add_argument("--shard")
        a = ap.parse_args()
        sweep(a.set, a.sizes.split(","), a.shard)
