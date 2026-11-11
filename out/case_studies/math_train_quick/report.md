# Touchstone appraisal: math_train

**Grade D** · fair value **$0.00 per example** · forecast net gain at 1.7B: **-0.7 pts** (range -3.2 to +1.9) on the held-out suite

**Flags**

- **no_measurable_gain** (block): No measurable gain above placebo on the held-out suite at the largest trained size.

## What was appraised

- Dataset: `/Users/nathanhe/.cache/touchstone/case_studies/inputs/math_train.jsonl`
- SHA-256: `e89f10bac98d166688b13b70d035968b69cc10d044749b6f627255756303745e`
- Items: 7,500 (7,500 unique)
- Mode: quick · runtime 37 min 21 s
- Models (real open weights, LoRA rank 16): 135M = `HuggingFaceTB/SmolLM2-135M-Instruct`

## Held-out suite

- Suite: **math_test_suite** (/Users/nathanhe/.cache/touchstone/case_studies/inputs/math_test_suite.jsonl (subset of 149)), 149 items
- Domain: math_test_suite
- user-supplied suite from math_test_suite.jsonl
- Never used for training. 147 of 149 suite items have no match in the appraised material; gains are also reported on that untouched subset.

## Transfer to the held-out suite

Accuracy points gained after training, with 90% bootstrap intervals over suite items (averaged over seeds). *Placebo* trains on the same prompts with answers shuffled between examples; *net* is material minus placebo, the value of the content itself.

| Size | Seeds | Base acc | After acc | Gain (pts) | Placebo gain | Net gain | Gain, untouched items | Prob. gain (pts) |
|---|---|---|---|---|---|---|---|---|
| 135M | 1 | 2.0% | 1.3% | -0.7 [-3.4, +2.0] | +0.0 [-2.7, +2.7] | -0.7 [-3.4, +2.0] | -0.7 [-3.4, +2.0] | +1.2 [-2.0, +4.8] |

*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Overlap

- With the held-out suite: **5.0%** of suite items appear in the material; **0.1%** of the material matches the suite (exact 0.0%, near-duplicate 0.1%, reworded 0.0%)
- With free public data (none (no public baseline for this domain; pass --public)): **0.0%**
- Internal duplicates: 0.0%
  - suite match (near): "Determine the number of ways to arrange the letters of the word RADII." ~ "Determine the number of ways to arrange the letters of the word NINE."
  - suite match (near): "Determine the number of ways to arrange the letters of the word MADAM." ~ "Determine the number of ways to arrange the letters of the word NINE."

## Forecast at 1.7B

Method: **rank_largest**. No calibration sweep exists for this suite, so the forecast is the gain measured at 135M (the DataDecide default: rank at the largest affordable size). Treat it as a ranking signal; its scale at 1.7B is not validated.

| | Point | Range |
|---|---|---|
| material | -0.7 pts | -3.2 to +1.9 |
| placebo | +0.0 pts | -2.8 to +2.8 |
| net | -0.7 pts | -3.2 to +1.9 |

Smooth score (probability on the right answer against near misses), ranked at 135M: -2.1 pts (-4.6 to +0.6). This is a secondary signal: it predicts the larger model's smooth score well, but neither it nor accuracy at the small size reliably predicts the larger model's accuracy (see METHOD.md for the measured decision accuracies).

Buyer models larger than 1.7B are not forecast: we have not validated the method beyond the largest size we can train, and RL/SFT gains often shrink as base models get stronger.

## Grade and fair value

- Grade **D** from net gain -0.7 pts (A >= 5, B >= 2, C >= 0.5, else D; F if training measurably hurts), capped by the flags above.
- Not priced: blocked by no_measurable_gain.
- $ per point is an assumption (set with --dollars-per-point), not a measurement.

## Limits of this appraisal

- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale better than absolute gains do.
- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).
- The held-out suite measures one domain. Skills outside it are not credited.
- See METHOD.md for how each number is computed and validated.
