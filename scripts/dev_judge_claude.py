"""Development test: a Claude model as the judge for the two-route multiple-choice label check.

Same rows, same statistic and same tuning as `scripts/dev_judge_mcq.py` (8 sources, 2 clean draws and 1 draw with 30% wrong
labels per source, 150 rows each), so the result sits beside the Qwen2.5 1.5B and 7B judges in `out/dev_judge_mcq_tune.json`.
The judge is called through the `claude` command line in print mode, with no tools, from an empty directory.

    python scripts/dev_judge_claude.py run claude-haiku-5-5     # writes out/dev_judge_mcq_claude-haiku-5-5.json
    python scripts/dev_judge_claude.py run claude-fable-5-2 60  # first 60 rows of each draw only: ..._first60.json
    python scripts/dev_judge_mcq.py tune                        # adds it to out/dev_judge_mcq_tune.json

Development data only. The rows are public train splits, which a large model may have seen in training, so its accuracy
here can be higher than on a vendor's private material. The model never sees the label.
"""
import json
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "examples" / "dev_judge"
BATCH, WORKERS = 25, 6
DIRECT = ('Answer each multiple-choice question. Reply with exactly one line per question in the form "Q<number>: <letter>" '
          "and nothing else.")
COT = ("Answer each multiple-choice question. For each question, reason step by step in a few sentences, then end that "
       'question\'s answer with a line in the form "Q<number>: <letter>".')
LINE = re.compile(r"^\s*\**Q(\d+)\**\s*[:.]\s*\**\(?([A-J])\)?\**\s*$", re.M)
CWD = tempfile.mkdtemp(prefix="judge_cwd_")


def ask(model, system, questions):
    """One call for a batch. Returns ({question number: letter}, cost in dollars). Retries until every question has a letter."""
    prompt = "\n\n".join(f"Q{i + 1}.\n{q}" for i, q in enumerate(questions))
    best, cost = {}, 0.0
    for attempt in range(5):
        why = ""
        try:
            p = subprocess.run(["claude", "-p", "--model", model, "--system-prompt", system, "--tools", "", "--strict-mcp-config",
                                "--no-session-persistence", "--disable-slash-commands", "--output-format", "json"],
                               input=prompt, capture_output=True, text=True, cwd=CWD, timeout=600)
            # the result is the last JSON line; the command line can print a warning line before it
            j = next(json.loads(x) for x in reversed(p.stdout.splitlines()) if x.startswith("{") and '"result"' in x)
            cost += j.get("total_cost_usd") or 0.0
            got = {int(n): letter for n, letter in LINE.findall(j.get("result") or "")}  # the last line for a question wins
            if len(got) > len(best):
                best = got
            if not j.get("is_error") and len(got) == len(questions):
                return got, cost
            why = f"is_error={j.get('is_error')} stop={j.get('stop_reason')} parsed={len(got)}/{len(questions)} text={(j.get('result') or '')[:120]!r}"
        except (ValueError, StopIteration, subprocess.TimeoutExpired) as e:
            why = f"{type(e).__name__}: {str(e)[:200]} stdout={p.stdout[-200:] if 'p' in dir() else ''!r}"
        print("  retry", attempt + 1, why, file=sys.stderr, flush=True)
        time.sleep(15 * (attempt + 1))
    return best, cost


def route(model, system, questions):
    chunks = [questions[s:s + BATCH] for s in range(0, len(questions), BATCH)]
    with ThreadPoolExecutor(WORKERS) as ex:
        res = list(ex.map(lambda c: ask(model, system, c), chunks))
    out = []
    for c, (got, _) in zip(chunks, res):
        out += [got.get(i + 1) for i in range(len(c))]
    return out, sum(cost for _, cost in res)


def run(model, per=None):
    """per: use only the first `per` rows of each draw (a cheaper first look); the file name says so."""
    out_f = ROOT / "out" / f"dev_judge_mcq_{model}{'' if per is None else f'_first{per}'}.json"
    res = json.loads(out_f.read_text()) if out_f.exists() else {}
    cost = res.pop("_meta", {}).get("cost_usd", 0.0)
    t0 = time.time()
    for m in json.loads((D / "manifest.json").read_text()):
        key = f"{m['source']}_{m['draw']}"
        if key in res and not any(x["direct"] is None or x["cot"] is None for x in res[key]["rows"]):
            continue
        rows = [json.loads(x) for x in (D / m["path"]).read_text().splitlines()][:per]
        q = [r["prompt"] for r in rows]
        d, c1 = route(model, DIRECT, q)
        c, c2 = route(model, COT, q)
        cost += c1 + c2
        res[key] = {"source": m["source"], "draw": m["draw"],
                    "rows": [{"direct": a, "cot": b, "label": r["completion"], "wrong": r["wrong"]} for a, b, r in zip(d, c, rows)]}
        conf = [x for x in res[key]["rows"] if x["direct"] and x["direct"] == x["cot"]]
        print(key, f"confident {len(conf)}/{len(rows)}", f"disagree {sum(x['direct'] != x['label'] for x in conf) / max(1, len(conf)):.3f}",
              f"missing {sum(x['direct'] is None for x in res[key]['rows'])}+{sum(x['cot'] is None for x in res[key]['rows'])}",
              f"${cost:.2f}", f"{time.time() - t0:.0f}s", flush=True)
        out_f.write_text(json.dumps({**res, "_meta": {"model": model, "backend": "claude command line, print mode, no tools",
                                                      "batch": BATCH, "cost_usd": round(cost, 4)}}))


if __name__ == "__main__":
    {"run": lambda: run(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None)}[sys.argv[1]]()
