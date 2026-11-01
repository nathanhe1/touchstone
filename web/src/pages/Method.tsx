import { Close, Faq, PageHead } from '../ui'

/* Each check and its effect on the price mirrors touchstone/valuation.py. */
const CHECKS: [string, string, 'block' | 'adv'][] = [
  ['Gameable grader', 'Answers that solve nothing still collect reward.', 'block'],
  ['Reward that stays in training', 'Reward climbs while accuracy on new problems does not.', 'block'],
  ['Leaked answers', 'The answer is sitting in the prompt.', 'block'],
  ['Wrong labels', 'Worked solutions that do not add up.', 'adv'],
  ['Test overlap', 'Items that overlap our private test suite.', 'block'],
  ['Copied material', 'Tasks that are already free in public sets.', 'adv'],
  ['Repeats', 'The same item sold more than once.', 'adv'],
  ['Off topic', 'Material that does not fit what it claims to train.', 'adv'],
]
const PROBES: [string, string, string][] = [
  ['Empty answer', '""', 'Submit nothing at all.'],
  ['Digit soup', '7 3 9 1 0 4 8 2', 'Spray digits and hope one matches.'],
  ['Hedged guesses', '85 or 86 or 87', 'Glue several guesses together.'],
  ['Echo the prompt', '47+38=', 'Repeat the question back.'],
  ['Random digits', '412', 'The right shape, the wrong value.'],
  ['Edit the tests', 'assert True', 'Rewrite the check instead of the code.'],
  ['Exit early', 'sys.exit(0)', 'Quit before the tests can fail.'],
  ['Format gaming', '<answer>\\boxed{…}</answer>', 'Match the format, not the answer.'],
]
const SOURCES: [string, string, string][] = [
  ['Training on a well-chosen 5% of a dataset often beat training on all of it.', 'Xia et al., LESS, ICML 2024', 'https://proceedings.mlr.press/v235/xia24c.html'],
  ['One published study of pretraining found that small-model experiments ranked its options at larger scale.', 'Magnusson et al., DataDecide, ICML 2025', 'https://proceedings.mlr.press/v267/magnusson25a.html'],
  ['A vendor reports +9.6, +5.3 and +3.5 points from its own environments, measured on its own setup.', 'Surge, cross-benchmark generalization', 'https://surgehq.ai/blog/cross-benchmark-generalization-for-long-horizon-agentic-tasks'],
  ['Weak graders, leaked answers and tasks passed without being solved are the most common failure.', 'Invisible, the grader problem', 'https://invisibletech.ai/blog/the-grader-problem-why-most-rl-environments-fail'],
]

export default function Method() {
  return (
    <>
      <PageHead title="The same audit, for every vendor." text="Fixed checks, a fixed training recipe and a private test suite. Here is what runs and what each result means." />
      <section className="band">
        <div className="wrap split">
          <div><h2>What a report can flag.</h2><p>A blocking flag stops the price. On datasets, every flag is advisory for now.</p></div>
          <table className="ledger">
            <thead><tr><th>Check</th><th>What it means</th><th>Effect</th></tr></thead>
            <tbody>{CHECKS.map(([n, m, e]) => <tr key={n}><td>{n}</td><td>{m}</td><td className={e}>{e === 'block' ? 'Blocks the price' : 'Advisory on datasets'}</td></tr>)}</tbody>
          </table>
        </div>
      </section>
      <section className="band">
        <div className="wrap split">
          <div><h2>What we feed the grader.</h2><p>A model will learn any shortcut a grader allows. Every grader gets answers that should earn nothing.</p></div>
          <table className="ledger">
            <thead><tr><th>Probe</th><th>Sample</th><th>What it tries</th></tr></thead>
            <tbody>{PROBES.map(([n, s, w]) => <tr key={n}><td>{n}</td><td><code>{s}</code></td><td>{w}</td></tr>)}</tbody>
          </table>
        </div>
      </section>
      <section className="band">
        <div className="wrap split">
          <div><h2>What the numbers mean.</h2></div>
          <dl className="defs">
            <div><dt>Net gain</dt><dd>Accuracy gained on private problems, minus what a placebo run gained, with a range.</dd></div>
            <div><dt>Grade</dt><dd>A to F, from the net gain and any caps. It describes the size we measured.</dd></div>
            <div><dt>Estimated value</dt><dd>Net gain at the buyer’s dollars per point, spread across the novel items. An estimate, always shown with its assumption.</dd></div>
          </dl>
        </div>
      </section>
      <section className="band">
        <div className="wrap split">
          <div><h2>What we build on.</h2></div>
          <ul className="sources">{SOURCES.map(([t, c, u]) => <li key={u}><p>{t}</p><a href={u} target="_blank" rel="noopener">{c}</a></li>)}</ul>
        </div>
      </section>
      <section className="band">
        <div className="wrap split">
          <div><h2>Questions.</h2></div>
          <Faq items={[
            ['Do you ever see the vendor’s tasks?', 'They stay in a sealed sandbox. Buyers get results, never the tasks.'],
            ['Which models do you train?', 'A fixed family of small open models with one fixed RL recipe. Results describe the sizes we measured, each with its range.'],
            ['Why trust small models?', 'Small models keep an audit cheap, and most checks do not depend on model size: exploit probes, overlap and duplicates read the material itself. Where we train, the report states the size we measured and the range.'],
            ['What can you test today?', 'RL environments with automatic graders. Post-training datasets are coming, and dataset checks are advisory for now.'],
          ]} />
        </div>
      </section>
      <Close title="See it on your environment." text="We’re taking on a small number of pilot audits." />
    </>
  )
}
