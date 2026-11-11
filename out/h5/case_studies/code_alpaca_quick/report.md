# Touchstone appraisal: code_alpaca_20k

**Grade D** · fair value **$0.00 per example** · forecast net gain at 1.7B: **+0.0 pts** (range +0.0 to +0.0) on the held-out suite

**Flags**

- **no_measurable_gain** (block): No measurable gain above placebo on the held-out suite at the largest trained size.

## What was appraised

- Dataset: `/workspace/case_inputs/code_alpaca_20k.json`
- SHA-256: `2cabb4ceaf69871633e0a5eab7cdb547863f3a6b5bd7b9a712981fb856610a0f`
- Items: 20,016 (20,016 unique)
- Skipped: 6 of 20,022 rows could not be read and were left out (for example: code_alpaca_20k.json:record 7955: empty 'instruction' or 'output')
- Mode: quick · runtime 1 min 4 s
- Models (real open weights, LoRA rank 16): 135M = `HuggingFaceTB/SmolLM2-135M-Instruct`

## Held-out suite

- Suite: **humaneval_suite** (/workspace/case_inputs/humaneval_suite.jsonl (subset of 150)), 150 items
- Domain: humaneval_suite
- user-supplied suite from humaneval_suite.jsonl
- Never used for training. 150 of 150 suite items have no match in the appraised material; gains are also reported on that untouched subset.

## Transfer to the held-out suite

Accuracy points gained after training, with 90% bootstrap intervals over suite items (averaged over seeds). *Placebo* trains on the same prompts with answers shuffled between examples; *net* is material minus placebo, the value of the content itself.

| Size | Seeds | Base acc | After acc | Gain (pts) | Placebo gain | Net gain | Gain, untouched items | Prob. gain (pts) |
|---|---|---|---|---|---|---|---|---|
| 135M | 1 | 0.0% | 0.0% | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [-0.0, +0.1] |

*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Overlap

- With the held-out suite: **0.0%** of suite items appear in the material; **0.0%** of the material matches the suite (exact 0.0%, near-duplicate 0.0%, reworded 0.0%)
- With free public data (none (no public baseline for this domain; pass --public)): **0.0%**
- Internal duplicates: 0.0%

## Forecast at 1.7B

Method: **rank_largest**. No calibration sweep exists for this suite, so the forecast is the gain measured at 135M (the DataDecide default: rank at the largest affordable size). Treat it as a ranking signal; its scale at 1.7B is not validated.

| | Point | Range |
|---|---|---|
| material | +0.0 pts | +0.0 to +0.0 |
| placebo | +0.0 pts | +0.0 to +0.0 |
| net | +0.0 pts | +0.0 to +0.0 |

Smooth score (probability on the right answer against near misses), ranked at 135M: -0.0 pts (-0.0 to -0.0). This is a secondary signal: it predicts the larger model's smooth score well, but neither it nor accuracy at the small size reliably predicts the larger model's accuracy (see METHOD.md for the measured decision accuracies).

Buyer models larger than 1.7B are not forecast: we have not validated the method beyond the largest size we can train, and RL/SFT gains often shrink as base models get stronger.

## Grade and fair value

- Grade **D** from net gain +0.0 pts (A >= 5, B >= 2, C >= 0.5, else D; F if training measurably hurts), capped by the flags above.
- Not priced: blocked by no_measurable_gain.
- $ per point is an assumption (set with --dollars-per-point), not a measurement.

## Limits of this appraisal

- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale better than absolute gains do.
- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).
- The held-out suite measures one domain. Skills outside it are not credited.
- See METHOD.md for how each number is computed and validated.
