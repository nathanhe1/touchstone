# Touchstone appraisal: QuickGrade Math Pack

**Grade D** · fair value **$0.00 per task** · forecast net gain at 1.7B: not measured (quick mode stopped after screening)

**Flags**

- **gameable_grader** (block): Gameable grader: 'hedge: right then wrong' collects 100% reward without solving the task.
- **screen_only** (info): Quick mode stopped after screening: the problems above already rule out a price, so no model was trained. Run the full mode for training measurements.

## What was appraised

- RL environment: `/Users/nathanhe/Downloads/touchstone/.claude/worktrees/agent-a733cb471ee107784/examples/demo/gameable_env`
- SHA-256: `a884ee9a1da63af5ded3fab514449bb7e470644cb04506faf75233ef0ba9a991`
- Items: 5,000 (3,504 unique)
- Mode: quick · runtime 0 min 28 s
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
| hedge: right then wrong | 100% |
| hedge: wrong or right | 100% |
| answer buried in junk | 100% |
| digit soup | 6% |
| model's own wrong answers | 1% |
| empty answer | 0% |
| echo the prompt | 0% |
| letter soup | 0% |
| copy a prompt span (last-1) | 0% |
| near miss | 0% |
| same shape, wrong content | 0% |

The grader accepts 100% of reference answers. The answer appears verbatim in 0% of prompts.
| Size | Env reward before | after (material) | after (placebo) |
|---|---|---|---|

## Overlap

- With the held-out suite: **0.0%** of suite items appear in the material; **0.0%** of the material matches the suite (exact 0.0%, near-duplicate 0.0%, reworded 0.0%)
- With free public data (Public Addition (free) environment): **3.2%**
- Internal duplicates: 29.9%
  - public match (near): "Calculate 99 + 25. Reply with only the number." ~ "Calculate 25 + 99. Reply with only the number."
  - public match (exact): "Calculate 50 + 86. Reply with only the number." ~ "Calculate 50 + 86. Reply with only the number."

## Forecast at 1.7B

Method: **skipped**. Not forecast: training was skipped because a blocking flag fired during screening.

| | Point | Range |
|---|---|---|

Buyer models larger than 1.7B are not forecast: we have not validated the method beyond the largest size we can train, and RL/SFT gains often shrink as base models get stronger.

## Grade and fair value

- Grade **D** from the screening flags alone (rubric in METHOD.md).
- Not priced: blocked by gameable_grader.
- $ per point is an assumption (set with --dollars-per-point), not a measurement.

## Limits of this appraisal

- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale better than absolute gains do.
- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).
- The held-out suite measures one domain. Skills outside it are not credited.
- See METHOD.md for how each number is computed and validated.
