import { motion } from 'motion/react'
import { Close, reduced, PageHead } from '../ui'
import { Evidence, Section } from './Sections'

const ease = [.22, 1, .36, 1] as const

export const SOURCES: [string, string][] = [
  ['Xia et al., LESS: selecting influential data (ICML 2024)', 'https://proceedings.mlr.press/v235/xia24c.html'],
  ['Magnusson et al., DataDecide (ICML 2025)', 'https://proceedings.mlr.press/v267/magnusson25a.html'],
  ['Small-to-large generalization of data choices', 'https://arxiv.org/pdf/2505.16260'],
  ['Data Shapley (Ghorbani and Zou)', 'https://proceedings.mlr.press/v97/ghorbani19c/ghorbani19c.pdf'],
  ['TuneAhead: forecasting fine-tune results from a short probe', 'https://arxiv.org/html/2606.17660v1'],
  ['Scale AI on RL environments', 'https://scale.com/blog/rl-environments'],
  ['WMDQS 2025, submission 11', 'https://wmdqs.org/submissions-2025/11.pdf'],
  ['Surge: cross-benchmark generalization (vendor-run)', 'https://surgehq.ai/blog/cross-benchmark-generalization-for-long-horizon-agentic-tasks'],
  ['Invisible: the grader problem', 'https://invisibletech.ai/blog/the-grader-problem-why-most-rl-environments-fail'],
  ['Delphik: audit the environment', 'https://posttrain.dev/blog/audit-the-environment'],
  ['TechCrunch: Silicon Valley bets on RL environments', 'https://techcrunch.com/2025/09/21/silicon-valley-bets-big-on-environments-to-train-ai-agents/'],
  ['What AI labs pay for human data (citing Epoch AI)', 'https://aitraining.jobs/research/what-ai-labs-pay-for-human-data'],
  ['Pebblous: from labeling to RL environments', 'https://blog.pebblous.ai/blog/labeling-to-rl-environments/en/'],
  ['TechTimes on Gartner: inference passes training spend', 'https://www.techtimes.com/articles/323879/20260811/gartner-marks-first-year-inference-spending-beats-ai-training-55-cents-every-cloud-dollar.htm'],
  ['Troveo: how to buy AI training data', 'https://www.troveo.ai/resources/buy-ai-training-data'],
  ['Future Stack: RL environment platforms', 'https://future-stack-reviews.com/rl-environment-platforms/'],
  ['DataGravity: RL environments, who is who', 'https://www.datagravity.dev/p/rl-environments-for-agentic-ai-who'],
  ['RL List: environment vendors', 'https://www.rl-list.com/'],
]

export default function Research() {
  const plan: [string, string, string][] = [
    ['Pick environments', '6 to 8 open RL environments', 'From the Prime Intellect Environments Hub, OpenEnv and Reasoning Gym.'],
    ['Train small', '0.5B, 1.5B and 3B models', 'One published GRPO recipe, identical at every size.'],
    ['Check against large', 'One 7B to 8B model', 'The "large-scale truth" the small models must predict.'],
    ['Publish', 'Touchstone Report #1', 'Which open environments transfer, which can be hacked, and what each is worth.'],
  ]
  return (
    <>
      <PageHead>
        <motion.h1 initial={reduced ? false : { opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease }}>Built on <span className="transfer">the research.</span></motion.h1>
        <motion.p className="lede" initial={reduced ? false : { opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: .1, ease }}>
          Data value varies enormously, and small training runs can predict which data wins at scale. Touchstone turns that research into a product for RL environments.
        </motion.p>
      </PageHead>

      <Section title="What the research shows." flush><Evidence /></Section>

      <Section title={<>Next: <span className="transfer">Touchstone Report #1.</span></>} text="The first public appraisal of open RL environments, run on real open models in about 150 to 250 GPU hours.">
        <ol className="plan">
          {plan.map(([title, big, text], i) => (
            <motion.li key={title} initial={reduced ? false : { opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * .1, duration: .7, ease }}>
              <small>{i + 1}</small><b>{title}</b><span>{big}</span><p>{text}</p>
            </motion.li>
          ))}
        </ol>
      </Section>

      <Section title="Sources." flush>
        <ul className="sources">{SOURCES.map(([t, u]) => <li key={u}><a href={u} target="_blank" rel="noopener">{t}</a></li>)}</ul>
      </Section>

      <Close title="Get your environment appraised." text="If you build or buy RL environments, we'd like to appraise yours." />
    </>
  )
}
