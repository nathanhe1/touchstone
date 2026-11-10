"""The h5 scorer on synthetic run files: every path a real h5 scoring can take (pass, fail, abstain, RL gate, soft signal,
hash refusal, no overwrite). Synthetic numbers exist only in this test."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import h5_score as S  # noqa: E402

MATS = ["m1", "m2", "m3", "m4", "m5"]
FAMS = ["fa", "fb", "fc", "fd"]


def _runs(arm, rungs, truth, noise=0.0, soft_scale=1.0, gate=True):
    """truth[f][m] = target gain; proxies get the same order (a perfect forecast) unless noise flips it."""
    R = {}
    for f in FAMS:
        for seed in (0, 1):
            for m in MATS + ["wrong100", "placebo"]:
                t = truth[f].get(m, -10.0 if m == "wrong100" else 1.0)
                for role, size in rungs.items():
                    g = t + (0.3 if seed else -0.3) + (noise if role == "p12" and m == "m1" else 0.0)
                    if role != "target" and m == "wrong100" and not gate:
                        g = t + 30.0  # all-wrong does as well as clean: the gate must fail
                    R[f"{arm}|{f}|{m}|{size}|{seed}"] = {"gain": g, "soft_gain": soft_scale * g, "base": "0110" * 25}
    return R


def _cfg(kind, rungs):
    fams = {f: {"passing": MATS, "failing": ["wrong100"], "gate_ref": "m1", "gate_wrong": "wrong100"} for f in FAMS}
    return {"arms": {kind: {"kind": kind, "run_arm": "sft" if kind == "ft" else "rl", "rungs": rungs, "families": fams}}}


def _gates(rl=None):
    bal = {"max_share": 0.6, **{f: {"suite": 0.5, "materials": {m: 0.5 for m in MATS}} for f in FAMS}}
    return {"balance": bal, "rl": rl or {}}


RUNGS = {"p12": "0.6B", "p4": "1.7B", "target": "8B"}
TRUTH = {f: {m: float(10 - 2 * i) for i, m in enumerate(MATS)} for f in FAMS}


def _score(tmp_path, R, cfg, G, mode="dry", extra=()):
    d = tmp_path / "runs"
    d.mkdir(exist_ok=True)
    (d / "h5_ft.json").write_text(json.dumps(R))
    (d / "h5_gates.json").write_text(json.dumps(G))
    c = tmp_path / "cfg.json"
    c.write_text(json.dumps(cfg))
    return S.main([mode, "--config", str(c), "--runs", str(d), "--out", str(tmp_path / "res.json"), *extra])


def test_perfect_forecast_passes_and_soft_signal_is_scored(tmp_path):
    res = _score(tmp_path, _runs("sft", RUNGS, TRUTH), _cfg("ft", RUNGS), _gates())
    X = res["arms"]["ft"]
    assert X["noise_ceiling"]["screen_passing"] == 1.0
    for name in S.CANDIDATES:
        c = X["candidates"][name]
        assert c["screen_passing"]["decision"] == 1.0 and c["screen_passing"]["pairs"] == 40
        assert c["verdict"] == "pass", (name, c["verdict"])
    assert X["comparisons"]["C1 acc_final 4x vs B acc_final 12x"]["difference"] == 0.0


def test_a_wrong_signal_fails_and_is_retired(tmp_path):
    R = _runs("sft", RUNGS, TRUTH)
    for k, r in R.items():  # reverse the 12x proxy's order: the baseline and C2 must fail
        if "|0.6B|" in k and k.split("|")[2] in MATS:
            r["gain"] = 20 - r["gain"]
            r["soft_gain"] = 20 - r["soft_gain"]
    X = _score(tmp_path, R, _cfg("ft", RUNGS), _gates())["arms"]["ft"]
    assert X["candidates"]["B acc_final 12x"]["verdict"] == "fail: retired"
    assert X["candidates"]["C2 soft 12x"]["verdict"] == "fail: retired"
    assert X["candidates"]["C1 acc_final 4x"]["verdict"] == "pass"
    cmp = X["comparisons"]["C1 acc_final 4x vs B acc_final 12x"]
    # 4 families: a family-level sign-flip test cannot go below 1/16, so "beats" cannot be shown (METHOD.md, h5)
    assert cmp["difference"] == 1.0 and not cmp["beats_baseline"] and cmp["p_one_sided"] > 0.05


def test_ft_gate_abstains_and_coverage_makes_it_inconclusive(tmp_path):
    X = _score(tmp_path, _runs("sft", RUNGS, TRUTH, gate=False), _cfg("ft", RUNGS), _gates())["arms"]["ft"]
    for name in S.CANDIDATES:
        c = X["candidates"][name]
        assert c["covered"] == [] and set(c["abstained"]) == set(FAMS)
        assert c["verdict"].startswith("inconclusive: coverage")


def test_class_balance_drops_family_and_material(tmp_path):
    G = _gates()
    G["balance"]["fa"]["suite"] = 0.9
    G["balance"]["fb"]["materials"]["m5"] = 0.95
    X = _score(tmp_path, _runs("sft", RUNGS, TRUTH), _cfg("ft", RUNGS), G)["arms"]["ft"]
    assert "fa" in X["abstained_families"]
    assert "m5" in X["gates"]["fb"]["excluded_materials"]
    assert X["candidates"]["B acc_final 12x"]["screen_passing"]["pairs"] == 10 + 6 + 10  # fb loses m5's 4 pairs


def test_headroom_gate(tmp_path):
    R = _runs("sft", RUNGS, TRUTH)
    for k, r in R.items():
        if k.startswith("sft|fd|") and "|8B|" in k:
            r["base"] = "1" * 95 + "0" * 5
    X = _score(tmp_path, R, _cfg("ft", RUNGS), _gates())["arms"]["ft"]
    assert any("no headroom" in w for w in X["abstained_families"]["fd"])


def test_low_ceiling_is_inconclusive(tmp_path):
    R = _runs("sft", RUNGS, TRUTH)
    rng = __import__("random").Random(1)
    for k, r in R.items():  # target seeds disagree with each other
        if "|8B|" in k:
            r["gain"] = rng.uniform(-5, 5)
    X = _score(tmp_path, R, _cfg("ft", RUNGS), _gates())["arms"]["ft"]
    assert X["arm_inconclusive"]
    assert all(c["verdict"].startswith("inconclusive: target noise ceiling") for c in X["candidates"].values())


def test_rl_gate(tmp_path):
    rungs = {"p12": "0.6B", "p4": "1.7B", "target": "4B"}
    rl = {}
    for f in FAMS:
        rl[f"{f}|4B"] = {"reward_rate": 0.6, "chance": 0.25, "truncated": 0.0}
        rl[f"{f}|1.7B"] = {"reward_rate": 0.5, "chance": 0.25, "truncated": 0.02}
        rl[f"{f}|0.6B"] = {"reward_rate": 0.27, "chance": 0.25, "truncated": 0.0}  # guessing: kappa 0.03
    rl["fd|1.7B"]["truncated"] = 0.4
    X = _score(tmp_path, _runs("rl", rungs, TRUTH), _cfg("rl", rungs), _gates(rl))["arms"]["rl"]
    assert X["candidates"]["B acc_final 12x"]["covered"] == []
    assert X["candidates"]["C1 acc_final 4x"]["covered"] == ["fa", "fb", "fc"]
    assert "truncated" in X["candidates"]["C1 acc_final 4x"]["abstained"]["fd"][0]


def test_final_refuses_bad_hash_and_second_scoring(tmp_path):
    R, cfg, G = _runs("sft", RUNGS, TRUTH), _cfg("ft", RUNGS), _gates()
    _score(tmp_path, R, cfg, G)  # writes runs and config
    man = tmp_path / "h.sha256"
    c = tmp_path / "cfg.json"
    rel = c.relative_to(S.ROOT) if str(c).startswith(str(S.ROOT)) else None
    if rel is None:  # the hash file names repo-relative paths; point one at a missing file to force a mismatch
        man.write_text("0" * 64 + "  out/does_not_exist.json\n")
        with pytest.raises(SystemExit):
            S.main(["final", "--config", str(c), "--runs", str(tmp_path / "runs"), "--out", str(tmp_path / "final.json"), "--hashes", str(man)])
    good = tmp_path / "ok.sha256"
    target = S.ROOT / "scripts" / "h5_score.py"
    good.write_text(hashlib.sha256(target.read_bytes()).hexdigest() + "  scripts/h5_score.py\n")
    S.main(["final", "--config", str(c), "--runs", str(tmp_path / "runs"), "--out", str(tmp_path / "final.json"), "--hashes", str(good)])
    with pytest.raises(SystemExit):
        S.main(["final", "--config", str(c), "--runs", str(tmp_path / "runs"), "--out", str(tmp_path / "final.json"), "--hashes", str(good)])
