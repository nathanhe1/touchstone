# Touchstone appraisal: Clone Premium Addition

**Grade C** · fair value **$213 per task** · forecast net gain at 1.7B: **+17.5 pts** (range +9.4 to +25.6) on the held-out suite

**Flags**

- **mostly_public** (discount): 90% of items are already in free public data.

## What was appraised

- RL environment: `/Users/nathanhe/Downloads/touchstone/.claude/worktrees/agent-a733cb471ee107784/envs/clone_arith`
- SHA-256: `99480e1dfacdcb18c8d76b9aa481dcb272e3c4ebdcba29c14a23ec501ea79c29`
- Items: 2,500 (2,099 unique)
- Mode: quick · runtime 11 min 19 s
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
| 135M | 1 | 32.5% | 50.8% | +18.3 [+11.7, +25.8] | +0.8 [-3.3, +5.0] | +17.5 [+10.0, +25.0] | +18.3 [+11.7, +25.8] | +18.3 [+13.6, +23.0] |

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

**Training reward vs held-out transfer** at 135M: environment reward +3.1 pts, held-out accuracy +18.3 pts.

| Size | Env reward before | after (material) | after (placebo) |
|---|---|---|---|
| 135M | 69% | 72% | 59% |

## Overlap

- With the held-out suite: **0.0%** of suite items appear in the material; **0.0%** of the material matches the suite (exact 0.0%, near-duplicate 0.0%, reworded 0.0%)
- With free public data (Public Addition (free) environment): **89.8%**
- Internal duplicates: 16.0%
  - public match (exact): "Calculate 65 + 41. Reply with only the number." ~ "Calculate 65 + 41. Reply with only the number."
  - public match (exact): "Calculate 42 + 81. Reply with only the number." ~ "Calculate 42 + 81. Reply with only the number."

## Forecast at 1.7B

Method: **rank_largest**. No calibration sweep exists for this suite, so the forecast is the gain measured at 135M (the DataDecide default: rank at the largest affordable size). Treat it as a ranking signal; its scale at 1.7B is not validated.

| | Point | Range |
|---|---|---|
| material | +18.3 pts | +11.4 to +25.3 |
| placebo | +0.8 pts | -3.3 to +4.9 |
| net | +17.5 pts | +9.4 to +25.6 |

Buyer models larger than 1.7B are not forecast: we have not validated the method beyond the largest size we can train, and RL/SFT gains often shrink as base models get stronger.

## Grade and fair value

- Grade **C** from net gain +17.5 pts (A >= 5, B >= 2, C >= 0.5, else D; F if training measurably hurts), capped by the flags above.
- Value = 17.50 pts x $250,000 per point x 0.10 (share not already free) = $448,000, over 2,099 unique items = **$213 per item**.
- $ per point is an assumption (set with --dollars-per-point), not a measurement.

## Limits of this appraisal

- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale better than absolute gains do.
- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).
- The held-out suite measures one domain. Skills outside it are not credited.
- See METHOD.md for how each number is computed and validated.
