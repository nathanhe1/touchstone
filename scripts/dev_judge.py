"""DEV ONLY: reference-judge label audit on development data (dev, test v1, test v2; never test v3).

Results are written after every dataset, with per-item answers so that confidence rules can be
re-scored offline. Resumable: finished datasets are skipped.

    python scripts/dev_judge.py qwen 60
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from touchstone import data, judge  # noqa: E402

E, T1, T2 = "examples/datasets/", "examples/redflags_test/datasets/", "examples/redflags_test2/datasets/"
CASES = [  # (path, percent of labels wrong; None = unknown-but-small real data)
    (E + "good_short", 0), (T2 + "d_clean_answer", 0), (T2 + "s_clean", 0), (E + "short_noisy_30", 30),
    (T2 + "d_noise40_answer_random", 40), (T2 + "s_noisy_30", 30), (T2 + "d_gsm8k_synonyms", None),
    (E + "v2_short_300", 0), (E + "v2_hard_short", 0), (T1 + "t_clean_short", 0), (T2 + "d_clean_answer_b", 0),
    (T2 + "d_clean_units", 0), (T2 + "s_clean_b", 0), (T1 + "t_strings_clean", 0), (T1 + "t_gsm8k_reworded", None),
    (T2 + "d_noise10_answer", 10), (E + "dev_short_noisy_60", 60), (E + "dev_short_shuffled", 100),
    (T1 + "t_shuffled_labels", 100), (T1 + "t_noisy_answer_only", None), (T2 + "d_noise40_answer_reverse", 40),
    (T2 + "d_noise100_units", 100), (T2 + "d_shuffled_answers", 100), (T2 + "s_noisy_scrambled", 50),
]

key, n = sys.argv[1], int(sys.argv[2])
judge.use_judge(key)
f = ROOT / "out" / f"dev_judge_{key}.json"
out = json.loads(f.read_text()) if f.exists() else {}
for path, noise in CASES:
    name = path.split("/")[-1]
    if name in out:
        continue
    t = time.time()
    r = judge.audit(data.load_dataset(ROOT / (path + ".jsonl")), n=n)
    r.update(noise=noise, seconds=round(time.time() - t))
    out[name] = r
    f.write_text(json.dumps(out))
    print(f"{key} {name:28s} noise {noise} conf {r['confident']}/{r['sampled']} disagree {r['disagree']} {r['seconds']}s "
          f"e.g. {r['rows'][:2]}", flush=True)
