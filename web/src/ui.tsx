import { useEffect, useRef, useState, type ReactNode } from 'react'
import { REQUEST_FORM_URL } from './data'

export const reduced = typeof window !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches

export const Arrow = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 8h10M9 4l4 4-4 4" /></svg>
)

/* The mark: a dark stone with one gold streak. */
export const Brand = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M3.5 8 8 3.5l8.5.8 4.5 5-1.3 8.2-6.3 3.2-8.6-1.7L2.5 13z" fill="currentColor" />
    <path d="M7 14.5c3-2.6 6.4-3.6 10-3.4" fill="none" stroke="var(--gold)" strokeWidth="2" strokeLinecap="round" />
  </svg>
)

export function RequestButton({ label = 'Request an audit', ghost = false }: { label?: string; ghost?: boolean }) {
  const external = Boolean(REQUEST_FORM_URL)
  return <a className={`btn${ghost ? ' ghost' : ''}`} href={external ? REQUEST_FORM_URL : '#request'} {...(external ? { target: '_blank', rel: 'noopener' } : {})}>{label}</a>
}

export function Faq({ items }: { items: [string, string][] }) {
  return <div className="faq">{items.map(([q, a]) => <details key={q}><summary>{q}</summary><p>{a}</p></details>)}</div>
}

/* The grade as an A to F scale, never a lone letter. */
export function Rating({ grade }: { grade: string }) {
  return (
    <span className="rating" role="img" aria-label={grade === '—' ? 'No grade' : `Grade ${grade} on a scale from A to F`}>
      {['A', 'B', 'C', 'D', 'F'].map(l => <i key={l} className={l === grade ? `on ${l === 'A' || l === 'B' ? 'good' : 'bad'}` : ''}>{l}</i>)}
    </span>
  )
}

export function Close({ title, text }: { title: ReactNode; text: string }) {
  return (
    <section className="close dark">
      <div className="wrap">
        <h2>{title}</h2>
        <p>{text}</p>
        <div className="actions"><RequestButton /><a className="btn ghost" href="#demo">Try the live demo</a></div>
      </div>
    </section>
  )
}

/** Header shared by every subpage. */
export function PageHead({ title, text, children }: { title: ReactNode; text: string; children?: ReactNode }) {
  return (
    <header className="page-head dark">
      <div className="wrap"><h1>{title}</h1><p className="lede">{text}</p>{children}</div>
    </header>
  )
}

/** True once the element has come onto the screen. */
export function useSeen<T extends Element>() {
  const ref = useRef<T>(null)
  const [seen, setSeen] = useState(reduced)
  useEffect(() => {
    if (reduced || !ref.current) return
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect() } }, { threshold: .3 })
    io.observe(ref.current)
    return () => io.disconnect()
  }, [])
  return [ref, seen] as const
}
