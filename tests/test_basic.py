import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone import env as envmod  # noqa: E402
from touchstone import heldout, probes, redundancy  # noqa: E402
from touchstone.forecast import forecast, spearman  # noqa: E402
from touchstone.appraise import grade  # noqa: E402

ENVS = ROOT / "envs"


def load(name):
    return envmod.load(ENVS / name)


def test_seal_is_content_addressed(tmp_path):
    a = envmod.seal(ENVS / "northwind_arith", tmp_path)
    b = envmod.seal(ENVS / "northwind_arith", tmp_path)
    assert a["sha256"] == b["sha256"]
    assert load_from(a).name == "Northwind Arithmetic Pro"


def load_from(manifest):
    return envmod.load(manifest["vault_path"])


def test_static_probes_catch_bad_graders():
    assert probes.hackability(load("northwind_arith"))["score"] == 0
    assert probes.hackability(load("shapeonly_arith"))["score"] > 0.3
    assert probes.hackability(load("hintleak_arith"))["score"] == 1.0
    assert probes.grader_reliability(load("northwind_arith"))["ok"]


def test_redundancy_and_contamination():
    public = load("public_arith")
    assert redundancy.redundancy(load("clone_arith"), [public])["public_overlap"] >= 0.8
    assert redundancy.redundancy(load("mirror_strings"), [public])["public_overlap"] == 0
    held = [t for ts in heldout.suite().values() for t in ts]
    for name in ["northwind_arith", "mirror_strings", "quickgrade_arith"]:
        assert redundancy.contamination(load(name), held) == 0


def test_forecast_recovers_a_clean_trend():
    params = [10_000, 100_000, 1_000_000]
    base = [[0] * 100 for _ in params]
    tuned = [[1] * k + [0] * (100 - k) for k in (2, 4, 6)]
    f = forecast(params, base, tuned, target_params=10_000_000, n_boot=50)
    assert abs(f["forecast"] - 8.0) < 1e-6
    assert spearman([1, 2, 3], [10, 20, 30]) == 1.0


def test_grade_caps():
    assert grade(10, 0.0, 0, 0, False)[0] == "A"
    assert grade(10, 0.5, 0, 0, False)[0] == "D"
    assert grade(10, 0.0, 0, 0.9, False)[0] == "C"
    assert grade(-3, 0.5, 0, 0, False)[0] == "F"
