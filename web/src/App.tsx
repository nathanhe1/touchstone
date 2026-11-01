import { useEffect, useState } from 'react'
import { AnimatePresence, motion, LayoutGroup } from 'motion/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Lenis from 'lenis'
import 'lenis/dist/lenis.css'
import Home from './sample/Sample'
import { Company, Market, Pricing, Product, Report, Request } from './pages/Pages'
import Research from './pages/Research'
import { Privacy, Terms } from './pages/Legal'
import Demo from './pages/Demo'
import { Brand, RequestButton, reduced } from './ui'

// Plain #name hashes route between pages, which works on any static host and inside the artifact viewer.
const PAGES = { '': Home, product: Product, report: Report, market: Market, research: Research, pricing: Pricing, company: Company, request: Request, terms: Terms, privacy: Privacy, demo: Demo }
type Route = keyof typeof PAGES
const NAV: [Route, string][] = [['demo', 'Live demo'], ['product', 'Product'], ['report', 'Sample report'], ['research', 'Research'], ['market', 'Market'], ['pricing', 'Pricing'], ['company', 'Company']]
const TITLES: Record<Route, string> = { '': 'Touchstone', product: 'Product · Touchstone', report: 'Sample report · Touchstone', market: 'Market · Touchstone', research: 'Research · Touchstone', pricing: 'Pricing · Touchstone', company: 'Company · Touchstone', request: 'Request an audit · Touchstone', terms: 'Terms of use · Touchstone', privacy: 'Privacy policy · Touchstone', demo: 'Live demo · Touchstone' }
const read = (): Route => { const h = location.hash.slice(1); return (h in PAGES ? h : '') as Route }

export default function App() {
  const [route, setRoute] = useState<Route>(read)
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  // Smooth scrolling (Lenis) driven by GSAP's ticker so ScrollTrigger stays in sync.
  useEffect(() => {
    if (reduced) return
    // Light smoothing: heavier values feel like input lag.
    const lenis = new Lenis({ lerp: .2 })
    lenis.on('scroll', ScrollTrigger.update)
    const tick = (t: number) => lenis.raf(t * 1000)
    gsap.ticker.add(tick); gsap.ticker.lagSmoothing(0)
    ;(window as any).__lenis = lenis
    return () => { gsap.ticker.remove(tick); lenis.destroy() }
  }, [])
  // A soft gold spotlight follows the cursor across whichever panel it is over.
  useEffect(() => {
    // At most one update per frame, however fast the pointer moves.
    let frame = 0, last: PointerEvent | null = null
    const apply = () => {
      frame = 0
      const e = last!, panel = (e.target as HTMLElement).closest?.('.panel') as HTMLElement | null
      if (!panel) return
      const r = panel.getBoundingClientRect()
      panel.style.setProperty('--mx', `${e.clientX - r.left}px`); panel.style.setProperty('--my', `${e.clientY - r.top}px`)
    }
    const move = (e: PointerEvent) => { last = e; if (!frame) frame = requestAnimationFrame(apply) }
    addEventListener('pointermove', move, { passive: true })
    return () => { removeEventListener('pointermove', move); cancelAnimationFrame(frame) }
  }, [])
  useEffect(() => {
    const onHash = () => {
      const h = location.hash.slice(1), el = h && !(h in PAGES) ? document.getElementById(h) : null
      if (el) { const l = (window as any).__lenis; if (l) l.scrollTo(el, { offset: -72 }); else el.scrollIntoView(); return }
      setRoute(read()); setOpen(false); const l = (window as any).__lenis; if (l) l.scrollTo(0, { immediate: true }); else window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior }) }
    const onScroll = () => setScrolled(scrollY > 8)
    addEventListener('hashchange', onHash); addEventListener('scroll', onScroll, { passive: true })
    return () => { removeEventListener('hashchange', onHash); removeEventListener('scroll', onScroll) }
  }, [])
  useEffect(() => { document.title = TITLES[route]; const t = setTimeout(() => ScrollTrigger.refresh(), 700); return () => clearTimeout(t) }, [route])
  // ScrollTrigger stores pixel positions, so anything that changes the page height above a trigger makes it fire late.
  useEffect(() => {
    let timer = 0, height = 0
    const ro = new ResizeObserver(() => {
      const next = document.documentElement.scrollHeight
      if (next === height) return
      height = next
      clearTimeout(timer)
      timer = window.setTimeout(() => ScrollTrigger.refresh(), 150)
    })
    ro.observe(document.body)
    document.fonts?.ready.then(() => ScrollTrigger.refresh())
    return () => { ro.disconnect(); clearTimeout(timer) }
  }, [])
  const Page = PAGES[route]
  return (
    <>
      <header className="bar">
        <a className="mark" href="#" aria-label="Touchstone home"><Brand />touchstone</a>
        <LayoutGroup id="nav">
          <nav className={open ? 'open' : ''} aria-label="Main">
            {NAV.map(([key, label]) => (
              <a key={key} href={`#${key}`} aria-current={route === key ? 'page' : undefined}>
                {label}{route === key && <motion.span layoutId="nav-line" className="nav-line" transition={{ type: 'spring', stiffness: 380, damping: 32 }} />}
              </a>
            ))}
            <a className="nav-req" href="#request">Request an audit</a>
          </nav>
        </LayoutGroup>
        <RequestButton />
        <button className="menu" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(o => !o)}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true"><path d="M3 6h12M3 12h12" /></svg>
        </button>
      </header>
      <AnimatePresence mode="wait">
        <motion.main key={route} className={route ? 'legacy' : undefined} initial={reduced ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={reduced ? undefined : { opacity: 0, y: -8 }} transition={{ duration: .35, ease: [.16, 1, .3, 1] }}>
          <Page />
        </motion.main>
      </AnimatePresence>
      <footer className="foot">
        <div className="in foot-in">
          <div className="foot-cols">
            <div><a className="mark" href="#"><Brand />touchstone</a><p>Independent audit and appraisal for AI training material. We test it before you buy it.</p></div>
            <div><h4>Product</h4><a href="#demo">Live demo</a><a href="#product">How it works</a><a href="#report">Sample report</a><a href="#research">Research and sources</a></div>
            <div><h4>Company</h4><a href="#market">Market</a><a href="#pricing">Pricing</a><a href="#company">About and roadmap</a></div>
            <div><h4>Start</h4><a href="#request">Request an audit</a><a href="#terms">Terms of use</a><a href="#privacy">Privacy policy</a></div>
          </div>
        </div>
      </footer>
    </>
  )
}
