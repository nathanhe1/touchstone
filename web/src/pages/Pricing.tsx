import { Close, Faq, PageHead, RequestButton } from '../ui'

const TIERS: [string, string, string, string][] = [
  ['Grader audit', 'Every exploit probe run against the grader, the share of reward won without solving, and a fix list.', '$5k–$15k', 'per environment'],
  ['Full appraisal', 'Sealed training at several model sizes, transfer to private problems, overlap, exploits, and a fair price per task.', '$10k–$50k', 'per environment'],
  ['Subscription', 'Side-by-side comparison, re-tests as environments change, and vendor ratings over time.', '$100k–$250k', 'per year'],
]

export default function Pricing() {
  return (
    <>
      <PageHead title="Costs less than one bad run." text="An audit runs on small open models, so it costs a fraction of the material it checks." />
      <section className="band">
        <div className="wrap">
          <table className="ledger tiers">
            <thead><tr><th>Service</th><th>What you get</th><th>Price</th></tr></thead>
            <tbody>{TIERS.map(([n, d, p, per]) => <tr key={n}><td>{n}</td><td>{d}</td><td><b>{p}</b><small>{per}</small></td></tr>)}</tbody>
          </table>
          <div className="actions"><RequestButton label="Start with a pilot" /></div>
        </div>
      </section>
      <section className="band">
        <div className="wrap split">
          <div><h2>Questions.</h2></div>
          <Faq items={[
            ['Who pays, the buyer or the vendor?', 'Either. Buyers audit before purchase. Vendors commission a neutral rating to win contracts and back up their price.'],
            ['Why start with a grader audit?', 'It is the cheapest test, and a broken grader makes the rest of the appraisal moot.'],
            ['Can we pilot first?', 'Yes. Every new customer starts with a pilot audit.'],
          ]} />
        </div>
      </section>
      <Close title="Price the risk before you pay." text="Tell us what you’re about to buy, and we’ll scope the audit." />
    </>
  )
}
