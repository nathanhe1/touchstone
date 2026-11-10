# h5 real competing materials

Built by `scripts/h5_materials.py` (`fetch` with pyarrow 17.0.0, then `build` in the engine venv). Every file below is a
uniform random sample of one public source at a pinned Hugging Face revision, the same size for every material, and
screened against its family's held-out suite before it was written. Rebuilding from the cached sources reproduces every
hash (checked twice). Combined hash of all material and suite files: `8a8a837a353639d6d47cf96e772eb04d26841895aa64152534b72ced58ff133b` (`h5_materials.sha256`; per-file
hashes and every number below are in `manifest.json`). `tests/test_h5_materials.py` checks the files against it.

## Row format

- Materials: `{"id", "prompt", "completion", "answer", ...}`. Fine-tuning trains on prompt -> completion. For `nli`
  and `sci` the completion is the answer letter and the prompt uses the h4 form (options as `A) ...`, then
  "Reply with the letter only."). For `gsm` the completion is the source's worked solution, unchanged except that
  GSM8K's calculator annotations (`<<48/2=24>>`) are removed. `answer` lets each material double as an RL
  environment (numeric match for `gsm`, letter match for `nli`/`sci`, `kk_correct` for `kk`).
- Suites: `{"id", "prompt", "answer", "match", ...}` in a fixed seeded order; for `nli`/`sci` classes are
  interleaved so any prefix is balanced. `kk` suite rows also carry `names` and `solution` for the grader.

## What the screen found

- **ANLI's own training rounds share premises with ANLI test**: 146 of the first 1,000 sampled `anli_train` rows
  (14.6%) matched a test item, all as near-duplicates or paraphrases of the same Wikipedia premise with a different
  hypothesis. They were dropped and replaced. The other four NLI sources had none (FEVER-NLI: 2 near matches among
  3,000 candidates, outside the first 1,000).
- **ARC train splits contain ARC-Challenge test questions**: `arc_challenge_train` 15 of 1,000 (6 exact copies),
  `arc_easy_train` 8 of 1,000 (2 exact). Dropped and replaced. SciQ, OpenBookQA, QASC and MMLU's auxiliary set had 1-2
  each, mostly paraphrase matches.
- **Grade-school math sources are clean against GSM8K-Platinum** under the item screen (0 of 1,000 for all five).
  The gated answer-and-number check matched 0.8-1.5% of suite items per source (`gated_suite_match_rate`), under the
  5% contamination line.
- **Knights and Knaves**: the engine's generic screen matched 94% of K&K training puzzles to the test set, because all
  puzzles share one template. None is the same puzzle (same people and near-identical statements), so none was dropped.
  This is the "same-template clone" question for v5, and it means the product would falsely call this environment
  contaminated against its own test set.

## Things the run matrix must handle

- **Reply lengths differ a lot.** Completion tokens (Qwen2.5 tokenizer) p50 / p95: GSM8K 85 / 176, MetaMathQA 147 / 330,
  OpenMathInstruct-2 152 / 290, Orca-Math 260 / 553, NuminaMath-CoT 372 / 1026. At h4's `max_len` of 256, 82% of
  NuminaMath and 67% of Orca-Math rows would be cut before the answer, which measures the cut, not the material.
  The gsm arm needs `max_len` >= 1024 (or the cut reported as part of the comparison), and an evaluation reply limit
  that fits a worked solution.
- **MMLU's auxiliary set has long prompts** (p50 387 tokens, RACE passages); 78% exceed 256 tokens with the reply.
- **QASC has 8 options**, the suite (ARC-Challenge) 4 (a few 3 or 5).
- **Licences**: ANLI (suite and material), SciQ and Knights and Knaves are non-commercial; fine for this test, not for
  resale. FEVER-NLI's Hub copy is untagged (FEVER itself is CC-BY-SA-3.0). Its Hub copy also names the claim
  "premise" and the evidence "hypothesis"; they are swapped back to standard NLI order here.
- First-listed material per family (for the all-wrong arm): `gsm8k_train`, `snli`, `arc_easy_train`, `kk_train`.

Seed 20261110, 1000 rows per material. Tokens counted with Qwen/Qwen2.5-1.5B-Instruct.

**gsm** (worked solutions, numeric answer). Suite: `examples/h5/gsm/suite.jsonl`, 1209 rows from madrylab/gsm8k-platinum test @ e762492455, licence MIT, sha256 `4496e48f635385db`.

| Material | Source @ revision | Licence | Eligible rows | Suite overlap in raw sample | Dropped | Majority class | Completion tokens p50 / p95 | Over 512 tokens | sha256 (first 16) | Why a buyer compares it |
|---|---|---|---|---|---|---|---|---|---|---|
| `gsm8k_train` | openai/gsm8k @ 740312add8 | MIT | 7,473 | 0 of 1000 | none | n/a | 85 / 176 | 0% | `3b1996dbcb13b2dc` | The benchmark's own human-written training split: the default a buyer already has for free. |
| `metamathqa_gsm` | meta-math/MetaMathQA @ aa4f34d3d2 | MIT | 240,000 | 0 of 1000 | duplicate 9 | n/a | 147 / 330 | 1% | `7c5c2e731ae9de2f` | MetaMathQA's GSM8K-derived part (rephrased, answer-augmented, backward questions); widely used to lift GSM8K scores. |
| `omi2_gsm` | nvidia/OpenMathInstruct-2 @ 469216e3f4 | CC-BY-4.0 | 153,311 | 0 of 1000 | duplicate 3 | n/a | 152 / 290 | 0% | `c5e3a72eb14ad8de` | NVIDIA's OpenMathInstruct-2 1M release, grade-school part: new problems and solutions synthesised by Llama-3.1-405B. |
| `orca_math` | microsoft/orca-math-word-problems-200k @ 29255d1770 | MIT | 200,035 | 0 of 1000 | none | n/a | 260 / 553 | 18% | `1c7fc59eb70113d3` | Microsoft's Orca-Math 200k: GPT-4-Turbo solutions to synthetic grade-school word problems, sold as a GSM8K booster. |
| `numina_cot` | AI-MO/NuminaMath-CoT @ 9d8d210c9f | Apache-2.0 | 859,494 | 0 of 1000 | none | n/a | 372 / 1026 | 42% | `e51fed3105b20aba` | NuminaMath-CoT as delivered: a broad math set (K-12 to olympiad) a buyer might pick to improve math in general. |

**nli** (3-way NLI as a letter choice). Suite: `examples/h5/nli/suite.jsonl`, 3200 rows from facebook/anli test_r1+test_r2+test_r3 @ 8e4813d81f, licence CC-BY-NC-4.0 (non-commercial), majority class 0.334, sha256 `fd6340b0d01c2bac`.

| Material | Source @ revision | Licence | Eligible rows | Suite overlap in raw sample | Dropped | Majority class | Completion tokens p50 / p95 | Over 512 tokens | sha256 (first 16) | Why a buyer compares it |
|---|---|---|---|---|---|---|---|---|---|---|
| `snli` | stanfordnlp/snli @ cdb5c3d5ee | CC-BY-SA-4.0 | 549,367 | 0 of 1000 | none | 0.334 | 1 / 1 | 0% | `9aafeec53d0c949c` | The original large NLI set (image captions); cheap and large. |
| `mnli` | nyu-mll/multi_nli @ da70db2af9 | mixed per genre: CC-BY-3.0, CC-BY-SA-3.0, MIT, other (OANC) | 392,702 | 0 of 1000 | none | 0.334 | 1 / 1 | 0% | `c98a3e1deafa4564` | MultiNLI: multi-genre, the standard NLI training set. |
| `wanli` | alisawuffles/WANLI @ 61c95318fd | CC-BY-4.0 | 102,885 | 0 of 1000 | none | 0.334 | 1 / 1 | 0% | `723d802922c9629c` | WANLI: GPT-3 generated and human-filtered, published as transferring better than MultiNLI to hard sets. |
| `anli_train` | facebook/anli @ 8e4813d81f | CC-BY-NC-4.0 (non-commercial) | 162,865 | 146 of 1000 | suite_overlap 168 | 0.334 | 1 / 1 | 0% | `1283fb1077342917` | ANLI's own adversarial training rounds, in-distribution for the suite. |
| `fever_nli` | pietrolesci/nli_fever @ 1eddac6311 | untagged on the Hub; built from FEVER (CC-BY-SA-3.0, Wikipedia-derived) | 208,346 | 0 of 1000 | duplicate 2 | 0.334 | 1 / 1 | 0% | `0ffd74571648e312` | FEVER claims paired with Wikipedia evidence, a fact-verification set re-cast as NLI. |

**sci** (science multiple choice, letter answer). Suite: `examples/h5/sci/suite.jsonl`, 1172 rows from allenai/ai2_arc ARC-Challenge/test @ 210d026faf, licence CC-BY-SA-4.0, majority class 0.265, sha256 `72fdf94ddb2acd63`.

| Material | Source @ revision | Licence | Eligible rows | Suite overlap in raw sample | Dropped | Majority class | Completion tokens p50 / p95 | Over 512 tokens | sha256 (first 16) | Why a buyer compares it |
|---|---|---|---|---|---|---|---|---|---|---|
| `arc_easy_train` | allenai/ai2_arc @ 210d026faf | CC-BY-SA-4.0 | 2,251 | 8 of 1000 | suite_overlap 8, duplicate 1 | 0.262 | 1 / 1 | 0% | `33f5754c11eafb9d` | ARC-Easy training questions: same exam source as the suite, easier items. |
| `arc_challenge_train` | allenai/ai2_arc @ 210d026faf | CC-BY-SA-4.0 | 1,119 | 15 of 1000 | suite_overlap 15, duplicate 1 | 0.272 | 1 / 1 | 0% | `c12c866519bcbc43` | ARC-Challenge's own training split: in-distribution for the suite, and small. |
| `sciq` | allenai/sciq @ 2c94ad3e1a | CC-BY-NC-3.0 (non-commercial) | 11,679 | 1 of 1000 | suite_overlap 1 | 0.265 | 1 / 1 | 0% | `c552822eb147fcb9` | SciQ: crowd-written science exam questions with supporting passages. |
| `obqa` | allenai/openbookqa @ 388097ea77 | Apache-2.0 per the AllenAI release; 'unknown' on the Hub card | 4,957 | 2 of 1000 | duplicate 4, suite_overlap 2 | 0.285 | 1 / 1 | 0% | `bb58198ed792a5e9` | OpenBookQA: elementary science questions that need one core fact plus common knowledge. |
| `qasc` | allenai/qasc @ a34ba204eb | CC-BY-4.0 | 8,134 | 1 of 1000 | duplicate 18, suite_overlap 1 | 0.144 | 1 / 1 | 0% | `95a4a4f06f423cfa` | QASC: grade-school science questions built by composing two facts, 8 options. |
| `mmlu_aux` | cais/mmlu @ c30699e835 | MIT | 99,842 | 2 of 1000 | suite_overlap 2 | 0.282 | 1 / 1 | 12% | `39a3a8e33d7ea353` | MMLU's auxiliary training set: a broad multiple-choice mix (ARC, OBQA, RACE, MCTest and more). |

**kk** (RL environment: logic puzzles, graded by kk_correct). Suite: `examples/h5/kk/suite.jsonl`, 400 rows from K-and-K/knights-and-knaves test people 2-5 @ 2f68547989, licence CC-BY-NC-SA-4.0 (non-commercial), sha256 `a814c5d23e263d0c`.

| Material | Source @ revision | Licence | Eligible rows | Suite overlap in raw sample | Dropped | Majority class | Completion tokens p50 / p95 | Over 512 tokens | sha256 (first 16) | Why a buyer compares it |
|---|---|---|---|---|---|---|---|---|---|---|
| `kk_train` | K-and-K/knights-and-knaves @ 2f68547989 | CC-BY-NC-SA-4.0 (non-commercial) | 3,200 | 0 of 1000 | none | n/a | 33 / 43 | 0% | `f6f5e152655bf0d2` | Knights and Knaves (Xie et al. 2024), procedurally generated logic puzzles with a unique checkable answer; the RL environment Logic-RL (Xie et al. 2025) trained on. |

