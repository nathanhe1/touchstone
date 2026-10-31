# Component audit

What each part of Touchstone actually measures, what evidence exists on data it never touched, how it can fail, and what to do with it. Verdicts are keep, fix, make advisory, or remove.

"Untouched" means test v3 (`out/flag_eval.json`, frozen before the work, scored once) or the real-data stress test (`out/stress_real.json`, 12 real unmodified sources drawn 4 times each, nothing planted). Test v3 is mostly planted cases from our own generators, so it can't show how a check behaves on real data. Intervals are 90%.

## Flags

A flag that blocks sets the price to zero, so a false flag costs a vendor real money.

| Component | What it actually measures | Evidence on untouched data | How it fails | Risk to a customer | Verdict |
|---|---|---|---|---|---|
| `noisy_labels`, numeric, judge | Whether Qwen 1.5B, answering two independent ways, agrees with the label on items where both routes agree | Test v3 recall 20/20 [0.88, 1.00] across all label types. Real clean data: 0 false flags in 20 draws, top signal 0.05 against a limit of 0.15 | Hard problems give few confident items (15-30 of 120 on GSM8K), so power falls there. Labels are sampled, so noise near 20% can land on either side | Noise in the hardest items can go unseen. Sampling can flip a borderline dataset | **Keep.** Report the confident count |
| `noisy_labels`, arithmetic and unsupported final answer | Whether stated sums are right and the answer appears in the working. Says nothing on whether the working solves the problem | 0 false flags on real GSM8K: 2.6% at worst against a 10% limit | **Bug found by the stress test:** 1 slip in 3 checked rows on Dolly read as 33%. Fixed after test v3: needs 20 checked rows and 20% of the set. The fix has no untouched measurement yet | Consistent wrong working passes this check; the judge covers it | **Keep**, fixed |
| Multiple-choice labels | Whether the judge picks the labelled option. Mostly reflects how hard the questions are for the judge | Unseen OpenBookQA falsely flagged 2 of 4 draws; clean disagreement already 0.25-0.47 against a limit of 0.37 | The threshold came from one source, so it does not travel | A clean hard quiz loses its price | **Made advisory** |
| Free-text fit | Whether the judge says a reply fits its request. Facts are not checked | Unseen No Robots falsely flagged 3 of 4 draws; three decisions sit within 2.3% of the limit | Same as multiple choice. Style and length move the score | A clean dataset loses its price; a wrong but on-topic reply passes | **Made advisory** |
| Chat fit, non-English labels | The same fit check on the last turn; the judge on non-English math | Coverage eval: 5 of 6 false positives came from these (`out/coverage_eval_eval.json`). That choice was made after seeing the eval | Clean SODA already scores below its limit; few confident items in Spanish and German | As above | **Made advisory** |
| Code labels | Whether the code passes the tests supplied, in a sandbox. Only as good as those tests | Real clean: 0 of 8 draws, all 0.0. Coverage eval: 3-4 of 4 right per source, one false positive at exactly 10% | Weak tests pass wrong code. The limit (10%) sits close to a 10% noise negative | Low. An execution result is explainable | **Keep.** Sandbox tested on macOS; the Linux route is untested |
| Tool-call structure | Whether calls parse and fit declared schemas. Says nothing on whether the right tool was used | Coverage eval 4 of 4 right. Glaive only | One source format | Passing does not mean the trajectories are good. `partial` in the report says so | **Keep** as partial |
| `copied_from_public` | Matches against four word-problem corpora (exact, near, reworded, number fingerprints) | Test v3 recall 11/11 [0.80, 1.00]. No false flags on clean cases | Only corpora we hold. Copies from elsewhere pass. A 0.56 true case sits 12% from the limit | A paid-for dataset may be free somewhere we do not index | **Keep.** Report the corpora covered. English word problems only unless `--public` |
| Fingerprint chance floor | A guard, added after clean data showed a false 5-12% public rate | Clean data at 4% or less on dev | The 5% floor was set on dev data | Under 5% copied is not discounted | **Keep** |
| `contaminated` | Overlap with the held-out suite | Test v3 recall 5/6, no false flags | Reworded pairs in short tasks evade it (`c_env_suite_pairs`, read 0.01): the fingerprint runs only against public data | **A contaminated environment can inflate its own gain and be priced** | **Fix next round:** run the fingerprint against the suite, test on a new set |
| `gameable_grader` | Whether fixed probes earn reward. Finds only what a probe can reach | Test v3 recall 9/13 = 0.69 [0.47, 0.85], no false flags. The weakest flag | Bugs needing specific inputs pass (`g_strip_nondigits`, `g_prefix_of_answer`, `g_digit_set`). A training policy may still find these | **A passing audit does not mean the grader is safe.** A gameable environment can be priced | **Fix next round:** more probes, or fuzzing, on a new test. Never present a pass as proof |
| Reward-noise correction | Removes a stochastic grader's flip rate from the audit | Test v3: the honest noisy grader was not flagged (0.06) | It uses the median probe, so it could hide a bug that pays most probes at random | Low | **Keep** |
| `answer_leakage` | The answer appears verbatim in the prompt | Test v3 3/3, wide margins | Encoded or reworded answers pass | Low | **Keep** |
| `duplicated` | Exact repeats after normalisation, against a 50% line | Test v3: 4/4 caught. All 3 false flags were our own wrong labels: those environments are 85.6% repeats | Near-duplicates are not counted | Low | **Keep** |
| `off_topic` | Nearest-neighbour MiniLM distance to the suite | Test v3 5/5, no false flags. A true case at 0.59 sits 18% from the limit | Embedding-based, so English-centred | Low | **Keep** |
| Type detection | Which checks apply, from the row content | 48 of 48 on the coverage eval, 12 of 12 on the stress sources | Mixed datasets get one type | A mixed set is partly unchecked | **Keep.** The `checks` block shows what ran |
| Label plausibility, 360M | Probability of the label against near misses | Failed on dev in round 2 (0.42 clean, 0.46 noisy) | Could not separate them | None: it was never used, but its code implied otherwise | **Removed** |
| Qwen-Math judge | The same audit with a math model | Failed on dev: 0-3 confident of 60 | Ignores the program instruction | None | **Rejected** |

## Forecast signals

**On fresh non-arithmetic environments all three frozen candidates failed: 0.40-0.45 within families, p 0.47-0.89** (`out/forecast_h3.json`). Three of those four families were at a competence floor or badly measured, including one design flaw of ours, so this is weak evidence about skill there and strong evidence that no general forecast has been shown. The table below is on the 17 spent arithmetic environments, 135M to 360M unless stated.

| Component | What it actually measures | Evidence | How it fails | Risk to a customer | Verdict |
|---|---|---|---|---|---|
| `acc_final` | Held-out accuracy gain at the small size | 0.70 all pairs [0.56, 0.82], 0.79 resolvable, Spearman 0.60, p = 0.01. Below the 0.90 and 0.85 targets. Ceiling 0.81 | Tasks the small model cannot solve give it no reward (`sub_honest`, +2 and +9) | **About 3 pairwise calls in 10 go wrong.** Ranking two honest environments is close to a coin flip when they are near each other | **Keep as a measurement. Retired as a general forecast:** failed on fresh families (0.45, p 0.47). Arithmetic-domain ranking only, marked advisory |
| `smooth_final` | Probability on the right answer at the small size | 0.68, p = 0.02 | As above | As above | **Keep as a measurement.** Failed on fresh families (0.40) |
| 360M to 1.7B | Same, one rung up | 0.86, or 0.81 without 3 near-zero environments. Development 0.67. Spent set. 1.7B's start is partly a format effect: about +7 of +28.6 in the 3 environments checked | Unconfirmed on fresh data | Promising, not proven | **Do not claim** until the fresh run lands |
| Calibrated map | Learned small-to-large map | Worse than ranking in round 2; no map ships | | | **Remove** the claim from the README |
| `hand_pool`, `hand_pool_clean`, `reach_clean`, `probe_rank`, `reward_gain`, ridge fits | Hand-built forecast terms | Development up to 0.90, held-out 0.57-0.65 | Built from 13 environments | None: never shipped | **Retired** |

## Price and grade

| Component | What it actually measures | Evidence | How it fails | Risk to a customer | Verdict |
|---|---|---|---|---|---|
| Net gain (placebo) | Accuracy gain above shuffled answers or rewards | The placebo is the check that catches format-only gains. Word problems: all-wrong answers matched correct ones. 1.7B: about +7 of +28 was format | Only the free format benefit is subtracted | Low | **Keep** |
| Grade | A to F from the headline gain and caps | **The good demo's interval spans C to A** (+7.3, [+1.7, +12.9]). No test checks that a grade predicts anything for a buyer | Cut-offs at 5, 2 and 0.5 points were set by hand. In quick mode it rests on one seed at 135M | **A buyer may read A as a fact about their model.** It is a fact about a 135M model on one suite | **Fix:** show the range (added as `fair_value_range`) |
| Fair value | Net gain x $ per point x novel share / items | **The good demo is $18 to $135 per item, a 7.4x range, shown as $76.** Dollars per point is an assumption ($5,000) | Linear in a gain that is itself uncertain; no market data | **A precise-looking number with no calibration** | **Fix:** show the range, label it an estimate. Do not use it for contracts |

### How much do price and grade rely on the forecast?

Fully. Both are direct functions of the headline gain, and nothing dampens them. With no calibration map, that headline is the gain **measured at the largest trained size**, not a prediction. Three consequences:

1. The price is a measurement at 135M or 360M multiplied by an assumed dollar rate. It says nothing proven about the buyer's model.
2. The forecast's weakness applies to ranking: about 70% on arithmetic, and chance on fresh families. Two honest environments priced 20% apart are not reliably ordered, and nothing supports comparing them across domains.
3. The report's `forecast` field carries `"target": "1.7B"` and `"source": "forecast"` even in this case, though the value was measured at 135M. Schema 1.0 fields are kept, so the `method` of `rank_largest` and the `basis` text are what disclose this. A client reading only `forecast.value` would be misled.

Recommended: present grade and price as a statement about the measured size, always with the range, and do not describe them as what the buyer will get. Flags work independently of the forecast, so they are the most trustworthy part of a report.

## Where text claims more than the evidence

These were not edited: the site is the founder's. Exact locations:

| Where | Text | Problem | Suggested direction |
|---|---|---|---|
| `touchstone/site.py:683` | "The gain you should expect at your own model size, with an uncertainty range." | **No model beyond 1.7B was tested**, and the headline is measured, not forecast | "The gain we measured on small models, with its range" |
| `touchstone/site.py:663`, `web/src/pages/Pages.tsx:34` | "We predict the gain at your model size" / "project it to yours" | Same. The method of fitting a curve and projecting it was dropped | "We rank material at small sizes and report how well that has held up" |
| `touchstone/site.py:746` | "We fit how the gain grows with model size and project it to yours" | Describes a method that does not run | As above |
| `touchstone/site.py:804` | "Small runs predict big ones." | Our result is 0.70 on arithmetic and chance on fresh families | Remove, or limit to the published pretraining result |
| `touchstone/site.py:857`, `web/src/pages/Pages.tsx:317` | "Published research shows small runs predict which data wins at scale" and "every report shows how well our forecast held up" | The research is on pretraining data, not RL environments. Reports do not show forecast outcomes | Say what was shown, and remove the per-report claim |
| `web/src/pages/Pages.tsx:310` | "The same small-to-large method, applied to how a model will behave before deployment" | Never tested | Mark it as a future direction |
| `web/src/pages/Pages.tsx:309` | "predict from cheap pilots whether it will..." | Not validated for that use | Same |
| `web/src/pages/Research.tsx:32` | "One 7B to 8B model" as the large-scale truth | No 7B result exists | Update or remove |
| `web/src/pages/Pages.tsx:191` | "Every result sharpens our forecasts" | Nothing feeds back | Future tense |

`README.md` and `METHOD.md` were corrected in this round. Any statement of precision and recall should say "on planted test cases", and any "no false flags" claim must carry the data type.
