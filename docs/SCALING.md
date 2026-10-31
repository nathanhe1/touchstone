# Scaling Touchstone past a 16 GB laptop

What a full test across all data types costs, which parts belong on a rented GPU, and how to run them there. Nothing here has been run on a rented machine: no account was opened and no money was spent. Laptop timings are measured (`out/heavy_jobs.log`). GPU times are estimates, marked as such. Check them with the smoke test below before committing to a long rental.

## What the laptop can and can't do

Measured on an Apple Silicon Mac with 16 GB of memory, one job at a time:

| Job | Laptop time | Peak model memory | Notes |
|---|---|---|---|
| Static screens, one dataset | seconds | under 1 GB | Overlap, duplicates, arithmetic, code tests, tool checks |
| Reference judge, one dataset (60-120 items) | 2-6 minutes | 3.6 GB | Qwen2.5-1.5B on MLX |
| All flag sets, with judge (108 cases) | 2.3 hours | 3.6 GB | |
| Coverage eval, eval half (32 cases) | 35 minutes | 3.6 GB | |
| GRPO run, 135M, 30 steps, 3 evals on 600 items | 5-23 minutes, median about 10 | 2 GB | Varies with other apps' memory use |
| GRPO run, 360M | see `out/validate_rl_real2.log` | | Slower than 135M |

The sweep is the part that doesn't fit: 156 runs at those rates is at least 30 hours of continuous running, with one model at a time and a machine still in daily use. One run hung and was killed by the job guard. Anything needing 1.7B rungs for many materials also doesn't fit: round 2 could not complete 1.7B evaluation on this laptop.

## What belongs where

| Work | Laptop | Rented GPU |
|---|---|---|
| Unit tests, static screens, code sandbox | Yes | No need |
| Label audits on a few datasets | Yes | Only at volume |
| One appraisal in quick mode | Yes | No need |
| Forecast sweeps with 3+ seeds | Interim only | **Yes** |
| 1.7B rung, 7B+ targets | No | **Yes**, the only way to test forecasts at real scale |
| Stronger judges (7B+) for GSM8K-hard data, multiple choice and fact checks | No | **Yes** |
| Images, audio, video | No | **Yes** |

## Cost of a full test across data types

Estimates for one large GPU, such as a single MI300X with 192 GB of memory, running 8 parallel jobs. Laptop rates are measured. The GPU speed-up is an assumption until the smoke test confirms it.

| Experiment | Runs | GPU-hours, estimate |
|---|---|---|
| Round-3 RL sweep (26 environments, 135M and 360M, 3 seeds) | 156 | 4-8 |
| Add a 1.7B rung (26 environments, 3 seeds) | 78 | 6-12 |
| Dataset sweep (26 datasets, 3 sizes, 3 seeds) | 234 | 6-12 |
| Per-type forecast sweeps (code, multiple choice, free text, chat, tools; about 12 materials each) | 500+ | 15-30 |
| Full flag and coverage evals, stronger judge | 200 cases | 1-2 |
| 7B+ forecast target, one family of materials | 100+ | 30+ |

Rough total without the 7B+ target: **30-65 GPU-hours**; with it, about 100. Multiply by the provider's current hourly rate. Prices were not checked here.

## Running it

An MI300X uses AMD's ROCm stack, and the PyTorch ROCm build exposes it through `torch.cuda`, so `lm.py` selects it as `cuda` with no code change. MLX isn't available there, and `judge.py` falls back to `transformers`. `run_heavy.py` is for the laptop, so skip it on the GPU box. This path has not been tested on real hardware.

```bash
# 1. Set up (Python 3.9+; choose the ROCm wheel from pytorch.org that matches the driver and torch 2.8.0)
git clone <this repository> && cd touchstone
git checkout ml-appraisal-engine
python -m venv .venv && . .venv/bin/activate
pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/<rocm-build>
pip install transformers==4.56.2 peft==0.17.1 -e .

# 2. Smoke test: about 15 minutes. Check the GPU is used, and time one run at each size.
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
python -m pytest -q -m "not slow"
time python scripts/validate_rl_real2.py --one mix_honest 135M 0 | tail -1 | cut -c1-100
time python scripts/validate_rl_real2.py --one mix_honest 360M 0 | tail -1 | cut -c1-100

# 3. Sweep: copy out/validation_rl_real2.json from the laptop first, so finished runs are kept.
for i in 0 1 2 3 4 5 6 7; do
  nohup python scripts/validate_rl_real2.py --shard $i/8 > out/sweep_$i.log 2>&1 &
done
wait
python scripts/validate_rl_real2.py --merge
python scripts/report_rl_real2.py                # development environments only

# 4. Flags and coverage, on the same machine
python scripts/eval_flags.py --set all --tag _gpu
python scripts/eval_coverage.py --part dev
```

**Stop rules.** If the smoke test is slower than the laptop or the GPU isn't used, stop and fix that before renting more time. Copy `out/` off the machine often: it holds every result. Shut the machine down when jobs finish.

**Keep the honesty rules on the GPU box.** Test v3 and the held-out environments are scored once. Choose the signal on development environments first, then run `scripts/report_rl_real2.py --final <signal>`. Changing hardware changes numbers slightly, so don't mix runs from different machines in one comparison without saying so.
