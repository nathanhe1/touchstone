# h5x real competing materials

Four more families of real public datasets in letter/label form, for the h5 extension test. Built by
`scripts/h5x_materials.py`, which reuses the sampling, screening and manifest code of `scripts/h5_materials.py`
unchanged. Families were chosen by task type and public availability only, before h5 was scored and without sight of
any h5 run result. Three are needed; `tox` is the spare. Combined hash of all material and suite files:
`3b8f9fdccb8728f41dc8fda1e9056a62cb6434c5f8f742817345b1c3f6eb0578` (`h5x_materials.sha256`; everything below is in `manifest.json`).

- **Rows:** 1,000 per material, seed 20261110, uniform without replacement. Label families (`sent`, `para`, `tox`)
  are stratified 500 / 500, so the answer letter is uniform. For `cs` the options are shuffled per row.
- **Format:** the h5 row format and h4 prompt form (`A) ...` options, "Reply with the letter only."); the completion is
  the answer letter. Every prompt fits 32-token replies; the longest prompts are HellaSwag (p95 276 tokens).
- **Suites come from a different dataset than every material**, except `para`, whose suite is MRPC test and whose
  materials include MRPC's own training split (as `anli_train` does in h5). Label suites are cut to equal class sizes
  with a seeded sample; all pass the class-balance cap min(0.65, 2.5/k), as does every material.
- **Text is cut at 600 characters** at a word boundary (reviews and comments), as h4 cut at 500.
- **Label mappings made here:** TweetEval sentiment drops neutral tweets; Civil Comments counts toxicity >= 0.5 as
  toxic; Davidson counts hate speech or offensive language as toxic; Amazon polarity and Civil Comments are first
  cut to a uniform 6,000 rows per class, then sampled like the rest.
- **Screen:** the only overlap is `mrpc_train`: 24 of its first 1,000 sampled rows match an MRPC test pair (4 exact,
  the rest near-duplicates or paraphrases among all candidates). Dropped and replaced.
- **Option counts differ within `cs`:** SWAG, HellaSwag, CosmosQA 4; Social IQa 3; PIQA 2; the suite (CODAH) 4.
- **First-listed material per family** (all-wrong and placebo arms): `sst2`, `qqp`, `swag`, `wiki_toxic`.
- **Licences:** several are untagged or "unknown" on the Hub and are research datasets; ToxicChat (suite) is
  non-commercial. Fine for this test, not for resale. `tox` files contain offensive text by nature.

Seed 20261110, 1000 rows per material. Tokens counted with Qwen/Qwen2.5-1.5B-Instruct.

**sent** (binary sentiment as a letter choice). Suite: `examples/h5x/sent/suite.jsonl`, 2730 rows from SetFit/CR test + train @ 01e427e689, licence untagged on the Hub (Hu and Liu 2004 customer reviews), majority class 0.5, sha256 `e0cb12d83a17108b`.

| Material | Source @ revision | Licence | Eligible rows | Suite overlap in raw sample | Dropped | Majority class | Completion tokens p50 / p95 | Over 512 tokens | sha256 (first 16) | Why a buyer compares it |
|---|---|---|---|---|---|---|---|---|---|---|
| `sst2` | stanfordnlp/sst2 @ 8d51e7e488 | unknown on the Hub (Stanford Sentiment Treebank; research use) | 67,349 | 0 of 1000 | duplicate 1 | 0.5 | 1 / 1 | 0% | `8baf416ba5b66cf9` | SST-2: the standard sentiment training set (movie-review phrases). |
| `imdb` | stanfordnlp/imdb @ e6281661ce | other (Maas et al. 2011; research use) | 25,000 | 0 of 1000 | none | 0.5 | 1 / 1 | 0% | `a91bb2c303a9f078` | IMDB: long movie reviews, the other default sentiment set. |
| `amazon` | fancyzhx/amazon_polarity @ 9d9c45c18f | Apache-2.0 | 3,600,000 | 0 of 1000 | none | 0.5 | 1 / 1 | 0% | `13795da16a1957f5` | Amazon polarity: product reviews, the largest and the closest in domain to a product-review suite. |
| `rotten` | cornell-movie-review-data/rotten_tomatoes @ aa13bc287f | unknown on the Hub (Pang and Lee 2005) | 8,530 | 0 of 1000 | none | 0.5 | 1 / 1 | 0% | `dcb932f1185802f3` | Rotten Tomatoes: one-sentence movie reviews, small and clean. |
| `tweets` | cardiffnlp/tweet_eval @ b3a375baf0 | unknown on the Hub (SemEval tasks; research use) | 24,942 | 0 of 1000 | none | 0.5 | 1 / 1 | 0% | `48a521793eaef61d` | TweetEval sentiment (SemEval-2017), neutral tweets dropped: social-media text. |

**para** (paraphrase / duplicate detection as a letter choice). Suite: `examples/h5x/para/suite.jsonl`, 1156 rows from nyu-mll/glue mrpc/test @ bcdcba79d0, licence other (MRPC: Microsoft Research licence; QQP: Quora terms), majority class 0.5, sha256 `1ceb438c55318300`.

| Material | Source @ revision | Licence | Eligible rows | Suite overlap in raw sample | Dropped | Majority class | Completion tokens p50 / p95 | Over 512 tokens | sha256 (first 16) | Why a buyer compares it |
|---|---|---|---|---|---|---|---|---|---|---|
| `qqp` | nyu-mll/glue @ bcdcba79d0 | other (MRPC: Microsoft Research licence; QQP: Quora terms) | 363,846 | 0 of 1000 | none | 0.5 | 1 / 1 | 0% | `ad6e967cc71362f2` | Quora Question Pairs: the largest duplicate-question set. |
| `mrpc_train` | nyu-mll/glue @ bcdcba79d0 | other (MRPC: Microsoft Research licence; QQP: Quora terms) | 3,668 | 24 of 1000 | suite_overlap 24 | 0.5 | 1 / 1 | 0% | `caff39a26c7b80f2` | MRPC's own training split: in-distribution for the suite, and small. |
| `paws` | google-research-datasets/paws @ 161ece9501 | other (free use with attribution to Google) | 49,401 | 0 of 1000 | none | 0.5 | 1 / 1 | 0% | `fbd2aa4473bf3fd7` | PAWS: human-labelled adversarial pairs with high word overlap. |
| `paws_silver` | google-research-datasets/paws @ 161ece9501 | other (free use with attribution to Google) | 645,652 | 0 of 1000 | none | 0.5 | 1 / 1 | 0% | `6dcceb45cc41bb48` | PAWS unlabeled_final: the same kind of pairs with model-assigned (silver) labels, far larger and noisier. |
| `medqp` | curaihealth/medical_questions_pairs @ d91d9da9b2 | unknown on the Hub | 3,048 | 0 of 1000 | none | 0.5 | 1 / 1 | 0% | `5dc7e4a3adecc276` | Medical question pairs written by doctors: a small specialist set. |

**cs** (commonsense multiple choice, letter answer). Suite: `examples/h5x/cs/suite.jsonl`, 2773 rows from jaredfern/codah codah/train (the full set) @ 4b0e0e7f33, licence ODC-BY, majority class 0.259, sha256 `7f07a6666c60f7a2`.

| Material | Source @ revision | Licence | Eligible rows | Suite overlap in raw sample | Dropped | Majority class | Completion tokens p50 / p95 | Over 512 tokens | sha256 (first 16) | Why a buyer compares it |
|---|---|---|---|---|---|---|---|---|---|---|
| `swag` | allenai/swag @ dc48148372 | unknown on the Hub (MIT in the authors' repository) | 73,546 | 0 of 1000 | duplicate 5 | 0.26 | 1 / 1 | 0% | `f7673d994813274e` | SWAG: pick the plausible next event, from video captions. |
| `hellaswag` | Rowan/hellaswag @ 218ec52e09 | untagged on the Hub (MIT in the authors' repository) | 39,905 | 0 of 1000 | none | 0.264 | 1 / 1 | 0% | `429bc22d6e573ae0` | HellaSwag: SWAG's harder, adversarially filtered successor. |
| `cosmos` | allenai/cosmos_qa @ ed50fe83db | CC-BY-4.0 | 25,252 | 0 of 1000 | duplicate 14 | 0.276 | 1 / 1 | 0% | `0568845c171132a9` | CosmosQA: commonsense reading of short personal narratives. |
| `socialiqa` | allenai/social_i_qa @ 537a2ec8ec | untagged on the Hub | 33,377 | 0 of 1000 | none | 0.342 | 1 / 1 | 0% | `d53581c4c1f419d8` | Social IQa: social and emotional commonsense, 3 options. |
| `piqa` | ybisk/piqa @ 142c51238b | unknown on the Hub (AFL-3.0 in the authors' repository) | 16,113 | 0 of 1000 | duplicate 16 | 0.523 | 1 / 1 | 0% | `81d811ca2389c732` | PIQA: physical commonsense, 2 options. |

**tox** (toxicity as a letter choice (spare family)). Suite: `examples/h5x/tox/suite.jsonl`, 1492 rows from lmsys/toxic-chat 0124 test + train @ 29df8e4dba, licence CC-BY-NC-4.0 (non-commercial), majority class 0.5, sha256 `d2c7080d6aced909`.

| Material | Source @ revision | Licence | Eligible rows | Suite overlap in raw sample | Dropped | Majority class | Completion tokens p50 / p95 | Over 512 tokens | sha256 (first 16) | Why a buyer compares it |
|---|---|---|---|---|---|---|---|---|---|---|
| `wiki_toxic` | OxAISH-AL-LLM/wiki_toxic @ 872656a156 | CC0-1.0 | 127,656 | 0 of 1000 | duplicate 1 | 0.5 | 1 / 1 | 0% | `15cc7d9404a07342` | Jigsaw Wikipedia talk-page comments: the standard toxicity training set. |
| `civil` | google/civil_comments @ f2970eb3a5 | CC0-1.0 | 1,804,874 | 0 of 1000 | none | 0.5 | 1 / 1 | 0% | `d844fe63dbf86fc5` | Civil Comments: news-site comments with crowd toxicity scores (toxic at 0.5 or more). |
| `tweet_offensive` | cardiffnlp/tweet_eval @ b3a375baf0 | unknown on the Hub (SemEval tasks; research use) | 11,916 | 0 of 1000 | none | 0.5 | 1 / 1 | 0% | `cd44c590678a81df` | TweetEval offensive (OLID): offensive tweets. |
| `tweet_hate` | cardiffnlp/tweet_eval @ b3a375baf0 | unknown on the Hub (SemEval tasks; research use) | 8,993 | 0 of 1000 | duplicate 1 | 0.5 | 1 / 1 | 0% | `a99b5f5a47b64301` | TweetEval hate (HatEval): hate speech against women and immigrants. |
| `davidson` | tdavidson/hate_speech_offensive @ adc5fb7746 | unknown on the Hub (MIT in the authors' repository) | 24,783 | 0 of 1000 | none | 0.5 | 1 / 1 | 0% | `5328a412bac037ec` | Davidson et al. hate and offensive tweets (hate or offensive counted as toxic). |

