import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion, LayoutGroup } from 'motion/react'
import { useSprings, animated } from '@react-spring/web'
import { animate, createTimeline, stagger } from 'animejs'
import NumberFlow from '@number-flow/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import LiquidGlass from 'liquid-glass-react'
import { data, vendors, base, truth, signed, pct, money, params, gradeClass, type Env } from '../data'
import { Alert, Check, Close, Count, Gradient, Panel, Rating, Reveal, RequestButton, reduced } from '../ui'
import { Caught, Evidence, Exploits, Paradox, Section } from './Sections'

gsap.registerPlugin(ScrollTrigger)
const ease = [.16, 1, .3, 1] as const

/* ---------- Hero: a real training run where reward climbs and new-problem accuracy falls ---------- */
function RunChart() {
  const env = vendors.find(e => e.id === 'quickgrade_arith') ?? vendors[0]
  const rung = env.rungs[truth]
  const W = 960, H = 300, L = 36, B = 26
  const x = (i: number, n: number) => L + (i / (n - 1)) * (W - L - 8)
  const y = (pctv: number) => 8 + (1 - pctv / 100) * (H - B - 8)
  const reward = rung.curve.map(v => v * 100)
  const accuracy = reward.map((_, i) => rung.heldout_before + (rung.heldout_after - rung.heldout_before) * (i / (reward.length - 1)))
  const path = (vals: number[]) => vals.map((v, i) => `${i ? 'L' : 'M'}${x(i, vals.length).toFixed(1)} ${y(v).toFixed(1)}`).join(' ')
  const area = (vals: number[]) => `${path(vals)} L${x(vals.length - 1, vals.length)} ${H - B} L${L} ${H - B} Z`
  const stepRef = useRef<HTMLElement>(null)
  const rewardRef = useRef<HTMLElement>(null)
  const accRef = useRef<HTMLElement>(null)
  const [done, setDone] = useState(reduced)
  const box = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState<{ x: number; i: number } | null>(null)
  const onMove = (e: React.PointerEvent) => {
    const r = box.current!.getBoundingClientRect()
    const fx = ((e.clientX - r.left) / r.width * W - L) / (W - L - 8)
    if (fx < 0 || fx > 1) return setHover(null)
    setHover({ x: e.clientX - r.left, i: Math.round(fx * (reward.length - 1)) })
  }

  useEffect(() => {
    if (reduced) return
    const s = { t: 0 }
    const last = reward.length - 1
    const a = animate(s, {
      t: 1, duration: 2600, delay: 500, ease: 'inOutQuad',
      onUpdate: () => {
        const i = s.t * last, lo = Math.floor(i), f = i - lo
        const r = reward[lo] + ((reward[Math.min(lo + 1, last)] - reward[lo]) * f)
        const acc = accuracy[lo] + ((accuracy[Math.min(lo + 1, last)] - accuracy[lo]) * f)
        if (stepRef.current) stepRef.current.textContent = Math.round(s.t * 1000).toLocaleString('en-US')
        if (rewardRef.current) rewardRef.current.textContent = `${r.toFixed(1)}%`
        if (accRef.current) accRef.current.textContent = `${acc.toFixed(1)}%`
      },
      onComplete: () => setDone(true),
    })
    return () => { a.pause() }
  }, [])

  const grid = [0, 25, 50, 75, 100]
  const draw = (delay: number) => (reduced ? {} : { initial: { pathLength: 0 }, animate: { pathLength: 1 }, transition: { duration: 2.6, delay, ease: 'easeInOut' as const } })
  return (
    <Panel className="run" title={<>run · <span style={{ color: 'var(--ink)' }}>{env.name}</span></>} meta={<span className="live">appraised</span>}>
      <div className="run-chart panel-body" ref={box} onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        {hover && (<>
          <span className="xhair" style={{ left: hover.x }} />
          <span className="xtip" style={{ left: Math.min(hover.x + 12, (box.current?.clientWidth ?? 600) - 170) }}>
            step {Math.round(hover.i / (reward.length - 1) * 1000)}
            <b className="reward">reward {reward[hover.i].toFixed(1)}%</b><b className="transfer">new problems {accuracy[hover.i].toFixed(1)}%</b>
          </span>
        </>)}
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Training reward climbs from ${reward[0].toFixed(0)}% to ${reward[reward.length - 1].toFixed(0)}% while accuracy on new problems falls from ${accuracy[0].toFixed(1)}% to ${accuracy[accuracy.length - 1].toFixed(1)}%`}>
          {grid.map(g => (<g key={g}><line className="grid-line" x1={L} x2={W - 8} y1={y(g)} y2={y(g)} /><text className="axis-text" x={L - 8} y={y(g) + 4} textAnchor="end">{g}</text></g>))}
          <text className="axis-text" x={L} y={H - 6}>step 0</text><text className="axis-text" x={W - 8} y={H - 6} textAnchor="end">1,000</text>
          <defs>
            <linearGradient id="fill-r" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#b9bfc8" /><stop offset="1" stopColor="#b9bfc8" stopOpacity="0" /></linearGradient>
            <linearGradient id="fill-t" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#e2b45a" /><stop offset="1" stopColor="#e2b45a" stopOpacity="0" /></linearGradient>
          </defs>
          <motion.path d={area(reward)} fill="url(#fill-r)" className="curve-fill" initial={reduced ? false : { opacity: 0 }} animate={{ opacity: .14 }} transition={{ delay: 2.4, duration: .8 }} />
          <motion.path d={path(reward)} className="curve" stroke="var(--reward)" {...draw(.5)} />
          <motion.path d={path(accuracy)} className="curve" stroke="var(--transfer)" {...draw(.5)} />
          {done && <>
            <text className="end-label" x={W - 8} y={y(reward[reward.length - 1]) - 10} textAnchor="end" fill="var(--reward)">{reward[reward.length - 1].toFixed(1)}%</text>
            <text className="end-label" x={W - 8} y={y(accuracy[accuracy.length - 1]) + 22} textAnchor="end" fill="var(--transfer)">{accuracy[accuracy.length - 1].toFixed(1)}%</text>
          </>}
        </svg>
        <AnimatePresence>
          {done && (
            <motion.div className="verdict-wrap" initial={reduced ? false : { opacity: 0, scale: .9, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} transition={{ type: 'spring', stiffness: 220, damping: 18 }}>
              <LiquidGlass mouseContainer={box} displacementScale={48} blurAmount={0.08} saturation={140} aberrationIntensity={1.4} elasticity={0.18} cornerRadius={16} padding="14px 18px" style={{ position: 'absolute', top: '27%', left: '56%' }}>
                <Verdict env={env} />
              </LiquidGlass>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      <p className="verdict-inline"><b className="bad">Don't buy at this price.</b> {pct(env.hackability.score)} of non-answers still scored.</p>
      <div className="legend" style={{ padding: '0 20px 16px' }}><span><i style={{ background: 'var(--reward)' }} />reward on its own grader</span><span><i style={{ background: 'var(--transfer)' }} />accuracy on new problems</span></div>
      <div className="run-foot">
        <div><small>step</small><b ref={stepRef} className="num">{reduced ? '1,000' : '0'}</b></div>
        <div><small>reward</small><b ref={rewardRef} className="num reward">{reduced ? `${reward[reward.length - 1].toFixed(1)}%` : `${reward[0].toFixed(1)}%`}</b></div>
        <div><small>new problems</small><b ref={accRef} className="num transfer">{reduced ? `${accuracy[accuracy.length - 1].toFixed(1)}%` : `${accuracy[0].toFixed(1)}%`}</b></div>
      </div>
    </Panel>
  )
}

const RUNS = [
  { name: 'coding-agent-v3', exploit: '2 exploits found', overlap: '31% already free', gain: '−0.4 pts', verdict: 'Not worth full price', tone: 'bad' },
  { name: 'math-reasoning-v1', exploit: 'no exploits', overlap: '6% already free', gain: '+4.1 pts', verdict: 'Worth buying', tone: 'good' },
]
function Console() {
  const [run, setRun] = useState(0)
  const body = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = body.current
    if (!el || reduced) return
    const lines = el.querySelectorAll('[data-l]'), bars = el.querySelectorAll('.cbar i')
    let timer = 0
    const tl = createTimeline({ onComplete: () => { timer = window.setTimeout(() => setRun(r => (r + 1) % RUNS.length), 2600) } })
    tl.set(lines, { opacity: 0, translateY: 6 }).set(bars, { scaleX: 0 })
    lines.forEach((line, i) => {
      tl.add(line, { opacity: 1, translateY: 0, duration: 320, ease: 'outQuad' }, i ? '+=330' : 400)
      if (line.classList.contains('cbars')) tl.add(bars, { scaleX: 1, duration: 800, delay: stagger(120), ease: 'outQuad' })
    })
    tl.add(el.querySelector('.stamp')!, { scale: [1.7, 1], rotate: [-12, -2], duration: 600, ease: 'outBack(2.2)' }, '-=300')
    return () => { tl.pause(); clearTimeout(timer) }
  }, [run])
  const r = RUNS[run]
  return (
    <Panel title="touchstone · appraisal" meta="live" className="console">
      <div className="console-body" ref={body} key={run}>
        <p className="cl" data-l><span className="p">›</span>seal <b>{r.name}</b><span className="r good">sealed</span></p>
        <p className="cl" data-l><span className="p">›</span>train 4 small models</p>
        <div className="cbars" data-l>{[['S', 38], ['M', 56], ['L', 74], ['XL', 92]].map(([s, w]) => <div key={s}><span>{s}</span><i style={{ width: `${w}%` }} /></div>)}</div>
        <p className="cl" data-l><span className="p">›</span>probe the grader<span className={`r ${r.tone}`}>{r.exploit}</span></p>
        <p className="cl" data-l><span className="p">›</span>check overlap<span className="r">{r.overlap}</span></p>
        <p className="cl" data-l><span className="p">›</span>forecast at your scale<span className={`r ${r.tone}`}>{r.gain}</span></p>
        <span className={`stamp ${r.tone}`} data-l>{r.verdict}</span>
      </div>
    </Panel>
  )
}

function Verdict({ env }: { env: Env }) {
  return (
    <span className="verdict">
      <small>touchstone verdict</small>
      <b className="bad">Don't buy at this price</b>
      <small>{pct(env.hackability.score)} of non-answers still scored</small>
    </span>
  )
}

/* ---------- Proof: reward against real change, for every demo environment ---------- */
function Proof() {
  const envs = [...vendors, base]
  const limit = 8
  return (
    <Panel title="six environments · largest model" meta="appraised">
      <div className="proof">
        <div className="proof-row head"><span>environment</span><span>change on new problems, pts</span><span style={{ textAlign: 'right' }}>reward</span><span style={{ textAlign: 'right' }}>change</span></div>
        {envs.map((e, i) => {
          const r = e.rungs[truth].env_reward_after, c = e.actual_at_truth, share = Math.min(Math.abs(c) / limit, 1) * 50
          return (
            <Reveal key={e.id} delay={i * .05}>
              <div className="proof-row">
                <span className="proof-name">{e.name}</span>
                <div className="proof-track">
                  <motion.span className="proof-link" style={{ left: c < 0 ? `${50 - share}%` : '50%', width: `${share}%`, background: c < 0 ? 'var(--bad)' : 'var(--good)' }}
                    initial={reduced ? false : { scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }} transition={{ duration: 1, delay: .2 + i * .06, ease }} />
                  <span className="proof-dot" style={{ left: `${50 + (c / limit) * 50}%`, background: c < 0 ? 'var(--bad)' : 'var(--good)' }} />
                </div>
                <span className="num reward" style={{ textAlign: 'right' }}>{pct(r)}</span>
                <span className={`num ${c < 0 ? 'bad' : 'good'}`} style={{ textAlign: 'right' }}>{signed(c)}</span>
              </div>
            </Reveal>
          )
        })}
      </div>
    </Panel>
  )
}

/* ---------- How it works: scroll drives the steps; each stage has its own motion ---------- */
const STEPS = [
  ['Seal', 'The vendor uploads the environment to a sealed sandbox. You never see their tasks, only the results.'],
  ['Train small', 'Small open models train on it at four sizes with one fixed recipe. Cheap, fast and repeatable.'],
  ['Measure', 'The models face private problems they never trained on, and we try to fool the grader.'],
  ['Forecast and price', 'We predict the gain at your model size and put a fair price on each task.'],
] as const

function Spheres() {
  const sizes = Object.entries(data.ladder)
  const biggest = Math.max(...sizes.map(([, v]) => v))
  const [springs, api] = useSprings(sizes.length, i => ({ from: { scale: 0, y: 30 }, to: { scale: 1, y: 0 }, delay: 120 * i, config: { tension: 210, friction: 12 } }))
  return (
    <div className="atoms">
      {springs.map((s, i) => {
        const d = Math.sqrt(sizes[i][1] / biggest) * 150
        return (
          <div className="atom" key={sizes[i][0]}>
            <animated.div className="sphere" style={{ width: d, height: d, ...s }}
              onPointerEnter={() => api.start(j => (j === i ? { scale: 1.12, config: { tension: 320, friction: 10 } } : {}))}
              onPointerLeave={() => api.start(j => (j === i ? { scale: 1 } : {}))} />
            <b>{sizes[i][0]}</b><small>{params(sizes[i][1])}</small>
          </div>
        )
      })}
    </div>
  )
}

function Stage({ index }: { index: number }) {
  const env = vendors[0]
  if (index === 0) return (
    <div className="vault">
      {['task 001', 'task 002', 'task 003', 'task 004'].map((t, i) => (
        <motion.div key={t} className="vault-row" initial={{ opacity: 0, x: -40 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * .08, type: 'spring', stiffness: 260, damping: 22 }}>
          <span>{t}</span><span className="lock">sealed</span>
        </motion.div>
      ))}
      <motion.div className="num dim" style={{ fontSize: 12, marginTop: 8, textAlign: 'center' }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: .5 }}>sha256 {env.sha256.slice(0, 20)}…</motion.div>
    </div>
  )
  if (index === 1) return <Spheres />
  if (index === 2) {
    const rows: [string, string, number, string][] = [
      ['Better on new problems', `${signed(env.actual_at_truth)} pts`, .62, 'var(--transfer)'],
      ['Reward won by exploits', pct(env.hackability.score), Math.max(env.hackability.score, .02), 'var(--bad)'],
      ['Already in free data', pct(env.redundancy.public_overlap), env.redundancy.public_overlap, 'var(--reward)'],
    ]
    return (
      <div className="bars">
        {rows.map(([label, value, w, c], i) => (
          <div className="bar-row" key={label}><span>{label}</span><b>{value}</b>
            <div className="track"><motion.i style={{ background: c, width: `${w * 100}%` }} initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: .1 + i * .12, duration: 1, ease }} /></div>
          </div>
        ))}
      </div>
    )
  }
  return (
    <div className="price">
      <svg viewBox="0 0 400 170" aria-hidden="true">
        <motion.polygon points="250,86 380,34 380,90 250,106" fill="#e2b45a22" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: .8 }} />
        <motion.path d="M40 132 L130 118 L250 96" fill="none" stroke="var(--ink)" strokeWidth="2.5" strokeLinecap="round" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: .9, ease }} />
        <motion.path d="M250 96 L380 62" fill="none" stroke="var(--transfer)" strokeWidth="2.5" strokeDasharray="6 6" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: .9 }} />
        {[[40, 132], [130, 118], [250, 96]].map(([cx, cy], i) => <motion.circle key={i} cx={cx} cy={cy} r="6" fill="var(--ink)" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: .2 + i * .2, type: 'spring' }} />)}
        <motion.circle cx="380" cy="62" r="9" fill="var(--transfer)" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 1.1, type: 'spring', stiffness: 300, damping: 10 }} />
        <text className="axis-text" x="40" y="162">small runs</text><text className="axis-text" x="380" y="162" textAnchor="end">your model size</text>
      </svg>
      <motion.div className="tag" initial={{ opacity: 0, y: 12, rotate: -4 }} animate={{ opacity: 1, y: 0, rotate: 0 }} transition={{ delay: 1.2, type: 'spring', stiffness: 260, damping: 16 }}>
        <b>{money(env.fair_value_per_task)}</b><small>fair value per task</small>
      </motion.div>
    </div>
  )
}

function HowItWorks() {
  const [active, setActive] = useState(0)
  const steps = useRef<(HTMLLIElement | null)[]>([])
  const bar = useRef<HTMLElement>(null)
  const list = useRef<HTMLOListElement>(null)
  useEffect(() => {
    const triggers = steps.current.map((el, i) => el && ScrollTrigger.create({ trigger: el, start: 'top 55%', end: 'bottom 55%', onToggle: self => self.isActive && setActive(i) }))
    const progress = list.current && ScrollTrigger.create({ trigger: list.current, start: 'top 55%', end: 'bottom 55%', scrub: true,
      onUpdate: self => { if (bar.current) bar.current.style.transform = `scaleX(${self.progress})` } })
    return () => { triggers.forEach(t => t?.kill()); progress?.kill() }
  }, [])
  return (
    <div className="story">
      <ol className="story-steps" ref={list}>
        {STEPS.map(([title, text], i) => (
          <li key={title} ref={el => { steps.current[i] = el }}>
            <div className={`story-step${active === i ? ' on' : ''}`} onClick={() => steps.current[i]?.scrollIntoView({ behavior: 'smooth', block: 'center' })}>
              <h3 style={{ fontSize: 30 }}>{title}</h3><p>{text}</p>
            </div>
          </li>
        ))}
      </ol>
      <div className="story-stage">
        <Panel title={STEPS[active][0].toLowerCase()} meta={`${active + 1} / 4`}>
          <div className="stage-body">
            <AnimatePresence mode="wait">
              <motion.div key={active} className="stage" initial={{ opacity: 0, y: 16, filter: 'blur(6px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} exit={{ opacity: 0, y: -12, filter: 'blur(6px)' }} transition={{ duration: .4, ease }}>
                <Stage index={active} />
              </motion.div>
            </AnimatePresence>
          </div>
          <div className="progress"><i ref={bar} style={{ transform: 'scaleX(0)' }} /></div>
        </Panel>
      </div>
    </div>
  )
}

/* ---------- One report: switch environment, every number re-reads ---------- */
const verdict = (e: Env) =>
  e.is_public_baseline ? 'The free baseline every purchase is compared against.'
  : e.hackability.score >= .2 ? 'Fix the grader before anyone buys this.'
  : e.redundancy.public_overlap >= .5 ? 'Mostly already free. Not worth the asking price.'
  : e.actual_at_truth < 0 ? 'Don\'t buy: the model gets worse at new problems.'
  : `Worth buying at up to ${money(e.fair_value_per_task)} a task.`

export function ReportSample() {
  const envs = [...vendors, base]
  const [id, setId] = useState(envs[0].id)
  const [phase, setPhase] = useState(4)
  const [runId, setRunId] = useState(0)
  const env = envs.find(e => e.id === id)!
  const rung = env.rungs[truth]
  useEffect(() => {
    if (reduced || runId === 0) return
    setPhase(0)
    const timers = [1, 2, 3, 4].map(k => window.setTimeout(() => setPhase(k), k * 520))
    return () => timers.forEach(clearTimeout)
  }, [runId])
  const pick = (next: string) => { setId(next); setRunId(n => n + 1) }
  const pctF = { style: 'percent', maximumFractionDigits: 0 } as const
  const ptsF = { signDisplay: 'always', minimumFractionDigits: 1, maximumFractionDigits: 1 } as const
  const usd = { style: 'currency', currency: 'USD', maximumFractionDigits: 0 } as const
  const rows: [string, string, number, React.ReactNode, string][] = [
    ['Learns the environment', 'Reward on its own tasks, before → after', 1, <><NumberFlow value={rung.env_reward_before} format={pctF} /> → <NumberFlow value={rung.env_reward_after} format={pctF} /></>, ''],
    ['Better on new problems', 'The number that matters', 2, <NumberFlow value={env.actual_at_truth} format={ptsF} suffix=" pts" />, env.actual_at_truth < 0 ? 'bad' : 'good'],
    ['Reward won by exploits', 'Non-answers that still scored', 2, <NumberFlow value={env.hackability.score} format={pctF} />, env.hackability.score >= .2 ? 'bad' : ''],
    ['Already in free data', 'Overlap with public sets', 2, <NumberFlow value={env.redundancy.public_overlap} format={pctF} />, env.redundancy.public_overlap >= .5 ? 'bad' : ''],
    ['Forecast at the largest size', `90% range ${signed(env.forecast.lo)} to ${signed(env.forecast.hi)}`, 3, <NumberFlow value={env.forecast.forecast} format={ptsF} suffix=" pts" />, ''],
    ['Fair value per task', 'Compared with free practice', 4, <NumberFlow value={env.fair_value_per_task} format={usd} />, 'transfer'],
  ]
  const stages = ['Seal', 'Train', 'Measure', 'Price']
  return (
    <Panel title="appraisal report" meta="pick an environment to run it">
      <LayoutGroup id="report-tabs">
        <div className="tabs" role="tablist" aria-label="Sample environment">
          {envs.map(e => (
            <button key={e.id} className="tab" role="tab" aria-selected={e.id === id} onClick={() => pick(e.id)}>
              {e.id === id && <motion.span layoutId="tab-pill" className="tab-pill" transition={{ type: 'spring', stiffness: 380, damping: 32 }} />}
              <span>{e.name.replace(' (free)', '')}</span>
            </button>
          ))}
        </div>
      </LayoutGroup>
      <div className="runbar" aria-live="polite">
        {stages.map((st, i) => (
          <span key={st} className={phase > i ? 'done' : phase === i ? 'active' : ''}>
            {phase > i ? <Check /> : <svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="5" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg>}{st}
          </span>
        ))}
      </div>
      <div className="report">
        <div className="metrics">
          {rows.map(([label, sub, stage, value, tone]) => (
            <div className="metric" key={label}>
              <span>{label}</span><small>{sub}</small>
              <b className={`num ${tone}`}>{phase >= stage ? value : <span className="pending" />}</b>
            </div>
          ))}
        </div>
        <div className="report-side">
          <div>
            <LayoutGroup id="rating"><Rating grade={phase >= 4 ? env.grade : '—'} layoutId="rating-hl" /></LayoutGroup>
            <span className="rating-cap">{env.grade === '—' ? 'free comparison set, not graded' : phase >= 4 ? `grade ${env.grade}` : 'grading…'}</span>
            <h3 style={{ marginTop: 22 }}>{env.name}</h3>
            <p className="dim" style={{ margin: '6px 0 0', fontSize: 14 }}>{env.redundancy.n_tasks.toLocaleString('en-US')} tasks · sealed {env.sha256.slice(0, 10)}</p>
          </div>
          <div className="by-size" aria-label="Change on new problems at each model size">
            <small>change on new problems, by model size</small>
            {Object.keys(data.ladder).map((k, i) => {
              const g = env.rungs[k].heldout_after - env.rungs[k].heldout_before
              const w = phase >= 2 ? Math.min(Math.abs(g) / 12, 1) * 50 : 0
              return (
                <div className="bs-row" key={k}>
                  <span>{k}</span>
                  <div className="bs-track"><motion.i className={g < 0 ? 'neg' : 'pos'} animate={{ width: `${w}%` }} transition={{ type: 'spring', stiffness: 140, damping: 20, delay: i * .06 }} /></div>
                  <b className={`num ${g < 0 ? 'bad' : 'good'}`}>{phase >= 2 ? signed(g) : '·'}</b>
                </div>
              )
            })}
          </div>
          {phase >= 4 && <motion.p key={id + 'v'} className="verdict-line" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>{verdict(env)}</motion.p>}
          <AnimatePresence mode="wait">
            {phase >= 4 && (
              <motion.ul key={id} className="flags" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                {(env.flags.length ? env.flags : ['No appraisal flags']).map((f, i) => (
                  <motion.li key={f} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * .08 }}>{env.flags.length ? <span className="bad"><Alert /></span> : <span className="good"><Check /></span>}{f}</motion.li>
                ))}
              </motion.ul>
            )}
          </AnimatePresence>
        </div>
      </div>
    </Panel>
  )
}

/* ---------- Neutral by design: tasks flow in, only numbers flow out ---------- */
function Beam() {
  const [narrow, setNarrow] = useState(typeof window !== 'undefined' && innerWidth < 900)
  const [hot, setHot] = useState<string | null>(null)
  useEffect(() => { const on = () => setNarrow(innerWidth < 900); addEventListener('resize', on); return () => removeEventListener('resize', on) }, [])
  const pos = narrow ? { vendor: [50, 12], core: [50, 50], buyer: [50, 88] } : { vendor: [13, 50], core: [50, 50], buyer: [87, 50] }
  const line = (a: number[], b: number[]) => `M${a[0] * 10} ${a[1] * (narrow ? 5.2 : 3.4)} L${b[0] * 10} ${b[1] * (narrow ? 5.2 : 3.4)}`
  const node = (key: 'vendor' | 'core' | 'buyer', title: string, sub: string) => (
    <div className={`node${key === 'core' ? ' core' : ''}`} style={{ left: `${pos[key][0]}%`, top: `${pos[key][1]}%` }}
      onPointerEnter={() => setHot(key)} onPointerLeave={() => setHot(null)}>
      <motion.div style={{ display: 'grid', gap: 4 }} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ type: 'spring', stiffness: 200, damping: 16, delay: key === 'core' ? 0 : .2 }}>
        <b>{title}</b><small>{sub}</small>
      </motion.div>
    </div>
  )
  const H = narrow ? 520 : 340
  return (
    <div className="beam" aria-label="The vendor's tasks go into Touchstone's sealed sandbox; only results reach the buyer">
      <svg viewBox={`0 0 1000 ${H}`} preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="pulse" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2={narrow ? 0 : 1000} y2={narrow ? H : 0}>
            <stop offset="0" stopColor="#e2b45a" stopOpacity="0" /><stop offset=".5" stopColor="#e2b45a" /><stop offset="1" stopColor="#e2b45a" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[[pos.vendor, pos.core, 'vendor'], [pos.core, pos.buyer, 'buyer']].map(([a, b, k]) => (
          <g key={k as string}>
            <path d={line(a as number[], b as number[])} stroke="var(--line-2)" strokeWidth="1.5" fill="none" vectorEffect="non-scaling-stroke" />
            <motion.path d={line(a as number[], b as number[])} stroke={k === 'vendor' ? 'var(--reward)' : 'var(--transfer)'} strokeWidth={hot === k || hot === 'core' ? 3 : 2} fill="none" vectorEffect="non-scaling-stroke" strokeLinecap="round"
              initial={{ pathLength: .18, pathOffset: 0 }} animate={reduced ? { pathOffset: .4 } : { pathOffset: [0, 1] }} transition={{ duration: 2.2, repeat: Infinity, ease: 'linear', delay: k === 'buyer' ? 1.1 : 0 }} />
          </g>
        ))}
      </svg>
      {node('vendor', 'Vendor', 'uploads tasks')}
      {node('core', 'Touchstone', 'sealed sandbox')}
      {node('buyer', 'You', 'see results only')}
      <span className="beam-tag" style={{ left: `${(pos.vendor[0] + pos.core[0]) / 2}%`, top: `calc(${(pos.vendor[1] + pos.core[1]) / 2}% - ${narrow ? 0 : 22}px)` }}>tasks · grader</span>
      <span className="beam-tag" style={{ left: `${(pos.core[0] + pos.buyer[0]) / 2}%`, top: `calc(${(pos.core[1] + pos.buyer[1]) / 2}% - ${narrow ? 0 : 22}px)` }}>+4.1 pts · $640/task</span>
    </div>
  )
}

/* ---------- Compare: the order flips when you rank by what matters ---------- */
const ENVS = [
  { name: 'Env A · coding agent', reward: 92, transfer: 2.0, value: .4 },
  { name: 'Env B · math reasoning', reward: 81, transfer: 9.1, value: 3.1 },
  { name: 'Env C · web browsing', reward: 75, transfer: 6.2, value: 1.8 },
  { name: 'Env D · tool use', reward: 70, transfer: 4.0, value: 1.1 },
]
type Key = 'reward' | 'transfer' | 'value'
const KEYS: [Key, string, string, (v: number) => string, string][] = [
  ['reward', 'Training reward', 'Ranked by training reward, Env A looks like the best buy.', v => `${v}%`, 'var(--reward)'],
  ['transfer', 'Real improvement', 'Ranked by improvement on new problems, Env B wins by a mile.', v => `+${v.toFixed(1)} pts`, 'var(--transfer)'],
  ['value', 'Value per $1k', 'Per dollar, Env B delivers almost 8× what Env A does.', v => `${v.toFixed(1)} pts`, 'var(--good)'],
]
function Compare() {
  const [k, setK] = useState<Key>('reward')
  const meta = KEYS.find(x => x[0] === k)!
  const rows = useMemo(() => [...ENVS].sort((a, b) => b[k] - a[k]), [k])
  const max = rows[0][k]
  return (
    <div>
      <LayoutGroup id="seg">
        <div className="seg" role="tablist" aria-label="Rank environments by">
          {KEYS.map(([key, label]) => (
            <button key={key} role="tab" aria-selected={k === key} onClick={() => setK(key)}>
              {k === key && <motion.span layoutId="seg-pill" className="seg-pill" transition={{ type: 'spring', stiffness: 380, damping: 32 }} />}
              <span>{label}</span>
            </button>
          ))}
        </div>
      </LayoutGroup>
      <div className="cmp">
        {rows.map((r, i) => (
          <motion.div layout key={r.name} className={`cmp-row${i === 0 ? ' top' : ''}`} transition={{ type: 'spring', stiffness: 260, damping: 28 }}>
            <span className="name">{r.name}</span>
            <div className="cmp-bar"><motion.i animate={{ width: `${(r[k] / max) * 100}%`, background: meta[4] }} transition={{ duration: .8, ease }} /></div>
            <span className="num" style={{ textAlign: 'right' }}>{meta[3](r[k])}</span>
          </motion.div>
        ))}
      </div>
      <AnimatePresence mode="wait"><motion.p key={k} className="cmp-note" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>{meta[2]}</motion.p></AnimatePresence>
    </div>
  )
}

export default function Home() {
  return (
    <>
      <section className="hero">
        <Gradient />
        <div className="wrap">
          <div>
            <h1 aria-label="Don't buy training material blind.">
              {["Don't", 'buy', 'training', 'material'].map((w, i) => (
                <motion.span key={w} aria-hidden="true" style={{ display: 'inline-block', marginRight: '.25em' }} initial={reduced ? false : { opacity: 0, y: 40, filter: 'blur(8px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} transition={{ duration: .9, delay: i * .08, ease }}>{w}</motion.span>
              ))}
              <motion.span aria-hidden="true" className="transfer" style={{ display: 'inline-block' }} initial={reduced ? false : { opacity: 0, scale: .6, rotate: -6 }} animate={{ opacity: 1, scale: 1, rotate: 0 }} transition={{ delay: .45, type: 'spring', stiffness: 220, damping: 12 }}>blind.</motion.span>
            </h1>
            <motion.p className="lede" initial={reduced ? false : { opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: .12, ease }}>
              Touchstone tests an RL environment or dataset on small models before you pay, and tells you whether it will make your model better.
            </motion.p>
            <motion.div className="actions" initial={reduced ? false : { opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: .22, ease }}>
              <RequestButton /><a className="btn secondary" href="#report">See a sample report</a>
            </motion.div>
            <motion.div className="hero-note" initial={reduced ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: .5 }}>
              <span><Check />Sealed: you never see vendor tasks</span><span><Check />Independent: we sell no training material</span>
            </motion.div>
          </div>
          <motion.div initial={reduced ? false : { opacity: 0, y: 40, scale: .97 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: 1.1, delay: .15, ease }}>
            <Console />
          </motion.div>
        </div>
      </section>

      <Section title={<>Touchstone catches <span className="transfer">what sellers won't tell you.</span></>} text="Six RL environments, each hiding a different failure. Touchstone found every one.">
        <Caught />
      </Section>

      <section className="section flush">
        <div className="wrap">
          <div className="section-head">
            <Reveal><h2>Training material is expensive. <span className="transfer">Finding out it didn't work is worse.</span></h2></Reveal>
            <Reveal delay={.1}><p>A high training reward can hide a model that learned nothing. In our appraisals, most environments pushed reward up while the model got worse at new problems.</p></Reveal>
          </div>
          <Reveal><RunChart /></Reveal>
          <div style={{ height: 24 }} />
          <Reveal><Proof /></Reveal>
          <div className="facts">
            {([['$2,000', 'what a single RL task can sell for, and up to $20k at the high end'], ['4–5×', 'more for an exclusive deal, so a bad buy costs even more'], ['Weeks', 'of GPU time before a full training run tells you it failed'], ['0', 'independent checks between the vendor\'s claim and your purchase']] as const).map(([big, text], i) => (
              <motion.div key={big} initial={reduced ? false : { opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * .08, duration: .7, ease: [.16, 1, .3, 1] }}>
                <b>{big.startsWith('$') ? <Count value={big} /> : big}</b><p>{text}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="section"><div className="wrap"><Paradox /></div></section>

      <section className="section flush">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>Small experiments, before the big spend.</h2></Reveal><Reveal delay={.1}><p>An appraisal costs a fraction of one training run and finishes before you sign.</p></Reveal></div>
          <HowItWorks />
        </div>
      </section>

      <Section title={<>We break the grader <span className="transfer">before your model does.</span></>} text="A model will find any shortcut a grader allows, and learn the shortcut instead of the skill. These are the answers we feed every grader. Open one to see what the graders paid for it.">
        <Exploits />
      </Section>

      <section className="section flush">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>One report. Every number you need to decide.</h2></Reveal><Reveal delay={.1}><p>Pick an environment and watch the appraisal run: seal, train, measure, price.</p></Reveal></div>
          <Reveal><ReportSample /></Reveal>
        </div>
      </section>

      <section className="section flush">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>The highest reward isn't the best buy.</h2></Reveal><Reveal delay={.1}><p>Switch what you rank by and watch the order change.</p></Reveal></div>
          <Reveal><Compare /></Reveal>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>Neutral by design.</h2></Reveal><Reveal delay={.1}><p>The vendor's tasks stay sealed. You get the numbers, never the material, and we never sell training material ourselves.</p></Reveal></div>
          <Beam />
        </div>
      </section>

      <section className="section flush">
        <div className="wrap two">
          <Reveal><h2 style={{ fontSize: 'clamp(30px,3.2vw,44px)' }}>For AI teams buying training material</h2>
            <ul className="list">{['Test an environment before you pay for it', 'Compare vendors on one private test', 'Stop paying for tasks your model can game'].map(t => <li key={t}><Check />{t}</li>)}</ul></Reveal>
          <Reveal delay={.1}><h2 style={{ fontSize: 'clamp(30px,3.2vw,44px)' }}>For vendors selling it</h2>
            <ul className="list">{['A neutral rating buyers trust more than self-reported results', 'Find grader exploits before a customer does', 'Back your price with measured value'].map(t => <li key={t}><Check />{t}</li>)}</ul></Reveal>
        </div>
      </section>

      <Section title={<>Built on what the research <span className="transfer">already shows.</span></>} text="Data value varies enormously, small runs can rank it, and today the evidence buyers see comes from the people selling.">
        <Evidence />
      </Section>

      <Close title="Know before you train." text="Send us the environment you're considering. We'll scope a pilot appraisal with you." />
    </>
  )
}
