"""All-data-types layer: routing, the code sandbox, and 'not checked' instead of a false clean pass."""
import pytest

from touchstone import codecheck, coverage, judge, screen
from touchstone.data import Example


def ex(p, c, **meta):
    return Example([{"role": "user", "content": p}], c, meta)


def test_detects_types_from_content():
    assert coverage.detect_type([ex("Sam has 3 cats and 4 dogs. How many pets?", "7")] * 20) == "numeric"
    assert coverage.detect_type([ex("Which is a gas?\nA) iron\nB) helium\nC) salt", "B")] * 20) == "multiple_choice"
    assert coverage.detect_type([ex("Add.", "def add(a, b):\n    return a + b", test_list=["assert add(1, 2) == 3"])] * 20) == "code"
    assert coverage.detect_type([ex("Tell me about tea.", "Tea is a drink made from leaves and it is popular in many places.")] * 20) == "free_text"
    assert coverage.detect_type([ex("Weather?", '<functioncall> {"name": "w", "arguments": {}}')] * 20) == "tool_use"


def test_language():
    assert coverage.language(["Los patos ponen huevos cada día y ella vende lo que sobra en el mercado."]) == "non_en"
    assert coverage.language(["The ducks lay eggs every day and she sells the rest of them at the market."]) == "en"


def test_label_of_formats():
    assert judge.label_of("#### 1,200") == "1200"
    assert judge.label_of("The answer is \\boxed{42}.") == "42"
    assert judge.label_of('{"answer": 7}') == "7"
    assert judge.label_of("First, 3 × 4 = 12. Answer: 12") == "12"
    assert judge.label_of("olleh") == "olleh"


@pytest.mark.parametrize("expr", ["__import__('os')", "open('/etc/passwd')", "(1).__class__", "exec('1')", "[x for x in (1,)]", "9**9**9"])
def test_safe_eval_refuses(expr):
    with pytest.raises(Exception):
        judge.safe_eval(expr)


def test_safe_eval_allows():
    assert judge.safe_eval("3 * 12 - 5") == 31
    assert judge.safe_eval('"abc"[::-1]') == "cba"


def test_program_route_drops_mistyped_literal():
    assert judge._pal_value('"abd"[::-1]', "Reverse abc.") is None
    assert judge._pal_value('"abc"[::-1]', "Reverse abc.") == "cba"


def test_cot_fallback_without_box():
    assert judge._cot_value("Total = 12\n\nSo, Kim runs a total of 12 laps.") == "12"
    assert judge._cot_value("So it is \\(\\boxed{97}\\) dollars.") == "97"


def test_unsupported_final_only_on_worked_solutions():
    assert screen.unsupported_final("3 x 4 = 12; 12 + 5 = 17. So the answer is 23.")
    assert not screen.unsupported_final("3 x 4 = 12; 12 + 5 = 17. So the answer is 17.")
    assert not screen.unsupported_final("The answer is 23.")


@pytest.mark.skipif(codecheck.isolation() is None, reason="no process isolation here")
@pytest.mark.parametrize("code,ok", [
    ("def f(x):\n    return x + 1", True),
    ("def f(x):\n    return x", False),
    ("import socket\nsocket.create_connection(('1.1.1.1', 53), timeout=2)\ndef f(x):\n    return x + 1", False),
    ("open('/Users/x', 'w')\ndef f(x):\n    return x + 1", False),
    ("import subprocess\nsubprocess.check_call(['/bin/ls'])\ndef f(x):\n    return x + 1", False),
    ("while True:\n    pass", False),
])
def test_sandbox(code, ok):
    assert codecheck.run_test(code, "assert f(1) == 2", timeout=3)["passed"] is ok


def test_no_isolation_means_not_checked(monkeypatch):
    monkeypatch.setattr(codecheck, "isolation", lambda: None)
    r = coverage.label_checks("code", [ex("Add.", "def f(): pass", test="assert True")] * 20, use_judge=False)
    assert r["status"] == "not_checked" and not r["noisy"]


def test_no_judge_means_not_checked_rather_than_clean():
    for t in ("multiple_choice", "free_text", "chat", "short_transform", "numeric"):
        r = coverage.label_checks(t, [ex("q", "a")] * 20, {"rate": None}, use_judge=False)
        assert r["status"] == "not_checked" and "reason" in r and not r["noisy"]


def test_code_without_tests_is_only_partial():
    r = coverage.label_checks("code", [ex("Add.", "def f(:\n  pass")] * 20, use_judge=False)
    assert r["status"] == "partial" and r["noisy"]


def test_tool_audit_finds_violations():
    sys = {"role": "system", "content": '{"name": "w", "parameters": {"properties": {"c": {"type": "string"}}, "required": ["c"]}}'}
    good = Example([sys, {"role": "user", "content": "x"}], '<functioncall> {"name": "w", "arguments": {"c": "a"}}')
    bad = Example([sys, {"role": "user", "content": "x"}], '<functioncall> {"name": "z", "arguments": {}}')
    cut = Example([sys, {"role": "user", "content": "x"}], '<functioncall> {"name": "w", "argu')
    r = coverage.tool_audit([good, bad, cut])
    assert r["checked"] == 3 and r["violations"] == 2
