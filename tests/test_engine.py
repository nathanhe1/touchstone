"""Fast unit tests for the real-model appraisal engine (no model downloads)."""
import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from touchstone import data, forecast, overlap, probes, suites, valuation  # noqa: E402
from touchstone import env as envmod  # noqa: E402
from touchstone.cli import main  # noqa: E402

ENVS = ROOT / "envs"


# ---------------------------------------------------------------- suites

def test_builtin_suites_are_deterministic_and_well_formed():
    for name, fn in suites.BUILTIN.items():
        a, b = fn(), fn()
        assert [i.prompt for i in a.items] == [i.prompt for i in b.items]
        assert len(a.items) >= 290
        for it in a.items[:50]:
            assert it.answer not in it.distractors and len(it.distractors) == suites.N_DISTRACTORS


def test_answer_matching():
    num = suites.Item("q", "79", "numeric")
    assert suites.is_correct("73 + 6 = 79. The answer is 79.", num)
    assert not suites.is_correct("The answer is 89.", num)
    assert suites.is_correct("1,079", suites.Item("q", "1079", "numeric"))
    s = suites.Item("q", "dcba", "exact")
    assert suites.is_correct("dcba", s) and suites.is_correct("The reversed string is 'dcba'.", s)
    assert not suites.is_correct("abcd", s)


def test_subset_is_stratified():
    s = suites.word_math_suite().subset(100)
    assert 95 <= len(s.items) <= 105 and len(s.parts()) == 10


def test_custom_suite_validation(tmp_path):
    f = tmp_path / "s.jsonl"
    f.write_text("\n".join(json.dumps({"prompt": f"q{i}", "answer": str(i)}) for i in range(40)))
    s = suites.get_suite(str(f))
    assert s.items[0].match == "numeric" and s.items[0].distractors
    f.write_text('{"prompt": "x"}\n')
    with pytest.raises(suites.SuiteError, match="answer"):
        suites.get_suite(str(f))


# ---------------------------------------------------------------- datasets

def test_dataset_formats_and_errors(tmp_path):
    f = tmp_path / "d.jsonl"
    rows = [{"prompt": f"p{i}", "completion": f"c{i}"} for i in range(15)]
    rows += [{"messages": [{"role": "user", "content": f"u{i}"}, {"role": "assistant", "content": f"a{i}"}]} for i in range(10)]
    f.write_text("\n".join(json.dumps(r) for r in rows))
    ex = data.load_dataset(f)
    assert len(ex) == 25 and ex[-1].completion == "a9" and ex[0].prompt_text == "p0"
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\n{bad json\n")
    with pytest.raises(data.DatasetError, match=":26: not valid JSON"):
        data.load_dataset(f)
    f.write_text(json.dumps({"text": "x"}) + "\n")
    with pytest.raises(data.DatasetError, match="unrecognised format"):
        data.load_dataset(f)
    with pytest.raises(data.DatasetError, match="folder"):
        data.load_dataset(tmp_path)


def test_messages_and_prompt_completion_train_identically(tmp_path):
    """Regression (good_short graded F): the chat 'messages' path must build exactly the same
    training text and loss target as the prompt/completion path."""
    from transformers import AutoTokenizer
    from touchstone.lm import LADDER, cached

    class Tok:  # minimal stand-in for lm.LM: only the chat template matters here
        tok = cached(AutoTokenizer.from_pretrained, LADDER["135M"])

        def chat_messages(self, messages):
            return self.tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    rows = [json.loads(x) for x in (ROOT / "examples" / "datasets" / "good_short.jsonl").read_text().splitlines()[:30]]
    a, b = tmp_path / "m.jsonl", tmp_path / "p.jsonl"
    a.write_text("\n".join(json.dumps(r) for r in rows))
    b.write_text("\n".join(json.dumps({"prompt": r["messages"][0]["content"], "completion": r["messages"][1]["content"]})
                           for r in rows))
    pa = data.to_training_pairs(Tok(), data.load_dataset(a))
    pb = data.to_training_pairs(Tok(), data.load_dataset(b))
    assert pa == pb
    assert pa[0][0].endswith("<|im_start|>assistant\n") and pa[0][1].startswith("The answer is")


def test_placebo_keeps_answers_breaks_pairs():
    ex = [data.Example([{"role": "user", "content": str(i)}], str(i)) for i in range(50)]
    pl = data.placebo(ex)
    assert sorted(e.completion for e in pl) == sorted(e.completion for e in ex)
    assert sum(e.completion == e.prompt_text for e in pl) < 5


# ---------------------------------------------------------------- overlap

def test_overlap_tiers():
    ref = ["Maria has 83 stickers. She gives 10 to her brother and then buys 6 more. How many stickers does she have now?",
           "A train travels 120 km in the morning and 80 km in the afternoon. How many km does it travel in total?"]
    items = [ref[0],  # exact
             "maria has 83 stickers she gives 10 to her brother and then buys 6 more how many stickers does she have now",
             "A train goes 120 km before noon and 80 km after noon. What total distance in km does it cover?",  # reworded
             "A train travels 130 km in the morning and 80 km in the afternoon. How many km does it travel in total?",  # new numbers
             "Sort these words: apple, pear."]
    m = overlap.match(items, ref)
    assert m["exact"] == 2 / 5
    assert 2 in m["matched_idx"], "reworded copy with the same numbers should match"
    assert 3 not in m["matched_idx"], "same template with different numbers is a different item"
    assert 4 not in m["matched_idx"]


def test_contaminated_example_dataset_is_caught():
    ex = data.load_dataset(ROOT / "examples" / "datasets" / "contaminated.jsonl")
    suite = suites.word_math_suite()
    m = overlap.match([e.prompt_text for e in ex], [i.prompt for i in suite.items])
    assert m["rate"] >= 0.2  # 150 of 600 lines are reworded suite items
    good = data.load_dataset(ROOT / "examples" / "datasets" / "good_cot.jsonl")
    assert overlap.match([e.prompt_text for e in good], [i.prompt for i in suite.items])["rate"] < 0.01


# ---------------------------------------------------------------- grader audit

@pytest.mark.parametrize("name,flagged,exploit", [
    ("northwind_arith", False, None), ("public_arith", False, None), ("mirror_strings", False, None),
    ("quickgrade_arith", True, "hedge"), ("shapeonly_arith", True, "same shape"), ("hintleak_arith", True, "copy a prompt span"),
])
def test_grader_audit_catches_planted_graders(name, flagged, exploit):
    e = envmod.load(ENVS / name)
    a = probes.audit_grader(e)
    assert a["flagged"] == flagged
    if exploit:
        assert exploit in a["worst_exploit"] and a["score"] >= 0.9
    else:
        assert a["score"] < 0.05 and a["reference_accept_rate"] == 1.0


def test_final_answer_parser_is_strict_but_format_tolerant():
    fa = envmod.final_answer
    assert fa("742") == fa("673 + 69 = 742") == fa("The answer is 742.") == fa("**742**") == "742"
    assert fa("The reversed string is 'cba'.") == "cba"
    assert fa("85 86") is None and fa("86 or 85") is None and fa("abc 85 xyz") is None


def test_env_validation_errors(tmp_path):
    f = tmp_path / "env.py"
    f.write_text("X = 1\n")
    with pytest.raises(envmod.EnvError, match="ENV"):
        envmod.load(tmp_path)
    f.write_text("from touchstone.env import Task\nclass E:\n    def tasks(self): return [Task('p')]*5\n"
                 "    def verify(self, t, o): return 1.0\nENV = E()\n")
    with pytest.raises(envmod.EnvError, match="at least 20"):
        envmod.validate(envmod.load(tmp_path), tmp_path)
    f.write_text("from touchstone.env import Task\nclass E:\n    def tasks(self): return [Task('p')]*30\n"
                 "    def verify(self, t, o): return 5.0\nENV = E()\n")
    with pytest.raises(envmod.EnvError, match=r"\[0, 1\]"):
        envmod.validate(envmod.load(tmp_path), tmp_path)


# ---------------------------------------------------------------- forecast and valuation

def test_decision_accuracy():
    assert forecast.decision_accuracy([1, 2, 3], [10, 20, 30]) == 1.0
    assert forecast.decision_accuracy([3, 2, 1], [10, 20, 30]) == 0.0


def test_calibrated_forecast_recovers_a_linear_map():
    rng = random.Random(0)
    rows = []
    for i in range(12):
        a, c = rng.uniform(-5, 10), rng.uniform(-5, 10)
        rows.append({"name": str(i), "small": {"135M": {"acc": 0, "cand": 0}, "360M": {"acc": a, "cand": c}},
                     "target": 1.0 + 2.0 * a + 0.5 * c})
    params = {"135M": 1.35e8, "360M": 3.6e8, "target": 1.7e9}
    v = forecast.validate(rows, params)
    assert v["methods"]["calibrated"]["mae_pts"] < 0.05
    assert v["methods"]["calibrated"]["decision_accuracy"] == 1.0
    cal = forecast.make_calibration(rows, params)
    f = forecast.calibrated_forecast({"135M": {"acc": 0, "cand": 0}, "360M": {"acc": 2, "cand": 4}}, cal)
    assert abs(f["point"] - 7.0) < 0.05 and f["lo"] <= f["point"] <= f["hi"]


def test_grade_and_value_rules():
    clean = valuation.flags_for({"measurable": True})
    assert clean == [] and valuation.grade(6, clean) == "A" and valuation.grade(1, clean) == "C"
    v = valuation.fair_value(2.0, clean, 1000, 0.25, 250_000)
    assert v["per_item"] == 375.0
    contam = valuation.flags_for({"measurable": True, "contamination": 0.2})
    assert valuation.grade(9, contam) == "D" and valuation.fair_value(9, contam, 1000, 0, 250_000)["per_item"] == 0
    hack = valuation.flags_for({"measurable": True, "hackability": 1.0, "worst_exploit": "x"})
    assert valuation.grade(9, hack) == "D"
    unmeasured = valuation.flags_for({"measurable": False})
    assert valuation.grade(9, unmeasured) == "D" and valuation.fair_value(9, unmeasured, 10, 0, 1)["per_item"] == 0
    assert valuation.grade(-3, valuation.flags_for({"measurable": False, "harmful": True})) == "F"
    copy = valuation.flags_for({"measurable": True, "public_overlap": 0.9})
    assert valuation.grade(9, copy) == "F" and valuation.fair_value(9, copy, 10, 0.9, 1)["per_item"] == 0
    pub = valuation.flags_for({"measurable": True, "public_overlap": 0.6})
    assert valuation.grade(9, pub) == "D" and valuation.fair_value(2, pub, 1000, 0.6, 250_000)["per_item"] == 200.0


def test_fair_value_is_not_inflated_by_repetition():
    """Regression: 20 unique examples repeated to fill a 960-example budget were priced at the full gain / 20."""
    clean = valuation.flags_for({"measurable": True})
    tiny = valuation.fair_value(5.0, clean, 20, 0.0, 250_000, examples_seen=960)
    big = valuation.fair_value(5.0, clean, 2000, 0.0, 250_000, examples_seen=960)
    assert tiny["per_item"] == big["per_item"] == round(5.0 * 250_000 / 2000, 2) or tiny["per_item"] == round(
        5.0 * 250_000 / 960, 2)
    assert tiny["per_item"] == round(5.0 * 250_000 / 960, 2) and tiny["total"] < big["total"]


# ---------------------------------------------------------------- report rendering

def _gain(g):
    return {"gain": g, "lo": g - 2, "hi": g + 2, "se": 1.0}


def test_report_renders_env_and_dataset():
    from touchstone.report_md import render
    rung = {"params": 1, "seeds": 1, "before": {"accuracy": 40.0, "candidate_prob": 50.0},
            "material": {"after": {"accuracy": 45.0, "candidate_prob": 55.0}, "acc_gain": _gain(5), "cand_gain": _gain(5),
                         "acc_gain_clean": _gain(5), "env_reward_after": 0.9},
            "placebo": {"after": {"accuracy": 41.0, "candidate_prob": 50.0}, "acc_gain": _gain(1), "cand_gain": _gain(0),
                        "acc_gain_clean": _gain(1), "env_reward_after": 0.5},
            "net": {"acc": _gain(4), "cand": _gain(5)}, "env_reward_before": 0.5}
    r = {"kind": "env", "mode": "quick", "grade": "B", "runtime_s": 65,
         "material": {"name": "X", "path": "p", "sha256": "abc", "n_items": 100, "unique_items": 90},
         "heldout": {"name": "arithmetic", "domain": "addition", "description": "d", "n_items": 120, "source": "s",
                     "n_items_untouched_by_material": 120},
         "overlap": {"heldout": {"rate": 0.0, "exact": 0, "near": 0, "paraphrase": 0, "suite_share": 0.0},
                     "public": {"rate": 0.1, "baseline": "free"}, "duplicates": {"dup_rate": 0.1}},
         "grader_audit": {"n_probed": 200, "has_reference": True, "per_exploit": {"empty answer": 0.0},
                          "reference_accept_rate": 1.0, "answer_in_prompt": 0.0},
         "transfer_check": {"rung": "135M", "env_reward_gain_pts": 40.0, "heldout_gain_pts": 5.0, "transfer_gap": False},
         "rungs": {"135M": rung},
         "forecast": {"target": "1.7B", "method": "rank_largest", "method_note": "n",
                      "material": {"point": 5, "lo": 3, "hi": 7}, "placebo": {"point": 1, "lo": 0, "hi": 2},
                      "net": {"point": 4, "lo": 2, "hi": 6}},
         "flags": [], "fair_value": {"per_item": 12.5, "total": 1000, "blocked_by": [], "novel_share": 0.9,
                                     "dollars_per_point": 250000},
         "models": {"135M": "m"}, "recipe": {"lora_r": 16}}
    md = render(r)
    assert "Grade B" in md and "## Grader audit" in md and "| 135M | 1 | 40.0%" in md
    r["kind"] = "dataset"
    assert "## Grader audit" not in render(r)


# ---------------------------------------------------------------- CLI input errors

def test_cli_rejects_bad_input(tmp_path, capsys):
    assert main(["appraise", str(tmp_path / "missing.jsonl")]) == 2
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"prompt": "x"}\n')
    assert main(["appraise", str(bad), "--kind", "dataset", "--quick"]) == 2
    assert "unrecognised format" in capsys.readouterr().err
    assert main(["appraise", str(ROOT / "examples" / "datasets" / "good_cot.jsonl"), "--suite", "nope"]) == 2
    assert "unknown held-out suite" in capsys.readouterr().err
