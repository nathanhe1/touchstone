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

1. **SmolLM2-360M as judge (round 2 idea).** The planned run (`scratchpad/dev_judge.py 360M 48`, pid 38445) stalled: the laptop was 21-31 GB into swap and the process made no progress in 80+ minutes on a job that needs about two minutes. It could not be stopped from this session; its result, if it ever finishes, is in `out/dev_judge_360M.json`. The 360M model's GSM8K-style accuracy is single digits, so its confident errors would swamp 10-30% noise anyway (round 2 measured its label plausibility at 0.42 on clean data against 0.46 on 30%-noisy data).
2. **Qwen2.5-1.5B-Instruct as judge, on MLX** (`touchstone/judge.py`). See the results table below.
3. **Unsupported final answer** (model-free, `screen.unsupported_final`). In a worked solution the stated final answer must be produced somewhere in the working (any number written before it, or any equation's value). Real GSM8K train solutions: 0.2% flagged (7,321 checked), and the three inspected are genuine GSM8K label errors (for example "#### 49" after computing $0.49). Development sets with a correct working but a wrong final answer: 20%, 26% and 57% flagged. Folded into the existing 10% arithmetic-consistency rule.

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

