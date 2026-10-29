/* Components ported from Watermelon UI (MIT, github.com/WatermelonCorp/watermelon-platform): fluid tabs, adaptive
   slider, deployment card and changeable pricing section. Behaviour and motion follow the originals; styling uses
   Touchstone's own tokens instead of Tailwind so the rest of the site is untouched. */
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { AnimatePresence, motion, LayoutGroup } from 'motion/react'

const reduced = typeof window !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches

/* ---------- Fluid tabs: a pill that springs between options, with a brief blur on the label that becomes active ---------- */
export function FluidTabs<T extends string>({ items, value, onChange, id, label }: { items: { id: T; label: string }[]; value: T; onChange: (id: T) => void; id: string; label: string }) {
  return (
    <LayoutGroup id={id}>
      <div className="wm-tabs" role="tablist" aria-label={label}>
        {items.map(t => {
          const on = t.id === value
          return (
            <button key={t.id} role="tab" aria-selected={on} className={on ? 'on' : ''} onClick={() => onChange(t.id)}>
              {on && <motion.span layoutId="wm-pill" className="wm-pill" transition={{ type: 'spring', stiffness: 280, damping: 25, mass: .8 }} />}
              <motion.span className="wm-label" animate={reduced ? undefined : { filter: on ? ['blur(0px)', 'blur(4px)', 'blur(0px)'] : 'blur(0px)', scale: on ? 1.03 : 1 }}
                transition={{ filter: { duration: .3, ease: 'easeOut' }, scale: { type: 'spring', stiffness: 300, damping: 15 } }}>{t.label}</motion.span>
            </button>
          )
        })}
      </div>
    </LayoutGroup>
  )
}

/* ---------- Adaptive slider: a pill track whose fill and thumb spring after the input, with rolling digits ---------- */
function Rolling({ text }: { text: string }) {
  return (
    <span className="wm-roll">
      <AnimatePresence mode="popLayout" initial={false}>
        {text.split('').map((c, i) => (
          <motion.span key={c + i} initial={reduced ? false : { y: 12, opacity: 0 }} animate={{ y: 0, opacity: 1, transition: { type: 'spring', stiffness: 200, damping: 20 } }} exit={{ opacity: 0, transition: { duration: 0 } }}>{c}</motion.span>
        ))}
      </AnimatePresence>
    </span>
  )
}
export function AdaptiveSlider({ id, label, value, min, max, step, format, onChange, tone = 'gold' }: { id: string; label: string; value: number; min: number; max: number; step: number; format: (v: number) => string; onChange: (v: number) => void; tone?: 'gold' | 'risk' }) {
  const p = (value - min) / (max - min)
  // The fill shifts colour with the value: silver, then gold, then red once the risk is high.
  const fill = tone === 'risk' ? (p < .4 ? 'linear-gradient(90deg,#6f757d,#b9bfc8)' : p < .7 ? 'linear-gradient(90deg,#8a6b2c,#e2b45a)' : 'linear-gradient(90deg,#8a3a32,#ff6b5b)') : 'linear-gradient(90deg,#8a6b2c,#e2b45a)'
  const spring = { type: 'spring' as const, stiffness: 300, damping: 30 }
  return (
    <div className="wm-slider">
      <label htmlFor={id}><span>{label}</span><b><Rolling text={format(value)} /></b></label>
      <div className="wm-track">
        <div className="wm-dots">{Array.from({ length: 6 }, (_, i) => <i key={i} />)}</div>
        <motion.div className="wm-fill" animate={{ width: `calc(${p} * (100% - 36px) + 36px)`, background: fill }} transition={spring} />
        <input id={id} type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(+e.target.value)} />
        <motion.div className="wm-thumb" animate={{ left: `calc(${p} * (100% - 36px))` }} transition={spring}><i /></motion.div>
      </div>
    </div>
  )
}

/* ---------- Appraisal card: the deployment card, recast as one environment moving through an appraisal ---------- */
type StepStatus = 'pending' | 'loading' | 'success' | 'error'
export type AppraisalStep = { name: string; detail: string; seconds: number; result: string; tone?: 'good' | 'bad' }
const Icon = ({ s }: { s: StepStatus }) => s === 'loading'
  ? <motion.svg viewBox="0 0 16 16" animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}><circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="20 18" strokeLinecap="round" /></motion.svg>
  : s === 'success' ? <svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="7" fill="currentColor" opacity=".18" /><path d="M5 8.4 7 10.4 11 6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
  : s === 'error' ? <svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="7" fill="currentColor" opacity=".18" /><path d="M8 4.6v4M8 11v.4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
  : <svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeWidth="1.5" opacity=".5" /></svg>
const time = (s: number) => `${Math.floor(s / 60)}m ${String(Math.floor(s % 60)).padStart(2, '0')}s`

export function AppraisalCard({ name, hash, steps, grade, verdict }: { name: string; hash: string; steps: AppraisalStep[]; grade: string; verdict: ReactNode }) {
  const [active, setActive] = useState(reduced ? steps.length : 0)
  const [run, setRun] = useState(0)
  const [started, setStarted] = useState(reduced)
  const [ref, setRef] = useState<HTMLDivElement | null>(null)
  useEffect(() => {
    if (!ref || reduced) return
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setStarted(true); io.disconnect() } }, { threshold: .4 })
    io.observe(ref)
    return () => io.disconnect()
  }, [ref])
  useEffect(() => {
    if (!started || reduced || active >= steps.length) return
    const t = setTimeout(() => setActive(a => a + 1), 900)
    return () => clearTimeout(t)
  }, [active, started, run])
  const done = active >= steps.length
  const elapsed = useMemo(() => steps.slice(0, active).reduce((s, x) => s + x.seconds, 0), [active])
  const status = (i: number): StepStatus => i < active ? (steps[i].tone === 'bad' ? 'error' : 'success') : i === active && started ? 'loading' : 'pending'
  return (
    <div className="wm-card" ref={setRef}>
      <div className="wm-card-head">
        <div><small>Appraisal</small><b>{name}</b></div>
        <span className={`wm-status ${done ? 'ready' : 'building'}`}><i />{done ? 'Appraised' : 'Appraising'}</span>
      </div>
      <div className="wm-meta"><span>sealed {hash}</span><span className="num">{time(elapsed * 60)}</span></div>
      <div className="wm-segments">{steps.map((s, i) => <motion.i key={s.name} className={status(i)} initial={false} animate={{ opacity: status(i) === 'pending' ? .35 : 1 }} />)}</div>
      <ul className="wm-steps">
        {steps.map((s, i) => {
          const st = status(i)
          return (
            <li key={s.name} className={st}>
              <span className="wm-icon"><Icon s={st} /></span>
              <span className="wm-name">{s.name}<small>{s.detail}</small></span>
              <AnimatePresence mode="wait">
                {i < active && <motion.span key="r" className={`wm-tag ${s.tone ?? ''}`} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}>{s.result}</motion.span>}
              </AnimatePresence>
            </li>
          )
        })}
      </ul>
      <AnimatePresence>
        {done && (
          <motion.div className="wm-result" initial={reduced ? false : { opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} transition={{ type: 'spring', stiffness: 260, damping: 28 }}>
            <div><small>Grade</small><b className="grade">{grade}</b></div><p>{verdict}</p>
            <button className="wm-rerun" onClick={() => { setActive(0); setRun(r => r + 1) }}>Run again</button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/* ---------- Plan picker: the changeable pricing section; the chosen plan opens to show what it includes ---------- */
export type PlanOption = { id: string; name: string; description: string; price: string; per: string; badge?: string; features: string[] }
export function PlanPicker({ plans, defaultId, cta, href }: { plans: PlanOption[]; defaultId: string; cta: string; href: string }) {
  const [sel, setSel] = useState(defaultId)
  return (
    <div className="wm-plans">
      <div className="wm-plans-head"><b>Choose an appraisal</b><span>Priced per environment</span></div>
      <div className="wm-plan-list" role="radiogroup" aria-label="Appraisal plans">
        {plans.map(p => {
          const on = p.id === sel
          return (
            <motion.div key={p.id} layout className={`wm-plan${on ? ' on' : ''}`} role="radio" aria-checked={on} tabIndex={0} onClick={() => setSel(p.id)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSel(p.id) } }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}>
              <motion.div layout="position" className="wm-plan-top">
                <span className="wm-radio"><AnimatePresence>{on && <motion.i initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} />}</AnimatePresence></span>
                <span className="wm-plan-name">{p.name}{p.badge && <em>{p.badge}</em>}<small>{p.description}</small></span>
                <span className="wm-price">{p.price}<small>{p.per}</small></span>
              </motion.div>
              <AnimatePresence initial={false}>
                {on && (
                  <motion.ul key="f" className="wm-features" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} transition={{ type: 'spring', stiffness: 300, damping: 30 }}>
                    {p.features.map((f, i) => <motion.li key={f} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: .05 + i * .04 }}>{f}</motion.li>)}
                  </motion.ul>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>
      <a className="btn wm-continue" href={href}>{cta}</a>
    </div>
  )
}
