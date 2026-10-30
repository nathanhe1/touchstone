import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import recorded from '../demo/recorded.json'
import { STAGES, STAGE_LABEL, findApi, getJob, listExamples, normalize, runExample, upload, type Example, type View } from '../demo/api'
import { Rating, reduced } from '../ui'

type Recorded = { id: string; name: string; kind: string; description: string; recorded: string; report: unknown; log: string[] }
const RECORDED = recorded as Recorded[]
const pct = (v: number) => `${(v * 100).toFixed(v > 0 && v < .1 ? 1 : 0)}%`
const pts = (v: number) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(1)}`
const usd = (v: number) => `$${Math.round(v).toLocaleString('en-US')}`
const ease = [.16, 1, .3, 1] as const

type Run = { source: 'live' | 'recorded'; name: string; stage: string; progress: number; log: string[]; status: 'running' | 'done' | 'error'; error?: string; report?: View }

/* ---------- The report, drawn from the normalized view ---------- */
function Report({ v }: { v: View }) {
  const blocked = v.flags.some(f => f.severity === 'block')
  const span = Math.max(12, ...v.gains.flatMap(g => [Math.abs(g.lo), Math.abs(g.hi)]), v.forecast ? Math.max(Math.abs(v.forecast.lo), Math.abs(v.forecast.hi)) : 0)
  const x = (n: number) => 50 + (n / span) * 50
  return (
    <motion.div className="demo-report" initial={reduced ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .5, ease }}>
      <div className="demo-verdict">
        <div><small>Grade</small><Rating grade={v.grade} /></div>
        <div><small>Fair value per item</small><b className={v.perItem > 0 ? 'transfer' : 'bad'}>{v.perItem > 0 ? usd(v.perItem) : 'Not priced'}</b>{v.blockedBy.length > 0
          ? <span className="dim">blocked by {v.blockedBy.join(', ').replace(/_/g, ' ')}</span>
          : v.dollarsPerPoint ? <span className="dim">at {usd(v.dollarsPerPoint)} per point, the buyer's assumption</span> : null}</div>
        <div><small>Net gain on held-out tasks{v.forecast ? `, ${v.forecast.where}` : ''}</small><b className={blocked ? 'muted' : (v.forecast?.point ?? 0) < 0 ? 'bad' : 'good'}>{v.forecast ? `${pts(v.forecast.point)} pts` : 'Not trained'}</b>{!v.forecast && v.screened && <span className="dim">Screening already ruled out a price</span>}{v.forecast && <span className="dim">{blocked ? 'Not trusted: see the red flags below' : `90% range ${pts(v.forecast.lo)} to ${pts(v.forecast.hi)}`}</span>}</div>
      </div>

      <div className="demo-flags">
        {v.flags.length === 0
          ? <p className="flag ok"><i />No red flags. The material passed every check.</p>
          : v.flags.map(f => <p key={f.text} className={`flag ${f.severity}`}><i />{f.text}</p>)}
      </div>

      <div className="demo-grid">
        <section>
          <h4>{v.gains.length ? 'Gain over a placebo run, by model size' : 'Training'}</h4>
          {v.gains.length > 0
            ? <p className="dim">Accuracy change on {v.heldout ? `${v.heldout.n} private held-out problems (${v.heldout.domain})` : 'the private held-out suite'}, after subtracting a control run.</p>
            : <p className="dim">No model was trained. Screening found a blocking problem first, so a training run would only spend GPU time.</p>}
          <div className="demo-bars">
            {v.gains.map(g => (
              <div key={g.size} className="demo-bar">
                <span>{g.size}</span>
                <div className="track"><i className="zero" /><i className="range" style={{ left: `${x(Math.min(g.lo, g.hi))}%`, width: `${x(Math.max(g.lo, g.hi)) - x(Math.min(g.lo, g.hi))}%` }} />
                  <motion.i className={`dot ${blocked ? 'muted' : g.net < 0 ? 'neg' : 'pos'}`} initial={reduced ? false : { left: '50%' }} animate={{ left: `${x(g.net)}%` }} transition={{ type: 'spring', stiffness: 120, damping: 18 }} /></div>
                <b className={blocked ? 'muted' : g.net < 0 ? 'bad' : 'good'}>{pts(g.net)}</b>
              </div>
            ))}
          </div>
          {v.forecast?.note && <p className="note">{v.forecast.note}</p>}
        </section>
        <section>
          <h4>Overlap and duplicates</h4>
          <dl className="demo-dl">
            <div><dt>Overlaps the private test suite</dt><dd className={v.overlap.suite >= .05 ? 'bad' : ''}>{pct(v.overlap.suite)}</dd></div>
            <div><dt>Already in free public data{v.overlap.publicBaseline ? ` (${v.overlap.publicBaseline})` : ''}</dt><dd className={v.overlap.public >= .5 ? 'bad' : ''}>{pct(v.overlap.public)}</dd></div>
            <div><dt>Duplicate items</dt><dd className={v.overlap.duplicates >= .1 ? 'bad' : ''}>{pct(v.overlap.duplicates)}</dd></div>
          </dl>
          {v.overlap.examples.length > 0 && <div className="demo-matches"><small>Matches found</small>{v.overlap.examples.map((m, i) => <p key={i}><span className="kind">{m.kind}</span>{m.item}</p>)}</div>}
        </section>
        {v.probes.length > 0 && (
          <section>
            <h4>Grader exploit probes</h4>
            <p className="dim">Share of reward each junk strategy collects without solving the task.</p>
            <div className="demo-probes">{v.probes.map(p => (
              <div key={p.name}><span>{p.name}</span><div className="track"><motion.i initial={reduced ? false : { width: 0 }} animate={{ width: `${Math.max(p.reward * 100, 1)}%` }} transition={{ duration: .8, ease }} className={p.reward >= .2 ? 'bad' : ''} /></div><b className={p.reward >= .2 ? 'bad' : ''}>{pct(p.reward)}</b></div>
            ))}</div>
            {v.transfer && <p className="note">Training reward rose {pts(v.transfer.envReward)} pts; held-out accuracy moved {pts(v.transfer.heldout)} pts.{v.transfer.gap ? ' The model learned the grader, not the skill.' : ''}</p>}
          </section>
        )}
      </div>
      <p className="demo-foot dim">{v.items ? `${v.items.toLocaleString('en-US')} items · ` : ''}{v.models.length ? `models: ${v.models.join(', ')} · ` : ''}{v.runtime ? `ran in ${v.runtime < 90 ? `${Math.round(v.runtime)} s` : `${Math.round(v.runtime / 60)} min`}` : ''}</p>
    </motion.div>
  )
}

/* ---------- Stage stepper ---------- */
function Stages({ stage, done, kind }: { stage: string; done: boolean; kind: string }) {
  const list = STAGES.filter(s => kind === 'env' || s !== 'probe')
  const at = list.indexOf(stage as typeof list[number])
  return (
    <ol className="demo-stages">
      {list.map((s, i) => {
        const st = done || i < at ? 'done' : i === at ? 'active' : ''
        return <li key={s} className={st}><i />{STAGE_LABEL[s]}</li>
      })}
    </ol>
  )
}

export default function Demo() {
  const [api, setApi] = useState<{ base: string; device: string } | null | undefined>(undefined)
  const [examples, setExamples] = useState<Example[]>([])
  const [run, setRun] = useState<Run | null>(null)
  const [busy, setBusy] = useState(false)
  const [over, setOver] = useState(false)
  const timers = useRef<number[]>([])
  const fileRef = useRef<HTMLInputElement>(null)
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => { findApi().then(a => { setApi(a); if (a) listExamples(a.base).then(setExamples).catch(() => setExamples([])) }) }, [])
  useEffect(() => () => timers.current.forEach(clearTimeout), [])
  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight }) }, [run?.log.length])

  const live = !!api
  const options = useMemo(() => live && examples.length ? examples.map(e => ({ id: e.id, name: e.name, kind: e.kind, description: e.description })) : RECORDED, [live, examples])

  // Polls a live job until it finishes.
  const follow = (base: string, id: string, name: string, kind: string) => {
    const tick = async () => {
      try {
        const j = await getJob(base, id)
        setRun({ source: 'live', name, stage: j.stage, progress: j.progress, log: j.log, status: j.status === 'done' ? 'done' : j.status === 'error' ? 'error' : 'running', error: j.error ?? undefined, report: j.report ? normalize(j.report, name) : undefined })
        if (j.status === 'done' || j.status === 'error') { setBusy(false); return }
      } catch (e) { setRun(r => r && { ...r, status: 'error', error: (e as Error).message }); setBusy(false); return }
      timers.current.push(window.setTimeout(tick, 1000))
    }
    setRun({ source: 'live', name, stage: 'validate', progress: 0, log: [`Queued ${name} (${kind})`], status: 'running' })
    tick()
  }

  // Replays a recorded engine run, stage by stage, when no backend is reachable.
  const replay = (rec: Recorded) => {
    timers.current.forEach(clearTimeout); timers.current = []
    const stages = STAGES.filter(s => rec.kind === 'env' || s !== 'probe')
    setRun({ source: 'recorded', name: rec.name, stage: stages[0], progress: 0, log: [], status: 'running' })
    stages.forEach((s, i) => timers.current.push(window.setTimeout(() => setRun(r => r && {
      ...r, stage: s, progress: (i + 1) / stages.length,
      log: rec.log.slice(0, Math.ceil((i + 1) / stages.length * rec.log.length)),
    }), i * (reduced ? 0 : 900))))
    timers.current.push(window.setTimeout(() => { setRun(r => r && { ...r, status: 'done', progress: 1, report: normalize(rec.report, rec.name) }); setBusy(false) }, stages.length * (reduced ? 0 : 900)))
  }

  const start = async (id: string) => {
    if (busy) return
    setBusy(true)
    const opt = options.find(o => o.id === id)!
    if (live) {
      try { const { job_id } = await runExample(api!.base, id); follow(api!.base, job_id, opt.name, opt.kind) }
      catch (e) { setRun({ source: 'live', name: opt.name, stage: 'validate', progress: 0, log: [], status: 'error', error: (e as Error).message }); setBusy(false) }
    } else replay(RECORDED.find(r => r.id === id)!)
  }

  const send = async (file: File) => {
    if (busy) return
    if (!/\.(jsonl|ndjson|json|zip|tar\.gz|tgz)$/i.test(file.name)) { setRun({ source: 'live', name: file.name, stage: 'validate', progress: 0, log: [], status: 'error', error: 'Upload a .jsonl dataset, or an RL environment as a .zip or .tar.gz folder.' }); return }
    if (file.size > 50e6) { setRun({ source: 'live', name: file.name, stage: 'validate', progress: 0, log: [], status: 'error', error: 'That file is over 50 MB.' }); return }
    if (!live) { setRun({ source: 'live', name: file.name, stage: 'validate', progress: 0, log: [], status: 'error', error: 'Live appraisals need the Touchstone engine, which this preview page cannot reach. Try one of the recorded runs, or open the demo from the Touchstone server.' }); return }
    setBusy(true)
    const kind = /\.jsonl|\.ndjson|\.json$/i.test(file.name) ? 'dataset' : 'env'
    try { const { job_id } = await upload(api!.base, file, kind); follow(api!.base, job_id, file.name, kind) }
    catch (e) { setRun({ source: 'live', name: file.name, stage: 'validate', progress: 0, log: [], status: 'error', error: (e as Error).message }); setBusy(false) }
  }

  const runKind = options.find(o => o.name === run?.name)?.kind ?? (run?.name.endsWith('.jsonl') ? 'dataset' : 'env')
  return (
    <>
      <header className="page-head wrap">
        <h1>Appraise training material, <span className="transfer">live.</span></h1>
        <p className="lede">Pick a dataset or RL environment, or upload your own. Touchstone checks it for leaks and copies, probes the grader, trains small models on it against a placebo, and prices what is left.</p>
        <p className="demo-status">
          {api === undefined ? <><i className="wait" />Connecting to the engine…</>
            : live ? <><i className="on" />Engine online · {api.device === 'cpu' ? 'CPU' : `GPU (${api.device})`} · runs take a few minutes</>
            : <><i className="off" />Engine not reachable from this page · replaying real recorded runs from Oct 30, 2026</>}
        </p>
      </header>
      <section className="wrap demo">
        <div className="demo-pick">
          <h3>Try an example</h3>
          <div className="demo-options">
            {options.map(o => (
              <button key={o.id} className={`demo-option${run?.name === o.name ? ' on' : ''}`} onClick={() => start(o.id)} disabled={busy} aria-busy={busy && run?.name === o.name}>
                <span className="demo-kind">{o.kind === 'env' ? 'RL environment' : 'Dataset'}</span>
                <b>{o.name}</b><span className="dim">{o.description}</span>
              </button>
            ))}
          </div>
          <h3 style={{ marginTop: 28 }}>Or upload your own</h3>
          <div className={`demo-drop${over ? ' over' : ''}`} onDragOver={e => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
            onDrop={e => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) send(f) }}
            onClick={() => fileRef.current?.click()} role="button" tabIndex={0} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') fileRef.current?.click() }}>
            <b>Drop a .jsonl dataset or a zipped RL environment</b>
            <span className="dim">One JSON example per line: {'{"prompt", "completion"}'} or {'{"messages": [...]}'}. Up to 50 MB.</span>
          </div>
          <input ref={fileRef} type="file" accept=".jsonl,.ndjson,.json,.zip,.tar.gz,.tgz" hidden onChange={e => { const f = e.target.files?.[0]; if (f) send(f); e.target.value = '' }} />
        </div>

        <div className="demo-run panel">
          <div className="panel-head"><span className="title">{run ? run.name : 'appraisal'}</span><span className="meta">{run ? (run.status === 'done' ? (run.source === 'recorded' ? 'recorded run' : 'done') : run.status === 'error' ? 'error' : `${Math.round(run.progress * 100)}%`) : 'idle'}</span></div>
          {!run && <div className="demo-empty"><p>Choose an example or upload a file to start an appraisal.</p></div>}
          {run && (<>
            <div className="demo-progress"><motion.i animate={{ width: `${Math.round((run.status === 'done' ? 1 : run.progress) * 100)}%` }} transition={{ duration: .4, ease }} /></div>
            <Stages stage={run.stage} done={run.status === 'done'} kind={runKind} />
            <div className="demo-log" ref={logRef} aria-live="polite">{run.log.length ? run.log.map((l, i) => <p key={i}>{l}</p>) : <p className="dim">Starting…</p>}</div>
            <AnimatePresence>{run.status === 'error' && <motion.p className="demo-error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>{run.error}</motion.p>}</AnimatePresence>
            {run.status !== 'done' && run.status !== 'error' && <div className="demo-skeleton"><span className="pending" /><span className="pending" /><span className="pending" /></div>}
            {run.report && <Report v={run.report} />}
          </>)}
        </div>
      </section>
    </>
  )
}
