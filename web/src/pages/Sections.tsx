import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { vendors, pct } from '../data'
import { Alert, Arrow, Check, Reveal, reduced } from '../ui'

const ease = [.16, 1, .3, 1] as const

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
