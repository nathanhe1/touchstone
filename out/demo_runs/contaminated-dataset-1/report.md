# Touchstone appraisal: contaminated_word_problems

**Grade D** · fair value **$0.00 per example** · forecast net gain at 1.7B: not measured (quick mode stopped after screening)

**Flags**

- **contaminated** (block): Overlaps the held-out suite (46.0%, exact, near-duplicate or reworded matches). Held-out gains are inflated; not priced.
- **screen_only** (info): Quick mode stopped after screening: the problems above already rule out a price, so no model was trained. Run the full mode for training measurements.

## What was appraised

- Dataset: `/Users/nathanhe/Downloads/touchstone/.claude/worktrees/agent-a733cb471ee107784/examples/demo/contaminated_word_problems.jsonl`
- SHA-256: `291b41f4fad0f35e4136db80ed42c44d1a1274d70e1e41fc4130ef8f495ed5e3`
- Items: 600 (600 unique)
- Mode: quick · runtime 2 min 7 s
- Models (real open weights, LoRA rank 16): 

## Held-out suite

- Suite: **word_math** (built-in, seed 90210 (subset of 150)), 150 items
- Domain: grade-school arithmetic word problems (one or two steps, whole numbers)
- 10 private templates (purchases, rates, groups, change, multi-step add/sub/mul) x 30 items each; answers are whole numbers.
- Never used for training. 81 of 150 suite items have no match in the appraised material; gains are also reported on that untouched subset.

## Transfer to the held-out suite

Accuracy points gained after training, with 90% bootstrap intervals over suite items (averaged over seeds). *Placebo* trains on the same prompts with answers shuffled between examples; *net* is material minus placebo, the value of the content itself.

| Size | Seeds | Base acc | After acc | Gain (pts) | Placebo gain | Net gain | Gain, untouched items | Prob. gain (pts) |
|---|---|---|---|---|---|---|---|---|
No model was trained in this run: quick mode stopped after screening (see flags).


*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Overlap

- With the held-out suite: **46.0%** of suite items appear in the material; **11.5%** of the material matches the suite (exact 5.8%, near-duplicate 5.7%, reworded 0.0%)
- With free public data (GSM8K train+test, SVAMP, ASDiv (12,097 public problems)): **0.0%**
- Internal duplicates: 0.0%
  - suite match (exact): "A book costs 15 dollars and a pen costs 9 dollars. How much do 5 books and one pen cost in dollars?" ~ "A book costs 15 dollars and a pen costs 9 dollars. How much do 5 books and one pen cost in dollars?"
  - suite match (exact): "A movie ticket costs 8 dollars. A family buys 3 tickets and pays with a 100 dollar bill. How much change do they get in dollars?" ~ "A movie ticket costs 8 dollars. A family buys 3 tickets and pays with a 100 dollar bill. How much change do they get in dollars?"

## Forecast at 1.7B

Method: **skipped**. Not forecast: training was skipped because a blocking flag fired during screening.

| | Point | Range |
|---|---|---|

Buyer models larger than 1.7B are not forecast: we have not validated the method beyond the largest size we can train, and RL/SFT gains often shrink as base models get stronger.

## Grade and fair value

- Grade **D** from the screening flags alone (rubric in METHOD.md).
- Not priced: blocked by contaminated.
- $ per point is an assumption (set with --dollars-per-point), not a measurement.

## Limits of this appraisal

- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale better than absolute gains do.
- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).
- The held-out suite measures one domain. Skills outside it are not credited.
- See METHOD.md for how each number is computed and validated.
