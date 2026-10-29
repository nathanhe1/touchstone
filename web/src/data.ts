import raw from '../../out/appraisals.json'

// Edit these as things happen; the whole site reads them.
export const REQUEST_FORM_URL = ''
export const ROADMAP: [stage: 'Done' | 'Now' | 'Next' | 'Later', title: string, detail: string][] = [
  ['Done', 'Prototype pipeline', 'Seal, train four model sizes, test transfer, probe the grader, forecast and price. Runs end to end.'],
  ['Now', 'Customer conversations', 'Reaching out to RL environment vendors and AI teams about pilot appraisals.'],
  ['Next', 'A real open-source environment', 'Run a public RL environment through the full pipeline.'],
  ['Next', 'Compare environments', 'Rank several environments side by side by value per dollar.'],
  ['Later', 'Beyond RL', 'Training decisions across model types, and forecasting behaviour before a model ships.'],
]
// [name, role, one line on why you, profile link or '']
export const FOUNDERS: [string, string, string, string][] = []

type Rung = { params: number; env_reward_before: number; env_reward_after: number; heldout_before: number; heldout_after: number; curve: number[] }
export type Env = {
  id: string
  name: string
  sha256: string
  is_public_baseline: boolean
  hackability: { score: number; per_exploit: Record<string, number> }
  grader: { ok: boolean }
  redundancy: { public_overlap: number; unique_tasks: number; n_tasks: number }
  contamination: number
  forecast: { forecast: number; lo: number; hi: number; gains_by_rung: number[] }
  actual_at_truth: number
  lift_over_free: number
  fair_value_per_task: number
  grade: string
  flags: string[]
  rungs: Record<string, Rung>
}
type Data = { ladder: Record<string, number>; truth_rung: string; heldout_items: number; validation: { spearman_forecast_vs_actual: number; mean_abs_error_pts: number }; environments: Env[] }

export const data = raw as unknown as Data
export const truth = data.truth_rung
export const base = data.environments.find(e => e.is_public_baseline)!
export const vendors = data.environments
  .filter(e => !e.is_public_baseline)
  .sort((a, b) => 'ABCDF'.indexOf(a.grade) - 'ABCDF'.indexOf(b.grade) || b.lift_over_free - a.lift_over_free)

export const signed = (v: number, d = 1) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(d)}`
export const pct = (v: number) => `${Math.round(v * 100)}%`
export const money = (v: number) => `$${Math.round(v).toLocaleString('en-US')}`
export const params = (v: number) => (v >= 1e6 ? `${(v / 1e6).toFixed(2)}M` : `${Math.round(v / 1e3)}K`)
export const gradeClass = (g: string) => (g === 'A' || g === 'B' ? 'g-a' : g === '—' ? 'g-base' : 'g-low')
