"""DEV ONLY (round 4): do two-route multiple choice and paired free-text checks travel across sources?

Dev sources only. Sources reserved for test v4 are never used here. Clean rows are real and unmodified; planted rows
have 30% wrong labels or swapped replies. Three draws each, resumable, MLX.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import h4_common as H4  # noqa: E402
import stress_real as S  # noqa: E402
from touchstone import judge  # noqa: E402
from touchstone.data import Example  # noqa: E402

F = ROOT / "out" / "dev_travel.json"
res = json.loads(F.read_text()) if F.exists() else {}


def ex(p, c):
    return Example([{"role": "user", "content": p}], c, {})


def mcq(name):
    return [ex(p.replace("\nReply with the letter only.", ""), a) for p, a, _ in H4.items(name, H4.SPLITS[name][0])]


src = S.sources()
M = {"arc": mcq("arc"), "openbook": mcq("openbook"), "csqa": mcq("csqa"), "sciq": mcq("sciq")}
T = {"dolly": src["dolly"], "no_robots": src["unseen_no_robots"]}


def wrong_letter(e, rng):
    opts = [c for c in "ABCD" if c != e.completion]
    return Example(e.messages, rng.choice(opts), {})


for kind, D in (("mcq", M), ("text", T)):
    for name, rows in D.items():
        for noise in (0, 30):
            for d in range(3):
                key = f"{kind}|{name}|{noise}|{d}"
                if key in res:
                    continue
                rng = random.Random(100 + d)
                sub = rng.sample(rows, min(100, len(rows)))
                if noise:
                    pick = set(rng.sample(range(len(sub)), 30))
                    if kind == "mcq":
                        sub = [wrong_letter(e, rng) if i in pick else e for i, e in enumerate(sub)]
                    else:
                        sub = [Example(e.messages, sub[(i + 7) % len(sub)].completion, {}) if i in pick else e for i, e in enumerate(sub)]
                r = judge.audit_mcq2(sub, n=100, seed=d) if kind == "mcq" else judge.audit_pair(sub, n=100, seed=d)
                res[key] = r
                F.write_text(json.dumps(res, indent=1))
                print(key, r, flush=True)
