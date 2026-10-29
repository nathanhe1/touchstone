import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import Home from './pages/Home'
import { Company, Market, Pricing, Product, Report, Request } from './pages/Pages'
import Research from './pages/Research'
import { Privacy, Terms } from './pages/Legal'
import { Brand, DUR, RequestButton, ease, reduced } from './ui'

// Plain #name hashes route between pages, which works on any static host and inside the artifact viewer.
const PAGES = { '': Home, product: Product, report: Report, market: Market, research: Research, pricing: Pricing, company: Company, request: Request, terms: Terms, privacy: Privacy }
type Route = keyof typeof PAGES
const NAV: [Route, string][] = [['product', 'Product'], ['report', 'Sample report'], ['research', 'Research'], ['market', 'Market'], ['pricing', 'Pricing'], ['company', 'Company']]
const TITLES: Record<Route, string> = { '': 'Touchstone: independent appraisal for RL environments', product: 'Product · Touchstone', report: 'Sample report · Touchstone', market: 'Market · Touchstone', research: 'Research · Touchstone', pricing: 'Pricing · Touchstone', company: 'Company · Touchstone', request: 'Request an appraisal · Touchstone', terms: 'Terms of use · Touchstone', privacy: 'Privacy policy · Touchstone' }
const read = (): Route => { const h = location.hash.slice(1); return (h in PAGES ? h : '') as Route }

export default function App() {
  const [route, setRoute] = useState<Route>(read)
  const [open, setOpen] = useState(false)
  useEffect(() => {
    const onHash = () => { setRoute(read()); setOpen(false); window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior }) }
    addEventListener('hashchange', onHash)
    return () => removeEventListener('hashchange', onHash)
  }, [])
  useEffect(() => { document.title = TITLES[route] }, [route])
  const Page = PAGES[route]
  return (
    <>
      <header className="nav">
        <div className="wrap">
          <a className="brand" href="#" aria-label="Touchstone home"><Brand />touchstone</a>
          <nav className={`nav-links${open ? ' open' : ''}`} aria-label="Main">
            {NAV.map(([key, label]) => <a key={key} href={`#${key}`} aria-current={route === key ? 'page' : undefined}>{label}</a>)}
          </nav>
          <RequestButton />
          <button className="menu" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(o => !o)}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d={open ? 'M3 3l10 10M13 3 3 13' : 'M2 5h12M2 11h12'} /></svg>
          </button>
        </div>
      </header>
      <AnimatePresence mode="wait">
        <motion.main key={route} initial={reduced ? false : { opacity: 0 }} animate={{ opacity: 1 }} exit={reduced ? undefined : { opacity: 0 }} transition={{ duration: DUR.quick, ease }}>
          <Page />
        </motion.main>
      </AnimatePresence>
      <footer className="footer">
        <div className="wrap">
          <div><a className="brand" href="#"><Brand />touchstone</a><p>Independent appraisal for AI training material. We test it before you buy it.</p></div>
          <div><h4>Product</h4><a className="f" href="#product">How it works</a><a className="f" href="#report">Sample report</a><a className="f" href="#research">Research</a></div>
          <div><h4>Company</h4><a className="f" href="#market">Market</a><a className="f" href="#pricing">Pricing</a><a className="f" href="#company">About</a></div>
          <div><h4>Start</h4><a className="f" href="#request">Request an appraisal</a></div>
          <div><h4>Legal</h4><a className="f" href="#terms">Terms of use</a><a className="f" href="#privacy">Privacy policy</a></div>
          <div className="legalline"><span>© {new Date().getFullYear()} Touchstone</span><a href="#terms">Terms</a><a href="#privacy">Privacy</a></div>
        </div>
      </footer>
    </>
  )
}
