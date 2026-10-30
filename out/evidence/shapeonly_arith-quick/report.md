# Touchstone appraisal: ShapeOnly Numeracy

**Grade D** · fair value **$0.00 per task** · forecast net gain at 1.7B: **-0.8 pts** (range -9.4 to +7.7) on the held-out suite

**Flags**

- **gameable_grader** (block): Gameable grader: 'same shape, wrong content' collects 100% reward without solving the task.
- **no_measurable_gain** (block): No measurable gain above placebo on the held-out suite at the largest trained size.

## What was appraised

- RL environment: `/Users/nathanhe/Downloads/touchstone/.claude/worktrees/agent-a733cb471ee107784/envs/shapeonly_arith`
- SHA-256: `ed31c53ce6af7d5751c3df1959fb99ddb887427933868948dac5ad722c5111a1`
- Items: 5,000 (3,460 unique)
- Mode: quick · runtime 11 min 11 s
- Models (real open weights, LoRA rank 16): 135M = `HuggingFaceTB/SmolLM2-135M-Instruct`

## Held-out suite

- Suite: **arithmetic** (built-in, seed 90210 (subset of 120)), 120 items
- Domain: multi-digit addition stated in words (2-digit and 3-digit operands)
- 100 items each of 2+2, 3+2 and 3+3 digit addition, in four phrasings unused by the sample vendors.
- Never used for training. 120 of 120 suite items have no match in the appraised material; gains are also reported on that untouched subset.

## Transfer to the held-out suite

Accuracy points gained after training, with 90% bootstrap intervals over suite items (averaged over seeds). *Placebo* trains on the same prompts with rewards shuffled within each batch; *net* is material minus placebo, the value of the content itself.

| Size | Seeds | Base acc | After acc | Gain (pts) | Placebo gain | Net gain | Gain, untouched items | Prob. gain (pts) |
|---|---|---|---|---|---|---|---|---|
| 135M | 1 | 32.5% | 40.0% | +7.5 [+0.0, +15.0] | +8.3 [+4.2, +12.5] | -0.8 [-8.3, +6.7] | +7.5 [+0.0, +15.0] | +15.9 [+11.5, +20.6] |

*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Grader audit

Known-wrong and junk answers fed to `verify()` on 200 sampled tasks (reference answers available). Hackability = most reward any probe earns; flagged at 20%.

| Probe | Reward earned |
|---|---|
| same shape, wrong content | 100% |
| near miss | 92% |
| copy a prompt span (first+2) | 37% |
| model's own wrong answers | 25% |
| empty answer | 0% |
| echo the prompt | 0% |
| digit soup | 0% |
| letter soup | 0% |
| hedge: right then wrong | 0% |
| hedge: wrong or right | 0% |
| answer buried in junk | 0% |

The grader accepts 100% of reference answers. The answer appears verbatim in 0% of prompts.

**Training reward vs held-out transfer** at 135M: environment reward +0.0 pts, held-out accuracy +7.5 pts.

| Size | Env reward before | after (material) | after (placebo) |
|---|---|---|---|
| 135M | 92% | 92% | 92% |

## Overlap

- With the held-out suite: **0.0%** of suite items appear in the material; **0.0%** of the material matches the suite (exact 0.0%, near-duplicate 0.0%, reworded 0.0%)
- With free public data (Public Addition (free) environment): **46.8%**
- Internal duplicates: 30.8%
  - public match (exact): "Calculate 47 + 13. Reply with only the number." ~ "Calculate 47 + 13. Reply with only the number."
  - public match (exact): "Calculate 38 + 24. Reply with only the number." ~ "Calculate 38 + 24. Reply with only the number."

## Forecast at 1.7B

Method: **rank_largest**. No calibration sweep exists for this suite, so the forecast is the gain measured at 135M (the DataDecide default: rank at the largest affordable size). Treat it as a ranking signal; its scale at 1.7B is not validated.

| | Point | Range |
|---|---|---|
| material | +7.5 pts | +0.0 to +15.0 |
| placebo | +8.3 pts | +4.2 to +12.5 |
| net | -0.8 pts | -9.4 to +7.7 |

Buyer models larger than 1.7B are not forecast: we have not validated the method beyond the largest size we can train, and RL/SFT gains often shrink as base models get stronger.

## Grade and fair value

- Grade **D** from net gain -0.8 pts (A >= 5, B >= 2, C >= 0.5, else D; F if training measurably hurts), capped by the flags above.
- Not priced: blocked by gameable_grader, no_measurable_gain.
- $ per point is an assumption (set with --dollars-per-point), not a measurement.

## Limits of this appraisal

- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale better than absolute gains do.
- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).
- The held-out suite measures one domain. Skills outside it are not credited.
- See METHOD.md for how each number is computed and validated.
