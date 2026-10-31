# Round 3 research notes

What was read, what was tried on development data, and what was kept. Every result quoted here comes from a file in `out/` named next to it. Test v3 (`examples/redflags_test3/`, hash in `out/test_v3.sha256`) was frozen before any of this work and is not used to choose anything below.

## 1. Wrong labels

### What the literature offers

| Technique | Idea | Needs | Fit for Touchstone |
|---|---|---|---|
| Confident learning (Northcutt, Jiang, Chuang 2021, JAIR; the method behind cleanlab) | Estimate the joint distribution of given and true labels from out-of-sample predicted probabilities, with a per-class threshold (the class's mean self-confidence); items whose confident prediction differs from the label are likely errors. | A classifier that is usually right on the task. | The core idea transfers. For open-ended answers the "classes" are answers, so the practical form is *confident disagreement*: a judge that is usually right, an agreement-based confidence filter, and the disagreement rate among confident items. |
| Dataset cartography (Swayamdipta et al. 2020) | Per-item confidence and variability of the gold label across training epochs; mislabelled items sit in the low-confidence, low-variability corner. | Several epochs of training on the material. | Needs a model that can fit the task. A 135M model fine-tuned for 60 steps does not learn multi-step arithmetic, so clean and wrong labels look alike (both hard to learn). |
| Area Under the Margin (Pleiss et al. 2020) | Margin between the gold logit and the largest other logit, averaged over training; mislabelled items have low or negative AUM. A planted "threshold class" calibrates the cut-off. | Classification with a fixed label set. | Same limitation as cartography for generated answers; the threshold-sample idea (plant known-wrong labels to calibrate) is the useful part, and it is how the dev thresholds were checked. |
| Forgetting events (Toneva et al. 2019) | Items learned then forgotten during training are hard or mislabelled. | Many epochs. | Not affordable here. |
| Small-model ensemble disagreement | Several weak models voting. | Models that are right more often than the noise rate. | SmolLM2-135M/360M are below 10% on these word problems; their votes are noise. |
| Program-aided verification (PAL, Gao et al. 2023; PoT, Chen et al. 2023) | Have the model write a program and execute it, rather than compute in text. | A sandbox or a restricted evaluator. | Strong fit for checkable answers (arithmetic, string manipulation). Implemented as a whitelisted AST evaluator: nothing the model writes is ever `exec`'d. |
| Self-consistency (Wang et al. 2023) | Agreement across samples signals correctness. | Several samples per item. | Used in the cheaper two-route form: a chain-of-thought answer and a program answer must agree. |

### What was tried (development data only)

1. **SmolLM2-360M as judge (round 2 idea): no result.** The planned run stalled at 80+ minutes with the laptop 21-31 GB into swap, holding 10 GB by itself, and it died with the session; `out/dev_judge_360M.json` was never written. It was not rerun: round 2 had measured this model's label plausibility at 0.42 on clean labels against 0.46 on 30%-noisy labels, and Qwen below separates the same data outright.
2. **Qwen2.5-1.5B-Instruct as judge, on MLX: adopted** (`touchstone/judge.py`, `out/dev_judge_qwen.json`, 24 development datasets, 60 items each, about 3.6 GB and 1.8 minutes per dataset). Each item is answered by chain-of-thought and by a program run in a whitelisted evaluator. First attempts failed for fixable reasons: the program prompt invited `len(...)` tricks and 16 of 60 answers lacked `\\boxed`. A few-shot prompt and a fallback parser took the routes from 44/60 and 15/60 to 60/60 and 54/60 on `good_short`.

   | Development data | Share of confident items that disagree with the label |
   |---|---|
   | Clean numeric (8 sets) | 0.00 on all 8 |
   | Real GSM8K (2 sets) | 0.00, 0.04 |
   | 10% wrong (below the truth line) | 0.14 |
   | 30% wrong | 0.18 |
   | 40-60% wrong (4 sets) | 0.35-0.43 |
   | 100% wrong (4 sets) | 1.00 |

   Threshold 0.15. The gap between 10% and 30% noise is the thin part, so a dataset landing between 0.08 and 0.25 gets 60 more items. On GSM8K-level problems only about 40% of items are confident, so the audit has less power there. String labels defeat chain-of-thought (it cannot reverse letters), so non-numeric labels use the program route alone, discarding programs whose literal is not in the prompt: clean 0.02-0.11, noisy 0.40-0.61, threshold 0.20.
3. **Qwen2.5-Math-1.5B-Instruct as judge: rejected** (`out/dev_judge_qwen-math.json`, same 24 sets). It ignores the program instruction and writes reasoning, so almost nothing is confident (0-3 of 60). Its chain-of-thought is no stronger than the general model on this data (GSM8K 36/60 and 42/60 against 42/60 and 48/60), and it took 33% longer. A math specialisation is no help on grade-school problems, and the general model's ability to follow instructions is what makes two routes possible.
4. **Unsupported final answer** (model-free, `screen.unsupported_final`). In a worked solution the stated final answer must be produced somewhere in the working (any number written before it, or any equation's value). Real GSM8K train solutions: 0.2% flagged (7,321 checked), and the three inspected are genuine GSM8K label errors (for example "#### 49" after computing $0.49). Development sets with a correct working but a wrong final answer: 20%, 26% and 57% flagged. Folded into the existing 10% arithmetic-consistency rule.

## 2. Public copies

| Technique | Idea | Status |
|---|---|---|
| Wider public snapshots | The baseline must contain what a vendor could resell. | Word problems now compare against GSM8K train + test, SVAMP and ASDiv (`touchstone/public_corpora.py`, about 12k problems) instead of GSM8K train only. |
| Normalised n-gram / MinHash (Broder 1997; Lee et al. 2022) | Near-duplicate text. | Already used (character 5-gram Jaccard, with a same-numbers guard). |
| Embedding similarity (Yang et al. 2023) | Paraphrases. | Already used (MiniLM cosine with the same-numbers guard). |
| Number fingerprints with chance correction (round 2) | Rewording leaves the numbers. | Used for short templated prompts. |
| Min-K% prob (Shi et al. 2024), zlib ratio (Carlini et al. 2021) | Membership inference: text the model was trained on has fewer very-unlikely tokens. | Only detects copies of data the reference model was trained on, and SmolLM2's pretraining mix is not documented item by item. Not adopted; the explicit corpora are the stronger, explainable signal. |

## 3. Forecasting

| Technique | Idea | Status |
|---|---|---|
| Cut measurement noise | Bigger eval sets, more seeds (Heineman et al. 2025, "Signal and Noise": decision accuracy is bounded by the signal-to-noise ratio of the benchmark). | Round 3 sweep: 600 items, 3 seeds at proxy and target. |
| Resolvable pairs | Score only pairs whose target gap exceeds its noise. | Pre-registered in METHOD.md before the sweep ran. |
| Checkpoint averaging | Average the proxy's score over late checkpoints to cut training noise (also DataDecide's recommendation to smooth over checkpoints). | Proxy evaluated at steps 10, 20, 30. |
| Smaller proxy learning rate (Wang et al. 2026) | Proxies trained with a lower learning rate rank data more like large models. | Round 2: helped datasets (Spearman 0.43 -> 0.89 on 8 datasets). |
| Gradient-similarity valuation (LESS, Xia et al. 2024; TracIn, Pruthi et al. 2020) | Score training data by the alignment of its gradients with the held-out set's gradients. | See section 3 results. |
| Learning-curve extrapolation (Domhan et al. 2015; Ruan et al. 2024) | Fit the proxy's curve and extend. | Two rungs only on this laptop; fitting a curve through two points is a line, which round 1 showed is worse than ranking. |

Results are filled in below as experiments finish.

## 4. Coverage by data type

Touchstone must eventually appraise every kind of training material. This matrix says what works today, what would extend it, and whether that fits on a 16 GB laptop. `touchstone/coverage.py` detects the type from row content and reports each check as `checked`, `partial` or `not_checked` in a new `checks` block of the report (additive; schema 1.0 fields are unchanged). A type no check can read reports `not_checked` with the reason; it is never shown as clean.

| Data type | Labels | Public copy | Held-out value (training) | Extension | Laptop? |
|---|---|---|---|---|---|
| Math word problems | **Checked.** Arithmetic and unsupported-final audits, judge re-solves two ways | **Checked.** GSM8K train+test, SVAMP, ASDiv | **Yes**, built-in `word_math` suite | MATH, MAWPS corpora | Yes |
| Short transforms (strings) | **Checked.** Judge's program route executes the transform | Not checked unless `--public` | Yes, built-in `strings` suite | More transforms in the evaluator | Yes |
| Multiple choice | **Checked.** Judge picks an option | Not checked unless `--public` | Only with a user suite | MMLU/ARC corpora as a baseline | Yes |
| Code with tests | **Checked.** Runs against its tests in a sandbox (no network, no home reads, no exec, limits) | Not checked unless `--public` | Only with a user suite; exact-match scoring does not fit code | MBPP/HumanEval as a baseline; held-out scoring by test pass rate | Yes for labels; scoring by tests is new work |
| Code without tests | **Partial.** Syntax only | Not checked unless `--public` | Only with a user suite | Judge writes tests, or Python-only type checks | Partly |
| Free text, instruction | **Partial.** Judge rates fit to the request, calibrated by shuffled pairs. Facts are not checked | Not checked unless `--public` | Only with a user suite; exact-match scoring does not fit prose | Retrieval-backed fact checks; held-out scoring by likelihood or a stronger judge | Fit yes; facts need a bigger judge and an index |
| Chat, conversation | **Partial.** Same fit check on the last turn only | Not checked unless `--public` | Only with a user suite | Turn-level audit; safety and persona checks | Yes for turns; rented GPU at volume |
| Tool-use trajectories | **Partial.** Call parses, tool is declared, arguments fit the schema. Choice of tool is not judged | Not checked | No held-out suite | Replay against mock tools; judge scores the choice of tool | Structure yes; replay is new work |
| Non-English | **Numeric: checked** by the judge. Text: same partial fit check | **Not checked** (baselines are English) | Only with a user suite | Multilingual baselines; multilingual embeddings instead of MiniLM | Yes, small |
| Images, audio, video | **Not checked** (the loader accepts text JSONL only) | Not checked | No | Vision or audio judge | No: rented GPU |
| RL env: math | Grader audit, leakage, training gap | Checked for `arithmetic` | Yes | | Yes |
| RL env: strings | Grader audit, leakage, training gap | Not checked unless `--public` | Yes | | Yes |
| RL env: code | Grader audit runs only if `verify` is safe in-process; vendor code is not sandboxed yet | Not checked | No suite | Run `verify` in the sandbox of `codecheck.py` | Yes, new work |
| RL env: tools, agents, browsers, games | Generic probes only (empty, echo, junk); no domain probes | Not checked | No suite | Domain probes, simulator-based held-out tasks | Mostly rented GPU |

