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

- **Label noise** (`screen.py`): every `expression = number` in a worked solution is re-computed (the maximal arithmetic expression left of `=`, evaluated safely). The flag fires at 10% or more of solutions with an error. On real GSM8K the rate is 1.3% (fractions and times the parser misreads), against 0% for clean data and 22-100% for the planted noisy sets. It cannot see errors in answer-only data. A label-plausibility score from SmolLM2-360M was tried and rejected on the development set, because it could not separate clean answer-only labels (0.42) from 30%-noisy ones (0.46). A stronger judge (for example sampling a 7B+ model and counting confident disagreements, the Cleanlab idea) is the fix; it does not fit this laptop's time budget.
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

### What the forecast is not

**What the product reports.** No calibrated map ships yet: fitting one needs measured gains at the target size for a dozen or more datasets, and the 1.7B rung could not be completed for the sweep on this 16 GB laptop (training fits in 4.7 GB with gradient checkpointing, but 1.7B evaluation drove the machine into swap). So `forecast.value` is the rank-at-largest number (the net accuracy gain at the largest trained size, labelled as a ranking signal whose scale at 1.7B is not validated), and `forecast.smooth_value` carries the smooth-score ranking, which is the better-validated signal. The calibrated method stays in the code and is used automatically once `touchstone/calibration/dataset_<suite>.json` exists (`scripts/validate_sft.py --target 1.7B` on a bigger machine writes the data for it).

- Validated scale: 43x on the tiny GPTs (RL) and 2.7x on real models (135M to 360M, datasets). Buyers train 7B to 400B+ models. Touchstone reports no number beyond the largest trained size, and RL gains tend to shrink as base models get stronger (Tan et al. 2025; ScaleRL, Khatri et al. 2025).
- A calibration holds for one suite, one recipe and one model family. A custom suite would need its own sweep (`scripts/validate_sft.py` is the template).
- RL environments on real models have no ladder sweep yet: GRPO at three sizes x 15+ environments x seeds does not fit on a laptop. The RL forecasting methods were validated on the tiny GPTs instead.

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
