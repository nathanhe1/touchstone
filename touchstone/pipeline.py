"""The appraisal pipeline on real open models (what `touchstone appraise` runs).

    dataset: validate -> overlap checks -> SFT at each rung (+ shuffled-answer placebo)
             -> held-out gains -> forecast at the target size -> flags, grade, fair value
    env:     validate -> grader audit -> GRPO at each rung (+ shuffled-reward placebo)
             -> held-out gains and env reward -> forecast -> flags, grade, fair value
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import data as datamod
from . import env as envmod
from . import forecast as fc
from . import lm as L
from . import measure, overlap, probes, suites, valuation

ROOT = Path(__file__).resolve().parents[1]
CALIB_DIR = Path(__file__).resolve().parent / "calibration"
CACHE = Path.home() / ".cache" / "touchstone"
GSM8K_URL = "https://raw.githubusercontent.com/openai/grade-school-math/master/grade_school_math/data/train.jsonl"


@dataclass
class Plan:
    mode: str
    rungs: list[str]
    seeds: dict[str, int]
    suite_items: int
    placebo: bool = True
    recipe: L.Recipe = field(default_factory=L.Recipe)
    backend: str = "mps"  # "mps", "cpu" (PyTorch) or "mlx"


def plan_for(quick: bool, kind: str) -> Plan:
    """Quick and full use the same training recipe as the calibration sweep, so the
    calibrated maps apply. Quick trains only the smallest rung (one seed) and
    forecasts 1.7B from it; full trains 135M and 360M (two seeds each), forecasts
    from 360M, and also measures 1.7B directly."""
    if quick:
        # Environments have no calibration sweep, so quick RL can use a lighter recipe (30 steps, groups of 4).
        rec = L.Recipe(rl_steps=30, rl_group=4) if kind == "env" else L.Recipe()
        return Plan("quick", ["135M"], {"135M": 1}, 120, True, rec)
    return Plan("full", ["135M", "360M", "1.7B"], {"135M": 2, "360M": 2, "1.7B": 1}, 200, True, L.Recipe())


def stage(log, name: str, progress: float):
    """Machine-readable progress marker, parsed by the API server (touchstone/server.py)."""
    log(f"@stage {name} {progress:.3f}")


# ---------------------------------------------------------------- backends

def select_backend(device: str, kind: str) -> str:
    """--device: auto|mps|cpu (PyTorch) or mlx (Apple MLX, dataset appraisals only)."""
    if device == "mlx":
        try:
            import mlx.core  # noqa: F401
            import mlx_lm  # noqa: F401
        except ImportError:
            print("WARNING: mlx / mlx-lm not installed; using PyTorch on the Apple GPU instead.", flush=True)
            return L.set_device("auto")
        if kind == "env":
            print("NOTE: GRPO runs on PyTorch MPS; --device mlx applies to dataset appraisals.", flush=True)
            return L.set_device("auto")
        return "mlx"
    return L.set_device(device)


def new_lm(plan: Plan, size: str):
    if plan.backend == "mlx":
        from .mlx_backend import MLXLM
        return MLXLM(size)
    return L.LM(size)


def fresh(plan: Plan, tuned):
    """The base model again, adapter removed, for the next training run."""
    if plan.backend == "mlx":
        from .mlx_backend import reload
        return reload(tuned)
    return L.drop_lora(tuned)


# ---------------------------------------------------------------- helpers

def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    files = sorted(x for x in p.rglob("*") if x.is_file() and "__pycache__" not in x.parts) if p.is_dir() else [p]
    for f in files:
        h.update(str(f.relative_to(p) if p.is_dir() else f.name).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def _suite_key(suite: suites.Suite) -> str:
    h = hashlib.sha256("\n".join(i.prompt + "\t" + i.answer for i in suite.items).encode()).hexdigest()
    return f"{suite.name}-{len(suite.items)}-{h[:12]}"


def base_eval(lm: L.LM, suite: suites.Suite, max_new: int) -> dict:
    """Base-model scores are deterministic (greedy), so cache them across appraisals."""
    tag = "" if getattr(lm, "dev", "mps") != "mlx" else "-mlx"
    f = CACHE / "base_evals" / f"{lm.size}{tag}-{_suite_key(suite)}-{max_new}.json"
    if f.exists():
        return json.loads(f.read_text())
    ev = measure.evaluate(lm, suite, max_new)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(ev))
    return ev


def public_baseline(spec: str | None, suite_name: str) -> tuple[list[str], str]:
    """Prompts of the free public data to compare against, and a label."""
    if spec:
        p = Path(spec)
        if p.is_dir() or p.suffix == ".py":
            e = envmod.load(p)
            return [t.prompt for t in e.tasks()], f"environment {p.name}"
        return [e.prompt_text for e in datamod.load_dataset(p)], f"dataset {p.name}"
    if suite_name == "word_math":
        cache = CACHE / "gsm8k_train.jsonl"
        if not cache.exists():
            import urllib.request
            cache.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(GSM8K_URL, cache)
        return [json.loads(x)["question"] for x in cache.read_text().splitlines()], "GSM8K train (7,473 public problems)"
    if suite_name == "arithmetic":
        e = envmod.load(ROOT / "envs" / "public_arith")
        return [t.prompt for t in e.tasks()], "Public Addition (free) environment"
    return [], "none (no public baseline for this domain; pass --public)"


def calibration(suite_name: str, kind: str) -> dict | None:
    f = CALIB_DIR / f"{kind}_{suite_name}.json"
    return json.loads(f.read_text()) if f.exists() else None


def _avg(lists: list[list[float]]) -> list[float]:
    return [sum(v) / len(v) for v in zip(*lists)]


# ---------------------------------------------------------------- core loop

def run_ladder(train_fn, plan: Plan, suite: suites.Suite, clean_idx: list[int], log, extra_eval=None) -> dict:
    """train_fn(lm, seed, placebo) -> (tuned_lm, info). Returns per-rung measurements."""
    rungs = {}
    total = sum(plan.seeds[s] for s in plan.rungs) * (2 if plan.placebo else 1)
    done = 0
    for size in plan.rungs:
        t0 = time.time()
        lm = new_lm(plan, size)
        before = base_eval(lm, suite, plan.recipe.eval_max_new)
        log(f"  {size}: base accuracy {100 * measure.mean(before['acc']):.1f}%  "
            f"candidate prob {100 * measure.mean(before['cand']):.1f}%")
        arms = {"material": [], "placebo": []}
        infos = {"material": [], "placebo": []}
        extras = {"material": [], "placebo": []}
        for seed in range(plan.seeds[size]):
            for arm in (["material", "placebo"] if plan.placebo else ["material"]):
                stage(log, "train", 0.15 + 0.75 * done / total)
                tuned, info = train_fn(lm, seed, arm == "placebo")
                stage(log, "measure", 0.15 + 0.75 * (done + 0.6) / total)
                ev = measure.evaluate(tuned, suite, plan.recipe.eval_max_new)
                done += 1
                if extra_eval:
                    extras[arm].append(extra_eval(tuned))
                arms[arm].append(ev)
                infos[arm].append(info)
                log(f"  {size} seed {seed} {arm:8s}: accuracy {100 * measure.mean(ev['acc']):.1f}%  "
                    f"candidate prob {100 * measure.mean(ev['cand']):.1f}%  ({info['seconds']:.0f}s train)")
                lm = fresh(plan, tuned)
        r = {"params": L.PARAMS[size], "seeds": plan.seeds[size], "before": measure.summary(before),
             "sample_outputs_before": before["samples"][:2], "reply_chars_before": before.get("reply_chars")}
        for arm, evs in arms.items():
            if not evs:
                continue
            acc, cand = _avg([e["acc"] for e in evs]), _avg([e["cand"] for e in evs])
            r[arm] = {
                "after": {"accuracy": round(100 * measure.mean(acc), 2), "candidate_prob": round(100 * measure.mean(cand), 2)},
                "acc_gain": measure.paired_gain(before["acc"], acc),
                "cand_gain": measure.paired_gain(before["cand"], cand),
                "acc_gain_clean": measure.paired_gain([before["acc"][i] for i in clean_idx], [acc[i] for i in clean_idx]),
                "acc_gain_by_seed": [round(100 * (measure.mean(e["acc"]) - measure.mean(before["acc"])), 2) for e in evs],
                "per_part": measure.per_part(suite, before["acc"], acc),
                "train": infos[arm],
                "sample_outputs": evs[0]["samples"][:2],
                "reply_chars": round(sum(e.get("reply_chars", 0) for e in evs) / len(evs), 1),
                "_acc": acc, "_cand": cand,
            }
            if extras[arm]:
                r[arm]["extra"] = extras[arm]
        if plan.placebo:
            m, p = r["material"], r["placebo"]
            # Net = material minus the placebo's gain, but only when the placebo helps: shuffled answers
            # often *hurt*, and subtracting a loss would credit the material for merely not being wrong.
            r["net"] = {k: (measure.paired_gain(p[f"_{k}"], m[f"_{k}"]) if p[f"{k}_gain"]["gain"] > 0
                            else dict(m[f"{k}_gain"])) for k in ("acc", "cand")}
        for arm in arms:
            if arm in r:
                r[arm].pop("_acc"), r[arm].pop("_cand")
        r["seconds"] = round(time.time() - t0)
        rungs[size] = r
        del lm
        L.free_memory()
    return rungs


def make_forecast(rungs: dict, plan: Plan, calib: dict | None) -> dict:
    """Forecast the material's and the placebo's gain at the target size; net = difference."""
    small = [s for s in L.SMALL if s in rungs]
    largest = small[-1]
    out = {"target": L.TARGET, "target_params": L.PARAMS[L.TARGET]}
    arms = ["material", "placebo"] if plan.placebo else ["material"]
    cmap = (calib or {}).get("maps", {}).get(largest)
    if cmap:
        for arm in arms:
            g = {largest: {"acc": rungs[largest][arm]["acc_gain"]["gain"], "cand": rungs[largest][arm]["cand_gain"]["gain"]}}
            out[arm] = fc.calibrated_forecast(g, cmap, (largest,))
        v = cmap["validation"]["methods"]["calibrated"]
        out["method"] = f"calibrated from {largest}"
        out["method_note"] = (f"Calibrated {largest} -> {L.TARGET} map fitted on {cmap['n']} reference datasets run at "
                              f"every size; leave-one-out on those: Spearman {v['spearman']}, decision accuracy "
                              f"{v['decision_accuracy']}, mean error {v['mae_pts']} pts. Range = the "
                              f"{int(100 * cmap['coverage'])}% leave-one-out error band.")
    else:
        # No calibration for this suite: rank at the largest trained small rung (DataDecide's default),
        # with an interval from evaluation noise and seed spread only.
        for arm in arms:
            gg = rungs[largest][arm]["acc_gain"]
            seeds = rungs[largest][arm]["acc_gain_by_seed"]
            spread = (max(seeds) - min(seeds)) / 2 if len(seeds) > 1 else 0.0
            hw = 1.645 * gg["se"] + spread
            out[arm] = {"method": "rank_largest", "point": gg["gain"], "lo": round(gg["gain"] - hw, 2),
                        "hi": round(gg["gain"] + hw, 2), "coverage": 0.9, "calibrated_on": 0}
        out["method"] = "rank_largest"
        out["method_note"] = (f"No calibration sweep exists for this suite, so the forecast is the gain measured at "
                              f"{largest} (the DataDecide default: rank at the largest affordable size). Treat it as a "
                              f"ranking signal; its scale at {L.TARGET} is not validated.")
    if plan.placebo:
        m, p = out["material"], out["placebo"]
        if p["point"] > 0:  # subtract only the gain the placebo itself would buy (see run_ladder)
            hw = (((m["hi"] - m["lo"]) / 2) ** 2 + ((p["hi"] - p["lo"]) / 2) ** 2) ** 0.5
            pt = m["point"] - p["point"]
        else:
            hw, pt = (m["hi"] - m["lo"]) / 2, m["point"]
        out["net"] = {"point": round(pt, 2), "lo": round(pt - hw, 2), "hi": round(pt + hw, 2)}
    else:
        out["net"] = dict(out["material"])
    out["headline"] = dict(out["net"], source="forecast")
    if L.TARGET in rungs:  # full mode trains the target size too: the measurement beats the forecast
        t = rungs[L.TARGET]
        n = t["net"]["acc"] if plan.placebo else t["material"]["acc_gain"]
        out["measured_at_target"] = {"material": t["material"]["acc_gain"]["gain"], "net": n["gain"]}
        out["headline"] = {"point": n["gain"], "lo": n["lo"], "hi": n["hi"], "source": "measured"}
    return out


def _measurable_and_harmful(rungs: dict, plan: Plan) -> tuple[bool, bool, str]:
    largest = plan.rungs[-1]
    g = rungs[largest]["net"]["acc"] if plan.placebo else rungs[largest]["material"]["acc_gain"]
    gc = rungs[largest]["net"]["cand"] if plan.placebo else rungs[largest]["material"]["cand_gain"]
    measurable = g["lo"] > 0 or (gc["lo"] > 0 and g["gain"] > 0)
    harmful = rungs[largest]["material"]["acc_gain"]["hi"] < 0 and g["hi"] < 0
    return measurable, harmful, largest


# ---------------------------------------------------------------- static screening (no training)

def screen_material(kind: str, prompts: list[str], suite, public: str | None, log=print, examples=None, env=None,
                    tasks=None, probe_size: str = "135M", label_model: str = "360M") -> dict:
    """Every red flag that needs no training run: overlap with the suite and public data, duplicates,
    off-topic share, label noise (datasets), grader audit and answer leakage (environments).
    Used by the full appraisal and by scripts/eval_flags.py, so the benchmark measures the product."""
    from . import screen
    contam = overlap.match(prompts, [i.prompt for i in suite.items])
    hit = overlap.match([i.prompt for i in suite.items], prompts)  # suite items found in the material
    contam["suite_share"] = hit["rate"]
    clean_idx = [i for i in range(len(suite.items)) if i not in set(hit["matched_idx"])] or list(range(len(suite.items)))
    pub_prompts, pub_label = public_baseline(public, suite.name)
    pub = overlap.match(prompts, pub_prompts, use_embeddings=len(prompts) * len(pub_prompts) < 5e7) if pub_prompts \
        else {"rate": 0.0, "examples": []}
    if kind == "dataset":
        dups = overlap.duplicates([p + "\n" + e.completion for p, e in zip(prompts, examples)])
    else:
        dups = overlap.duplicates(prompts)
    rel = screen.relevance(prompts, [i.prompt for i in suite.items])
    log(f"  overlap: {100 * hit['rate']:.1f}% of held-out items appear in the material ({100 * contam['rate']:.1f}% "
        f"of material), public ({pub_label}) {100 * pub['rate']:.1f}%, duplicates {100 * dups['dup_rate']:.1f}%, "
        f"off-topic {100 * rel['off_topic_share']:.0f}%")
    meas = {"contamination": max(contam["rate"], hit["rate"]), "public_overlap": pub["rate"],
            "dup_rate": dups["dup_rate"], "off_topic_share": rel["off_topic_share"]}
    out = {"contam": contam, "hit": hit, "clean_idx": clean_idx, "pub": pub, "pub_label": pub_label, "dups": dups,
           "relevance": rel, "meas": meas}
    if kind == "dataset":
        lm = L.LM(label_model) if suite.items and suite.items[0].match == "numeric" else None
        q = screen.screen_dataset(examples, suite, lm)
        del lm
        L.free_memory()
        out["label_quality"] = {k: q[k] for k in ("arithmetic", "plausibility") if k in q}
        if q["noisy"]:
            meas["noisy"] = out["label_quality"]
        log(f"  labels: arithmetic errors in {q['arithmetic']['rate'] if q['arithmetic']['rate'] is not None else 'n/a'} "
            f"of worked solutions; plausibility {q.get('plausibility', {}).get('mean')}")
    else:
        from .env import reference
        lm = L.LM(probe_size)
        audit = probes.audit_grader(env, tasks, lm)
        del lm
        L.free_memory()
        refs = [reference(env, t) for t in tasks[:500]]
        leak = screen.answer_leakage([t.prompt for t in tasks[:500]], refs)
        out["audit"], out["answer_leakage"] = audit, leak
        meas.update({"hackability": audit["score"], "worst_exploit": audit["worst_exploit"],
                     "grader_flagged": audit["flagged"], "answer_leakage": leak})
        log(f"  grader audit: worst exploit '{audit['worst_exploit']}' earns {100 * audit['score']:.0f}% reward; "
            f"answer in prompt for {100 * leak:.0f}% of tasks")
    return out


# ---------------------------------------------------------------- dataset

def appraise_dataset(path: str | Path, suite_spec: str, plan: Plan, public: str | None, dollars_per_point: float,
                     log=print) -> dict:
    t0 = time.time()
    path = Path(path)
    stage(log, "validate", 0.01)
    examples = datamod.load_dataset(path)
    suite = suites.get_suite(suite_spec).subset(plan.suite_items)
    log(f"Appraising dataset {path.name}: {len(examples)} examples; held-out suite '{suite.name}' "
        f"({len(suite.items)} items: {suite.domain}); mode {plan.mode}")

    stage(log, "seal", 0.04)
    stage(log, "overlap", 0.06)
    prompts = [e.prompt_text for e in examples]
    sc = screen_material("dataset", prompts, suite, public, log, examples=examples)
    contam, pub, pub_label, dups, clean_idx = sc["contam"], sc["pub"], sc["pub_label"], sc["dups"], sc["clean_idx"]

    plac = datamod.placebo(examples, seed=0)

    def train(lm, seed, placebo):
        ex = plac if placebo else examples
        if plan.backend == "mlx":
            from . import mlx_backend
            return mlx_backend.sft(lm, datamod.to_training_pairs(lm, ex), plan.recipe, seed=seed)
        return L.sft(lm, datamod.to_training_pairs(lm, ex), plan.recipe, seed=seed)

    rungs = run_ladder(train, plan, suite, clean_idx, log)
    stage(log, "forecast", 0.91)
    fcast = make_forecast(rungs, plan, calibration(suite.name, "dataset"))
    measurable, harmful, largest = _measurable_and_harmful(rungs, plan)
    meas = {"contamination": max(contam["rate"], hit["rate"]), "public_overlap": pub["rate"], "dup_rate": dups["dup_rate"],
            "measurable": measurable, "harmful": harmful}
    top = rungs[largest]
    rb, ra = top.get("reply_chars_before"), top["material"].get("reply_chars")
    if rb and ra is not None and ra < 0.4 * rb and top["material"]["acc_gain"]["gain"] < 0:
        meas["suppresses_reasoning"] = (rb, ra)
    stage(log, "price", 0.95)
    flags = valuation.flags_for(meas)
    g = valuation.grade(fcast["headline"]["point"], flags)
    value = valuation.fair_value(fcast["headline"]["point"], flags, dups["unique"], pub["rate"], dollars_per_point)
    return {
        "touchstone_version": "0.2",
        "kind": "dataset", "mode": plan.mode,
        "material": {"path": str(path), "name": path.stem, "sha256": sha256_path(path), "n_items": len(examples),
                     "unique_items": dups["unique"]},
        "heldout": _suite_info(suite, len(clean_idx)),
        "overlap": {"heldout": _strip(contam), "public": {**_strip(pub), "baseline": pub_label},
                    "duplicates": dups},
        "rungs": rungs, "forecast": fcast,
        "measurable_at": largest, "flags": flags, "grade": g,
        "fair_value": {**value, "dollars_per_point": dollars_per_point, "basis": f"net gain at {L.TARGET} ({fcast['headline']['source']})"},
        "models": {s: L.LADDER[s] for s in plan.rungs}, "recipe": asdict(plan.recipe),
        "runtime_s": round(time.time() - t0),
    }


def reforecast(r: dict) -> dict:
    """Recompute forecast, flags, grade and value of an existing report (e.g. after a new calibration).

    Uses only the measurements saved in report.json, so no model is retrained.
    """
    from .schema import public_report
    r = public_report(r)  # older reports: move overlap/forecast to *_detail
    plan = Plan(r["mode"], list(r["rungs"]), {s: g["seeds"] for s, g in r["rungs"].items()},
                r["heldout"]["n_items"], "placebo" in next(iter(r["rungs"].values())))
    r["forecast_detail"] = make_forecast(r["rungs"], plan, calibration(r["heldout"]["name"], r["kind"]))
    keep = [f for f in r["flags"] if f["code"] not in ("no_measurable_gain", "harmful")]
    measurable, harmful, _ = _measurable_and_harmful(r["rungs"], plan)
    extra = valuation.flags_for({"measurable": measurable, "harmful": harmful})
    r["flags"] = keep + extra
    hl = r["forecast_detail"]["headline"]
    r["grade"] = valuation.grade(hl["point"], r["flags"])
    fv = r["fair_value"]
    r["fair_value"] = {**valuation.fair_value(hl["point"], r["flags"], r["material"]["unique_items"],
                                             r["overlap_detail"]["public"]["rate"], fv["dollars_per_point"]),
                       "dollars_per_point": fv["dollars_per_point"], "basis": f"net gain at {L.TARGET} ({hl['source']})"}
    return public_report(r)


def _suite_info(suite, n_clean):
    return {"name": suite.name, "domain": suite.domain, "description": suite.description, "n_items": len(suite.items),
            "source": suite.source, "parts": {k: len(v) for k, v in suite.parts().items()},
            "n_items_untouched_by_material": n_clean}


def _strip(m: dict) -> dict:
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k != "matched_idx"}


# ---------------------------------------------------------------- environment

def appraise_env(path: str | Path, suite_spec: str | None, plan: Plan, public: str | None, dollars_per_point: float,
                 log=print) -> dict:
    t0 = time.time()
    path = Path(path)
    stage(log, "validate", 0.01)
    env = envmod.load(path)
    tasks = envmod.validate(env, path)
    suite_spec = suite_spec or getattr(env, "domain", None)
    if not suite_spec:
        raise envmod.EnvError(f"{path}: no held-out suite given; pass --suite or set ENV.domain")
    suite = suites.get_suite(suite_spec).subset(plan.suite_items)
    name = getattr(env, "name", path.name)
    log(f"Appraising environment {name}: {len(tasks)} tasks; held-out suite '{suite.name}' "
        f"({len(suite.items)} items: {suite.domain}); mode {plan.mode}")

    stage(log, "seal", 0.04)
    stage(log, "overlap", 0.06)
    prompts = [t.prompt for t in tasks]
    contam = overlap.match(prompts, [i.prompt for i in suite.items])
    hit = overlap.match([i.prompt for i in suite.items], prompts)
    clean_idx = [i for i in range(len(suite.items)) if i not in set(hit["matched_idx"])] or list(range(len(suite.items)))
    pub_prompts, pub_label = public_baseline(public, suite.name)
    pub = overlap.match(prompts, pub_prompts, use_embeddings=len(prompts) * len(pub_prompts) < 5e7) if pub_prompts \
        else {"rate": 0.0, "examples": []}
    dups = overlap.duplicates(prompts)
    contam["suite_share"] = hit["rate"]  # share of suite items leaked: what inflates held-out scores
    log(f"  overlap: {100 * hit['rate']:.1f}% of held-out items appear in the material ({100 * contam['rate']:.1f}% of material), public ({pub_label}) {100 * pub['rate']:.1f}%, "
        f"duplicates {100 * dups['dup_rate']:.1f}%")

    stage(log, "probe", 0.11)
    probe_lm = L.LM(plan.rungs[0])
    audit = probes.audit_grader(env, tasks, probe_lm)
    del probe_lm
    L.free_memory()
    log(f"  grader audit: worst exploit '{audit['worst_exploit']}' earns {100 * audit['score']:.0f}% reward")

    rng = random.Random(1)
    reward_sample = [rng.choice(tasks) for _ in range(64)]

    def env_reward(lm):
        outs = lm.generate([t.prompt for t in reward_sample], max_new=plan.recipe.rl_max_new,
                           system=getattr(env, "system", None))
        return round(sum(float(env.verify(t, o)) for t, o in zip(reward_sample, outs)) / len(outs), 4)

    from .grpo import grpo

    class _Env:  # restrict GRPO to the validated task list
        def __init__(self):
            self.system = getattr(env, "system", None)

        def tasks(self):
            return tasks

        def verify(self, t, o):
            return env.verify(t, o)

    wrapped = _Env()

    def train(lm, seed, placebo):
        return grpo(lm, wrapped, plan.recipe, seed=seed, placebo=placebo)

    rungs = run_ladder(train, plan, suite, clean_idx, log, extra_eval=env_reward)
    for size in plan.rungs:  # env reward before training, per rung (cheap, separate load)
        lm = L.LM(size)
        r = rungs[size]
        r["env_reward_before"] = env_reward(lm)
        del lm
        L.free_memory()
        for arm in ("material", "placebo"):
            if arm in r:
                r[arm]["env_reward_after"] = round(sum(r[arm].pop("extra")) / plan.seeds[size], 4)
    stage(log, "forecast", 0.91)
    fcast = make_forecast(rungs, plan, calibration(suite.name, "env"))
    measurable, harmful, largest = _measurable_and_harmful(rungs, plan)
    top = rungs[largest]
    reward_gain = 100 * (top["material"]["env_reward_after"] - top["env_reward_before"])
    heldout_gain = top["material"]["acc_gain"]
    transfer_gap = reward_gain >= 15 and heldout_gain["hi"] < reward_gain / 3 and heldout_gain["lo"] <= 0.5
    meas = {"hackability": audit["score"], "worst_exploit": audit["worst_exploit"], "grader_flagged": audit["flagged"],
            "contamination": max(contam["rate"], hit["rate"]), "public_overlap": pub["rate"], "dup_rate": dups["dup_rate"],
            "transfer_gap": transfer_gap, "measurable": measurable, "harmful": harmful}
    peak = max(max(rungs[s]["env_reward_before"], rungs[s]["material"]["env_reward_after"]) for s in plan.rungs)
    if peak < 0.02:  # every GRPO group had identical (zero) rewards: nothing to learn from at these sizes
        meas["no_signal"] = max(peak, 1e-4)
    stage(log, "price", 0.95)
    flags = valuation.flags_for(meas)
    g = valuation.grade(fcast["headline"]["point"], flags)
    value = valuation.fair_value(fcast["headline"]["point"], flags, dups["unique"], pub["rate"], dollars_per_point)
    return {
        "touchstone_version": "0.2",
        "kind": "env", "mode": plan.mode,
        "material": {"path": str(path), "name": name, "sha256": sha256_path(path), "n_items": len(tasks),
                     "unique_items": dups["unique"]},
        "heldout": _suite_info(suite, len(clean_idx)),
        "overlap": {"heldout": _strip(contam), "public": {**_strip(pub), "baseline": pub_label}, "duplicates": dups},
        "grader_audit": audit,
        "transfer_check": {"rung": largest, "env_reward_gain_pts": round(reward_gain, 2),
                           "heldout_gain_pts": heldout_gain["gain"], "transfer_gap": transfer_gap},
        "rungs": rungs, "forecast": fcast,
        "measurable_at": largest, "flags": flags, "grade": g,
        "fair_value": {**value, "dollars_per_point": dollars_per_point, "basis": f"net gain at {L.TARGET} ({fcast['headline']['source']})"},
        "models": {s: L.LADDER[s] for s in plan.rungs}, "recipe": asdict(plan.recipe),
        "runtime_s": round(time.time() - t0),
    }
