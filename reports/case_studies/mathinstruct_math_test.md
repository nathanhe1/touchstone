# Case study: MathInstruct and the MATH test set

**Verdict: mostly missed.** A published audit found rephrased copies of 15.4% of MATH test problems in MathInstruct. Touchstone found matches for 2.4%, under its 5% line, and raised no contamination flag. It did refuse to price the set, for a different reason that this case cannot confirm.

## What was appraised

- **Material:** MathInstruct as published, 262,039 instruction / output rows from 14 sub-sources (TIGER-Lab/MathInstruct @ `b4fdc323a7`, MIT). sha256 `50a0b2f46dbc1891`. One row (line 18,866) has an empty reply; the loader skipped it and said so. Before this sprint that one row made Touchstone refuse the whole file.
- **Held-out suite:** the MATH test split, 5,000 problems (EleutherAI/hendrycks_math @ `21a5633873`, MIT).
- **Runs, on the Mac, CPU, engine commit `c21c9919`:**
  - A quick appraisal (`out/case_studies/mathinstruct_quick/`), 52 minutes, nearly all of it the overlap screen on 262,038 prompts.
  - The same overlap screen against all 5,000 test items (`out/case_studies/math_full_suite_overlap.json`).
  - The label check split by sub-source (`out/case_studies/mathinstruct_label_check_by_source.json`).

## The documented problem

Yang et al. (2023), *Rethinking Benchmark and Contamination for Language Models with Rephrased Samples* (arXiv:2311.04850, Table 7): **769 of 5,000 MATH test problems (15.4%) have a rephrased copy in MathInstruct.** The same table gives 79 (1.6%) for MATH's own training split, which MathInstruct includes.

## What Touchstone found

| Check | Result |
|---|---|
| Test items with a match in the material, all three tiers, full test set | **118 of 5,000 (2.4%)**: 10 exact, 48 near-duplicate, 60 paraphrase |
| Where the matching rows sit | 313 of 346 in the two `MATH_train` sub-sources, 33 in `math50k_camel` |
| Gated check (similar text, same answer, shared number) | 4.5% |
| Quick appraisal, on its 149-item suite sample | 2.7% |
| Internal duplicates | 6.5% of rows |
| Label check on worked solutions | 12,600 of 84,584 flagged (**14.9%**); flag needs 10% |
| Flags | `noisy_labels` (blocking) |
| Grade and price | **D, $0 per item**; quick mode stopped after screening |

## Did the grade and the price come out right?

**Not for the documented reason, and the stated reason is unconfirmed.**

- On contamination, Touchstone read 2.4% where the audit read 15.4%. Its 118 are almost exactly what it finds in MATH train alone (114), so it saw the MATH-train part of MathInstruct and none of the rest.
- The `noisy_labels` flag comes from two sub-sources: `aqua_rat` rationales (21% flagged) and `math50k_camel` (31%). The GSM8K- and MATH-derived parts read 2-3%. Three sampled AQuA hits show one real slip in the working (2.54 x 1.5 written as 4.81) and two parsing artefacts (a chained equality `2*2*2*2*2*2=2^6=64` read as "= 2"). AQuA-RAT's crowd-written rationales are widely regarded as noisy, but we have no row-level ground truth, so this flag is neither confirmed nor refuted here.

## What it missed, and why

- **About 650 of the 769 documented rephrasings.** The audit used an LLM to judge whether two problems are the same. Touchstone's paraphrase tier requires a 0.85 sentence-embedding cosine and the same set of numbers; a rewording that changes a number's form, or a rewrite into a program-of-thought prompt, falls outside it. Note the two methods also disagree on what counts: some of the audit's pairs may be looser than "the same item".
- **Speed at this size.** 52 minutes of a "quick" appraisal went to the overlap screen. On 262k rows quick mode is not quick.

Filed to the researcher in `STATUS.md` as a miss.
