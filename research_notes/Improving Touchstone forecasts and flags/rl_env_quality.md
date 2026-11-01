# Measuring RL environment quality and transfer value, and reducing GRPO variance

Evidence tags used throughout: [peer] accepted at a conference; [preprint] arXiv only, no review seen; [theory] proof or simulation, no LLM training; [interview] anonymous practitioners; [vendor] the source sells environments or tooling; [snippet] seen only through search results, page not opened or fetch failed; [repo] this repository's own measured results. Dates are as shown on the source.

Most striking repo finding, used below: the sweeps do not run the published default recipe. `scripts/validate_rl_real2.py` line 39 sets `Recipe(rl_steps=30, rl_group=4, eval_max_new=48)`, and `validate_rl_h3.py` reuses it. With `rl_prompts=8` and the default `rl_max_new=24` in `touchstone/lm.py`, a sweep run is 30 steps x 8 prompts x 4 samples: 240 groups, 960 rollouts, group size 4, and training replies capped at 24 tokens. `METHOD.md` lists 8 samples for the default recipe and records the 48-token evaluation limit as the flaw; the 24-token training cap and group of 4 are a stronger version of that flaw. `validate_rl_h3_17.py` reuses the same recipe, so 1.7B trains at 24 tokens even though its primary target asks for working at 200 tokens.

## Can partial credit, potential-based shaping or curriculum get signal out of small models without changing what is measured?

### Takeaway
Filtering to reachable items has better support than ordering them or adding partial credit, and it can be done without touching the held-out suite. True potential-based shaping cannot help trajectory-level GRPO at all, because it telescopes away. Any shaping or curriculum that Touchstone adds changes the thing being appraised, so it must be reported as a second number and never replace the as-delivered gain.

### Cited Findings
- Ng, Harada and Russell: an added reward of the form gamma*Phi(s') - Phi(s) is necessary and sufficient to preserve optimal policies under arbitrary dynamics, and can reduce learning time. Only secondary summaries were read, not the PDF. — [Ng et al. 1999 record](https://www.cs.utexas.edu/~shivaram/readings/b2hd-NgHR1999.html) [peer] [snippet]
- SPAE uses a training-free probe of intermediate confidence and correctness, combined into a "Step Potential", and rewards gains and penalises drops. It reports higher accuracy and shorter replies. It adds a saturation penalty, and the page does not claim PBRS invariance. Abstract only. — [SPAE, arXiv 2601.03823](https://arxiv.org/abs/2601.03823) [preprint]
- GRPO-VPS probes the conditional probability of the correct answer at segment boundaries and reports gains of up to 2.6 and 2.4 points over GRPO. Self-reported, listing only. — [GRPO-VPS, ICLR 2026](https://www.alphaxiv.org/abs/2604.20659) [peer] [snippet]
- ProbePO estimates expected terminal verifier reward from continuation rollouts at selected partial solutions and redistributes trajectory advantage, keeping the verifier. Authors report it higher in all 18 benchmark-setting cells. Listing only. — [ProbePO, NeurIPS 2026 listing](https://neurips.cc/virtual/2026/172348) [snippet]
- DAPO: punishing truncated replies "may introduce noise", since sound reasoning is penalised for length alone. Its Overlong Reward Shaping used 16,384 expected tokens plus a 4,096-token soft penalty zone. — [DAPO](https://arxiv.org/html/2503.14476v2) [preprint]
- Overlong filtering's benefit is clear at 8k and diminishes at 20k; useful for "short-to-medium reasoning tasks". — [Tricks or Traps (Lite PPO)](https://arxiv.org/html/2508.08221v2) [preprint]
- Hard samples dilute signal: Qwen2.5-Math training on Easy+Medium beat the full dataset, and hard@8 alone was worst. Table 1: full data vs hard@8 on MATH-500 72.20 vs 65.00, AMC 40.96 vs 39.76, AIME-2024 10.00 vs 3.33. Rewriting hard items into a backward-reasoning form (AugHard@8) reached AMC 43.37 and AIME 13.33. The paper also reports degenerate behaviours on overly hard items, such as answer repetition and skipped computation. — [Cheng et al. May 2026](https://arxiv.org/pdf/2605.28388) [preprint]
- In that same paper, difficulty is defined from 8 base-model rollouts: easy@k (all pass), hard@k (none pass), medium otherwise. — [Cheng et al.](https://arxiv.org/pdf/2605.28388) [preprint]
- Against curricula: across Llama3.2-1B and 3B, Qwen3-0.6B, 1.7B and 4B, and Gemma2-9B, with five strategies on synthetic arithmetic and logic benchmarks, "no robust advantage in difficulty-based sequencing over standard random sampling", under both SFT and RL. The authors note it may still change convergence speed, which they did not measure, and results are specific to controlled synthetic tasks. This is the closest size class to Touchstone. — [Mordig et al. March 2026](https://arxiv.org/pdf/2603.27226) [preprint]
- For curricula: E2H on Qwen 1.5B Hard/OOD, Countdown GRPO 18.1/9.2 vs E2H-G 41.0/19.2; Blocksworld 21.1/2.6 vs 32.9/7.3. Yet E2H-C scored 0.0/0.0 on Blocksworld, and E2H-G numbers are the best of three settings, which is selection on results. MATH gains are small (46.3 vs 48.7). — [E2H Reasoner, ICLR 2026](https://arxiv.org/html/2506.06632v3) [peer]
- RLVE's adaptive difficulty: promote when accuracy at the top level reaches 0.9, with a check after 8 x rollouts-per-problem attempts, and a sliding window of width 4. Static low ranges saturate (effective prompt ratio falls to zero); static high ranges stay well below adaptive. Requires environments with a difficulty parameter. — [RLVE, ICML 2026](https://arxiv.org/html/2511.07317v1) [peer]
- Sign advantage (+1 correct, -1 wrong regardless of group) gives gradient in all-fail groups; in those groups its expected gradient raises pass@G under on-policy, unclipped assumptions. The authors state it is not a new algorithm. — [Nie et al. May 2026](https://arxiv.org/html/2605.07689) [preprint]
- Negative feedback matters: positive-only GRPO and RAFT collapsed, especially at Qwen2.5-0.5B. Reward there was 0.1 format plus 1 correctness, on 1,800 GSM8K items. Single run per comparison as far as reported. — [Carrino et al. March 2026](https://arxiv.org/html/2603.18756v1) [preprint]
- Base-rollout gate (PBA): prompts with no verifier-positive rollout among 8 frozen-base samples get a KL anchor to the base instead of GRPO. Lost boundary prompts fell from 654 to 91, and pass@256 on Omni-MATH-Test rose from 68.3 to 73.0, on Qwen2.5-7B, 3 seeds. The paper claims it preserves coverage, not that it expands capability. — [Zhou July 2026](https://arxiv.org/html/2607.20543v1) [preprint]
- Format is not neutral here: at 1.7B about +7 of a +28.6 gain came from change in format, and random rewards alone reached +13.8 and +18.2 on two seeds of `mix_honest`. — `METHOD.md` section 6, 1.7B check [repo]

### Inferences
- **Potential-based shaping is a no-op for trajectory-level GRPO.** Touchstone's `grpo.py` assigns one scalar per reply. With gamma=1 and Phi(terminal)=0 the shaping sum telescopes to a constant, Phi(start), so shaped and unshaped returns are identical within a group and an all-zero group stays all-zero. If terminal Phi is not zero, the shaped reward differs and invariance is gone. So strict PBRS can only act through per-token or per-step advantages, the SPAE and TEMPO style, which is a change to the algorithm. This is my derivation, not found in a paper.
- A per-step potential for a small model needs P(gold answer | prefix). That is close to `smooth_final`, which scored 0.40 on fresh environments. So the most principled form of step credit has already failed in Touchstone as a forecast signal, though not as a training signal.
- Partial credit changes what is measured unless the credit is a strict prerequisite of the target skill. A format bonus is not, given the repo's format result. Acceptable forms are few: credit for a correct intermediate value the task truly requires, reported as a separate arm with a placebo.
- Curriculum evidence reconciles best as: filtering matters, ordering does not. Cheng removes unreachable items, Mordig reorders the same items, E2H does both and is reported with selection. Touchstone should test filtering (items with at least one success in 8-16 base rollouts), not ordering.
- For a buyer, filtered gain answers "what is the reachable part of this environment worth at this size". It is a different question from as-delivered gain, and both should be printed. Held-out suites stay untouched in either case.
- Sign is the most tempting fix for floor families and the riskiest for measurement. It pushes away from failures with no evidence of what is right, and needs a placebo arm before any gain is believed.

### Gaps
- No paper found that tests partial credit against as-delivered gain on a held-out suite with models under 2B.
- No held-out evidence that any shaping lifts a model that starts at 0-1% rather than 10-30%.
- Full SPAE, GRPO-VPS and ProbePO papers were not read; baselines and seed counts are unknown.

## What is known on GRPO sample size, group size, batch size, seed variance, reward normalization and reproducibility?

### Takeaway
For binary rewards the group update is exactly the group standard deviation times a contrast, so silent-group rate and gradient fidelity are closed-form functions of p and G. Touchstone's G=4, 240-group sweeps are nearly silent below about 5% success, which is enough to explain flat rewards on floor families. Literature seed reporting is poor (often 1-3 seeds or none stated), so published gains between GRPO variants below 2-3 points should not be trusted.

### Cited Findings
- GRPO original: G=64 (the HTML renders "6464"), KL 0.04, policy learning rate 1e-6, training batch size 1024, mean/std advantage normalization, one update per exploration stage. No seeds or variance reported. — [DeepSeekMath](https://arxiv.org/html/2402.03300v3) [preprint]
- DAPO: 512 prompts per rollout step, 16 responses each, clip 0.2/0.28, KL removed, AIME evaluation repeated 32 times, and over-sampling to replace zero-advantage groups. — [DAPO](https://arxiv.org/html/2503.14476v2) [preprint]
- Dr. GRPO: G=8, removes length and std normalization, finds a question-level bias toward very easy or very hard items, uses 3 independent runs for the comparison, and does not vary group size. Llama-3.2-3B averaged 6.8 (base 3.3); a math-pretrained variant reached 20.7 from 0.14, so base-model training dominates the ceiling. — [Liu et al.](https://arxiv.org/html/2503.20783v2) [preprint; venue not checked]
- Lite PPO (group mean, batch std): removing std helps on easy data and is similar on hard data. Token-level loss is better for base models, sequence-level for aligned models. Config shows a single seed 42, and text gives no seed variance. — [Tricks or Traps](https://arxiv.org/html/2508.08221v2) [preprint]
- "GRPO++" is a blog survey, not a paper, as far as I could find. — [Wolfe, GRPO++](https://cameronrwolfe.substack.com/p/grpo-tricks) [snippet]
- Identity (binary rewards, exact for any group): the per-prompt update equals sigma = sqrt(k(G-k))/G times the contrast between mean scores of correct and incorrect replies. Group size law: fidelity phi is about 1 - 1/(8Gp(1-p)), so a coin-flip prompt is faithful by G about 10 and a 5% prompt needs G about 70. On Big-Math (215,608 problems) the silent rate is 44% at G=8; standardization moves gradient mass on extreme prompts from 13.9% to 24.7%. The authors validated on a Bernoulli-logit toy (R2 0.999), not an LLM, and set aside clipping, KL and non-binary rewards. — [Bay and Yearick, June 2026](https://arxiv.org/pdf/2607.00152) [preprint] [theory]
- Silent probability is p^G + (1-p)^G. Because p varies by prompt, the real rate is higher than the rate at mean p: 0.90 vs 0.56 at G=2 on Qwen3.5-9B. A logged G=4 run had 69.25% silent groups (54.75% all-fail), from one seed. — [Nie et al.](https://arxiv.org/html/2605.07689) [preprint]
- Group 4 vs 8, same paper: base 25.5; DrGRPO G=4 28.4 (sd 1.2, 7 seeds), G=8 81.7 (sd 0.4, 7 seeds); Sign G=4 73.8 (sd 8.6, range 64.6-90.1). The G=8 runs also changed gradient accumulation and token cap, so the comparison is confounded. Sign gave nothing on Qwen3.5-2B (17.4 to 17.4), and was not better on MATH-500 at G=8 (29.3 vs 32.3). The paper's base figures also conflict (25.5 greedy GSM8K vs pass@1 81.4 at temperature 1 on 200 questions) and I could not resolve this. — [Nie et al.](https://arxiv.org/html/2605.07689) [preprint]
- Counter-view: 2-GRPO retains 97.6% of 16-GRPO performance at 12.5% of rollouts (Qwen-1.5B/MATH 33.37 vs 34.31), and the authors argue mini-batch rollout count, not group size, is the main variance lever. No seeds found in the portion read. — [Wu et al.](https://arxiv.org/html/2510.00977v3) [preprint]
- Group sizes 3, 5, 7, 9 at Qwen3-1.7B on MATH: larger groups help GRPO and TEMPO, shown only as a figure. "Seed" does not appear in the extracted text. — [TEMPO](https://arxiv.org/pdf/2509.18314) [preprint]
- A computer-use study: n=32 best but not worth the compute, n=4 slightly beat n=8 and was judged potentially unstable. — [arXiv 2511.07332](https://arxiv.org/pdf/2511.07332) [snippet]
- Pilot-Commit spends a pilot share of rollouts to estimate p per prompt, keeps prompts in an asymmetric p range, and commits the rest. It needs 1.5-1.9x fewer rollouts than GRPO at ample budgets, but only about 1.0x at 1.5B and 14B when n=16. "Seed" does not appear in the extracted text. — [Kim et al., Databricks/Cornell, May 2026](https://arxiv.org/pdf/2605.26606) [preprint]
- VCRL filters on normalized group variance and reports 41.76 to 49.43 at Qwen3-4B, with no seeds reported. — [VCRL](https://arxiv.org/html/2509.19803v1) [preprint]
- RLVE setup: 16 rollouts, batch 128, oversampling 384, clip 0.2/0.28, no KL; 350-1,500 H100 GPU hours a run; seeds not reported. — [RLVE appendix](https://arxiv.org/html/2511.07317v1) [peer]
- Runs with 3 seeds show small spread on larger models: Zhou reports 25.1 +/- 0.9 and 29.0 +/- 0.8 pass@1. — [Zhou](https://arxiv.org/html/2607.20543v1) [preprint]
- Kang et al. ran at least 4 RL runs per recipe with at least 4 checkpoints and reported the best result, which inflates and does not estimate variance. — [Quagmires](https://arxiv.org/html/2510.01624v1) [peer, ICLR 2026]
- Reproducibility: vLLM does not guarantee reproducible outputs by default, and determinism holds only on the same hardware and version. — [vLLM docs](https://docs.vllm.ai/en/v0.9.2/usage/reproducibility.html) [snippet]. I found no GitHub issue that measures GRPO seed reproducibility directly.
- General RL reporting standard: use interval estimates, performance profiles and interquartile mean when runs are few. — [Agarwal et al.](https://arxiv.org/abs/2108.13264) [peer]
- Tinker: I found no Thinking Machines report on GRPO variance. Cookbook recipes cover Math RL and Verifiers RL; one Harbor example uses group_size=4 and groups_per_batch=8. — [Tinker recipes](https://tinker-docs.thinkingmachines.ai/cookbook/recipes/) [snippet]. A hobbyist repository runs G=8. — [JustTinker](https://github.com/Guanghan/JustTinker) [snippet]
- Touchstone baseline: noise ceiling 0.81-0.84 on arithmetic, 0.68-0.69 on fresh families, 24 of 112 fresh pairs resolvable. — `METHOD.md` [repo]

### Inferences
Signal per run under the sweep recipe (960 rollouts, 240 groups, G=4) and at G=8 with the same rollouts. The silent rate uses the formula above; fidelity uses the exact binomial sum, which reproduces the paper's G about 10 and about 70 at 95%. Prompt heterogeneity makes real silent rates worse than shown. All values are my calculation.

| Success rate p | Silent G=4 | Mixed groups of 240 | Silent G=8 | Mixed groups of 120 | Fidelity G=4 | Fidelity G=8 | G for 95% | Successes in 960 |
|---|---|---|---|---|---|---|---|---|
| 0.2% | 0.992 | 2 | 0.984 | 2 | - | - | - | 2 |
| 1% | 0.961 | 9 | 0.923 | 9 | 0.17 | 0.26 | 336 | 10 |
| 2% | 0.922 | 19 | 0.851 | 18 | 0.24 | 0.36 | 169 | 19 |
| 5% | 0.815 | 44 | 0.663 | 40 | 0.37 | 0.54 | 69 | 48 |
| 10% | 0.656 | 83 | 0.430 | 68 | 0.51 | 0.70 | 36 | 96 |
| 25% | 0.320 | 163 | 0.100 | 108 | 0.71 | 0.88 | 16 | 240 |
| 50% | 0.125 | 210 | 0.008 | 119 | 0.81 | 0.93 | 11 | 480 |

- At fixed rollouts, raising G does not create more mixed groups at low p; the table shows nearly equal counts. It does give each mixed group a more faithful gradient. This fits both camps: Bay and Yearick on per-prompt fidelity, Wu et al. on total rollouts. The cheap fix for floor families is more rollouts or a reachable prompt pool, not G alone.
- The 24-token training cap is probably a bigger defect than G. Any worked reply is cut before its answer and scores 0, which depresses p toward zero and creates the reward noise DAPO describes. The word family's training reward was likely capped this way, on top of the evaluation flaw already recorded. Verify by measuring truncation at `rl_max_new` for each family.
- Touchstone uses GRPO's std normalization (`grpo.py` line 55). At k=1, G=8 it multiplies the lone winner's advantage by about 3, which favours sparse prompts and may be useful at the floor; Bay and Yearick's toy shows GRPO lifting hardest prompts where Dr. GRPO stalls. Dr. GRPO and Lite PPO favour removal or batch std on easy data. For near-floor small models the evidence points to keeping it, but no LLM study settles this.
- Touchstone's learning rate (5e-5) is above GRPO literature values (1e-6 to 2e-5). LoRA runs in Nie and Carrino used 2e-5 and 1e-5. The repo found a 10x smaller proxy rate improved forecasting on SFT datasets; the same test has not been run for GRPO. A high rate over 240 groups may also amplify seed variance, as Sign's sd of 8.6 hints. That paper suggests LoRA initialization sensitivity, unverified.
- Variance reduction with the best expected return per GPU hour, in order: (1) evaluate with k sampled replies per item at temperature 1 rather than one greedy reply, giving a per-item p that moves before greedy accuracy does, matching what GRPO optimises; papers routinely use 16-64 samples, and Mechanize says "many dozens"; (2) a variance decomposition of existing per-item, per-seed data into environment, seed and item components, which tells whether seeds or items limit the noise ceiling; (3) fixed LoRA init and shared sampling seeds across environments within a pair; (4) IRT-selected evaluation items, see the next section.
- Report interval estimates and never best-of-N. Treat variant gaps below about 3 points on 1-3 seeds as unresolved.

### Gaps
- No study sweeps group size with many seeds across models under 2B.
- No measured seed variance for SmolLM2 or any model under 500M in published GRPO work. SmolLM2 community GRPO runs report no verified accuracy gain; the base card lists 5-shot GSM8K 1.4. — [SmolLM2-135M card](https://huggingface.co/HuggingFaceTB/SmolLM2-135M) [snippet]
- Whether non-binary reward has an equivalent of the identity is open; the paper names this as future work.

## Are there environment-level predictors that need no training?

### Takeaway
Several no-training measures predict whether training signal exists: reward variance, silent rate, pass@k at the base. None has been shown on held-out data to rank environments by transfer gain. Treat them as a gate that says "measurable", not a forecast that says "valuable". The strong pass@k correlations in the literature rank models under fixed RL data, which is the wrong axis for Touchstone.

### Cited Findings
- Epoch interviewees: 0% or 100% pass rate gives no learning signal. Minimum named was about 2-3%, or one success in 64-128 rollouts. One suggested a mix near 0%, 5% and 30%, with tasks near 70% possibly discarded. Anecdotal, 18 interviewees. — [Epoch AI, Jan 2026](https://epoch.ai/gradient-updates/state-of-rl-envs) [interview]
- Effective prompt ratio, the share of prompts whose rollouts yield non-identical rewards, is RLVE's direct environment health measure. Numbers appear in figures only. — [RLVE](https://arxiv.org/html/2511.07317v1) [peer]
- Pass@64 predicted post-RL performance: Spearman 0.92-0.95 (dataset-level) and 0.94-0.98 (instance-level), against 0.69-0.78 for Pass@1; Llama3 R2 0.92 +/- 0.05. Generalization loss reached 0.90-0.94 but does not work across datasets. But this used only 6-14 models per fit, math only, and it ranks post-SFT checkpoints of a model, with RL data fixed. — [Kang et al.](https://arxiv.org/html/2510.01624v1) [peer]
- Pass@k gap is a diagnostic of reasoning diversity, not an objective; theory only, with no experiments. — [Yu, Nov 2025](https://ar5iv.labs.arxiv.org/html/2511.16231) [theory]
- Debate on capacity: Yue et al. find RL mainly compresses search, base models can match or beat RL at large k, and paths are already in the base distribution. — [Yue et al., NeurIPS 2025](https://arxiv.org/abs/2504.13837v1) [peer] [snippet]. Wen et al. dispute it and find RLVR "can extend the reasoning boundary" for math and code, with a CoT-Pass@K metric. — [Wen et al.](https://arxiv.org/abs/2506.14245) [preprint]
- Boundary prompts can lose: GRPO's Delta pass@256 on boundary prompts was -39 +/- 3, and retained entropy 19%. So a mixed prompt is not guaranteed to gain. — [Zhou](https://arxiv.org/html/2607.20543v1) [preprint]
- Entropy evidence is about collapse during training (clip-higher slows it for aligned 4B models, little benefit for base models), not pre-training prediction. — [Tricks or Traps](https://arxiv.org/html/2508.08221v2) [preprint]
- IRT, fixed response matrices: PSN-IRT, 12 models, 41,871 items. It flags items too easy for strong models (abilities above 3.0, hardest items about 1.0), and lower discrimination at extreme difficulty. Parameter stability was uneven (discrimination r 0.74-0.82 on subsets) and no confidence intervals are given. — [Lost in Benchmarks (PSN-IRT)](https://arxiv.org/html/2505.15055v3) [preprint]
- Fluid Benchmarking: 2PL calibrated on 102 pretrained models. At 100 items, variance 19.8 to 6.1 and rank distance 16.9 to 8.7, against random items. IRT scoring mainly improves validity; dynamic item selection mainly reduces variance. — [Hofmann et al.](https://arxiv.org/html/2509.11106v1) [preprint, peer status not checked]
- ATLAS reports 3-6% of items with negative discrimination, indicating annotation errors, and 90% item reduction on HellaSwag. — [ATLAS](https://arxiv.org/pdf/2511.04689v1) [snippet]
- As few as 5% of items suffice on well-built benchmarks (rho above 0.95), not on BBQ. Student project. — [Ramprasath, Stanford](https://aimslab.stanford.edu/cs321m-projects/Ramprasath2026.pdf) [snippet]
- Transfer is established only at large scale: RLVE trained on up to 256 environments and tested on 50 held-out ones, with held-out performance rising as the collection grows (1, 4, 16, 256), and +3.37 vs +0.49 on six benchmarks with 400 environments. — [RLVE](https://arxiv.org/html/2511.07317v1) [peer]
- Math tasks are easy to create but "don't transfer as well to other capabilities", per one founder, with no data. — [Epoch](https://epoch.ai/gradient-updates/state-of-rl-envs) [interview]
- Repo: `reach_clean`, the larger model's early reward combined with pool and clean, fell from 0.83 on development to 0.56 held-out; `probe_rank` 0.90 to 0.62-0.65; gradient similarity was the weakest signal on development (0.59). — `METHOD.md` round 3 [repo]

### Inferences
- Recommended no-training card, per environment and per size, at temperature 1 and the training token limit: mean p, share of prompts in p between about 3% and 70%, mean sigma at the recipe's G, silent rate with real prompt heterogeneity, pass@32, truncation rate, chance rate for multiple-choice items, and duplicate-reply rate.
- Mean sigma is the best single statistic, since it is the update magnitude by identity rather than a proxy. It is exact only for binary rewards.
- **Multiple choice breaks this gate unless corrected.** Round 4 pre-flight (`scripts/h4_preflight.py`) moves to letter answers with a 16-token limit. These have high base p and many mixed groups from pure guessing, so sigma is high with no skill signal. Use chance-corrected p, or 3PL's guessing parameter. A reply-level check that reward varies with reasoning, not with a random letter, would be needed for free-form tasks.
- Separate three claims: **signal exists** (sigma, silent rate), **reward is sound** (reference model, next section), **skill transfers** (only a held-out suite shows this). No literature measure covers the third without training.
- A pass@k rate at the small model can test the Yue view directly: if base pass@64 on suite items is about 0, the expected gain at that size is near zero, regardless of environment. This gives a size-specific floor. It does not rank environments above the floor.
- IRT on Touchstone's own ladder is weak for calibration with 3 sizes. It can use trained checkpoints as extra respondents, but those are not independent of the environments under test. A Rasch model is the most that this supports. Its first use should be finding mis-keyed items (negative discrimination), which serves the flagging product too.
- A candidate transfer proxy is agreement between the item-level gain in the environment's own hold-out prompts and in the suite after a short run. It requires training, so it is outside this question.

### Gaps
- I found no study of reward discriminability (does the reward separate good from bad replies of a strong model) as a predictor of RL gain. The closest are audits of grader soundness.
- No held-out test of pre-training response entropy as a predictor of RL gain.
- No study ranks environments by predicted gain with models under 2B.
- Whether environment-level predictors agree across a 12x size gap is unknown; repo evidence on `reach_clean` is discouraging.

## Using a stronger reference model to score the environment rather than a small learner: evidence, cost, risks?

### Takeaway
Direct evidence that a reference model forecasts RL value does not exist that I could find, and Touchstone's own larger-model reach signal failed held-out. The reference is well supported for a narrower job: proving tasks are solvable and catching broken graders. Use it as a soundness audit, not as a value signal.

### Cited Findings
- A founder: a 0% pass-rate task may be infeasible unless a second annotator blind-solved it. — [Epoch](https://epoch.ai/gradient-updates/state-of-rl-envs) [interview]
- OpenAI's audit of a 27.6% subset that models often failed found at least 59.4% had tests rejecting correct fixes; a separate 138-problem audit of tasks o3 did not consistently solve found 18.8% tested behaviour the description never specified. The page returned 403 to my fetch, so these come through search. — [OpenAI, Feb 2026](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/) [snippet]
- Strong-model audit of graders: on 49 SWE-bench Verified tasks, 28.5% had tests weak enough that a verified incorrect patch passed; 25.0% on 20 R2E-Gym tasks. Within difficulty strata, 134 frontier submissions had Pass@1 +14.14 points on hackable tasks (95% CI 11.80-16.48). Gold-sanity gating flagged 65 of 105 decisive LLM-generated tests. Single author. — [Rajan, June 2026](https://arxiv.org/pdf/2606.16062) [preprint]
- Hack-Verifiable Environments plant detectable hacks: hack rate 17.2% on average, higher for logical bugs (34.8%), and rising with task difficulty for most models. — [Roth et al., May 2026](https://arxiv.org/html/2605.20744) [preprint]
- Rule-based verifiers miss equivalent answers, and this hurts more as models strengthen; model-based verifiers are vulnerable to hacking during RL. — [Pitfalls of Verifiers, EMNLP 2026 submission page](https://arxiv.org/abs/2505.22203) [abstract only]
- Ability saturation: top models far exceed the hardest items, so strong models lose discrimination. — [PSN-IRT](https://arxiv.org/html/2505.15055v3) [preprint]
- Cross-model failure rate as empirical difficulty gave an ordering stable to dropping any model, on code benchmarks. Page content could not be read beyond the title; seen through search only. — [Research Square preprint](https://www.researchsquare.com/article/rs-10241058) [snippet]
- RLVE-class strong small models exist under 2B: ProRL-1.5B-v2, DeepScaleR-1.5B, R1-Distill-Qwen-1.5B. — [RLVE](https://arxiv.org/html/2511.07317v1) [peer]
- Qwen-Math-1.5B as Touchstone judge was rejected: it ignored instructions, was no stronger than the general model on this data, and took 33% longer. — `RESEARCH.md` [repo]
- Repo: `word_leak30` went from 0.03 to 0.29 at 360M, target +22, proxy 0, and 135M's rewards never moved. — `METHOD.md` [repo]

### Inferences
- Reference-model jobs, in order of evidence: (1) solvability: at least one correct in 16-64 tries, with zero successes flagging a broken or infeasible item; (2) grader soundness: score reference replies and intentionally corrupted versions, and estimate false-positive and false-negative rates; (3) spot audit of rewarded rollouts; (4) difficulty profile, mainly to detect a flat easy or flat impossible set. Do not use it for (5) forecast value.
- Reference runs give a cheap "reward discriminability" number: AUC of reward on correct vs wrong reference replies, with correctness from a second check. An AUC near 0.5 says the reward measures nothing. This is my proposal, untested.
- Risks: saturation (reference at 100% tells nothing), hack sensitivity (strong models find exploits that small models do not, so false alarms for a small learner, while weak models may find different ones), leakage (reference memorised public items and so solvability is inflated), and format mismatch (replies a reference writes may overrun limits small learners face). Difficulty for a 1.5B model does not rank difficulty for a 135M model, especially in strings, where tokenizer behaviour matters.
- Cost under the constraints: a local 1.5-1.7B reference is free at the margin, and 16 samples on 60 prompts per environment is about 15,000 rollouts for 16 environments. Reserve the $5 for a small hard-case audit by a frontier API model. Check pricing before running; I did not verify it.
- Choose a reference at least one size step above the target. Using the 1.7B target as a reference would contaminate the test.

### Gaps
- No published test of whether a reference model's score predicts a learner's RL gain.
- No data on the false-alarm rate of strong-model audits for small-model training.
- The cross-model difficulty preprint could not be read, so its correlation is unavailable.

## How do labs and vendors evaluate RL environments today?

### Takeaway
Public practice is craft: anti-hacking iteration, pass-rate bands, human review, repeated runs. I found no lab or vendor publishing held-out evidence that environments cause capability gain, except RLVE from academia. Most statements come from interviews or sellers.

### Cited Findings
- Epoch's FAQ, 18 interviewees across startups, neolabs and frontier labs: "Soundness matters most: high reward must mean the task was actually solved, not hacked"; reward hacking took "many many iterations"; quality at scale is "the number one bottleneck". It cites no systematic experiment. Authors state it reflects their views. — [Epoch AI](https://epoch.ai/gradient-updates/state-of-rl-envs) [interview]
- Mechanize's head of quality and CTO: choose work at the edge of model ability; a task it cannot attempt yields zero and tells you nothing; run the same task "many dozens of times" for low noise; an eval that always gives the same score is useless; LLM filtering missed unfair tasks without manual review. RL environments are bought cheaper per case than evals. No threshold or formal noise metric. — [Mechanize, June 2026](https://mechanizework.substack.com/p/how-bad-data-teaches-models-to-write) [vendor]
- Mechanize's "Cheap RL tasks will waste compute" gives $2,400 lifetime compute per task under stated assumptions (500k tokens, G=64, five reuses) and no quality metric. The argument favours its own product. — [Mechanize, Aug 2025](https://www.mechanize.work/blog/cheap-rl-tasks-will-waste-compute/) [vendor]
- Latent Space guest post by a former Gemini RL worker: heuristics include harness failure above 5% means fix the harness first, label episodes model-failure vs harness-failure, check isolation between episodes, and check that different actions yield different rewards. No measured data. — [Wright, Latent Space](https://latent.space/p/bad-envs) [practitioner, unmeasured]
- Snorkel ships gold traces, rubrics and verifiers, and uses domain and technical expert review. — [Snorkel](https://snorkel.ai/blog/snorkeling-in-rl-environments/) [vendor] [snippet]
- HUD treats a model grader as a component that needs calibration, with narrow observable rubric criteria. — [HUD on dev.to](https://dev.to/ethan_5383afd058ff/verifier-and-reward-design-for-rl-environments-8mi) [vendor] [snippet]
- Anthropic's Alignment blog describes training on 80 environments previously identified as vulnerable to reward hacking, since fixed or removed, and reports grader-pleasing behaviour. The page fetch failed, so this is search-result level only. — [Anthropic Alignment Science](https://alignment.anthropic.com/2026/reward-seeker/) [snippet]
- OpenAI stopped reporting SWE-bench Verified after finding flawed tests and contamination. — [OpenAI](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/) [snippet]
- Prime Intellect: verifiers rubrics combine weighted reward functions and zero-weight metrics; changelog lists pass@k support; `prime eval run` runs a Hub environment. I found no Hub quality score or review process, and only a star sort is visible. — [verifiers docs](https://docs.primeintellect.ai/verifiers/overview.md), [PyPI changelog](https://pypi.org/project/verifiers/0.1.15.dev164/) [vendor] [partly snippet]
- prime-rl's reverse-text example trains a 0.6B Qwen3 after SFT warm-up, at 128-token context, on one consumer GPU in minutes. I found no published gain figure. — [prime-rl README mirror](https://github.yxlr123.workers.dev/PrimeIntellect-ai/prime-rl) [vendor] [snippet]
- INTELLECT-3 results use public Hub environments for evaluation, and these are reproducible benchmarks, not evidence of environment transfer value. — [INTELLECT-3 card](https://huggingface.co/PrimeIntellect/INTELLECT-3) [vendor]
- OpenEnv positions itself as a deployment and interface layer below verifiers and harbor, and I found no quality metric in it. — [Hugging Face, June 2026](https://huggingface.co/blog/openenv-agentic-rl) [vendor]
- Chakra Labs argues labs buy tasks, not environments. The page failed to load, so this is seen through search only. — [Chakra](https://www.chakra.dev/publications/rl-environments-are-worthless) [vendor] [snippet]

### Inferences
- Soundness, pass-rate band and repeatability form the shared public standard. Touchstone already covers more of the held-out transfer question than anything public, so that remains its differentiator, and also the place with the weakest forecast.
- Interview pass-rate bands come from frontier models with long replies. They are not validated for 135M to 1.7B.

### Gaps
- No primary lab document on acceptance criteria for purchased environments.
- No public measure of environment uplift from any lab or vendor. Epoch's "demonstrated uplift" for coding is an uncited statement.
- Environments Hub evaluation docs at the URL tried returned 404, so its CI and testing may be understated here.

## SFT vs RL: when does a fine-tuning forecast tell you about RL value?

### Takeaway
An SFT forecast tells you about RL only when base, domain and data distribution match and you use held-out reasoning loss or Pass@large-k, not post-SFT accuracy. SFT and RL move models differently, so an SFT result on an environment's solutions measures absorbability, not RL value. It is still useful when reward is at zero, as a separate number.

### Cited Findings
- Post-SFT score misleads: Llama3 post-SFT vs post-RL R2 0.43; repeated data and shortest-example SFT raise scores but lower RL gains; Qwen3 stayed flat despite large SFT gains. Better proxies: Pass@64 and generalization loss. Math only, 3 base models, Qwen3 qualitative. — [Kang et al.](https://arxiv.org/html/2510.01624v1) [peer]
- "RL amplifies existing capabilities, while SFT replaces old skills with new ones", on OLMo-2 7B. KL rose sharply under SFT and more slowly under GRPO. The authors call this preliminary and flag that learning rates differ (5e-5 vs 1e-6), a confound. The paper makes no claim about SFT predicting RL. — [Rajani et al.](https://ar5iv.labs.arxiv.org/html/2507.10616) [preprint]
- SFT on golden paths without negative examples fails to learn efficient backtracking in a toy pathfinding model, while RLVR can. Theory only. — [Provable Benefits of RLVR over SFT, ICML 2026](https://proceedings.mlr.press/v306/wei26o.html) [peer] [theory]
- Distillation can add knowledge where RLVR does not. — [Yue et al.](https://arxiv.org/abs/2504.13837v1) [peer] [snippet]
- Curriculum results were the same under SFT and RL in Mordig, one case of shared behaviour. — [Mordig et al.](https://arxiv.org/pdf/2603.27226) [preprint]
- Repo: datasets at 135M to 360M reach Spearman 0.48-0.68 by accuracy; 10x smaller proxy learning rate raises 0.43 to 0.89 on 8 datasets, 0.58 to 0.68 on 13; 360M often loses from data that helps 135M, so scale dependence is real. — `METHOD.md` section 6 [repo]
- Labs do use environments for SFT on successful trajectories, though RL remains primary. — [Epoch](https://epoch.ai/gradient-updates/state-of-rl-envs) [interview]

### Inferences
- SFT on reference-model traces is the one way to get a floor-free reading on a task with no reward. Train a short SFT on traces from environment tasks, and measure the held-out suite. It answers "if this model were shown solutions, would it learn?", not "would RL teach it?". Label it that way.
- SFT is likely to overstate RL at small sizes, given Yue's distillation contrast and Rajani's replace view. Treat a positive SFT result with no reward signal as "valuable only to larger or pre-seeded models".
- Reported together, the two give a useful 2x2: RL and SFT both positive; SFT only (material is good, model cannot find it); RL only (sharpening of what exists); neither.

### Gaps
- No paper directly correlates SFT-proxy and RL gains across environments at fixed model. Kang varies models and SFT data, not environments.
- No result under 2B. Kang's smallest base is 4B, reported qualitatively.

## What can be run in about 10 GPU hours on one RTX 5090 plus a Mac, for $5?

### Takeaway
Fix sweep defects first, then spend about a tenth of the budget on a no-training card and most of the rest on two pre-registered tests: whether the card predicts measurability, and whether filtering to reachable items lifts forecast skill. Do not expect a validated value forecast from this budget.

### Cited Findings
- Timing evidence is thin: repo file timestamps show a median gap of about 2 minutes between h3 result files and about 10.6 minutes between 1.7B result files. Few files were sampled, and that metric may not be per-run. — `out/gpu3/h3`, `out/gpu3/h317` [repo]
- Prior repo plan calls for a base-accuracy gate of 10-90% at both sizes and a token limit checked against reply length for each suite. — `METHOD.md` [repo]
- The gate, group, filter and sampled-evaluation methods are drawn from [Bay and Yearick](https://arxiv.org/pdf/2607.00152), [Cheng et al.](https://arxiv.org/pdf/2605.28388), [Fluid Benchmarking](https://arxiv.org/html/2509.11106v1) and [Kang et al.](https://arxiv.org/html/2510.01624v1), as cited above.

### Inferences
All budgets are estimates and need a 10-minute timing pilot first. Everything should be pre-registered in the repo's existing style, with a stop rule. The H4 families must be new, because spent environments cannot be rescored.

| Step | Work | Est. GPU hours | Decision it informs |
|---|---|---|---|
| 0 | Repair: training token limit from per-family reply length, record truncation at training, log silent rate per step | under 0.25 | Without this, later runs repeat the flaw |
| 1 | No-training card for about 16 environments, 3 sizes plus a 1.5-1.7B reference, 60 prompts, 16 samples at temperature 1 | 1.0 | Gate environments and families; compute reference solvability and grader AUC |
| 2 | Rollout split at fixed 960 rollouts: (G=2, B=16), (G=4, B=8), (G=8, B=4), 2 environments near p of 5-25%, 5 seeds, at 360M (30 runs) | 1.0 | Choose recipe, and get the first small-model seed variance data |
| 3 | Variance decomposition from existing per-item data, plus k=16 sampled evaluation on a subset | 0.5 (mostly Mac) | Whether items or seeds cap the noise ceiling |
| 4 | Fresh forecast test on passing environments only: 10 environments x 2 seeds at 1.7B (3.5 h), plus 135M and 360M proxies at 2 seeds (1.3 h) | 4.8 | The gated forecast, scored once, with noise ceiling reported |
| 5 | Filter arm at 360M: as-delivered, reachable-prompts-only, placebo; 4 environments x 3 seeds (36 runs) | 1.2 | Whether filtering adds real signal |
| Reserve | Failures and reruns | 1.25 | |

- Pre-registrable claims: (a) silent rate at base predicts whether the target gain resolves from noise; (b) mean sigma correlates with resolved target gain within family; (c) reachable-only training beats as-delivered on the suite by more than placebo. Claim (b) is the first real test of a no-training predictor on models under 2B, and a null here is a publishable and useful result.
- Spend the $5 only on the audit in Step 1: rewarded replies from small models plus items the reference failed. Review pricing first.
- The 10 x 2 seed target is underpowered: with a 0.68 ceiling on fresh families it may again be inconclusive. If Step 3 shows items dominate, spend on sampled evaluation rather than seeds. If results stay under the ceiling rule, report inconclusive rather than dropping the rule.
- Product wording: a gated environment can be called measurable at a size. Nothing here licenses a claim of transfer value without a held-out gain.

### Gaps
- Actual rollouts per hour on the 5090 at 1.7B are not measured in the data I checked, so the budget above may be off by 2x.
- Whether multiple-choice H4 families behave like reply-based tasks under GRPO at all is unknown; short letter replies may give little to learn besides item-level associations.
