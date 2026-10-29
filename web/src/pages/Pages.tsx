import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { AnimatePresence, motion, useScroll, useSpring } from 'motion/react'
import { data, vendors, base, truth, signed, pct, money, params, gradeClass, ROADMAP, FOUNDERS, REQUEST_FORM_URL, type Env } from '../data'
import { Alert, Check, Close, Count, Faq, Panel, Reveal, RequestButton, reduced } from '../ui'
import { ReportSample } from './Home'

const ease = [.16, 1, .3, 1] as const

function Head({ title, text, children }: { title: ReactNode; text: string; children?: ReactNode }) {
  return (
    <header className="page-head wrap">
      <motion.h1 initial={reduced ? false : { opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease }}>{title}</motion.h1>
      <motion.p className="lede" initial={reduced ? false : { opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: .1, ease }}>{text}</motion.p>
      {children}
    </header>
  )
}

/* ---------------- Product ---------------- */
export function Product() {
  return (
    <>
      <Head title="One sealed test. Six answers." text="Every appraisal ends in one report. It tells you what an environment teaches, whether it can be gamed, what you already have, and what it is worth at your model size." />
      <section className="wrap"><Reveal><ReportSample /></Reveal></section>
      <section className="section">
        <div className="wrap two">
          <Reveal><h2>From upload to verdict.</h2><p className="lede">The vendor never shows you its tasks, and you never have to take its word for the results.</p></Reveal>
          <Reveal delay={.1}>
            <ol className="steps-list">
              <li><div><b>Sealed intake</b><p>The seller uploads tasks, tools and grader. They are fingerprinted and never leave the sandbox.</p></div></li>
              <li><div><b>Standard training</b><p>A fixed family of small open models, such as 0.5B, 1.5B and 3B, trained with one published recipe.</p></div></li>
              <li><div><b>Private tests</b><p>The trained models face a held-out suite no vendor has seen, and adversarial probes try to game the grader.</p></div></li>
              <li><div><b>Forecast and price</b><p>We fit how the gain grows with model size, project it to yours, and price each task against free alternatives.</p></div></li>
            </ol>
          </Reveal>
        </div>
      </section>
      <section className="section flush">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>The technical details.</h2></Reveal><Reveal delay={.1}><p>Our forecast didn't rank well in the demo run, and we say so. <a className="textlink" href="#forecast">See the forecast check</a>.</p></Reveal></div>
          <Reveal><Faq items={[
            ['Which models do you train?', 'A fixed family of small open models with one published RL recipe. The demo uses tiny CPU models; production runs use models like 0.5B, 1.5B and 3B.'],
            ['How do you test transfer?', 'On a private held-out suite that no vendor ever sees or trains on. That suite is what keeps the result honest.'],
            ['How do you find reward exploits?', 'Known exploit probes, such as empty answers, format gaming and editing tests, plus adversarial policies trained against the grader.'],
            ['What can you test today?', 'RL environments with automatic graders. Post-training datasets and other data types come next.'],
          ]} /></Reveal>
        </div>
      </section>
      <Close title="See it on your environment." text="We're running a small number of pilot appraisals." />
    </>
  )
}

/* ---------------- Sample report: sortable table plus detail ---------------- */
type SortKey = 'grade' | 'change' | 'hack' | 'overlap' | 'value'
export function Report() {
  const all = [...vendors, base]
  const [sort, setSort] = useState<SortKey>('grade')
  const [sel, setSel] = useState(all[0].id)
  const value = (e: Env, k: SortKey) => k === 'grade' ? -'ABCDF—'.indexOf(e.grade) : k === 'change' ? e.actual_at_truth : k === 'hack' ? e.hackability.score : k === 'overlap' ? e.redundancy.public_overlap : e.fair_value_per_task
  const rows = useMemo(() => [...all].sort((a, b) => value(b, sort) - value(a, sort)), [sort])
  const env = all.find(e => e.id === sel)!
  const th = (k: SortKey, label: string, right = false) => (
    <th className={right ? 'r' : ''} aria-sort={sort === k ? 'descending' : 'none'}><button onClick={() => setSort(k)}>{label}{sort === k && <svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ marginLeft: 6, verticalAlign: -1 }}><path d="M4 6l4 4 4-4" /></svg>}</button></th>
  )
  return (
    <>
      <Head title="Six environments. One test." text="Six fictional RL environments, each built to show a common failure, appraised with tiny models. The pipeline is real; the vendors and numbers are examples." />
      <section className="wrap">
        <Reveal>
          <Panel title="sample report · largest model" meta="click a row · click a column to sort">
            <div className="scroll-x">
              <table className="table">
                <thead><tr><th>environment</th>{th('grade', 'grade')}{th('change', 'change on new problems')}{th('hack', 'exploit reward', true)}{th('overlap', 'already free', true)}{th('value', 'value / task', true)}</tr></thead>
                <motion.tbody layout>
                  {rows.map(e => (
                    <motion.tr layout key={e.id} className={e.id === sel ? 'sel' : ''} onClick={() => setSel(e.id)} transition={{ type: 'spring', stiffness: 300, damping: 30 }}>
                      <td style={{ fontWeight: 500 }}>{e.name}</td>
                      <td><span className={`chip grade ${gradeClass(e.grade)}`} style={{ width: 'auto', height: 28, fontSize: 14, borderRadius: 8 }}>{e.grade}</span></td>
                      <td><div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                        <div className="mini diverge" style={{ flex: 1 }}><i style={{ left: e.actual_at_truth < 0 ? `${50 + (e.actual_at_truth / 8) * 50}%` : '50%', width: `${Math.min(Math.abs(e.actual_at_truth) / 8, 1) * 50}%`, background: e.actual_at_truth < 0 ? 'var(--bad)' : 'var(--good)' }} /></div>
                        <span className={`num ${e.actual_at_truth < 0 ? 'bad' : 'good'}`}>{signed(e.actual_at_truth)}</span></div></td>
                      <td className={`r num ${e.hackability.score >= .2 ? 'bad' : ''}`}>{pct(e.hackability.score)}</td>
                      <td className={`r num ${e.redundancy.public_overlap >= .5 ? 'bad' : ''}`}>{pct(e.redundancy.public_overlap)}</td>
                      <td className="r num">{money(e.fair_value_per_task)}</td>
                    </motion.tr>
                  ))}
                </motion.tbody>
              </table>
            </div>
          </Panel>
        </Reveal>
      </section>
      <section className="section">
        <div className="wrap">
          <AnimatePresence mode="wait">
            <motion.div key={sel} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: .4, ease }}>
              <Detail env={env} />
            </motion.div>
          </AnimatePresence>
        </div>
      </section>
      <Close title="Want this for a real environment?" text="Send us what you're considering buying." />
    </>
  )
}

function Detail({ env }: { env: Env }) {
  const rungs = Object.entries(env.rungs)
  const top = Math.max(...rungs.flatMap(([, r]) => [r.heldout_before, r.heldout_after]))
  return (
    <Panel title={<>certificate · <span style={{ color: 'var(--ink)' }}>{env.name}</span></>} meta={`sealed ${env.sha256.slice(0, 12)}`}>
      <div className="detail">
        <div>
          <h3>Accuracy on new problems, before → after training</h3>
          <div style={{ display: 'grid', gap: 18, marginTop: 24 }}>
            {rungs.map(([size, r], i) => {
              const from = r.heldout_before / top * 100, to = r.heldout_after / top * 100, up = to >= from
              return (
                <div key={size} style={{ display: 'grid', gridTemplateColumns: '64px minmax(0,1fr) 64px', gap: 14, alignItems: 'center' }}>
                  <span className="num dim" style={{ fontSize: 13 }}>{size} · {params(r.params)}</span>
                  <div style={{ position: 'relative', height: 14 }}>
                    <div style={{ position: 'absolute', inset: '6px 0', background: 'var(--line)', borderRadius: 1 }} />
                    <motion.div style={{ position: 'absolute', top: 5, height: 4, borderRadius: 2, left: `${Math.min(from, to)}%`, width: `${Math.abs(to - from)}%`, background: up ? 'var(--good)' : 'var(--bad)', transformOrigin: up ? 'left' : 'right' }}
                      initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: .1 + i * .1, duration: .8, ease }} />
                    <span style={{ position: 'absolute', top: 2, left: `calc(${from}% - 5px)`, width: 10, height: 10, borderRadius: '50%', border: '2px solid var(--ink-2)', background: 'var(--ground)' }} />
                    <motion.span style={{ position: 'absolute', top: 1, left: `calc(${to}% - 6px)`, width: 12, height: 12, borderRadius: '50%', background: up ? 'var(--good)' : 'var(--bad)' }} initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: .7 + i * .1, type: 'spring' }} />
                  </div>
                  <span className={`num ${up ? 'good' : 'bad'}`} style={{ textAlign: 'right', fontSize: 14 }}>{signed(r.heldout_after - r.heldout_before)}</span>
                </div>
              )
            })}
          </div>
          <p className="note">Hollow dot: before training. Filled: after.</p>
        </div>
        <div>
          <h3>Would the grader reward a shortcut?</h3>
          <div style={{ marginTop: 18 }}>
            {Object.entries(env.hackability.per_exploit).map(([name, v], i) => (
              <div className="probe" key={name}><span>{name}</span>
                <div className="mini"><motion.i style={{ left: 0, background: v >= .2 ? 'var(--bad)' : 'var(--ink-3)', width: `${Math.max(v * 100, 1)}%`, transformOrigin: 'left' }} initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: .1 + i * .06, duration: .7, ease }} /></div>
                <span className={`num ${v >= .2 ? 'bad' : ''}`} style={{ textAlign: 'right' }}>{pct(v)}</span></div>
            ))}
          </div>
          <ul className="flags" style={{ marginTop: 22 }}>
            {(env.flags.length ? env.flags : ['No appraisal flags']).map(f => <li key={f}>{env.flags.length ? <span className="bad"><Alert /></span> : <span className="good"><Check /></span>}{f}</li>)}
          </ul>
        </div>
      </div>
    </Panel>
  )
}

/* ---------------- Forecast check ---------------- */
export function Forecast() {
  const v = data.validation
  const envs = vendors
  const lo = -20, hi = 12, W = 560, H = 400, P = 48
  const sx = (x: number) => P + (x - lo) / (hi - lo) * (W - P - 16)
  const sy = (y: number) => H - P - (y - lo) / (hi - lo) * (H - P - 16)
  const [hover, setHover] = useState<string | null>(null)
  const ticks = [-20, -15, -10, -5, 0, 5, 10]
  return (
    <>
      <Head title="Do small runs predict big ones?" text="Touchstone forecasts each environment's gain at your model size from small runs. Here we check those forecasts against the largest model in our demo." />
      <section className="wrap two" style={{ alignItems: 'start' }}>
        <Reveal>
          <Panel title="forecast vs measured · largest model" meta="hover a point">
            <div className="scatter panel-body">
              <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Forecast against measured change for six demo environments">
                {ticks.map(t => (<g key={t}><line className="grid-line" x1={sx(t)} x2={sx(t)} y1={sy(hi)} y2={sy(lo)} /><line className="grid-line" y1={sy(t)} y2={sy(t)} x1={sx(lo)} x2={sx(hi)} />
                  <text className="axis-text" x={sx(t)} y={H - P + 18} textAnchor="middle">{t > 0 ? `+${t}` : t}</text><text className="axis-text" x={P - 8} y={sy(t) + 4} textAnchor="end">{t > 0 ? `+${t}` : t}</text></g>))}
                <motion.line x1={sx(lo)} y1={sy(lo)} x2={sx(hi)} y2={sy(hi)} stroke="var(--ink-3)" strokeDasharray="5 5" initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: 1.2 }} />
                <text className="axis-text" x={sx(8)} y={sy(9.5)} textAnchor="middle" transform={`rotate(-38 ${sx(8)} ${sy(9.5)})`}>perfect forecast</text>
                {envs.map((e, i) => (
                  <g key={e.id} className="pt" onPointerEnter={() => setHover(e.id)} onPointerLeave={() => setHover(null)}>
                    <line x1={sx(e.forecast.forecast)} x2={sx(e.forecast.forecast)} y1={sy(e.actual_at_truth)} y2={sy(e.forecast.forecast)} stroke="var(--ink-3)" strokeDasharray="2 3" opacity={hover === e.id ? 1 : .4} />
                    <motion.circle cx={sx(e.forecast.forecast)} cy={sy(e.actual_at_truth)} r={hover === e.id ? 10 : 7} fill={e.actual_at_truth >= 0 ? 'var(--good)' : 'var(--bad)'} stroke="var(--ground)" strokeWidth="2"
                      initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }} transition={{ delay: .5 + i * .1, type: 'spring' }} />
                    {hover === e.id && <text x={sx(e.forecast.forecast) + 14} y={sy(e.actual_at_truth) - 10} fill="var(--ink)" fontSize="13">{e.name}: forecast {signed(e.forecast.forecast)}, measured {signed(e.actual_at_truth)}</text>}
                  </g>
                ))}
                <text className="axis-text" x={(W + P) / 2} y={H - 8} textAnchor="middle">forecast change, pts</text>
                <text className="axis-text" x={14} y={H / 2} textAnchor="middle" transform={`rotate(-90 14 ${H / 2})`}>measured change, pts</text>
              </svg>
            </div>
          </Panel>
        </Reveal>
        <Reveal delay={.1}>
          <div className="big-figure"><Count value={signed(v.spearman_forecast_vs_actual, 2)} /></div>
          <p className="lede" style={{ marginTop: 16 }}>Rank match between forecast and measured results. 1 means the same order, 0 means no match.</p>
          <p className="lede">In this demo the forecast didn't rank the six environments well. With tiny models and six sets that is a warning, not a verdict. The average miss was <b className="num">{v.mean_abs_error_pts.toFixed(1)} pts</b>.</p>
          <p className="lede">The research says small runs can predict big ones. Every Touchstone report will show how well its forecast held up, so you can judge it yourself.</p>
        </Reveal>
      </section>
      <div style={{ height: 120 }} />
      <Close title="Judge the evidence yourself." text="Every report shows its forecast track record." />
    </>
  )
}

/* ---------------- Market ---------------- */
export function Market() {
  const players: [string, number, number, string, string][] = [
    ['Scale AI', 30, 18, 'Provides training data and AI infrastructure.', 'Sells the data it would be grading.'],
    ['Patronus AI', 22, 74, 'Develops AI evaluation and testing tools.', 'Tests finished models, not the data that trains them.'],
    ['In-house ML teams', 74, 44, 'Run their own training experiments.', 'Learn the answer after buying, at full cost.'],
    ['Touchstone', 84, 86, 'Independently evaluates the value of training resources.', 'Before you buy, at small-model cost.'],
  ]
  return (
    <>
      <Head title="Training data is the new compute bill." text="AI companies are spending more on specialized data, RL and agent environments every year, with no neutral way to check what they are buying." />
      <section className="wrap">
        <Reveal className="cols">
          <div><b><Count value="$1B" /></b><p>a year reportedly spent on human-curated data by each leading lab</p><small>TechCrunch, market maps</small></div>
          <div><b><Count value="55%" /></b><p>of AI cloud spend goes to inference in 2026, driven by fine-tuned models</p><small>Gartner forecast</small></div>
          <div><b>0</b><p>independent auditors of training value in current market maps</p><small>Market maps</small></div>
        </Reveal>
      </section>
      <section className="section">
        <div className="wrap two" style={{ alignItems: 'center' }}>
          <Reveal><div className="big-figure">$30M–$100M+</div>
            <p className="lede">If environment and post-training data spend reaches a few billion dollars a year by 2027–28, a verification layer taking 1–3% is a $30M–$100M+ business, before any marketplace.</p><p className="note">Our estimate.</p></Reveal>
          <Reveal delay={.1}>
            <Panel title="where each player sits" meta="illustrative">
              <div className="map panel-body" style={{ margin: 20 }}>
                <div style={{ position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px)', backgroundSize: '25% 25%', opacity: .7 }} />
                <span className="map-axis" style={{ left: 8, top: 8 }}>independent ↑</span><span className="map-axis" style={{ right: 8, bottom: 8 }}>measures training value →</span>
                {players.map(([name, x, y], i) => (
                  <div key={name} className={`map-dot${name === 'Touchstone' ? ' us' : ''}${x > 60 ? ' left' : ''}`} style={{ left: `${x}%`, bottom: `${y}%` }}>
                    <motion.i initial={{ scale: 0 }} whileInView={{ scale: 1 }} viewport={{ once: true }} transition={{ delay: .2 + i * .15, type: 'spring', stiffness: 260, damping: 12 }} />
                    <motion.span initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ delay: .35 + i * .15 }}>{name}</motion.span>
                  </div>
                ))}
              </div>
            </Panel>
          </Reveal>
        </div>
      </section>
      <section className="section flush">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>Close neighbours, different job.</h2></Reveal></div>
          <div className="rows-table">
            {players.map(([name, , , what, gap], i) => (
              <Reveal key={name} delay={i * .05}><div className={`row${name === 'Touchstone' ? ' us' : ''}`}><b>{name}</b><p>{what}</p><p>{gap}</p></div></Reveal>
            ))}
          </div>
        </div>
      </section>
      <section className="section">
        <div className="wrap two">
          <Reveal><h2>A moat that grows with every report.</h2></Reveal>
          <Reveal delay={.1}><ol className="steps-list">
            <li><div><b>Neutral by design</b><p>We never sell data or environments, and we publish our method.</p></div></li>
            <li><div><b>A private test suite</b><p>No vendor can train on it. It becomes more valuable the longer it stays clean.</p></div></li>
            <li><div><b>Every appraisal teaches us</b><p>Each run sharpens which environment features actually transfer.</p></div></li>
            <li><div><b>The first standard sticks</b><p>In ratings and audits, the first credible standard tends to win.</p></div></li>
          </ol></Reveal>
        </div>
      </section>
      <section className="section flush">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>Small runs predict big ones.</h2></Reveal></div>
          <div className="cols">
            <Reveal><div><b>5%</b><p>Training on a well-chosen 5% of data can beat training on all of it.</p><a className="textlink" href="https://proceedings.mlr.press/v235/xia24c.html" target="_blank" rel="noopener">Xia et al., LESS · ICML 2024</a></div></Reveal>
            <Reveal delay={.1}><div><b>Small → large</b><p>Small, cheap experiments predict which data wins at larger scale.</p><a className="textlink" href="https://proceedings.mlr.press/v267/magnusson25a.html" target="_blank" rel="noopener">Magnusson et al., DataDecide · ICML 2025</a></div></Reveal>
            <Reveal delay={.2}><div><b>RL</b><p>How the leading data company thinks about RL environments.</p><a className="textlink" href="https://scale.com/blog/rl-environments" target="_blank" rel="noopener">Scale AI on RL environments</a></div></Reveal>
          </div>
        </div>
      </section>
      <Close title="A verification layer for a new market." text="Talk to us about a pilot." />
    </>
  )
}

/* ---------------- Pricing ---------------- */
export function Pricing() {
  const [tasks, setTasks] = useState(5000), [price, setPrice] = useState(800), [waste, setWaste] = useState(30)
  const spend = tasks * price, risk = spend * waste / 100, cost = 25000
  const fill = (v: number, min: number, max: number) => ({ '--fill': `${(v - min) / (max - min) * 100}%` } as React.CSSProperties)
  const riskSpring = useSpring(risk, { stiffness: 120, damping: 20 })
  const riskRef = useRef<HTMLElement>(null)
  useEffect(() => { riskSpring.set(risk) }, [risk])
  useEffect(() => riskSpring.on('change', v => { if (riskRef.current) riskRef.current.textContent = money(v) }), [])
  return (
    <>
      <Head title="Costs less than one bad run." text="Pay per appraisal when you're evaluating a purchase, or subscribe to test every environment you train on." />
      <section className="wrap plans">
        <Reveal><Panel className="plan" title="per appraisal">
          <div style={{ padding: 32, display: 'grid', gap: 16 }}>
            <h3 style={{ fontSize: 28 }}>Check one environment</h3><div className="amount">$10k–$50k <small>per appraisal</small></div>
            <ul className="list" style={{ marginTop: 0 }}>{['Sealed test of one environment', 'The full report', 'Forecast and fair value per task'].map(t => <li key={t}><Check />{t}</li>)}</ul>
            <div><RequestButton /></div></div></Panel></Reveal>
        <Reveal delay={.1}><Panel className="plan featured" title="subscription">
          <div style={{ padding: 32, display: 'grid', gap: 16 }}>
            <h3 style={{ fontSize: 28 }}>Every environment, always</h3><div className="amount">$50k–$250k <small>per year</small></div>
            <ul className="list" style={{ marginTop: 0 }}>{['Side-by-side comparison of environments', 'Re-tests as environments change', 'Vendor ratings over time'].map(t => <li key={t}><Check />{t}</li>)}</ul>
            <div><RequestButton label="Talk to us" /></div></div></Panel></Reveal>
      </section>
      <div className="wrap"><p className="note">Planned pilot pricing. Each appraisal uses roughly $1k–$5k of small-model compute.</p></div>
      <section className="section">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>What's at stake on your purchase.</h2></Reveal><Reveal delay={.1}><p>Move the sliders to match a purchase you're considering. Illustrative, using a $25k appraisal.</p></Reveal></div>
          <Reveal><Panel title="purchase at risk" meta="illustrative calculator">
            <div className="calc">
              <div>
                <div className="field"><label htmlFor="tasks">Tasks you're buying <output>{tasks.toLocaleString('en-US')}</output></label><input id="tasks" type="range" min={100} max={20000} step={100} value={tasks} style={fill(tasks, 100, 20000)} onChange={e => setTasks(+e.target.value)} /></div>
                <div className="field"><label htmlFor="price">Price per task <output>{money(price)}</output></label><input id="price" type="range" min={200} max={2000} step={50} value={price} style={fill(price, 200, 2000)} onChange={e => setPrice(+e.target.value)} /></div>
                <div className="field" style={{ marginBottom: 0 }}><label htmlFor="waste">Share that won't help your model <output>{waste}%</output></label><input id="waste" type="range" min={0} max={80} step={5} value={waste} style={fill(waste, 0, 80)} onChange={e => setWaste(+e.target.value)} /></div>
              </div>
              <div aria-live="polite">
                <div className="out"><small>total spend</small><b className="num">{money(spend)}</b></div>
                <div className="out"><small>money at risk</small><b ref={riskRef} className="num bad">{money(risk)}</b></div>
                <div className="out"><small>at risk per dollar of appraisal</small><b className="num transfer">{(risk / cost).toFixed(1)}×</b></div>
              </div>
            </div>
          </Panel></Reveal>
        </div>
      </section>
      <section className="section flush"><div className="wrap"><Reveal><Faq items={[
        ['Who pays, the buyer or the vendor?', 'Either. Buyers appraise before purchase; vendors commission a neutral rating to win contracts.'],
        ['Why does an appraisal cost this much?', 'It covers compute, the private test suite and a full report. It is still a small fraction of a single purchase.'],
        ['Can we pilot first?', 'Yes. Pilot appraisals are how we are starting.'],
      ]} /></Reveal></div></section>
      <Close title="Costs less than one bad run." text="Tell us what you're about to buy." />
    </>
  )
}

/* ---------------- Company ---------------- */
export function Company() {
  const ref = useRef<HTMLOListElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 70%', 'end 50%'] })
  const fill = useSpring(scrollYProgress, { stiffness: 120, damping: 24 })
  return (
    <>
      <Head title="Less wasted training. More real learning." text="Our goal is to help AI companies spend less on ineffective training and get more useful learning from their compute. We're starting with RL environments, and will support training decisions across every type of AI model." />
      {FOUNDERS.length > 0 && (
        <section className="section flush"><div className="wrap"><h2>Who is building this.</h2>
          <div className="cols" style={{ marginTop: 40 }}>{FOUNDERS.map(([n, r, w, l]) => <div key={n}><b style={{ fontSize: 28 }}>{n}</b><p className="dim">{r}</p><p>{w}</p>{l && <a className="textlink" href={l} target="_blank" rel="noopener">Profile</a>}</div>)}</div></div></section>
      )}
      <section className="section flush">
        <div className="wrap two" style={{ alignItems: 'start' }}>
          <Reveal><h2>Where we are, and where we're going.</h2><p className="lede">We'll keep this current as pilots start.</p></Reveal>
          <ol className="timeline" ref={ref}>
            <motion.span className="timeline-fill" style={{ scaleY: fill, height: 'calc(100% - 12px)' }} />
            {ROADMAP.map(([stage, title, text], i) => (
              <Reveal key={title} delay={i * .05}><li className={stage.toLowerCase()}><span className="stage-name">{stage}</span><h3>{title}</h3><p>{text}</p></li></Reveal>
            ))}
          </ol>
        </div>
      </section>
      <section className="section">
        <div className="wrap two">
          <Reveal><h2>Where this could lead.</h2></Reveal>
          <Reveal delay={.1}><ol className="steps-list">
            <li><div><b>Forecasting behaviour before deployment</b><p>The same small-to-large method, applied to predicting how a model will behave before it ships.</p></div></li>
            <li><div><b>Accessible ML infrastructure</b><p>Making it possible for anyone to practice and experiment with machine learning.</p></div></li>
          </ol></Reveal>
        </div>
      </section>
      <section className="section flush"><div className="wrap"><div className="section-head"><Reveal><h2>Fair questions.</h2></Reveal></div><Reveal><Faq items={[
        ['Do you ever see the vendor\'s tasks?', 'They stay in a sealed sandbox. Buyers get results, never the tasks.'],
        ['Why trust small models?', 'Published research shows small runs predict which data wins at scale. Every report also shows how well our forecast held up.'],
        ['Are you independent?', 'Yes. We never sell data or environments, and we publish our method.'],
      ]} /></Reveal></div></section>
      <Close title="Building the neutral standard for training data." text="Talk to us about a pilot." />
    </>
  )
}

/* ---------------- Request ---------------- */
export function Request() {
  return (
    <>
      <Head title="Tell us what you're about to buy." text="We're running a small number of pilot appraisals. Here's what helps us scope one." />
      <section className="wrap two" style={{ alignItems: 'start', paddingBottom: 140 }}>
        <Reveal><ol className="steps-list">
          <li><div><b>The environment or dataset</b><p>What it trains, how big it is and who sells it.</p></div></li>
          <li><div><b>The decision</b><p>What you'd pay, and what you need to know before you do.</p></div></li>
          <li><div><b>Your model</b><p>Rough size and what you're training it to do, so we forecast at your scale.</p></div></li>
        </ol></Reveal>
        <Reveal delay={.1}><Panel title="pilot appraisals" meta="limited">
          <div style={{ padding: 28, display: 'grid', gap: 16 }}>
            <h3>For AI teams buying RL environments or post-training data, and for vendors who want a neutral rating.</h3>
            {REQUEST_FORM_URL ? <div><RequestButton label="Open the request form" /></div> : <p className="dim" style={{ margin: 0 }}>The request form opens shortly. Check back here for the link.</p>}
          </div>
        </Panel></Reveal>
      </section>
    </>
  )
}
