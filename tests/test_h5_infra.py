"""Sprint infrastructure: the class-balance gate, number scoring and fetch sampling (no network, no models)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import h4_common as H  # noqa: E402


def rows(answers, k):
    return [(f"q{i}", a, 1 / k) for i, a in enumerate(answers)]


def test_gate_refuses_single_class_material():
    b = H.balance(rows(["A"] * 100, 14))  # h4's dbpedia material: every row one class
    assert not b["ok"] and b["share"] == 1.0
    with pytest.raises(H.ImbalancedError):
        H.gate_balance(rows(["A"] * 100, 14), "dbpedia material")


def test_gate_refuses_imdb_skew_but_allows_natural_binary_skew():
    assert not H.balance(rows(["A"] * 78 + ["B"] * 22, 2))["ok"]  # h4's imdb fetch: 78% one class
    assert H.balance(rows(["A"] * 64 + ["B"] * 36, 2))["ok"]  # CR's natural 64% positive
    assert H.balance(rows(["A"] * 62 + ["B"] * 38, 2))["ok"]  # BoolQ's natural 62% yes


def test_gate_cap_tightens_with_more_classes():
    five = list("ABCDE")
    assert H.balance(rows([five[i % 5] for i in range(100)], 5))["ok"]
    skew = ["A"] * 55 + [five[1 + i % 4] for i in range(45)]
    assert not H.balance(rows(skew, 5))["ok"]  # 55% > 2.5/5
    assert H.balance(rows(skew, 2))["cap"] == 0.65


def test_number_scoring():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import h5_run as R
    assert R.num_correct("3 + 4 = 7. The answer is 7.", "7")
    assert R.num_correct("She pays $1,250 in total.", "1250")
    assert not R.num_correct("The answer is 8. Then 7", "7")
    assert not R.num_correct("no number here", "7")


def test_fetch_samples_whole_split_at_random_offsets(monkeypatch):
    import fetch_h4_sources as F
    data = [{"label": i // 100} for i in range(1000)]  # sorted by label, like dbpedia
    monkeypatch.setattr(F, "split_size", lambda ds, cfg, split: len(data))
    monkeypatch.setattr(F, "block", lambda ds, cfg, split, off, n: data[off:off + n])
    monkeypatch.setattr(F.time, "sleep", lambda s: None)
    got, prov = F.sample("x", "y", "train", 200, seed=1)
    assert len(got) == 200 and len({r["label"] for r in got}) >= 6
    assert got != sorted(got, key=lambda r: r["label"])  # shuffled
    again, _ = F.sample("x", "y", "train", 200, seed=1)
    assert again == got  # reproducible from the seed
    small, prov2 = F.sample("x", "y", "train", 5000, seed=1)
    assert len(small) == 1000 and prov2["method"] == "whole split"


def test_answer_detection_ignores_prose_capitals():
    import h5_run as R
    ok = ["C) Business", "  B", "(D)", "A.", "B\nbecause"]
    bad = ["I purchased this", "Text: A) negative", "A great film"]
    assert all(R.has_answer("ag_news", x) for x in ok)
    assert not any(R.has_answer("ag_news", x) for x in bad)


def test_placebo_and_all_wrong_differ(tmp_path):
    import h5_run as R
    rows = [{"prompt": f"Q{i}\nA) x\nB) y\nC) z\nReply with the letter only.", "completion": "ABC"[i % 3], "answer": "ABC"[i % 3]}
            for i in range(300)]
    f = tmp_path / "m.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in rows))
    clean = R.material("toy", f"file:{f}", "final", "m")
    placebo = R.material("toy", f"shuffle:file:{f}", "final", "placebo")
    shuffled = R.material("toy", f"shuffle:file:{f}", "final", "shuffled_m")
    wrong = R.material("toy", f"wrong:file:{f}", "final", "wrong_m")
    same = lambda a, b: sum(x[1] == y[1] for x, y in zip(a, b)) / len(a)
    assert same(placebo, shuffled) < 0.6  # seeded by the arm's name: not the same rows
    assert same(wrong, clean) == 0.0  # every completion wrong
