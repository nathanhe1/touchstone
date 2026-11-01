# How Touchstone measures

This explains each number in a Touchstone report, the evidence that it works on this hardware, and where it stops working. Results quoted here come from `out/` and were produced by the scripts named next to them.

## 1. The model ladder

Three sizes of one open family, so that size is the only thing that changes: SmolLM2-135M, 360M and 1.7B-Instruct (Allal et al. 2025). Every size gets the same LoRA recipe (Hu et al. 2021), rank 16 on all linear layers:

- SFT: 60 steps x 16 examples, learning rate 2e-4, warm-up then linear decay, loss on completion tokens only.
- GRPO: 40 steps x 8 prompts x 8 samples at temperature 1, learning rate 5e-5, KL penalty 0.04 to the base model.

Budgets are fixed per appraisal rather than per dataset, so every dataset gets the same compute: small datasets repeat, large ones are subsampled. The value measured is "what this material teaches in a fixed small budget". A buyer training for longer could get more.

1.7B is the largest model that trains in 16 GB of unified memory (fp16 base weights, fp32 adapters). It is the forecast target, and the only target that was checked against real measurements.

## 2. Held-out transfer

The headline number is **accuracy gain on a held-out suite**: score each suite item before and after training, greedy decoding, final answer extracted (the last number for numeric items; exact match otherwise). Gains are paired per item, so item difficulty cancels, and the 90% intervals are a bootstrap over items. Training noise is handled with seeds: two at 135M and 360M in a full run.

**What "held out" means.** Built-in suites are generated from templates and seeds that no vendor sees: `word_math` uses 10 templates (purchases, rates, groups, change, multi-step) whose wording and contexts differ from every example dataset and environment in this repo. A gain therefore requires the skill to carry over to new phrasings; memorizing items cannot produce it. Every appraised item is also checked against the suite (section 5). Leaked items are flagged and the price is set to zero, and the gain is reported again on the untouched remainder of the suite.

**Your own domain.** Supply a JSONL suite (`--suite my_suite.jsonl`; format in the README). It must be written by you, never shared with the vendor, and ideally 200+ items. Following GSM1k (Zhang et al. 2024), fresh items in the style of the target domain are the most reliable way to keep a suite clean.

**A smooth score next to accuracy.** Small models are rarely fully right, and exact-match metrics make small-model progress look like noise (Schaeffer et al. 2023). DataDecide (Magnusson et al. 2025) found continuous likelihood metrics far more predictive across scale. Touchstone therefore also reports the model's probability on the correct answer against four plausible wrong ones (near misses, digit swaps). Chance is 20%. The score is taken in the answer slot of the model's own reply ("... 73 + 6 = [79]."), so it doesn't depend on whether training taught the model to reason first or answer directly.

## 3. The placebo

Raw gains mostly measure format, not content. On `word_math` at 135M, fine-tuning on **all-wrong** answers raised held-out accuracy by about as much as correct ones did when replies were truncated, because it taught a short "steps, then the answer" format. Spurious Rewards (Shao et al. 2025) found the same effect in RL: random rewards alone raised Qwen2.5-Math scores by 21 points.

So every appraisal trains a placebo with the same compute at every rung:

- dataset: the same prompts with completions **shuffled across examples** (format, length and answer distribution kept, prompt-answer link destroyed);
- environment: the same tasks with **rewards shuffled within each batch** (reward rate kept, which reply was rewarded randomized).

**Net gain = material gain - max(0, placebo gain).** Only the free format benefit is subtracted. A placebo that hurts (shuffled answers often teach wrong arithmetic) is not used to credit the material for merely being correct.

## 4. Grader audit (environments)

Following Rajan (2026), Touchstone mechanically checks whether `verify()` pays for answers known to be wrong. It does not ask a model whether the grader looks right.

- With a reference answer per task: near misses (+-1, +-10), same-shape wrong answers (one character changed), hedges ("85 86", "86 or 85"), the answer buried in junk, and the base model's own wrong samples.
- Reference-free: empty reply, echoing the prompt, digit soup, letter soup, and copying a span of the prompt. The best of 12 fixed positions is kept, which is what an RL policy would converge to.

Hackability is the most reward any probe earns. At 20% or more the grader is flagged, the grade is capped at D, and nothing is priced. The audit also checks that the grader accepts reference answers and stays in [0, 1]. A stochastic grader that flips rewards at random pays every wrong probe about the same, which no policy can exploit, so its flip rate (the median probe) is measured and removed before the 20% test; the rate is reported as `reward_noise`.

A second, training-based signal follows Gao et al. (2022): if training reward rises by 15 points or more while held-out accuracy does not (transfer gap), the policy is learning the grader rather than the skill.

## 5. Overlap and contamination

Three tiers (`touchstone/overlap.py`):

1. exact match after normalization;
2. near-duplicate: character 5-gram Jaccard of at least 0.6 (Broder 1997; Lee et al. 2022);
3. reworded: all-MiniLM-L6-v2 sentence-embedding cosine of at least 0.85, which catches paraphrases that string checks miss (Yang et al. 2023).

For text with numbers, tiers 2 and 3 also require the same multiset of numbers. Without that guard, every "Sam has 12 apples" would match every "Sam has 15 apples": the same template, not the same item.

Overlap is checked against the held-out suite (contamination: more than 5% blocks the price and caps the grade at D) and against a free public baseline (GSM8K train for `word_math`; your `--public` file otherwise). The share already free discounts the price, and more than half free caps the grade at C.

### Other static screens

- **Label noise.** Worked solutions (`screen.py`): every `expression = number` is recomputed and the stated final answer must appear in the working. The flag fires when 10% or more are inconsistent, given at least 20 checked solutions and a fifth of the set. Answer-only data goes to a reference judge, Qwen2.5-1.5B, which answers each sampled item by reasoning and by a program in a restricted evaluator (`judge.py`). Where both routes agree, disagreement with the label estimates noise; the flag fires at 15%, or 20% for text labels using the program route. Other data types: see RESEARCH.md, section 4, and `docs/AUDIT.md`. Multiple-choice, free-text, chat and non-English signals are advisory, because they false-flagged real clean data.
- **Off-topic**: share of material prompts whose nearest held-out item has a MiniLM cosine below 0.35; flagged at half or more.
- **Answer leakage** (environments): the reference answer appears verbatim in the prompt for 20% or more of tasks.

### How accurate are the red flags?

`scripts/eval_flags.py`, `out/flag_eval.md`. Thresholds were set on the development set (the sample environments and example datasets) and frozen. A **held-out test set** was then written with new generators: different templates and wording, label noise by shuffling and by uniform random answers, contamination by verbatim copies and by question-first rewording, a reworded GSM8K slice, trivia and code as off-topic data, and five new grader bugs (prefix match, ±10 tolerance, always-1, case-insensitive substring, a bonus for long replies). It was evaluated once. "Before" is the original prototype's detectors.

| Flag (test set, 23 items) | Positives | Before: precision / recall | After: precision / recall |
|---|---|---|---|
| gameable_grader | 6 | 1.00 / 0.33 | 1.00 / 1.00 |
| answer_leakage | 1 | - / 0.00 | 1.00 / 1.00 |
| contaminated | 3 | - / 0.00 | 1.00 / 1.00 |
| copied_from_public | 2 | - / 0.00 | 1.00 / 0.50 |
| duplicated | 2 | - / 0.00 | 1.00 / 1.00 |
| noisy_labels | 3 | - / 0.00 | 1.00 / 0.33 |
| off_topic | 2 | - / 0.00 | 1.00 / 1.00 |
| **all** | 19 | 1.00 / 0.11 | **1.00 / 0.84** |

Items with exactly the right set of flags: 26% before, 87% after. On the development set: 1.00 / 0.94 overall. No false flag was raised on any clean item in either set. The misses: two answer-only noisy datasets (no static detector, see above; training then shows no measurable gain, so they are still not priced), and one environment whose tasks are the free addition set reworded ("What's 65 plus 41? Just the number."): MiniLM puts very short arithmetic prompts below the paraphrase threshold. A same-numbers-only rule for short prompts would catch it, but adding it now would be tuning on the test set, so it waits for a fresh test set.

**A correct dataset that tests as harmful.** `good_short` (correct answers, no working shown) lowers 135M held-out accuracy by about 9 points. This is not a formatting bug: the chat and prompt/completion paths produce identical training text (regression test `test_messages_and_prompt_completion_train_identically`), and the scorer reads "The answer is 15." correctly. The model learns to answer without working the problem out and gets multi-step problems wrong (79 becomes 15). The report now names this (`suppresses_reasoning`, from reply length collapsing by more than 60% while accuracy falls) so a buyer sees why.

## 6. Forecast: small to large

### Methods compared

1. **extrapolate**: the original prototype. Fit gain against log(parameters) through the small rungs and extend the line to the target.
2. **rank_largest**: DataDecide's finding (Magnusson et al. 2025) was that none of eight scaling-law fits beat ranking at the largest affordable size. The prediction is the gain at the largest small rung.
3. **calibrated**: learn the small-to-large map from a sweep of materials run at every size, target gain ~ a + b x accuracy gain + c x probability gain at the largest small rung. This is observational calibration in the spirit of Ruan et al. (2024), and it is consistent with Khaddaj et al. (2025), who find data effects are strongly correlated across scale. The **range** in a report is the 80% quantile of absolute leave-one-out error on that sweep, the error actually observed on datasets the fit never saw.

Every method is scored by **leave-one-out** on the sweep, with Spearman rank correlation, pairwise **decision accuracy** (did it pick the same winner of each pair as the 1.7B truth? chance is 0.5), and mean absolute error.

### Results

**RL environments, tiny GPTs** (`scripts/validate_rl_tiny.py`, `out/validation_rl_tiny_summary.json`). This reruns the experiment that gave the original prototype its Spearman of −0.03, with 16 environments (skill mix, pool size, grader noise, broken graders), 4 sizes (29K to 1.3M parameters), 3 seeds each (192 GRPO runs), predicting the largest size (XL) from S, M and L:

| Target at XL | Method | Spearman | Decision accuracy | MAE (pts) |
|---|---|---|---|---|
| accuracy gain | extrapolate (the prototype's method) | 0.12 | 0.56 | 11.3 |
| accuracy gain | rank_largest | 0.17 | 0.56 | 9.9 |
| accuracy gain | calibrated (LOO) | −0.24 | 0.40 | 3.8 |
| **smooth-score gain** | extrapolate | 0.92 | 0.90 | 3.0 |
| **smooth-score gain** | **rank_largest** | **0.93** | **0.91** | 1.8 |
| **smooth-score gain** | calibrated (LOO) | 0.93 | 0.91 | 1.1 |

The XL accuracy gains are themselves reproducible (seed 0 vs the mean of seeds 1-2: Spearman 0.78), so the failure is not noise: exact-match accuracy changes non-monotonically with scale, while the probability placed on the correct answer moves smoothly and its ranking carries across a 43x size gap. This is the "mirage" effect (Schaeffer et al. 2023) and DataDecide's continuous-metric result, reproduced on RL. With the old protocol (one seed) the accuracy numbers bounce between 0.19 and 0.42, which is why one-seed results such as the prototype's −0.03 and 0.18 should not be read either way. **Consequence for the product:** every report now carries the smooth-score gain at the largest trained size as the ranking signal (`forecast.smooth_value`), next to the accuracy forecast.

**Datasets, real models** (`scripts/validate_sft.py`, `out/validation_sft_summary*.json`). Thirteen example datasets (good, noisy at 20-100%, answer-only, harder, tiny, duplicated, partly or mostly off-topic) were fine-tuned at 135M and at 360M (2.7x larger) with the same recipe, scored on 200 held-out word problems, and the proxy's ranking of the datasets was compared with the 360M ranking. The 1.7B target could not be completed on this laptop (section "What the product reports").

| Proxy at 135M (datasets) | Rank by accuracy: Spearman / decision acc. | Rank by smooth score | Calibrated map (LOO) |
|---|---|---|---|
| standard recipe, 2 seeds (8) | 0.48 / 0.75 | 0.31 / 0.71 | −0.17 / 0.46 |
| quick recipe, 30 steps, 1 seed (13) | 0.58 / 0.72 | 0.52 / 0.68 | 0.35 / 0.65 |
| **learning rate / 10**, 1 seed (13) | **0.68 / 0.72** | **0.67 / 0.74** | |
| same 8 datasets: lr / 10 vs standard | **0.89 / 0.82** vs 0.43 / 0.71 | 0.69 / 0.79 vs 0.31 / 0.71 | |

What this says, honestly:

- The proxy is not noisy: two seeds of the 135M proxy rank the datasets almost identically (Spearman 0.98). The disagreement with 360M is real scale dependence. At 360M (base accuracy 49%), most of these short worked-solution datasets *lower* accuracy (good_cot −3, noisy_80 −18.5, good_short −35.5), while at 135M (base 15%) the same data helps. A small model that is still learning the format rewards different data than a larger model that already reasons.
- Ranking at the proxy gives about 3 correct pairwise calls in 4 (chance is 1 in 2). That is better than chance and well short of DataDecide's ~80% on pretraining.
- A learned calibration map does worse than simple ranking, which is also DataDecide's finding. That is one more reason no calibrated map ships.
- **A 10x smaller learning rate for the proxy helps**, as Wang et al. (ICLR 2026) found for pretraining proxies: Spearman 0.43 → 0.89 on the 8 datasets measured both ways, 0.58 → 0.68 on all 13 against the quick recipe. Adopting it changes the measured gains (they shrink), so the quick-mode grade thresholds would need re-checking. It is the first change to make next, not yet the default.
- Small-to-large on RL (tiny GPTs, above) favors the smooth score. On datasets with real models the two signals are close. Both are reported.

### Round 3 pre-registration (written and committed before any round-3 forecast run)

Round 2 was noise-limited: two seeds of the 135M proxy agreed on only 0.87 of pairwise decisions, and the target was one seed on 150 items. Round 3 cuts the noise and fixes the scoring rules in advance.

**Sweep.** `scripts/validate_rl_real2.py`: 26 new arithmetic-domain environments (difficulty, related and unrelated skills, off-topic share, reward noise, pool size, leaky prompts, lax graders, a prompt/grader format mismatch). GRPO with the quick recipe at 135M (proxy) and 360M (target), **3 seeds at each size**, scored on a **600-item** held-out arithmetic suite with per-item results stored. The proxy is also evaluated at steps 10 and 20.

**Split.** Fixed before any run by a seeded shuffle (`split()` in the script, seed 20261030): 13 development environments (`add3ops_honest, add_sub_mix, grader_lastdigit, leak100, mix_honest, mul_honest, noise10, noise20, offtopic75, pool10, pool100, spaced_honest, sub_honest`) and 13 held-out environments (`add4_honest, answer_tag_mismatch, carry_honest, grader_format_bonus, grader_number, grader_tol2, leak30, nocarry_honest, noise45, offtopic25, offtopic50, strings_only, word_honest`). The 12 round-2 environments count as development data too. Any choice of forecasting signal (accuracy, smooth score, checkpoint averaging, combinations) is made on development environments only; the held-out numbers are reported for that choice, with every other candidate shown next to it.

**Primary metrics** (unchanged): Spearman and pairwise decision accuracy between the proxy signal (mean over proxy seeds) and the target's accuracy gain (mean over target seeds), over **all pairs** of held-out environments.

**Resolvable-pairs decision accuracy** (secondary, always reported next to all-pairs). A pair (i, j) is resolvable when the target gap exceeds two standard errors of that gap: |T_i - T_j| > 2 SE_ij, with SE_ij^2 = Var_boot + s_i^2/n_i + s_j^2/n_j. T is the target accuracy gain averaged over seeds; Var_boot is the variance of the gap over 1,000 bootstrap resamples of suite items (seed-averaged per-item correctness, paired, item indices shared by both environments, bootstrap seed 0); s_k^2 is the sample variance of environment k's per-seed target gains and n_k its number of target seeds. Decision accuracy is then computed over resolvable pairs only, and the number of resolvable pairs is reported. Pairs the target itself cannot order are not counted as forecast errors or successes.

**Noise ceiling** (reported, not a target): decision accuracy of one target seed against the mean of the other target seeds, all pairs.

The same definitions apply to any round-3 dataset sweep, whose split will be committed before it runs.

**Round 3 interim and scale decisions** (added during the sweep; the pre-registered definitions above are unchanged). Development environments now run first within each seed, which changes when results arrive, not what is measured. At seed 0 on the 13 development environments: Spearman 0.54, decision accuracy 0.71 on all 78 pairs and 0.71 on the 38 resolvable pairs for final-checkpoint accuracy; every other signal lands at 0.59-0.72, and gradient similarity is the weakest (0.59). The first 8 environments alone had shown 0.93, which did not survive the other 5. Laptop cost: about 10 minutes a run at 135M and 5 at 360M. About 1 run in 20 hit a kernel-level MPS hang that ignores SIGKILL; the job guard restarts the sweep and finished runs are kept.

**Round 3 forecast addendum** (written and committed before any held-out result was seen; the rules above are unchanged).

*Final candidates, each scored once on held-out, all reported:*

1. `acc_final`: mean proxy accuracy gain at the last checkpoint. Chosen on development (0.71, tied with every simple signal), and the simplest.
2. `hand_pool`: `acc_final` x min(1, log10(unique tasks) / 3), so a task pool under 1,000 scales the signal down. Development: 0.77 on all pairs, 0.89 on resolvable pairs. Its form was chosen after seeing `pool10` on development, with no fitted weights.

Five other screen-aware candidates were tried on development and are not going to held-out (`scripts/dev_forecast_features.py`, `out/forecast_features.json`): `hand_pool_clean` 0.74, `smooth_hand_pool` 0.74, and three leave-one-environment-out ridge fits at 0.59-0.63; `proxy_only` is `acc_final`.

*Held-out extension.* The original split happened to put all small-pool environments in development, so held-out could not test `hand_pool`. Four new environments join held-out, chosen by pool size alone and never run before this was committed: `pool20`, `pool50`, `pool300`, `pool30_mix`. Held-out is reported both ways: the original 13, and the 13 plus these 4.

*Seeds.* After seeds 1 and 2: decision accuracy at 1, 2 and 3 seeds for both candidates, and the noise ceiling.

*Harder suite pilot.* 360M starts at about 77% on the arithmetic suite and target gains cluster at 8-10 points. `scripts/dev_headroom.py` tests whether a harder suite spreads them. Candidates in this order, 300 items each, same hash bucket as the held-out suite: `hard_a` 4-digit + 3-digit, `hard_b` 4-digit + 4-digit, `hard_c` three 3-digit numbers. The first whose 360M base accuracy is 40-60% is used, decided from base accuracy alone. The pilot runs the first 4 development environments in alphabetical order (`add3ops_honest, add_sub_mix, grader_lastdigit, leak100`) at both sizes, seed 0, and is not selected for spread. It reports the standard deviation of target gains on both suites. If it helps, a full run applies the suite to every environment.

*Platforms.* Every sweep run records its device and torch version. Mac runs (MPS, torch 2.8.0) and any runs on a rented GPU (CUDA, a newer torch) are not pooled into one signal or one target unless they are first shown to agree on shared environments and seeds. `--merge` refuses a mixed set by default.

**Round 3 final candidates** (supersedes the two-candidate list above; committed before any held-out score). Scored once on held-out from the GPU sweep (`cuda`, torch 2.14.1, 180 runs, 30 environments, 3 seeds at each size) by `scripts/final_forecast.py`; Mac runs are not pooled. All five are reported, on the original 13 held-out environments and on all 17.

| Candidate | Definition | Uses the larger model? | Development, 3 seeds: all pairs / resolvable |
|---|---|---|---|
| `acc_final` | Proxy accuracy gain, last checkpoint | No | 0.61 / 0.73 |
| `hand_pool` | `acc_final` x pool term | No | 0.66 / 0.87 |
| **`hand_pool_clean`** (primary) | `hand_pool` x (1 - off-topic) x (1 - leakage) x (1 - grader exploit) | No | 0.79 / 0.89 |
| `reach_clean` | Larger model's mean reward over its first GRPO steps x pool x clean | Yes | 0.83 / 0.91 |
| `probe_rank` | Sum of the ranks of `hand_pool_clean` and `reach_clean` | Yes | 0.90 / 0.93 |

`hand_pool_clean` is primary because it is a true small-model forecast. `reach_clean` and `probe_rank` need a short probe at the larger size, so they answer a different question: what a buyer learns by also touching the larger model briefly. All five forms were chosen after seeing development results, with no fitted weights, so development scores are optimistic. Development noise ceiling with 3 seeds: 0.84, one target seed against the mean of the others.

**Round 3 forecast results** (`out/forecast_final.json`, `scripts/final_forecast.py`; 3 seeds at each size, 600 items, 135M to 360M, GPU sweep). Decision accuracy over all pairs / resolvable pairs, with a 90% interval from resampling environments:

| Candidate | Development (13 envs) | Held-out, original (13) | Held-out, all (17) |
|---|---|---|---|
| `acc_final` | 0.61 / 0.73 | 0.68 / 0.72 [0.52, 0.83] | **0.70 / 0.79** [0.57, 0.81] |
| `hand_pool` | 0.66 / 0.87 | 0.68 / 0.72 [0.53, 0.83] | 0.61 / 0.71 [0.46, 0.74] |
| `hand_pool_clean` (pre-registered primary) | 0.79 / 0.89 | 0.65 / 0.62 [0.46, 0.84] | 0.65 / 0.68 [0.48, 0.81] |
| `reach_clean` | 0.83 / 0.91 | 0.56 / 0.62 [0.36, 0.72] | 0.57 / 0.62 [0.37, 0.73] |
| `probe_rank` | 0.90 / 0.93 | 0.65 / 0.66 [0.42, 0.85] | 0.62 / 0.68 [0.42, 0.79] |
| Noise ceiling, all pairs | 0.84 | 0.83 | 0.81 |
| Resolvable pairs | 45 of 78 | 47 of 78 | 77 of 136 |

Spearman on held-out (13 / 17): `acc_final` 0.54 / 0.60, `hand_pool_clean` 0.44 / 0.44, `probe_rank` 0.44 / 0.38.

**The screen-aware candidates did not generalise.** All were built from development patterns, and development scores of 0.79-0.90 fell to 0.56-0.68. The pre-registered primary lost to the plain proxy. The pool term was wrong: development's `pool10` gained +3.3 at the target, but held-out's `pool20`, `pool30_mix` and `pool50` gained +9.0 to +9.7. No candidate reaches 0.90 or Spearman 0.85, and with a noise ceiling of 0.81-0.84, 0.90 on all pairs cannot be reached at this size pair and suite. The plain proxy's held-out 0.70 / 0.79 is the honest number. It is close to round 2's 0.74, so cutting noise made the measurement trustworthy without improving the forecast itself. More seeds do not lift the plain proxy on development: 0.74, 0.68, 0.61 at 1, 2 and 3 seeds. Its failures are structural: a task 135M cannot solve gives it no reward to learn from, while 360M can (`sub_honest`, +2 and +9).

**Harder suite pilot** (`out/dev_headroom.json`, Mac, seed 0, 4 environments). `hard_a` was picked by base accuracy (60% at 360M). Target gains are 0.0, 5.7, 1.0, 2.0 against -0.5, 9.8, 9.3, 7.3 on the standard suite: the 8-10 cluster breaks apart, but the spread in points narrows. Inconclusive at this size.

**Larger targets, pre-registered before any run** (GPU, `cuda`, torch 2.14.1, same 30 environments, split and quick GRPO recipe, 3 seeds, `scripts/validate_rl_real2.py --sizes ...`). Only one signal goes to held-out: `acc_final`, 135M and separately 360M as proxy. No new candidate is built from these runs and scored on the same held-out environments. Reported: Spearman, decision accuracy on all and resolvable pairs, and the noise ceiling.

1. **1.7B on the standard suite.** Same family, 12.7x the proxy.
2. **Harder suite `hard_a`, all environments, at 135M, 360M and 1.7B.** The pilot was inconclusive, so this measures it properly. It adopts the suite only if the target's noise ceiling rises on development.
3. **7B (Qwen2.5-7B-Instruct).** A different family, so size is not the only change, and a result here is reported as cross-family. If its base accuracy on the suite exceeds 90% it is scored on `hard_a` only.

**Round 3 selection rules, retirements and fresh held-out set** (committed before any fresh held-out run).

*The 17 held-out environments are spent.* They are kept as a reported result and are not used to choose anything again.

*Selection.* At most 3 candidates, fixed rules with no fitted parameters, chosen on development environments. Each is reported with leave-one-family-out scores (siblings like `noise10` and `noise20` cannot vouch for each other), a 90% bootstrap interval, and a permutation p-value against shuffled targets (`scripts/tune_forecast.py`, `out/forecast_selection.json`).

*A low development p-value is not evidence on its own.* `probe_rank` scored p < 0.001 on development, then 0.61-0.65 on held-out with p = 0.09. A permutation test cannot correct for a method designed after seeing the same data.

*Retired, not to be retuned:* `hand_pool`, `hand_pool_clean`, `reach_clean`, `probe_rank`, `reward_gain`. Gradient similarity did not reach the final list.

*Frozen candidates for the fresh set* (`scripts/score_h3.py`): `acc_final` (primary), `smooth_final`, and `rank_mean` (sum of within-family ranks of the two). On the spent held-out set they scored 0.70, 0.68 and 0.68 (p = 0.01, 0.02, 0.01). On development alone none clears p < 0.05 (0.13-0.15). They are chosen because they are simple and have no parameters, not because development favoured them.

*Fresh held-out set.* `scripts/validate_rl_h3.py`: 32 unseen environments, 4 families that are not arithmetic (strings, word problems, unit conversion, reading code) crossed with 8 conditions fixed in advance (`honest, hard, off50, noise20, noise45, pool20, leak30, lax_grader`), with no selection for spread. 135M to 360M, 3 seeds each, the same quick GRPO recipe, 300-item suites, one per family; no suite prompt appears in any environment (`--check`). Graders compare strings, so no vendor code runs. Each family has its own suite, so pairs are compared **within a family** only: 112 pairs. Reported: decision accuracy within family (all pairs and resolvable pairs, as defined above), mean within-family Spearman, per-family results, the noise ceiling, 90% bootstrap intervals, and permutation p-values shuffling targets within families. Each candidate is scored once. A candidate that fails here is retired, not retuned.

**1.7B check, rules set before any result** (`scripts/debug_17_placebo.py`). The 1.7B scores are withheld from claims because 1.7B's base accuracy (about 60%) is below 360M's (about 80%). Truncation and precision are ruled out (`out/debug_17_base.log`): 1.7B replies with a bare number, while 360M writes the equation. Three development environments, 3 seeds, three arms: own rewards, shuffled rewards, random rewards.

- If the mean placebo gain is at least half the material gain, the 1.7B target is measuring a format shift. It is reported as such and is not used as a forecast target.
- If the placebo gain is under a quarter of the material gain, the target stands, and held-out scores are reported net of that placebo.
- In between, it is reported as mixed and not used for claims.

A forced-format target (the prompt asks for the working) is adopted only if base accuracy at 1.7B then exceeds 360M's under the same prompt. It would be a new target, pre-registered and run on the fresh held-out set, never rescored on spent environments.

**1.7B check, result** (`out/gpu3/placebo/`, 27 runs, 3 development environments, 3 seeds each).

| Environment | Own rewards | Shuffled | Random | Mean placebo / own |
|---|---|---|---|---|
| `mix_honest` | +26.5 | +1.7 | +12.2 | 26% |
| `spaced_honest` | +31.6 | +6.2 | -2.9 | 5% |
| `sub_honest` | +27.6 | +0.8 | +2.6 | 6% |
| All | **+28.6** | +2.9 | +4.0 | **12%** |

By the pre-registered rule the target stands: mean placebo gain is 12% of the material gain, under a quarter. Per environment, `mix_honest` sits at 26%, and its random arm alone at 46%, driven by two seeds where random rewards flipped the reply into equation form (+13.8, +18.2).

**How much is format?** Across all 27 runs, gain = 2.0 + 0.14 x (change in share of replies with an equals sign) + 19.3 if the rewards are real (R² 0.88). So about +19 of the +28.6 comes from real rewards at constant format, and about +7 from the change in format. A separate measurement agrees: asking for the working, with no training, lifts 1.7B from 62.8% to 70.0%. Two material runs barely changed format and still reached 85-88% (+22 and +25), against 64% for placebo runs at that format.

**What this does not show.** Three honest arithmetic environments, all development: the placebo says nothing about noisy, gameable, small-pool or off-topic environments. The check rules out "any reinforcement gives +28" on those three only. A placebo measured per environment is needed before net gains can be quoted per environment. A constant subtraction leaves rankings unchanged.

**Forced-format comparison: invalid so far.** Under the working prompt 360M scored 2.17%, because its replies overrun the sweep's 48-token limit and the last number parsed is not the answer. That number must not be used. The rerun uses a 200-token limit (`debug_17_format_200.json`).

**Forced-format rule applied.** At a 200-token limit, 1.7B scores 85.5% and 360M 42.2% under the working prompt (`out/gpu3/placebo/debug_17_format_200.json`), so 1.7B beats 360M under the same prompt, and also beats 360M's best prompt (77.5%). The earlier sanity failure is explained: 1.7B is the stronger model when it shows its work. Spent environments are not rescored.

**Fresh 1.7B target, pre-registered before any run** (`scripts/validate_rl_h3_17.py`, a separate job; the frozen h3 job is unchanged). The same 32 fresh environments, GRPO at 1.7B, the same quick recipe, 3 seeds, 96 runs. Each run is evaluated before and after training under both definitions, so the second is an extra evaluation and not extra training.

- **Primary target: working prompt.** The prompt asks for the working, 200-token limit, same prompt before and after training. Format is fixed on both sides, so a format shift cannot produce a gain, which was the flaw in the plain target.
- **Secondary target: plain prompt**, as in the sweeps, 48-token limit, kept for comparability.
- **Primary forecast: `acc_final` at 360M to the 1.7B primary target. Secondary: `acc_final` at 135M.** Proxy values come from the frozen h3 runs. No other signal is scored, and no method is built from these runs.
- **Metrics:** decision accuracy within family, mean within-family Spearman, per-family results, noise ceiling, 90% bootstrap interval, within-family permutation p-value. Each is scored once.
- **Headroom risk, stated in advance.** At 85.5% on arithmetic the primary target may saturate: gains would shrink and the ranking would become noisier, possibly with a low noise ceiling. The base accuracy for each family is reported. A family with a base of 90% or more is flagged as saturated and stays in the primary result, so the result cannot be improved by dropping it. If the primary noise ceiling is below 0.70, the result is reported as inconclusive, not as a forecast failure or success.
- **Limits, stated in advance.** Reply format is only held fixed by the prompt, and training may still change it. Strings are scored by the existing matcher, which is stricter on long replies, so that family's working-prompt accuracy may be understated.

**Harder suite: not adopted** (`out/forecast_hard.json`, 135M and 360M, 178 of 180 runs at scoring; every development run present). The pre-registered test was whether the target's noise ceiling rises on development. It did not: 0.82 against 0.84. Harder items also narrowed the spread of target gains (SD 2.3 against 2.8) and reduced resolvable pairs from 45 to 30 of 78, so they added difficulty without adding signal at 360M. For the record, on spent held-out with two environments short one seed: all pairs 0.60 with the same-suite proxy, 0.67 with the standard proxy, against 0.70 on the standard suite.

**Fresh held-out result** (`out/forecast_h3.json`, 192 runs, scored once). All three frozen candidates failed.

| Candidate | Decision within family (112 pairs) | Resolvable (24 pairs) | Spearman | p | strings / word / units / code |
|---|---|---|---|---|---|
| `acc_final` | 0.45 [0.32, 0.59] | 0.63 | -0.04 | 0.47 | 0.20 / 0.32 / 0.50 / 0.71 |
| `smooth_final` | 0.40 [0.25, 0.56] | 0.46 | -0.23 | 0.89 | 0.35 / 0.29 / 0.46 / 0.50 |
| `rank_mean` | 0.42 [0.29, 0.56] | 0.50 | -0.20 | 0.82 | 0.30 / 0.25 / 0.46 / 0.64 |

Noise ceiling 0.69. **By the stop rule, none of the three stands as a general forecast.** The 0.70 on arithmetic does not carry over to these families, and no claim should imply that it does.

**Why, as far as can be seen. This explains the result and does not change it.** The set partly failed to measure anything:

- Strings: base accuracy 0-0.7% at both sizes, reward stuck at 0. Neither model can do the task, so nearly every target is 0.
- Code: base 7-8%, gains mostly within noise.
- Word: base 1-2%, against 49% at 360M in earlier runs. **This is a flaw in the design:** the sweep's 48-token limit was reused on a suite with no "number only" instruction, so worked replies are cut off before the answer. Gains there largely reflect shorter replies.
- Units: the one healthy family (base 25% and 71%), still 0.50.

So the result says little about forecast skill on three families, and these runs are not rescored or rerun under the same name. What it does show: **below a floor of competence at the proxy, a forecast has nothing to work with**, and on these tasks 135M's rewards never move while 360M's sometimes do (`word_leak30`, 0.03 to 0.29, target +22, proxy 0).

**What a next test needs, written before it runs:** a gate on base accuracy at both sizes (say 10-90%) checked before any training, an evaluation token limit checked against reply length for each suite, and environments in families that pass both.

**Fresh 1.7B result** (`out/forecast_h3_17.json`, 96 runs, scored once).

| Target | Noise ceiling | 360M proxy: decision, p | 135M proxy: decision, p | Base accuracy: strings / word / units / code |
|---|---|---|---|---|
| Working prompt (primary) | **0.68** | 0.45 [0.33, 0.57], 0.63 | 0.38 [0.27, 0.51], 0.74 | 11 / 83 / 32 / 87 |
| Plain prompt (secondary) | 0.66 | 0.53 [0.39, 0.66], 0.21 | 0.34 [0.20, 0.48], 0.90 | 11 / 20 / 51 / 8 |

The primary noise ceiling is below the pre-registered 0.70, so **the result is inconclusive by the rule, neither a pass nor a fail.** It also gives the earlier result no support: 360M to 1.7B scored 0.86 on spent environments and 0.45 here, so that 0.86 **is not confirmed and must not be claimed.** No family reached the 90% saturation line. The 360M proxy came from the same flawed h3 runs, where three families were at a floor or truncated, so this is a weak test of 360M to 1.7B. Per family at 360M: strings 0.29, word 0.71, units 0.21, code 0.57; each is 28 pairs, and none is a finding on its own.

### What the forecast is not

**What the product reports.** No calibrated map ships yet: fitting one needs measured gains at the target size for a dozen or more datasets, and the 1.7B rung could not be completed for the sweep on this 16 GB laptop (training fits in 4.7 GB with gradient checkpointing, but 1.7B evaluation drove the machine into swap). So `forecast.value` is the rank-at-largest number (the net accuracy gain at the largest trained size, labelled as a ranking signal whose scale at 1.7B is not validated), and `forecast.smooth_value` carries the smooth-score ranking, which is the better-validated signal. The calibrated method stays in the code and is used automatically once `touchstone/calibration/dataset_<suite>.json` exists (`scripts/validate_sft.py --target 1.7B` on a bigger machine writes the data for it).

- Validated scale: 43x on the tiny GPTs (RL) and 2.7x on real models (135M to 360M, datasets). Buyers train 7B to 400B+ models. Touchstone reports no number beyond the largest trained size, and RL gains tend to shrink as base models get stronger (Tan et al. 2025; ScaleRL, Khatri et al. 2025).
- A calibration holds for one suite, one recipe and one model family. A custom suite would need its own sweep (`scripts/validate_sft.py` is the template).
- RL environments on real models have no ladder sweep yet: GRPO at three sizes x 15+ environments x seeds does not fit on a laptop. The RL forecasting methods were validated on the tiny GPTs instead.

### Round 4 (in progress)

**Test v4 frozen** (`examples/test4/`, hash in `out/test_v4.sha256`, committed before any detector ran on it). 71 cases from real public data and sources the flag checks never used: 32 clean real draws, 4 known-bad sets (TruthfulQA's human-written false answers; GSM-Plus perturbed questions paired with the original answer), 3 public-copy cases from GSM-Plus's real rewordings, 9 planted on real rows, 2 contaminated datasets, and 21 environment cases (12 new grader bugs, 5 honest idioms, 3 reworded suite contaminations, 1 control). False flags are reported per source. Test v3 is development data from now on; its published figures stand, and any later score on it is a development number.

**A training-length limitation in every past RL result.** GRPO's training rollouts are capped by `rl_max_new`, 24 tokens by default, and no sweep overrode it (`lm.py`, `grpo.py`). This applies to every GRPO run so far: the tiny-model work excepted, rounds 2 and 3, h3, h3_17, the placebo arms, and the product recipe. Evaluation limits (48, 200) never applied to training, and training-side truncation was never measured. Where it matters: tasks whose replies need more than 24 tokens to reach the answer. For short arithmetic replies ("10 + 25 = 35") it should not matter. For h3 word and code tasks, and for any working-style reply, the policy may never have reached an answer in training, so zero rewards there could be this cap and not incompetence, and h3_17's working-prompt evaluation at 200 tokens was measured on policies trained under a 24-token cap with no working requested. Those results are not rescored or reinterpreted; they stand with this limitation. From round 4, GRPO records `rollouts_truncated` and `mixed_groups`, and h4 trains at the same limit as it evaluates. The product default is now 64 tokens, with truncation recorded per run; past results keep their 24-token limitation.

**How test v4 is scored, written before scoring.** Engine as committed at this point. Reported separately for each part: clean real, known-bad, planted on real rows, public, contaminated, environments. Blocking flags are the primary result; advisory signals (multiple choice, free text, chat, non-English) are reported beside them, and a false advisory is not a blocked price. False flags are reported per source with an upper bound. It is scored once. Multiple choice may become blocking only in a later round, on evidence beyond this set.

**Test v4 crash and resume.** Scoring on 2fa7e455 stopped at case 9 with a NameError: a cleanup in that commit deleted the constant `MCQ_COT`. The development run of the two-route check used the commit before the cleanup, and no fast test covers that path. The fix (58bdec7d) restores that one line, unchanged. Cases 1-8 (`multiarith` and `mawps`) took the numeric judge path, never reached the broken line, and are kept without a rerun (`out/test_v4_results.first8.json`). Scoring resumed from case 9 under the same hash. Engine: 2fa7e455 for cases 1-8, 58bdec7d for cases 9-71. No threshold or other code changed. Scoring stopped again at case 29: one real Alpaca row has an empty reply, and the loader refuses the whole file. The frozen data was not edited. The evaluation script now records such a case as rejected by the loader and excludes it from flag scoring; the engine did not change.

**Forecast pre-flight** (`out/h4/h4_preflight.json`, no training, under 3 GPU minutes, 400 items per family, same prompt and 32-token reply limit at every size). On choice and classification families, 135M and 360M sit at chance on nearly everything, while 1.7B is far above it (for example `arc_easy` 74% against 25%, `sciq` 74%, `csqa` 48% against 20%). A 10-90% band alone would pass these at-chance scores, so accuracy is judged against chance as well. Fine-tuning and RL are separate arms with separate verdicts, never pooled.

**Test v4 result** (`out/test_v4_results.json`, `out/test_v4_report.json`, `scripts/report_test4.py`; scored once, hash verified, 70 of 71 cases; one Alpaca file refused by the loader). **Precision 0.51, recall 0.69, 47 of 70 exactly right.** Engine: 2fa7e455 for cases 1-8, 58bdec7d after. Below the 0.90 and 0.95 targets. Blocking flags only:

| Part | Cases | Exactly right | Notes |
|---|---|---|---|
| Environments | 21 | **21** | 12 of 12 new grader bugs [lower 95% bound 0.78], 3 of 3 reworded suite leaks, 6 of 6 honest and control cases |
| Contaminated datasets | 2 | 2 | |
| Clean real | 31 | 18 | 13 draws falsely flagged [upper 95% bound 0.58] |
| Known-bad | 4 | 2 | The two GSM-Plus sets caught; TruthfulQA's false answers advisory only |
| Planted on real rows | 9 | 2 | Mostly advisory types |
| Public | 3 | 2 | Reworded copies caught (0.57), distractor copies missed (0.12) |

False flags per source, draws: `multiarith` 0/3, `mawps` 0/3, `gsmplus` 0/2, `qasc` 0/3, `medmcqa` 0/3, `alpaca` 0/2, `truthful` 1/3, `mmlu` 3/3, `aqua` 3/3, `oasst` 3/3, `prealgebra` 3/3. Zero counts are weak: 0 of 3 allows up to 63%. Clean math in plain text, 0 of 8 draws [upper bound 0.31].

Causes, found after scoring and not acted on:

- `prealgebra`, **a defect in the unsupported-final check.** It cannot read LaTeX: in `$102/2=\\boxed{51}$` the answer looks unproduced. One of the two fixes from after v3 was the sample-size rule for that audit. It held on prose (`alpaca` and `oasst` raised no arithmetic flag), and this LaTeX defect is a separate one.
- `off_topic`, 9 false flags, **a real limit.** With a 60-row suite drawn from a broad source, diverse material sits far from its nearest suite item. The check is unreliable on small custom suites.
- `oasst`, a **labelling mistake in the test.** OASST has several replies per prompt, so 23% of suite prompts truly appear in the material. The detector was right. The frozen label stands.
- `aqua`, 5 gated hits on 60 suite items (0.067). Whether these are true near-duplicates was not checked.
- Multiple choice, the second post-v3 change: the 0.30 threshold **did not travel.** `medmcqa` clean read 0.42-0.58 and `mmlu` 0.31 at worst, 4 false advisories in 12 clean draws, though `qasc` held (at most 0.21). The check stays advisory.
- `planted_mawps_30`: detected at 0.27, downgraded because the language heuristic called this English file non-English.
- Reports must not imply general precision. The product's flags are best read per data type: strong on graders and plain-text math, weak on LaTeX math and on small custom suites.

**Forecast pilot and dev trial** (`out/h4/`, `out/forecast_h4_dev.json`; dev families `ag_news`, `rotten`, `emotion`, pilot rows).

- *RL arm, no family passes.* On every family tried, reward at 135M and 360M stays at guessing level, with gains around +/-3 and 135M to 360M agreement 0.43 on 30 pairs. 1.7B does learn (reward 0.6 to 0.8, +7 to +11). **RL forecasting remains untested on non-arithmetic work.** No RL arm is in the final set.
- *Fine-tuning gate*, replacing the base-accuracy gate, which would block nearly everything. A family passes when clean minus all-wrong material is at least 5 points at the proxy, and the larger model is under 90% base. Passing: `ag_news`, `rotten`, `emotion`, `dbpedia`, `imdb`, `amazon`, `cr`, `subj`, `enron`, `sst5`, `bbc`. Abstaining: `sciq`, `yelp` (measured), and `arc_easy`, `csqa`, `openbook` (small sizes only). So coverage so far is classification, not knowledge questions.
- *Dev scores, screen-passing pairs / all pairs:* baseline 360M to 1.7B 0.41 / 0.63; 10x lower learning rate 0.64 / 0.58; truncated 1.7B (10 steps, net of same-length placebo) 0.73 / 0.74; 135M to 360M 0.82 / 0.84. Noise ceiling at 1.7B 0.92 / 0.94, at 360M 0.70 / 0.66 (some 360M seeds were lost to GPU memory). These forms were picked on development data, and development scores are optimistic.

**h4, pre-registered before any final run.** Fine-tuning only. Hash of materials and suites in `out/h4_final.sha256`; config in `scripts/h4_config.json`. Each candidate is scored once by `scripts/h4_score.py final`.

- *Set:* 8 families never measured at 1.7B (`dbpedia, imdb, amazon, cr, subj, enron, sst5, bbc`), final rows only, disjoint from dev rows and suites, 10 materials each, 2 seeds, 135M, 360M and 1.7B, 600-item suites or the whole suite where smaller.
- *Primary question:* does 360M predict 1.7B? *Primary number:* decision accuracy within family on pairs of the 7 screen-passing materials (`clean, pool100, pool200, pool300, wrong10, off25, drop`), 168 pairs. All pairs (360) sit beside it, with noise ceiling and family coverage.
- *Candidates, three in all:* `acc_final` at 360M (baseline), 10x lower learning rate at 360M, truncated 1.7B net of placebo. The truncated run is a target measurement and not a small-model forecast, and it is reported as that. Secondary: `acc_final` 135M to 360M.
- *Pass bar for a candidate:* screen-passing decision at least 0.80, permutation p below 0.0167 (0.05 over three candidates), and at least 5 of 8 families above 0.5. The 0.90 target stays reported as a target.
- *Inconclusive* if the 1.7B screen-passing noise ceiling is below 0.75.
- *Stop rule:* a candidate that misses the bar is retired, not retuned.

**h4 result** (`out/forecast_h4_final.json`, `out/h4/`, 976 runs, none missing, `cuda`, torch 2.14.1; scored once). Fine-tuning only. The 1.7B noise ceiling on screen-passing pairs is 0.77, above the 0.75 line, so the test is conclusive.

| Candidate | Screen-passing (161 pairs) [90%], p | Families above 0.5 | All pairs (349) | Bar met? |
|---|---|---|---|---|
| `acc_final` 360M to 1.7B | **0.61** [0.43, 0.76], 0.0004 | 6 of 8 | 0.73 | No |
| 10x lower learning rate, 360M to 1.7B | **0.45** [0.26, 0.63], 0.15 | 4 of 8 | 0.58 | No |
| Truncated 1.7B net of placebo | **0.68** [0.53, 0.82], 0.0007 | 7 of 8 | 0.81 | No |
| Secondary: `acc_final` 135M to 360M | **0.77** [0.64, 0.88], 0.0001 (137 pairs) | 6 of 7 | 0.88 | Below 0.80, at its 0.77 ceiling |
| Also scored: `acc_final` 135M to 1.7B | 0.58, 0.006 | | 0.71 | |

All three pre-registered candidates miss the 0.80 bar and are retired as forecasts, not retuned. 7 pairs had exact target ties and dropped out of the 168, and 8 more of the secondary's pairs where a target was tied at 360M. The result is real but limited: small models beat chance on classification material, with p far below the bar, yet they rank materials a buyer would actually compare only about 6 times in 10, and pre-registered disasters lift that to 7 in 10. It holds for 8 classification families, fine-tuning, this suite and recipe. Knowledge questions failed the gate, so nothing here covers them. A truncated target run did best at 360M's job, but it trains the target, so it does not show that a small model forecasts anything.

Lower learning rate is retired. In this short-run setting it scored worse than the baseline on every headline. It did well on one family (`cr`), which is no basis for a claim.

**RL test skipped.** It was approved on condition of at least 1 hour of reserve after h4. h4 took 4.05 hours and finished with about 0.9 hours left under the 7-hour cap, partly because 8 unseen families and 976 runs took longer than the 3.5-hour estimate. **RL forecasting remains untested on non-arithmetic work.** The code is ready (`scripts/h4_run.py`, `scripts/h4_score_rl.py`).

## 7. Grade and fair value

`touchstone/valuation.py`. The rules are printed in every report. The grade has to agree with the measurements: nothing that is mostly public, contaminated or gameable can grade above D.

**Grading rubric** (applied in this order):

| Step | Rule |
|---|---|
| 1 | **F** if a public copy (>= 80% of items already in free public data), or if training measurably lowers held-out accuracy (net and raw 90% intervals both below zero). |
| 2 | Otherwise grade the headline net gain at 1.7B (measured in full mode, forecast in quick mode): **A** >= 5 points, **B** >= 2, **C** >= 0.5, else **D**. |
| 3 | Cap at **D** if any of: no measurable gain (the net gain's 90% interval at the largest trained size includes zero, unless the smooth score's interval is above zero and accuracy is positive), gameable grader (any probe earns >= 20% reward above the grader's own random noise, or the grader rejects >= 10% of reference answers), answer leakage (answer in >= 20% of prompts), contamination (> 5% overlap with the held-out suite), transfer gap (training reward +15 points with no matching held-out gain), half or more of the items already public, noisy labels, or half or more of the material off-topic. |
| 4 | Cap at **C** if half or more of the items are exact repeats. |

**Fair value per unique item** = headline net gain x $ per point x (share not already free) / max(unique items, example presentations in the training budget). The second term matters for small sets: the gain was measured with a fixed budget (960 presentations in full mode), so a set of 20 examples repeated 48 times cannot be credited with the whole gain per 20 items. Before this rule, the planted `duplicated` set was priced at $66,625 per item; now $2,776. It is **zero** when any blocking flag fires: gameable grader, answer leakage, contamination, transfer gap, noisy labels, public copy (>= 80%), no measurable gain, or harmful. Off-topic and partly-public material is priced only on what remains. The default $ per point ($5,000) is an assumption about the buyer, not a measurement; set it with `--dollars-per-point`. It is chosen so a clean A-grade reasoning dataset lands near what expert-written examples sell for ($50 to $150 each). The earlier default of $250,000 priced the 400-item demo dataset at $1.5M, which no buyer would accept as a reading of a 135M model's gain. When the forecast is uncalibrated (rank at the largest size), reports say the gain was *measured at* that size instead of quoting it at the 1.7B target.

Informational flags explain a result without changing it: `no_learning_signal` (the trained sizes never solve the tasks, so RL had nothing to learn from) and `suppresses_reasoning` (after training the model stops working problems out, as answer-only data does to small models, and accuracy falls).

Value is split evenly across items. Per-item value (LESS, Xia et al. 2024; Data Shapley, Ghorbani & Zou 2019) and marginal value on top of what the buyer already owns (one more "free + vendor" run per rung) are the next steps; neither is implemented.

## 8. Limits

- Small stand-in models: rankings carry across scale better than absolute gains do. Absolute points at a 70B model are not claimed.
- Short fixed budgets: a material whose value appears only after long training (a high ceiling with a slow start, as in ScaleRL) will be under-rated.
- One domain per suite: skills outside the suite earn nothing.
- The built-in suites are generated by code in this repo. They are held out from the sample vendors, but a real vendor with repo access could target them. Production suites must be private.
- Vendor environment code runs in-process. Production needs a sandbox with no network.
- Laptop compute: few seeds, 120-200 suite items, so intervals are wide. That is the honest price of a laptop.

## References

- Allal et al. 2025, SmolLM2. arXiv:2502.02737
- Broder 1997, On the resemblance and containment of documents.
- Gao, Schulman, Hilton 2022, Scaling Laws for Reward Model Overoptimization. arXiv:2210.10760
- Ghorbani & Zou 2019, Data Shapley. arXiv:1904.02868
- Heineman et al. 2025, Signal and Noise. arXiv:2508.13144
- Hu et al. 2021, LoRA. arXiv:2106.09685
- Khaddaj, Engstrom, Madry 2025, Small-to-Large Generalization: Training Data Influences Models Consistently Across Scale. ICLR 2025, arXiv:2505.16260
- Khatri et al. 2025, The Art of Scaling Reinforcement Learning Compute for LLMs (ScaleRL). arXiv:2510.13786
- Lee et al. 2022, Deduplicating Training Data Makes Language Models Better. arXiv:2107.06499
- Magnusson et al. 2025, DataDecide: How to Predict Best Pretraining Data with Small Experiments. ICML 2025
- Rajan 2026, Auditing Reward Hackability in Code RL Training Environments. arXiv:2606.16062
- Ruan, Maddison, Hashimoto 2024, Observational Scaling Laws. arXiv:2405.10938
- Schaeffer, Miranda, Koyejo 2023, Are Emergent Abilities of Large Language Models a Mirage? arXiv:2304.15004
- Shao et al. 2024, DeepSeekMath (GRPO). arXiv:2402.03300
- Shao et al. 2025, Spurious Rewards: Rethinking Training Signals in RLVR.
- Tan et al. 2025, Scaling Behaviors of LLM Reinforcement Learning Post-Training.
- Xia et al. 2024, LESS: Selecting Influential Data for Targeted Instruction Tuning. arXiv:2402.04333
- Yang et al. 2023, Rethinking Benchmark and Contamination for Language Models with Rephrased Samples. arXiv:2311.04850
- Zhang et al. 2024, A Careful Examination of LLM Performance on Grade School Arithmetic (GSM1k). arXiv:2405.00332
- Related, not used directly: Zhang et al. 2024, When Scaling Meets LLM Finetuning (ICLR 2024); TuneAhead (arXiv:2606.17660, ICML 2026), which predicts fine-tuning success from dataset descriptors plus a short probe run, a close cousin of the quick mode.
