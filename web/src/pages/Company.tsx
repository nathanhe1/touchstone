import { FOUNDERS, ROADMAP } from '../data'
import { Close, PageHead } from '../ui'

const MARKET: [string, string, string][] = [
  ['$1B', 'a year spent on human-curated training material by each leading lab', 'TechCrunch, Pebblous'],
  ['$1B+', 'on RL environments in a single year at one frontier lab', 'TechCrunch'],
  ['$20k', 'for a single RL task at the high end; most sell for $200 to $2,000', 'Price summary citing Epoch AI'],
]

export default function Company() {
  return (
    <>
      <PageHead title="Less wasted training. More real learning." text="We help AI companies spend less on ineffective training and get more useful learning from their compute." />
      <section className="band">
        <div className="wrap split">
          <div><h2>Why Touchstone.</h2></div>
          <div className="prose"><p>A touchstone is the dark stone merchants used to test gold before they bought it. Rub the metal across the stone, read the streak, and you know what it’s worth. We do the same for training material.</p><p>The buyer can’t judge it without seeing it, and the seller can’t show it without giving it away. It takes a neutral third party to fix that. We never sell training material, so we can audit every vendor.</p></div>
        </div>
      </section>
      <section className="band">
        <div className="wrap split">
          <div><h2>Why now.</h2><p>The money in AI training is moving from compute to training material, and most results reach buyers from the people selling.</p></div>
          <dl className="market">{MARKET.map(([n, t, s]) => <div key={n}><dd>{n}</dd><dt>{t}<small>{s}</small></dt></div>)}</dl>
        </div>
      </section>
      {FOUNDERS.length > 0 && (
        <section className="band"><div className="wrap split"><div><h2>Who is building this.</h2></div>
          <div className="prose">{FOUNDERS.map(([n, r, w, l]) => <p key={n}><b>{n}</b>, {r}. {w} {l && <a href={l} target="_blank" rel="noopener">Profile</a>}</p>)}</div></div></section>
      )}
      <section className="band">
        <div className="wrap split">
          <div><h2>Where we are.</h2></div>
          <table className="ledger">
            <tbody>{ROADMAP.map(([stage, title, text]) => <tr key={title}><td>{stage}</td><td><b>{title}</b>{text}</td></tr>)}</tbody>
          </table>
        </div>
      </section>
      <Close title="The neutral check on training material." text="Talk to us about a pilot audit." />
    </>
  )
}
