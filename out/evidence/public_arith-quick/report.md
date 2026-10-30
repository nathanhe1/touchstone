# Touchstone appraisal: Public Addition (free)

**Grade F** · fair value **$0.00 per task** · forecast net gain at 1.7B: not measured (quick mode stopped after screening)

**Flags**

- **copied_from_public** (block): 100% of items are already in free public data; essentially a copy, not priced.
- **screen_only** (info): Quick mode stopped after screening: the problems above already rule out a price, so no model was trained. Run the full mode for training measurements.

## What was appraised

- RL environment: `/Users/nathanhe/Downloads/touchstone/.claude/worktrees/agent-a733cb471ee107784/envs/public_arith`
- SHA-256: `55d839a93fe7a177eb69ece283d294415d875c44c11ffdc79469186de3572cba`
- Items: 2,000 (1,752 unique)
- Mode: quick · runtime 0 min 19 s
- Models (real open weights, LoRA rank 16): 

## Held-out suite

- Suite: **arithmetic** (built-in, seed 90210 (subset of 150)), 150 items
- Domain: multi-digit addition stated in words (2-digit and 3-digit operands)
- 100 items each of 2+2, 3+2 and 3+3 digit addition, in four phrasings unused by the sample vendors.
- Never used for training. 150 of 150 suite items have no match in the appraised material; gains are also reported on that untouched subset.

## Transfer to the held-out suite

Accuracy points gained after training, with 90% bootstrap intervals over suite items (averaged over seeds). *Placebo* trains on the same prompts with rewards shuffled within each batch; *net* is material minus placebo, the value of the content itself.

| Size | Seeds | Base acc | After acc | Gain (pts) | Placebo gain | Net gain | Gain, untouched items | Prob. gain (pts) |
|---|---|---|---|---|---|---|---|---|
No model was trained in this run: quick mode stopped after screening (see flags).


*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Grader audit

Known-wrong and junk answers fed to `verify()` on 200 sampled tasks (reference answers available). Hackability = most reward any probe earns; flagged at 20%.

| Probe | Reward earned |
|---|---|
| empty answer | 0% |
| echo the prompt | 0% |
| digit soup | 0% |
| letter soup | 0% |
| copy a prompt span (last-1) | 0% |
| near miss | 0% |
| same shape, wrong content | 0% |
| hedge: right then wrong | 0% |
| hedge: wrong or right | 0% |
| answer buried in junk | 0% |
| model's own wrong answers | 0% |

The grader accepts 100% of reference answers. The answer appears verbatim in 0% of prompts.
| Size | Env reward before | after (material) | after (placebo) |
|---|---|---|---|

## Overlap

- With the held-out suite: **0.0%** of suite items appear in the material; **0.0%** of the material matches the suite (exact 0.0%, near-duplicate 0.0%, reworded 0.0%)
- With free public data (Public Addition (free) environment): **100.0%**
- Internal duplicates: 12.4%
  - public match (exact): "Calculate 65 + 41. Reply with only the number." ~ "Calculate 65 + 41. Reply with only the number."
  - public match (exact): "Calculate 42 + 81. Reply with only the number." ~ "Calculate 42 + 81. Reply with only the number."

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
