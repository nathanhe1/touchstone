# Touchstone appraisal: contaminated

**Grade D** · fair value **$0.00 per example** · forecast net gain at 1.7B: **+4.2 pts** (range -3.3 to +11.6) on the held-out suite

**Flags**

- **contaminated** (block): Overlaps the held-out suite (45.0%, exact, near-duplicate or reworded matches). Held-out gains are inflated; not priced.

## What was appraised

- Dataset: `/Users/nathanhe/Downloads/touchstone/.claude/worktrees/agent-a733cb471ee107784/examples/datasets/contaminated.jsonl`
- SHA-256: `9a70eec42e5c54fb67b98ca0bafea5c8db9713c8826b8d534e545d3d574e2297`
- Items: 600 (600 unique)
- Mode: quick · runtime 3 min 38 s
- Models (real open weights, LoRA rank 16): 135M = `HuggingFaceTB/SmolLM2-135M-Instruct`

## Held-out suite

- Suite: **word_math** (built-in, seed 90210 (subset of 120)), 120 items
- Domain: grade-school arithmetic word problems (one or two steps, whole numbers)
- 10 private templates (purchases, rates, groups, change, multi-step add/sub/mul) x 30 items each; answers are whole numbers.
- Never used for training. 66 of 120 suite items have no match in the appraised material; gains are also reported on that untouched subset.

## Transfer to the held-out suite

Accuracy points gained after training, with 90% bootstrap intervals over suite items (averaged over seeds). *Placebo* trains on the same prompts with answers shuffled between examples; *net* is material minus placebo, the value of the content itself.

| Size | Seeds | Base acc | After acc | Gain (pts) | Placebo gain | Net gain | Gain, untouched items | Prob. gain (pts) |
|---|---|---|---|---|---|---|---|---|
| 135M | 1 | 14.2% | 18.3% | +4.2 [-3.3, +11.7] | -14.2 [-20.0, -9.2] | +4.2 [-3.3, +11.7] | +3.0 [-7.6, +13.6] | +12.5 [+5.7, +19.6] |

*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Overlap

- With the held-out suite: **45.0%** of suite items appear in the material; **9.5%** of the material matches the suite (exact 4.3%, near-duplicate 5.2%, reworded 0.0%)
- With free public data (GSM8K train (7,473 public problems)): **0.0%**
- Internal duplicates: 0.0%
  - suite match (exact): "A book costs 15 dollars and a pen costs 9 dollars. How much do 5 books and one pen cost in dollars?" ~ "A book costs 15 dollars and a pen costs 9 dollars. How much do 5 books and one pen cost in dollars?"
  - suite match (near): "A water tank holds 268 liters. After that, 67 liters leak out and 49 liters are added. How many liters are in the tank now?" ~ "A water tank holds 268 liters. Then 67 liters leak out and 49 liters are added. How many liters are in the tank now?"

## Forecast at 1.7B

Method: **rank_largest**. No calibration sweep exists for this suite, so the forecast is the gain measured at 135M (the DataDecide default: rank at the largest affordable size). Treat it as a ranking signal; its scale at 1.7B is not validated.

| | Point | Range |
|---|---|---|
| material | +4.2 pts | -3.3 to +11.6 |
| placebo | -14.2 pts | -19.5 to -8.8 |
| net | +4.2 pts | -3.3 to +11.6 |

Buyer models larger than 1.7B are not forecast: we have not validated the method beyond the largest size we can train, and RL/SFT gains often shrink as base models get stronger.

## Grade and fair value

- Grade **D** from net gain +4.2 pts (A >= 5, B >= 2, C >= 0.5, else D; F if training measurably hurts), capped by the flags above.
- Not priced: blocked by contaminated.
- $ per point is an assumption (set with --dollars-per-point), not a measurement.

## Limits of this appraisal

- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale better than absolute gains do.
- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).
- The held-out suite measures one domain. Skills outside it are not credited.
- See METHOD.md for how each number is computed and validated.
