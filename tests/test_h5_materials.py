"""h5 real competing materials: the frozen files match their manifest, and the answer helpers read real formats."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import h5_materials as M  # noqa: E402

H5 = ROOT / "examples" / "h5"


def test_files_match_manifest_hashes_and_sizes():
    m = json.loads((H5 / "manifest.json").read_text())
    for fam, F in m["families"].items():
        files = [F["suite"]] + list(F["materials"].values())
        for f in files:
            p = ROOT / f["file"]
            assert hashlib.sha256(p.read_bytes()).hexdigest() == f["sha256"], p
        for v in F["materials"].values():
            rows = [json.loads(x) for x in (ROOT / v["file"]).read_text().splitlines()]
            assert len(rows) == m["rows_per_material"]
            assert all(r["prompt"].strip() and r["completion"].strip() for r in rows)
            assert len({r["prompt"] for r in rows}) == len(rows)


def test_class_balance_of_classification_materials():
    m = json.loads((H5 / "manifest.json").read_text())
    for fam in ("nli", "sci"):
        for v in m["families"][fam]["materials"].values():
            k = v["class_balance"]["classes"]
            assert v["class_balance"]["majority_share"] <= 1 / k + 0.1, (fam, v["file"])


def test_boxed_and_last_number():
    assert M.boxed(r"so $x = \boxed{\frac{1}{2}}$.") == r"\frac{1}{2}"
    assert M.boxed(r"\boxed{3} then \boxed{51}") == "51"
    assert M.boxed("no box") is None
    assert M.last_number("He pays 1,200 dollars, so 45.") == "45"
    assert M.last_number("Total: 1,200") == "1200"


def test_kk_grader():
    names, sol = ["Zoey", "Oliver"], [True, False]
    assert M.kk_correct("Zoey is a knave? No.\n(1) Zoey is a knight\n(2) Oliver is a knave", names, sol)
    assert not M.kk_correct("(1) Zoey is a knight", names, sol)
    assert not M.kk_correct("(1) Zoey is a knight\n(2) Oliver is a knight", names, sol)
