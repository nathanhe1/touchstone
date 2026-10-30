# Touchstone appraisal: gsm8k_clone

**Grade F** · fair value **$0.00 per example** · forecast net gain at 1.7B: not measured (quick mode stopped after screening)

**Flags**

- **copied_from_public** (block): 100% of items are already in free public data; essentially a copy, not priced.
- **screen_only** (info): Quick mode stopped after screening: the problems above already rule out a price, so no model was trained. Run the full mode for training measurements.

## What was appraised

- Dataset: `/Users/nathanhe/Downloads/touchstone/.claude/worktrees/agent-a733cb471ee107784/examples/datasets/gsm8k_clone.jsonl`
- SHA-256: `254a47306b799c24f6e7d20511c97229ca559024b47a22816bbfa7487350e306`
- Items: 600 (600 unique)
- Mode: quick · runtime 0 min 7 s
- Models (real open weights, LoRA rank 16): 

## Held-out suite

- Suite: **word_math** (built-in, seed 90210 (subset of 150)), 150 items
- Domain: grade-school arithmetic word problems (one or two steps, whole numbers)
- 10 private templates (purchases, rates, groups, change, multi-step add/sub/mul) x 30 items each; answers are whole numbers.
- Never used for training. 150 of 150 suite items have no match in the appraised material; gains are also reported on that untouched subset.

## Transfer to the held-out suite

Accuracy points gained after training, with 90% bootstrap intervals over suite items (averaged over seeds). *Placebo* trains on the same prompts with answers shuffled between examples; *net* is material minus placebo, the value of the content itself.

| Size | Seeds | Base acc | After acc | Gain (pts) | Placebo gain | Net gain | Gain, untouched items | Prob. gain (pts) |
|---|---|---|---|---|---|---|---|---|
No model was trained in this run: quick mode stopped after screening (see flags).


*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Overlap

- With the held-out suite: **0.0%** of suite items appear in the material; **0.0%** of the material matches the suite (exact 0.0%, near-duplicate 0.0%, reworded 0.0%)
- With free public data (GSM8K train (7,473 public problems)): **100.0%**
- Internal duplicates: 0.0%
  - public match (exact): "The school band is having a car wash to raise money. Their goal is to collect $150. So far they have earned $10 each from three families and $5 each from 15 fam" ~ "The school band is having a car wash to raise money. Their goal is to collect $150. So far they have earned $10 each from three families and $5 each from 15 fam"
  - public match (exact): "Penny has $20. Penny buys 4 pairs of socks for $2 a pair and a hat for $7. How much money does Penny have left?" ~ "Penny has $20. Penny buys 4 pairs of socks for $2 a pair and a hat for $7. How much money does Penny have left?"

## Forecast at 1.7B

Method: **skipped**. Not forecast: training was skipped because a blocking flag fired during screening.

| | Point | Range |
|---|---|---|

Buyer models larger than 1.7B are not forecast: we have not validated the method beyond the largest size we can train, and RL/SFT gains often shrink as base models get stronger.

## Grade and fair value

- Grade **F** from the screening flags alone (rubric in METHOD.md).
- Not priced: blocked by copied_from_public.
- $ per point is an assumption (set with --dollars-per-point), not a measurement.

## Limits of this appraisal

- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale better than absolute gains do.
- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).
- The held-out suite measures one domain. Skills outside it are not credited.
- See METHOD.md for how each number is computed and validated.
