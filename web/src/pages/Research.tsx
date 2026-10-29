import { motion } from 'motion/react'
import { data } from '../data'
import { Close, Count, Faq, Panel, Reveal, reduced } from '../ui'
import { Evidence, Section } from './Sections'

const ease = [.16, 1, .3, 1] as const

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
  const rho = data.validation.spearman_forecast_vs_actual
  const plan: [string, string, string][] = [
    ['Pick environments', '6 to 8 open RL environments', 'From the Prime Intellect Environments Hub, OpenEnv and Reasoning Gym.'],
    ['Train small', '0.5B, 1.5B and 3B models', 'One published GRPO recipe, identical at every size.'],
    ['Check against large', 'One 7B to 8B model', 'The "large-scale truth" the small models must predict.'],
    ['Publish', 'Touchstone Report #1', 'Which open environments transfer, which can be hacked, and whether the forecast held.'],
  ]
  return (
    <>
      <header className="page-head wrap">
        <motion.h1 initial={reduced ? false : { opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease }}>The evidence, <span className="transfer">and the open question.</span></motion.h1>
        <motion.p className="lede" initial={reduced ? false : { opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: .1, ease }}>
          Research says data value varies enormously and that small runs can predict which data wins. Nobody has shown that yet for RL environments. Here is what we know, what we don't, and the experiment that settles it.
        </motion.p>
      </header>

      <Section title="What's already known." flush><Evidence /></Section>

      <Section title={<>What our prototype <span className="transfer">hasn't proved yet.</span></>} text="On tiny CPU models, the small-model forecast did not predict the larger model. With six environments, that is too few to prove or disprove anything.">
        <div className="two" style={{ alignItems: 'center' }}>
          <Reveal>
            <div className="big-figure"><Count value={`${rho < 0 ? '−' : ''}${Math.abs(rho).toFixed(2)}`} /></div>
            <p className="lede">Rank match between forecast and result in the demo. We keep the forecast only if a real test reaches <b>0.7</b> or higher, and drop it below <b>0.6</b>.</p>
          </Reveal>
          <Reveal delay={.1}>
            <Panel title="keep or kill" meta="pre-registered">
              <div style={{ padding: 24 }}>
                <div className="kk">
                  <motion.div className="kk-bar" initial={reduced ? false : { scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }} transition={{ duration: 1.2, ease }}>
                    <span className="kk-zone drop" style={{ width: '80%' }}>drop the forecast</span><span className="kk-zone grey" style={{ width: '5%' }} /><span className="kk-zone keep" style={{ width: '15%' }}>keep</span>
                  </motion.div>
                  <motion.span className="kk-mark" style={{ left: `${(rho + 1) / 2 * 100}%` }} initial={reduced ? false : { opacity: 0, y: -10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: .9, type: 'spring' }}>demo</motion.span>
                  <div className="kk-axis"><span>−1</span><span>0</span><span>0.6</span><span>1</span></div>
                </div>
                <p className="note">If the forecast fails, Touchstone narrows to grader audits, which already work.</p>
              </div>
            </Panel>
          </Reveal>
        </div>
      </Section>

      <Section title={<>The first real test: <span className="transfer">4 to 6 weeks, under $5k.</span></>} text="About 150 to 250 GPU hours. Small enough to run before raising, decisive enough to change the plan." flush>
        <ol className="plan">
          {plan.map(([title, big, text], i) => (
            <motion.li key={title} initial={reduced ? false : { opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * .1, duration: .7, ease }}>
              <small>{i + 1}</small><b>{title}</b><span>{big}</span><p>{text}</p>
            </motion.li>
          ))}
        </ol>
      </Section>

      <Section title="The risks, honestly.">
        <Faq items={[
          ['Small models may not predict frontier value', 'The make-or-break technical risk. Pretraining research suggests small runs rank data well; RL environments are unproven. The first experiment tests it directly.'],
          ['Frontier labs may evaluate in-house', 'So we start with vendors and second-tier buyers, who feel the pain and have no evaluation team.'],
          ['The ratings-agency conflict', 'If sellers pay, there is pressure to inflate. We publish and pre-register the method, fix the recipe, and sell buyer-side subscriptions.'],
          ['Vendors may not share environments', 'The sealed sandbox and private-by-default reports address this. Public badges are opt-in.'],
          ['A big vendor launches its own "verified" label', 'A seller verifying itself is the problem Touchstone exists to fix. Neutrality is the product.'],
        ]} />
      </Section>

      <Section title="Sources." flush>
        <ul className="sources">{SOURCES.map(([t, u]) => <li key={u}><a href={u} target="_blank" rel="noopener">{t}</a></li>)}</ul>
      </Section>

      <Close title="Help us run the first test." text="If you build or buy RL environments, we'd like to appraise yours." />
    </>
  )
}
