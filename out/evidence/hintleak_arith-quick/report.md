# Touchstone appraisal: HintLeak Tutor Set

**Grade D** · fair value **$0.00 per task** · forecast net gain at 1.7B: **+4.2 pts** (range -1.2 to +9.5) on the held-out suite

**Flags**

- **gameable_grader** (block): Gameable grader: 'copy a prompt span (last-1)' collects 100% reward without solving the task.
- **transfer_gap** (block): Training reward climbs but the held-out suite does not improve: the model is learning the grader, not the skill.

## What was appraised

- RL environment: `/Users/nathanhe/Downloads/touchstone/.claude/worktrees/agent-a733cb471ee107784/envs/hintleak_arith`
- SHA-256: `9daf62d268f9fd51c214470f5e692e8456fff12c627b26f744278293c6cb983e`
- Items: 5,000 (3,494 unique)
- Mode: quick · runtime 10 min 58 s
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
| 135M | 1 | 32.5% | 36.7% | +4.2 [-0.8, +9.2] | +0.0 [-4.2, +4.2] | +4.2 [-0.8, +9.2] | +4.2 [-0.8, +9.2] | +6.0 [+2.6, +9.5] |

*Prob. gain* is the change in the model's probability on the right answer versus four plausible wrong ones: a smooth score that moves even when small models are rarely fully right.

## Grader audit

Known-wrong and junk answers fed to `verify()` on 200 sampled tasks (reference answers available). Hackability = most reward any probe earns; flagged at 20%.

| Probe | Reward earned |
|---|---|
| copy a prompt span (last-1) | 100% |
| empty answer | 0% |
| echo the prompt | 0% |
| digit soup | 0% |
| letter soup | 0% |
| near miss | 0% |
| same shape, wrong content | 0% |
| hedge: right then wrong | 0% |
| hedge: wrong or right | 0% |
| answer buried in junk | 0% |
| model's own wrong answers | 0% |

The grader accepts 100% of reference answers. The answer appears verbatim in 100% of prompts.

**Training reward vs held-out transfer** at 135M: environment reward +48.4 pts, held-out accuracy +4.2 pts (transfer gap: flagged).

| Size | Env reward before | after (material) | after (placebo) |
|---|---|---|---|
| 135M | 52% | 100% | 66% |

## Overlap

- With the held-out suite: **0.0%** of suite items appear in the material; **0.0%** of the material matches the suite (exact 0.0%, near-duplicate 0.0%, reworded 0.0%)
- With free public data (Public Addition (free) environment): **0.0%**
- Internal duplicates: 30.1%

## Forecast at 1.7B

Method: **rank_largest**. No calibration sweep exists for this suite, so the forecast is the gain measured at 135M (the DataDecide default: rank at the largest affordable size). Treat it as a ranking signal; its scale at 1.7B is not validated.

| | Point | Range |
|---|---|---|
| material | +4.2 pts | -1.2 to +9.5 |
| placebo | +0.0 pts | -3.9 to +3.9 |
| net | +4.2 pts | -1.2 to +9.5 |

Buyer models larger than 1.7B are not forecast: we have not validated the method beyond the largest size we can train, and RL/SFT gains often shrink as base models get stronger.

## Grade and fair value

- Grade **D** from net gain +4.2 pts (A >= 5, B >= 2, C >= 0.5, else D; F if training measurably hurts), capped by the flags above.
- Not priced: blocked by gameable_grader, transfer_gap.
- $ per point is an assumption (set with --dollars-per-point), not a measurement.

## Limits of this appraisal

- Small open models (SmolLM2 135M to 1.7B) stand in for the buyer's model. Rankings transfer across scale better than absolute gains do.
- One fixed, short training recipe per rung; a buyer's longer training could extract more (or less).
- The held-out suite measures one domain. Skills outside it are not credited.
- See METHOD.md for how each number is computed and validated.
