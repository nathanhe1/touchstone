# Case study: CodeAlpaca and its rephrased HumanEval problems

**Verdict: missed.** Touchstone found no overlap between CodeAlpaca and HumanEval, where a published audit found 21 of HumanEval's 164 problems rephrased in it. Touchstone also cannot score a code suite, so its training measurement here is empty.

## What was appraised

- **Material:** CodeAlpaca-20k as published, a JSON array of 20,022 instruction / input / output records (sahil2801/CodeAlpaca-20k @ `152bb5e9a2`, CC-BY-4.0). sha256 `2cabb4ceaf698716`. The loader skipped 6 records with an empty instruction or output and said so in the report.
- **Held-out suite:** HumanEval's 164 prompts with their canonical solutions (openai/openai_humaneval @ `7dce6050a7`, MIT), as an exact-match suite, which is the only kind Touchstone accepts.
- **Run:** quick mode on the Mac, CPU, engine commit `c21c9919`, 21 minutes. Raw output: `out/case_studies/code_alpaca_quick/`; string-tier check on all 164 items: `out/case_studies/string_overlap.json`.

## The documented problem

Yang et al. (2023), *Rethinking Benchmark and Contamination for Language Models with Rephrased Samples* (arXiv:2311.04850, Table 7): **21 of 164 HumanEval problems (12.8%) have a rephrased copy in CodeAlpaca.** The copies are the same task described in different words, usually without the function signature.

## What Touchstone found

| Check | Result |
|---|---|
| Suite items found in the material (150 sampled, all tiers) | **0** |
| Suite items found, string tiers, all 164 | **0** |
| Off-topic share of the material against the suite | 39% (flag needs 50%) |
| Code replies that fail to parse (74 tried) | 5 (6.8%); behaviour unchecked, no tests supplied |
| Training, 135M, 30 steps | accuracy 0.0% before, after, and for the placebo |
| Flags | `no_measurable_gain` (blocking) |
| Grade and price | **D, $0 per item** |

## Did the grade and the price come out right?

**No.** The documented problem is contamination, and Touchstone reported 0.0%. The $0 price has an unrelated cause: the suite is scored by exact string match against the canonical solution, which no model reply will ever equal, so accuracy is 0% by construction and "no measurable gain" follows. A buyer would read this report as "clean but useless", and both halves are wrong.

## What it missed, and why

- **All 21 rephrased problems.** A HumanEval prompt is a Python signature plus a docstring with examples. CodeAlpaca's version is one English sentence. The string tiers compare character 5-grams and the paraphrase tier compares whole-prompt sentence embeddings at a 0.92 cosine line; a code prompt and a one-line English instruction land far apart on both.
- **Code suites.** Touchstone has no way to run a reply against tests, so it cannot measure transfer to any code benchmark. This case shows the gap on the best-known one.

Filed to the researcher in `STATUS.md` as a miss.
