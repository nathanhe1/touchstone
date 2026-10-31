# Touchstone appraisal: good_word_problems

**Grade A** · fair value **$76.35 per example** · forecast net gain at 1.7B: **+7.3 pts** (range +1.7 to +12.9) on the held-out suite

No flags.

## What was appraised

- Dataset: `/Users/nathanhe/Downloads/touchstone/.claude/worktrees/agent-a733cb471ee107784/examples/demo/good_word_problems.jsonl`
- SHA-256: `dd9733471031cd007e651dba9e5b6429f0acba6d0b63a93e418e2c2a519bc04f`
- Items: 400 (400 unique)
- Mode: quick · runtime 6 min 49 s
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
| 135M | 1 | 11.3% | 18.7% | +7.3 [+2.0, +13.3] | -6.0 [-10.7, -1.3] | +7.3 [+2.0, +13.3] | +7.3 [+2.0, +13.3] | +9.1 [+3.6, +14.9] |

*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Overlap

- With the held-out suite: **0.0%** of suite items appear in the material; **0.0%** of the material matches the suite (exact 0.0%, near-duplicate 0.0%, reworded 0.0%)
- With free public data (GSM8K train+test, SVAMP, ASDiv (12,097 public problems)): **0.0%**
- Internal duplicates: 0.0%

## Forecast at 1.7B

Method: **rank_largest**. No calibration sweep exists for this suite, so the forecast is the gain measured at 135M (the DataDecide default: rank at the largest affordable size). Treat it as a ranking signal; its scale at 1.7B is not validated.

| | Point | Range |
|---|---|---|
| material | +7.3 pts | +1.7 to +12.9 |
| placebo | -6.0 pts | -10.5 to -1.5 |
| net | +7.3 pts | +1.7 to +12.9 |

Smooth score (probability on the right answer against near misses), ranked at 135M: +9.1 pts (+3.6 to +14.9). This is a secondary signal: it predicts the larger model's smooth score well, but neither it nor accuracy at the small size reliably predicts the larger model's accuracy (see METHOD.md for the measured decision accuracies).

Buyer models larger than 1.7B are not forecast: we have not validated the method beyond the largest size we can train, and RL/SFT gains often shrink as base models get stronger.

## Grade and fair value

- Grade **A** from net gain +7.3 pts (A >= 5, B >= 2, C >= 0.5, else D; F if training measurably hurts), capped by the flags above.
- Value = 7.33 pts x $5,000 per point x 1.00 (share not already free) = $30,542, over 400 unique items = **$76.35 per item**.
- $ per point is an assumption (set with --dollars-per-point), not a measurement.

## Limits of this appraisal

- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale better than absolute gains do.
- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).
- The held-out suite measures one domain. Skills outside it are not credited.
- See METHOD.md for how each number is computed and validated.
