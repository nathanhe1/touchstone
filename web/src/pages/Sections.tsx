import { vendors, pct } from '../data'
import { Panel, Reveal } from '../ui'

/* The exploit probes every grader faces, and the most any appraised grader paid for each. */
export function Exploits() {
  const probes: [string, string, string][] = [
    ['empty answer', '""', 'Submit nothing at all.'],
    ['digit soup', '7 3 9 1 0 4 8 2', 'Spray digits and hope one matches.'],
    ['hedged guesses', '85 or 86 or 87', 'Join several guesses together.'],
    ['echo the prompt', '47+38=', 'Repeat the question back.'],
    ['repeat last number in prompt', '38', 'Copy a number from the question.'],
    ['random 2-3 digits', '412', 'Right length, wrong value.'],
  ]
  const worst = (name: string) => vendors.map(e => [e.name, e.hackability.per_exploit[name] ?? 0] as const).sort((a, b) => b[1] - a[1])[0]
  return (
    <Panel title="exploit probes · arithmetic graders" meta={`${vendors.length} graders tested`}>
      <div className="scroll-x">
        <table className="table">
          <thead><tr><th>probe</th><th>example answer</th><th>what it tries</th><th className="r">most reward paid</th><th>by</th></tr></thead>
          <tbody>
            {probes.map(([name, sample, what]) => {
              const [who, score] = worst(name)
              return (
                <tr key={name}>
                  <td>{name}</td>
                  <td><code>{sample}</code></td>
                  <td className="dim">{what}</td>
                  <td className={`r num ${score >= .2 ? 'bad' : ''}`}>{pct(score)}</td>
                  <td className="dim">{score > 0 ? who : 'no grader'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

/* What the research and the market already show, with sources. */
export function Evidence() {
  const items: [string, string, string, string][] = [
    ['Data value varies widely', 'Training on a well-chosen 5% of a dataset often beat training on all of it.', 'Xia et al., LESS, ICML 2024', 'https://proceedings.mlr.press/v235/xia24c.html'],
    ['Small runs can rank data', 'Small-model experiments predicted which pretraining data wins at larger scale.', 'Magnusson et al., DataDecide, ICML 2025', 'https://proceedings.mlr.press/v267/magnusson25a.html'],
    ['Vendors grade themselves', 'Surge reports gains of 9.6, 5.3 and 3.5 points from its own environments, measured on its own setup.', 'Surge, cross-benchmark generalization', 'https://surgehq.ai/blog/cross-benchmark-generalization-for-long-horizon-agentic-tasks'],
    ['Graders are the weak point', 'Weak graders, leaked answers and tasks passed without being solved are the most common failure.', 'Invisible; Delphik', 'https://invisibletech.ai/blog/the-grader-problem-why-most-rl-environments-fail'],
  ]
  return (
    <div className="rows">
      {items.map(([title, text, cite, url]) => (
        <div key={title}><b>{title}</b><p>{text}</p><a className="textlink" href={url} target="_blank" rel="noopener">{cite}</a></div>
      ))}
    </div>
  )
}

export function Section({ title, text, children, flush = false }: { title: React.ReactNode; text?: string; children: React.ReactNode; flush?: boolean }) {
  return (
    <section className={`section${flush ? ' flush' : ''}`}>
      <div className="wrap">
        <div className="section-head"><Reveal><h2>{title}</h2></Reveal>{text && <Reveal delay={.05}><p>{text}</p></Reveal>}</div>
        {children}
      </div>
    </section>
  )
}
