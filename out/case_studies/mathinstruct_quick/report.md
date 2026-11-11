# Touchstone appraisal: mathinstruct

**Grade D** · fair value **$0.00 per example** · forecast net gain at 1.7B: not measured (quick mode stopped after screening)

**Flags**

- **noisy_labels** (block): Many labels look wrong: 15% of worked solutions contain an arithmetic error.
- **screen_only** (info): Quick mode stopped after screening: the problems above already rule out a price, so no model was trained. Run the full mode for training measurements.

## What was appraised

- Dataset: `/Users/nathanhe/.cache/touchstone/case_studies/inputs/mathinstruct.jsonl`
- SHA-256: `50a0b2f46dbc1891f60169dc76166eee2e14767d95b190e3d17d61ba5549808b`
- Items: 262,038 (245,043 unique)
- Skipped: 1 of 262,039 rows could not be read and were left out (for example: mathinstruct.jsonl:18866: empty 'prompt' or 'completion')
- Mode: quick · runtime 52 min 28 s
- Models (real open weights, LoRA rank 16): 

## Held-out suite

- Suite: **math_test_suite** (/Users/nathanhe/.cache/touchstone/case_studies/inputs/math_test_suite.jsonl (subset of 149)), 149 items
- Domain: math_test_suite
- user-supplied suite from math_test_suite.jsonl
- Never used for training. 147 of 149 suite items have no match in the appraised material; gains are also reported on that untouched subset.

## Transfer to the held-out suite

Accuracy points gained after training, with 90% bootstrap intervals over suite items (averaged over seeds). *Placebo* trains on the same prompts with answers shuffled between examples; *net* is material minus placebo, the value of the content itself.

| Size | Seeds | Base acc | After acc | Gain (pts) | Placebo gain | Net gain | Gain, untouched items | Prob. gain (pts) |
|---|---|---|---|---|---|---|---|---|
No model was trained in this run: quick mode stopped after screening (see flags).


*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Overlap

- With the held-out suite: **2.7%** of suite items appear in the material; **0.0%** of the material matches the suite (exact 0.0%, near-duplicate 0.0%, reworded 0.0%)
- With free public data (none (no public baseline for this domain; pass --public)): **0.0%**
- Internal duplicates: 6.5%
  - suite match (near): "Determine the number of ways to arrange the letters of the word RADII." ~ "Determine the number of ways to arrange the letters of the word NINE."
  - suite match (near): "Determine the number of ways to arrange the letters of the word PROOF." ~ "Determine the number of ways to arrange the letters of the word NINE."

## Forecast at 1.7B

Method: **skipped**. Not forecast: training was skipped because a blocking flag fired during screening.

| | Point | Range |
|---|---|---|

Buyer models larger than 1.7B are not forecast: we have not validated the method beyond the largest size we can train, and RL/SFT gains often shrink as base models get stronger.

## Grade and fair value

- Grade **D** from the screening flags alone (rubric in METHOD.md).
- Not priced: blocked by noisy_labels.
- $ per point is an assumption (set with --dollars-per-point), not a measurement.

## Limits of this appraisal

- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale better than absolute gains do.
- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).
- The held-out suite measures one domain. Skills outside it are not credited.
- See METHOD.md for how each number is computed and validated.
