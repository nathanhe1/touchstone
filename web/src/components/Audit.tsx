/* The appraisal, front and centre: verified results under the hero, and the checks a report can raise.
   Each check and its effect on the price mirrors touchstone/valuation.py, so the list stays true to the engine. */
import { motion } from 'motion/react'
import { Count, reduced } from '../ui'

const ease = [.16, 1, .3, 1] as const

/* Only verified figures belong here, each with the scope it was measured on. */
const RESULTS: [value: string, label: string, scope: string][] = [
  ['21 of 21', 'RL environment cases exactly right', 'Locked test on test cases'],
  ['12 of 12', 'gameable graders caught', 'Locked test on test cases'],
  ['3 of 3', 'reworded test leaks caught', 'Locked test on test cases'],
]

export function Results() {
  return (
    <section className="results" aria-label="Appraisal results">
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
