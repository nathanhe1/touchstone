# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + Vite (TypeScript), built to static files in `web/dist` and published to the Touchstone claude.ai artifact link. Code lives in the private GitHub repo `nathanhe1/touchstone`; every change ships as a branch, pull request and merge. The Python package (`touchstone/`) is the appraisal engine and produces `out/appraisals.json`, which the site reads. Animation libraries the founder asked for: GSAP, Motion, React Spring, ShaderGradient, Anime.js, plus a liquid-glass effect.

## Users

Primary: AI teams buying RL environments and post-training material (frontier labs, neolabs, AI product companies doing RL for coding agents, legal, finance, support). Their question: "Will training on this environment improve my model enough to justify the cost?"
Secondary: environment and data vendors who want a neutral rating to win contracts and justify prices. Also read by YC partners during the founder's application.

## Product Purpose

Touchstone helps AI companies decide which training material and RL environments are worth paying for. It runs small, cheap experiments before a company commits to full-scale training, so they spend less on ineffective training and get more useful learning from their compute budget.

## Positioning

Independent: it never sells data or environments. It measures training value (not finished-model quality), before purchase, at small-model cost. Scale AI sells data and grades its own; Patronus AI evaluates finished models; in-house teams only learn after buying, at full cost.

## Operating Context

The vendor uploads an environment (tasks, tools, grader) to a sealed sandbox; the buyer never sees the tasks, only results. Touchstone trains a fixed family of small open models with one published recipe at several sizes, tests transfer on a private held-out suite, probes the grader for reward exploits, checks overlap with free data, forecasts the gain at the buyer's model size and estimates fair value per task.

## Capabilities and Constraints

- Working prototype: the full pipeline runs end to end on tiny CPU models and six fictional environments (`out/appraisals.json`).
- Report measures: learnability, transfer, reward exploits (hackability), redundancy, forecast, fair value per task.
- In the demo run the small-to-large forecast did not rank well (rank match −0.03); the site must stay honest about this.
- Planned, not built: comparing environments side by side; testing a real open-source environment; support beyond RL environments.
- Planned pricing: $10k–$50k per appraisal, $50k–$250k a year subscription; compute roughly $1k–$5k per appraisal.
- The request form is an external link not yet provided (`REQUEST_FORM_URL` in `touchstone/report.py`).

## Brand Commitments

Name: Touchstone (not "Assay"). Voice: plain, direct, short sentences; no AI-sounding filler. The founder wants it straightforward and powerful, with rich motion and interactive elements.

## Evidence on Hand

- Demo appraisal data: `out/appraisals.json` (fictional vendors, real pipeline).
- Research: Xia et al., LESS, ICML 2024 (5% of well-chosen data can beat 100%); Magnusson et al., DataDecide, ICML 2025 (small runs predict which data wins at scale); Scale AI blog on RL environments.
- Market figures from the founder's research: RL tasks $200–$2,000 each; leading labs reportedly ~$1B/yr each on human data; Gartner expects inference at 55% of AI cloud spend in 2026; no independent auditor in market maps; opportunity estimate $30M–$100M+ (1–3% of a few $B spend by 2027–28).
- No customers, testimonials, pilots or founder bios yet. Do not fabricate any; traction is "actively reaching out".

## Product Principles

1. Independence is the product: never imply Touchstone sells data.
2. Transfer to unseen problems is the number that matters, not training reward.
3. Show the evidence, including where the method fell short.
4. Cheap before expensive: an appraisal costs a fraction of one bad purchase.
