import { useEffect, useState } from 'react'
import { AnimatePresence, motion, LayoutGroup } from 'motion/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Lenis from 'lenis'
import 'lenis/dist/lenis.css'
import Home from './pages/Home'
import { Company, Market, Pricing, Product, Report, Request } from './pages/Pages'
import Research from './pages/Research'
import { Privacy, Terms } from './pages/Legal'
import { Brand, RequestButton, reduced } from './ui'

// Plain #name hashes route between pages, which works on any static host and inside the artifact viewer.
const PAGES = { '': Home, product: Product, report: Report, market: Market, research: Research, pricing: Pricing, company: Company, request: Request, terms: Terms, privacy: Privacy }
type Route = keyof typeof PAGES
const NAV: [Route, string][] = [['product', 'Product'], ['report', 'Sample report'], ['research', 'Research'], ['market', 'Market'], ['pricing', 'Pricing'], ['company', 'Company']]
const TITLES: Record<Route, string> = { '': 'Touchstone', product: 'Product · Touchstone', report: 'Sample report · Touchstone', market: 'Market · Touchstone', research: 'Research · Touchstone', pricing: 'Pricing · Touchstone', company: 'Company · Touchstone', request: 'Request an appraisal · Touchstone', terms: 'Terms of use · Touchstone', privacy: 'Privacy policy · Touchstone' }
const read = (): Route => { const h = location.hash.slice(1); return (h in PAGES ? h : '') as Route }

export default function App() {
  const [route, setRoute] = useState<Route>(read)
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  // Smooth scrolling (Lenis) driven by GSAP's ticker so ScrollTrigger stays in sync.
  useEffect(() => {
    if (reduced) return
    const lenis = new Lenis({ lerp: .11 })
    lenis.on('scroll', ScrollTrigger.update)
    const tick = (t: number) => lenis.raf(t * 1000)
    gsap.ticker.add(tick); gsap.ticker.lagSmoothing(0)
    ;(window as any).__lenis = lenis
    return () => { gsap.ticker.remove(tick); lenis.destroy() }
  }, [])
  // A soft gold spotlight follows the cursor across whichever panel it is over.
  useEffect(() => {
    const move = (e: PointerEvent) => {
      const panel = (e.target as HTMLElement).closest?.('.panel') as HTMLElement | null
      if (!panel) return
      const r = panel.getBoundingClientRect()
      panel.style.setProperty('--mx', `${e.clientX - r.left}px`); panel.style.setProperty('--my', `${e.clientY - r.top}px`)
    }
    addEventListener('pointermove', move, { passive: true })
    return () => removeEventListener('pointermove', move)
  }, [])
  useEffect(() => {
    const onHash = () => { setRoute(read()); setOpen(false); const l = (window as any).__lenis; if (l) l.scrollTo(0, { immediate: true }); else window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior }) }
    const onScroll = () => setScrolled(scrollY > 8)
    addEventListener('hashchange', onHash); addEventListener('scroll', onScroll, { passive: true })
    return () => { removeEventListener('hashchange', onHash); removeEventListener('scroll', onScroll) }
  }, [])
  useEffect(() => { document.title = TITLES[route]; const t = setTimeout(() => ScrollTrigger.refresh(), 700); return () => clearTimeout(t) }, [route])
  const Page = PAGES[route]
  return (
    <>
      <header className={`nav${scrolled ? ' scrolled' : ''}`}>
        <div className="wrap">
          <a className="brand" href="#" aria-label="Touchstone home"><Brand />touchstone</a>
          <LayoutGroup id="nav">
            <nav className={`nav-links${open ? ' open' : ''}`} aria-label="Main">
              {NAV.map(([key, label]) => (
                <a key={key} href={`#${key}`} aria-current={route === key ? 'page' : undefined}>
                  {route === key && <motion.span layoutId="nav-pill" className="nav-pill" transition={{ type: 'spring', stiffness: 380, damping: 32 }} />}
                  {label}
                </a>
              ))}
            </nav>
          </LayoutGroup>
          <RequestButton />
          <button className="menu" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(o => !o)}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true"><path d="M3 6h12M3 12h12" /></svg>
          </button>
        </div>
      </header>
      <AnimatePresence mode="wait">
        <motion.main key={route} initial={reduced ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={reduced ? undefined : { opacity: 0, y: -8 }} transition={{ duration: .35, ease: [.16, 1, .3, 1] }}>
          <Page />
        </motion.main>
      </AnimatePresence>
      <footer className="footer">
        <div className="wrap">
          <div><a className="brand" href="#"><Brand />touchstone</a><p>Independent appraisal for AI training material. We test it before you buy it.</p></div>
          <div><h4>product</h4><a className="f" href="#product">How it works</a><a className="f" href="#report">Sample report</a><a className="f" href="#research">Research and sources</a></div>
          <div><h4>company</h4><a className="f" href="#market">Market</a><a className="f" href="#pricing">Pricing</a><a className="f" href="#company">About and roadmap</a></div>
          <div><h4>start</h4><a className="f" href="#request">Request an appraisal</a><a className="f" href="#terms">Terms of use</a><a className="f" href="#privacy">Privacy policy</a></div>
        </div>
      </footer>
    </>
  )
}
