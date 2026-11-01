/* The audit, front and centre: verified results under the hero, and the checks a report can raise.
   Each check and its effect on the price mirrors touchstone/valuation.py, so the list stays true to the engine. */
import { motion } from 'motion/react'
import { Count, Panel, reduced } from '../ui'

const ease = [.16, 1, .3, 1] as const

/* Only verified figures belong here, each with the scope it was measured on. */
const RESULTS: [value: string, label: string, scope: string][] = [
  ['92%', 'of problems caught', 'blind test, on test cases'],
  ['95%', 'of flags correct', 'blind test, on test cases'],
  ['0', 'false alarms in 28 clean real samples', 'numeric and code checks'],
]

export function Results() {
  return (
    <section className="results" aria-label="Audit results">
      <div className="wrap">
        <dl className="results-row">
          {RESULTS.map(([value, label, scope], i) => (
            <motion.div key={label} initial={reduced ? false : { opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * .08, duration: .6, ease }}>
              <dd><Count value={value} /></dd>
              <dt>{label}<small>{scope}</small></dt>
            </motion.div>
          ))}
        </dl>
      </div>
    </section>
  )
}

type Effect = 'block' | 'cut'
const CHECKS: [name: string, meaning: string, effect: Effect][] = [
  ['Gameable grader', 'Answers that solve nothing still collect reward.', 'block'],
  ['Reward that stays in training', 'Reward climbs while accuracy on new problems does not.', 'block'],
  ['Leaked answers', 'The answer is sitting in the prompt.', 'block'],
  ['Wrong labels', 'Worked solutions that do not add up.', 'block'],
  ['Test overlap', 'Items that overlap our private test suite.', 'block'],
  ['Copied material', 'Tasks that are already free in public sets.', 'cut'],
  ['Repeats', 'The same item sold more than once.', 'cut'],
  ['Off topic', 'Material that does not fit what it claims to train.', 'cut'],
]

export function Checks() {
  return (
    <Panel title="audit checks" meta="what a report can flag" className="checks">
      <ul className="check-list">
        {CHECKS.map(([name, meaning, effect], i) => (
          <motion.li key={name} initial={reduced ? false : { opacity: 0, x: -14 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true, margin: '0px 0px -6% 0px' }} transition={{ delay: i * .05, duration: .5, ease }}>
            <b>{name}</b>
            <span>{meaning}</span>
            <em className={effect}>{effect === 'block' ? 'blocks the price' : 'cuts the price'}</em>
          </motion.li>
        ))}
      </ul>
    </Panel>
  )
}
