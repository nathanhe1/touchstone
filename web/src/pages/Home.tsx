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
const TABS: [string, string][] = [['gameable-env', 'Gameable grader'], ['contaminated-dataset', 'Leaked test items'], ['noisy-dataset', 'Wrong labels'], ['good-dataset', 'Clean material']]

function lines(r: any, v: View): Line[] {
  const out: Line[] = [
    { key: `seal ${r.material.name}`, value: `${r.material.n_items.toLocaleString('en-US')} items` },
    { key: 'overlap with the test suite', value: pct(v.overlap.suite), tone: v.overlap.suite >= .05 ? 'bad' : undefined },
    { key: 'overlap with free material', value: pct(v.overlap.public) },
  ]
  if (v.probes.length) out.push({ key: 'probe the grader', value: `'${v.probes[0].name}' earns ${pct(v.probes[0].reward)}`, tone: v.probes[0].reward >= .2 ? 'bad' : undefined })
  else { const rate = r.label_quality.arithmetic.rate; out.push({ key: 'check the labels', value: `${pct(rate)} arithmetic errors`, tone: rate >= .2 ? 'bad' : undefined }) }
  out.push(v.screened ? { key: 'stop before training', value: 'no model trained', tone: 'bad' } : { key: `train ${r.measurable_at} against a placebo`, value: `${pts(v.forecast!.point)} pts net`, tone: 'good' })
  return out
}

function Console() {
  const runs = useMemo(() => TABS.map(([id, label]) => {
    const rec = (recorded as Rec[]).find(r => r.id === id)!, v = normalize(rec.report, label)
    const flag = v.flags.find(f => f.severity === 'block')
    return { id, label, lines: lines(rec.report, v), v, finding: flag ? flag.text.split(/(?<=\.)\s/)[0] : 'No red flags on the checks that ran.' }
  }), [])
  const [run, setRun] = useState(0)
  const [held, setHeld] = useState(false)
  const [shown, setShown] = useState(reduced ? 99 : 0)
  useEffect(() => {
    if (reduced) return
    const total = runs[run].lines.length + 1
    setShown(0)
    const timers = Array.from({ length: total }, (_, i) => window.setTimeout(() => setShown(i + 1), 500 + i * 520))
    if (!held) timers.push(window.setTimeout(() => setRun(r => (r + 1) % runs.length), 500 + total * 520 + 3200))
    return () => timers.forEach(clearTimeout)
  }, [run, held])
  const r = runs[run], done = shown > r.lines.length
  return (
    <figure className="console" aria-label="Recorded Touchstone audit runs">
      <div className="console-tabs" role="tablist" aria-label="Recorded run">
        {runs.map((x, i) => <button key={x.id} role="tab" aria-selected={run === i} onClick={() => { setHeld(true); setRun(i) }}>{x.label}</button>)}
      </div>
      <div className="console-body">
        <ol className="console-log" key={r.id}>
          {r.lines.map((l, i) => (
            <li key={l.key} className={i < shown ? 'on' : ''}><span>{l.key}</span><b className={l.tone}>{l.value}</b></li>
          ))}
        </ol>
        <div className={`console-verdict${done ? ' on' : ''}`}>
          <Rating grade={done ? r.v.grade : '—'} />
          <p>{r.finding}</p>
          <small>{r.v.perItem > 0 ? `Estimated value $${Math.round(r.v.perItem)} an item at $${r.v.dollarsPerPoint!.toLocaleString('en-US')} a point, the buyer's assumption` : 'Not priced'}</small>
        </div>
      </div>
      <figcaption>Recorded engine run, October 30, 2026</figcaption>
    </figure>
  )
}

/* ---------- One chart: reward climbs while accuracy on new problems falls ---------- */
function RunChart() {
  const env = vendors.find(e => e.id === 'quickgrade_arith') ?? vendors[0]
  const rung = env.rungs[truth]
  const [narrow, setNarrow] = useState(() => matchMedia('(max-width: 720px)').matches)
  useEffect(() => { const m = matchMedia('(max-width: 720px)'), on = () => setNarrow(m.matches); m.addEventListener('change', on); return () => m.removeEventListener('change', on) }, [])
  const W = narrow ? 560 : 1200, H = narrow ? 400 : 420, L = narrow ? 56 : 44, R = narrow ? 4 : 150, T = 16, B = 32
  const reward = rung.curve.map(v => v * 100)
  const accuracy = reward.map((_, i) => rung.heldout_before + (rung.heldout_after - rung.heldout_before) * (i / (reward.length - 1)))
  const x = (i: number) => L + (i / (reward.length - 1)) * (W - L - R)
  const y = (v: number) => T + (1 - v / 100) * (H - T - B)
  const path = (vals: number[]) => vals.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ')
  const [ref, seen] = useSeen<HTMLElement>()
  const box = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState<number | null>(null)
  const onMove = (e: React.PointerEvent) => {
    const r = box.current!.getBoundingClientRect(), f = ((e.clientX - r.left) / r.width * W - L) / (W - L - R)
    setHover(f < 0 || f > 1 ? null : Math.round(f * (reward.length - 1)))
  }
  const draw = reduced ? {} : { initial: { pathLength: 0 }, animate: { pathLength: seen ? 1 : 0 }, transition: { duration: 1.4, ease: 'easeInOut' as const } }
  const last = reward.length - 1
  return (
    <figure className="chart" ref={ref}>
      <div ref={box} onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Training reward climbs to ${reward[last].toFixed(0)}% while accuracy on new problems falls to ${accuracy[last].toFixed(0)}%`}>
          {[0, 50, 100].map(g => <g key={g}><line x1={L} x2={W - R} y1={y(g)} y2={y(g)} /><text x={L - 12} y={y(g) + 5} textAnchor="end">{g}%</text></g>)}
          <text x={L} y={H - 6}>step 0</text><text x={W - R} y={H - 6} textAnchor="end">step 1,000</text>
          {hover !== null && <line className="cursor" x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} />}
          <motion.path className="reward" d={path(reward)} {...draw} />
          <motion.path className="truth" d={path(accuracy)} {...draw} />
          <text className="end reward" x={narrow ? W - R : W - R + 14} y={y(reward[last]) + (narrow ? 34 : 6)} textAnchor={narrow ? 'end' : 'start'}>Reward {(hover === null ? reward[last] : reward[hover]).toFixed(0)}%</text>
          <text className="end truth" x={narrow ? W - R : W - R + 14} y={y(accuracy[last]) + (narrow ? -14 : 6)} textAnchor={narrow ? 'end' : 'start'}>New problems {(hover === null ? accuracy[last] : accuracy[hover]).toFixed(0)}%</text>
        </svg>
      </div>
      <figcaption>Sample run on {env.name}</figcaption>
    </figure>
  )
}

const RESULTS: [string, string, string][] = [
  ['92%', 'of problems caught', 'Blind test, on test cases'],
  ['95%', 'of flags correct', 'Blind test, on test cases'],
  ['0', 'false alarms in 28 clean real samples', 'Numeric and code checks'],
]
const STEPS: [string, string, string][] = [
  ['Seal', 'The seller\'s tasks go into a sealed sandbox. You get results, never the tasks, and we sell no training material.', '5,000 items sealed, 3,504 unique'],
  ['Screen', 'Grader probes, overlap and label checks run first. A blocking problem can end the audit before any training.', '\'hedge: right then wrong\' collects 100% reward'],
  ['Train', 'Small open models train on the material against a placebo, then face private problems they never saw.', '135M net gain +7.3 pts, range +1.7 to +12.9'],
  ['Report', 'A grade, the gain with its range, and an estimated value, all stated at the size we measured.', 'Grade A, estimated $76 an item'],
]

function Step({ title, text, output }: { title: string; text: string; output: string }) {
  const [ref, seen] = useSeen<HTMLLIElement>()
  return <li ref={ref} className={seen ? 'on' : ''}><h3>{title}</h3><p>{text}</p><code>{output}</code></li>
}

export default function Home() {
  return (
    <>
      <section className="hero dark">
        <div className="wrap">
          <h1>Don't buy training material blind.</h1>
          <div className="hero-row">
            <p className="lede">Touchstone audits RL environments and post-training material before you pay. We catch broken graders, copied tasks and reward that never reaches new problems.</p>
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
            <h2>Training material is expensive. Finding out it didn't work is worse.</h2>
            <p>A high reward can hide a model that learned nothing. The first line is what a seller shows you. The second is what you are paying for.</p>
          </div>
          <RunChart />
        </div>
      </section>

      <section className="band how">
        <div className="wrap">
          <div className="how-head">
            <h2>Small experiments, before the big spend.</h2>
            <p>Every audit runs the same way, on every vendor.</p>
            <a className="more" href="#method">Read the method</a>
          </div>
          <ol className="steps">{STEPS.map(([title, text, output]) => <Step key={title} title={title} text={text} output={output} />)}</ol>
        </div>
      </section>

      <Close title="Know before you train." text="Send us the environment or dataset you're considering. We'll scope a pilot audit with you." />
    </>
  )
}
