import { useMemo, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { data, vendors, base, truth, signed, pct, money, params, ROADMAP, FOUNDERS, REQUEST_FORM_URL, type Env } from '../data'
import NumberFlow from '@number-flow/react'
import { Close, Count, DUR, Faq, Panel, Rating, Reveal, RequestButton, ease, reduced } from '../ui'
import { ReportSample } from './Home'


function Head({ title, text, children }: { title: ReactNode; text: string; children?: ReactNode }) {
  return (
    <header className="page-head wrap">
      <motion.h1 initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: DUR.standard, ease }}>{title}</motion.h1>
      <motion.p className="lede" initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: DUR.standard, delay: .05, ease }}>{text}</motion.p>
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
          <div className="section-head"><Reveal><h2>The technical details.</h2></Reveal><Reveal delay={.1}><p>Fixed models, a fixed recipe and a private test suite. The method is the same for every vendor.</p></Reveal></div>
          <Reveal><Faq items={[
            ['Which models do you train?', 'A fixed family of small open models with one published RL recipe. Models like 0.5B, 1.5B and 3B, with results projected to your model size.'],
            ['How do you test transfer?', 'On a private held-out suite that no vendor ever sees or trains on. No vendor can train on it, so no vendor can game it.'],
            ['How do you find reward exploits?', 'Known exploit probes, such as empty answers, format gaming and editing tests, plus adversarial policies trained against the grader.'],
            ['What can you test today?', 'RL environments with automatic graders. Post-training datasets and other training material are next.'],
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
      <Head title="Six environments. One test." text="Six RL environments, each hiding a different failure. Touchstone appraised all six and priced the one worth buying." />
      <section className="wrap">
        <Reveal>
          <Panel title="sample report · largest model" meta="select a row · sort by any column">
            <div className="scroll-x">
              <table className="table click">
                <thead><tr><th>environment</th>{th('grade', 'grade')}{th('change', 'change on new problems')}{th('hack', 'exploit reward', true)}{th('overlap', 'already free', true)}{th('value', 'value / task', true)}</tr></thead>
                <motion.tbody layout>
                  {rows.map(e => (
                    <motion.tr layout key={e.id} className={e.id === sel ? 'sel' : ''} onClick={() => setSel(e.id)} transition={{ duration: DUR.standard, ease }}>
                      <td>{e.name}</td>
                      <td><Rating grade={e.grade} compact /></td>
                      <td><div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                        <div className="mini diverge" style={{ flex: 1 }}><i style={{ left: e.actual_at_truth < 0 ? `${50 + (e.actual_at_truth / 8) * 50}%` : '50%', width: `${Math.min(Math.abs(e.actual_at_truth) / 8, 1) * 50}%`, background: e.actual_at_truth < 0 ? 'var(--bad)' : 'var(--transfer)' }} /></div>
                        <span className={`num ${e.actual_at_truth < 0 ? 'bad' : 'transfer'}`}>{signed(e.actual_at_truth)}</span></div></td>
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
            <motion.div key={sel} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: DUR.standard, ease }}>
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
    <Panel title={`certificate · ${env.name}`} meta={`sealed ${env.sha256.slice(0, 12)}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap', padding: 24, borderBottom: '1px solid var(--line)' }}>
        <Rating grade={env.grade} /><h3>{env.name}</h3>
      </div>
      <div className="detail">
        <div>
          <span className="label">accuracy on new problems, before and after training</span>
          <div style={{ display: 'grid', gap: 16, marginTop: 24 }}>
            {rungs.map(([size, r], i) => {
              const from = r.heldout_before / top * 100, to = r.heldout_after / top * 100, up = to >= from
              return (
                <div key={size} style={{ display: 'grid', gridTemplateColumns: '96px minmax(0,1fr) 64px', gap: 16, alignItems: 'center' }}>
                  <span className="num dim" style={{ fontSize: 12, fontFamily: 'var(--mono)' }}>{size} · {params(r.params)}</span>
                  <div style={{ position: 'relative', height: 14 }}>
                    <div style={{ position: 'absolute', inset: '7px 0', height: 1, background: 'var(--line-2)' }} />
                    <motion.div style={{ position: 'absolute', top: 6, height: 2, left: `${Math.min(from, to)}%`, width: `${Math.abs(to - from)}%`, background: up ? 'var(--transfer)' : 'var(--bad)', transformOrigin: up ? 'left' : 'right' }}
                      initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: i * .05, duration: DUR.slow, ease }} />
                    <span style={{ position: 'absolute', top: 3, left: `calc(${from}% - 4px)`, width: 8, height: 8, borderRadius: '50%', border: '1px solid var(--ink-2)', background: 'var(--panel)' }} />
                    <span style={{ position: 'absolute', top: 3, left: `calc(${to}% - 4px)`, width: 8, height: 8, borderRadius: '50%', background: up ? 'var(--transfer)' : 'var(--bad)' }} />
                  </div>
                  <span className={`num ${up ? 'transfer' : 'bad'}`} style={{ textAlign: 'right', fontSize: 14 }}>{signed(r.heldout_after - r.heldout_before)}</span>
                </div>
              )
            })}
          </div>
          <p className="note">Open dot: before training. Filled dot: after.</p>
        </div>
        <div>
          <span className="label">reward paid for each exploit probe</span>
          <div style={{ marginTop: 16 }}>
            {Object.entries(env.hackability.per_exploit).map(([name, v], i) => (
              <div className="probe" key={name}><span>{name}</span>
                <div className="mini"><motion.i style={{ left: 0, background: v >= .2 ? 'var(--bad)' : 'var(--ink-3)', width: `${Math.max(v * 100, 1)}%`, transformOrigin: 'left' }} initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: i * .04, duration: DUR.slow, ease }} /></div>
                <span className={`num ${v >= .2 ? 'bad' : ''}`} style={{ textAlign: 'right' }}>{pct(v)}</span></div>
            ))}
          </div>
          <ul className="flags" style={{ marginTop: 24 }}>
            {(env.flags.length ? env.flags : ['No appraisal flags']).map(f => <li key={f} className={env.flags.length ? 'bad' : ''}>{f}</li>)}
          </ul>
        </div>
      </div>
    </Panel>
  )
}

/* ---------------- Market ---------------- */
export function Market() {
  return (
    <>
      <Head title={<>Training material is the new <span className="transfer">compute bill.</span></>} text="The money in AI training is moving from compute to data and RL environments. Nobody can check what they're buying." />
      <section className="wrap" style={{ paddingBottom: 96 }}>
        <Reveal className="rows">
          {([['$1B', 'a year spent on human-curated training material by each leading lab', 'TechCrunch, Pebblous'], ['$2B', 'annualized revenue at Mercor; AfterQuery reached about $100M in a year', 'Pebblous market map'], ['$20k', 'for a single RL task at the high end; most sell for $200 to $2,000', 'Epoch AI price summary'], ['$1B+', 'on RL environments in a single year at one frontier lab', 'TechCrunch'], ['55%', 'of AI cloud spend goes to inference in 2026, driven by fine-tuned models in production', 'Gartner, via TechTimes'], ['0', 'independent auditors of training value in the market today', 'DataGravity, Future Stack']] as const).map(([big, text, src]) => (
            <div key={big}><span className="big">{/^[$\d]/.test(big) && big !== '0' ? <Count value={big} /> : big}</span><p>{text}</p><span>{src}</span></div>
          ))}
        </Reveal>
      </section>
      <section className="section">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>A market <span className="transfer">with no referee.</span></h2></Reveal><Reveal delay={.1}><p>Every dollar spent on training material is a purchase someone should check first.</p></Reveal></div>
          <Reveal className="scenario">
            <div><b>$5M–$10M</b><span>a year from appraisals</span><p>About 50 environment vendors and 15 to 20 serious buyers, paying per appraisal and by subscription.</p></div>
            <div className="up"><b>$30M–$100M+</b><span>a year as the standard rating</span><p>As environment and post-training spend reaches billions a year, a verification layer earning 1–3% of every purchase.</p></div>
          </Reveal>
          <p className="note">Lab spend on training material is forecast to pass $100B a year by 2030.</p>
        </div>
      </section>
      <section className="section flush">
        <div className="wrap two">
          <Reveal><h2>A moat that grows <span className="transfer">with every report.</span></h2></Reveal>
          <Reveal delay={.1}><ol className="steps-list">
            <li><div><b>Neutral by design</b><p>We never sell training material, so we can rate every vendor, including the largest.</p></div></li>
            <li><div><b>A private test suite</b><p>No vendor can train on it. It becomes more valuable the longer it stays clean.</p></div></li>
            <li><div><b>Every appraisal teaches us</b><p>Every result sharpens our forecasts of what transfers. The data compounds.</p></div></li>
            <li><div><b>The first standard sticks</b><p>In ratings and audits, the first trusted standard becomes the default.</p></div></li>
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
  const offers: [string, string, string, string[], string][] = [
    ['Grader audit', '$5k–$15k', 'per environment', ['Every exploit probe run against the grader', 'Share of reward won without solving the task', 'A fix list the vendor can act on'], 'Talk to us'],
    ['Full appraisal', '$10k–$50k', 'per environment', ['Sealed training at four model sizes', 'Transfer to private problems, overlap with free data, exploits', 'Forecast at your model size and a fair price per task'], 'Request an appraisal'],
  ]
  return (
    <>
      <Head title={<>Costs less than <span className="transfer">one bad run.</span></>} text="An appraisal runs on small open models, so it costs a fraction of the material it checks." />
      <section className="wrap" style={{ paddingBottom: 96 }}>
        <Reveal>
          <div className="offers">
            {offers.map(([name, amount, per, items, cta]) => (
              <div className="offer" key={name}>
                <span className="label">{name}</span>
                <div className="amount">{amount}<small>{per}</small></div>
                <ul className="list">{items.map(t => <li key={t}>{t}</li>)}</ul>
                <RequestButton label={cta} secondary={cta === 'Talk to us'} />
              </div>
            ))}
          </div>
          <div className="subscription"><span><b>Rating every environment you use.</b> A subscription re-tests environments as they change and tracks vendors over time.</span><span className="num">$100k–$250k a year</span></div>
        </Reveal>
      </section>
      <section className="section">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>The unit economics.</h2></Reveal><Reveal delay={.1}><p>Small models keep compute cheap, which is the whole point.</p></Reveal></div>
          <Reveal className="rows">
            <div><span className="big">$300–$2k</span><p>of GPU per appraisal on small open models</p><span>compute cost</span></div>
            <div><span className="big">80–90%</span><p>gross margin on a full appraisal</p><span>margin</span></div>
            <div><span className="big">1–3%</span><p>fee on purchases once Touchstone is the standard rating</p><span>at scale</span></div>
          </Reveal>
        </div>
      </section>
      <section className="section flush">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>What's at stake on your purchase.</h2></Reveal><Reveal delay={.1}><p>Move the sliders to match a purchase you're considering, against a $25k appraisal.</p></Reveal></div>
          <Reveal><Panel title="purchase at risk" meta="calculator">
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
        ['Why start with a grader audit?', 'It is the cheapest test and catches the most common failure. A broken grader makes the rest of the appraisal moot.'],
        ['Can we pilot first?', 'Yes. Every new customer starts with a pilot appraisal.'],
      ]} /></Reveal></div></section>
      <Close title="Price the risk before you pay." text="Tell us what you're about to buy, and we'll scope the appraisal." />
    </>
  )
}

/* ---------------- Company ---------------- */
export function Company() {
  return (
    <>
      <Head title={<>Less wasted training. <span className="transfer">More real learning.</span></>} text="We help AI companies spend less on ineffective training and get more useful learning from their compute. We start with RL environments and expand to every kind of training material." />
      <section className="section flush">
        <div className="wrap two" style={{ alignItems: 'center' }}>
          <Reveal><h2>Why <span className="transfer">Touchstone.</span></h2></Reveal>
          <Reveal delay={.05}><p className="lede" style={{ marginTop: 0 }}>A touchstone is the dark stone merchants used to test gold before they bought it. Rub the metal across the stone, read the streak, and you know what it's worth. We do the same for training material.</p></Reveal>
        </div>
      </section>
      <section className="section">
        <div className="wrap">
          <div className="section-head"><Reveal><h2>What we've decided.</h2></Reveal></div>
          <Reveal className="rows">
            <div><b>Appraisal only</b><p>We value training material before purchase. We do not clean, label or sell it.</p></div>
            <div><b>Neutral</b><p>We never sell training material, so we can rate every vendor, including the largest.</p></div>
            <div><b>GPU time is the saving</b><p>The saving is the training runs a lab no longer wastes on material that does not transfer.</p></div>
          </Reveal>
        </div>
      </section>
      {FOUNDERS.length > 0 && (
        <section className="section flush"><div className="wrap"><h2>Who is building this.</h2>
          <div className="rows" style={{ marginTop: 48 }}>{FOUNDERS.map(([n, r, w, l]) => <div key={n}><b>{n}<br /><span className="dim">{r}</span></b><p>{w}</p>{l ? <a className="textlink" href={l} target="_blank" rel="noopener">Profile</a> : <span />}</div>)}</div></div></section>
      )}
      <section className="section flush">
        <div className="wrap two" style={{ alignItems: 'start' }}>
          <Reveal><h2>Where we are, <span className="transfer">and what's next.</span></h2><p className="lede">A working pipeline today, and a clear path to the standard rating for training material.</p></Reveal>
          <ol className="timeline">
            {ROADMAP.map(([stage, title, text]) => (
              <li key={title} className={stage.toLowerCase()}><span className="stage-name">{stage}</span><div><h3>{title}</h3><p>{text}</p></div></li>
            ))}
          </ol>
        </div>
      </section>
      <section className="section">
        <div className="wrap two">
          <Reveal><h2>Where this <span className="transfer">leads.</span></h2></Reveal>
          <Reveal delay={.1}><ol className="steps-list">
            <li><div><b>Forecasting post-training runs</b><p>Before a $20k–$500k fine-tuning or RL run, predict from cheap pilots whether it will pay off.</p></div></li>
            <li><div><b>Forecasting behaviour before deployment</b><p>The same small-to-large method, applied to how a model will behave before it ships.</p></div></li>
            <li><div><b>A marketplace priced by appraised value</b><p>Escrowed purchases where the price follows the measured value.</p></div></li>
          </ol></Reveal>
        </div>
      </section>
      <section className="section flush"><div className="wrap"><div className="section-head"><Reveal><h2>Questions.</h2></Reveal></div><Reveal><Faq items={[
        ['Do you ever see the vendor\'s tasks?', 'They stay in a sealed sandbox. Buyers get results, never the tasks.'],
        ['Why trust small models?', 'Published research shows small runs predict which data wins at scale. Touchstone applies that to RL environments, and every report shows its forecast next to the result.'],
        ['What can you test today?', 'RL environments with automatic graders. Post-training datasets and other training material are next.'],
        ['Are you independent?', 'Yes. We never sell training material, and we publish our method.'],
      ]} /></Reveal></div></section>
      <Close title="Building the neutral standard for training material." text="Talk to us about a pilot." />
    </>
  )
}

/* ---------------- Request ---------------- */
export function Request() {
  return (
    <>
      <Head title="Tell us what you're about to buy." text="We're running a small number of pilot appraisals. Here's what helps us scope one." />
      <section className="wrap two" style={{ alignItems: 'start', paddingBottom: 96 }}>
        <Reveal><ol className="steps-list">
          <li><div><b>The environment or dataset</b><p>What it trains, how big it is and who sells it.</p></div></li>
          <li><div><b>The decision</b><p>What you'd pay, and what you need to know before you do.</p></div></li>
          <li><div><b>Your model</b><p>Rough size and what you're training it to do, so we forecast at your scale.</p></div></li>
        </ol></Reveal>
        <Reveal delay={.1}><Panel title="pilot appraisals" meta="limited">
          <div style={{ padding: 24, display: 'grid', gap: 16 }}>
            <h3>For AI teams buying RL environments or post-training material, and for vendors who want a neutral rating.</h3>
            {REQUEST_FORM_URL ? <div><RequestButton label="Open the request form" /></div> : <p className="dim" style={{ margin: 0 }}>The request form opens shortly. Check back here for the link.</p>}
          </div>
        </Panel></Reveal>
      </section>
    </>
  )
}
