# Touchstone appraisal: offtopic

**Grade D** · fair value **$0.00 per example** · forecast net gain at 1.7B: **-0.7 pts** (range -4.5 to +3.1) on the held-out suite

**Flags**

- **off_topic** (discount): 100% of items are unrelated to the held-out domain; they cannot raise the skill being measured.
- **no_measurable_gain** (block): No measurable gain above placebo on the held-out suite at the largest trained size.

## What was appraised

- Dataset: `/Users/nathanhe/Downloads/touchstone/.claude/worktrees/agent-a733cb471ee107784/examples/datasets/offtopic.jsonl`
- SHA-256: `f4dac3faeae75c22daf5e1a5cdde7942f0ea1e3514af681edc060d8f965ae6ec`
- Items: 800 (799 unique)
- Mode: quick · runtime 3 min 13 s
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
| 135M | 1 | 11.3% | 10.7% | -0.7 [-4.0, +3.3] | -7.3 [-11.3, -2.7] | -0.7 [-4.0, +3.3] | -0.7 [-4.0, +3.3] | -0.2 [-5.4, +5.0] |

*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Overlap

- With the held-out suite: **0.0%** of suite items appear in the material; **0.0%** of the material matches the suite (exact 0.0%, near-duplicate 0.0%, reworded 0.0%)
- With free public data (GSM8K train (7,473 public problems)): **0.0%**
- Internal duplicates: 0.1%

## Forecast at 1.7B

Method: **rank_largest**. No calibration sweep exists for this suite, so the forecast is the gain measured at 135M (the DataDecide default: rank at the largest affordable size). Treat it as a ranking signal; its scale at 1.7B is not validated.

| | Point | Range |
|---|---|---|
| material | -0.7 pts | -4.5 to +3.1 |
| placebo | -7.3 pts | -11.8 to -2.8 |
| net | -0.7 pts | -4.5 to +3.1 |

Smooth score (probability on the right answer against near misses), ranked at 135M: -0.2 pts (-5.4 to +5.0). In validation this ranking picked the larger model's winner far more reliably than accuracy (91% vs 56% of pairs on 16 RL environments); use it to compare materials.

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
