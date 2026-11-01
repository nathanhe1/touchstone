/* One-page sample of a new Touchstone direction. On this page, the streak a metal leaves on a touchstone becomes every mark:
   silver breaks, gold holds. The live thing is a real grader the visitor can try to cheat. */
import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react'
import { motion, useInView, useMotionValue, useSpring, useTransform } from 'motion/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import '@fontsource-variable/inter/opsz.css'
import './sample.css'
import scales from './img/goldsmith-scales.jpg'

gsap.registerPlugin(ScrollTrigger)
const Stone = lazy(() => import('./Stone'))
const reduced = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches
const ease = [.16, 1, .3, 1] as const
const REQUEST = 'https://claude.ai/artifact/McLyEufkHwxkX3UovCR1gH#request'

const webgl = () => { try { return !!document.createElement('canvas').getContext('webgl2') } catch { return false } }

function Rise({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  return <motion.div className={className} initial={reduced ? false : { opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-8% 0px' }} transition={{ duration: .8, delay, ease }}>{children}</motion.div>
}

/* Adapted from cult-ui's rolling-number: a spring runs the figure to its value. */
function Rolling({ value, format }: { value: number; format: (n: number) => string }) {
  const ref = useRef<HTMLSpanElement>(null), seen = useInView(ref, { once: true })
  const start = useMotionValue(reduced ? value : 0)
  const spring = useSpring(start, { mass: .8, stiffness: 75, damping: 15 })
  const text = useTransform(spring, format)
  useEffect(() => { if (seen) start.set(value) }, [seen, value, start])
  return <motion.span ref={ref}>{text}</motion.span>
}

/* The site's button: cult-ui's texture-button (a lit edge around a soft fill) in gold, without Tailwind. */
function Button({ href, children, quiet }: { href: string; children: ReactNode; quiet?: boolean }) {
  return <a className={`tbtn${quiet ? ' quiet' : ''}`} href={href}><span>{children}</span></a>
}

function Nav() {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const on = () => setScrolled(scrollY > 24)
    on(); addEventListener('scroll', on, { passive: true })
    return () => removeEventListener('scroll', on)
  }, [])
  return (
    <header className={`bar${scrolled ? ' solid' : ''}`}>
      <a className="mark" href="#top">touchstone</a>
      <nav aria-label="Main">
        <a href="#try">Try it</a><a href="#checks">What we check</a><a href="#proof">Proof</a><a href="#how">How it works</a>
      </nav>
      <Button href={REQUEST}>Request an audit</Button>
    </header>
  )
}

function Hero() {
  const ref = useRef<HTMLElement>(null), seen = useInView(ref)
  const [gl] = useState(webgl), [ready, setReady] = useState(false)
  return (
    <section className="hero" id="top" ref={ref}>
      <div className={`stone-still${ready ? ' off' : ''}`} aria-hidden="true"><i /></div>
      {gl && <Suspense fallback={null}><Stone active={seen} still={reduced} onReady={() => setReady(true)} /></Suspense>}
      <div className="hero-copy">
        <motion.h1 initial={reduced ? false : { opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease }}>Don't buy training material <em>blind.</em></motion.h1>
        <motion.p initial={reduced ? false : { opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: .12, ease }}>Touchstone audits RL environments before you pay for them. We try to cheat the grader, look for leaked tests, and show you what we find.</motion.p>
        <motion.div className="hero-act" initial={reduced ? false : { opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: .22, ease }}>
          <Button href={REQUEST}>Request an audit</Button>
          <Button href="#try" quiet>Try to cheat a grader</Button>
        </motion.div>
      </div>
    </section>
  )
}

function Why() {
  return (
    <section className="why">
      <div className="why-text">
        <Rise><h2>Training material is expensive.</h2></Rise>
        <Rise delay={.07}><p className="statement">Finding out it didn't work is worse.</p></Rise>
        <Rise delay={.14}><p>A goldsmith tested metal before paying for it. An RL environment deserves the same care. If its grader can be cheated, a model can earn reward without learning the task, and you find out after the training run.</p></Rise>
      </div>
      <figure className="why-pic">
        <motion.div className="shutter" initial={reduced ? false : { clipPath: 'inset(0 100% 0 0)' }} whileInView={{ clipPath: 'inset(0 0% 0 0)' }} viewport={{ once: true, margin: '-12% 0px' }} transition={{ duration: 1.1, ease }}>
          <motion.img src={scales} width={930} height={570} loading="lazy" alt="A goldsmith's hand holding small scales above a counter of coins and weights" initial={reduced ? false : { scale: 1.12 }} whileInView={{ scale: 1 }} viewport={{ once: true, margin: '-12% 0px' }} transition={{ duration: 1.4, ease }} />
        </motion.div>
        <figcaption>Detail from A Goldsmith in his Shop, Petrus Christus, 1449.</figcaption>
      </figure>
    </section>
  )
}

const PRESETS: [string, string][] = [['Hedge', '85 or 94'], ['Buried', 'qwer 85 zxcv'], ['Honest', '85'], ['Wrong', '94']]
const ANSWER = '85'

function Meter({ name, code, reward }: { name: string; code: string; reward: number }) {
  return (
    <div className={`meter${reward ? ' paid' : ''}`}>
      <div><b>{name}</b><code>{code}</code></div>
      <strong><Rolling value={reward} format={n => n.toFixed(2)} /></strong>
      <i style={{ transform: `scaleX(${reward})` }} />
    </div>
  )
}

function Cheat() {
  const [reply, setReply] = useState(PRESETS[0][1])
  const text = reply.trim()
  const loose = text && reply.includes(ANSWER) ? 1 : 0, strict = text === ANSWER ? 1 : 0
  const verdict = !text ? 'Type a reply to see what each grader pays.'
    : loose && !strict ? 'The loose grader paid in full and the strict one paid nothing. A model can learn to exploit that gap.'
    : strict ? 'A right answer earns full reward from both. That is how a grader should behave.'
    : 'No reward from either. A wrong answer should earn nothing.'
  return (
    <section className="try" id="try">
      <Rise className="try-head">
        <h2>Try to cheat this grader.</h2>
        <p>This one is real and runs in your browser. It uses the same line of code as the sample environment below: full reward if the answer appears anywhere in the reply.</p>
      </Rise>
      <div className="try-grid" data-ui>
        <div className="plate">
          <p className="task">Calculate 47 + 38. Reply with only the number.</p>
          <label htmlFor="reply">Model's reply</label>
          <textarea id="reply" rows={2} value={reply} onChange={e => setReply(e.target.value)} spellCheck={false} />
          <div className="presets" role="group" aria-label="Example replies">
            {PRESETS.map(([name, value]) => <button key={name} type="button" aria-pressed={reply === value} onClick={() => setReply(value)}>{name}</button>)}
          </div>
        </div>
        <div className="result" aria-live="polite">
          <Meter name="Vendor's grader" code="answer in reply" reward={loose} />
          <Meter name="Strict grader" code="reply == answer" reward={strict} />
          <p>{verdict}</p>
        </div>
      </div>
    </section>
  )
}

/* The engine's real output on the sample environment, typed out. After cult-ui's terminal-animation, much reduced. */
const CMD = 'touchstone appraise quickgrade --quick'
const OUT: [string, string?][] = [
  ['overlap: 0.0% of held-out items appear in the material'],
  ["grader audit: worst exploit 'hedge: right then wrong' earns 100% reward", 'bad'],
  ['blocking problem found in screening; quick mode skips training'],
  ['Grade D | value $0.00/item | flags: gameable_grader', 'gold'],
]
const PROBES: [string, number][] = [['Hedge: right then wrong', 100], ['Hedge: wrong or right', 100], ['Answer buried in junk', 100], ['Near miss', 0], ['Empty answer', 0]]

function Console() {
  const ref = useRef<HTMLDivElement>(null), seen = useInView(ref, { once: true, margin: '-15% 0px' })
  const [typed, setTyped] = useState(reduced ? CMD.length : 0), [lines, setLines] = useState(reduced ? OUT.length : 0)
  useEffect(() => {
    if (!seen || reduced) return
    let n = 0, l = 0
    const type = setInterval(() => {
      setTyped(++n)
      if (n < CMD.length) return
      clearInterval(type)
      const show = setInterval(() => { setLines(++l); if (l >= OUT.length) clearInterval(show) }, 620)
    }, 26)
    return () => clearInterval(type)
  }, [seen])
  return (
    <section className="run">
      <Rise><h2>The real audit runs hundreds of these.</h2></Rise>
      <div className="run-grid" ref={ref} data-ui>
        <pre aria-label={`${CMD}. ${OUT.map(o => o[0]).join('. ')}`}><code>
          <span className="prompt">$ </span>{CMD.slice(0, typed)}{typed < CMD.length && <span className="caret" />}{'\n'}
          {OUT.slice(0, lines).map(([t, c]) => <span key={t} className={`ln ${c ?? ''}`}>{t}{'\n'}</span>)}
        </code></pre>
        <table>
          <caption>Reward earned, 400 sampled tasks</caption>
          <tbody>{PROBES.map(([p, v]) => <tr key={p}><th scope="row">{p}</th><td className={v ? 'bad' : ''}>{v}%</td></tr>)}</tbody>
        </table>
      </div>
      <Rise delay={.1}><p className="note">Output from the Touchstone engine on our sample environment. 27 seconds on a Mac, no training run.</p></Rise>
    </section>
  )
}

const CHECKS: [string, string, boolean][] = [
  ['Can a model cheat for reward?', 'Known-wrong answers, hedges and junk go to the grader. Anything that pays gets flagged.', true],
  ['Did the test leak into training?', 'We compare the material with a private test suite, reworded copies included.', true],
  ['Does the gain beat a placebo?', 'Small open models train on the real rewards and on shuffled ones. Only the difference counts.', false],
  ['Is it already public?', 'We measure overlap with free public material.', false],
]

function Check({ q, a, on: first }: { q: string; a: string; on: boolean }) {
  const [on, setOn] = useState(first)
  return (
    <div className={`check${on ? ' on' : ''}`}>
      <button type="button" role="switch" aria-checked={on} onClick={() => setOn(!on)}>
        <span className="q">{q}</span><span className="sw" data-ui><i /></span>
      </button>
      <motion.div className="a" initial={false} animate={{ height: on ? 'auto' : 0, opacity: on ? 1 : 0 }} transition={{ duration: reduced ? 0 : .35, ease }}><p>{a}</p></motion.div>
    </div>
  )
}

function Checks() {
  return (
    <section className="checks" id="checks">
      <Rise className="checks-head"><h2>What the audit checks.</h2><p>Four questions, answered before anyone commits to a large training run.</p></Rise>
      <div>{CHECKS.map(([q, a, on]) => <Check key={q} q={q} a={a} on={on} />)}</div>
    </section>
  )
}

const TILES: [number, string][] = [[21, 'RL environment cases exactly right'], [12, 'gameable graders caught'], [3, 'reworded test leaks caught'], [6, 'clean controls left unflagged']]

function Proof() {
  return (
    <section className="proof" id="proof">
      <Rise className="tile gold"><h2>A locked test.</h2><p>Frozen before scoring, run on RL environment test cases.</p></Rise>
      <div className="rows">
        {TILES.map(([n, label], i) => (
          <Rise className="row" delay={.05 + i * .06} key={label}>
            <b><Rolling value={n} format={v => `${Math.round(v)} of ${n}`} /></b><p>{label}</p>
          </Rise>
        ))}
      </div>
    </section>
  )
}

const STAGES: [string, string, number][] = [
  ['Under a minute', 'First we attack the grader and look for leaks.', 14],
  ['Minutes', 'Then we train a small model against a placebo.', 30],
  ['Hours, when it matters', 'Then we go up to 1.7B parameters.', 56],
]

function How() {
  return (
    <section className="how" id="how">
      <Rise><h2>Small experiments, before the big spend.</h2></Rise>
      <div className="stages" data-ui>
        {STAGES.map(([time, text, grow], i) => (
          <motion.div key={time} style={{ flexGrow: grow, transformOrigin: 'left' }} initial={reduced ? false : { scaleX: .2, opacity: 0 }} whileInView={{ scaleX: 1, opacity: 1 }} viewport={{ once: true, margin: '-10% 0px' }} transition={{ duration: .9, delay: i * .1, ease }}>
            <b>{time}</b><p>{text}</p>
          </motion.div>
        ))}
      </div>
      <Rise delay={.1}><p className="note">A blocking problem ends a quick audit early, so nobody pays to train on an environment that can't be trusted.</p></Rise>
    </section>
  )
}

/* The motif at full width: scrolling rubs the gold streak across the page. */
function Streak() {
  const ref = useRef<SVGSVGElement>(null)
  useEffect(() => {
    if (reduced || !ref.current) return
    const rect = ref.current.querySelector('rect')!
    const t = gsap.fromTo(rect, { attr: { width: 0 } }, { attr: { width: 1600 }, ease: 'none', scrollTrigger: { trigger: ref.current, start: 'top 92%', end: 'top 30%', scrub: .4 } })
    return () => { t.scrollTrigger?.kill(); t.kill() }
  }, [])
  const lines = Array.from({ length: 26 }, (_, i) => {
    const y = 34 + i * 2.6 + Math.sin(i * 7) * 1.4
    return <path key={i} d={`M${10 + (i * 37) % 60} ${y} C 500 ${y - 28}, 1100 ${y + 24}, ${1590 - (i * 53) % 90} ${y - 6}`} strokeWidth={.8 + (i * 13 % 7) / 3.4} opacity={.5 + (i * 11 % 5) / 10} />
  })
  return (
    <svg className="streak" ref={ref} viewBox="0 0 1600 110" preserveAspectRatio="none" aria-hidden="true">
      <defs><clipPath id="rub"><rect x="0" y="0" width={reduced ? 1600 : 0} height="110" /></clipPath></defs>
      <g clipPath="url(#rub)" fill="none" stroke="#e2b45a" strokeLinecap="round">{lines}</g>
    </svg>
  )
}

function Close() {
  return (
    <section className="close" id="request">
      <Streak />
      <div className="close-body">
        <Rise><h2>Know before you train.</h2></Rise>
        <Rise delay={.08}><p>Send us the environment you're about to buy. Neutral by design: we sell no training material, and we grade no material of our own.</p></Rise>
        <Rise delay={.14}><Button href={REQUEST}>Request an audit</Button></Rise>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="foot">
      <p className="huge" aria-hidden="true">touchstone</p>
      <div className="foot-row">
        <nav aria-label="Footer"><a href="#try">Try it</a><a href="#checks">What we check</a><a href="#proof">Proof</a><a href="#how">How it works</a></nav>
        <p>Painting: Petrus Christus, A Goldsmith in his Shop, 1449, The Metropolitan Museum of Art, CC0, via Wikimedia Commons.</p>
        <p>© 2026 Touchstone</p>
      </div>
    </footer>
  )
}

const GROUNDS: [string, string][] = [['silver', 'Silver'], ['pewter', 'Pewter'], ['graphite', 'Graphite']]

function Grounds() {
  const [ground, setGround] = useState(() => { try { return localStorage.getItem('ground') || 'silver' } catch { return 'silver' } })
  useEffect(() => { document.documentElement.dataset.ground = ground; try { localStorage.setItem('ground', ground) } catch { /* private window */ } }, [ground])
  return <div className="grounds" role="group" aria-label="Background colour">{GROUNDS.map(([id, name]) => <button key={id} type="button" aria-pressed={ground === id} onClick={() => setGround(id)}>{name}</button>)}</div>
}

export default function Sample() {
  return <><Grounds /><Nav /><main><Hero /><Why /><Cheat /><Console /><Checks /><Proof /><How /><Close /></main><Footer /></>
}
