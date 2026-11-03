/* The appraisal request form. It posts to the Touchstone server (POST /api/requests), which validates, rate-limits and
   stores each request. Validation here mirrors the server's so people see problems before they submit. */
import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { findApi, sendRequest } from '../demo/api'

const KINDS: [string, string][] = [['rl_environment', 'RL environment'], ['dataset', 'Post-training dataset'], ['other', 'Something else']]
const empty = { name: '', email: '', company: '', role: '', material_kind: 'rl_environment', description: '', budget: '', consent: false }
type Form = typeof empty

function check(f: Form): Partial<Record<keyof Form, string>> {
  const e: Partial<Record<keyof Form, string>> = {}
  if (!f.name.trim()) e.name = 'Your name, please.'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(f.email.trim())) e.email = 'A valid work email, please.'
  if (!f.company.trim()) e.company = 'Which company or lab?'
  if (f.description.trim().length < 20) e.description = 'A sentence or two about the material helps us scope it (20 characters or more).'
  if (f.description.length > 4000) e.description = 'Keep it under 4,000 characters.'
  if (!f.consent) e.consent = 'We need your consent to store this and reply.'
  return e
}

export function RequestForm() {
  const [f, setF] = useState<Form>(empty)
  const [touched, setTouched] = useState(false)
  const [state, setState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const [message, setMessage] = useState('')
  const [base, setBase] = useState<string | null | undefined>(undefined)
  useEffect(() => { findApi().then(a => setBase(a ? a.base : null)) }, [])
  const errors = check(f)
  const set = <K extends keyof Form>(k: K, v: Form[K]) => setF(p => ({ ...p, [k]: v }))
  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault(); setTouched(true)
    if (Object.keys(errors).length) return
    if (!base) { setState('error'); setMessage('The request server is not reachable from this page. Please try again from the Touchstone website.'); return }
    setState('sending')
    try {
      await sendRequest(base, { ...f, name: f.name.trim(), email: f.email.trim(), company: f.company.trim(), budget: f.budget.trim() || null })
      setState('sent')
    } catch (e) { setState('error'); setMessage((e as Error).message || 'Something went wrong. Please try again.') }
  }
  const err = (k: keyof Form) => touched && errors[k] ? <span className="rf-err" id={`rf-${k}-err`}>{errors[k]}</span> : null
  if (state === 'sent') return (
    <motion.div className="rf-done" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <b>Request received.</b><p>Thanks, {f.name.split(' ')[0]}. We'll reply to {f.email} within two working days to scope the appraisal.</p>
    </motion.div>
  )
  return (
    <form className="rf" onSubmit={submit} noValidate>
      <div className="rf-row">
        <label>Name<input value={f.name} onChange={e => set('name', e.target.value)} autoComplete="name" aria-invalid={touched && !!errors.name} aria-describedby="rf-name-err" />{err('name')}</label>
        <label>Work email<input type="email" value={f.email} onChange={e => set('email', e.target.value)} autoComplete="email" aria-invalid={touched && !!errors.email} aria-describedby="rf-email-err" />{err('email')}</label>
      </div>
      <div className="rf-row">
        <label>Company or lab<input value={f.company} onChange={e => set('company', e.target.value)} autoComplete="organization" aria-invalid={touched && !!errors.company} aria-describedby="rf-company-err" />{err('company')}</label>
        <label>Role <span className="dim">(optional)</span><input value={f.role} onChange={e => set('role', e.target.value)} autoComplete="organization-title" /></label>
      </div>
      <fieldset className="rf-kinds"><legend>What do you want appraised?</legend>
        {KINDS.map(([k, label]) => <label key={k} className={f.material_kind === k ? 'on' : ''}><input type="radio" name="kind" value={k} checked={f.material_kind === k} onChange={() => set('material_kind', k)} />{label}</label>)}
      </fieldset>
      <label>The material and the decision<textarea rows={5} value={f.description} onChange={e => set('description', e.target.value)} placeholder="What it trains, roughly how many tasks or examples, who sells it, the asking price, and the model you'd train." aria-invalid={touched && !!errors.description} aria-describedby="rf-description-err" />{err('description')}</label>
      <label>Budget for the purchase <span className="dim">(optional)</span><input value={f.budget} onChange={e => set('budget', e.target.value)} placeholder="e.g. $300k" /></label>
      <label className="rf-consent"><input type="checkbox" checked={f.consent} onChange={e => set('consent', e.target.checked)} />I agree that Touchstone stores these details to reply to me, as described in the <a className="textlink" href="#privacy">privacy policy</a>.</label>
      {err('consent')}
      <AnimatePresence>{state === 'error' && <motion.p className="rf-fail" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>{message}</motion.p>}</AnimatePresence>
      <button className="btn rf-submit" type="submit" disabled={state === 'sending'} aria-busy={state === 'sending'}>{state === 'sending' ? <><span className="rf-spin" />Sending…</> : 'Send request'}</button>
      {base === null && <p className="dim rf-note">This preview page can't reach the request server, so sending will fail here. It works on the Touchstone site.</p>}
    </form>
  )
}
