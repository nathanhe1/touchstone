"""Flags, grade and fair value. Pure functions, so the rules are easy to test and to read.

Rules (each one is printed in the report next to the numbers it used):

* The gain that counts is the forecast gain at the target size *above placebo*
  (shuffled answers for a dataset, shuffled rewards for an environment).
* Grade from that net gain: A >= 5 pts, B >= 2, C >= 0.5, otherwise D; F if
  training measurably hurts the held-out suite.
* A grade needs the gain to be measurable: if the measured net gain at the
  largest trained rung has a 90% interval that includes zero, the grade is at
  most C and nothing is priced.
* Caps: gameable grader -> D at best; held-out contamination over 5% -> D at
  best; reward climbs without held-out gain (transfer gap) -> D at best; mostly
  free public data (>= 50%) -> C at best.
* Price per item = net gain (pts) x $ per point x share not already free
  / unique items. Zero when any blocking flag fires: gameable grader,
  contamination, transfer gap, or no measurable gain.
"""
from __future__ import annotations

HACK_LIMIT = 0.2
CONTAM_LIMIT = 0.05
PUBLIC_LIMIT = 0.5   # half or more already free: grade capped at D, priced on the novel share
PUBLIC_BLOCK = 0.8   # four fifths or more already free: a copy, not priced
ORDER = "ABCDF"


def _cap(g: str, worst: str) -> str:
    return max(g, worst, key=ORDER.index)


def flags_for(r: dict) -> list[dict]:
    """r: the measurements. Returns [{'code','severity','text'}]."""
    f = []
    if r.get("hackability", 0) >= HACK_LIMIT or r.get("grader_flagged"):
        f.append({"code": "gameable_grader", "severity": "block",
                  "text": f"Gameable grader: '{r.get('worst_exploit')}' collects {100 * r.get('hackability', 0):.0f}% reward "
                          "without solving the task."})
    if r.get("contamination", 0) > CONTAM_LIMIT:
        f.append({"code": "contaminated", "severity": "block",
                  "text": f"Overlaps the held-out suite ({100 * r['contamination']:.1f}%, exact, near-duplicate or "
                          "reworded matches). Held-out gains are inflated; not priced."})
    if r.get("transfer_gap"):
        f.append({"code": "transfer_gap", "severity": "block",
                  "text": "Training reward climbs but the held-out suite does not improve: the model is learning the "
                          "grader, not the skill."})
    if r.get("public_overlap", 0) >= PUBLIC_LIMIT:
        blocked = r["public_overlap"] >= PUBLIC_BLOCK
        f.append({"code": "copied_from_public", "severity": "block" if blocked else "discount",
                  "text": f"{100 * r['public_overlap']:.0f}% of items are already in free public data"
                          + ("; essentially a copy, not priced." if blocked else "; priced only on the novel share.")})
    if r.get("dup_rate", 0) >= 0.5:
        f.append({"code": "duplicated", "severity": "discount",
                  "text": f"{100 * r['dup_rate']:.0f}% of items are exact repeats; value is priced per unique item."})
    if r.get("no_signal"):
        f.append({"code": "no_learning_signal", "severity": "info",
                  "text": f"The trained models almost never solve these tasks (reward {100 * r['no_signal']:.1f}%), so "
                          "RL had nothing to learn from. The tasks may be too hard for these sizes: run the full mode "
                          "(up to 1.7B) or use larger models before concluding the environment has no value."})
    if not r.get("measurable", False):
        f.append({"code": "no_measurable_gain", "severity": "block",
                  "text": "No measurable gain above placebo on the held-out suite at the largest trained size."})
    if r.get("harmful"):
        f.append({"code": "harmful", "severity": "block",
                  "text": "Training on this material measurably lowers held-out accuracy."})
    return f


def grade(net_gain: float, flags: list[dict]) -> str:
    codes = {x["code"] for x in flags}
    if "harmful" in codes:
        return "F"
    if any(x["code"] == "copied_from_public" and x["severity"] == "block" for x in flags):
        return "F"  # a copy of free data: the buyer already has it
    g = "A" if net_gain >= 5 else "B" if net_gain >= 2 else "C" if net_gain >= 0.5 else "D"
    if codes & CAP_D:
        g = _cap(g, "D")
    if "duplicated" in codes:
        g = _cap(g, "C")
    return g


# Any of these caps the grade at D: the measured gain is absent, untrustworthy, or mostly free.
CAP_D = {"no_measurable_gain", "gameable_grader", "answer_leakage", "contaminated", "transfer_gap",
         "copied_from_public", "noisy_labels", "off_topic"}


def fair_value(net_gain: float, flags: list[dict], unique_items: int, public_overlap: float,
               dollars_per_point: float) -> dict:
    blocked = [x["code"] for x in flags if x["severity"] == "block"]
    novel = max(0.0, 1.0 - public_overlap)
    if blocked or net_gain <= 0 or unique_items <= 0:
        return {"per_item": 0.0, "total": 0.0, "blocked_by": blocked, "novel_share": round(novel, 3)}
    total = net_gain * dollars_per_point * novel
    return {"per_item": round(total / unique_items, 2), "total": round(total, 0), "blocked_by": [],
            "novel_share": round(novel, 3)}
