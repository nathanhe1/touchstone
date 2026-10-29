import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'motion/react'
import NumberFlow from '@number-flow/react'
import { data, vendors, base, truth, signed, pct, money, params, type Env } from '../data'
import { Close, Count, DUR, Panel, Rating, Reveal, RequestButton, ease, reduced } from '../ui'
import { Evidence, Exploits, Section } from './Sections'

const verdict = (e: Env) =>
  e.is_public_baseline ? 'The free baseline every purchase is compared against.'
  : e.hackability.score >= .2 ? 'Fix the grader before anyone buys this.'
  : e.redundancy.public_overlap >= .5 ? 'Mostly already free. Not worth the asking price.'
  : e.actual_at_truth < 0 ? 'Do not buy: the model gets worse at new problems.'
  : `Worth buying at up to ${money(e.fair_value_per_task)} a task.`

/* ---------- The report: switch environment and the appraisal runs stage by stage ---------- */
export function ReportSample({ demo = false }: { demo?: boolean }) {
  const envs = [...vendors, base]
  const [id, setId] = useState(envs[0].id)
  const [phase, setPhase] = useState(demo && !reduced ? 0 : 4)
  const [runId, setRunId] = useState(demo ? 1 : 0)
  const [touched, setTouched] = useState(!demo)
  const env = envs.find(e => e.id === id)!
  const rung = env.rungs[truth]
  // Each run reveals one stage at a time; skeletons hold the space until a number exists.
  useEffect(() => {
    if (reduced || runId === 0) return
    setPhase(0)
    const timers = [1, 2, 3, 4].map(k => window.setTimeout(() => setPhase(k), k * 600))
    return () => timers.forEach(clearTimeout)
  }, [runId])
  // As a demo, it moves to the next environment until the visitor picks one.
  useEffect(() => {
    if (touched || reduced || phase < 4) return
    const t = window.setTimeout(() => { const i = envs.findIndex(e => e.id === id); setId(envs[(i + 1) % (envs.length - 1)].id); setRunId(n => n + 1) }, 4000)
    return () => clearTimeout(t)
  }, [phase, touched, id])
  const pick = (next: string) => { setTouched(true); setId(next); setRunId(n => n + 1) }
  const pctF = { style: 'percent', maximumFractionDigits: 0 } as const
  const ptsF = { signDisplay: 'always', minimumFractionDigits: 1, maximumFractionDigits: 1 } as const
  const usd = { style: 'currency', currency: 'USD', maximumFractionDigits: 0 } as const
  const rows: [string, string, number, React.ReactNode, string][] = [
    ['Learns the environment', 'Reward on its own tasks, before and after', 1, <><NumberFlow value={rung.env_reward_before} format={pctF} /> to <NumberFlow value={rung.env_reward_after} format={pctF} /></>, ''],
    ['Better on new problems', 'Accuracy change on the private suite', 2, <NumberFlow value={env.actual_at_truth} format={ptsF} suffix=" pts" />, env.actual_at_truth < 0 ? 'bad' : 'good'],
    ['Reward won by exploits', 'Junk answers that still scored', 2, <NumberFlow value={env.hackability.score} format={pctF} />, env.hackability.score >= .2 ? 'bad' : ''],
    ['Already in free data', 'Overlap with public sets', 2, <NumberFlow value={env.redundancy.public_overlap} format={pctF} />, env.redundancy.public_overlap >= .5 ? 'bad' : ''],
    ['Forecast at the largest size', `90% range ${signed(env.forecast.lo)} to ${signed(env.forecast.hi)} pts`, 3, <NumberFlow value={env.forecast.forecast} format={ptsF} suffix=" pts" />, ''],
    ['Fair value per task', 'Compared with free practice data', 4, <NumberFlow value={env.fair_value_per_task} format={usd} />, 'transfer'],
  ]
  const stages = ['Seal', 'Train', 'Measure', 'Price']
  return (
    <Panel title="appraisal report" meta={phase < 4 ? 'running' : `sealed ${env.sha256.slice(0, 10)}`}>
      <div className="tabs" role="tablist" aria-label="Environment">
        {envs.map(e => <button key={e.id} className="tab" role="tab" aria-selected={e.id === id} onClick={() => pick(e.id)}>{e.name.replace(' (free)', '')}</button>)}
      </div>
      <div className="runbar" aria-live="polite">
        {stages.map((st, i) => <span key={st} className={phase > i ? 'done' : phase === i ? 'active' : ''}><i />{st}</span>)}
      </div>
      <div className="report">
        <div>
          {rows.map(([label, sub, stage, value, tone]) => (
            <div className="metric" key={label}>
              <span>{label}</span><small>{sub}</small>
              <b className={tone}>{phase >= stage ? value : <span className="skeleton" />}</b>
            </div>
          ))}
        </div>
        <div className="report-side">
          <div>
            <span className="label">{env.grade === '—' ? 'not graded' : 'grade'}</span>
            <div style={{ marginTop: 8 }}><Rating grade={phase >= 4 ? env.grade : ''} /></div>
          </div>
          <div className="by-size" aria-label="Change on new problems at each model size">
            <span className="label">change on new problems by model size</span>
            {Object.keys(data.ladder).map(k => {
              const g = env.rungs[k].heldout_after - env.rungs[k].heldout_before
              const w = phase >= 2 ? Math.min(Math.abs(g) / 12, 1) * 50 : 0
              return (
                <div className="bs-row" key={k}>
                  <span>{k}</span>
                  <div className="bs-track"><motion.i className={g < 0 ? 'neg' : 'pos'} animate={{ width: `${w}%` }} transition={{ duration: DUR.slow, ease }} /></div>
                  <b className={g < 0 ? 'bad' : 'good'}>{phase >= 2 ? signed(g) : <span className="skeleton" style={{ width: 40, height: 16 }} />}</b>
                </div>
              )
            })}
          </div>
          <div>
            <span className="label">verdict</span>
            <div style={{ marginTop: 8 }}>{phase >= 4 ? <p className="verdict-line">{verdict(env)}</p> : <span className="skeleton wide" />}</div>
          </div>
          {phase >= 4 && env.flags.length > 0 && <ul className="flags">{env.flags.map(f => <li key={f} className="bad">{f}</li>)}</ul>}
        </div>
      </div>
    </Panel>
  )
}

/* ---------- A real training run: reward climbs while accuracy on new problems falls ---------- */
function RunChart() {
  const env = vendors.find(e => e.id === 'quickgrade_arith') ?? vendors[0]
  const rung = env.rungs[truth]
  const W = 960, H = 300, L = 36, B = 24
  const x = (i: number, n: number) => L + (i / (n - 1)) * (W - L - 8)
  const y = (v: number) => 8 + (1 - v / 100) * (H - B - 8)
  const reward = rung.curve.map(v => v * 100)
  const accuracy = reward.map((_, i) => rung.heldout_before + (rung.heldout_after - rung.heldout_before) * (i / (reward.length - 1)))
  const path = (vals: number[]) => vals.map((v, i) => `${i ? 'L' : 'M'}${x(i, vals.length).toFixed(1)} ${y(v).toFixed(1)}`).join(' ')
  const end = reward.length - 1
  const box = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState<{ x: number; i: number } | null>(null)
  const onMove = (e: React.PointerEvent) => {
    const r = box.current!.getBoundingClientRect()
    const fx = ((e.clientX - r.left) / r.width * W - L) / (W - L - 8)
    if (fx < 0 || fx > 1) return setHover(null)
    setHover({ x: e.clientX - r.left, i: Math.round(fx * end) })
  }
  const draw = reduced ? {} : { initial: { pathLength: 0 }, whileInView: { pathLength: 1 }, viewport: { once: true }, transition: { duration: 1.2, ease } }
  return (
    <Panel title={env.name} meta={<span className="legend"><span><i style={{ background: 'var(--reward)' }} />Training reward</span><span><i style={{ background: 'var(--transfer)' }} />Accuracy on new problems</span></span>}>
      <div className="run-chart panel-body" ref={box} onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        {hover && (<>
          <span className="xhair" style={{ left: hover.x }} />
          <span className="xtip" style={{ left: Math.min(hover.x + 12, (box.current?.clientWidth ?? 600) - 190) }}>
            step {Math.round(hover.i / end * 1000)}<b className="reward">reward {reward[hover.i].toFixed(1)}%</b><b className="transfer">new problems {accuracy[hover.i].toFixed(1)}%</b>
          </span>
        </>)}
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Training reward climbs from ${reward[0].toFixed(0)}% to ${reward[end].toFixed(0)}% while accuracy on new problems falls from ${accuracy[0].toFixed(1)}% to ${accuracy[end].toFixed(1)}%`}>
          {[0, 25, 50, 75, 100].map(g => (<g key={g}><line className="grid-line" x1={L} x2={W - 8} y1={y(g)} y2={y(g)} /><text className="axis-text" x={L - 8} y={y(g) + 4} textAnchor="end">{g}</text></g>))}
          <text className="axis-text" x={L} y={H - 4}>step 0</text><text className="axis-text" x={W - 8} y={H - 4} textAnchor="end">1,000</text>
          <motion.path d={path(reward)} className="curve" stroke="var(--reward)" {...draw} />
          <motion.path d={path(accuracy)} className="curve" stroke="var(--transfer)" {...draw} />
          <text className="end-label" x={W - 8} y={y(reward[end]) - 10} textAnchor="end" fill="var(--reward)">{reward[end].toFixed(1)}%</text>
          <text className="end-label" x={W - 8} y={y(accuracy[end]) + 20} textAnchor="end" fill="var(--transfer)">{accuracy[end].toFixed(1)}%</text>
        </svg>
      </div>
      <div className="run-foot">
        <div><small>steps</small><b>1,000</b></div>
        <div><small>training reward</small><b className="reward">{reward[end].toFixed(1)}%</b></div>
        <div><small>new problems</small><b className="transfer">{accuracy[end].toFixed(1)}%</b></div>
        <div className="verdict"><small>verdict</small><b>{pct(env.hackability.score)} of junk answers scored</b></div>
      </div>
    </Panel>
  )
}

/* ---------- Every environment: reward against real change at the largest model ---------- */
function Proof() {
  const envs = [...vendors, base]
  const limit = 8
  return (
    <Panel title="six environments · largest model" meta="change on new problems, pts">
      <div className="proof-row head"><span>environment</span><span>change on new problems</span><span>reward</span><span>change</span></div>
      {envs.map(e => {
        const c = e.actual_at_truth, share = Math.min(Math.abs(c) / limit, 1) * 50
        return (
          <div className="proof-row" key={e.id}>
            <span>{e.name}</span>
            <div className="proof-track">
              <motion.span className="proof-bar" style={{ left: c < 0 ? `${50 - share}%` : '50%', width: `${share}%`, background: c < 0 ? 'var(--bad)' : 'var(--transfer)', transformOrigin: c < 0 ? 'right' : 'left' }}
                initial={reduced ? false : { scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }} transition={{ duration: DUR.slow, ease }} />
            </div>
            <span className="num reward">{pct(e.rungs[truth].env_reward_after)}</span>
            <span className={`num ${c < 0 ? 'bad' : 'transfer'}`}>{signed(c)}</span>
          </div>
        )
      })}
    </Panel>
  )
}

/* ---------- How it works: four steps, each with a plain diagram ---------- */
function Steps() {
  const env = vendors[0]
  const sizes = Object.entries(data.ladder)
  const biggest = Math.max(...sizes.map(([, v]) => v))
  const visuals = [
    <div className="sealed">{['task_0001', 'task_0002', 'task_0003'].map(t => <div key={t}><span>{t}</span><span>sealed</span></div>)}<div><span>sha256</span><span>{env.sha256.slice(0, 8)}</span></div></div>,
    <div className="atoms">{sizes.map(([k, v]) => { const d = 8 + Math.sqrt(v / biggest) * 56; return <div className="atom" key={k}><div className="sphere" style={{ width: d, height: d }} /><small>{k} · {params(v)}</small></div> })}</div>,
    <div className="mini-bars">{([['New problems', `${signed(env.actual_at_truth)} pts`, .6, 'var(--transfer)'], ['Exploit reward', pct(env.hackability.score), .02, 'var(--bad)'], ['Already free', pct(env.redundancy.public_overlap), env.redundancy.public_overlap, 'var(--reward)']] as const).map(([l, v, w, c]) => (
      <div key={l}><span>{l}</span><span>{v}</span><i><motion.span style={{ width: `${w * 100}%`, background: c }} initial={reduced ? false : { scaleX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }} transition={{ duration: DUR.slow, ease }} /></i></div>))}</div>,
    <div className="price-tag"><b><Count value={money(env.fair_value_per_task)} /></b><small>fair value per task</small><div style={{ marginTop: 16, display: 'flex', justifyContent: 'center' }}><Rating grade={env.grade} compact /></div></div>,
  ]
  const steps: [string, string][] = [
    ['Seal', 'The vendor uploads the environment to a sealed sandbox. Buyers see results, never the tasks.'],
    ['Train small', 'Open models train on it at four sizes with one fixed recipe.'],
    ['Measure', 'The models face private problems they never trained on, and we probe the grader for exploits.'],
    ['Price', 'We forecast the gain at your model size and price each task against free alternatives.'],
  ]
  return (
    <ol className="process">
      {steps.map(([title, text], i) => (
        <li key={title}><h3>{title}</h3><p>{text}</p><div className="visual">{visuals[i]}</div></li>
      ))}
    </ol>
  )
}

/* ---------- Compare: rank four environments three ways ---------- */
const ENVS = [
  { name: 'Env A · coding agent', reward: 92, transfer: 2.0, value: .4 },
  { name: 'Env B · math reasoning', reward: 81, transfer: 9.1, value: 3.1 },
  { name: 'Env C · web browsing', reward: 75, transfer: 6.2, value: 1.8 },
  { name: 'Env D · tool use', reward: 70, transfer: 4.0, value: 1.1 },
]
type Key = 'reward' | 'transfer' | 'value'
const KEYS: [Key, string, string, (v: number) => string, string][] = [
  ['reward', 'Training reward', 'By training reward, Env A looks like the best buy.', v => `${v}%`, 'var(--reward)'],
  ['transfer', 'Improvement', 'By improvement on new problems, Env B leads by a wide margin.', v => `+${v.toFixed(1)} pts`, 'var(--transfer)'],
  ['value', 'Value per $1k', 'Per dollar, Env B delivers almost 8 times what Env A does.', v => `${v.toFixed(1)} pts`, 'var(--transfer)'],
]
function Compare() {
  const [k, setK] = useState<Key>('reward')
  const meta = KEYS.find(x => x[0] === k)!
  const rows = useMemo(() => [...ENVS].sort((a, b) => b[k] - a[k]), [k])
  const max = rows[0][k]
  return (
    <div>
      <div className="seg" role="tablist" aria-label="Rank environments by">
        {KEYS.map(([key, label]) => <button key={key} role="tab" aria-selected={k === key} onClick={() => setK(key)}>{label}</button>)}
      </div>
      <div className="cmp">
        {rows.map(r => (
          <motion.div layout key={r.name} className="cmp-row" transition={{ duration: DUR.standard, ease }}>
            <span>{r.name}</span>
            <div className="cmp-bar"><motion.i animate={{ width: `${(r[k] / max) * 100}%` }} style={{ background: meta[4] }} transition={{ duration: DUR.slow, ease }} /></div>
            <span className="num">{meta[3](r[k])}</span>
          </motion.div>
        ))}
      </div>
      <p className="cmp-note">{meta[2]}</p>
    </div>
  )
}

export default function Home() {
  const enter = (delay: number) => reduced ? {} : { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: DUR.standard, delay, ease } }
  return (
    <>
      <section className="hero">
        <div className="wrap">
          <div className="hero-copy">
            <div>
              <motion.h1 {...enter(0)}>Don't buy training material blind.</motion.h1>
              <motion.p className="lede" {...enter(.05)}>Touchstone trains small models on an RL environment before you pay for it, then tells you whether it will make your model better and what each task is worth.</motion.p>
              <motion.div className="actions" {...enter(.1)}><RequestButton /><a className="btn secondary" href="#product">How it works</a></motion.div>
            </div>
            <motion.div {...enter(.15)}>
              <div className="hero-fact"><b>Sealed</b><span>Vendor tasks never leave the sandbox. Buyers see results only.</span></div>
              <div className="hero-fact"><b>Independent</b><span>Touchstone sells no training material, so it can rate every vendor.</span></div>
            </motion.div>
          </div>
          <motion.div {...enter(.2)}><ReportSample demo /></motion.div>
        </div>
      </section>

      <Section title="Training material is expensive. Finding out it didn't work is worse." text="A high training reward can hide a model that learned nothing. In our appraisals, most environments pushed reward up while the model got worse at new problems.">
        <Reveal><RunChart /></Reveal>
        <div style={{ height: 24 }} />
        <Reveal><Proof /></Reveal>
        <div className="facts">
          {([['$2,000', 'for a single RL task, and up to $20k at the high end'], ['4–5×', 'more for an exclusive deal, so a bad buy costs more'], ['Weeks', 'of GPU time before a full training run shows it failed'], ['0', 'independent checks between the vendor\'s claim and your purchase']] as const).map(([big, text]) => (
            <div key={big}><b>{big.startsWith('$') ? <Count value={big} /> : big}</b><p>{text}</p></div>
          ))}
        </div>
      </Section>

      <Section title="Small experiments, before the big spend." text="An appraisal costs a fraction of one training run and finishes before you sign.">
        <Steps />
      </Section>

      <Section title="Rank by real improvement and the order flips." text="Training reward and real improvement rank the same four environments differently. Switch the ranking to see it.">
        <Compare />
      </Section>

      <Section title="We test the grader before your model learns to game it." text="A model learns any shortcut a grader allows. Every grader faces the same set of junk answers, and the report shows how much each one paid.">
        <Exploits />
      </Section>

      <section className="section">
        <div className="wrap two">
          <div><h2>For teams buying training material</h2>
            <ul className="list">{['Test an environment before you pay for it', 'Compare vendors on one private test', 'Stop paying for tasks your model can game'].map(t => <li key={t}>{t}</li>)}</ul></div>
          <div><h2>For vendors selling it</h2>
            <ul className="list">{['A neutral rating buyers trust more than self-reported results', 'Find grader exploits before a customer does', 'Back your price with measured value'].map(t => <li key={t}>{t}</li>)}</ul></div>
        </div>
      </section>

      <Section title="Built on published research." text="Data value varies enormously, small runs can rank it, and today the evidence buyers see comes from the people selling.">
        <Evidence />
      </Section>

      <Close title="Know before you train." text="Send us the environment you're considering. We'll scope a pilot appraisal with you." />
    </>
  )
}
