"""h5 soft score: chance-corrected probability on the correct answer, per suite item (reference implementation).

Definition, fixed in METHOD.md (h5) before any final run:

- Letter items (classification, multiple choice): the candidates are the option letters shown in the prompt. The score is
  P(correct letter) / P(any option letter), each letter scored alone as the first token of the reply, with no end-of-reply
  token: base-model ladders never trained an end token, so its probability before training is noise.
- Numeric items: the candidates are the answer and 4 near misses from `suites.numeric_distractors` (seed fixed per item),
  each scored in the answer slot of the model's own greedy reply, exactly as the product's smooth score does.
- Chance correction: s = (p - c) / (1 - c), where c = 1 / (number of candidates). s is 0 at chance and 1 when all
  probability sits on the correct answer; it can be negative.

A run records `soft_base` and `soft_after` (the mean of s over the suite, before and after training, on the same items as
accuracy) and `soft_gain` = 100 x (soft_after - soft_base), in points like the accuracy gain.

    from h5_soft import soft_scores
    s = soft_scores(lm, items, replies)   # items: (prompt, answer, chance) as in h4_common; replies: greedy outputs
"""
import random
import re
import zlib

_OPT = re.compile(r"(?m)^([A-P])\) ")


def _letters(prompt):
    return _OPT.findall(prompt)


def candidates(prompt, answer, reply=None):
    """(answer, distractors, slot) for one item, or None if the item has no usable candidates."""
    opts = _letters(prompt)
    if opts and answer in opts:
        return answer, [x for x in opts if x != answer], ("", "")  # the letter alone, no end token
    if re.fullmatch(r"-?\d+", str(answer).strip()):
        from touchstone.measure import answer_slot
        from touchstone.suites import numeric_distractors
        rng = random.Random(zlib.crc32(prompt.encode()))
        slot = answer_slot(reply) if reply else None
        return str(answer).strip(), numeric_distractors(str(answer).strip(), rng), slot
    return None


def chance_corrected(p, n_candidates):
    c = 1.0 / n_candidates
    return (p - c) / (1.0 - c)


def soft_scores(lm, items, replies=None):
    """Per-item chance-corrected soft score. Items without usable candidates get None and are left out of the mean."""
    rows = []
    for i, it in enumerate(items):
        c = candidates(it[0], it[1], replies[i] if replies else None)
        rows.append(c)
    idx = [i for i, c in enumerate(rows) if c]
    if not idx:
        return [None] * len(items)
    probs = lm.candidate_probs([items[i][0] for i in idx], [rows[i][0] for i in idx], [rows[i][1] for i in idx],
                               [rows[i][2] for i in idx])
    out = [None] * len(items)
    for i, p in zip(idx, probs):
        out[i] = chance_corrected(p, 1 + len(rows[i][1]))
    return out


def mean_soft(scores):
    v = [x for x in scores if x is not None]
    return sum(v) / len(v) if v else None
