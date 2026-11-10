# Case study: WebArena's string-match grader

**Verdict: caught.** Touchstone refused to price this environment because its grader pays for wrong answers, which is the problem the WebArena authors' peers documented.

## What was appraised

- **Material:** the 212 WebArena test tasks graded by string matching alone, without the LLM judge: 172 `must_include` tasks and 40 `exact_match` tasks. They come from `config_files/test.raw.json` in github.com/web-arena-x/webarena at commit `dce04686a5` (Apache-2.0).
- **The grader:** `verify()` re-implements WebArena's `StringEvaluator` (`clean_answer`, `exact_match`, `must_include` in `evaluation_harness/evaluators.py` at the same commit) line for line. The one change: `nltk.word_tokenize`, which WebArena uses only when a `must_include` list holds a single one-character reference, is replaced by a regex word split.
- **Held-out suite:** the 82 WebArena tasks graded by fuzzy match, with their reference answers. It is used only for the overlap screen, since no model was trained.
- **Built by:** `scripts/build_case_studies.py`. Material sha256 `39eeab50ccb5089c`.
- **Run:** quick mode on the Mac (MPS), engine commit `1f9089a6`, 63 s end to end. Raw output is in `out/case_studies/webarena_strings_quick/` (`report.json`, `report.md`, `run.log`).

## The documented problem

Zhu et al. (2025), *Establishing Best Practices for Building Rigorous Agentic Benchmarks* (NeurIPS 2025 Datasets and Benchmarks; arXiv:2507.02825), found that WebArena's "substring-matching ignores extraneous content" and that "an agent that includes irrelevant information is considered successful". Their checklist also marks WebArena as failing the item on systematically listing all possible answers. They estimate that string-matching issues overstate agent performance on WebArena by up to 5.2%.

## What Touchstone found

| Check | Result |
|---|---|
| Grader audit, worst exploit | `wrong: fraction appended` earns **84%** of the reward (a wrong answer that still contains the right string) |
| Hedges: right and wrong answers listed together, across 8 separators | **82.5%** each |
| Right answer buried in junk text | **82.5%** |
| Negated answer (`-` prefixed) | **81%** |
| Grader accepts its own reference answers | 100% |
| Grader is deterministic and stays in [0, 1] | yes |
| Overlap with the held-out suite | 3.7% of suite items (below the 5% line) |
| Flags | `gameable_grader` (blocking) |
| Grade and price | **D, $0 per item**; quick mode stopped after screening |

The 82.5% payoff is no accident. 172 of the 212 tasks (81%) use `must_include`, which passes any reply that contains the reference string. The other 40 use `exact_match`, which rejects padding. The probes measure that split almost exactly.

A concrete case, re-run by hand against the same grader. Task: "Tell me the full address of all international airports that are within a driving distance of …". The reference is "Pittsburgh International Airport, Southern Beltway, Findlay Township, Allegheny County, 15231, United States". All four replies below earn full reward:

- `Not Pittsburgh International Airport, …, United States`
- `-Pittsburgh International Airport, …, United States`
- `Pittsburgh International Airport, …, United States or 7`
- `I could not find it. Candidates: 7, 12, Pittsburgh International Airport, …, United States, 31.`

## Did the grade and the price come out right?

**Yes.** A buyer training a policy against this grader would pay for hedged and padded answers on four tasks in five. The blocking flag and the $0 price are the right outcome. Touchstone reached them in about a minute with no training run, and it named the exploit family the published audit describes.

## What it missed, and the limits of this test

- **Only the string-match part of WebArena was appraised.** WebArena's `url_match` and `program_html` graders need the live websites, and the `fuzzy_match` grader calls an LLM judge. Touchstone's environment interface sees only a reply string, so it cannot appraise those parts.
- **The LLM-judge issue Zhu et al. report** (an empty reply accepted on tasks whose answer is "N/A") was out of reach for the same reason.
- **No training run.** Quick mode stops at a blocking flag, so this does not show that a small policy would actually find the hedge within a training budget. The probe measures what the grader pays, not what a policy learns.
- **The re-implementation is ours.** It follows WebArena's code line for line, but it is not WebArena's harness running.
