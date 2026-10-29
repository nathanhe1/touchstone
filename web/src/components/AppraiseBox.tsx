/* A prompt-style entry point under the hero: pick what to appraise, describe it or drop a dataset in.
   Dropped files are read in the browser only; a first check (format, size, exact duplicates) runs right away. */
import { useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { REQUEST_FORM_URL } from '../data'

type Mode = 'dataset' | 'env' | 'grader' | 'compare'
const MODES: [Mode, string, string][] = [
  ['dataset', 'Appraise a dataset', 'Drop a .jsonl post-training dataset here, or describe the one you are considering buying.'],
  ['env', 'Appraise an RL environment', 'Describe the environment: what it trains, how many tasks, who sells it and the asking price.'],
  ['grader', 'Audit a grader', 'Describe the grader, or paste a few tasks with the answers it accepts.'],
  ['compare', 'Compare vendors', 'List the environments or datasets you are choosing between.'],
]
type Check = { file: string; rows: number; format: string; fields: string[]; dupes: number; bad: number; avgChars: number }

function inspect(name: string, text: string): Check {
  const lines = text.split(/\r?\n/).filter(l => l.trim())
  const seen = new Set<string>(); let dupes = 0, bad = 0, chars = 0
  const fields = new Map<string, number>()
  for (const l of lines) {
    try {
      const o = JSON.parse(l)
      Object.keys(o).forEach(k => fields.set(k, (fields.get(k) ?? 0) + 1))
      const key = JSON.stringify(o); if (seen.has(key)) dupes++; else seen.add(key)
      chars += l.length
    } catch { bad++ }
  }
  const f = [...fields.keys()]
  const format = f.includes('messages') ? 'chat messages' : f.includes('prompt') && (f.includes('completion') || f.includes('response')) ? 'prompt and completion' : f.includes('task') || f.includes('question') ? 'tasks' : 'unrecognized'
  return { file: name, rows: lines.length - bad, format, fields: f.slice(0, 6), dupes, bad, avgChars: lines.length - bad ? Math.round(chars / (lines.length - bad)) : 0 }
}

export function AppraiseBox() {
  const [mode, setMode] = useState<Mode>('dataset')
  const [text, setText] = useState('')
  const [over, setOver] = useState(false)
  const [busy, setBusy] = useState(false)
  const [check, setCheck] = useState<Check | null>(null)
  const [error, setError] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const read = (file: File) => {
    setError(''); setCheck(null)
    if (!/\.(jsonl|json|ndjson)$/i.test(file.name)) { setError('Drop a .jsonl file: one JSON example per line.'); return }
    if (file.size > 50e6) { setError('That file is over 50 MB. Send us a sample of it instead.'); return }
    setBusy(true); setMode('dataset')
    file.text().then(t => { setTimeout(() => { setCheck(inspect(file.name, t)); setBusy(false) }, 500) })
  }
  const href = REQUEST_FORM_URL || '#request'
  return (
    <div className="abox-wrap">
      <h2 className="abox-title">What do you want to appraise?</h2>
      <div className={`abox${over ? ' over' : ''}`}
        onDragOver={e => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
        onDrop={e => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) read(f) }}>
        <textarea value={text} onChange={e => setText(e.target.value)} placeholder={MODES.find(m => m[0] === mode)![2]} rows={3} aria-label="Describe what you want appraised" />
        <AnimatePresence mode="wait">
          {(busy || check || error) && (
            <motion.div key={busy ? 'busy' : check ? check.file : 'err'} className="abox-check" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
              {error ? <p className="bad">{error}</p>
                : busy ? <div className="abox-grid">{[0, 1, 2, 3].map(i => <div key={i}><small>&nbsp;</small><span className="pending" /></div>)}</div>
                : check && (<>
                  <p className="abox-file">{check.file} <span>checked in your browser, not uploaded</span></p>
                  <div className="abox-grid">
                    <div><small>examples</small><b>{check.rows.toLocaleString('en-US')}</b></div>
                    <div><small>format</small><b className={check.format === 'unrecognized' ? 'bad' : ''}>{check.format}</b></div>
                    <div><small>exact duplicates</small><b className={check.dupes / Math.max(check.rows, 1) > .05 ? 'bad' : ''}>{check.dupes.toLocaleString('en-US')} ({Math.round(check.dupes / Math.max(check.rows, 1) * 100)}%)</b></div>
                    <div><small>unreadable lines</small><b className={check.bad ? 'bad' : ''}>{check.bad}</b></div>
                  </div>
                  <p className="abox-note">Fields: {check.fields.join(', ') || 'none'} · about {check.avgChars.toLocaleString('en-US')} characters per example. A full appraisal adds training at four model sizes, transfer to private problems, overlap with free data and a fair price.</p>
                </>)}
            </motion.div>
          )}
        </AnimatePresence>
        <div className="abox-bar">
          <button className="abox-attach" onClick={() => input.current?.click()} aria-label="Attach a .jsonl dataset">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true"><path d="M10.5 4.5 5.8 9.2a1.5 1.5 0 0 0 2.1 2.1l4.9-4.9a3 3 0 0 0-4.2-4.2L3.7 7.1a4.5 4.5 0 0 0 6.4 6.4l3.4-3.4" /></svg>
            Attach .jsonl
          </button>
          <input ref={input} type="file" accept=".jsonl,.json,.ndjson" hidden onChange={e => { const f = e.target.files?.[0]; if (f) read(f); e.target.value = '' }} />
          <a className="btn abox-go" href={href}>Request this appraisal</a>
        </div>
      </div>
      <div className="abox-modes" role="tablist" aria-label="Appraisal type">
        {MODES.map(([k, label]) => <button key={k} role="tab" aria-selected={mode === k} className={mode === k ? 'on' : ''} onClick={() => setMode(k)}>{label}</button>)}
      </div>
    </div>
  )
}
