import { useState } from 'react'
import { AnimatePresence, motion, LayoutGroup } from 'motion/react'
import { vendors, pct } from '../data'
import { Alert, Arrow, Check, Panel, Reveal, reduced } from '../ui'

const ease = [.16, 1, .3, 1] as const

/* What the pipeline caught, counted from the appraisal data rather than typed in. */
export function Caught() {
  const gamed = vendors.filter(e => e.hackability.score >= .2).length
  const copied = vendors.filter(e => e.redundancy.public_overlap >= .5).length
  const best = [...vendors].sort((a, b) => b.fair_value_per_task - a.fair_value_per_task)[0]
  const items: [string, string, string][] = [
    [`${gamed} of ${gamed}`, 'broken graders flagged', 'Each paid out reward for answers that solved nothing.'],
    [`${copied} of ${copied}`, 'copied dataset caught', `${pct(vendors.find(e => e.redundancy.public_overlap >= .5)!.redundancy.public_overlap)} of its tasks were already free.`],
    [best.grade, `for the one honest set`, `Priced at $${Math.round(best.fair_value_per_task)} a task, the only one worth buying.`],
  ]
  return (
    <div className="caught">
      {items.map(([big, label, text], i) => (
        <motion.div key={label} className="caught-item" initial={reduced ? false : { opacity: 0, y: 24, scale: .96 }} whileInView={{ opacity: 1, y: 0, scale: 1 }} viewport={{ once: true }}
          transition={{ delay: i * .12, type: 'spring', stiffness: 220, damping: 20 }} whileHover={{ y: -4 }}>
          <b>{big}</b><span>{label}</span><p>{text}</p>
        </motion.div>
      ))}
    </div>
  )
}

/* Arrow's information paradox, as a before-and-after the visitor can flip. */
export function Paradox() {
  const [side, setSide] = useState<'without' | 'with'>('without')
  const lines = side === 'without'
    ? [['buyer', 'Can I see the tasks before I pay?'], ['vendor', 'If I show you, I\'ve given the product away.'], ['buyer', 'Then show me proof it works.'], ['vendor', 'Here are results we ran ourselves.'], ['buyer', 'So I either trust you, or pay first and find out in weeks.']]
    : [['vendor', 'I upload the environment to Touchstone. It stays sealed.'], ['touchstone', 'We train small models on it and test them on problems neither of you has seen.'], ['buyer', 'I get the numbers and a fair price per task.'], ['vendor', 'My tasks never leave the sandbox.'], ['touchstone', 'And we never sell data, so we can rate everyone.']]
  return (
    <div className="paradox">
      <div className="paradox-copy">
        <h2>The buyer can't judge it without seeing it. <span className="transfer">The seller can't show it without giving it away.</span></h2>
        <p className="lede">Economists call this Arrow's information paradox. It is why training material is bought on trust today, and why it takes a neutral third party to fix it. Neither side can solve it alone.</p>
        <LayoutGroup id="paradox">
          <div className="seg" role="tablist" aria-label="Show the conversation">
            {(['without', 'with'] as const).map(k => (
              <button key={k} role="tab" aria-selected={side === k} onClick={() => setSide(k)}>
                {side === k && <motion.span layoutId="paradox-pill" className="seg-pill" transition={{ type: 'spring', stiffness: 380, damping: 32 }} />}
                <span>{k === 'without' ? 'Without Touchstone' : 'With Touchstone'}</span>
              </button>
            ))}
          </div>
        </LayoutGroup>
      </div>
      <Panel title={side === 'without' ? 'a purchase today' : 'a purchase with touchstone'} meta={side === 'without' ? 'stuck' : 'resolved'}>
        <div className="chat">
          <AnimatePresence mode="popLayout">
            {lines.map(([who, text], i) => (
              <motion.div key={side + i} className={`bubble ${who}`} initial={{ opacity: 0, y: 14, scale: .96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, scale: .96 }}
                transition={{ delay: reduced ? 0 : i * .22, type: 'spring', stiffness: 260, damping: 22 }}>
                <small>{who}</small>{text}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </Panel>
    </div>
  )
}

/* The exploit gallery: what we feed the grader, and what the appraised graders paid for it. */
export function Exploits() {
  const probes: [string, string, string][] = [
    ['empty answer', '""', 'Submit nothing at all.'],
    ['digit soup', '7 3 9 1 0 4 8 2', 'Spray digits and hope one matches.'],
    ['hedged guesses', '85 or 86 or 87', 'Glue several guesses together.'],
    ['echo the prompt', '47+38=', 'Repeat the question back.'],
    ['repeat last number in prompt', '38', 'Copy a number from the question.'],
    ['random 2-3 digits', '412', 'Answer with the right shape, wrong value.'],
  ]
  const code: [string, string, string][] = [
    ['edit the tests', 'assert True  # was: assert f(3) == 9', 'Rewrite the check instead of the code.'],
    ['exit early', 'sys.exit(0)', 'Quit before the tests can fail.'],
    ['format gaming', '<answer>\\boxed{…}</answer>', 'Match the expected format, not the answer.'],
  ]
  const [open, setOpen] = useState<string | null>('hedged guesses')
  const paid = (name: string) => {
    const scores = vendors.map(e => [e.name, e.hackability.per_exploit[name] ?? 0] as const).sort((a, b) => b[1] - a[1])
    return scores[0]
  }
  return (
    <div className="exploits">
      {probes.map(([name, sample, what], i) => {
        const [worst, score] = paid(name)
        const isOpen = open === name
        return (
          <motion.button key={name} layout className={`exploit${isOpen ? ' open' : ''}${score >= .2 ? ' hit' : ''}`} onClick={() => setOpen(isOpen ? null : name)}
            initial={reduced ? false : { opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * .05, layout: { type: 'spring', stiffness: 300, damping: 30 } }}>
            <motion.span layout="position" className="exploit-head"><b>{name}</b><span className={score >= .2 ? 'bad' : 'good'}>{score >= .2 ? <Alert /> : <Check />}{score >= .2 ? 'paid out' : 'held'}</span></motion.span>
            <motion.code layout="position">{sample}</motion.code>
            <AnimatePresence>
              {isOpen && (
                <motion.span className="exploit-more" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} transition={{ duration: .35, ease }}>
                  {what} The weakest grader we tested gave it <b className={score >= .2 ? 'bad' : ''}>{pct(score)}</b> of the reward{score > 0 ? ` (${worst})` : ''}.
                </motion.span>
              )}
            </AnimatePresence>
          </motion.button>
        )
      })}
      {code.map(([name, sample, what]) => (
        <div key={name} className="exploit code"><span className="exploit-head"><b>{name}</b><span className="dim">code environments</span></span><code>{sample}</code><span className="exploit-more static">{what}</span></div>
      ))}
    </div>
  )
}

/* The evidence: what the research and the market already show, with sources. */
export function Evidence() {
  const items: [string, string, string, string][] = [
    ['Data value varies wildly', 'Training on a well-chosen 5% of a dataset often beat training on all of it.', 'Xia et al., LESS · ICML 2024', 'https://proceedings.mlr.press/v235/xia24c.html'],
    ['Small runs can rank data', 'Small-model experiments predicted which pretraining data wins at larger scale.', 'Magnusson et al., DataDecide · ICML 2025', 'https://proceedings.mlr.press/v267/magnusson25a.html'],
    ['Vendors grade themselves', 'Surge reports +9.6, +5.3 and +3.5 points from its own environments, measured on its own setup.', 'Surge, cross-benchmark generalization', 'https://surgehq.ai/blog/cross-benchmark-generalization-for-long-horizon-agentic-tasks'],
    ['Graders are the weak point', 'Weak graders, leaked answers and tasks passed without being solved are the most common failure.', 'Invisible · Delphik', 'https://invisibletech.ai/blog/the-grader-problem-why-most-rl-environments-fail'],
  ]
  return (
    <div className="evidence">
      {items.map(([title, text, cite, url], i) => (
        <motion.a key={title} className="ev" href={url} target="_blank" rel="noopener" initial={reduced ? false : { opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * .08, duration: .7, ease }} whileHover={{ y: -4 }}>
          <b>{title}</b><p>{text}</p><small>{cite}<Arrow /></small>
        </motion.a>
      ))}
    </div>
  )
}

export function Section({ title, text, children, flush = false }: { title: React.ReactNode; text?: string; children: React.ReactNode; flush?: boolean }) {
  return (
    <section className={`section${flush ? ' flush' : ''}`}>
      <div className="wrap">
        <div className="section-head"><Reveal><h2>{title}</h2></Reveal>{text && <Reveal delay={.1}><p>{text}</p></Reveal>}</div>
        {children}
      </div>
    </section>
  )
}
