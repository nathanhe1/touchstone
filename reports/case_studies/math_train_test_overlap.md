# Case study: MATH's training split against its own test set

**Verdict: caught in size, with caveats.** Touchstone's overlap screen finds about the documented amount of train/test overlap in MATH. The amount is below Touchstone's 5% line, so no flag is raised on the full test set, and that is the right call under its rule.

## What was appraised

- **Material:** the MATH training split, 7,500 problems with worked solutions (EleutherAI/hendrycks_math @ `21a5633873`, MIT). sha256 `e89f10bac98d1666`.
- **Held-out suite:** the MATH test split, 5,000 problems, answers taken from each solution's `\boxed{}`.
- **Runs, on the Mac, CPU, engine commit `c21c9919`:**
  - A quick appraisal (`out/case_studies/math_train_quick/`), 37 minutes. Quick mode scores and screens a 149-item sample of the suite.
  - The same overlap screen against all 5,000 test items (`out/case_studies/math_full_suite_overlap.json`, 2 minutes), plus its string tiers alone (`out/case_studies/string_overlap.json`).

## The documented problem

Yang et al. (2023), *Rethinking Benchmark and Contamination for Language Models with Rephrased Samples* (arXiv:2311.04850, Table 7), report that **79 of the 5,000 MATH test problems (1.6%)** have a rephrased copy in MATH train. Their example: test "How many three-digit positive integers are multiples of 11?" against train "How many positive 3-digit numbers are divisible by 11?".

## What Touchstone found

| Check | Result |
|---|---|
| Test items with a match in train, all three tiers, full test set | **114 of 5,000 (2.3%)**: 10 exact, 65 near-duplicate, 39 paraphrase |
| Test items with a match, string tiers only | 63 of 5,000 (1.3%) |
| Gated check (similar text, same answer, shared number) | 2.9% |
| Quick appraisal, on its 149-item suite sample | 5.0%, at the line but not over it |
| Label check on worked solutions | 74 of 3,444 flagged (2.1%); flag needs 10% |
| Training, 135M, 30 steps | base accuracy 2.0%, after 1.3%, placebo 2.0%; net -0.7 points [-3.4, +2.0] |
| Flags | `no_measurable_gain` (blocking) |
| Grade and price | **D, $0 per item** |

## Did the grade and the price come out right?

**The contamination call is right; the price says little.** 2.3% against a documented 1.6% is the same order, and neither crosses a 5% line. The $0 comes from a different cause: a 135M model scores 2% on MATH before and after training, so the quick run cannot measure any gain from this material. That is a floor in the measurement and should not be read as "MATH train is worthless".

## What it missed, and the caveats

- **Touchstone's 114 are not all true copies.** Two of the three examples it prints are different problems that share wording and numbers: "maximum value of y" against "minimum value of y" on the same circle, and "a³·a² if a = 5" against "a²·a⁵ if a = 3". The same-numbers guard does not help when two different questions use the same numbers. We did not hand-check all 114, so the true count is unknown; the number matches the published one in size only.
- **Quick mode screens a sample.** On 149 suite items one or two matches move the rate by a point; the same material read 5.0% there and 2.3% on the full set. A buyer with a large suite should ask for the full screen.
- **The label check was not rerun against a ground truth here.** An earlier engine flagged 71% of these LaTeX solutions as inconsistent, which is the v4 defect the researcher has since fixed; on the fixed engine it reads 2.1%.
- **The forecast is uninformative at this size.** Nothing in this case tests whether Touchstone can value competition-math material.
