import { motion } from 'motion/react'
import { Close, reduced } from '../ui'
import { Evidence, Section } from './Sections'

const ease = [.16, 1, .3, 1] as const

export const SOURCES: [string, string][] = [
  ['Xia et al., LESS: selecting influential data (ICML 2024)', 'https://proceedings.mlr.press/v235/xia24c.html'],
  ['Magnusson et al., DataDecide (ICML 2025)', 'https://proceedings.mlr.press/v267/magnusson25a.html'],
  ['Small-to-large generalization of data choices', 'https://arxiv.org/pdf/2505.16260'],
  ['Surge: cross-benchmark generalization (vendor-run)', 'https://surgehq.ai/blog/cross-benchmark-generalization-for-long-horizon-agentic-tasks'],
  ['Invisible: the grader problem', 'https://invisibletech.ai/blog/the-grader-problem-why-most-rl-environments-fail'],
  ['Delphik: audit the environment', 'https://posttrain.dev/blog/audit-the-environment'],
  ['TechCrunch: Silicon Valley bets on RL environments', 'https://techcrunch.com/2025/09/21/silicon-valley-bets-big-on-environments-to-train-ai-agents/'],
  ['What AI labs pay for human data (citing Epoch AI)', 'https://aitraining.jobs/research/what-ai-labs-pay-for-human-data'],
  ['Pebblous: from labeling to RL environments', 'https://blog.pebblous.ai/blog/labeling-to-rl-environments/en/'],
]

export default function Research() {
  return (
    <>
      <header className="page-head wrap">
        <motion.h1 initial={reduced ? false : { opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease }}>Built on <span className="transfer">the research.</span></motion.h1>
        <motion.p className="lede" initial={reduced ? false : { opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: .1, ease }}>
          The value of training material varies enormously, and vendors mostly grade their own. Touchstone builds on that research with independent checks for RL environments.
        </motion.p>
      </header>

      <Section title="What the research shows." flush><Evidence /></Section>

      <Section title="Sources." flush>
        <ul className="sources">{SOURCES.map(([t, u]) => <li key={u}><a href={u} target="_blank" rel="noopener">{t}</a></li>)}</ul>
      </Section>

      <Close title="Get your environment appraised." text="If you build or buy RL environments, we'd like to appraise yours." />
    </>
  )
}
