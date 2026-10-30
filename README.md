# Touchstone

An independent appraisal lab for RL environments and post-training data. Give it a dataset or an environment; it trains real open models on it at several sizes with one fixed recipe, measures how much the training carries over to a held-out suite, subtracts what a placebo would have bought, probes the grader for reward hacks, checks overlap with the held-out suite and with free public data, forecasts the gain at a larger model size with a validated error band, and writes a grade, a fair value per item and a report.

How each number is computed, what it rests on in the literature, and where it stops working: [METHOD.md](METHOD.md).

## Appraise your own data

### Install (macOS, Apple silicon; also runs on CPU or Linux)

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"     # pins torch 2.8.0, transformers 4.56.2, peft 0.17.1
.venv/bin/touchstone suites           # list the built-in held-out suites
```

Models download from Hugging Face on first use (SmolLM2 135M/360M/1.7B-Instruct, about 4.5 GB, plus a 90 MB sentence-embedding model).

### A dataset (supervised fine-tuning data)

```bash
.venv/bin/touchstone appraise my_data.jsonl --kind dataset --quick            # about 5 minutes
.venv/bin/touchstone appraise my_data.jsonl --kind dataset --out reports/my_data   # full: about 45 minutes
```

One JSON object per line, in any of these shapes (at least 20 lines):

```json
{"prompt": "A box holds 12 pens. How many pens are in 5 boxes?", "completion": "12 x 5 = 60. The answer is 60."}
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
{"question": "...", "answer": "..."}
{"instruction": "...", "input": "...", "output": "..."}
```

For `messages`, the last assistant turn is the training target and everything before it is the prompt. Bad lines are reported with file and line number, and nothing is trained until the whole file validates.

### An RL environment

```bash
.venv/bin/touchstone appraise envs/northwind_arith --kind env --quick       # 10 to 20 minutes
.venv/bin/touchstone appraise path/to/my_env.py --kind env --suite word_math
```

An environment is a folder with `env.py` (or a single `.py` file) that defines `ENV`:

```python
from touchstone.env import Task

class MyEnv:
    name = "My Environment"
    domain = "word_math"            # optional: the built-in held-out suite it should transfer to
    def tasks(self):                # the task pool; each prompt is sent to the model as the user message
        return [Task("What is 17 + 25? End with the number.", {"answer": "42"}), ...]
    def verify(self, task, output): # reward in [0, 1] for the model's reply
        return float(output.strip().endswith(task.meta["answer"]))
    # optional: def reference(self, task) -> str   (or put the answer in task.meta["answer"])

ENV = MyEnv()
```

A correct reference answer per task is optional but strongly recommended: it lets the grader audit feed `verify()` answers that are known to be wrong (near misses, hedges, same-shape wrong answers, the model's own mistakes). Without it only reference-free probes run. `examples/envs/wordmath_rl/env.py` is a template to copy.

### The held-out suite (what "transfer" is measured on)

Built in:

| Suite | Domain | Items |
|---|---|---|
| `word_math` | grade-school arithmetic word problems, one or two steps | 300 (10 private templates) |
| `arithmetic` | multi-digit addition stated in words | 300 |
| `strings` | reversing short letter strings | 300 |

Datasets default to `word_math`; environments default to their `ENV.domain`. For any other domain, bring your own suite as JSONL and pass `--suite my_suite.jsonl`:

```json
{"prompt": "How many minutes are in 7 hours?", "answer": "420", "match": "numeric"}
{"prompt": "Reverse 'abc'.", "answer": "cba", "match": "exact", "distractors": ["abc", "bca", "cab", "acb"]}
```

`match` is `numeric` (the last number in the reply must equal the answer) or `exact`. `distractors` are plausible wrong answers used for the smooth probability score; they are generated automatically if omitted. Use at least 200 items. The suite must never be shown to the vendor; Touchstone checks every appraised item against it (exact, near-duplicate and reworded matches) and flags any overlap. `examples/suites/unit_conversion.jsonl` shows the format. A custom suite has no calibration sweep, so its forecast is the rank-at-largest-size number, labelled as uncalibrated in the report (see METHOD.md to calibrate one).

Pass `--public free_data.jsonl` (or an environment folder) to check overlap against a free baseline of your choice. The defaults are GSM8K train for `word_math` and the free addition environment for `arithmetic`.

### What you get

`report.md` (readable), `report.json` (everything, machine-readable) and `run.log` in the `--out` folder:

- held-out accuracy before and after training at each model size, with 90% intervals, and the same for the shuffled-answer (or shuffled-reward) placebo; the net gain is the material minus the placebo;
- a smooth score (probability on the right answer against four plausible wrong ones);
- grader audit (environments): reward earned by each exploit, and training reward against held-out gain;
- overlap with the held-out suite, with free public data, and internal duplicates;
- forecast of the net gain at 1.7B with the range observed in validation; the grade (A to F), fair value per item, and every flag with its reason.

`--quick` screens first and stops if a blocking problem already rules out a price; otherwise it trains only the 135M rung (30 SFT steps, one seed, material + placebo) and scores 150 held-out items; for environments it runs 30 GRPO steps with groups of 4. Measured on an M5 with other work running: about 5 minutes for a dataset, 10 to 20 for an environment. The full run trains 135M and 360M (two seeds each) and 1.7B (one seed), scores 200 items, and also measures 1.7B directly. `--dollars-per-point` sets what one held-out accuracy point is worth to the buyer (default $250,000, an assumption, not a measurement).

### Devices

`--device auto` (default) trains on the Apple GPU through PyTorch MPS (or CUDA on Linux) and falls back to the CPU with a printed warning. `--device mlx` uses Apple MLX for dataset appraisals (`pip install -e ".[mlx]"`); `--device cpu` forces the CPU. Measured on this M5 (16 GB, other apps open), using the production LoRA trainer at batch 16 (`scripts/bench_devices.py`, `out/device_bench.json`):

| Size | PyTorch MPS | MLX | CPU |
|---|---|---|---|
| 135M | 1.0 s/step, 1,306 tok/s, 4.5 GB | 1.2 s/step, 1,063 tok/s, 5.0 GB | 1.9 s/step, 690 tok/s, 3.3 GB |
| 360M | 2.0-3.2 s/step, 417-663 tok/s, 5.6-7.7 GB | 1.6-16.9 s/step (swaps at full batch), 7.3 GB | 5.6-5.9 s/step, 227-236 tok/s, 4.1 GB |
| 1.7B | 5.0 s/step, 268 tok/s, 9.0 GB (micro-batches of 4) | 27.2 s/step, 48 tok/s, 6.7 GB (micro-batches of 4) | not practical (fp32 weights alone are 6.8 GB) |

PyTorch MPS is the default because it is the fastest at every size on this machine. MLX is kept as a fallback. Timings vary by about 1.5x with other load on the machine; ranges show repeated runs.

## Web API and demo

```bash
.venv/bin/touchstone serve --port 8000        # API under /api, the built website (web/dist) at /
```

The full contract (endpoints, job lifecycle, report.json schema, the website request form) is in [docs/API.md](docs/API.md). Four ready demo inputs live in `examples/demo/`: a good dataset, a contaminated one, one with wrong labels, and an RL environment with a gameable grader. `GET /api/examples` lists them and `POST /api/appraise/example/<id>` runs one. Docker and cloud notes are in [DEPLOY.md](DEPLOY.md).

## Evidence

- **Planted failures** (`out/evidence.md`, `scripts/run_evidence.py`): the six sample environments and eight example datasets, quick mode. Every planted problem gets its flag and no price.
- **Red-flag accuracy** (`out/flag_eval.md`, `scripts/eval_flags.py`): on a held-out test set of 23 new planted cases, built after the thresholds were frozen, precision is 1.00 for every flag and recall 0.84 overall. The original prototype scored 0.11 recall. The misses are explained in METHOD.md.
- **Forecast validation**: RL environments on the tiny GPTs (16 environments x 4 sizes x 3 seeds, `out/validation_rl_tiny_summary.json`): ranking by the smooth score at the largest small size picks the largest model's winner 91% of the time (Spearman 0.93). Ranking by accuracy is near chance (56%, Spearman 0.17), which is what sank the original prototype's forecast (−0.03). Datasets on the real 135M/360M/1.7B ladder: `out/validation_sft_summary.json`, summarized in METHOD.md.

```bash
python scripts/build_examples.py                  # regenerate examples/datasets/
python scripts/run_evidence.py --envs --datasets --quick
python scripts/validate_sft.py                     # dataset forecast validation + calibration (hours)
python scripts/validate_rl_tiny.py                 # RL forecast validation on the tiny GPTs (hours, CPU)
.venv/bin/python -m pytest -q tests                # unit tests + CLI smoke tests (about 10 minutes)
.venv/bin/python -m pytest -q tests -m "not slow"  # unit tests only, under a minute
```

## What's real and what's a stand-in

| Piece | Status |
|---|---|
| Models | Real open weights: SmolLM2-135M/360M/1.7B-Instruct, LoRA rank 16 on all linear layers, on Apple MPS. The buyer's frontier model is not run; 1.7B is the largest validated target. |
| Training | Real SFT (completion-only loss) and real GRPO (group-normalized advantages, KL to the base model, on-policy). Short fixed budgets: 60 SFT steps of 16 examples, 40 GRPO steps of 8 prompts x 8 samples. |
| Held-out suites | Built-in, procedurally generated with private templates and seeds; or your own JSONL. |
| Grader audit | Real: mechanical known-wrong and reference-free probes plus the model's own wrong samples. |
| Overlap | Real: exact, character 5-gram near-duplicate, and MiniLM sentence-embedding paraphrase matching with a same-numbers guard. |
| Forecast | Calibrated small-to-large map, validated by leave-one-out on a sweep of datasets run at all three sizes. For RL environments on real models there is no calibration sweep yet (too slow for a laptop); the RL forecasting method was validated on the tiny GPTs instead. |
| Vendors | The six environments and the example datasets are fictional, built to plant specific failures. |
| Sealing | `touchstone/env.py` can copy an environment into a content-addressed vault, but vendor code still runs in Touchstone's process. Production needs a sandbox. |

## The original tiny-model prototype

The first prototype (character-level GPTs, 29K to 1.3M parameters, toy GRPO on CPU) still runs and still feeds the website data in `out/appraisals.json`:

```bash
python3 scripts/run_demo.py --quick
python3 -m touchstone.site out/appraisals.json site
```

Its forecast did not validate (Spearman -0.03 between forecast and actual at the largest size, 7 environments, one seed). `scripts/validate_rl_tiny.py` re-runs that experiment with the fixes; METHOD.md reports what changed.

## Layout

- `touchstone/cli.py`: the `touchstone` command
- `touchstone/pipeline.py`: the appraisal pipeline on real models (dataset and environment)
- `touchstone/lm.py`: the model ladder, generation, scoring, LoRA SFT
- `touchstone/grpo.py`: GRPO with LoRA and the shuffled-reward placebo
- `touchstone/suites.py`: held-out suites, answer matching, distractors
- `touchstone/measure.py`: evaluation and paired bootstrap gains
- `touchstone/data.py`: dataset loading, validation and the shuffled-answer placebo
- `touchstone/overlap.py`: exact, near-duplicate and paraphrase overlap
- `touchstone/probes.py`: grader audit
- `touchstone/forecast.py`: forecasting methods, leave-one-out validation, calibration
- `touchstone/valuation.py`: flags, grade and fair value rules
- `touchstone/report_md.py`: report.md
- `touchstone/calibration/`: fitted small-to-large maps
- `touchstone/{model,pretrain,rl,heldout,redundancy,appraise}.py`: the original tiny-model prototype
- `touchstone/site.py`, `touchstone/report.py`: the static website generator
- `envs/`: the six sample vendor environments and the free baseline
- `examples/`: example datasets, an environment template and a custom suite
