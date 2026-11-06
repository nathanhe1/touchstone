/* The homepage. The streak a metal leaves on a touchstone becomes every mark: silver breaks, gold holds. Each section takes its
   own ground from the palette and is held apart by lines. */
import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react'
import { Brand, Pill, RequestButton, Rating, reduced } from '../ui'
import { HowItWorks } from '../pages/Home'
import { AnimatePresence, motion, useInView, useMotionValue, useSpring, useTransform } from 'motion/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import '@fontsource-variable/instrument-sans/wght.css'
import scales from './img/goldsmith-scales.jpg'

gsap.registerPlugin(ScrollTrigger)
const Stone = lazy(() => import('./Stone'))
const ease = [.16, 1, .3, 1] as const
const webgl = () => { try { return !!document.createElement('canvas').getContext('webgl2') } catch { return false } }

function Rise({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  return <motion.div className={className} initial={reduced ? false : { opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-8% 0px' }} transition={{ duration: .8, delay, ease }}>{children}</motion.div>
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

const FACTS: [string, string][] = [['Check labels and graders', 'Wrong labels, and graders that pay for junk.'], ['Look for leaks', 'Test items hidden in the training material.'], ['Beat a placebo', 'Real answers and rewards against shuffled ones.']]

function Hero() {
  const ref = useRef<HTMLElement>(null), seen = useInView(ref)
  const [gl] = useState(webgl), [ready, setReady] = useState(false)
  return (
    <section className="hero" id="top" ref={ref}>
      <div className={`stone-still${ready ? ' off' : ''}`} aria-hidden="true"><i /></div>
      {gl && <Suspense fallback={null}><Stone active={seen} still={reduced} onReady={() => setReady(true)} /></Suspense>}
      <div className="in hero-in">
        <div className="hero-copy">
          <motion.h1 initial={reduced ? false : { opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease }}>Don't buy training material <em>blind.</em></motion.h1>
          <motion.p initial={reduced ? false : { opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: .12, ease }}>Touchstone appraises training datasets and RL environments before you pay for them. We check the labels, try to cheat the grader, look for leaked tests, and show you what we find.</motion.p>
          <motion.div className="hero-act" initial={reduced ? false : { opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: .22, ease }}>
            <RequestButton />
            <Pill href="#demo" tone="line">See the live demo</Pill>
          </motion.div>
        </div>
        <ul className="facts">
          {FACTS.map(([t, d], i) => (
            <motion.li key={t} initial={reduced ? false : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .8, delay: .35 + i * .09, ease }}><b>{t}</b><span>{d}</span></motion.li>
          ))}
        </ul>
      </div>
    </section>
  )
}

const PROBES = ['Hedge: right then wrong', 'Answer buried in junk', 'Near miss', 'Empty answer', 'Echo the prompt', 'Digit soup', 'Same shape, wrong content', "The model's own wrong answers", 'Fixed reply', 'Copy a prompt span']

function Ticker() {
  const row = PROBES.map(p => <span key={p}>{p}</span>)
  return <div className="ticker" aria-hidden="true"><div>{row}{row}</div></div>
}

function Why() {
  return (
    <section className="why">
      <div className="in why-in">
        <div className="why-text">
          <Rise><h2>Training material is expensive.</h2></Rise>
          <Rise delay={.07}><p className="statement">Finding out it didn't work is worse.</p></Rise>
          <Rise delay={.14}><p>A goldsmith tested metal before paying for it. A dataset or an RL environment deserves the same care. If the labels are wrong or the grader can be cheated, a model learns the wrong lesson, and you find out after the training run.</p></Rise>
        </div>
        <figure className="why-pic">
          <motion.div className="shutter" initial={reduced ? false : { clipPath: 'inset(0 100% 0 0)' }} whileInView={{ clipPath: 'inset(0 0% 0 0)' }} viewport={{ once: true, margin: '-12% 0px' }} transition={{ duration: 1.1, ease }}>
            <motion.img src={scales} width={930} height={570} loading="lazy" alt="A goldsmith's hand holding small scales above a counter of coins and weights" initial={reduced ? false : { scale: 1.12 }} whileInView={{ scale: 1 }} viewport={{ once: true, margin: '-12% 0px' }} transition={{ duration: 1.4, ease }} />
          </motion.div>
          <figcaption>Detail from A Goldsmith in his Shop, Petrus Christus, 1449.</figcaption>
        </figure>
      </div>
    </section>
  )
}

const PRESETS: [string, string][] = [['Hedge', '85 or 94'], ['Buried', 'qwer 85 zxcv'], ['Honest', '85'], ['Wrong', '94']]
const ANSWER = '85'
const seeded = (seed: number) => () => (seed = (seed * 16807) % 2147483647) / 2147483647

/* One rub across the slab. Paid rubs hold as gold; unpaid ones break up as silver and stop short. */
function Lane({ name, code, paid }: { name: string; code: string; paid: boolean }) {
  const r = seeded(name.length * 977 + 13)
  const strokes = Array.from({ length: 16 }, (_, i) => {
    const y = 8 + i * 1.9 + (r() - .5) * 1.2, a = 4 + r() * 14, b = 586 - r() * 22
    return <path key={i} d={`M${a} ${y} C 200 ${y - 5}, 400 ${y + 5}, ${b} ${y - 1}`} strokeWidth={.5 + r() * 1.2} opacity={.55 + r() * .45} />
  })
  return (
    <div className="lane">
      <div className="lane-name"><b>{name}</b><code>{code}</code></div>
      <svg viewBox="0 0 600 46" preserveAspectRatio="none" aria-hidden="true">
        <motion.g key={String(paid)} fill="none" strokeLinecap="round" stroke={paid ? '#e7c37a' : '#c0c6d0'} strokeDasharray={paid ? undefined : '18 26 7 31'} initial={reduced ? false : { clipPath: 'inset(0 100% 0 0)' }} animate={{ clipPath: `inset(0 ${paid ? 0 : 74}% 0 0)` }} transition={{ duration: paid ? .9 : .5, ease }}>{strokes}</motion.g>
      </svg>
      <strong className={paid ? 'paid' : ''}><Rolling value={paid ? 1 : 0} format={n => n.toFixed(2)} /></strong>
    </div>
  )
}

function Bench() {
  const [reply, setReply] = useState(PRESETS[0][1]), [held, setHeld] = useState(reduced)
  const box = useRef<HTMLDivElement>(null), seen = useInView(box, { margin: '-20% 0px' })
  const text = reply.trim()
  const loose = !!text && reply.includes(ANSWER), strict = text === ANSWER
  const stamp = !text ? null : loose && !strict ? ['False gold', 'bad'] : strict ? ['True gold', 'good'] : ['Nothing paid', 'none']
  const verdict = !text ? 'Type a reply to rub it on the stone.'
    : loose && !strict ? 'Full reward, and no answer given. The reply contains 85, so the vendor\'s grader never asks whether the model committed to it.'
    : strict ? 'Full reward from both graders. This one was earned.'
    : 'Neither grader paid. A wrong answer should earn nothing.'
  // The slab plays through its samples until someone takes over.
  useEffect(() => {
    if (held || !seen) return
    const t = setInterval(() => setReply(now => PRESETS[(PRESETS.findIndex(p => p[1] === now) + 1) % PRESETS.length][1]), 3800)
    return () => clearInterval(t)
  }, [held, seen])
  return (
    <section className="try" id="try">
      <div className="in">
        <Rise className="split-head">
          <h2>Try to cheat this grader.</h2>
          <p>This one is real and runs in your browser. It uses the same line of code as our sample environment: full reward if the answer appears anywhere in the reply.</p>
        </Rise>
        <div className="bench" ref={box}>
          <Rise className="slab">
            <div className="slab-top">
              <p className="task">Calculate 47 + 38.<span>Reply with only the number.</span></p>
              <div className="samples" role="group" aria-label="Example replies">
                {PRESETS.map(([name, value]) => <button key={name} type="button" aria-pressed={reply === value} onClick={() => { setHeld(true); setReply(value) }}>{name}</button>)}
              </div>
            </div>
            <label className="slab-reply"><span>The model replies</span>
              <input value={reply} onChange={e => { setHeld(true); setReply(e.target.value) }} onFocus={() => setHeld(true)} spellCheck={false} autoComplete="off" placeholder="Type a reply" />
            </label>
            <div className="lanes" data-ui>
              <Lane name="Vendor's grader" code="answer in reply" paid={loose} />
              <Lane name="Strict grader" code="reply == answer" paid={strict} />
              <AnimatePresence mode="wait">
                {stamp && <motion.span key={stamp[0]} className={`stamp ${stamp[1]}`} initial={reduced ? false : { opacity: 0, scale: 1.7, rotate: -14 }} animate={{ opacity: 1, scale: 1, rotate: -7 }} exit={{ opacity: 0 }} transition={{ delay: .35, type: 'spring', stiffness: 520, damping: 24 }}>{stamp[0]}</motion.span>}
              </AnimatePresence>
            </div>
            <p className="slab-verdict" aria-live="polite">{verdict}</p>
          </Rise>
          <Slip />
        </div>
      </div>
    </section>
  )
}

/* The assay slip: the engine's real figures for the sample environment. */
const LEDGER: [string, string, boolean][] = [['Hedged replies paid', '100%', true], ['Test items found in tasks', '0.0%', false], ['Overlap with public tasks', '3.2%', false], ['Value per task', '$0.00', true]]

function Slip() {
  const ref = useRef<HTMLDivElement>(null), seen = useInView(ref, { once: true, margin: '-12% 0px' })
  return (
    <motion.div className="slip" ref={ref} data-ui initial={reduced ? false : { opacity: 0, y: 34, rotate: 1.6 }} animate={seen ? { opacity: 1, y: 0, rotate: .5 } : {}} transition={{ duration: .9, ease }}>
      <div className="slip-head"><span className="mark"><Brand />Assay slip</span><span>Screened in 27 seconds</span></div>
      <p className="slip-name">QuickGrade Math Pack</p>
      <dl>{LEDGER.map(([k, v, bad], i) => (
        <motion.div key={k} initial={reduced ? false : { opacity: 0, x: -10 }} animate={seen ? { opacity: 1, x: 0 } : {}} transition={{ duration: .5, delay: .3 + i * .13, ease }}><dt>{k}</dt><i /><dd className={bad ? 'bad' : ''}>{v}</dd></motion.div>
      ))}</dl>
      <div className="slip-foot">
        <div><span>Grade</span><Rating grade="D" /></div>
        <motion.svg className="hallmark" viewBox="0 0 120 120" aria-hidden="true" initial={reduced ? false : { opacity: 0, scale: 1.8, rotate: -30 }} animate={seen ? { opacity: 1, scale: 1, rotate: -12 } : {}} transition={{ delay: 1, type: 'spring', stiffness: 420, damping: 20 }}>
          <circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" strokeWidth="2.5" /><circle cx="60" cy="60" r="38" fill="none" stroke="currentColor" strokeWidth="1.2" />
          <path id="hm" d="M60 60m-46 0a46 46 0 1 1 92 0a46 46 0 1 1 -92 0" fill="none" />
          <text fontSize="11.500" fontWeight="600" letterSpacing="2.2" fill="currentColor"><textPath href="#hm">GAMEABLE GRADER · NOT PRICED ·</textPath></text>
          <text x="60" y="73" textAnchor="middle" fontSize="38" fontWeight="500" fill="currentColor">D</text>
        </motion.svg>
      </div>
    </motion.div>
  )
}

/* The real run, typed out. After cult-ui's terminal-animation, much reduced. */
const CMD = 'touchstone appraise quickgrade --quick'
const OUT: [string, string?][] = [
  ['overlap: 0.0% of held-out items appear in the material'],
  ["grader check: worst exploit 'hedge: right then wrong' earns 100% reward", 'bad'],
  ['blocking problem found in screening; quick mode skips training'],
  ['Grade D | value $0.00/item | flags: gameable_grader', 'gold'],
]

function Console() {
  const ref = useRef<HTMLDivElement>(null), seen = useInView(ref, { once: true, margin: '-15% 0px' })
  const [typed, setTyped] = useState(reduced ? CMD.length : 0), [lines, setLines] = useState(reduced ? OUT.length : 0)
  useEffect(() => {
    if (!seen || reduced) return
    let n = 0, l = 0, show = 0
    const type = window.setInterval(() => {
      setTyped(++n)
      if (n < CMD.length) return
      clearInterval(type)
      show = window.setInterval(() => { setLines(++l); if (l >= OUT.length) clearInterval(show) }, 620)
    }, 26)
    return () => { clearInterval(type); clearInterval(show) }
  }, [seen])
  return (
    <section className="run">
      <div className="in run-in" ref={ref}>
        <Rise className="run-copy">
          <h2>A real appraisal runs hundreds of these.</h2>
          <p>Output from the Touchstone engine on our sample environment, on a Mac, with no training run.</p>
        </Rise>
        <div className="term" data-ui>
          <div className="term-bar"><i /><i /><i /><span>touchstone</span></div>
          <pre aria-label={`${CMD}. ${OUT.map(o => o[0]).join('. ')}`}><code>
            <span className="prompt">$ </span>{CMD.slice(0, typed)}{typed < CMD.length && <span className="caret" />}{'\n'}
            {OUT.slice(0, lines).map(([t, c]) => <span key={t} className={`ln ${c ?? ''}`}>{t}{'\n'}</span>)}
          </code></pre>
        </div>
      </div>
    </section>
  )
}

function How() {
  return (
    <section className="how">
      <div className="in">
        <Rise className="split-head"><h2>Small experiments, before the big spend.</h2><p>Screening takes under a minute. Small models take minutes. Larger ones, up to 1.7B parameters, take hours and only run when the decision needs them.</p></Rise>
        <div className="legacy how-story"><HowItWorks /></div>
        <Rise className="how-more"><Pill href="#demo">Open the live demo</Pill><Pill href="#product" tone="line">Read how the product works</Pill></Rise>
      </div>
    </section>
  )
}

const CHECKS: [string, string, boolean][] = [
  ['Can a model cheat for reward?', 'Known-wrong answers, hedges and junk go to the grader. Anything that pays gets flagged.', true],
  ['Are the labels right?', 'We recompute the worked answers and have a reference model re-solve a sample two ways. Confident disagreements count as wrong labels.', false],
  ['Did the test leak into training?', 'We compare the material with a private test suite, reworded copies included.', true],
  ['Does the gain beat a placebo?', 'Small open models train on the real answers or rewards, and on shuffled ones. Only the difference counts.', false],
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
    <section className="checks">
      <div className="in checks-in">
        <Rise><h2>What an appraisal checks.</h2></Rise>
        <div className="check-list">{CHECKS.map(([q, a, on]) => <Check key={q} q={q} a={a} on={on} />)}</div>
      </div>
    </section>
  )
}

const TILES: [number, string][] = [[21, 'RL environment cases exactly right'], [12, 'gameable graders caught'], [3, 'reworded test leaks caught'], [6, 'clean controls left unflagged']]

function Proof() {
  return (
    <section className="proof">
      <div className="in">
        <Rise className="split-head"><h2>A locked test.</h2><p>Frozen before scoring, run on RL environment test cases.</p></Rise>
      </div>
      <div className="in figs">
        {TILES.map(([n, label], i) => (
          <Rise className="fig" delay={.05 + i * .07} key={label}><b><Rolling value={n} format={v => `${Math.round(v)} of ${n}`} /></b><p>{label}</p></Rise>
        ))}
      </div>
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
      <g clipPath="url(#rub)" fill="none" stroke="#e7c37a" strokeLinecap="round">{lines}</g>
    </svg>
  )
}

function Close() {
  return (
    <section className="close">
      <Streak />
      <div className="in close-body">
        <Rise><h2>Know before you train.</h2></Rise>
        <Rise delay={.08}><p>Send us the dataset or environment you're about to buy. Neutral by design: we sell no training material, and we grade no material of our own.</p></Rise>
        <Rise delay={.14}><RequestButton tone="gold" /></Rise>
      </div>
    </section>
  )
}

export default function Sample() {
  // Section lines draw themselves in as they arrive.
  useEffect(() => {
    if (reduced) return
    const ctx = gsap.context(() => {
      gsap.utils.toArray<HTMLElement>('.draw').forEach(el => gsap.fromTo(el, { scaleX: 0 }, { scaleX: 1, duration: 1.2, ease: 'power3.out', scrollTrigger: { trigger: el, start: 'top 96%', once: true } }))
    })
    return () => ctx.revert()
  }, [])
  return <><Hero /><Ticker /><Why /><Bench /><Console /><How /><i className="draw" /><Checks /><Proof /><Close /></>
}
