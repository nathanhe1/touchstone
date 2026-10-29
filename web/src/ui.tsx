import { useEffect, useRef, type ReactNode } from 'react'
import { motion } from 'motion/react'
import { animate } from 'animejs'
import { REQUEST_FORM_URL } from './data'

export const reduced = typeof window !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches
/* The one motion curve and its durations, shared with styles.css. */
export const ease = [.2, 0, 0, 1] as const
export const DUR = { quick: .2, standard: .3, slow: .45 }

export const Brand = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M3 8 8 3h8l5 5v8l-5 5H8l-5-5z" fill="#2f343b" />
    <path d="M13.5 6 12 11l2.5 2-2 5" fill="none" stroke="#dcaa4f" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

export function RequestButton({ label = 'Request an appraisal', secondary = false }: { label?: string; secondary?: boolean }) {
  const external = Boolean(REQUEST_FORM_URL)
  return (
    <a className={`btn${secondary ? ' secondary' : ''}`} href={external ? REQUEST_FORM_URL : '#request'} {...(external ? { target: '_blank', rel: 'noopener' } : {})}>
      {label}
    </a>
  )
}

/** Fades content up 8px once it reaches the screen; visible immediately when motion is off. */
export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  if (reduced) return <div className={className}>{children}</div>
  return (
    <motion.div className={className} initial={{ opacity: 0, y: 8 }} whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '0px 0px -10% 0px' }} transition={{ duration: DUR.standard, delay, ease }}>
      {children}
    </motion.div>
  )
}

/** Counts the number inside a formatted string up from zero when it scrolls into view. */
export function Count({ value, className }: { value: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    const el = ref.current
    const m = value.match(/^(\D*?)([\d,.]+)(.*)$/)
    if (!el || !m || reduced) return
    const [, pre, num, post] = m
    const target = parseFloat(num.replace(/,/g, '')), dec = (num.split('.')[1] || '').length
    const io = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return
      io.disconnect()
      const state = { v: 0 }
      animate(state, {
        v: target, duration: 900, ease: 'outQuart',
        onUpdate: () => { el.textContent = pre + state.v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: num.includes(',') }) + post },
      })
    })
    io.observe(el)
    return () => io.disconnect()
  }, [value])
  return <span ref={ref} className={className}>{value}</span>
}

/** The one container: a bordered panel with a mono label row. */
export function Panel({ title, meta, children, className = '' }: { title: ReactNode; meta?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <div className={`panel ${className}`}>
      <div className="panel-head"><span className="title">{title}</span>{meta && <span className="meta">{meta}</span>}</div>
      {children}
    </div>
  )
}

export function Faq({ items }: { items: [string, string][] }) {
  return (
    <div className="faq">
      {items.map(([q, a]) => <details key={q}><summary>{q}</summary><p>{a}</p></details>)}
    </div>
  )
}

export function Close({ title, text }: { title: ReactNode; text: string }) {
  return (
    <section className="close">
      <div className="wrap">
        <Reveal><h2>{title}</h2><p className="lede">{text}</p></Reveal>
        <div className="actions"><RequestButton /><a className="btn secondary" href="#report">See a sample report</a></div>
      </div>
    </section>
  )
}

/** Grade as a credit-style A–F strip, never a lone letter. */
export function Rating({ grade, compact = false }: { grade: string; compact?: boolean }) {
  const tone = grade === 'A' || grade === 'B' ? 'good' : 'bad'
  return (
    <span className={`rating${compact ? ' compact' : ''}`} role="img" aria-label={grade === '—' ? 'Not graded: free comparison set' : `Grade ${grade} on a scale from A to F`}>
      {['A', 'B', 'C', 'D', 'F'].map(letter => <i key={letter} className={letter === grade ? `on ${tone}` : ''}>{letter}</i>)}
    </span>
  )
}
