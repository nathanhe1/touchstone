/* Terms of use and privacy policy for the website. Appraisals themselves are governed by a separate written agreement. */
const UPDATED = 'October 29, 2026'

export function Terms() {
  return (
    <>
      <header className="page-head wrap"><h1>Terms of use</h1><p className="lede">Last updated {UPDATED}</p></header>
      <article className="wrap legal">
        <p>These terms cover your use of the Touchstone website. By using the site you agree to them. If you do not agree, please do not use the site.</p>
        <h2>The website</h2>
        <p>The site describes Touchstone's appraisal service. The sample report, environments and figures on the site illustrate the method and are not an appraisal of any real product or vendor.</p>
        <h2>Appraisals</h2>
        <p>Appraisals are provided only under a separate written agreement between Touchstone and the customer. That agreement sets the scope, fees, confidentiality and handling of vendor material, and it takes precedence over anything on this site.</p>
        <h2>No advice or warranty</h2>
        <p>Content on the site is provided as is, for general information. It is not investment, legal or purchasing advice, and Touchstone makes no warranty that it is complete or current.</p>
        <h2>Intellectual property</h2>
        <p>The site's text, design and code belong to Touchstone. Research cited on the site belongs to its authors and is linked to its source.</p>
        <h2>Limitation of liability</h2>
        <p>To the extent the law allows, Touchstone is not liable for any loss arising from use of the website or reliance on its content.</p>
        <h2>Changes</h2>
        <p>We may update these terms. The date at the top shows the latest version.</p>
        <h2>Contact</h2>
        <p>Questions about these terms can be sent through the <a className="textlink" href="#request">request page</a>.</p>
      </article>
    </>
  )
}

export function Privacy() {
  return (
    <>
      <header className="page-head wrap"><h1>Privacy policy</h1><p className="lede">Last updated {UPDATED}</p></header>
      <article className="wrap legal">
        <p>This policy explains what information the Touchstone website collects and how it is used.</p>
        <h2>What the site collects</h2>
        <p>The website itself does not set cookies, does not run analytics or advertising trackers, and does not ask you for personal information. Our hosting provider may keep standard server logs, such as IP address and request time, for security and reliability.</p>
        <h2>When you contact us</h2>
        <p>If you request an appraisal or contact us, we use the details you send, such as your name, company and email address, only to reply and to scope the work. We do not sell this information or share it with vendors.</p>
        <h2>Vendor and customer material</h2>
        <p>Environments, datasets and results submitted for an appraisal are handled under the written agreement for that appraisal. Vendor tasks stay sealed and are not shown to buyers.</p>
        <h2>Retention and your rights</h2>
        <p>We keep contact details only as long as needed for the conversation or the engagement. You can ask us to access, correct or delete the information we hold about you.</p>
        <h2>Changes</h2>
        <p>We may update this policy. The date at the top shows the latest version.</p>
        <h2>Contact</h2>
        <p>Privacy questions can be sent through the <a className="textlink" href="#request">request page</a>.</p>
      </article>
    </>
  )
}
