/* Client for the Touchstone engine's web API (docs/API.md in the engine repo), plus a normalizer that turns either the
   API's report schema or the engine's raw report.json into one view model the demo page draws. */

const configured = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '')

export type Job = { job_id: string; status: 'queued' | 'running' | 'done' | 'error'; stage: string; progress: number; log: string[]; error: string | null; report: unknown | null }
export type Example = { id: string; name: string; kind: string; description: string }

/** Finds a reachable engine: the configured URL, then the page's own origin (when the backend serves the site). */
export async function findApi(): Promise<{ base: string; device: string } | null> {
  const candidates = [configured, typeof location !== 'undefined' && /^https?:/.test(location.protocol) ? location.origin : undefined].filter(Boolean) as string[]
  for (const base of candidates) {
    try {
      const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 2500)
      const r = await fetch(`${base}/api/health`, { signal: ctl.signal }); clearTimeout(t)
      if (!r.ok) continue
      const j = await r.json()
      if (j && j.ok) return { base, device: String(j.device ?? 'cpu') }
    } catch { /* unreachable: try the next one */ }
  }
  return null
}

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`
    try {
      const j = await r.json(); msg = j.detail ?? j.error ?? msg
      if (j.errors && typeof j.errors === 'object') msg = Object.entries(j.errors).map(([k, v]) => `${k.replace('_', ' ')}: ${v}`).join('; ')
    } catch { /* not json */ }
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }
  return r.json() as Promise<T>
}
export const listExamples = (base: string) => fetch(`${base}/api/examples`).then(r => json<Example[]>(r))
export const runExample = (base: string, id: string) => fetch(`${base}/api/appraise/example/${encodeURIComponent(id)}`, { method: 'POST' }).then(r => json<{ job_id: string }>(r))
export function upload(base: string, file: File, kind: string | null) {
  const f = new FormData(); f.append('file', file); f.append('mode', 'quick'); if (kind) f.append('kind', kind)
  return fetch(`${base}/api/appraise`, { method: 'POST', body: f }).then(r => json<{ job_id: string }>(r))
}
export const getJob = (base: string, id: string) => fetch(`${base}/api/jobs/${id}`).then(r => json<Job>(r))
export const sendRequest = (base: string, body: Record<string, unknown>) =>
  fetch(`${base}/api/requests`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(r => json<{ id: string }>(r))

/* ---------- One view model for both report shapes ---------- */
export type Flag = { severity: 'block' | 'discount' | 'info'; text: string }
export type View = {
  name: string; kind: string; grade: string; perItem: number; blockedBy: string[]
  flags: Flag[]
  overlap: { suite: number; public: number; publicBaseline?: string; duplicates: number; examples: { item: string; matches: string; kind: string }[] }
  gains: { size: string; net: number; lo: number; hi: number }[]
  forecast: { target?: string; point: number; lo: number; hi: number; method?: string; note?: string } | null
  probes: { name: string; reward: number }[]
  transfer?: { envReward: number; heldout: number; gap: boolean }
  heldout?: { name: string; domain: string; n: number }
  models: string[]; runtime?: number; summary?: string; items?: number
}
type Any = Record<string, any>
const num = (v: unknown, d = 0) => (typeof v === 'number' && isFinite(v) ? v : d)

export function normalize(raw: unknown, fallbackName = 'material'): View {
  const r = (raw ?? {}) as Any
  const flags: Flag[] = (r.flags ?? []).map((f: any) => typeof f === 'string' ? { severity: 'info', text: f } : { severity: f.severity ?? 'info', text: f.text ?? f.code ?? '' })
  const ov = r.overlap ?? {}
  const overlapOf = (v: any) => typeof v === 'number' ? v : num(v?.rate)
  const gains = r.gains_by_size
    ? Object.entries(r.gains_by_size as Any).map(([size, g]: [string, any]) => ({ size, net: num(g.net), lo: num(g.lo), hi: num(g.hi) }))
    : Object.entries((r.rungs ?? {}) as Any).map(([size, g]: [string, any]) => ({ size, net: num(g?.net?.acc?.gain), lo: num(g?.net?.acc?.lo), hi: num(g?.net?.acc?.hi) }))
  const fc = r.forecast
  const forecast = fc ? (fc.net || fc.value !== undefined
    ? { target: fc.target, point: num(fc.net?.point ?? fc.value), lo: num(fc.net?.lo ?? fc.lo), hi: num(fc.net?.hi ?? fc.hi), method: fc.method, note: fc.method_note }
    : null) : null
  const probeSrc = r.probes ?? r.grader_audit?.per_exploit ?? {}
  const probes = Object.entries(probeSrc as Any).map(([name, v]) => ({ name, reward: num(v) })).sort((a, b) => b.reward - a.reward)
  const tc = r.transfer_check
  return {
    name: r.material?.name ?? r.name ?? fallbackName, kind: r.kind ?? 'dataset', grade: String(r.grade ?? '?'),
    perItem: num(r.fair_value_per_item ?? r.fair_value?.per_item), blockedBy: r.fair_value?.blocked_by ?? [],
    flags,
    overlap: { suite: overlapOf(ov.suite ?? ov.heldout), public: overlapOf(ov.public), publicBaseline: ov.public?.baseline, duplicates: typeof ov.duplicates === 'number' ? ov.duplicates : num(ov.duplicates?.dup_rate), examples: [...(ov.heldout?.examples ?? []), ...(ov.public?.examples ?? [])].slice(0, 3) },
    gains, forecast, probes,
    transfer: tc ? { envReward: num(tc.env_reward_gain_pts), heldout: num(tc.heldout_gain_pts), gap: !!tc.transfer_gap } : undefined,
    heldout: r.heldout ? { name: r.heldout.name, domain: r.heldout.domain, n: num(r.heldout.n_items) } : undefined,
    models: Object.values((r.models ?? {}) as Any).map(String), runtime: r.runtime_s, summary: r.summary, items: r.material?.n_items,
  }
}

/** The stages a job moves through, as the API names them. */
export const STAGES = ['validate', 'seal', 'overlap', 'probe', 'train', 'measure', 'forecast', 'price', 'report'] as const
export const STAGE_LABEL: Record<string, string> = { validate: 'Validate', seal: 'Seal', overlap: 'Check overlap', probe: 'Probe grader', train: 'Train', measure: 'Measure', forecast: 'Forecast', price: 'Price', report: 'Report' }
