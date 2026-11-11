"""The dataset loader on the shapes real buyers send (FDE sprint). Each case is a fix; each test is fast."""
import csv
import gzip
import json

import pytest

from touchstone import data


def _jsonl(p, rows):
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


def _pc(n=25):
    return [{"prompt": f"What is {i} + 1?", "completion": f"{i + 1}"} for i in range(n)]


def test_one_empty_reply_is_skipped_not_fatal(tmp_path):
    # v4 lost a case, and MathInstruct (262,039 rows) was refused, because one row had an empty reply.
    rows = _pc(40) + [{"prompt": "Statement 1 ... Options: entailment or neutral?", "completion": ""}]
    r = data.load_dataset(_jsonl(tmp_path / "d.jsonl", rows))
    assert len(r) == 40 and r.skipped == 1 and r.total == 41
    assert "empty" in r.skip_reasons[0] and "d.jsonl:41" in r.skip_reasons[0]


def test_null_fields_and_bad_json_are_skipped_within_the_limit(tmp_path):
    p = tmp_path / "d.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in _pc(30)) + '{"prompt": null, "completion": "x"}\n{not json\n')
    r = data.load_dataset(p)
    assert len(r) == 30 and r.skipped == 2


def test_mostly_bad_file_is_still_refused(tmp_path):
    rows = _pc(20) + [{"prompt": "", "completion": ""}] * 10
    with pytest.raises(data.DatasetError, match="10 of 30 rows unreadable"):
        data.load_dataset(_jsonl(tmp_path / "d.jsonl", rows))


def test_sharegpt_conversations_with_system_and_multiturn(tmp_path):
    rows = [{"conversations": [{"from": "system", "value": "You are terse."}, {"from": "human", "value": f"hi {i}"},
                               {"from": "gpt", "value": "hello"}, {"from": "human", "value": "and 2+2?"},
                               {"from": "gpt", "value": "4"}]} for i in range(25)]
    r = data.load_dataset(_jsonl(tmp_path / "d.jsonl", rows))
    assert r[0].completion == "4" and [m["role"] for m in r[0].messages] == ["system", "user", "assistant", "user"]


def test_messages_with_content_parts_and_trailing_user_turn(tmp_path):
    rows = [{"messages": [{"role": "user", "content": [{"type": "text", "text": "Translate: chat"}]},
                          {"role": "assistant", "content": "cat"}, {"role": "user", "content": "thanks"}]}] * 25
    r = data.load_dataset(_jsonl(tmp_path / "d.jsonl", rows))
    assert r[0].completion == "cat" and r[0].messages[0]["content"] == "Translate: chat"


def test_json_array_export_and_field_aliases(tmp_path):
    rows = [{"query": f"q{i}", "response": "The answer is: 3"} for i in range(25)]  # MetaMathQA's shape
    p = tmp_path / "d.json"
    p.write_text(json.dumps(rows))
    assert len(data.load_dataset(p)) == 25
    p.write_text(json.dumps({"train": [{"problem": f"p{i}", "solution": "$\\boxed{2}$"} for i in range(25)]}))
    assert data.load_dataset(p)[0].completion == "$\\boxed{2}$"


def test_csv_tsv_with_byte_order_mark_and_gzip(tmp_path):
    p = tmp_path / "d.csv"
    with p.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["instruction", "input", "output"])
        for i in range(25):
            w.writerow([f"Résume la phrase {i}", "Le chat dort, et\nle chien aussi.", "Les animaux dorment."])
    r = data.load_dataset(p)
    assert len(r) == 25 and "Le chat" in r[0].messages[0]["content"]
    t = tmp_path / "d.tsv"
    t.write_text("prompt\tcompletion\n" + "".join(f"x{i}\ty\n" for i in range(25)))
    assert len(data.load_dataset(t)) == 25
    g = tmp_path / "d.jsonl.gz"
    g.write_bytes(gzip.compress("".join(json.dumps(r) + "\n" for r in _pc()).encode()))
    assert len(data.load_dataset(g)) == 25


def test_parquet(tmp_path):
    pa = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq
    p = tmp_path / "d.parquet"
    pq.write_table(pa.Table.from_pylist(_pc()), p)
    assert len(data.load_dataset(p)) == 25


def test_parquet_without_pyarrow_says_what_to_do(tmp_path, monkeypatch):
    import builtins
    real = builtins.__import__

    def fake(name, *a, **k):
        if name.startswith("pyarrow"):
            raise ImportError(name)
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", fake)
    p = tmp_path / "d.parquet"
    p.write_bytes(b"PAR1")
    with pytest.raises(data.DatasetError, match="convert the file to JSONL"):
        data.load_dataset(p)


def test_long_replies_latex_and_non_english_load_unchanged(tmp_path):
    long = "Step. " * 20000
    rows = [{"prompt": "Calcule $\\frac{1}{2}+\\frac{1}{3}$ 请解释", "completion": long + "\\boxed{\\frac{5}{6}}"}] * 25
    r = data.load_dataset(_jsonl(tmp_path / "d.jsonl", rows))
    assert r[0].completion.endswith("\\boxed{\\frac{5}{6}}") and len(r[0].completion) > 100000


def test_capitalised_csv_headers_and_inputs_targets(tmp_path):
    t = tmp_path / "d.csv"
    t.write_text("Question,Answer \n" + "".join(f"q{i},a{i}\n" for i in range(25)))
    assert data.load_dataset(t)[3].completion == "a3"
    rows = [{"inputs": "أجب على السؤال", "targets": "الإجابة", "language": "Standard Arabic"}] * 25  # Aya's shape
    assert data.load_dataset(_jsonl(tmp_path / "a.jsonl", rows))[0].completion == "الإجابة"


def _env_folder(tmp_path, extra=""):
    d = tmp_path / "myenv"
    d.mkdir(parents=True)
    (d / "helpers.py").write_text("def score(out, ans):\n    return float(out.strip() == ans)\n")
    (d / "requirements.txt").write_text("reasoning-gym==0.1.19\n")
    (d / "env.py").write_text(extra + "from touchstone.env import Task\nfrom helpers import score\n\n"
                              "class E:\n    name = 'e'\n    def tasks(self):\n        return [Task(f'{i}+1?', {'answer': str(i + 1)}) for i in range(30)]\n"
                              "    def verify(self, task, output):\n        return score(output, task.meta['answer'])\n\nENV = E()\n")
    return d


def test_env_folder_can_import_its_own_helper_module(tmp_path):
    from touchstone import env
    e = env.load(_env_folder(tmp_path))
    assert e.verify(e.tasks()[0], "1") == 1.0
    other = _env_folder(tmp_path / "second")  # a second environment's helpers.py is its own, not the first one's
    (other / "helpers.py").write_text("def score(out, ans):\n    return 0.5\n")
    assert env.load(other).verify(e.tasks()[0], "1") == 0.5 and e.verify(e.tasks()[0], "1") == 1.0


def test_env_with_uninstalled_dependency_names_it_and_its_requirements(tmp_path):
    from touchstone import env
    with pytest.raises(env.EnvError, match="imports 'reasoning_gym_not_here', which is not installed.*reasoning-gym==0.1.19"):
        env.load(_env_folder(tmp_path, "import reasoning_gym_not_here\n"))


def test_unknown_columns_get_one_error_that_says_what_to_rename(tmp_path):
    t = tmp_path / "TruthfulQA.csv"  # the real file's header
    t.write_text("Type,Category,Question,Best Answer,Source\n" + "a,b,q,ans,s\n" * 30)
    with pytest.raises(data.DatasetError) as e:
        data.load_dataset(t)
    msg = str(e.value)
    assert msg.count("unrecognised format") == 1 and "best answer" in msg and "question/answer" in msg
