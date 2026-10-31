"""Do the torch and MLX judges reach the same decisions? Compares two dev_judge files on identical rows.

    python scripts/compare_judge.py out/dev_judge_qwen.json out/gpu3/dev_judge_qwen_torch.json

Bar, set before any result: same flag decision on every dataset with a truth label, identical rows in the
two files, and at least 85% of items matching on both routes. Otherwise backends stay separate.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import judge, screen  # noqa: E402

a, b = (json.loads(Path(x).read_text()) for x in sys.argv[1:3])
same_flag = rows_same = rows = 0
diffs = []
names = [n for n in a if n in b]
aligned = all([r["label"] for r in a[n]["rows"]] == [r["label"] for r in b[n]["rows"]] for n in names)
for n in names:
    ra, rb = a[n]["rows"], b[n]["rows"]
    ta, tb = judge._tally(ra), judge._tally(rb)
    fa, fb = screen.judge_noisy(ta), screen.judge_noisy(tb)
    same_flag += fa == fb
    m = sum(x["cot"] == y["cot"] and x["pal"] == y["pal"] for x, y in zip(ra, rb))
    rows_same += m
    rows += len(ra)
    print(f"{n:28s} noise {str(a[n]['noise']):5} mlx {ta['confident']:2} {ta['disagree']} flag {fa} | torch {tb['confident']:2} "
          f"{tb['disagree']} flag {fb} | same rows {m}/{len(ra)}")
    if fa != fb:
        diffs.append(n)
share = rows_same / rows
ok = aligned and not diffs and share >= 0.85
print(f"datasets {len(names)}; aligned {aligned}; same flag {same_flag}/{len(names)}; rows matching {share:.3f}; disagree on {diffs}")
print("PASS: backends agree" if ok else "FAIL: keep backends separate")
