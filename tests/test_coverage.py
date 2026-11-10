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


def test_a_few_slips_in_mostly_prose_do_not_flag():
    from touchstone import suites
    suite = suites.word_math_suite(30)
    rows = [ex("Tell me about tea.", "Tea is a drink.")] * 97 + [ex("Sum?", "2 + 2 = 5"), ex("Sum?", "2 + 2 = 4"), ex("Sum?", "3 + 3 = 6")]
    assert not screen.screen_dataset(rows, suite)["noisy"]


def test_a_real_error_rate_still_flags():
    from touchstone import suites
    rows = [ex("Sum?", f"{i} + 1 = {i + 2}") for i in range(30)] + [ex("Sum?", f"{i} + 1 = {i + 1}") for i in range(70)]
    assert screen.screen_dataset(rows, suites.word_math_suite(30))["noisy"]


def test_price_range_spans_the_interval():
    from touchstone import valuation
    r = valuation.price_range(1.74, 12.93, [], 400, 0.0, 5000, 480)
    assert r["grade_low"] == "C" and r["grade_high"] == "A" and r["per_item_low"] < r["per_item_high"]
    b = valuation.price_range(1.0, 9.0, [{"code": "noisy_labels", "severity": "block"}], 400, 0.0, 5000, 480)
    assert b["per_item_high"] == 0


def test_two_route_multiple_choice_runs_end_to_end(monkeypatch):
    """A cleanup once deleted a constant only this path uses, and only a frozen test run found out."""
    rows = [ex(f"Q{i}\nA) yes\nB) no", "A") for i in range(30)]
    monkeypatch.setattr(judge, "_gen", lambda q, system, n, batch=8: ["A" if n < 20 else "so \\boxed{A}" for _ in q])
    r = judge.audit_mcq2(rows)
    assert r["confident"] == 30 and r["disagree"] == 0
    r = coverage.label_checks("multiple_choice", rows, use_judge=True)
    assert r["status"] == "checked" and not r["noisy"]


def test_every_upper_case_name_in_the_judge_is_defined():
    import ast
    from pathlib import Path
    src = Path(judge.__file__).read_text()
    names = {n.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name) and n.id.isupper()}
    assert all(hasattr(judge, x) for x in names)


def test_latex_boxed_answers_are_read():
    # test v4 defect: every MATH prealgebra draw was flagged because '$102/2=\boxed{51}$' looked unproduced
    real = r"The total distance traveled was $20+25+45+12=102$ km.  Therefore, the average speed was $102/2=\boxed{51}$ kph."
    assert screen.check_arithmetic(real) == (2, 0)
    assert not screen.unsupported_final(real)
    planted = real.replace(r"\boxed{51}", r"\boxed{53}")
    assert screen.check_arithmetic(planted) == (2, 1)
    assert screen.check_arithmetic(r"So $\frac{1}{2}(240) = \boxed{120}$ and $0.75 \cdot (90/15) = 4.5$, $5\frac{1}{2}\cdot 2=11$.") == (3, 0)
    assert screen.check_arithmetic(r"\begin{align*} 2^{3}+2^{2} &= 8+4 \\ &= \boxed{12} \end{align*}") == (2, 0)


def test_latex_algebra_is_not_misread_as_arithmetic():
    # sides with variables, roots or approximations are skipped, never evaluated as a suffix
    for t in [r"we have $x^2-4x-9 = 0$.", r"$\sqrt{16 + 4} = 2\sqrt{5}$", r"$3x^2+2 = 29$", r"$\frac{576}{\pi} \approx 183$",
              r"the points $(1,7)$ and $(13,7)$, so $|5-6| + 2\cdot 5 = 11$"]:
        assert screen.check_arithmetic(t)[1] == 0, t
    # prose final steps in competition solutions are not flagged as unsupported
    assert not screen.unsupported_final(r"Their product is $4\cdot6\cdot8=192$, so the units digit is $\boxed{2}$.")


def test_plain_text_dollars_unchanged():
    assert screen.check_arithmetic("He paid $10 x 3 = $30 and $30 + 5 = $36.") == (2, 1)
