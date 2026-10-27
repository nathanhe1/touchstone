# Touchstone (prototype)

An independent appraisal lab for RL environments and post-training data. A vendor's environment goes into a sealed vault. Touchstone trains models on it at several sizes with one fixed recipe, measures how much the training carries over to a private held-out suite, probes the grader for hacks, checks for duplicates of free data, and forecasts the gain at the buyer's model size. The output is a grade, a fair value per task, and a certificate.

The idea and market research are in `../research/parameters-and-scaling-startup-angles.md`.

## What's real and what's a stand-in

| Piece | In this prototype | In production |
|---|---|---|
| Environment contract | Real: `env.py` exposes `ENV` with `tasks()` and `verify()` | Same, or an adapter for OpenEnv / Prime Intellect `verifiers` |
| Sealing | Real: content-addressed copy into `vault/` with a SHA-256 fingerprint | Same, plus an isolated container with no network |
| Models | Tiny character-level GPTs (29K to 1.3M params) on CPU | Real open models, for example 0.5B / 1.5B / 3B, checked against 7B |
| Trainer | `ToyGRPO`, a real group-relative policy-gradient loop with a KL penalty to the base model and muP-style learning rates scaled by width | `TRLBackend` slot (TRL GRPOTrainer or Tinker), same interface |
| Held-out suite | 450 private items (2-digit and 3-digit addition, string reversal) | A large private suite per domain, never shared |
| Hack probes | Real: six static exploits plus a hedging probe that uses a real policy | Same idea, plus adversarial policies trained against the grader |
| Forecast | Real: fit gain against log(params), bootstrap the held-out items, check against the largest model | Same |

The six vendors are fictional and built to show different failure modes:

- **Northwind Arithmetic Pro**: an honest grader with harder 3-digit problems.
- **Mirror String Ops**: an honest grader on a different skill (reversal).
- **Clone Premium Addition**: 80% copied from the free public set.
- **QuickGrade Math Pack**: the grader only checks that the answer appears somewhere, so hedging wins.
- **ShapeOnly Numeracy**: the grader only checks the number of digits.
- **HintLeak Tutor Set**: the prompt contains the answer.

## Run it

```bash
pip install torch numpy pytest
python3 -m pytest -q tests                  # unit tests, a few seconds
python3 scripts/run_demo.py --quick         # smoke test, about 3 minutes
python3 scripts/run_demo.py                 # full demo, about 30 to 45 minutes on 4 CPU cores
python3 -m touchstone.report out/appraisals.json site/index.html
```

The report command writes a static multi-page site into `site/`: a homepage, a searchable appraisal index, a dedicated evidence certificate for each environment, forecast validation, and methodology. Open `site/index.html` to start.

## Layout

- `touchstone/env.py`: the vendor contract, sealing and loading
- `touchstone/model.py`: tiny GPT, generation, log-probs
- `touchstone/pretrain.py`: base models for each rung of the ladder
- `touchstone/rl.py`: `ToyGRPO` trainer and the production trainer slot
- `touchstone/heldout.py`: the private held-out suite
- `touchstone/probes.py`: hack probes and grader reliability
- `touchstone/redundancy.py`: overlap with free sets and with the held-out suite
- `touchstone/forecast.py`: small-to-large forecast and rank correlation
- `touchstone/appraise.py`: the pipeline and grading rules
- `touchstone/report.py`: the static multi-page appraisal site renderer
- `envs/`: sample vendor environments and the free baseline

## Next steps toward the real first experiment

1. Implement `TRLBackend` and run the same pipeline on 6 to 8 open environments with Qwen-class models at 0.5B, 1.5B, 3B and 7B.
2. Build a real held-out suite for each domain (math, code, tool use).
3. Keep or kill: if the small-to-large rank correlation stays under about 0.6, drop the forecast and keep the hack audit.
