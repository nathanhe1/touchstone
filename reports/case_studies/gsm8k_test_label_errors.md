# Case study: the original GSM8K test set and its documented label errors

**Verdict: missed.** Touchstone refused to price the set, but for a different reason (it is a public copy). Its label check did not find the errors GSM8K-Platinum documents.

## What was appraised

- **Material:** the original GSM8K test split, all 1,319 rows as published (openai/gsm8k @ `740312add8`, MIT), question and worked solution. sha256 `3bca3575ddc24bad`.
- **Held-out suite:** Touchstone's built-in `word_math` suite, with its default public baseline (GSM8K train and test, SVAMP, ASDiv: 12,097 problems).
- **Run:** quick mode on the Mac (MPS), engine tree at `122b8584`, 337 s. Raw output: `out/case_studies/gsm8k_test_quick/`. Row-level comparison with Platinum: `out/case_studies/gsm8k_label_check_vs_platinum.json`.
- **Order of events:** this run happened before test v5 was frozen, and v5 uses GSM8K-Platinum. The researcher was told at once, nothing was tuned on it, and v5 reports its GSM8K-Platinum part separately as "previewed".

## The documented problem

Vendrow et al. (2025), *Do Large Language Model Benchmarks Test Reliability?* (arXiv:2502.03461), re-checked GSM8K test and published GSM8K-Platinum (madrylab/gsm8k-platinum @ `e762492455`). Of the 1,319 questions, 219 were flagged by models; **110 were removed** as ambiguous or flawed and **10 had their answer corrected**. That is 120 problem rows, 9.1% of the set, and 10 outright wrong labels (0.8%).

## What Touchstone found

| Check | Result |
|---|---|
| Overlap with free public data | **93.5%** of rows are in the public baseline, all exact matches |
| Arithmetic check on worked solutions | 11 of 1,296 checked solutions flagged (0.85%); the flag needs 10% |
| Judge re-solving a sample of 60 | 1 confident disagreement in 19 (5.3%); the flag needs 15% |
| Flags | `copied_from_public` (blocking) |
| Grade and price | **F, $0 per item**; quick mode stopped after screening |

The 11 rows the arithmetic check flagged, against Platinum's verdicts:

| Platinum's verdict | Rows in the set | Flagged by Touchstone |
|---|---|---|
| Answer corrected | 10 | **0** |
| Removed as ambiguous or flawed | 110 | **1** |
| Kept (consensus or verified) | 1,199 | 10 |

So the check caught 1 of the 120 documented problem rows, and 10 of its 11 hits were rows Platinum kept. Most of those 10 are parsing artefacts: "4/5 of 300 = 240" is read as the claim that 4/5 equals 240.

## Did the grade and the price come out right?

**Right price, wrong reason.** $0 is correct for a buyer: this is a public benchmark's test split, and Touchstone said so. But the question this case asks is whether Touchstone sees the label errors, and it does not.

## What it missed, and why

- **All 10 wrong answers.** The arithmetic check verifies that each written equation is internally correct and that the final answer appears in the working. GSM8K's wrong labels are mostly correct arithmetic applied to a misread question, so the working is self-consistent and the check passes.
- **109 of 110 ambiguous or flawed questions.** Nothing in Touchstone reads a question for ambiguity.
- **Prevalence is below what the flag is built for.** Even a perfect detector would report 0.8% wrong labels, far under the 10% line. Touchstone's label flag answers "is this set badly mislabelled?", not "which rows are wrong?".
- **The judge is too weak to help here.** It was confident on 19 of 60 sampled rows.

Filed to the researcher in `STATUS.md` as a miss.
