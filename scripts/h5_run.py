"""Sprint h5: one training run from a job spec, and the record that makes it auditable.

    python scripts/h5_run.py one '<job json>'      # used by scripts/h5_jobs.py; prints one RESULT line

A job is {"id", "arm", "family", "material", "size", "seed", "part", "recipe": {...}}:

  arm       sft (LoRA fine-tuning), sfttr (sft cut to `trunc_steps`), rl (GRPO), rltr (GRPO cut short), base (no training),
            rlgate (no training: reward rate at temperature 1, a group of rollouts on each of 64 clean-material
            prompts, under the training reply limit; chance and truncation beside it)
  family    a family in scripts/h4_common.py (letter answers) or in NUMERIC below (number answers)
  material  a condition name built from the family's own rows (clean, placebo, wrong100, pool100, off25, drop, ...)
            or "file:<path>" for a supplied JSONL of {"prompt", "answer"} rows (the FDE's real materials),
            or "shuffle:file:<path>" for that material with its completions shuffled across rows
  recipe    overrides of the fixed recipe; anything that could move a result must be frozen in the pre-registration

Every result records the job, its config, seed, wall time, training time, peak GPU memory, platform and engine commit.
The class-balance gate (h4_common.gate_balance) is applied to every suite and to every clean or supplied material
before training; a refusal is recorded as a result with "refused" set, never silently skipped.
"""
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import h4_common as H  # noqa: E402

CFG = json.loads((ROOT / "scripts" / "h5_recipe.json").read_text())

_NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def last_number(s):
    m = _NUM.findall(s.replace("$", ""))
    if not m:
        return None
    try:
        return float(m[-1].replace(",", "").rstrip("."))
    except ValueError:
        return None


def num_correct(reply, answer):
    """The final answer is the number after 'answer is', else the last number in the reply."""
    m = re.search(r"answer is[:\s]*\$?(-?[\d,]*\.?\d+)", reply, re.I)
    v = float(m.group(1).replace(",", "")) if m else last_number(reply)
    try:
        return v is not None and abs(v - float(answer)) < 1e-6
    except ValueError:
        return False


FILE_FAMS = {}  # family -> {"suite": path, "kind": "letter" | "number" | "kk"}: families supplied as files (the FDE's)
_KIND = {"numeric": "number", "exact": "letter", "kk": "kk"}


def kk_correct(reply, names, solution):
    """Knights and Knaves (examples/h5, FDE): every person's last stated role must match the solution."""
    for name, knight in zip(names, solution):
        m = re.findall(rf"{re.escape(name)} is a (knight|knave)", reply or "", flags=re.I)
        if not m or (m[-1].lower() == "knight") != bool(knight):
            return False
    return True


def kind(fam):
    if fam in FILE_FAMS:
        return FILE_FAMS[fam]["kind"]
    return "number" if fam in CFG.get("numeric_families", {}) else "letter"


def is_numeric(fam):
    return kind(fam) == "number"


def correct(fam, reply, answer, meta=None):
    k = (meta or {}).get("kind") or kind(fam)
    if k == "kk":
        return kk_correct(reply, meta["names"], meta["solution"])
    return num_correct(reply, answer) if k == "number" else H.correct(reply, answer)


_LEAD_LETTER = re.compile(r"^\s*\(?([A-P])(?:\)|\.|:|,|\s*$|\s*\n)")  # "C", "C)", "(C)", "C.", "C\n": not "I purchased"


def has_answer(fam, reply, meta=None):
    """An answer in the form asked for, never a stray capital in prose: a letter at the very start of the reply; a number
    after "answer is" or alone on the reply's last line; for K&K, a stated role for every person (or one, without meta)."""
    reply = reply or ""
    k = kind(fam)
    if k == "kk":
        names = (meta or {}).get("names")
        if names:
            return all(re.search(rf"{re.escape(n)} is a (knight|knave)", reply, re.I) for n in names)
        return re.search(r"is a (knight|knave)", reply, re.I) is not None
    if k == "number":
        if re.search(r"answer is[:\s]*\$?-?[\d,]*\.?\d+", reply, re.I):
            return True
        last = reply.strip().splitlines()[-1] if reply.strip() else ""
        return re.fullmatch(r"[^A-Za-z]*-?[\d,]*\.?\d+[^A-Za-z]*", last) is not None
    return _LEAD_LETTER.match(reply) is not None


def register(job):
    if job.get("suite_file"):
        first = json.loads(Path(job["suite_file"]).read_text().splitlines()[0])
        FILE_FAMS[job["family"]] = {"suite": job["suite_file"], "kind": _KIND.get(first.get("match"), job.get("answer_kind", "letter"))}


def numeric_items(fam, split):
    """(prompt, answer, chance=0) rows of a number-answer family from its fetched JSON."""
    spec = CFG["numeric_families"][fam]
    out, seen = [], set()
    for r in H.load(spec.get("source", fam), split):
        q, a = r.get(spec["q"]), r.get(spec["a"])
        if q is None or a is None:
            continue
        a = str(a).split("####")[-1].strip().replace(",", "")
        try:
            float(a)
        except ValueError:
            continue
        p = q.strip() + "\n" + spec["instruction"]
        if p not in seen:
            seen.add(p)
            out.append((p, a, 0.0))
            if spec.get("worked"):  # the source's worked solution, calculator marks removed, ending as the prompt asks
                w = re.sub(r"<<[^>]*>>", "", str(r[spec["a"]]).split("####")[0]).strip()
                WORKED[p] = f"{w}\nThe answer is {a}."
    return out


WORKED = {}


def _worked(fam, rows, rng):
    """Number families with worked solutions train on the solution: a correct row gets its own, a wrong row (all-wrong,
    placebo, noisy) gets another problem's whole solution, so its working and answer are both unrelated to the prompt."""
    if not (is_numeric(fam) and fam not in FILE_FAMS and CFG["numeric_families"][fam].get("worked")):
        return rows
    truth = {p: a for p, a, _ in fam_items(fam, splits(fam)[0])}
    others = [WORKED[p] for p, _ in rows if p in WORKED]
    return [(p, WORKED[p]) if truth.get(p) == a and p in WORKED else (p, rng.choice(others)) for p, a in rows]


def fam_items(fam, split):
    return numeric_items(fam, split) if is_numeric(fam) else H.items(fam, split)


def splits(fam):
    return CFG["numeric_families"][fam]["splits"] if is_numeric(fam) else H.SPLITS[fam]


def suite(fam):
    """(prompt, answer, chance[, meta]) items, first `suite_items` in the suite's fixed order."""
    if fam in FILE_FAMS:
        rows = [json.loads(x) for x in Path(FILE_FAMS[fam]["suite"]).read_text().splitlines() if x.strip()]
        out = []
        for r in rows:
            p, a = r["prompt"], str(r["answer"])
            n = len(re.findall(r"(?m)^[A-P]\) ", p))
            ch = r.get("chance", 0.0 if kind(fam) == "number" else 1 / max(2, n))
            meta = {"names": r["names"], "solution": r["solution"]} if kind(fam) == "kk" else None
            out.append((p, a, ch, meta))
        return out[:CFG["suite_items"]]
    return fam_items(fam, splits(fam)[1])[:CFG["suite_items"]]


def pool(fam, part):
    """Material rows: `dev` uses even rows, `final` odd rows, so a final material never shares rows with development."""
    it = fam_items(fam, splits(fam)[0])
    s = {i[0] for i in suite(fam)}
    it = [x for x in it if x[0] not in s]
    return it[1::2] if part == "final" else it[::2]


def wrong(fam, ans, prompt, rng):
    if is_numeric(fam):
        v = float(ans)
        d = rng.choice([1, 2, 10, -1, -2, -10])
        w = v + d
        return str(int(w)) if w == int(w) else str(w)
    n = len(re.findall(r"(?m)^[A-P]\) ", prompt))
    return rng.choice([c for c in H.LETTERS[:max(n, 2)] if c != ans])


def other_family(fam):
    fams = CFG["families"]
    return fams[(fams.index(fam) + 1) % len(fams)]


def _rows(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def supplied(path):
    """(prompt, completion) for fine-tuning; files without a completion field train on the answer."""
    return [(r["prompt"], str(r.get("completion", r["answer"]))) for r in _rows(path)]


def supplied_rl(path):
    """(prompt, answer, meta) tasks for RL."""
    out = []
    for r in _rows(path):
        m = r.get("meta") or {}
        out.append((r["prompt"], str(r["answer"]), {"names": m["names"], "solution": m["solution"]} if "names" in m else None))
    return out


def rl_rows(fam, cond, part, base_file=None):
    """Environment tasks (prompt, answer, meta) for an RL condition, built from the family's reference material:
    clean, pool<N> (first N tasks), off<N> (N% replaced by another family's tasks, graded by their own rule),
    noise<N> (same tasks; the grader flips N% of rewards, see Env5), placebo (clean tasks; rewards shuffled in GRPO)."""
    rng = random.Random(zlib.crc32(f"rl|{fam}|{part}|{base_file}".encode()))  # one task order per family, every condition
    if base_file:
        base = supplied_rl(base_file)
    else:
        base = [(p, a, None) for p, a, _ in pool(fam, part)]
        rng.shuffle(base)
        base = base[:CFG["material_items"]]
    m = re.fullmatch(r"pool(\d+)", cond)
    if m:
        return base[:int(m.group(1))]
    m = re.fullmatch(r"off(\d+)", cond)
    if m:
        k = int(int(m.group(1)) / 100 * len(base))
        of = CFG.get("rl_off_family", "ag_news") if base_file else other_family(fam)
        ot = list(pool(of, part))
        rng.shuffle(ot)
        okind = kind(of)
        return base[:len(base) - k] + [(p, a, {"kind": okind}) for p, a, _ in ot[:k]]
    return base


def material(fam, cond, part, name=None):
    """(prompt, completion) rows. Material is fixed per condition and part, not per seed."""
    rows = _material(fam, cond, part, name or cond)
    return _worked(fam, rows, random.Random(zlib.crc32(f"worked|{fam}|{cond}|{part}".encode())))


def _material(fam, cond, part, name):
    if cond.startswith("file:"):
        return supplied(cond[5:])
    if cond.startswith("wrong:file:"):  # all-wrong: every completion replaced by a wrong one (letter: another option;
        rows = supplied(cond[11:])          # number and K&K: another row's whole completion with a different answer)
        rng = random.Random(zlib.crc32(f"wrong|{name}|{cond}".encode()))
        if kind(fam) == "letter":
            return [(p, wrong(fam, a, p, rng)) for p, a in rows]
        ans = [x[1] for x in supplied_rl(cond[11:])]
        out = []
        for i, (p, _) in enumerate(rows):
            j = rng.randrange(len(rows))
            while ans[j] == ans[i] and len(set(ans)) > 1:
                j = rng.randrange(len(rows))
            out.append((p, rows[j][1]))
        return out
    if cond.startswith("shuffle:file:"):  # completions shuffled across rows (placebo); seeded by the material's name too,
        rows = supplied(cond[13:])          # so two arms built from the same file never get the same rows
        rng = random.Random(zlib.crc32(f"shuffle|{name}|{cond}".encode()))
        ans = [a for _, a in rows]
        rng.shuffle(ans)
        return [(p, a) for (p, _), a in zip(rows, ans)]
    rng = random.Random(zlib.crc32(f"{fam}|{cond}|{part}".encode()))
    it = list(pool(fam, part))
    rng.shuffle(it)
    n = CFG["material_items"]
    base = it[:n]
    m = re.fullmatch(r"wrong(\d+)", cond)
    if m:
        k = int(m.group(1)) / 100
        return [(p, wrong(fam, a, p, rng) if rng.random() < k else a) for p, a, _ in base]
    m = re.fullmatch(r"off(\d+)", cond)
    if m:
        k = int(int(m.group(1)) / 100 * n)
        ot = list(pool(other_family(fam), part))
        rng.shuffle(ot)
        return [(p, a) for p, a, _ in base[:n - k]] + [(p, a) for p, a, _ in ot[:k]]
    m = re.fullmatch(r"pool(\d+)", cond)
    if m:
        return [(p, a) for p, a, _ in base[:int(m.group(1))]]
    if cond == "drop":
        c = sorted({a for _, a, _ in it})
        keep = set(c[:max(1, len(c) // 2)])
        return [(p, a) for p, a, _ in [x for x in it if x[1] in keep][:n]]
    if cond == "placebo":
        ans = [a for _, a, _ in base]
        rng.shuffle(ans)
        return [(p, a) for (p, _, _), a in zip(base, ans)]
    return [(p, a) for p, a, _ in base]


class Env5:
    """A family's material as an environment: the grader checks the reply's answer (letter, number or K&K roles).
    noise<N>: the grader flips each reward with probability N%, from its own seeded stream."""

    def __init__(self, fam, rows, cond="clean"):
        from touchstone.env import Task
        self.fam, self.cond = fam, cond
        self.name = f"{fam}_{cond}"
        m = re.fullmatch(r"noise(\d+)", cond)
        self.noise = int(m.group(1)) / 100 if m else 0.0
        self.rng = random.Random(zlib.crc32(self.name.encode()))
        self._t = [Task(p, {"answer": a, "meta": meta}) for p, a, meta in rows]

    def tasks(self):
        return self._t

    def verify(self, task, output):
        r = float(correct(self.fam, output, task.meta["answer"], task.meta["meta"]))
        if self.noise and self.rng.random() < self.noise:
            r = 1.0 - r
        return r


def commit():
    if os.environ.get("TS_COMMIT"):  # the GPU copy has no .git; the runner passes the commit it was synced from
        return os.environ["TS_COMMIT"]
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or None
    except Exception:
        return None


def one(job):
    import torch
    from touchstone import lm as L
    from touchstone.grpo import grpo
    t_wall = time.time()
    fam, size, seed, arm = job["family"], job["size"], int(job["seed"]), job["arm"]
    register(job)
    part = job.get("part", "dev")
    rc = {**CFG["recipe"], **job.get("recipe", {})}
    max_new = rc.pop("max_new")
    eval_batch = rc.pop("eval_batch", 32)
    rc_soft = rc.pop("soft", True)  # chance-corrected soft score before and after (scripts/h5_soft.py), same items and replies
    it = suite(fam)
    letter = kind(fam) == "letter"
    gates = {"suite": H.balance(it) if letter else None}
    out = {"job": job, "recipe": {**rc, "max_new": max_new}, "commit": commit()}
    rows = None
    if arm.startswith("sft"):
        rows = material(fam, job["material"], part, job.get("material_name"))
    gate_rows = rows if rows is not None else ([(p, a) for p, a, _ in rl_rows(fam, "clean", part, job.get("base_file"))] if arm.startswith("rl") else None)
    if letter and gate_rows:
        gates["material"] = H.balance([(p, a, 1 / max(2, len(re.findall(r'(?m)^[A-P]\) ', p)))) for p, a in gate_rows])
    out["gates"] = gates
    must = [gates["suite"]] if gates["suite"] else []
    if gates.get("material") and (job["material"] in ("clean",) or job["material"].startswith("file:") or arm.startswith("rl")):
        must.append(gates["material"])
    if any(not g["ok"] for g in must):
        out["refused"] = "class-balance gate"
        print("RESULT " + json.dumps(out), flush=True)
        return
    if arm in ("rl", "rltr") and job.get("rlgate_result"):  # RL trains only where the pre-training gate passed
        gp = Path(job["rlgate_result"])
        for _ in range(240):  # the gate job for this family and rung runs first; wait for it if it is still running
            if gp.exists():
                break
            time.sleep(5)
        g = json.loads(gp.read_text())
        rg = CFG.get("rl_gate", {"kappa_min": 0.10, "reward_max": 0.90})
        ok = g.get("kappa") is not None and g["kappa"] >= rg["kappa_min"] and g["reward_rate"] <= rg["reward_max"]
        out["rl_gate"] = {k: g.get(k) for k in ("reward_rate", "chance", "kappa", "truncated", "no_answer")}
        if not ok:
            out["skipped"] = "rl gate failed before training"
            print("RESULT " + json.dumps(out), flush=True)
            return
    torch.cuda.reset_peak_memory_stats() if torch.cuda.is_available() else None
    if arm == "rlgate":  # RL gate, before any training: reward at temperature 1 on 64 material prompts
        lm = L.LM(size)
        rng = random.Random(zlib.crc32(f"rlgate|{fam}|{part}".encode()))
        rs = rl_rows(fam, "clean", part, job.get("base_file"))
        prompts = [rs[rng.randrange(len(rs))] for _ in range(CFG.get("rl_gate_prompts", 64))]
        pick = [x for x in prompts for _ in range(rc["rl_group"])]  # a group of rollouts per prompt, as in training
        outs = lm.generate([x[0] for x in pick], max_new=max_new, temperature=1.0, batch=64)
        r = sum(correct(fam, o, a, meta) for o, (_, a, meta) in zip(outs, pick)) / len(pick)
        if kind(fam) == "number":
            ch = 0.0
        elif kind(fam) == "kk":  # guessing each person's role: 2^-people
            ch = sum(0.5 ** len(meta["names"]) for _, _, meta in pick) / len(pick)
        else:
            ch = sum(1 / max(2, len(re.findall(r"(?m)^[A-P]\) ", x[0]))) for x in pick) / len(pick)
        cut = sum(len(lm.tok(o, add_special_tokens=False).input_ids) >= max_new - 1 for o in outs) / len(pick)
        no_ans = sum(not has_answer(fam, o, meta) for o, (_, _, meta) in zip(outs, pick)) / len(pick)
        out.update({"reward_rate": round(r, 4), "chance": round(ch, 4), "kappa": round((r - ch) / (1 - ch), 4) if ch < 1 else None,
                    "truncated": round(cut, 4), "no_answer": round(no_ans, 4), "n": len(pick), "prompts": len(prompts), "sample": outs[:3], "wall_s": round(time.time() - t_wall, 1),
                    "model": L.LADDER[size]})
        print("RESULT " + json.dumps(out), flush=True)
        return
    t_load = time.time()
    lm = L.LM(size)
    load_s = time.time() - t_load
    t = time.time()
    import h5_soft
    # The untrained model's evaluation is the same for every run of a family at a rung (greedy, same items, same batches),
    # so it is computed once and reused. The cache key covers everything it depends on.
    ck = hashlib.sha256(json.dumps([L.LADDER[size], str(L.dtype_for(size)), max_new, eval_batch, rc_soft, [x[:2] for x in it]]).encode()).hexdigest()[:16]
    cdir = Path(os.environ.get("H5_BASE_CACHE", ROOT / "out" / "h5_basecache"))
    cf = cdir / f"{fam}|{size}|{ck}.json"
    if cf.exists():
        c = json.loads(cf.read_text())
        outs_b, soft_b = c["outs"], c["soft"]
    else:
        outs_b = lm.generate([x[0] for x in it], max_new=max_new, batch=eval_batch)
        soft_b = h5_soft.mean_soft(h5_soft.soft_scores(lm, it, outs_b)) if rc_soft else None
        cdir.mkdir(parents=True, exist_ok=True)
        tmp = cdir / f".{os.getpid()}.tmp"
        tmp.write_text(json.dumps({"outs": outs_b, "soft": soft_b, "model": L.LADDER[size], "family": fam, "max_new": max_new}))
        tmp.replace(cf)
    out["base_cached"] = cf.name
    b = "".join("1" if correct(fam, o, x[1], x[3] if len(x) > 3 else None) else "0" for o, x in zip(outs_b, it))
    eval_s = time.time() - t
    cut_b = sum(len(lm.tok(o, add_special_tokens=False).input_ids) >= max_new - 1 for o in outs_b) / len(it)
    out.update({"soft_base": None if soft_b is None else round(soft_b, 6)})
    out.update({"base": b, "base_acc": round(100 * b.count("1") / len(it), 2), "base_truncated": round(cut_b, 4),
                "base_sample": outs_b[:3], "chance": round(100 * sum(x[2] for x in it) / len(it), 2), "suite_n": len(it)})
    if arm != "base":
        variant = {"sfttr": {"sft_steps": rc["trunc_steps"]}, "rltr": {"rl_steps": rc["rl_trunc_steps"]}}.get(arm, {})
        keys = {k: rc[k] for k in ("lora_r", "lora_alpha", "sft_lr", "sft_batch", "sft_steps", "sft_max_len", "rl_lr",
                                   "rl_steps", "rl_prompts", "rl_group", "rl_kl") if k in rc}
        rec = L.Recipe(**{**keys, **variant}, rl_max_new=max_new, eval_max_new=max_new)
        t = time.time()
        if arm.startswith("sft"):
            pairs = [(lm.chat(p), a) for p, a in rows]
            tuned, info = L.sft(lm, pairs, rec, seed=seed)
            extra = {"loss_first": info["loss_first"], "loss_last": info["loss_last"]}
        else:
            cond = job.get("material_name") or job["material"]
            env = Env5(fam, rl_rows(fam, "clean" if cond == "placebo" else cond, part, job.get("base_file")), cond)
            tuned, info = grpo(lm, env, rec, seed=seed, placebo=job["material"] == "placebo")
            extra = {"reward_first": info["train_reward_first"], "reward_last": info["train_reward_last"], "skipped": info["skipped_no_signal"],
                     "rollouts_truncated": info.get("rollouts_truncated"), "mixed_groups": info.get("mixed_groups"), "curve": info.get("curve")}
        train_s = time.time() - t
        outs_a = tuned.generate([x[0] for x in it], max_new=max_new, batch=eval_batch)
        a = "".join("1" if correct(fam, o, x[1], x[3] if len(x) > 3 else None) else "0" for o, x in zip(outs_a, it))
        cut_a = sum(len(lm.tok(o, add_special_tokens=False).input_ids) >= max_new - 1 for o in outs_a) / len(it)
        soft_a = h5_soft.mean_soft(h5_soft.soft_scores(tuned, it, outs_a)) if rc_soft else None
        if soft_a is not None and soft_b is not None:
            out.update({"soft_after": round(soft_a, 6), "soft_gain": round(100 * (soft_a - soft_b), 4)})
        out.update({"after": a, "after_acc": round(100 * a.count("1") / len(it), 2), "after_truncated": round(cut_a, 4),
                    "gain": round(100 * (a.count("1") - b.count("1")) / len(it), 3), "train_s": round(train_s, 1),
                    "material_n": len(rows) if rows is not None else len(env.tasks()), "sample": outs_a[:3], **extra})
    out.update({"load_s": round(load_s, 1), "eval_s": round(eval_s, 1), "wall_s": round(time.time() - t_wall, 1),
                "peak_mem_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2) if torch.cuda.is_available() else None,
                "platform": f"{L.device()}|torch {torch.__version__.split('+')[0]}|{torch.cuda.get_device_name(0) if torch.cuda.is_available() else ''}",
                "model": L.LADDER[size], "dtype": str(L.dtype_for(size)).replace("torch.", "")})
    print("RESULT " + json.dumps(out), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "one":
        one(json.loads(sys.argv[2]))
