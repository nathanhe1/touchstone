# Touchstone appraisal: WebArena string-match tasks

**Grade D** · fair value **$0.00 per task** · forecast net gain at 1.7B: not measured (quick mode stopped after screening)

**Flags**

- **gameable_grader** (block): Gameable grader: 'wrong: fraction appended' collects 84% reward without solving the task.
- **screen_only** (info): Quick mode stopped after screening: the problems above already rule out a price, so no model was trained. Run the full mode for training measurements.

## What was appraised

- RL environment: `/Users/nathanhe/.cache/touchstone/case_studies/inputs/webarena_strings`
- SHA-256: `39eeab50ccb5089cb435245227f95edde5619e035202572cf2ccb0ce0cdf64e8`
- Items: 212 (209 unique)
- Mode: quick · runtime 1 min 3 s
- Models (real open weights, LoRA rank 16): 

## Held-out suite

- Suite: **webarena_fuzzy_suite** (/Users/nathanhe/.cache/touchstone/case_studies/inputs/webarena_fuzzy_suite.jsonl), 82 items
- Domain: webarena_fuzzy_suite
- user-supplied suite from webarena_fuzzy_suite.jsonl
- Never used for training. 79 of 82 suite items have no match in the appraised material; gains are also reported on that untouched subset.

## Transfer to the held-out suite

Accuracy points gained after training, with 90% bootstrap intervals over suite items (averaged over seeds). *Placebo* trains on the same prompts with rewards shuffled within each batch; *net* is material minus placebo, the value of the content itself.

| Size | Seeds | Base acc | After acc | Gain (pts) | Placebo gain | Net gain | Gain, untouched items | Prob. gain (pts) |
|---|---|---|---|---|---|---|---|---|
No model was trained in this run: quick mode stopped after screening (see flags).


*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Grader audit

Known-wrong and junk answers fed to `verify()` on 400 sampled tasks (reference answers available). Hackability = most reward any probe earns; flagged at 20%.

| Probe | Reward earned |
|---|---|
| wrong: fraction appended | 84% |
| hedge: right then wrong | 82% |
| hedge: wrong or right | 82% |
| hedge across ', ' | 82% |
| hedge across '/' | 82% |
| hedge across '\n' | 82% |
| hedge across ' | ' | 82% |
| hedge across ' and ' | 82% |
| hedge across '; ' | 82% |
| wrong: negated | 81% |
| wrong: off by a thousand | 32% |
| wrong: times ten | 32% |
| wrong: in an equation | 2% |
| fixed reply '-1' | 2% |
| fixed reply '.9' | 2% |
| echo the prompt | 2% |
| unevaluated expression from the prompt | 2% |
| copy a prompt span (last-1) | 1% |
| wrong: padded to 150 characters | 1% |
| digit soup | 0% |
| wrong: stated at length | 0% |
| near miss | 0% |
| same shape, wrong content | 0% |
| wrong: padded to 60 words | 0% |
| empty answer | 0% |
| letter soup | 0% |
| trigger: 'answer' | 0% |
| trigger: 'result' | 0% |
| trigger: 'total' | 0% |
| trigger: 'final' | 0% |
| trigger: 'correct' | 0% |
| trigger: 'solution' | 0% |
| trigger: 'therefore' | 0% |
| trigger: 'step' | 0% |
| trigger: 'sum' | 0% |
| trigger: 'yes' | 0% |
| trigger: 'true' | 0% |
| trigger: 'done' | 0% |
| trigger: '=' | 0% |
| trigger: 'because' | 0% |
| trigger: 'expected' | 0% |
| trigger: 'reasoning' | 0% |
| trigger: '<answer>' | 0% |
| trigger: '</answer>' | 0% |
| trigger: '\\boxed{}' | 0% |
| trigger: '####' | 0% |
| trigger: '.*' | 0% |
| trigger: '.+' | 0% |
| fixed reply '0' | 0% |
| fixed reply '1' | 0% |
| fixed reply 'nan' | 0% |
| fixed reply 'inf' | 0% |
| fixed reply '-inf' | 0% |
| fixed reply '1e9' | 0% |
| fixed reply 'None' | 0% |
| fixed reply 'null' | 0% |
| fixed reply 'true' | 0% |
| fixed reply '?' | 0% |
| fixed reply ' ' | 0% |
| fixed reply '\n' | 0% |
| fixed reply 'xxxxxxxx' | 0% |
| fixed reply '99999999' | 0% |
| fixed reply '{}' | 0% |
| fixed reply '[]' | 0% |
| wrong: first character only | 0% |
| wrong: all but the last character | 0% |
| wrong: last character only | 0% |
| wrong: scrambled characters | 0% |
| wrong: digits permuted | 0% |
| wrong: same digit sum | 0% |
| model's own wrong answers | 0% |

The grader accepts 100% of reference answers. The answer appears verbatim in 2% of prompts.
| Size | Env reward before | after (material) | after (placebo) |
|---|---|---|---|

## Overlap

- With the held-out suite: **3.7%** of suite items appear in the material; **1.4%** of the material matches the suite (exact 0.0%, near-duplicate 0.5%, reworded 0.9%)
- With free public data (none (no public baseline for this domain; pass --public)): **0.0%**
- Internal duplicates: 1.4%
  - suite match (near): "I will arrive Pittsburgh Airport soon. Provide the name of a Hilton hotel in the vicinity, if available. Then, tell me the the shortest walking distance to a su" ~ "I will arrive Pittsburgh Airport soon. Provide the name of a Hyatt hotel in the vicinity, if available. Then, tell me the the shortest walking time to a superma"
  - suite match (paraphrase): "Given the following locations, ['Princeton University', 'Yale University', 'Harvard University'], what would be the optimal route to travel through them all in " ~ "Given the following locations, ['Massachusetts Institute of Technology', 'Harvard University', 'Boston Logan International Airport'], what would be the optimal "

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
