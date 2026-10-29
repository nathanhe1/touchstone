import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion, LayoutGroup } from 'motion/react'
import { animate, createTimeline, stagger } from 'animejs'
import NumberFlow from '@number-flow/react'
import { data, vendors, base, truth, signed, pct, money, params, type Env } from '../data'
import { Alert, Arrow, Check, Close, Count, Panel, Rating, Reveal, RequestButton, Sky, reduced } from '../ui'
import { Exploits, Section } from './Sections'

const ease = [.16, 1, .3, 1] as const
const slug = (e: Env) => e.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-$/, '')
const good = (e: Env) => e.grade === 'A' || e.grade === 'B'
const reason = (e: Env) => e.hackability.score >= .2 ? 'gameable grader' : e.redundancy.public_overlap >= .5 ? 'mostly free copies' : 'no real gain'
const verdict = (e: Env) =>
  e.is_public_baseline ? 'The free baseline every purchase is compared against.'
  : e.hackability.score >= .2 ? 'Fix the grader before anyone buys this.'
  : e.redundancy.public_overlap >= .5 ? 'Mostly already free. Not worth the asking price.'
  : e.actual_at_truth < 0 ? 'Don\'t buy: the model gets worse at new problems.'
  : `Worth buying at up to ${money(e.fair_value_per_task)} a task.`

/* ---------- Hero: the product as a desktop app, appraising each environment in turn ---------- */
function AppWindow() {
  const [idx, setIdx] = useState(0)
  const [done, setDone] = useState(reduced)
  const body = useRef<HTMLDivElement>(null)
  const e = vendors[idx]
  useEffect(() => {
    const el = body.current
    if (!el || reduced) return
    setDone(false)
    const lines = el.querySelectorAll('[data-l]'), bars = el.querySelectorAll('.cbars i')
    let timer = 0
    const tl = createTimeline({ onComplete: () => { setDone(true); timer = window.setTimeout(() => setIdx(i => (i + 1) % vendors.length), 3200) } })
    tl.set(lines, { opacity: 0, translateY: 6 }).set(bars, { scaleX: 0 })
    lines.forEach((line, i) => {
      tl.add(line, { opacity: 1, translateY: 0, duration: 300, ease: 'outQuad' }, i ? '+=280' : 300)
      if (line.classList.contains('cbars')) tl.add(bars, { scaleX: 1, duration: 700, delay: stagger(110), ease: 'outQuad' })
    })
    tl.add(el.querySelector('.stamp')!, { scale: [1.25, 1], opacity: [0, 1], duration: 500, ease: 'outBack(2)' }, '-=250')
    return () => { tl.pause(); clearTimeout(timer) }
  }, [idx])
  const hack = e.hackability.score >= .2, copied = e.redundancy.public_overlap >= .5, gain = e.actual_at_truth
  return (
    <div className="app">
      <div className="app-bar"><i /><i /><i /><span>Touchstone</span><span className="meta">appraising</span></div>
      <div className="app-body">
        <aside className="app-side" aria-label="Environments">
          <small>Environments</small>
          {vendors.map((v, i) => (
            <button key={v.id} className={i === idx ? 'on' : ''} onClick={() => setIdx(i)}>
              <span>{v.name}</span><i className={`g ${i === idx && !done ? '' : v.grade}`}>{i === idx && !done ? '·' : v.grade}</i>
            </button>
          ))}
        </aside>
        <div className="console-body" ref={body} key={idx}>
          <p className="cl" data-l><span className="p">›</span>seal <b>{slug(e)}</b><span className="r good">sealed</span></p>
          <p className="cl" data-l><span className="p">›</span>train 4 model sizes</p>
          <div className="cbars" data-l>{Object.keys(data.ladder).map(k => <div key={k}><span>{k}</span><i style={{ width: `${Math.max(e.rungs[k].env_reward_after * 100, 2)}%` }} /><em>{pct(e.rungs[k].env_reward_after)}</em></div>)}</div>
          <p className="cl" data-l><span className="p">›</span>probe the grader<span className={`r ${hack ? 'bad' : 'good'}`}>{hack ? `${pct(e.hackability.score)} of junk scored` : 'grader held'}</span></p>
          <p className="cl" data-l><span className="p">›</span>check for free copies<span className={`r ${copied ? 'bad' : ''}`}>{pct(e.redundancy.public_overlap)} already free</span></p>
          <p className="cl" data-l><span className="p">›</span>test on new problems<span className={`r ${gain < 0 ? 'bad' : 'good'}`}>{signed(gain)} pts</span></p>
          <span className={`stamp ${good(e) ? 'good' : 'bad'}`} data-l>{good(e) ? <Check /> : <Alert />}Grade {e.grade} · {good(e) ? `worth ${money(e.fair_value_per_task)} a task` : reason(e)}</span>
        </div>
        <div className="app-out">
          <div><small>Grade</small><div style={{ marginTop: 8 }}><LayoutGroup id="hero-rating"><Rating grade={done ? e.grade : '—'} layoutId="hero-hl" /></LayoutGroup></div></div>
          <div><small>Change on new problems</small><div className={`big ${done ? (gain < 0 ? 'bad' : 'good') : 'dim'}`}>{done ? `${signed(gain)} pts` : '—'}</div></div>
          <div><small>Fair value per task</small><div className={`big${done ? '' : ' dim'}`}>{done ? money(e.fair_value_per_task) : '—'}</div></div>
          <AnimatePresence mode="wait">{done && <motion.p key={e.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>{verdict(e)}</motion.p>}</AnimatePresence>
        </div>
      </div>
    </div>
  )
}

/* ---------- A real training run: reward climbs while accuracy on new problems falls ---------- */
function RunChart() {
  const env = vendors.find(e => e.id === 'quickgrade_arith') ?? vendors[0]
  const rung = env.rungs[truth]
  const W = 960, H = 300, L = 36, B = 26
  const x = (i: number, n: number) => L + (i / (n - 1)) * (W - L - 8)
  const y = (v: number) => 8 + (1 - v / 100) * (H - B - 8)
  const reward = rung.curve.map(v => v * 100)
  const accuracy = reward.map((_, i) => rung.heldout_before + (rung.heldout_after - rung.heldout_before) * (i / (reward.length - 1)))
  const path = (vals: number[]) => vals.map((v, i) => `${i ? 'L' : 'M'}${x(i, vals.length).toFixed(1)} ${y(v).toFixed(1)}`).join(' ')
  const area = (vals: number[]) => `${path(vals)} L${x(vals.length - 1, vals.length)} ${H - B} L${L} ${H - B} Z`
  const stepRef = useRef<HTMLElement>(null), rewardRef = useRef<HTMLElement>(null), accRef = useRef<HTMLElement>(null)
  const box = useRef<HTMLDivElement>(null)
  const [started, setStarted] = useState(reduced)
  const [done, setDone] = useState(reduced)
  const [hover, setHover] = useState<{ x: number; i: number } | null>(null)
  const onMove = (ev: React.PointerEvent) => {
    const r = box.current!.getBoundingClientRect()
    const fx = ((ev.clientX - r.left) / r.width * W - L) / (W - L - 8)
    if (fx < 0 || fx > 1) return setHover(null)
    setHover({ x: ev.clientX - r.left, i: Math.round(fx * (reward.length - 1)) })
  }
  // Starts when the chart scrolls into view, so the climb is seen rather than missed.
  useEffect(() => {
    if (reduced || !box.current) return
    const io = new IntersectionObserver(([en]) => { if (en.isIntersecting) { setStarted(true); io.disconnect() } }, { threshold: .4 })
    io.observe(box.current)
    return () => io.disconnect()
  }, [])
  useEffect(() => {
    if (!started || reduced) return
    const s = { t: 0 }, last = reward.length - 1
    const a = animate(s, {
      t: 1, duration: 2600, ease: 'inOutQuad',
      onUpdate: () => {
        const i = s.t * last, lo = Math.floor(i), f = i - lo
        const r = reward[lo] + (reward[Math.min(lo + 1, last)] - reward[lo]) * f
        const acc = accuracy[lo] + (accuracy[Math.min(lo + 1, last)] - accuracy[lo]) * f
        if (stepRef.current) stepRef.current.textContent = Math.round(s.t * 1000).toLocaleString('en-US')
        if (rewardRef.current) rewardRef.current.textContent = `${r.toFixed(1)}%`
        if (accRef.current) accRef.current.textContent = `${acc.toFixed(1)}%`
      },
      onComplete: () => setDone(true),
    })
    return () => { a.pause() }
  }, [started])
  const draw = reduced ? {} : { initial: { pathLength: 0 }, animate: started ? { pathLength: 1 } : { pathLength: 0 }, transition: { duration: 2.6, ease: 'easeInOut' as const } }
  const end = reward.length - 1
  return (
    <Panel title={env.name} meta={<span className="legend"><span><i style={{ background: 'var(--reward)' }} />training reward</span><span><i style={{ background: 'var(--transfer)' }} />accuracy on new problems</span></span>}>
      <div className="run-chart panel-body" ref={box} onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        {hover && (<>
          <span className="xhair" style={{ left: hover.x }} />
          <span className="xtip" style={{ left: Math.min(hover.x + 12, (box.current?.clientWidth ?? 600) - 180) }}>
            step {Math.round(hover.i / end * 1000)}
            <b className="reward">reward {reward[hover.i].toFixed(1)}%</b><b className="transfer">new problems {accuracy[hover.i].toFixed(1)}%</b>
          </span>
        </>)}
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Training reward climbs from ${reward[0].toFixed(0)}% to ${reward[end].toFixed(0)}% while accuracy on new problems falls from ${accuracy[0].toFixed(1)}% to ${accuracy[end].toFixed(1)}%`}>
          {[0, 25, 50, 75, 100].map(g => (<g key={g}><line className="grid-line" x1={L} x2={W - 8} y1={y(g)} y2={y(g)} /><text className="axis-text" x={L - 8} y={y(g) + 4} textAnchor="end">{g}</text></g>))}
          <text className="axis-text" x={L} y={H - 6}>step 0</text><text className="axis-text" x={W - 8} y={H - 6} textAnchor="end">1,000</text>
          <defs><linearGradient id="fill-r" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#9aa6b8" /><stop offset="1" stopColor="#9aa6b8" stopOpacity="0" /></linearGradient></defs>
          <motion.path d={area(reward)} fill="url(#fill-r)" initial={{ opacity: 0 }} animate={{ opacity: done ? .18 : 0 }} transition={{ duration: .8 }} />
          <motion.path d={path(reward)} className="curve" stroke="var(--reward)" {...draw} />
          <motion.path d={path(accuracy)} className="curve" stroke="var(--transfer)" {...draw} />
          {done && <>
            <text className="end-label" x={W - 8} y={y(reward[end]) - 10} textAnchor="end" fill="var(--reward)">{reward[end].toFixed(1)}%</text>
            <text className="end-label" x={W - 8} y={y(accuracy[end]) + 22} textAnchor="end" fill="var(--transfer)">{accuracy[end].toFixed(1)}%</text>
          </>}
        </svg>
        <AnimatePresence>
          {done && (
            <motion.span className="verdict-card" initial={reduced ? false : { opacity: 0, scale: .9, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} transition={{ type: 'spring', stiffness: 220, damping: 18 }}>
              <small>Touchstone verdict</small><b>Don't buy at this price</b><small>{pct(env.hackability.score)} of junk answers still scored</small>
            </motion.span>
          )}
        </AnimatePresence>
      </div>
      <p className="verdict-inline"><b className="bad">Don't buy at this price.</b> {pct(env.hackability.score)} of junk answers still scored.</p>
      <div className="run-foot">
        <div><small>Step</small><b ref={stepRef}>{reduced ? '1,000' : '0'}</b></div>
        <div><small>Training reward</small><b ref={rewardRef} className="reward">{(reduced ? reward[end] : reward[0]).toFixed(1)}%</b></div>
        <div><small>New problems</small><b ref={accRef} className="transfer">{(reduced ? accuracy[end] : accuracy[0]).toFixed(1)}%</b></div>
      </div>
    </Panel>
  )
}

/* ---------- How it works: four colour cards, each with its own small scene ---------- */
const inView = (delay = 0) => reduced ? {} : { initial: 'off', whileInView: 'on', viewport: { once: true, margin: '0px 0px -15% 0px' }, transition: { delay } }

function SealArt() {
  return (
    <motion.div className="mini-win" {...inView()}>
      {['task_0001', 'task_0002', 'task_0003', 'task_0004'].map((t, i) => (
        <motion.div key={t} className="mini-row" variants={{ off: { opacity: 0, x: -24 }, on: { opacity: 1, x: 0, transition: { delay: .1 + i * .1, type: 'spring', stiffness: 260, damping: 22 } } }}>
          <span>{t}</span><span className="lock"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="2" /><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" /></svg>sealed</span>
        </motion.div>
      ))}
    </motion.div>
  )
}
function TrainArt() {
  const sizes = Object.entries(data.ladder)
  const biggest = Math.max(...sizes.map(([, v]) => v))
  return (
    <motion.div className="atoms" {...inView()}>
      {sizes.map(([k, v], i) => {
        const d = 16 + Math.sqrt(v / biggest) * 58
        return (
          <div className="atom" key={k}>
            <motion.div className="sphere" style={{ width: d, height: d }} whileHover={{ scale: 1.15 }}
              variants={{ off: { scale: 0, y: 24 }, on: { scale: 1, y: 0, transition: { delay: .1 + i * .12, type: 'spring', stiffness: 220, damping: 11 } } }} />
            <b>{k}</b><small>{params(v)}</small>
          </div>
        )
      })}
    </motion.div>
  )
}
function MeasureArt() {
  const env = vendors[0]
  const rows: [string, string, number, string][] = [
    ['Better on new problems', `${signed(env.actual_at_truth)} pts`, .62, 'var(--transfer)'],
    ['Reward from exploits', pct(env.hackability.score), .03, 'var(--bad)'],
    ['Already free', pct(env.redundancy.public_overlap), env.redundancy.public_overlap, 'var(--reward)'],
  ]
  return (
    <motion.div className="mini-win bars" {...inView()}>
      {rows.map(([label, value, w, c], i) => (
        <div className="bar-row" key={label}><span>{label}</span><b>{value}</b>
          <div className="track"><motion.i style={{ background: c, width: `${w * 100}%` }} variants={{ off: { scaleX: 0 }, on: { scaleX: 1, transition: { delay: .2 + i * .14, duration: .9, ease } } }} /></div>
        </div>
      ))}
    </motion.div>
  )
}
function PriceArt() {
  const env = vendors[0]
  return (
    <motion.div className="price" {...inView()}>
      <motion.div className="tag" variants={{ off: { opacity: 0, y: 16, rotate: -4 }, on: { opacity: 1, y: 0, rotate: 0, transition: { delay: .15, type: 'spring', stiffness: 240, damping: 15 } } }}>
        <small>Fair value per task</small><b><Count value={money(env.fair_value_per_task)} /></b><Rating grade={env.grade} compact />
      </motion.div>
    </motion.div>
  )
}
const STEPS: [string, string, string, () => React.ReactElement][] = [
  ['Seal.', 'The vendor uploads to a sealed sandbox. You see results, never their tasks.', 'rose', SealArt],
  ['Train small.', 'Open models train on it at four sizes with one fixed recipe.', 'sky2', TrainArt],
  ['Measure.', 'We test on private problems and try to fool the grader.', 'mint', MeasureArt],
  ['Price.', 'You get a grade, a forecast at your size and a fair price per task.', 'sun', PriceArt],
]

/* ---------- Ranking: benchmark-style bars, the order flips when you rank by what matters ---------- */
const ENVS = [
  { name: 'Env A · coding agent', reward: 92, transfer: 2.0, value: .4 },
  { name: 'Env B · math reasoning', reward: 81, transfer: 9.1, value: 3.1 },
  { name: 'Env C · web browsing', reward: 75, transfer: 6.2, value: 1.8 },
  { name: 'Env D · tool use', reward: 70, transfer: 4.0, value: 1.1 },
]
type Key = 'reward' | 'transfer' | 'value'
const KEYS: [Key, string, string, (v: number) => string, string][] = [
  ['reward', 'Training reward', 'By training reward, Env A looks like the best buy.', v => `${v}%`, 'var(--reward)'],
  ['transfer', 'Real improvement', 'By improvement on new problems, Env B wins by a mile.', v => `+${v.toFixed(1)} pts`, 'var(--transfer)'],
  ['value', 'Value per $1k', 'Per dollar, Env B delivers almost 8× what Env A does.', v => `${v.toFixed(1)} pts`, 'var(--good)'],
]
function Compare() {
  const [k, setK] = useState<Key>('reward')
  const meta = KEYS.find(x => x[0] === k)!
  const rows = useMemo(() => [...ENVS].sort((a, b) => b[k] - a[k]), [k])
  const max = rows[0][k]
  return (
    <div className="rank">
      <div className="cmp">
        {rows.map((r, i) => (
          <motion.div layout key={r.name} className="cmp-row" transition={{ type: 'spring', stiffness: 260, damping: 28 }}>
            <span className="name">{r.name}</span>
            <div className="cmp-bar"><motion.i initial={reduced ? false : { width: 0 }} animate={{ width: `${(r[k] / max) * 100}%`, background: i === 0 ? meta[4] : '#c9d1dd' }} transition={{ duration: .8, ease }} /></div>
            <span className="num">{meta[3](r[k])}</span>
          </motion.div>
        ))}
      </div>
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
      <AnimatePresence mode="wait"><motion.p key={k} className="cmp-note" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>{meta[2]}</motion.p></AnimatePresence>
    </div>
  )
}

/* ---------- One report: switch environment, every number re-reads ---------- */
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
    ['Reward won by exploits', 'Junk answers that still scored', 2, <NumberFlow value={env.hackability.score} format={pctF} />, env.hackability.score >= .2 ? 'bad' : ''],
    ['Already in free data', 'Overlap with public sets', 2, <NumberFlow value={env.redundancy.public_overlap} format={pctF} />, env.redundancy.public_overlap >= .5 ? 'bad' : ''],
    ['Forecast at the largest size', `90% range ${signed(env.forecast.lo)} to ${signed(env.forecast.hi)}`, 3, <NumberFlow value={env.forecast.forecast} format={ptsF} suffix=" pts" />, ''],
    ['Fair value per task', 'Compared with free practice', 4, <NumberFlow value={env.fair_value_per_task} format={usd} />, 'transfer'],
  ]
  const stages = ['Seal', 'Train', 'Measure', 'Price']
  return (
    <Panel title="Appraisal report" meta="pick an environment">
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
            <span className="rating-cap">{env.grade === '—' ? 'Free comparison set, not graded' : phase >= 4 ? `Grade ${env.grade}` : 'Grading…'}</span>
            <h3 style={{ marginTop: 20 }}>{env.name}</h3>
            <p className="dim" style={{ margin: '4px 0 0', fontSize: 14 }}>{env.redundancy.n_tasks.toLocaleString('en-US')} tasks · sealed {env.sha256.slice(0, 10)}</p>
          </div>
          <div className="by-size" aria-label="Change on new problems at each model size">
            <small>Change on new problems, by model size</small>
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

export default function Home() {
  const up = (delay: number) => reduced ? {} : { initial: { opacity: 0, y: 18 }, animate: { opacity: 1, y: 0 }, transition: { duration: .9, delay, ease } }
  return (
    <>
      <section className="hero">
        <Sky />
        <div className="wrap hero-copy">
          <motion.a className="kicker" href="#product" {...up(0)}>Independent appraisal for RL environments<Arrow /></motion.a>
          <h1 aria-label="Don't buy training material blind." style={{ marginTop: 18 }}>
            {["Don't", 'buy', 'training', 'material', 'blind.'].map((w, i) => (
              <motion.span key={w} aria-hidden="true" style={{ display: 'inline-block', marginRight: '.24em' }} initial={reduced ? false : { opacity: 0, y: 30, filter: 'blur(8px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} transition={{ duration: .9, delay: .05 + i * .07, ease }}>{w}</motion.span>
            ))}
          </h1>
          <motion.p className="lede" {...up(.25)}>Touchstone tests an RL environment on small models before you pay, and tells you if it will make your model better.</motion.p>
          <motion.div className="actions" {...up(.35)}><RequestButton /><a className="btn secondary" href="#report">See a sample report</a></motion.div>
          <motion.div className="hero-note" {...up(.45)}><span><Check />Sealed: you never see vendor tasks</span><span><Check />Independent: we sell no training material</span></motion.div>
        </div>
        <motion.div className="hero-stage" initial={reduced ? false : { opacity: 0, y: 60 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1.2, delay: .3, ease }}>
          <AppWindow />
        </motion.div>
      </section>

      <section className="section">
        <div className="wrap">
          <div className="statement">
            <Reveal><h2>Training material is expensive. <span className="transfer">Finding out it didn't work is worse.</span></h2></Reveal>
            <Reveal delay={.1}>
              <p><b>Today, the only evidence a buyer sees comes from the seller.</b> The real answer arrives weeks later, after a full training run.</p>
              <p><b>Touchstone is the check in between.</b> We train small models on the environment, test them on problems they've never seen, and try to fool the grader. You get a grade and a fair price before you sign.</p>
            </Reveal>
          </div>
          <div className="facts">
            {([['$2,000', 'for a single RL task, and up to $20k at the high end'], ['4–5×', 'more for an exclusive deal'], ['Weeks', 'of GPU time before a full run shows it failed'], ['0', 'independent checks before you buy, until now']] as const).map(([big, text], i) => (
              <motion.div key={big} initial={reduced ? false : { opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * .08, duration: .7, ease }}>
                <b>{big.startsWith('$') ? <Count value={big} /> : big}</b><p>{text}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <Section title={<>A high reward can hide a model <span className="transfer">that learned nothing.</span></>} text="Training reward climbs to 99% here while accuracy on new problems falls. Hover the chart to follow it." flush>
        <Reveal><RunChart /></Reveal>
      </Section>

      <Section title="Small experiments, before the big spend." text="An appraisal costs a fraction of one training run and finishes before you sign." flush>
        <div className="steps4">
          {STEPS.map(([title, text, tone, Art], i) => (
            <Reveal key={title} delay={i * .08} className="step-card">
              <div className={`step-art ${tone}`}><Art /></div>
              <p><b>{title}</b> {text}</p>
            </Reveal>
          ))}
        </div>
      </Section>

      <Section title={<>The highest reward <span className="transfer">isn't the best buy.</span></>} text="Rank four environments three ways and watch the order change." flush>
        <Reveal><Compare /></Reveal>
      </Section>

      <Section title={<>We break the grader <span className="transfer">before your model does.</span></>} text="A model learns any shortcut a grader allows. These are the answers we feed every grader. Open one to see what it paid." flush>
        <Exploits />
      </Section>

      <section className="section wash">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>One report. <span className="transfer">Every number you need.</span></h2></Reveal><Reveal delay={.1}><p>Pick an environment and watch the appraisal run.</p></Reveal></div>
          <Reveal><ReportSample /></Reveal>
        </div>
      </section>

      <div style={{ height: 10 }} />
      <Close title="Know before you train." text="Send us the environment you're considering. We'll scope a pilot appraisal with you." />
    </>
  )
}
