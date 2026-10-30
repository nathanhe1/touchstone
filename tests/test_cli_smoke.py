"""End-to-end smoke tests: the real CLI on real (small) models, shortened.

These download SmolLM2-135M-Instruct and all-MiniLM-L6-v2 on first run and take
a few minutes. Skip them with: pytest -m "not slow".
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone.cli import main  # noqa: E402

pytestmark = pytest.mark.slow
CONTRACT = {"grade", "fair_value_per_item", "flags", "overlap", "probes", "gains_by_size", "forecast", "summary"}


def _check(out: Path, kind: str, trained: bool):
    r = json.loads((out / "report.json").read_text())
    md = (out / "report.md").read_text()
    assert r["kind"] == kind and r["grade"] in "ABCDF"
    assert CONTRACT <= set(r) and set(r["overlap"]) == {"suite", "public", "duplicates"}
    assert r["heldout"]["domain"] and r["heldout"]["n_items"] > 0
    assert "## Held-out suite" in md and "## Forecast at 1.7B" in md
    if trained:
        assert "135M" in r["rungs"] and "placebo" in r["rungs"]["135M"]
        assert r["forecast"]["value"] is not None and "135M" in r["gains_by_size"]
    else:  # quick mode stops after screening when a blocking flag fires
        assert r["rungs"] == {} and r["forecast"]["value"] is None
        assert "screen_only" in [f["code"] for f in r["flags"]] and r["fair_value_per_item"] == 0
    return r


def test_cli_quick_dataset_trains(tmp_path):
    out = tmp_path / "good"
    rc = main(["appraise", str(ROOT / "examples" / "demo" / "good_word_problems.jsonl"), "--quick",
               "--suite-items", "30", "--steps", "4", "--out", str(out)])
    assert rc == 0
    r = _check(out, "dataset", trained=True)
    assert not [f for f in r["flags"] if f["code"] in ("contaminated", "noisy_labels", "copied_from_public")]


def test_cli_quick_dataset_contaminated_stops_after_screening(tmp_path):
    out = tmp_path / "contam"
    rc = main(["appraise", str(ROOT / "examples" / "datasets" / "contaminated.jsonl"), "--quick",
               "--suite-items", "30", "--out", str(out)])
    assert rc == 0
    r = _check(out, "dataset", trained=False)
    assert "contaminated" in [f["code"] for f in r["flags"]] and r["grade"] == "D"


def test_cli_quick_env_trains(tmp_path):
    out = tmp_path / "nw"
    rc = main(["appraise", str(ROOT / "envs" / "northwind_arith"), "--quick",
               "--suite-items", "30", "--steps", "2", "--out", str(out)])
    assert rc == 0
    r = _check(out, "env", trained=True)
    assert not r["grader_audit"]["flagged"]
    assert "## Grader audit" in (out / "report.md").read_text()


def test_cli_quick_env_gameable_stops_after_screening(tmp_path):
    out = tmp_path / "shape"
    rc = main(["appraise", str(ROOT / "envs" / "shapeonly_arith"), "--quick", "--suite-items", "30",
               "--out", str(out)])
    assert rc == 0
    r = _check(out, "env", trained=False)
    assert r["grader_audit"]["flagged"] and "gameable_grader" in [f["code"] for f in r["flags"]]
    assert r["probes"]["same shape, wrong content"] == 1.0
