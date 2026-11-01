import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'motion/react'
import recorded from '../demo/recorded.json'
import { normalize, type View } from '../demo/api'
import { truth, vendors } from '../data'
import { Close, Rating, RequestButton, reduced, useSeen } from '../ui'

const pct = (v: number) => `${(v * 100).toFixed(v > 0 && v < .1 ? 1 : 0)}%`
const pts = (v: number) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(1)}`

/* ---------- The console plays real recorded engine runs, read from the same file the live demo replays ---------- */
type Rec = { id: string; report: any }
type Line = { key: string; value: string; tone?: 'bad' | 'good' }
const TABS: [string, string][] = [['gameable-env', 'Gameable grader'], ['contaminated-dataset', 'Leaked test items'], ['good-dataset', 'Clean material']]

function lines(r: any, v: View): Line[] {
  const out: Line[] = [
    { key: `seal ${r.material.name}`, value: `${r.material.n_items.toLocaleString('en-US')} items` },
    { key: 'overlap with the test suite', value: pct(v.overlap.suite), tone: v.overlap.suite >= .05 ? 'bad' : undefined },
    { key: 'overlap with free material', value: pct(v.overlap.public) },
  ]
  if (v.probes.length) out.push({ key: 'probe the grader', value: `hedged answer earns ${pct(v.probes[0].reward)}`, tone: v.probes[0].reward >= .2 ? 'bad' : undefined })
  else { const rate = r.label_quality.arithmetic.rate; out.push({ key: 'check the labels', value: `${pct(rate)} arithmetic errors`, tone: rate >= .2 ? 'bad' : undefined }) }
  out.push(v.screened ? { key: 'stop before training', value: 'no model trained', tone: 'bad' } : { key: `train ${r.measurable_at} against a placebo`, value: `${pts(v.forecast!.point)} pts net`, tone: 'good' })
  return out
}

const BEAT = 260, DWELL = 3400

function Console() {
  const runs = useMemo(() => TABS.map(([id, label]) => {
    const rec = (recorded as Rec[]).find(r => r.id === id)!, v = normalize(rec.report, label)
    const flag = v.flags.find(f => f.severity === 'block')
    return { id, label, lines: lines(rec.report, v), v, finding: flag ? flag.text.split(/(?<=\.)\s/)[0] : 'No red flags on the checks that ran.' }
  }), [])
  const [run, setRun] = useState(0)
  const [held, setHeld] = useState(false)
  const [paused, setPaused] = useState(false)
  // Each line takes two beats: its key appears, then its value resolves.
  const [beat, setBeat] = useState(reduced ? 99 : 0)
  const r = runs[run], total = r.lines.length * 2 + 1, done = beat >= total
  useEffect(() => {
    if (reduced) return
    setBeat(0)
    const timers = Array.from({ length: total }, (_, i) => window.setTimeout(() => setBeat(i + 1), 400 + i * BEAT))
    return () => timers.forEach(clearTimeout)
  }, [run])
  const dwelling = done && !held && !paused && !reduced
  useEffect(() => {
    if (!dwelling) return
    const t = window.setTimeout(() => setRun(i => (i + 1) % runs.length), DWELL)
    return () => clearTimeout(t)
  }, [dwelling])
  const pick = (i: number) => { setHeld(true); setRun(i) }
  const keys = (e: React.KeyboardEvent) => {
    const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
    if (!d) return
    const i = (run + d + runs.length) % runs.length
    pick(i); (e.currentTarget.children[i] as HTMLElement).focus()
  }
  return (
    <figure className="console" aria-label="Recorded Touchstone audit runs" onPointerEnter={() => setPaused(true)} onPointerLeave={() => setPaused(false)} onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
      <div className="console-tabs" role="tablist" aria-label="Recorded run" onKeyDown={keys}>
        {runs.map((x, i) => (
          <button key={x.id} id={`tab-${x.id}`} role="tab" aria-selected={run === i} aria-controls="console-panel" tabIndex={run === i ? 0 : -1} onClick={() => pick(i)}>
            {x.label}{run === i && <i key={dwelling ? 'run' : 'rest'} className={dwelling ? 'dwell' : ''} style={{ animationDuration: `${DWELL}ms` }} />}
          </button>
        ))}
      </div>
      <div className="console-body" id="console-panel" role="tabpanel" aria-labelledby={`tab-${r.id}`}>
        <ol className="console-log" key={r.id}>
          {r.lines.map((l, i) => {
            const key = beat > i * 2, value = beat > i * 2 + 1
            return <li key={l.key} className={key ? 'on' : ''}><span>{l.key}</span><b className={value ? l.tone : 'wait'}>{value ? l.value : 'running'}</b></li>
          })}
        </ol>
        <div className={`console-verdict${done ? ' on' : ''}`}>
          <Rating grade={done ? r.v.grade : '—'} />
          <p>{r.finding}</p>
          <small>{r.v.perItem > 0 ? `Estimated value $${Math.round(r.v.perItem)} an item at $${r.v.dollarsPerPoint!.toLocaleString('en-US')} a point, the buyer’s assumption` : 'Price blocked'}</small>
        </div>
      </div>
      <figcaption>Recorded engine run on {r.v.kind === 'env' ? 'a test case' : 'a dataset test case'}, October 30, 2026. Ran in {r.v.runtime} seconds.{r.v.kind === 'env' ? '' : ' Dataset audits are advisory for now.'}</figcaption>
    </figure>
  )
}

/* ---------- One chart. Reward is the logged curve; accuracy on new problems was measured at the start and end only, so
   it is drawn as two points and a dashed join, and the cursor reads reward alone ---------- */
function RunChart() {
  const env = vendors.find(e => e.id === 'quickgrade_arith') ?? vendors[0]
  const rung = env.rungs[truth]
  const [narrow, setNarrow] = useState(() => matchMedia('(max-width: 720px)').matches)
  useEffect(() => { const m = matchMedia('(max-width: 720px)'), on = () => setNarrow(m.matches); m.addEventListener('change', on); return () => m.removeEventListener('change', on) }, [])
  const W = narrow ? 560 : 1200, H = narrow ? 400 : 400, L = 56, R = narrow ? 8 : 176, T = 16, B = 32
  const reward = rung.curve.map(v => v * 100)
  const last = reward.length - 1, from = rung.heldout_before, to = rung.heldout_after
  const x = (i: number) => L + (i / last) * (W - L - R)
  const y = (v: number) => T + (1 - (v - 40) / 60) * (H - T - B)
  const path = reward.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ')
  const [ref, seen] = useSeen<HTMLElement>()
  const box = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState<number | null>(null)
  const onMove = (e: React.PointerEvent) => {
    const r = box.current!.getBoundingClientRect(), f = ((e.clientX - r.left) / r.width * W - L) / (W - L - R)
    setHover(f < 0 || f > 1 ? null : Math.round(f * last))
  }
  const draw = (delay = 0) => reduced ? {} : { initial: { pathLength: 0 }, animate: { pathLength: seen ? 1 : 0 }, transition: { duration: 1.2, delay, ease: 'easeInOut' as const } }
  const later = reduced ? {} : { initial: { opacity: 0 }, animate: { opacity: seen ? 1 : 0 }, transition: { duration: .4, delay: 1.2 } }
  const gapX = narrow ? W - R - 150 : W - R + 8, mid = (y(reward[last]) + y(to)) / 2
  return (
    <figure className="chart" ref={ref}>
      <div ref={box} onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Training reward climbs to ${reward[last].toFixed(0)}% while accuracy on new problems falls from ${from.toFixed(0)}% to ${to.toFixed(0)}%`}>
          {[40, 70, 100].map(g => <g key={g}><line x1={L} x2={W - R} y1={y(g)} y2={y(g)} /><text x={L - 12} y={y(g) + 5} textAnchor="end">{g}%</text></g>)}
          <text x={L} y={H - 6}>Step 0</text><text x={W - R} y={H - 6} textAnchor="end">Step 1,000</text>
          {hover !== null && <line className="cursor" x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} />}
          <motion.path className="reward" d={path} {...draw()} />
          <path className="truth" d={`M${x(0)} ${y(from)} L${x(last)} ${y(to)}`} strokeDasharray="1 9" />
          <circle className="truth" cx={x(0)} cy={y(from)} r="5" /><circle className="truth" cx={x(last)} cy={y(to)} r="5" />
          <motion.g {...later}>
            <path className="gap" d={`M${gapX - 6} ${y(reward[last]) + 8} H${gapX} V${y(to) - 8} H${gapX - 6}`} />
            <text className="end" x={gapX + 12} y={mid + 6}>The gap</text>
          </motion.g>
          <text className="end reward" x={narrow ? W - R : W - R + 14} y={y(reward[last]) + (narrow ? -12 : -14)} textAnchor={narrow ? 'end' : 'start'}>Reward {(hover === null ? reward[last] : reward[hover]).toFixed(0)}%</text>
          <text className="end truth" x={narrow ? W - R : W - R + 14} y={y(to) + (narrow ? 28 : 30)} textAnchor={narrow ? 'end' : 'start'}>{narrow ? `Accuracy on new problems ${to.toFixed(0)}%` : <><tspan>Accuracy on</tspan><tspan x={W - R + 14} dy="20">new problems {to.toFixed(0)}%</tspan></>}</text>
        </svg>
      </div>
      <figcaption>Test environment, trained past the stop to show the gap. Accuracy on new problems was measured at the start and the end.</figcaption>
    </figure>
  )
}

const RESULTS: [string, string, string][] = [
  ['21 of 21', 'RL environment cases exactly right', 'Locked test on test cases'],
  ['12 of 12', 'gameable graders caught', 'Locked test on test cases'],
  ['3 of 3', 'reworded test leaks caught', 'Locked test on test cases'],
]
// All four outputs come from one recorded run, the clean test case.
const STEPS: [string, string, string, string][] = [
  ['Seal', 'The seller’s tasks go into a sealed sandbox. You get results, never the tasks, and we sell no training material.', 'seal good_word_problems', '400 items'],
  ['Screen', 'Grader probes and test-overlap checks run first. A blocking problem can end the audit before any training.', 'overlap with the test suite', '0%'],
  ['Train', 'Small open models train on the material against a placebo, then face private problems they never saw.', 'net gain at 135M', '+7.3 pts, +1.7 to +12.9'],
  ['Report', 'A grade, the gain with its range, and an estimated value, all stated at the size we measured.', 'report', 'Grade A, $76 an item'],
]

function Step({ index, title, text, output, onReach }: { index: number; title: string; text: string; output: string; onReach: (i: number) => void }) {
  const ref = useRef<HTMLLIElement>(null)
  useEffect(() => {
    if (reduced || !ref.current) return
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { onReach(index + 1); io.disconnect() } }, { rootMargin: '-25% 0px -25% 0px' })
    io.observe(ref.current)
    return () => io.disconnect()
  }, [])
  return <li ref={ref}><h3>{title}</h3><p>{text}</p><code>{output}</code></li>
}

function How() {
  const [reached, setReached] = useState(reduced ? STEPS.length : 0)
  const reach = (n: number) => setReached(r => Math.max(r, n))
  return (
    <section className="band how">
      <div className="wrap">
        <div className="how-head">
          <h2>Small experiments, before the big spend.</h2>
          <p>Every audit runs the same way, on every vendor.</p>
          <a className="more" href="#method">Read the method</a>
          <figure className="console mini" aria-label="One recorded run, step by step">
            <ol className="console-log">{STEPS.map(([title, , key, value], i) => <li key={title} className={i < reached ? 'on' : ''}><span>{key}</span><b className={i === 3 || i === 2 ? 'good' : undefined}>{value}</b></li>)}</ol>
            <figcaption>Recorded engine run on a dataset test case. Dataset audits are advisory for now.</figcaption>
          </figure>
        </div>
        <ol className="steps">{STEPS.map(([title, text, key, value], i) => <Step key={title} index={i} title={title} text={text} output={`${key}: ${value}`} onReach={reach} />)}</ol>
      </div>
    </section>
  )
}

export default function Home() {
  return (
    <>
      <section className="hero dark">
        <div className="wrap">
          <h1>Don’t buy training material blind.</h1>
          <div className="hero-row">
            <p className="lede">Touchstone audits RL environments before you pay. We catch gameable graders and leaked test items, and measure what a model learns on problems it never saw. Dataset audits are coming.</p>
            <div className="actions"><RequestButton /><a className="btn ghost" href="#demo">Try the live demo</a></div>
          </div>
        </div>
      </section>
      <div className="wrap console-wrap"><Console /></div>

      <section className="results" aria-label="Audit results">
        <dl className="wrap">
          {RESULTS.map(([n, label, scope]) => <div key={label}><dt>{label}<small>{scope}</small></dt><dd>{n}</dd></div>)}
        </dl>
      </section>

      <section className="band">
        <div className="wrap">
          <div className="band-head">
            <h2>Training material is expensive. Finding out it didn’t work is worse.</h2>
            <p>A high reward can hide a model that learned nothing. The first line is what a seller shows you. The second is what you are paying for.</p>
          </div>
          <RunChart />
        </div>
      </section>

      <How />

      <Close title="Know before you train." text="Send us the RL environment you’re considering. We’ll scope a pilot audit with you." />
    </>
  )
}
