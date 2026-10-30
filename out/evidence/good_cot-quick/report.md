# Touchstone appraisal: good_cot

**Grade A** · fair value **$2,916 per example** · forecast net gain at 1.7B: **+9.3 pts** (range +3.0 to +15.6) on the held-out suite

No flags.

## What was appraised

- Dataset: `/Users/nathanhe/Downloads/touchstone/.claude/worktrees/agent-a733cb471ee107784/examples/datasets/good_cot.jsonl`
- SHA-256: `1a61deea15b5bbcb082a9a3bba1e4c3db433bd20bcfcbc687b1825acb2c84bd0`
- Items: 800 (800 unique)
- Mode: quick · runtime 2 min 10 s
- Models (real open weights, LoRA rank 16): 135M = `HuggingFaceTB/SmolLM2-135M-Instruct`

## Held-out suite

- Suite: **word_math** (built-in, seed 90210 (subset of 150)), 150 items
- Domain: grade-school arithmetic word problems (one or two steps, whole numbers)
- 10 private templates (purchases, rates, groups, change, multi-step add/sub/mul) x 30 items each; answers are whole numbers.
- Never used for training. 150 of 150 suite items have no match in the appraised material; gains are also reported on that untouched subset.

## Transfer to the held-out suite

Accuracy points gained after training, with 90% bootstrap intervals over suite items (averaged over seeds). *Placebo* trains on the same prompts with answers shuffled between examples; *net* is material minus placebo, the value of the content itself.

| Size | Seeds | Base acc | After acc | Gain (pts) | Placebo gain | Net gain | Gain, untouched items | Prob. gain (pts) |
|---|---|---|---|---|---|---|---|---|
| 135M | 1 | 11.3% | 20.7% | +9.3 [+3.3, +15.3] | -6.7 [-10.7, -2.7] | +9.3 [+3.3, +15.3] | +9.3 [+3.3, +15.3] | +11.0 [+4.8, +16.9] |

*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Overlap

- With the held-out suite: **0.0%** of suite items appear in the material; **0.0%** of the material matches the suite (exact 0.0%, near-duplicate 0.0%, reworded 0.0%)
- With free public data (GSM8K train (7,473 public problems)): **0.0%**
- Internal duplicates: 0.0%

## Forecast at 1.7B

Method: **rank_largest**. No calibration sweep exists for this suite, so the forecast is the gain measured at 135M (the DataDecide default: rank at the largest affordable size). Treat it as a ranking signal; its scale at 1.7B is not validated.

| | Point | Range |
|---|---|---|
| material | +9.3 pts | +3.0 to +15.6 |
| placebo | -6.7 pts | -11.1 to -2.3 |
| net | +9.3 pts | +3.0 to +15.6 |

Smooth score (probability on the right answer against near misses), ranked at 135M: +11.0 pts (+4.8 to +16.9). In validation this ranking picked the larger model's winner far more reliably than accuracy (91% vs 56% of pairs on 16 RL environments); use it to compare materials.

Buyer models larger than 1.7B are not forecast: we have not validated the method beyond the largest size we can train, and RL/SFT gains often shrink as base models get stronger.

## Grade and fair value

- Grade **A** from net gain +9.3 pts (A >= 5, B >= 2, C >= 0.5, else D; F if training measurably hurts), capped by the flags above.
- Value = 9.33 pts x $250,000 per point x 1.00 (share not already free) = $2,332,500, over 800 unique items = **$2,916 per item**.
- $ per point is an assumption (set with --dollars-per-point), not a measurement.

## Limits of this appraisal

- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale better than absolute gains do.
- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).
- The held-out suite measures one domain. Skills outside it are not credited.
- See METHOD.md for how each number is computed and validated.
