import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { AnimatePresence, motion, useScroll, useSpring } from 'motion/react'
import { data, vendors, base, truth, signed, pct, money, params, ROADMAP, FOUNDERS, REQUEST_FORM_URL, type Env } from '../data'
import NumberFlow from '@number-flow/react'
import { Alert, Check, Close, Count, Faq, Panel, Rating, Reveal, RequestButton, reduced } from '../ui'
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
                      <td><Rating grade={e.grade} compact /></td>
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
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap', padding: '20px 24px', borderBottom: '1px solid var(--line)' }}>
        <Rating grade={env.grade} layoutId="detail-rating" /><h3 style={{ fontSize: 26 }}>{env.name}</h3>
      </div>
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
    ['Scale, Surge, Mercor', 30, 14, 'Build and sell training data and RL environments.', 'A seller can\'t neutrally grade its own product.'],
    ['Patronus AI', 22, 74, 'AI evaluation and testing tools.', 'Evaluates models and apps, not the value of training data.'],
    ['In-house ML teams', 74, 44, 'Run their own trial training.', 'Can\'t test before the vendor hands over data, or compare vendors.'],
    ['Touchstone', 84, 86, 'Independently appraises training data before purchase.', 'Neutral, before you buy, at small-model cost.'],
  ]
  const others: [string, string, string][] = [
    ['RL List', 'Ranks 42 environment vendors', 'Desk research on funding and press. Runs no training.'],
    ['CodeSOTA', 'Ranks environments as evals', 'Measures how well they separate models, not training gains. Also sells environments.'],
    ['Delphik (posttrain.dev)', 'Calls for independent environment audits', 'A position paper with no product yet. The closest one to watch.'],
    ['DatologyAI, Cleanlab', 'Data curation and cleaning', 'Preprocessing for your own data, not a neutral check before purchase.'],
    ['Human Native, Troveo', 'Data licensing marketplaces', 'Check rights, not training value.'],
    ['Prime Intellect Hub', 'Open hub of environments', 'Distribution, not valuation. A source of environments for our first tests.'],
  ]
  return (
    <>
      <Head title={<>Training data is the new <span className="transfer">compute bill.</span></>} text="The money in AI training is moving from compute to data and RL environments. Nobody can check what they're buying." />
      <section className="wrap">
        <Reveal className="cols">
          <div><b><Count value="$1B" /></b><p>a year reportedly spent on human-curated data by each leading lab</p><small>TechCrunch, Pebblous</small></div>
          <div><b><Count value="$2B" /></b><p>annualized revenue at Mercor; AfterQuery reached about $100M in a year</p><small>Pebblous market map</small></div>
          <div><b><Count value="$20k" /></b><p>for a single RL task at the high end; most sell for $200 to $2,000</p><small>Price summary citing Epoch AI</small></div>
        </Reveal>
        <Reveal className="cols" delay={.1}>
          <div><b>$1B+</b><p>on RL environments over a year, reportedly discussed by Anthropic</p><small>TechCrunch</small></div>
          <div><b><Count value="55%" /></b><p>of AI cloud spend goes to inference in 2026, driven by fine-tuned models in production</p><small>Gartner, via TechTimes</small></div>
          <div><b>0</b><p>independent auditors of training value in current market maps</p><small>DataGravity, Future Stack</small></div>
        </Reveal>
      </section>
      <section className="section">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>Two honest sizes.</h2></Reveal><Reveal delay={.1}><p>A useful business either way. A venture-scale one only if Touchstone becomes the rating labs require.</p></Reveal></div>
          <Reveal className="scenario">
            <div><b>$5M–$10M</b><span>a year, near term</span><p>About 50 environment vendors and 15 to 20 serious buyers, paying per appraisal and by subscription.</p></div>
            <div className="up"><b>$30M–$100M+</b><span>a year, as the standard</span><p>If environment and post-training spend reaches a few billion dollars a year by 2027–28, a verification layer taking 1–3% of it. Before any marketplace.</p></div>
          </Reveal>
          <p className="note">Our estimates. Lab data spend is forecast to pass $100B a year by 2030; that is a forecast, not a transaction.</p>
        </div>
      </section>
      <section className="section flush">
        <div className="wrap two" style={{ alignItems: 'center' }}>
          <Reveal><h2>Close neighbours, <span className="transfer">different job.</span></h2><p className="lede">Sellers can't referee. Evaluators test models, not data. In-house teams find out after they've paid. Nobody sells an independent, training-based valuation of RL environments.</p></Reveal>
          <Reveal delay={.1}>
            <Panel title="where each player sits" meta="illustrative">
              <div className="map panel-body" style={{ margin: 20 }}>
                <div style={{ position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px)', backgroundSize: '25% 25%', opacity: .7 }} />
                <span className="map-axis" style={{ left: 8, top: 8 }}>independent</span><span className="map-axis" style={{ right: 8, bottom: 8 }}>measures training value</span>
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
      <section className="section">
        <div className="wrap">
          <div className="rows-table">
            {[...players.map(([n, , , w, g]) => [n, w, g] as [string, string, string]), ...others].map(([name, what, gap], i) => (
              <Reveal key={name} delay={Math.min(i * .04, .3)}><div className={`row${name === 'Touchstone' ? ' us' : ''}`}><b>{name}</b><p>{what}</p><p>{gap}</p></div></Reveal>
            ))}
          </div>
          <p className="note">A web scan, not a patent search. A lab could be doing this privately in-house.</p>
        </div>
      </section>
      <section className="section flush">
        <div className="wrap two">
          <Reveal><h2>A moat that grows <span className="transfer">with every report.</span></h2></Reveal>
          <Reveal delay={.1}><ol className="steps-list">
            <li><div><b>Neutral by design</b><p>We never sell data or environments, so we can rate every vendor, Scale included.</p></div></li>
            <li><div><b>A private test suite</b><p>No vendor can train on it. It becomes more valuable the longer it stays clean.</p></div></li>
            <li><div><b>Every appraisal teaches us</b><p>After a few hundred, our forecasts of what transfers beat anyone's guesswork.</p></div></li>
            <li><div><b>The first standard sticks</b><p>In ratings and audits, the first credible standard tends to win.</p></div></li>
          </ol></Reveal>
        </div>
      </section>
      <Close title="A verification layer for a new market." text="Talk to us about a pilot appraisal." />
    </>
  )
}

/* ---------------- Pricing ---------------- */
export function Pricing() {
  const [tasks, setTasks] = useState(5000), [price, setPrice] = useState(800), [waste, setWaste] = useState(30)
  const spend = tasks * price, risk = spend * waste / 100, cost = 25000
  const fill = (v: number, min: number, max: number) => ({ '--fill': `${(v - min) / (max - min) * 100}%` } as React.CSSProperties)
  const tiers: [string, string, string, string, string[], boolean][] = [
    ['Grader audit', 'Find the exploits', '$5k–$15k', 'per environment', ['Every exploit probe run against the grader', 'Share of reward won without solving', 'Fix list for the vendor'], false],
    ['Full appraisal', 'Know what it\'s worth', '$10k–$50k', 'per environment', ['Sealed training at several model sizes', 'Transfer to private problems, overlap, exploits', 'Forecast at your size and fair price per task'], true],
    ['Subscription', 'Every environment, always', '$100k–$250k', 'per year', ['Side-by-side comparison of environments', 'Re-tests as environments change', 'Vendor ratings over time'], false],
  ]
  return (
    <>
      <Head title={<>Costs less than <span className="transfer">one bad run.</span></>} text="An appraisal runs on small open models, so it costs a fraction of the data it checks." />
      <section className="wrap tiers">
        {tiers.map(([name, sub, amount, per, items, featured], i) => (
          <Reveal key={name} delay={i * .08}>
            <Panel className={`tier${featured ? ' featured' : ''}`} title={name.toLowerCase()} meta={featured ? 'most teams start here' : undefined}>
              <div className="tier-body">
                <h3 style={{ fontSize: 24 }}>{sub}</h3><div className="amount">{amount} <small>{per}</small></div>
                <ul className="list" style={{ marginTop: 0 }}>{items.map(t => <li key={t}><Check />{t}</li>)}</ul>
                <div><RequestButton label={featured ? 'Request an appraisal' : 'Talk to us'} /></div>
              </div>
            </Panel>
          </Reveal>
        ))}
      </section>
      <section className="section">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>The unit economics.</h2></Reveal><Reveal delay={.1}><p>Small models keep compute cheap, which is the whole point.</p></Reveal></div>
          <Reveal className="cols">
            <div><b>$300–$2k</b><p>of GPU per appraisal on small open models</p><small>our estimate</small></div>
            <div><b><Count value="80%" />–90%</b><p>gross margin on a full appraisal</p><small>our estimate</small></div>
            <div><b>1–3%</b><p>fee on purchases later, if Touchstone becomes the standard rating</p><small>phase 3</small></div>
          </Reveal>
        </div>
      </section>
      <section className="section flush">
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
                <div className="out"><small>total spend</small><b className="num"><NumberFlow value={spend} format={{ style: 'currency', currency: 'USD', maximumFractionDigits: 0 }} /></b></div>
                <div className="out"><small>money at risk</small><b className="num bad"><NumberFlow value={risk} format={{ style: 'currency', currency: 'USD', maximumFractionDigits: 0 }} /></b></div>
                <div className="out"><small>at risk per dollar of appraisal</small><b className="num transfer"><NumberFlow value={risk / cost} format={{ minimumFractionDigits: 1, maximumFractionDigits: 1 }} suffix="×" /></b></div>
              </div>
            </div>
          </Panel></Reveal>
        </div>
      </section>
      <section className="section"><div className="wrap"><Reveal><Faq items={[
        ['Who pays, the buyer or the vendor?', 'Either. Buyers appraise before purchase. Vendors commission a neutral rating to win contracts and justify their price; small vendors can\'t afford their own transfer studies.'],
        ['Doesn\'t a vendor paying create a conflict?', 'It can, the same way it does for ratings agencies. We publish and pre-register the method, fix the training recipe, and sell buyer-side subscriptions so both sides pay.'],
        ['Why start with a grader audit?', 'It is the cheapest test and catches the most common failure. A broken grader makes the rest of the appraisal moot.'],
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
      <Head title={<>Less wasted training. <span className="transfer">More real learning.</span></>} text="We help AI companies spend less on ineffective training and get more useful learning from their compute. We're starting with RL environments, and will support training decisions across every type of AI model." />
      <section className="section flush">
        <div className="wrap two" style={{ alignItems: 'center' }}>
          <Reveal><h2>Why <span className="transfer">Touchstone.</span></h2></Reveal>
          <Reveal delay={.1}><p className="lede" style={{ marginTop: 0 }}>A touchstone is the dark stone merchants used to test gold before they bought it. Rub the metal across the stone, read the streak, and you know what it's worth. We do the same for training data.</p></Reveal>
        </div>
      </section>
      <section className="section">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>What we've decided.</h2></Reveal></div>
          <div className="cols">
            <Reveal><div><b style={{ fontSize: 26 }}>Appraisal, not cleaning</b><p>We check data before purchase. We don't curate or clean your own data; that is a different business.</p></div></Reveal>
            <Reveal delay={.08}><div><b style={{ fontSize: 26 }}>Neutral, always</b><p>We never sell data or environments, so we can rate every vendor, including the biggest.</p></div></Reveal>
            <Reveal delay={.16}><div><b style={{ fontSize: 26 }}>GPU time is the saving</b><p>The value is in the training runs you don't waste, not in cheaper compute.</p></div></Reveal>
          </div>
        </div>
      </section>
      {FOUNDERS.length > 0 && (
        <section className="section flush"><div className="wrap"><h2>Who is building this.</h2>
          <div className="cols" style={{ marginTop: 40 }}>{FOUNDERS.map(([n, r, w, l]) => <div key={n}><b style={{ fontSize: 28 }}>{n}</b><p className="dim">{r}</p><p>{w}</p>{l && <a className="textlink" href={l} target="_blank" rel="noopener">Profile</a>}</div>)}</div></div></section>
      )}
      <section className="section flush">
        <div className="wrap two" style={{ alignItems: 'start' }}>
          <Reveal><h2>Where we are, <span className="transfer">and what's next.</span></h2><p className="lede">The order matters: cheap proof first, expensive proof only once people say they'd pay.</p></Reveal>
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
          <Reveal><h2>Where this <span className="transfer">could lead.</span></h2></Reveal>
          <Reveal delay={.1}><ol className="steps-list">
            <li><div><b>Forecasting post-training runs</b><p>Before a $20k–$500k fine-tuning or RL run, predict from cheap pilots whether it will pay off.</p></div></li>
            <li><div><b>Forecasting behaviour before deployment</b><p>The same small-to-large method, applied to how a model will behave before it ships.</p></div></li>
            <li><div><b>A marketplace priced by appraised value</b><p>Escrowed purchases where the price follows the measured value.</p></div></li>
          </ol></Reveal>
        </div>
      </section>
      <section className="section flush"><div className="wrap"><div className="section-head"><Reveal><h2>Fair questions.</h2></Reveal></div><Reveal><Faq items={[
        ['Do you ever see the vendor\'s tasks?', 'They stay in a sealed sandbox. Buyers get results, never the tasks.'],
        ['Why trust small models?', 'Published research shows small runs predict which data wins at scale. For RL environments it is unproven, and our first test checks it. Every report shows how well the forecast held up.'],
        ['What can you test today?', 'RL environments with automatic graders. Post-training datasets and other data types come next.'],
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
