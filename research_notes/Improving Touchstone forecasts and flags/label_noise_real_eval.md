# Label-noise detection for multiple-choice and free-text training material, and how to evaluate detectors on real data

Scope note for the report writer. Touchstone's flags are dataset-level: `touchstone/judge.py` draws 60 rows and compares one aggregate number against a limit. Almost all published work is item-level (rank rows, review the top). Figures labelled "my tally" or "my calculation" are mine, computed from the linked data or stated inputs, and are not published results. Repo state read on 2026-10-31: `audit_mcq2` (two-route agreement) and `audit_pair` (own reply vs a same-source reply) exist as candidates; `out/dev_travel.json` holds only one result so far (ARC draw 0: 43 confident of 100, 3 disagree, 7.0%), so neither candidate has a measurement yet. Test v4 is frozen in `METHOD.md` and should not be touched by anything here.

## Which methods have measured results on real-world noise?

### Takeaway
Real-noise evidence exists for four families: loss ranking with a fine-tuned pretrained model, strong-LLM disagreement, item-response statistics across large model panels, and confident learning on simple models. None of the strong results used a single judge under 2B parameters. AUM, Shapley methods and CROWDLAB have little or no real-noise evidence on text, and I could not find any method called "Encourage".

### Cited Findings

Real-noise results, text and multiple choice:

| Method | Data, noise type | Result | Held-out? | Validation | Fits the constraints? |
|---|---|---|---|---|---|
| Fine-tuned pretrained model, rank by out-of-sample loss, ensemble of 3 (FME, DeBERTa-v3-base) | IMDB, Amazon, Recon; organic errors | AUPR 0.60 / 0.40 / 0.38, against confident learning 0.24 / 0.31 / 0.25 | Out-of-sample loss; audit pool was flagged items | MTurk 5 judgments per item, 50 expert checks per dataset | Probably; needs fine-tuning per dataset |
| Same | TweetNLP-5, SNLI-5; human-originated noise built from dissenting crowd labels | AUPR 0.68 / 0.61, against CL 0.30 / 0.17 | Same | Crowd labels | Same |
| LLM ensemble, flag confident disagreement | 4 TRUE datasets, 160 sampled each | Over two-thirds of disagreements above 95% confidence were human errors | No threshold fit, but no held-out split reported for the confidence bins | 2 authors, blind to both labels | No, used GPT-4, PaLM2 class models |
| Frontier LLMs with retrieval | MMLU, random 100 per subject | Best F2 41.92, recall 82.61, F1 28.72; authors call automatic detection unreliable | Yes in effect: random sample, expert labels | 14 experts | No |
| 4PL IRT forced-ceiling likelihood ratio | 20,986 items, 7 benchmarks, 114 models | P@100 98%, P@200 95%, AP 0.843 on strict mislabels; 874 flags, 81% mislabeled or subjective against 3% of unflagged | Partly: 2,864 items fit separately | GPT-5.4 weak labels, not humans; top flags human-checked | Needs a panel |
| Tetrachoric / measurement-theory flags | 9 benchmarks, 40-91 models | Up to 84% precision@50 | Expert review of top 50 | Experts per domain | Needs a panel |
| Confident learning, TF-IDF or FastText | 20news, IMDB, Amazon | Flag precision 88%, 55%, 73% (my arithmetic from counts below) | Cross-validated probabilities | MTurk | Yes |
| Training dynamics (DataMaps mean) | VariErr NLI, real MNLI errors | AP 22.8 against random 14.7; GPT-4 31.3; humans up to 46.5 | Ranking, 3 seeds | Human validity judgments | Yes, but weak |

Sources and detail:
- FME beat earlier methods by 9-36 points of absolute AUPR, and CL applied on top of FME changed little. Loss had a strong log-linear relationship with error-detection precision (r² 0.94) — [Chong, Hong, Manning 2022](https://arxiv.org/html/2205.12702v3).
- Label-error rates in TRUE sampled sets were MNBM 16.9%, BEGIN 21.2%, VitaminC 8.1%, PAWS 6.2%, with lower bounds of 11.6, 15.8, 4.4 and 3.0 for the whole dataset. LLM disagreement was 17.5-39.4%. Expert Fleiss κ was 0.486 before reconciliation and 0.851 after; MTurk κ was 0.074 — [Nahum et al., EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1360.pdf).
- MMLU audit used BM25 retrieval over Wikipedia or MS MARCO, and reports recall, F1, F2, not precision — [Gema et al. v3](https://arxiv.org/html/2406.04127v3). My back-calculation from those averages gives precision of about 14-17% for frontier models with retrieval. The three averages do not fit one operating point exactly, so treat this as a range.
- IRT panel size matters: P@100 stayed at 97% with 57 models and fell to 71% with 7. A plain 2PL low-discrimination ranking reached AP 0.642 — [Land 2026](https://arxiv.org/html/2605.30504v2).
- Precision@50 rises with number of LLMs, number of creator organisations, model size cutoff and release date. No single signal found all invalid GSM8K items. A frontier LLM reviewing 100 GSM8K items reached 98% precision, but 93.3% of those invalid items were grading problems rather than wrong keys — [Truong et al., NeurIPS 2025](https://arxiv.org/pdf/2511.16842).
- A model-consensus flag (at least 50% of models pick the same non-gold answer) on cybersecurity benchmarks: of 998 checked by a search-grounded verifier, 238 confirmed mislabels (23.8%), 653 false positives (65.4%), 16 both wrong, 91 uncertain — [Berriche et al. 2026](https://arxiv.org/pdf/2609.08765).
- A wrong key looks like a hard question. On 14,042 MMLU items and 1,000 open models, items flagged in the expert re-annotation were much harder (mean b +1.86 against -0.10, t = 12.08). Difficulty also moves with the panel: early and recent cohorts correlated at r = 0.832, and Mantel-Haenszel DIF classed 30.2-44.9% of items as B or C by model family — [Paquin & Jain 2026](https://arxiv.org/pdf/2609.09372).
- SciFact audit found 11 gold errors in 209 dev pairs (5.3%, CI 2.7-9.2) and 13 in 564 train pairs (2.3%, CI 1.2-3.9), using small-model screening at $0.11 plus manual checks against sources. Screening precision is not reported — [Sylvestre, BioNLP 2026](https://aclanthology.org/2026.bionlp-1.9/).

Methods with thin or no real-noise text evidence:
- **AUM:** on SST-2 with synthetic flips it filtered about 60-65% of noise and also removed many correct examples; the authors state lower efficacy on text than images — [Talukdar et al. 2021](https://arxiv.org/pdf/2109.09191). I found no AUM precision on real text errors. Training-dynamics relatives did reasonably on token and classification tasks: DataMaps was "on par or better" than cross-validated model-based methods — [Klie et al.](https://arxiv.org/abs/2206.02280).
- **Confident learning, conflicting results:** consistently worst of the methods on synthetic noise in [AQuA](https://arxiv.org/pdf/2306.09467); among those that "work well" in [Klie et al.](https://arxiv.org/abs/2206.02280); well behind FME on real text in [Chong et al.](https://arxiv.org/html/2205.12702v3).
- **Klie benchmark:** 18 methods on 9 English datasets. Random-noise datasets reach AP above 0.9 on ATIS; real-error PLANK reaches F1 about 0.5, AP about 0.4. Best overall: Borda count, diverse ensemble, label aggregation, retag. Inconsistencies are harder than plain errors. Calibration "can help... but it is very task and dataset specific" — [Klie et al.](https://arxiv.org/abs/2206.02280).
- **Shapley family:** OpenDataVal uses synthetic noise via `add_noise`, includes text only as DistilBERT embeddings of BBC and IMDB, and finds Data-OOB strongest — [OpenDataVal](https://arxiv.org/pdf/2306.10577). Beta Shapley tested real errors on CIFAR-100 images only — [Kwon & Zou](https://arxiv.org/pdf/2110.14049). I found no Shapley result on real text errors.
- **CROWDLAB:** evaluated on CIFAR-10H with real human annotators, reported as better than Dawid-Skene and GLAD. All data is image — [Goh et al.](https://arxiv.org/html/2210.06812v2). The tables did not render, so I have no numbers.
- **Separating error from legitimate disagreement:** on 500 MNLI items, AED methods underperformed GPT models and humans. GPT-4 AP 31.3, P@100 46.0; best human heuristic AP 46.5, P@100 47.0 — [VariErr NLI](https://arxiv.org/pdf/2403.01931).
- **AQuA:** 17 datasets and 4 detectors, but rankings are on injected noise; the authors did not tune hyperparameters — [AQuA](https://arxiv.org/pdf/2306.09467).

My tally from the [Fantastic Bugs expert reviews](https://huggingface.co/datasets/stair-lab/fantastic-bugs), by first word of each review:

| Split | Rows | Reviewed as flawed | Note |
|---|---|---|---|
| OpenBookQA | 50 | 2 (4%) | Top-50 of 500 by anomaly score. "Correct" for the other 48 |
| MedQA | 49 | 23 (47%) | |
| ThaiExam | 50 | 26 (52%) | Includes cultural and ambiguity notes |
| AIR-Bench | 50 | 9 (18%) | |
| MMLU Clinical Knowledge | 50 | 6 (12%) | |
| MMLU Professional Medicine | 57 | 6 (10.5%) | |
| GSM8K, MMLU math, MMLU 5-subject | 16, 8, 74 | All listed rows flawed | Only flawed rows seem to be published, so these are not precision figures |

I could not map the paper's 84% to a split from the rows; it comes from a figure.

The two flawed OpenBookQA rows: "all cells use cellular respiration to" (key "release waste", reviewer "Release energy") and "Cold-blooded animals are often" (key "hairless", reviewer "Slow").

### Inferences
- OpenBookQA is close to clean. With 91 models behind the anomaly score, 48 of the 50 most suspicious of 500 items were still judged correct. Touchstone's 0.25-0.47 disagreement there is judge weakness, which confirms the audit's "false flag" verdict with outside evidence.
- Evidence ranks like this for Touchstone: (1) panel IRT if a panel is affordable, (2) confident-disagreement ranking, (3) out-of-sample loss with a small fine-tuned model. A single Qwen2.5-1.5B is below every setup in the table, so published precision should not be quoted for it.
- Confident learning's per-class thresholds are the simplest real-data baseline to add, and it is cheap. Its measured precision on text is usefully above base rate but below loss ranking.

### Gaps
- "Encourage": one search found no such method. The name may be misremembered. If the source can be named, it should be rechecked.
- No published run of a detector built on one sub-2B judge against real MCQ errors. All judge evidence is frontier or a large panel.
- AUM on real text errors, and any Shapley method on real text errors: not found.
- Fantastic Bugs' per-benchmark precision is only in a figure. CROWDLAB numbers did not render.

## How can thresholds be made portable across sources?

### Takeaway
No published method makes an absolute cutoff travel. What works in the literature is to rank within a source, use a statistic with a built-in zero point, or calibrate on the same source with a small clean or human-checked sample. A label-shuffle baseline fixes only the chance end of the scale, and the No Robots run shows this directly.

### Cited Findings
- **Per-class self-calibration:** cleanlab's threshold for class j is "the model-predicted probability of this class averaged amongst all examples labeled as class j", so it is computed on the data under audit — [cleanlab docs](https://docs.cleanlab.ai/stable/cleanlab/count.html). This handles per-class confidence shift, and assumes class-conditional noise — [Northcutt et al.](https://arxiv.org/abs/1911.00068).
- **Built-in zero:** Land flags when a forced-zero-ceiling model fits better than the unrestricted one, Δℓ above 0, with no tuned cutoff, and needs only an item-by-model correctness matrix. Applied unchanged across 7 benchmarks and 32 subsets. It is a review queue, not a relabeling rule — [Land 2026](https://arxiv.org/html/2605.30504v2).
- **Rank-then-review:** CROWDLAB ranks by quality score and evaluates with Lift@T rather than a cutoff — [Goh et al.](https://arxiv.org/html/2210.06812v2). Truong et al. use Gaussian rank at -0.5 and note that such cutoffs in the psychometric literature are arbitrary — [Truong et al.](https://arxiv.org/pdf/2511.16842).
- **Conformal p-values:** they are marginally valid, positively dependent, and allow exact FDR control under Benjamini-Hochberg in a relatively weak marginal sense; a calibration-conditional version is stronger — [Bates et al. 2023](https://projecteuclid.org/journals/annals-of-statistics/volume-51/issue-1/Testing-for-outliers-with-conformal-p-values/10.1214/22-AOS2244.full).
- **Conformal with a dirty reference:** contamination in the calibration set makes tests conservative, losing power rather than validity. Naive trimming broke validity (type-I 0.017-0.036 at α 0.01). Label-Trim annotated the 50 top-scoring calibration points and kept type-I at about 0.008-0.01 with relative power 1.17-1.79. A small clean set alone had zero power at that α. Data was tabular and image, not text, and i.i.d. inliers are assumed — [Bashari et al., ICML 2025](https://arxiv.org/html/2502.04807v2).
- **Conformal applied to labels:** inductive conformal cleaning with a small curated calibration set exists for biomedical data — [PLOS Comp Biol](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1012803). Conformal-in-the-Loop reports difficulty separating mislabeled from hard examples above about 10% noise — [arXiv 2411.02281](https://arxiv.org/html/2411.02281). Conformal Labeling controls FDR with a small labeled calibration set, but for selecting AI labels rather than auditing human ones — [arXiv 2510.14581](https://www.arxiv.org/abs/2510.14581). I found no benchmark of conformal mislabel detection on real text noise.
- **Permutation baselines:** Ojala & Garriga's label-shuffle test asks whether a classifier found any real class structure — [JMLR 2010](https://www.jmlr.org/papers/v11/ojala10a.html). I found no paper using shuffled-label nulls to detect partial label noise.
- **IRT-style difficulty correction:** IRT separates item and model parameters, but it needs many respondents (see panel results above). Difficulty is not invariant across model families (r = 0.832 between cohorts) — [Paquin & Jain 2026](https://arxiv.org/pdf/2609.09372). A 4PL upper asymptote is what separates "hard" from "key wrong": strong models rarely pick the key — [Land 2026](https://arxiv.org/html/2605.30504v2).
- **Confidence-gated disagreement:** higher LLM confidence in a different label gives higher precision, with the trend replicated on SummEval — [Nahum et al.](https://aclanthology.org/2025.emnlp-main.1360.pdf). Bigger ensembles improved error-detection F1 from about 0.40 to 0.55 on TRUE, and 0.61 to 0.67 on SummEval, read from the figure axes — same source.
- **Touchstone's own runs (`out/stress_real.json`):** OpenBookQA disagreement was 0.25, 0.3833, 0.4667, 0.25 on 60 rows. No Robots had `yes_shuffled` 0.0 in all four draws, so `fit` equals `yes_real` (0.53-0.58).

### Inferences
- The shuffled baseline did nothing on No Robots: the judge said NO to every shuffled pair, so the rescale divided by 1. Chance was never the problem. The missing number is what a clean dataset scores on this source, and permuting labels cannot supply it, because a permutation only tells you what total noise looks like. For MCQ the same holds: shuffled keys give about 1 - 1/k regardless of question difficulty.
- OpenBookQA's limit (0.37) sits inside sampling noise. Mean of the four draws is 0.34; binomial SE at n=60 is about 0.06 (my calculation). A limit within one SE of the source's own mean would fire on roughly a third of draws from noise alone, which is close to the observed 2 of 4.
- Why numeric checks worked: the judge's clean disagreement on numbers is near zero, so any planted or real error stands out. The cure for MCQ is a statistic with a low clean rate, not a better limit. My calculation for 80% power at one-sided 5%, assuming a wrong-key item raises the statistic by the listed amount:

| Statistic | Clean rate | Lift per wrong key | Prevalence | Rows needed |
|---|---|---|---|---|
| Raw disagreement | 0.33 | 0.42 | 6.5% (MMLU-like) | ~1,860 |
| Raw disagreement | 0.33 | 0.42 | 30% (planted) | ~25 |
| Confident disagreement | 0.03 | 0.6 | 6.5% | ~190 of the confident subset |
| Confident disagreement | 0.02 | 0.6 | 6.5% | ~130 of the confident subset |

  Lifts and clean rates are assumptions, and the subset figures are confident rows. At a confident rate like ARC's 43%, 190 confident rows would need about 440 sampled rows. These numbers explain why the current check passed a 30% planted test and cannot find real-world rates.
- Ordered recommendation, each step a dev hypothesis to test, not a result:
  1. **Excess-over-expected for MCQ.** Use the judge's calibrated probability for its pick, and test observed disagreement against the sum of (1 - p) over the rows (Poisson-binomial). The expected value needs no labels, so difficulty is handled row by row. This assumes calibration travels, which [Klie et al.](https://arxiv.org/abs/2206.02280) warn is dataset-specific, so it should be fitted across several clean sources and tested leave-one-source-out. `audit_mcq2` is a cruder version of the same idea and is worth finishing first.
  2. **Forced-choice for free text.** `audit_pair` has a meaningful scale: 0.5 means replies are interchangeable, near 0 means replies belong to their requests. This is closer to a built-in zero than the current `fit` score.
  3. **Small model panel for MCQ.** 3-5 models under 2B on a Mac gives a route to a cheap correctness matrix. Land's 71% at 7 models is an upper reference and came from a panel with strong models, so a weak panel should be expected to do worse. Treat this as an experiment.
  4. **Same-source clean reference when one exists.** If a buyer or seller will label about 50 rows, Label-Trim style checking is the best-grounded calibration route. Fifty labels is the size at which Bashari et al. started to have power.
- Conformal does not solve portability on its own. It moves the assumption from "cutoff travels" to "calibration source is exchangeable with the new source", which is false across sources. Calibrating on a source's own rows finds outliers within it, but cannot detect uniform contamination. Its conservatism under contamination does suit a product where a false flag blocks a price.

### Gaps
- No study found that measures whether any threshold holds across sources on real label noise under leave-one-source-out.
- No published test of a Poisson-binomial excess test for label noise. The idea is mine and is unvalidated.
- No published data on model panels restricted to under 2B parameters. Truong et al. show precision rises with size cutoff, but the values are in a figure.

## For free text with no ground truth, what can be checked reliably at all?

### Takeaway
A sub-2B judge can check pairing and fit, format, internal arithmetic, and constraints that can be verified mechanically. It cannot check facts or rank quality reliably, and even frontier models miss most real errors in some tasks. Judge scores are dominated by style, so free-text fit should stay advisory unless it is rebuilt around paired comparison.

### Cited Findings
- **Real LLM-response errors are hard to detect.** On ReaLMistake (900 expert-annotated responses), LLM detectors often scored below a random baseline on F1. The two strongest columns on GPT-4 responses had F1 12.7 and 20.8 on fact verification and 20.0 and 22.1 on answerability, against random about 62 and human expert 95.5 and 90.5. Precision was high (79.9-100) and recall very low (6.8-12.6). Weaker models flipped this, with higher recall and precision near base rate. Self-consistency gave no improvement. Human figures rest on 35 cases per setting — [Kamoi et al., COLM 2024](https://arxiv.org/pdf/2404.03602).
- **Detection varied by task** on the same detectors, from reasonable on math generation to poor on fact verification — [Kamoi et al.](https://arxiv.org/pdf/2404.03602).
- **Style beats substance.** With a gpt-4o-mini judge, rewriting strong responses to add one factual error lost 13% of score; making them concise lost 63%; sarcastic lost 96%. Style and completeness were the strongest predictors, correctness and safety weaker, conciseness anti-correlated. Preference benchmarks disagreed with static ones (for example LiveBench against Arena-Hard r = 0.51) — [Feuer et al., ICLR 2025](https://arxiv.org/html/2409.15268v2).
- **Length control.** A GLM predicting judge preference from length difference and other features, evaluated at zero length difference, raised Spearman correlation with Chatbot Arena from 0.94 to 0.98. Tested on AlpacaEval with one judge prompt and simple English instructions — [Dubois et al. 2024](https://arxiv.org/abs/2404.04475).
- **Entailment with a source passage.** On 11 standardized datasets, large-scale NLI and question-generation approaches gave strong, complementary results for factual consistency at the example level — [Honovich et al., TRUE](https://arxiv.org/abs/2204.04991v2). The labels themselves have 6-21% errors in sampled TRUE sets, so reported metrics are understated, with LLM performance up to 15% higher after correction — [Nahum et al.](https://aclanthology.org/2025.emnlp-main.1360.pdf).
- **Stronger-model ranking has failure modes too.** IRT flags on preference benchmarks include chosen responses that are correct but a smoother rejected one wins the vote, and labels inherited from synthetic generation — [Land 2026](https://arxiv.org/html/2605.30504v2).
- **IFD ratio.** Instruction-following difficulty compares answer perplexity with and without the instruction — [Li et al. 2023](https://arxiv.org/pdf/2308.12032). GPT-2 sized filters showed consistent difficulty perception, about 20 times faster — [Superfiltering](https://arxiv.org/pdf/2402.00530). These are measured on downstream training gain. A 2026 comparison finds both a little better than random in several settings — [arXiv 2604.10448](https://arxiv.org/pdf/2604.10448). I found no error-detection precision for them, and high IFD means hard, not wrong.
- **Touchstone's stated limit** is that fit is checked and facts are not, and the audit records a wrong but on-topic reply passing — `docs/AUDIT.md`.

### Inferences

| Check | Reliability for Touchstone | Basis |
|---|---|---|
| Duplicates, empty or truncated replies, format, language | High | Deterministic |
| Arithmetic inside replies | High | Already implemented, deterministic |
| Mechanically verifiable instructions (word limits, JSON valid) | High where present | Deterministic, narrow coverage |
| Reply belongs to this request (own vs foreign forced choice) | Likely good, unmeasured | Design controls style and length at source level; `audit_pair` |
| Faithful to a supplied passage | Moderate | NLI literature uses bigger models |
| Length-corrected judge score | Moderate at best | Dubois method fits a rating-pair setting, not yes/no fit |
| Factual accuracy with no source | Low; do not claim | ReaLMistake, Feuer |
| Overall quality ranking by a small judge | Low; do not claim | Feuer, Land |

- `audit_pair` matches style in distribution, not pair by pair: a short reply against a long one will still carry length bias. Regress `share_foreign` on the length gap as Dubois does, or sample foreign replies from a similar length band. Near-duplicate requests also need excluding, because a foreign reply can be a valid reply.
- No Robots yes rates of 0.53-0.58 mean the judge rejects about 45% of human-written replies. That is a judge problem and supports dropping absolute YES rates altogether.
- Free text should report what was checked and never imply quality. This matches the product's existing "partial" status, and the tone can stay plain: fit is checked, facts are not.

### Gaps
- No precision or recall for a sub-2B judge on ReaLMistake-style data. The smallest tested were 7B models, so this could be run directly if the terms allow.
- No study of forced-choice own-vs-foreign detection on real instruction data.
- Whether length correction holds for yes/no fit judgments is untested.

## Which real benchmarks with known noise can Touchstone download?

### Takeaway
Best buys are MMLU-Redux 2.0 (random-sample expert audit, CC-BY-4.0), the Fantastic Bugs reviews (MIT, includes OpenBookQA), Writer's IRT items, GSM8K-Platinum, and ReaLMistake for free text. Many others in the brief have disagreement data or no audit at all, and I did not find audits of SQuAD or ANLI. Licenses and sizes below were checked on Hugging Face or GitHub on 2026-10-31.

### Cited Findings

Multiple choice and short answer:

| Source | Size | License | Known problems | How validated | Use |
|---|---|---|---|---|---|
| [MMLU-Redux 2.0](https://huggingface.co/datasets/edinburgh-dawg/mmlu-redux-2.0) | 5,700 rows, 57 subjects, 1.65 MB parquet | CC-BY-4.0 | Est. 6.49% errors: wrong key 1.42, multiple correct 1.54, no correct 0.62, bad question 2.47, bad options 0.44. Virology 57%; some subjects 0 of 100 | 14 experts, random 100 per subject | **Primary.** Only source here with both unbiased positives and negatives |
| [Fantastic Bugs](https://huggingface.co/datasets/stair-lab/fantastic-bugs) | 404 reviewed rows; raw 40.8 GB; matrices GSM8K 90×997, MMLU math 79×271, MedQA 91×998 | MIT | See tally above | Domain experts; OpenBookQA checked against public sources | Valid rows are hard-but-right negatives; matrices allow IRT tests with no inference |
| [Writer/IRT-mislabeled-items](https://huggingface.co/datasets/Writer/IRT-mislabeled-items) | 1,001 rows, 3.32 MB | ODC-BY; items keep source licenses | Flagged items, including RewardBench, GPQA, MATH, GSM | GPT-5.4 weak label plus human-checked top flags | Second-tier positives |
| [GSM8K-Platinum](https://huggingface.co/datasets/madrylab/gsm8k-platinum) | 1,209 of 1,319 test rows; `cleaning_status` field | Repo tag MIT; card says added annotations CC BY-SA 4.0 | 110 removed, 10 relabeled, 99 confirmed; the rest "consensus" | Hand check of every item any frontier model missed | Numeric positives, but the removed 110 are not in this repo. Get them by diff against GSM8K |
| [gsm8k-fix](https://huggingface.co/datasets/hkust-nlp/gsm8k-fix) | 1K-10K | MIT | Errors found via low pass rates | Community, "hopefully" exhaustive | Cross-check only |
| [MedQA](https://huggingface.co/datasets/GBaker/MedQA-USMLE-4-options) | 10K-100K; 1,273 test | CC-BY-4.0 | 23 of 49 flagged reviewed invalid (my tally). 41% of o1's initial errors traced to benchmark problems such as missing figures, per snippet | Physicians; JMIR audit against source platforms | Real hard-domain positives. Note 41% is a share of one model's errors. [JMIR 2026](https://www.jmir.org/2026/1/e90061) |
| [TruthfulQA](https://huggingface.co/datasets/truthfulqa/truthful_qa) | 1K-10K | Apache-2.0 | No full audit. Validator differed on 7% of questions, 3-4% estimated as real disagreement | Authors | Light use. [Lin et al.](https://arxiv.org/pdf/2109.07958) |
| [SciFact audit](https://aclanthology.org/2026.bionlp-1.9/) | 773 audited pairs | Not verified | 24 errors total | Manual check against publications | Release has corrected labels and a blind packet; no link on the page |

Free text and classification:

| Source | Size | License | Known problems | How validated | Use |
|---|---|---|---|---|---|
| [ReaLMistake](https://huggingface.co/datasets/ryokamoi/realmistake) | 900 | CC-BY-SA-4.0; gated, authors ask that examples not be published | Error rates in Table 2 about 44-81% by task | Experts | **Primary for free text.** Keep rows out of public reports |
| [AlpacaDataCleaned](https://github.com/gururise/AlpacaDataCleaned) | ~52k | Repo Apache-2.0; mirrors disagree, HF tag CC-BY-4.0, one summary says CC BY NC | Hallucinations, merged instructions, empty outputs, wrong answers; about 80% of math estimated wrong, per project | Curated by hand, unscored | Before-vs-after diff gives real bad rows; mixed quality. [HF mirror](https://huggingface.co/datasets/yahma/alpaca-cleaned) |
| [FindTheFlaws](https://github.com/modulo-research/findtheflaws) | Not confirmed; 5 datasets | Repo CC0-1.0 | Expert-annotated long-form solutions, correct or flawed | Experts | Good fit for worked reasoning; size needs checking. [Paper](https://arxiv.org/abs/2503.22989) |
| [VariErr NLI](https://github.com/mainlp/VariErr-NLI) | 500 MNLI items | No license on repo | Errors separated from variation | 7,732 validity judgments | Error-vs-ambiguity negatives |
| TRUE corrected subset | 640 evaluated | Not verified | 6-21% errors | 2 authors, blind | [Nahum et al.](https://aclanthology.org/2025.emnlp-main.1360.pdf); I found no data link in the text |
| [AlleNoise](https://github.com/allegro/AlleNoise) | 502,310 titles, 5,692 categories | MIT repo | 15% (74,094) real seller mistakes | Experts set true category for mislabeled rows; other 428,216 assumed clean | Large real noise, but negatives are assumed. [Paper](https://arxiv.org/html/2407.10992v2) |
| [cleanlab/label-errors](https://github.com/cleanlab/label-errors) | 20news 7,532; IMDB 25,000; Amazon 9,996,437 | Apache-2.0 repo; source data has own terms | Validated errors 82, 725, 732 of 1,000 checked | MTurk, flagged rows only | Text classification positives. Not training material for instruction tuning. [Paper](https://arxiv.org/pdf/2103.14749) |
| [lnlfm](https://github.com/dcx/lnlfm) | IMDB, Amazon eval sets; 22 MB repo | No license on repo | Verified flags | MTurk, tightened protocol | Evaluation data for loss ranking |
| [HateXplain](https://huggingface.co/datasets/Hate-speech-CNERG/hatexplain) | 20,148 posts | CC-BY-4.0 on HF; [MIT repo](https://github.com/punyajoy/HateXplain) | Disagreement, not verified error. α 0.46, per preprint; 13,761 unanimous | 3 annotators | Variation signal only. [Preprint](https://www.preprints.org/manuscript/202511.1748) |
| [FEVER](https://huggingface.co/datasets/fever/fever) | 100K-1M | CC-BY-SA-3.0 and GPL-3.0 tags | Partial: 3 of 618 sampled mislabeled SUPPORTED/REFUTED, 87 NEI to relabel | Volunteers, partial results | Weak. [Shared task](https://arxiv.org/pdf/1811.10971) |
| [WRENCH](https://github.com/JieyuZ2/wrench) | 22 datasets | Apache-2.0 code | Labeling functions with errors, plus gold labels | Not human-audited for this purpose in what I read | Real rule-based errors, not annotation errors. [Paper](https://arxiv.org/pdf/2109.11377) |
| [ANLI](https://huggingface.co/datasets/facebook/anli) | 100K-1M | CC-BY-NC-4.0 | No audit found | - | Do not use as known-bad |
| [MultiNLI](https://huggingface.co/datasets/nyu-mll/multi_nli) | 100K-1M | Mixed tags | Via VariErr only | - | Use VariErr |
| CIFAR-N, [repo](https://github.com/UCSC-REAL/cifar-10-100n) | Image | Not stated | Human noisy labels | Amazon MTurk | Not usable: image, and rates unconfirmed |

Licensing and audit design notes:
- Pervasive Label Errors audited only flagged rows; 51% of flags were validated on average, and error rates ranged 0.15-10.12% — [Northcutt et al. 2021](https://arxiv.org/pdf/2103.14749). labelerrors.com returned only a title to my fetch, so the [repo](https://github.com/cleanlab/label-errors) is the working source.
- Vendrow et al. are cited for about 5% invalid in GSM8K — [Truong et al.](https://arxiv.org/pdf/2511.16842). The Platinum card's 110 removed and 10 relabeled is about 9.1% of 1,319 by my arithmetic. Truong et al. count 88 of 997 — 8.8%. A random 1,000-problem sample elsewhere found about 2% — [arXiv 2507.17015 and related, search snippet](https://arxiv.org/pdf/2507.17015). The rates conflict because they count different things.
- Base-set licences relevant to current runs: [OpenBookQA](https://huggingface.co/datasets/allenai/openbookqa) is tagged unknown, and [No Robots](https://huggingface.co/datasets/HuggingFaceH4/no_robots) is CC-BY-NC-4.0.

### Inferences
- Test v4's known-bad sets (TruthfulQA false answers, GSM-Plus perturbations) are real rows but constructed pairings. MMLU-Redux and Fantastic Bugs add organic errors. They should go into a new test v5, because test v4 is frozen.
- Build dataset-level positives by subject instead of mixing: MMLU Virology, Logical Fallacies and College Chemistry are real known-bad subjects (20-57% errors), while Management, Philosophy and similar are real clean controls from the same benchmark and audit team. That gives positives and negatives under one source and one judge difficulty family.
- For hard-but-valid negatives, use the 48 OpenBookQA rows and MedQA's 26 valid rows. They are exactly what the detector must not flag.

### Gaps
- SQuAD: no audit of gold spans found. ANLI: none found.
- `mislabeled MMLU` beyond Gema and Land: nothing else solid found. MMLU-Pro is covered only through Land.
- MMLU-Redux tally by error type: my live count timed out, so rates here are the paper's.
- CIFAR-N rates, TRUE subset download link, SciFact license, FindTheFlaws size: unconfirmed.
- MedQA 41% rests on a search snippet of the JMIR paper, which I did not open.

## How should a detector with rare real positives be evaluated?

### Takeaway
Report precision on real data at real prevalence, audit a random sample of unflagged rows as well as flags, use the source as the unit of analysis, and never let the detector or a similar model define truth. Most published precision figures are enriched, because only flags were reviewed.

### Cited Findings
- **Planted noise flatters detectors.** Wasserstein distance from clean loss on IMDB was 2.67 for real errors against 5.04 uniform and 4.91 class-based. On TweetNLP, human-originated noise was 2.33-4.02 against 5.23-5.62 for synthetic — [Chong et al.](https://arxiv.org/html/2205.12702v3). Klie's injected-noise ATIS exceeded AP 0.9 against real PLANK at 0.4 — [Klie et al.](https://arxiv.org/abs/2206.02280). Real noise was much harder for noise-robust methods in NER — [NoiseBench](https://arxiv.org/html/2405.07609v2). On AlleNoise, methods gained nothing over cross-entropy (63.71 baseline, best 63.73), and some were worse — [AlleNoise](https://arxiv.org/html/2407.10992v2).
- **Flag-only audits understate errors.** ImageNet experts reviewed 934 flagged and 1,000 unflagged images. Unflagged rows still showed 16% with label issues, and flagged images were 2.6 times as likely to be wrong. The estimate rose from 6% to about 20% — [Northcutt et al.](https://arxiv.org/pdf/2103.14749). In diagnostic testing this is partial verification bias, treated as a missing-data problem with known corrections — [tutorial, arXiv 2509.12217](https://arxiv.org/pdf/2509.12217).
- **Consensus counts as truth in several sources.** Nahum et al. set gold to the original label wherever the LLM agreed, so error rates are lower bounds — [Nahum et al.](https://aclanthology.org/2025.emnlp-main.1360.pdf). GSM8K-Platinum leaves all-agree rows unreviewed — [card](https://huggingface.co/datasets/madrylab/gsm8k-platinum). Land's truth is a stronger LLM — [Land 2026](https://arxiv.org/html/2605.30504v2).
- **Reviewer design matters.** Nahum et al. shuffled items and hid both original and LLM labels. Chong et al. raised MTurk κ from 0.131 to 0.464 on IMDB and 0.014 to 0.556 on Amazon by adding qualification tests, sentinel items and minimum time. Gema et al. used a hierarchy that separates clarity problems from wrong keys, and VariErr separates error from legitimate variation — [Gema](https://arxiv.org/html/2406.04127v3), [VariErr](https://arxiv.org/pdf/2403.01931).
- **Prevalence.** PR is more informative than ROC on imbalanced data — [Saito & Rehmsmeier 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4349800). Precision depends on class prevalence, so PR curves need the imbalance stated — [arXiv 2001.05571](https://arxiv.org/pdf/2001.05571v1.pdf).
- **Sampling under a budget.** Importance sampling with an instrumental distribution minimises variance when estimating F-measures — [Sawade et al. 2010](https://papers.nips.cc/paper/3999-active-estimation-of-f-measures); it stays consistent but depends on model calibration — [Poms et al.](https://arxiv.org/pdf/2109.05720). Nahum et al. use Clopper-Pearson with finite population correction — [source](https://aclanthology.org/2025.emnlp-main.1360.pdf).
- **Flag precision is not an error rate.** Berriche et al. stress that 23.8% is flag precision on checked items, not a benchmark-wide rate — [source](https://arxiv.org/pdf/2609.08765).

### Inferences
- Precision at a given prevalence (my calculation, for sensitivity 0.9 and false-positive rate 0.05 at item level): 2% prevalence gives 27%; 6.5% gives 57%; 20% gives 82%; 50% gives 95%. A precision number with no prevalence attached means little.
- Touchstone's 0 of 20 false flags is compatible with a true rate up to 13.9% (one-sided 95%) or 16.8% (two-sided upper) by my calculation, and it comes from few sources. Report "0 of 20 draws, N sources" with that bound.
- Recommended design for the next frozen test:
  1. **Unit of analysis is the source.** Four draws of one source are not four independent trials for generalisation. Report per-source false-flag rates and leave-one-source-out results, with bootstrap by source. Test v4 already reports false flags by source.
  2. **Two tiers, reported apart.** Tier A is organic real errors at natural prevalence (MMLU-Redux subjects, MedQA, ReaLMistake). Tier B is planted, labelled as planted and used only as a sensitivity floor. Never pool them.
  3. **Three negative classes.** Clean easy, clean hard (OpenBookQA, Fantastic Bugs valid rows) and ambiguous (VariErr). The false-flag rate on clean hard is the number that matters for sellers.
  4. **Dataset-level and item-level both.** Dataset flag: power curve at 2, 5, 10, 20, 30% organic errors. Item level: P@k and recall against MMLU-Redux, which allows true recall because it is a random sample.
  5. **Own audit of flags and non-flags.** Stratify: all flags plus a random sample of non-flags, blind to label and detector verdict, two reviewers, κ reported, disputes resolved, verdict categories wrong / ambiguous / fine. Weight results back by sampling rate. Fifty to 100 non-flagged rows per source catches most of the bias, though the interval stays wide.
  6. **Pre-register** the statistic, n, limit and stop rule, and hash before scoring, as was done for test v4.
  7. **Report with the number:** prevalence, sample size, source count, Clopper-Pearson interval, held-out or not, reviewer type.
  8. **Report a capture-recapture estimate only as a rough check.** Two detectors flag sets A and B, and total errors is about |A||B|/|A∩B|. All LLM detectors share errors, so this will undercount. I found no label-error application of it.
- Claims wording to keep: precision and recall "on planted test cases" stays separate from "on real errors", in line with the `METHOD.md` rule already in place. Real-error results can be stated plainly as strengths once measured.

### Gaps
- No text-domain study that quantifies the gap between planted and real precision for the same detector with held-out thresholds. The nearest are Chong's distances and Klie's dataset contrasts.
- No published guidance on false-flag bounds across sources for dataset-level flags. Dataset-level flagging on small samples appears unstudied, and the design above is my synthesis.
