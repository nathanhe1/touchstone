"""End-to-end smoke tests: the real CLI on real (small) models, shortened.

These download SmolLM2-135M-Instruct and all-MiniLM-L6-v2 on first run and take
a couple of minutes. Skip them with: pytest -m "not slow".
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone.cli import main  # noqa: E402

pytestmark = pytest.mark.slow


def _check(out: Path, kind: str):
    r = json.loads((out / "report.json").read_text())
    md = (out / "report.md").read_text()
    assert r["kind"] == kind and r["grade"] in "ABCDF"
    assert "135M" in r["rungs"] and "placebo" in r["rungs"]["135M"]
    assert {"point", "lo", "hi"} <= set(r["forecast_detail"]["net"])
    assert {"grade", "fair_value_per_item", "flags", "overlap", "probes", "gains_by_size", "forecast", "summary"} <= set(r)
    assert r["heldout"]["domain"] and r["heldout"]["n_items"] > 0
    assert "## Held-out suite" in md and "## Forecast at 1.7B" in md
    return r


def test_cli_quick_dataset(tmp_path):
    out = tmp_path / "ds"
    rc = main(["appraise", str(ROOT / "examples" / "datasets" / "contaminated.jsonl"), "--quick",
               "--suite-items", "30", "--steps", "4", "--out", str(out)])
    assert rc == 0
    r = _check(out, "dataset")
    assert "contaminated" in [f["code"] for f in r["flags"]]
    assert r["fair_value"]["per_item"] == 0


def test_cli_quick_env(tmp_path):
    out = tmp_path / "env"
    rc = main(["appraise", str(ROOT / "envs" / "shapeonly_arith"), "--quick",
               "--suite-items", "30", "--steps", "2", "--out", str(out)])
    assert rc == 0
    r = _check(out, "env")
    assert r["grader_audit"]["flagged"] and "gameable_grader" in [f["code"] for f in r["flags"]]
    assert "## Grader audit" in (out / "report.md").read_text()
