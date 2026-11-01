import { PageHead } from '../ui'
import { RequestForm } from '../components/RequestForm'

export default function Request() {
  return (
    <>
      <PageHead title="Tell us what you're about to buy." text="We're taking on a small number of pilot audits. We reply within two working days." />
      <section className="band">
        <div className="wrap split">
          <div><h2>What helps.</h2><dl className="defs">
            <div><dt>The material</dt><dd>What it trains, how big it is and who sells it.</dd></div>
            <div><dt>The decision</dt><dd>What you'd pay, and what you need to know first.</dd></div>
            <div><dt>Your model</dt><dd>Rough size and what you're training it to do.</dd></div>
          </dl></div>
          <RequestForm />
        </div>
      </section>
    </>
  )
}
