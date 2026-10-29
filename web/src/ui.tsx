import { useEffect, useRef, type ReactNode } from 'react'
import { motion } from 'motion/react'
import { animate } from 'animejs'
import { REQUEST_FORM_URL } from './data'

export const reduced = typeof window !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches

export const Arrow = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 8h10M9 4l4 4-4 4" /></svg>
)
export const Check = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3.5 8.5 6.5 11.5 12.5 4.5" /></svg>
)
export const Alert = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="M8 2.5 14 13H2z" strokeLinejoin="round" /><path d="M8 6.5v3M8 11.3v.2" /></svg>
)
export const Plus = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="M8 3v10M3 8h10" /></svg>
)
export const Brand = () => (
  <svg viewBox="0 0 42 42" aria-hidden="true">
    <defs><linearGradient id="stone" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#8a8f96" /><stop offset=".5" stopColor="#3a3f45" /><stop offset="1" stopColor="#16191c" /></linearGradient></defs>
    <path d="M5 13 14 5l13 2 10 10-3 15-12 6L8 32 3 22z" fill="url(#stone)"  />
    <path d="m24 8 3 10-4 5 5 3-3 9" fill="none" stroke="#e2b45a" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.4" />
  </svg>
)

export function RequestButton({ label = 'Request an appraisal' }: { label?: string }) {
  const external = Boolean(REQUEST_FORM_URL)
  return (
    <a className="btn" href={external ? REQUEST_FORM_URL : '#request'} {...(external ? { target: '_blank', rel: 'noopener' } : {})}>
      {label}<Arrow />
    </a>
  )
}

/** Fades content up once it reaches the screen; it is visible by default if motion is off. */
export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  if (reduced) return <div className={className}>{children}</div>
  return (
    <motion.div className={className} initial={{ opacity: 0, y: 24, filter: 'blur(6px)' }} whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      viewport={{ once: true, margin: '0px 0px -10% 0px' }} transition={{ duration: .9, delay, ease: [.16, 1, .3, 1] }}>
      {children}
    </motion.div>
  )
}

/** Counts the number inside a formatted string up from zero with anime.js when it scrolls into view. */
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
        v: target, duration: 1400, ease: 'outExpo',
        onUpdate: () => { el.textContent = pre + state.v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: num.includes(',') }) + post },
      })
    })
    io.observe(el)
    return () => io.disconnect()
  }, [value])
  return <span ref={ref} className={className}>{value}</span>
}

/** A dashboard panel: header with title and meta, then the body. */
export function Panel({ title, meta, children, className = '' }: { title: ReactNode; meta?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <div className={`panel ${className}`}>
      <div className="panel-head"><span className="title">{title}</span>{meta && <span className="meta">{meta}</span>}</div>
      {children}
    </div>
  )
}

/** The sky behind the hero, page heads and the close: CSS gradients with slow drifting clouds. */
export const Sky = () => <div className="sky" aria-hidden="true"><i /><i /><i /><i /><i /></div>

export function Faq({ items }: { items: [string, string][] }) {
  return (
    <div className="faq">
      {items.map(([q, a]) => (
        <details key={q}><summary>{q}<Plus /></summary><p>{a}</p></details>
      ))}
    </div>
  )
}

export function Close({ title, text }: { title: ReactNode; text: string }) {
  return (
    <section className="close">
      <Sky />
      <div className="wrap">
        <Reveal><h2>{title}</h2><p className="lede">{text}</p>
          <div className="actions"><RequestButton /><a className="btn secondary" href="#report">See a sample report</a></div></Reveal>
      </div>
    </section>
  )
}

/** Grade as a credit-style A–F scale; the highlight slides between letters when a layoutId is given. */
export function Rating({ grade, compact = false, layoutId }: { grade: string; compact?: boolean; layoutId?: string }) {
  const good = grade === 'A' || grade === 'B'
  return (
    <span className={`rating${compact ? ' compact' : ''}`} role="img" aria-label={grade === '—' ? 'No grade: free comparison set' : `Grade ${grade} on a scale from A to F`}>
      {['A', 'B', 'C', 'D', 'F'].map(letter => (
        <i key={letter} className={letter === grade ? 'on' : ''}>
          {letter === grade && (layoutId
            ? <motion.span layoutId={layoutId} className={`hl ${good ? 'good' : 'bad'}`} transition={{ type: 'spring', stiffness: 420, damping: 30 }} />
            : <span className={`hl ${good ? 'good' : 'bad'}`} />)}
          {letter}
        </i>
      ))}
    </span>
  )
}
