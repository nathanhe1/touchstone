# Touchstone on real material: the buyer's view

Rely on Touchstone today to reject a broken grader or a copied dataset in about a minute, and to measure what a material teaches a model it actually trains. Do not rely on it to find wrong labels, to catch reworded contamination, or to pick between two good datasets on its own.

This page draws on five case studies of public materials whose problems someone else documented (this folder), the sprint's frozen tests (`METHOD.md`), and real files run through the product. Every number names its file.

## What it catches

- **Graders that pay for wrong answers.** WebArena's string-match grader, documented by Zhu et al. (2025) as passing padded answers, was refused in 63 seconds: hedged answers earn 82.5% of the reward, and the price is $0 (`out/case_studies/webarena_strings_quick/report.json`). On the frozen test it caught 6 of 6 new grader bugs (`out/test_v5_report.json`).
- **Verbatim and near-verbatim copies.** The original GSM8K test set was identified as 93.5% public and priced at $0 (`out/case_studies/gsm8k_test_quick/report.json`). MATH's training split overlaps its own test set by a documented 1.6%; Touchstone read 2.3% (`out/case_studies/math_full_suite_overlap.json`).
- **Leaks while sourcing real datasets.** Screening 37 public materials for the forecast tests, it found that 14.6% of sampled ANLI training rows share a premise with an ANLI test item, and that ARC's and MRPC's training splits hold test questions (15 and 24 per 1,000 sampled rows) (`examples/h5/manifest.json`, `examples/h5x/manifest.json`).

## What it misses

- **Wrong labels in real data.** GSM8K-Platinum corrected 10 answers and removed 110 flawed questions; Touchstone's label check flagged 1 of those 120 rows, and 10 of its 11 hits were sound (`out/case_studies/gsm8k_label_check_vs_platinum.json`). On expert-audited benchmarks it found 2 of 8 noisy sets at 13% precision (`out/test_v5_report.json`).
- **Reworded contamination.** A published audit found 21 of 164 HumanEval problems rephrased in CodeAlpaca; Touchstone found 0. The same audit found 15.4% of MATH test rephrased in MathInstruct; Touchstone found 2.4% (`out/case_studies/string_overlap.json`, `out/case_studies/math_full_suite_overlap.json`).
- **Clean material it wrongly blocks.** The arithmetic check misreads chained equalities and fractions "of" a quantity. It blocked Orca-Math, a clean synthetic set, at 18% (`out/case_studies_gpu/h5_orca_quick/report.json`), and MathInstruct at 15%. Its overlap screen matched 94% of Knights and Knaves training puzzles to the test set because they share one template.
- **Anything it cannot score.** Code suites score 0% under exact match, and a 135M model scores 2% on competition math before and after training. Both reports said "no measurable gain", which describes the measurement and not the material.

## What a buyer should and shouldn't rely on today

The researcher's summary of the frozen tests, quoted in full:

> Touchstone reliably catches broken graders and copied or leaked material: on a frozen test it caught 6 of 6 new grader bugs, 2 of 2 planted suite leaks and 8 of 8 public copies of GSM8K test. It measures what a material teaches a model it actually trains, net of a placebo, up to 8B on one 32 GB card. A 1.7B run ranks real competing fine-tuning datasets for an 8B model better than chance: it picked the better of two datasets 69% of the time across 55 pairs in 5 task families (90% interval 49-88%, against a ceiling of 78% set by the 8B's own run-to-run noise). That is a useful prior and not a decision rule. It missed the 80% bar we set in advance, a 0.6B run did no better than about 64%, and we could not show that the larger proxy beats the smaller one. Touchstone cannot yet forecast RL environments on non-arithmetic tasks: small base models earn no reward to learn from, so the test could not be run. Touchstone does not detect wrong labels in real data. On expert-audited benchmarks at natural error rates it found 2 of 8 noisy sets with 13% precision, and it falsely flagged 1 clean set in 6, mostly by mistaking shared passages for leaked test items. Its label and contamination flags on real multiple-choice and free-text data should be presented as advisory until that is fixed.

(`out/forecast_h5_real_pooled.json`, `out/forecast_h5.json`, `out/forecast_h5x.json`, `out/test_v5_report.json`.)

| Rely on it for | Treat as advisory | Don't rely on it for |
|---|---|---|
| A `gameable_grader` flag on a string or numeric grader | A `noisy_labels` flag: check the rows it lists | A clean label report meaning the labels are right |
| A `copied_from_public` flag, and exact or near-exact suite leaks | A `contaminated` flag on material that shares passages or a template with the suite | A clean overlap report meaning no reworded leak |
| The measured gain at a size it trained, net of placebo | A small run's ranking of two datasets for an 8B model (right 69% of the time) | Any forecast for RL environments, or beyond 8B |
| Reading real files: JSONL, JSON, CSV, parquet, chat formats, with bad rows skipped and counted (`out/fde_real_inputs_loader.json`) | "No measurable gain" when the base model scores near zero on the suite | Code benchmarks, or environments that need a live system |

**Speed.** On an RTX 5090 a quick appraisal of the demo dataset takes 61 seconds and the demo environment 9 seconds; a 262,000-row dataset takes 4 minutes (`out/case_studies_gpu/timing.txt`). On a laptop CPU the same large file takes 52 minutes (`out/case_studies/timing_mac.txt`).
