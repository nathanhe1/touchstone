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

Hackability is the most reward any probe earns. At 20% or more the grader is flagged, the grade is capped at D, and nothing is priced. The audit also checks that the grader accepts reference answers, is deterministic, and stays in [0, 1].

A second, training-based signal follows Gao et al. (2022): if training reward rises by 15 points or more while held-out accuracy does not (transfer gap), the policy is learning the grader rather than the skill.

## 5. Overlap and contamination

Three tiers (`touchstone/overlap.py`):

1. exact match after normalization;
2. near-duplicate: character 5-gram Jaccard of at least 0.6 (Broder 1997; Lee et al. 2022);
3. reworded: all-MiniLM-L6-v2 sentence-embedding cosine of at least 0.85, which catches paraphrases that string checks miss (Yang et al. 2023).

For text with numbers, tiers 2 and 3 also require the same multiset of numbers. Without that guard, every "Sam has 12 apples" would match every "Sam has 15 apples": the same template, not the same item.

Overlap is checked against the held-out suite (contamination: more than 5% blocks the price and caps the grade at D) and against a free public baseline (GSM8K train for `word_math`; your `--public` file otherwise). The share already free discounts the price, and more than half free caps the grade at C.

## 6. Forecast: small to large

### Methods compared

1. **extrapolate**: the original prototype. Fit gain against log(parameters) through the small rungs and extend the line to the target.
2. **rank_largest**: DataDecide's finding (Magnusson et al. 2025) was that none of eight scaling-law fits beat ranking at the largest affordable size. The prediction is the gain at the largest small rung.
3. **calibrated**: learn the small-to-large map from a sweep of materials run at every size, target gain ~ a + b x accuracy gain + c x probability gain at the largest small rung. This is observational calibration in the spirit of Ruan et al. (2024), and it is consistent with Khaddaj et al. (2025), who find data effects are strongly correlated across scale. The **range** in a report is the 80% quantile of absolute leave-one-out error on that sweep, the error actually observed on datasets the fit never saw.

Every method is scored by **leave-one-out** on the sweep, with Spearman rank correlation, pairwise **decision accuracy** (did it pick the same winner of each pair as the 1.7B truth? chance is 0.5), and mean absolute error.

### Results

RESULTS_PLACEHOLDER

### What the forecast is not

- It is validated to 1.7B, about 13x the 135M rung. Buyers train 7B to 400B+ models. Touchstone reports no number beyond 1.7B, because nothing beyond it was validated, and RL gains tend to shrink as base models get stronger (Tan et al. 2025; ScaleRL, Khatri et al. 2025).
- A calibration holds for one suite, one recipe and one model family. A custom suite has no calibration until a sweep is run for it (`scripts/validate_sft.py` is the template), so its forecast falls back to rank_largest, labelled uncalibrated.
- RL environments on real models have no calibration sweep yet: GRPO at three sizes x 15+ environments x seeds does not fit on a laptop. Environment forecasts are rank_largest with seed and item noise only. The RL forecasting methods were validated on the tiny GPTs instead.

## 7. Grade and fair value

`touchstone/valuation.py`. The rules are printed in every report. The grade has to agree with the measurements: nothing that is mostly public, contaminated or gameable can grade above D.

**Grading rubric** (applied in this order):

| Step | Rule |
|---|---|
| 1 | **F** if a public copy (>= 80% of items already in free public data), or if training measurably lowers held-out accuracy (net and raw 90% intervals both below zero). |
| 2 | Otherwise grade the headline net gain at 1.7B (measured in full mode, forecast in quick mode): **A** >= 5 points, **B** >= 2, **C** >= 0.5, else **D**. |
| 3 | Cap at **D** if any of: no measurable gain (the net gain's 90% interval at the largest trained size includes zero, unless the smooth score's interval is above zero and accuracy is positive), gameable grader (any probe earns >= 20% reward, or the grader rejects >= 10% of reference answers, or is non-deterministic), answer leakage (answer in >= 20% of prompts), contamination (> 5% overlap with the held-out suite), transfer gap (training reward +15 points with no matching held-out gain), half or more of the items already public, noisy labels, or half or more of the material off-topic. |
| 4 | Cap at **C** if half or more of the items are exact repeats. |

**Fair value per unique item** = headline net gain x $ per point x (share not already free) / unique items. It is **zero** when any blocking flag fires: gameable grader, answer leakage, contamination, transfer gap, noisy labels, public copy (>= 80%), no measurable gain, or harmful. Off-topic and partly-public material is priced only on what remains. The default $ per point ($250,000) is an assumption about the buyer, not a measurement; set it with `--dollars-per-point`.

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
