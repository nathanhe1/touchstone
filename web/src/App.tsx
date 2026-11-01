import { useEffect, useState } from 'react'
import Home from './pages/Home'
import Method from './pages/Method'
import Pricing from './pages/Pricing'
import Company from './pages/Company'
import Request from './pages/Request'
import Demo from './pages/Demo'
import { Privacy, Terms } from './pages/Legal'
import { Brand, RequestButton } from './ui'

// Plain #name hashes route between pages, which works on any static host and inside the artifact viewer.
const PAGES = { '': Home, method: Method, demo: Demo, pricing: Pricing, company: Company, request: Request, terms: Terms, privacy: Privacy }
type Route = keyof typeof PAGES
const MOVED: Record<string, Route> = { product: 'method', research: 'method', report: 'demo', market: 'company' }
const NAV: [Route, string][] = [['method', 'Method'], ['demo', 'Live demo'], ['pricing', 'Pricing'], ['company', 'Company']]
const TITLES: Record<Route, string> = { '': 'Touchstone', method: 'Method · Touchstone', demo: 'Live demo · Touchstone', pricing: 'Pricing · Touchstone', company: 'Company · Touchstone', request: 'Request an audit · Touchstone', terms: 'Terms of use · Touchstone', privacy: 'Privacy policy · Touchstone' }
const read = (): Route => { const h = location.hash.slice(1); return MOVED[h] ?? (h in PAGES ? h as Route : '') }

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
      <header className="nav dark">
        <div className="wrap">
          <a className="brand" href="#" aria-label="Touchstone home"><Brand />Touchstone</a>
          <nav className={open ? 'open' : ''} aria-label="Main">
            {NAV.map(([key, label]) => <a key={key} href={`#${key}`} aria-current={route === key ? 'page' : undefined}>{label}</a>)}
          </nav>
          <RequestButton />
          <button className="menu" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(o => !o)}>
            <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true"><path d="M3 6h12M3 12h12" /></svg>
          </button>
        </div>
      </header>
      <main><Page /></main>
      <footer className="footer dark">
        <div className="wrap">
          <p><a className="brand" href="#"><Brand />Touchstone</a><span>Independent audit and appraisal for RL environments.</span></p>
          <nav aria-label="Footer">
            {NAV.map(([key, label]) => <a key={key} href={`#${key}`}>{label}</a>)}
            <a href="#request">Request an audit</a><a href="#terms">Terms</a><a href="#privacy">Privacy</a>
          </nav>
        </div>
      </footer>
    </>
  )
}
