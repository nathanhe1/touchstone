# YC site analysis

Study of recent Y Combinator company websites, done to redesign the Touchstone preview from the structure down. Captured on 2026-10-31 in Chromium 151 through Playwright. Everything here separates **measured** facts from **judgement**. Sites are public home pages only: no logins, no sign-ups, no forms submitted, no bot protection bypassed.

## Coverage

| | Count |
|---|---|
| Sites attempted (W24 to F26, weighted to AI infrastructure, dev tools, RL and evals) | 66 |
| Sites measured by script | 63 |
| Sites with video recorded and frames read | 62 |
| ...of which desktop and mobile | 61 (Legora: desktop only, mobile refused) |
| Skipped: bot challenge | Retell AI |
| Skipped: HTTP 403 | Unsloth |
| Skipped: connection reset on every attempt | Evident Machines |

Batches measured: W24 11, S24 6, F24 6, W25 8, Spring 25 5, S25 7, F25 5, W26 3, Spring 26 4, S26 3, F26 5. Segments: RL, data and audit 17, AI infrastructure 17, dev tools 12, evals 10, design-led 7.

Limits worth keeping in mind:

- **Legora and Vibrant Labs:** a failed retry overwrote their result files, and in Vibrant's case the recording. Their measurements were restored from an earlier saved aggregate. Legora's frames survived. Vibrant has measurements only and no frames, so 62 not 63 sites have frame notes.
- **Load:** the Mac was busy with ML work and rendering was in software, so timing figures (load, LCP, frame rate, long tasks) are not real-world numbers. They are not used to rank sites. Early blank frames are not treated as site defects.
- **Reveal times** are the weakest measure here, because slow frames stretch them. The median below is an upper bound.
- **Pinning** counts an element held still for more than 260px of scroll. It can miss scrubbed canvases and video, which is why frame notes are counted separately.
- **Motion library detection** at medium confidence is a string match in shipped JavaScript, so a bundled but unused library would count.
- **Frames** were read as contact sheets (24 desktop and 20 mobile frames sampled from 2 to 4 fps extractions per site). Five sites were read by the lead and the rest by reader agents using a fixed template. Scrubbing was usually inferred from neighbouring frames, and each per-site note says what was seen and what was inferred. Hover changes were measured from computed styles, because hovers are too small to read at sheet resolution.
- **Sourcebot** mobile produced two grey frames. **idler** captured only about 10 seconds. **Variant**'s gallery did not render in this environment.

## How it was measured

Each home page was loaded at 1440x900 and at 390x844 with touch, with `recordVideo` on, one site at a time at low priority. The script waited for the page to settle, measured it, hovered nav items and primary buttons, scrolled slowly with real wheel input (touch-style scrolling on mobile), then clicked tabs and accordions outside forms. A third load used `prefers-reduced-motion`. Frames came from Playwright's bundled ffmpeg, so nothing new was installed. No user agent was spoofed.

Stack detection used window globals, script URLs, generator tags, DOM attributes and signatures in shipped CSS and JS, and a WebGL hook that counts compiled shaders. Confidence: **high** means a global, DOM marker, URL or compiled shader. **Medium** means a signature in shipped code. **Low** means tokens only. Font class is judged from the family name, including for custom fonts.

## Findings that matter most

1. **Touchstone's look is genuinely different in its own market.** Measured: 2 of 17 RL, data and audit sites have a dark hero, against 26 of 63 overall. A dark site is rare in this market.
2. **Serif is normal among peers.** Measured: 9 of those 17 use a serif H1, against 16 of 63 overall.
3. **A direct competitor exists.** Tokenless (S26) states "We find flaws in RL environments and evals and help you fix them." This contradicted the old claim that Touchstone is the first independent auditor, so that claim is gone. You may want to look at Tokenless, HUD, Halluminate and Vibrant Labs yourself.
4. **Proof sits straight after the hero.** Frames: 38 of 62 sites put a logo or stat row there. Touchstone has no logos to show, so verified results take that slot.
5. **The best sites commit to one idea.** Frames: 24 of 62 heroes are one object, image or diagram, 16 are product UI and 22 are text-led. Pinned content was measured on 19 of 63. Touchstone's object is its own console.
6. **Corners are tight.** Measured: median card radius 4px, 27 of 63 square cards, median button radius 7.5px, 14 of 63 pills. Touchstone had mixed 14 to 24px cards with 999px pills.
7. **Reduced motion is widely declared but not always safe.** Measured: 60 of 63 ship the query, and 10 of 63 still left text invisible with it on.
8. **Every site passes 390 wide.** Measured: 0 of 63 had horizontal scroll. Cookie banners were the most common mobile problem, noted on about 10 sites.

## Patterns with counts (measured)

### Measured patterns (n=63)

| Pattern | Count |
|---|---|
| Hero is dark (light text on dark ground or image) | 26 of 63 |
| Hero is light, whole page light | 25 of 63 |
| Light hero with at least one big dark band | 12 of 63 |
| H1 in a serif | 16 of 63 |
| H1 in a sans | 44 of 63 |
| H1 in a mono | 3 of 63 |
| H1 font weight 500 or lighter | 42 of 63 |
| H1 with negative tracking | 52 of 63 |
| H1 is a real <h1> element | 61 of 63 |
| Body text in a sans | 53 of 63 |
| Serif heading plus sans body | 13 of 63 |
| Pill buttons (radius 100px or more) | 14 of 63 |
| Square buttons (radius under 3px) | 15 of 63 |
| Square cards (radius under 3px) | 27 of 63 |
| Mono labels present | 39 of 63 |
| Uppercase labels present | 36 of 63 |
| Sticky or fixed nav | 44 of 63 |
| Nav hides on scroll | 14 of 63 |
| Pinned content measured (held >260px of scroll) | 19 of 63 |
| Parallax or scrubbed drift measured | 22 of 63 |
| Reveal on scroll measured (2+ elements) | 17 of 63 |
| prefers-reduced-motion in shipped CSS or JS | 60 of 63 |
| Text left hidden under reduced motion | 10 of 63 |
| Running CSS or WAAPI animations drop under reduced motion | 39 of 63 |
| WebGL shaders compiled | 10 of 63 |
| Autoplay or inline video on the page | 12 of 63 |
| Horizontal scroll at 390 wide | 0 of 63 |
| Pricing in nav | 38 of 63 |
| Privacy link found | 49 of 63 |
| Terms link found | 45 of 63 |
| Blockquote testimonials | 15 of 63 |
| SOC 2 / HIPAA / ISO / GDPR mentioned | 28 of 63 |
| YC named on the home page | 14 of 63 |
| Book-demo style CTA text on page | 36 of 63 |
| Self-serve CTA text on page | 39 of 63 |
| Tabs on page | 18 of 63 |
| Accordion on page | 33 of 63 |
| Code block on page | 23 of 63 |

| Measure | Median | Min | Max | n |
|---|---|---|---|---|
| H1 size desktop, px | 60 | 16 | 132.4 | 63 |
| H1 size mobile, px | 38 | 16 | 60 | 61 |
| H1 words | 6 | 1 | 20 | 63 |
| H1 tracking, em | -0.0 | -0.071 | 0.34 | 63 |
| H1 line height | 1.1 | 0.9 | 1.6 | 63 |
| H2 largest, px | 48.0 | 14 | 136 | 54 |
| Subhead words | 19 | 5 | 30 | 59 |
| Subhead size, px | 18 | 11 | 24 | 59 |
| Body size, px | 16 | 8.6 | 20.9 | 59 |
| Body line height | 1.5 | 1.2 | 1.8 | 58 |
| Primary button height, px | 42.0 | 26 | 64 | 56 |
| Button text, px | 14.0 | 11 | 20 | 56 |
| Button radius, px | 7.5 | 0.0 | 999.0 | 60 |
| Card radius, px | 4.0 | 0.0 | 40.0 | 57 |
| Max content width, px | 1200.0 | 654.0 | 1400.0 | 60 |
| Section vertical padding sum, px | 160 | 24 | 362 | 29 |
| Distance between H2s, px | 961 | 173 | 4131 | 51 |
| Page height, px | 7557 | 900 | 33895 | 63 |
| Words on page | 683 | 22 | 3153 | 63 |
| H2 count | 7 | 0 | 10 | 63 |
| Nav items | 8 | 0 | 14 | 63 |
| Reveal time, ms | 1234.0 | 175 | 21337 | 22 |
| Decoded JS, KB | 2197 | 1 | 7113 | 63 |
| Requests | 87 | 4 | 555 | 63 |

| Technology | High confidence | Medium | Low | Total |
|---|---|---|---|---|
| Tailwind | 44 | 0 | 0 | 44 |
| Next.js | 41 | 0 | 0 | 41 |
| Motion | 5 | 28 | 0 | 33 |
| Radix | 7 | 14 | 3 | 24 |
| shadcn | 0 | 9 | 8 | 17 |
| WebGL shaders | 10 | 0 | 0 | 10 |
| Lottie | 5 | 5 | 0 | 10 |
| CSS scroll-timeline | 0 | 8 | 0 | 8 |
| GSAP | 3 | 4 | 0 | 7 |
| ScrollTrigger | 3 | 4 | 0 | 7 |
| Lenis | 2 | 4 | 0 | 6 |
| Framer | 5 | 0 | 0 | 5 |
| Three.js | 4 | 1 | 0 | 5 |
| Astro | 4 | 0 | 0 | 4 |
| Webflow | 4 | 0 | 0 | 4 |
| react-spring | 0 | 1 | 0 | 1 |
| SvelteKit | 1 | 0 | 0 | 1 |
| Unicorn Studio | 0 | 1 | 0 | 1 |
| Rive | 1 | 0 | 0 | 1 |
| Spline | 0 | 1 | 0 | 1 |

H1 families seen: Geist (8), Inter (3), ui-sans-serif (2), Courier New (1), serif (1), marketingSans (1), GeistSans (1), Geist Variable (1), Terrane Serif Bold (1), Funnel Display (1), Plus Jakarta Sans (1), Aeonik (1), rethinkSans (1), PP Mori (1)

Body families seen: Geist (10), Inter (8), GeistSans (3), ui-sans-serif (2), Courier New (1), sans (1), marketingSans (1), Geist Variable (1), Haffer Regular (1), Plus Jakarta Sans (1)

| Segment | n | Dark hero | Serif H1 | Median H1 | Pinned | WebGL |
|---|---|---|---|---|---|---|
| design | 7 | 5 | 2 | 60 | 3 | 1 |
| rl-audit | 17 | 2 | 9 | 54 | 4 | 4 |
| dev | 12 | 9 | 0 | 56.0 | 6 | 2 |
| ai-infra | 17 | 6 | 4 | 61.9 | 3 | 2 |
| evals | 10 | 4 | 1 | 65.6 | 3 | 1 |

## Writing

Measured, with the H1 classification being a judgement call made by hand from the text in the per-site copy table:

| H1 formula | Sites | Examples |
|---|---|---|
| Category statement: what it is, and for whom | 31 | "The platform for building RL environments", "Email Inboxes for AI agents" |
| Imperative or outcome | 22 | "Turn documents into data.", "Catch bugs before they ship." |
| Belief or claim | 6 | "We teach machines how experts think.", "Legal work, without limits." |
| Wordmark only | 4 | Tokenless, hillclimb, Openbenchmarks, Abundant |

- **Length:** median H1 is 6 words, median subhead 19 words, median page 683 words.
- **Audience:** 27 of 63 H1s contain the word "agent". Only 6 of 63 subheads name a buyer type such as teams or labs. Most sites let the category imply the customer.
- **Numbers in the opening:** 4 of 63 use a digit in the H1 or subhead. Numbers usually wait for the proof row, and 44 of 63 pages show 3 or more stat-like figures somewhere.
- **CTAs:** 39 of 63 show two hero CTAs. Page copy is both demo and self-serve on 26, self-serve only on 13, demo only on 10. Common labels are "Start building", "Book a demo", "Request a Demo", "Get Started". RL and data labs are the exception and often have no CTA beyond "Contact us".
- **Proof in the frames (keyword count of 62 notes):** quotes on 21, stats on 20, backers named on 13, compliance on 11, nothing visible on 9.
- **Left out:** almost nobody explains method in the hero, and pricing is absent from 25 of 63 navs. RL and data labs drop product detail and rely on backers, research or a published result. Halluminate, Openbenchmarks and Tokenless all lead with results or writing.
- **What is rare:** a warning. No H1 in this set tells the reader what not to do, and only Momentic and Raindrop use prevention. "Don't buy training material blind." owns that position, so it stays.

## Interaction and scroll

- **Scroll (frames):** 27 of 62 notes describe pinned, sticky, scrubbed or stacked content, 8 are plain scroll, and the rest are ordinary sections with reveals. The common forms are a pinned hero object (AgentMail, Coval, Laminar, HUD), a sticky list that swaps a panel (Raindrop, Osmosis, Pulse, Sciloop) and panels stacking over the hero (Tinfoil, 21st).
- **Depth of pinning (measured):** the longest pinned elements were HumanLayer at 10,488px, cubic 4,774px, Mastra 3,906px, s2.dev 3,038px and Legora 2,480px.
- **Live demos (frames):** about 16 notes show a hero or section that changes by itself or with tabs. The most useful for Touchstone are Stacktrace's tabbed console, Arga and Tasklet's auto-playing UI, and Halluminate's chart tabs.
- **Sticky nav (measured):** 44 of 63 stick, and 14 of those hide on scroll.
- **Hover (measured over 220 controls):** colour changed on 70, border on 61, background on 60, nothing on 79. Shadow changed on 9 and transform on only 2. Median transition is 150ms. Lifting elements on hover is rare here.
- **Reveals (measured, upper bound):** 17 of 63 reveal two or more elements as they enter, with a median of about 1.2s under this load.
- **Libraries:** Motion 33 of 63 (5 high confidence, 28 medium), GSAP 7, Lenis 6, Three.js 5, compiled WebGL shaders 10, Lottie 10, Rive 1, Spline 1. Tailwind 44, Next.js 41, Framer 5, Webflow 4, Astro 4.
- **Performance cost:** median decoded JS is 2.2MB and median requests 87. Timing is unreliable here, but Browser Use, Archil, Pulse and 21st had the largest long-task totals, and all use heavy animated heroes.

## How the sites are organized (measured)

Measured on 61 sites with raw heading, nav and footer data. Section counts use H2s as the proxy, so a page that builds sections without H2s reads low.

| Segment | Sites | Median H2s | Median words | Median screens at 900px | Median nav items | Median footer links |
|---|---|---|---|---|---|---|
| RL, data and audit | 16 | 1 | 229 | 2.1 | 4 | 6 |
| AI infrastructure | 17 | 8 | 683 | 7.4 | 10 | 20 |
| Dev tools | 12 | 7.5 | 1,144 | 9.5 | 7.5 | 16.5 |
| Evals | 10 | 9 | 1,122 | 10.9 | 8.5 | 28.5 |
| Design-led | 6 | 9.5 | 1,355 | 10.9 | 13 | 15.5 |
| All | 61 | 7 | 683 | 8.4 | 8 | 20 |

**What each section does.** Keyword match on H2 text, so these are floors, and the number after the count is the median position on the page from 0 (top) to 1 (bottom):

| Section job | Sites | Median position |
|---|---|---|
| Problem or why | 14 | 0.10 |
| Customers or proof | 26 | 0.24 |
| Features or platform | 22 | 0.27 |
| How it works | 12 | 0.35 |
| Security or enterprise | 16 | 0.61 |
| Pricing | 8 | 0.76 |
| FAQ | 14 | 0.88 |

The studied order is therefore: what it is, proof, why it matters, how it works, then detail, then the next step. A closing CTA was too noisy to place by keyword, but the frames show one on most pages.

**Nav.** Items present, all 61 sites: Pricing 38, Blog 27, Product 26, Docs 24, Sign-in 23, Company 21, Customers 20, Demo 13, Research 13, Contact 10, Careers 10. Among the 33 RL, data and infrastructure sites: Blog 17, Pricing 14, Docs 13, Product 12, Company 11, Customers 10, Research 9, Contact 7, Careers 7, Sign-in 7, Demo 2.

**Footer.** Of 49 sites with a footer element: Privacy 45, Terms 41, Blog 38, Security 31, Careers 28, Pricing 27, social 26, Contact 21, Docs 18, Status 13, GitHub 9.

**Homepage versus subpages.** Sampled by loading real subpages of the reference sites, so these are examples and not medians of the full set:

| Page type | Words |
|---|---|
| Pricing | s2.dev 247, Browser Use 332, Stacktrace 417 |
| About | Osmosis 397, Stacktrace 414, Openbenchmarks 797 |
| Research index | Halluminate 326, AfterQuery 483 |
| Benchmark or method | Openbenchmarks 1,023, Browser Use 1,114, isoquant 2,005 |

Depth lives on the benchmark page, not the home page. Home pages hand off with one link.

**Proof without logos, RL, data and infrastructure group (frames):**

- **Publishing the result:** Halluminate (a leaderboard on the home page), Openbenchmarks (ranked tables), isoquant (prices and benchmarks), Luminal (benchmarks), Expanse (a measured-outcomes table).
- **Live numbers:** HUD (running counters).
- **Named backers in plain text:** hillclimb, Polymath, AfterQuery, Tokenless.

None of these needs a customer. The strongest ones show a result the reader can check.

## Best-in-class references

Judgement, from reading whole-page maps at 1440 plus the video frames. Polymath's map failed with a connection reset, so it rests on its earlier frames.

| Site | What makes it well made |
|---|---|
| **Browser Use** | Hierarchy. A two-tone headline owns the viewport, one orange accent does all the signalling, and proof is a head-to-head a reader takes in instantly. Pricing fits in two numbers on the home page. |
| **isoquant** | Proof without a single logo. Every figure sits in a comparison inside hairline containers with square corners, and the page ends in one dark field. |
| **Stacktrace** | One idea per section. A tabbed console sits in the hero, and the dark product panels keep returning on a light page. |
| **Openbenchmarks** | Restraint. The results are the design: ranked tables in one serif and one mono, no illustration. |
| **Halluminate** | Rhythm. A sticky left column and one scrolling column, with a published benchmark as the page's whole argument. |
| **Raindrop** | Spacing and pacing. A sticky step list swaps real product UI, and a stat row sits straight after the hero. |
| **Polymath** | Discipline. About 148 words and one line drawing that builds on load. It proves how little a credible lab site needs. |

## Fonts on the best sites (measured)

Best means the 27 sites graded A from the frames. Grades are judgement; the fonts are computed values.

| Measure | Result |
|---|---|
| A-grade H1 class | 18 sans, 9 serif |
| RL, data and audit H1 | 9 of 17 serif |
| All sites H1 family | Geist 10, Inter 3, every other family once or twice |
| All sites body family | Geist 14, Inter 8 |
| A-grade body family | Inter 5, Geist 3 |
| Mono labels | Geist Mono 8, JetBrains Mono 5, DM Mono 4, IBM Plex Mono 3 |
| Fonts loaded anywhere | Inter 15, Geist 14, Geist Mono 8, JetBrains Mono 7, DM Mono 5 |
| STIX Two Text | 2 sites: Openbenchmarks and Tokenless |
| A-grade type medians | H1 68px (40 on mobile), H2 55px, body 17px, tracking -0.025em, H1 line height 1.1 |
| A-grade serif H1s at display size | Reducto 84, s2.dev 80, Datacurve 79, Zep 88, Openbenchmarks 90, Bluejay 80 |

The two sites closest to an independent audit are the two that use STIX Two Text. Most other serifs on the list are custom or paid, such as Exposure, Grenette, Plantijn and Terrane, while STIX Two Text is free under the OFL.

## Design decisions

Every decision below comes from the studied sites. Where the evidence set a pattern but not a value, the table says so.

| Decision | Choice | Evidence |
|---|---|---|
| Display face | STIX Two Text, weight 500 | 9 of 17 RL and data peers use a serif H1. Openbenchmarks and Tokenless, the closest peers, use this family |
| Text and data faces | Geist and Geist Mono | Most used body family (14 of 63), most used mono label (8 of 63). Serif H1 with sans body on 13 of 63. HUD and hillclimb pair a serif with Geist |
| Type scale | H1 80 (44 mobile), H2 48, H3 28, body 17, small 14, mono 12 to 14 | A-grade serif H1s run 79 to 90. A-grade medians: mobile H1 40, H2 55, body 17, ratio to body 4. The H2 sits below the median so the H1 stays the only large line |
| Tracking and leading | -0.025em, line height 1.04 for H1, 1.55 for body | A-grade medians -0.025em and 1.1. Display serifs at 1.04 match Openbenchmarks (0.94) and s2.dev (1.05) |
| Theme | Dark hero, nav, close and footer; light body | Light hero on 26 of 34 RL and infrastructure sites, while A-grade sites split 12 dark, 12 light, 3 mixed. Zep and Legora run dark first then light, and Stacktrace runs light with dark panels |
| Dark ground | #121211, neutral | 11 of 14 dark grounds are neutral, none tinted blue. Median luminance 0.06 |
| Light ground | #f7f6f3, off-white | 26 of 42 light grounds are not pure white, and 12 are warm. Openbenchmarks, Polymath, AfterQuery, Datacurve and Reducto all sit here |
| Accent | One gold, with red and green only for results | Frames: dark sites hold one accent (Browser Use, Raindrop, AgentMail, Cua, Isoquant). The sites set the count, not the hue. Gold comes from the company name and is the one choice the evidence does not make |
| Grid and width | 12 columns, 1200px, 24px gutter | Median max width 1200 of 60 sites |
| Spacing | 8-point scale, 192px between sections | Section padding sum median 160, and 192 on Boat, Kernel and s2.dev |
| Radius | 4px everywhere, square tables | Card median 4, 27 of 63 square. Button median 7.5, only 14 of 63 pill |
| Buttons | 44px, solid fill, no arrow chip | Median height 42. Hover changes colour on most controls and transform on 2 of 220 |
| Nav | 4 items plus a CTA, sticky | RL peers median 4. 44 of 63 sticky. Pricing leads all nav items. Stacktrace keeps a dark bar on a light page |
| Footer | One line, 7 links, dark | RL peers median 6 links. Privacy and terms on most sites. isoquant, Stacktrace and Browser Use all end on one dark field |
| Section structure | 5 bands: hero with console, results, why, how, close | Order from the section-job table. 3 H2s sits between the RL median (1) and the overall median (7) |
| Amount of content | 385 words, 3.4 screens | Between RL (229 words) and overall (683). Below the requested 683 on purpose: every candidate addition failed the "what it is, why it matters, proof, next step" test, and the checks list moved to Method |
| Proof | Three locked-test figures straight after the hero | 38 of 62 sites put proof there. Stat rows on Browser Use, Raindrop, Hamming |
| Hero feature | Tabbed console of recorded runs | Product in the hero on 16 of 62. Stacktrace's console and Arga and Tasklet's auto-play carry the most credibility in the frames |
| Section features | One chart, one sticky step list | Sticky lists on Raindrop, Osmosis, Pulse, Sciloop. Halluminate's left column. Tabs on 18 of 63 |
| Dropped features | Calculator, ranking widget, exploit gallery, upload box, chat paradox, beam diagram | No RL or data peer has these on a home page |
| Motion, kept | Console run, chart draw, sticky run filling in, 150ms hover colour | Live demos in about 16 notes. Draw-in on Polymath and Luminal. Pinning on 19 of 63. Median hover transition 150ms |
| Motion, dropped | WebGL shader, smooth scrolling, scroll scrub, blur reveals, spring physics, entrance on every section | WebGL on 10 of 63, Lenis on 6 of 63. Most frames show no load entrance. Reveals on only 17 of 63 |
| Libraries | Motion only | Motion on 33 of 63, GSAP on 7. No site needs six |

**Conflict to weigh.** A warm-paper and serif round was rejected on 2026-10-29. The evidence still points to a light body, so I followed it, and the dark hero, nav, close and footer keep half the page black. If it reads wrong to you, the ground is one token: `--paper` in `web/src/styles.css`.

The site now has none of Instrument Serif, the WebGL hero, the typing console's hand-set lines, the gold spheres or the streak. The console stays as a real equivalent, and motion stays where the references justify it.

## The redesign

**Routes, 11 down to 8**

| Route | Job | Words |
|---|---|---|
| Home | What it is, proof, why, how, next step | 385 |
| Method | Checks, grader probes, what numbers mean, sources, questions. Replaces Product, Research and Sample report | 474 |
| Live demo | Recorded engine runs, and live runs when the engine is reachable | 232 |
| Pricing | Three services and three questions | 164 |
| Company | The name, why now, where we are. Replaces Market | 296 |
| Request | The form | 156 |
| Terms, Privacy | Footer only | |

Old links still work: `#product` and `#research` go to Method, `#report` to Live demo, `#market` to Company.

**Cut from the site**

- Sections: Streak, three-card strip, checks list on the home page (moved to Method), grader gallery on the home page (moved to Method as a table), Paradox (one sentence moved to Company), Neutral beam, ranking widget, For Buyers and For Vendors lists, upload box, Facts row, Evidence cards on the home page (moved to Method).
- Pages: Product, Research, Sample report, Market as routes.
- Content: purchase-risk calculator, unit economics, revenue scenarios, the Touchstone Report #1 plan, future-direction list.
- Code: GSAP, anime.js, react-spring, Lenis, three.js, React Three Fiber, ShaderGradient, liquid-glass, NumberFlow, and the Watermelon components.

**Before and after, home page, same instrument**

| Measure | Preview at start | Last iteration | Redesign |
|---|---|---|---|
| Words | 1,206 | 1,372 | 385 |
| H2s | 13 | 13 | 3 |
| Sections | 13 | 15 | 5 |
| Page height, desktop | 11,163px | 13,675px | 3,042px |
| Page height, mobile | 15,908px | 18,411px | 4,058px |
| Decoded JS | 1.9MB | about 1.9MB | 0.44MB |
| Whole bundle | 2.1MB | 2.1MB | 0.76MB |
| Long tasks, software rendering | 33,037ms | 20,692ms | 160ms |
| Median frame during scroll | 1,838ms | 180ms | 8ms |
| Layout shift | 0 | 0.021 | 0 |

Timing is relative, from the same loaded machine.

**Honest critique against the references**

- **Stronger now:** hierarchy, restraint and truth. The first viewport holds up next to Browser Use and Stacktrace, and nothing on the home page is a hand-set number.
- **Behind Stacktrace:** product depth. Its panels are dense and believable, while the how section here is a small panel beside text.
- **Behind Browser Use:** instant proof. Its 3.0% against 90.5% lands in a second. Touchstone's gap is drawn, not stated, because subtracting accuracy from reward would invent a number.
- **Behind isoquant:** figures in comparison. The three proof numbers stand alone, since adding denominators would add numbers.
- **Page rhythm:** below the console the page is calm and close to a well-set memo. That suits an audit, but it has one big moment and not two.
- **No imagery:** the strongest heroes have one object, and this one has a console. It is true to the product, but less memorable than Polymath's drawing or Osmosis's landscape.

**Sample numbers, for the record**

| Where | Source |
|---|---|
| Hero console, how panel | Recorded engine runs on planted test cases, October 30, 2026. Labelled "test case" on the page |
| Chart | A fictional test environment from `out/appraisals.json`. Reward is logged. Accuracy is two measurements, shown as two dots and a dotted join |
| Three proof figures | Locked test v4, part `env`, on test cases: 21 of 21 exact, 12 of 12 gameable graders, 3 of 3 reworded test leaks. They replace the earlier 92%, 95% and 0 of 28, which test v4 on real sources no longer supports |
| Pricing, market figures | Predate this work, not re-sourced. Market figures are third-party |
| Hand-set numbers | None remain on the site |

## Not verified

- Real iPhone or Android devices, and Safari or Firefox. Mobile here is Chromium emulation.
- Real-world load and frame timing, since this machine was busy.
- The published artifact as seen in the claude.ai viewer. The files were confirmed, but opening it needs a login.
- The live engine path on the demo and request form. This build ran the recorded replay; the request form correctly reports no server.
- The last small fixes (dotted accuracy line, reward-line contrast, red grade text, form reduced motion) were built after the final video round and not re-recorded.
- Market figures, pricing ranges and the "two working days" reply promise.
- `touchstone/site.py` still carries the AUDIT.md overclaims. It is outside `web/src`.


## Per-site table (measured)

| Site | Batch | Segment | Theme | H1 px d/m | H1 font | Body | Max w | Radius btn/card | Stack (confidence) | Pin px | Reveals | Reduced motion | Mobile overflow | Video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Abundant | F24 | rl-audit | light | 16/16 | Courier New 700 | Courier New 14 | 680 | pill/4 | none detected | - | 0 | none seen, anims 1->0 | no | D+M |
| Archil | F24 | ai-infra | dark | 61.9/38 | GeistSans 500 | GeistSans 17.5 | 1152 | 7/0 | Next.js (high), Tailwind (high), shadcn (low), Radix (low), Motion (med) | - | 1 | declared, anims 63->5, 1 hidden text | no | D+M |
| Cekura | F24 | evals | light | 64/36 | Geist 500 | Geist 14 | 1120 | pill/16 | Next.js (high), Tailwind (high), Radix (med), Motion (med) | 2170 | 4 | declared, anims 9->9 | no | D+M |
| HumanLayer | F24 | dev | dark | 32/24 | IBM Plex Mono 600 | IBM Plex Mono 14.4 | 1216 | 0/0 | Next.js (high), Tailwind (high) | 10488 | 8 | declared, anims 7->7 | no | D+M |
| Openbenchmarks | F24 | rl-audit | light | 89.6/41.6 | STIX Two Text 500 | STIX Two Text 14 | 1328 | 1/0 | Next.js (high) | - | 0 | declared, anims 1->0 | no | D+M |
| Variant | F24 | design | dark | 32/32 | Variant Neue Display 400 | Variant Neue Text 14 | - | 6/0 | Next.js (high), Motion (med), Rive (high) | - | 0 | declared, anims 0->0 | no | D+M |
| hillclimb | F25 | rl-audit | light | 46.4/34.4 | EB Garamond 400 | Geist 16 | 656 | -/- | none detected | - | 0 | none seen, anims 0->0 | no | D+M |
| s2.dev | F25 | ai-infra | light+dark band | 80/48 | fontGrenette 400 | -  | 1232 | pill/12 | Next.js (high), Tailwind (high), shadcn (med), Radix (high), Motion (med) | 3038 | 0 | declared, anims 0->3 | no | D+M |
| Sciloop | F25 | rl-audit | light | 76.8/41.6 | Instrument Serif 400 | GeistSans 16.8 | 1136 | pill/16 | Next.js (high), Tailwind (high) | - | 15 | declared, anims 2->1 | no | D+M |
| SF Tensor | F25 | ai-infra | light+dark band | 56/40 | Georgia 400 | inter 16 | 1280 | 10/0 | Next.js (high), Tailwind (high), shadcn (med), Motion (med), Lottie (med) | - | 0 | declared, anims 0->0 | no | D+M |
| Sourcebot | F25 | dev | light+dark band | 72/48 | JetBrains Mono 500 | JetBrains Mono 16 | 1118 | 6/8 | Next.js (high), Tailwind (high) | 310 | 0 | declared, anims 3->3 | no | D+M |
| Boat | F26 | ai-infra | dark | 56/34 | Funnel Display 500 | Inter 16 | 1344 | 0/0 | Next.js (high), Tailwind (high) | - | 0 | declared, anims 9->0 | no | D+M |
| Epsilab | F26 | rl-audit | light | 72/26.4 | Geist 700 | -  | 721 | -/- | Next.js (high), Tailwind (high), shadcn (low), Motion (med) | - | 0 | declared, anims 3->0 | no | D+M |
| isoquant | F26 | ai-infra | dark | 60.5/36 | Arial 450 | Arial 15 | 1184 | 0/0 | Next.js (high) | - | 0 | declared, anims 1->0 | no | D+M |
| Papaya | F26 | evals | light | 68/40 | -apple-system 700 | -apple-system 14.7 | 1280 | pill/14 | Tailwind (high), shadcn (low), Radix (med) | - | 4 | declared, anims 107->0 | no | D+M |
| Stacktrace | F26 | evals | light+dark band | 80/46.4 | DM Sans 600 | DM Mono 8.6 | 1160 | 4/6 | none detected | 1240 | 0 | declared, anims 6->0 | no | D+M |
| Conductor | S24 | dev | dark hero, light body | 36/26.4 | ui-sans-serif 600 | ui-sans-serif 16 | 704 | 6/0 | Next.js (high), Tailwind (high), Radix (med) | - | 0 | declared, anims 37->1 | no | D+M |
| Coval | S24 | evals | light | 72/44 | PP Mori 400 | PP Mori 17.3 | 1320 | 5/5 | Astro (high) | - | 0 | declared, anims 2->8, 4 hidden text | no | D+M |
| Hamming | S24 | evals | dark hero, light body | 60/40 | switzer 600 | switzer 16 | 1140 | pill/12 | Next.js (high), Tailwind (high), Radix (high), Motion (med) | - | 2 | declared, anims 2->2 | no | D+M |
| Laminar | S24 | evals | dark | 42/38 | sansLanding 480 | sansLanding 18 | 880 | 4/4 | Next.js (high), Tailwind (high), Radix (med), Motion (med) | - | 0 | declared, anims 246->5, 1 hidden text | no | D+M |
| Mem0 | S24 | ai-infra | light+dark band | 64/36 | Fustat SemiBold 600 | Fustat Medium 14 | 1020 | 0/12 | Framer (high), Motion (high), Lenis (med), WebGL shaders (high) | - | 0 | declared, anims 2->1, 1 hidden text | no | D+M |
| Pulse | S24 | ai-infra | light+dark band | 56/40 | Inria Serif 400 | Geist 16 | 1342 | 0/0 | Webflow (high), Motion (med), GSAP (high), ScrollTrigger (high), Lottie (high) | - | 0 | declared, anims 2->2 | no | D+M |
| AgentMail | S25 | dev | dark | 56/44 | marketingSans 400 | marketingSans 14 | 1200 | 6/0 | Next.js (high), Tailwind (high), shadcn (med), Radix (high), Motion (med) | - | 0 | declared, anims 358->0 | no | D+M |
| Autumn | S25 | dev | dark | 56/44 | Geist 400 | Geist 16 | 1360 | 0/0 | Next.js (high), Tailwind (high), Radix (low), Motion (med), GSAP (med), ScrollTrigger (med), Lottie (med) | - | 0 | declared, anims 8->1 | no | D+M |
| Dedalus Labs | S25 | ai-infra | dark | 72/44 | nacelle 600 | -  | 1208 | 0/0 | Next.js (high), Tailwind (high), shadcn (med), Radix (med), Motion (med), GSAP (med), ScrollTrigger (med), Three.js (med), react-spring (med) | - | 4 | declared, anims 0->0 | no | D+M |
| Halluminate | S25 | rl-audit | light | 40/30 | Octave 400 | Octave 18 | - | 0/0 | none detected | - | 0 | declared, anims 0->0 | no | D+M |
| idler | S25 | rl-audit | light | 40/40 | tekio 400 | -  | 680 | 6/- | Next.js (high), Tailwind (high), shadcn (low), Radix (med), Three.js (high), WebGL shaders (high) | - | 0 | declared, anims 0->0 | no | D+M |
| Kernel | S25 | ai-infra | light | 16/16 | Inter 300 | Inter 20 | 1312 | 0/0 | Next.js (high), Tailwind (high), Radix (med), Motion (med) | - | 0 | declared, anims 0->0 | no | D+M |
| Luminal | S25 | ai-infra | dark | 60/36 | ui-sans-serif 500 | ui-sans-serif 14 | 1150 | 4/0 | Next.js (high), Tailwind (high) | - | 0 | none seen, anims 25->25 | no | D+M |
| Caution | S26 | ai-infra | light+dark band | 132.4/48.2 | Plus Jakarta Sans 550 | Plus Jakarta Sans 17.5 | 848 | 60/16 | none detected | - | 5 | declared, anims 27->0 | no | D+M |
| Context.dev | S26 | ai-infra | light | 56/40 | rethinkSans 400 | rethinkSans 16.2 | 1170 | pill/7 | Next.js (high), Tailwind (high), shadcn (low), Radix (high), Motion (med) | 992 | 0 | declared, anims 19->0 | no | D+M |
| Tokenless | S26 | rl-audit | light+dark band | 40/32 | STIX Two Text Variable 400 | Figtree Variable 15 | 1080 | -/0 | Astro (high), Tailwind (high) | - | 0 | declared, anims 1->0 | no | D+M |
| Better Auth | Sp25 | dev | dark | 36/24 | Geist 400 | Geist 13 | - | 0/0 | Next.js (high), Tailwind (high), shadcn (med), Radix (med), Motion (med), WebGL shaders (high) | 1054 | 0 | declared, anims 56->1693 | no | D+M |
| Bluejay | Sp25 | evals | light | 80/40 | Terrane Serif Bold 700 | Haffer Regular 14 | 812 | pill/8 | Framer (high), Motion (high) | - | 0 | declared, anims 1->0 | no | D+M |
| Cua | Sp25 | dev | dark | 79.2/46 | Outfit 500 | Inter 18 | 1152 | pill/16 | Astro (high), Tailwind (high), Motion (med) | - | 0 | declared, anims 102->0 | no | D+M |
| cubic | Sp25 | dev | dark | 68/29 | Geist 200 | Geist 18 | 800 | 8/16 | Framer (high), Motion (high), Lenis (med), Lottie (med) | 4774 | 4 | declared, anims 1->0 | no | D+M |
| Tinfoil | Sp25 | ai-infra | light+dark band | 48/36 | aeonikFono 300 | aeonikFono 18 | 1280 | 4/4 | Next.js (high), Tailwind (high), shadcn (med), Radix (med), Motion (med) | - | 0 | declared, anims 2->0 | no | D+M |
| Arga Labs | Sp26 | rl-audit | light | 54/48 | Geist Variable 500 | Geist Variable 15.2 | 1280 | pill/0 | Tailwind (high), shadcn (low), Radix (med) | - | 0 | declared, anims 36->0, 2 hidden text | no | D+M |
| Expanse | Sp26 | ai-infra | light+dark band | 80/56 | Manrope 700 | Manrope 20 | 1310 | 0/0 | SvelteKit (high), Tailwind (high), Lottie (high) | 2418 | 3 | declared, anims 23->0, 6 hidden text | no | D+M |
| Hub | Sp26 | rl-audit | light | 86.4/44 | Geist 600 | Geist 18 | 1280 | 99/12 | Next.js (high), Three.js (high), WebGL shaders (high) | - | 8 | declared, anims 20->0 | no | D+M |
| Tasklet | Sp26 | design | light | 60/36 | Season Mix 600 | Inter 16 | 1280 | 11/0 | Tailwind (high) | - | 6 | declared, anims 7->6 | no | D+M |
| Datacurve | W24 | rl-audit | light | 79.2/44 | exposure 400 | suisseIntlRegular 18 | 654 | 8/- | Next.js (high), Tailwind (high), Motion (med), GSAP (med), ScrollTrigger (med), Lenis (high), Three.js (high), WebGL shaders (high) | 936 | 7 | declared, anims 4->0, 1 hidden text | no | D+M |
| Greptile | W24 | dev | light+dark band | 96/60 | Anybody 700 | DM Sans 16 | 672 | 0/0 | Next.js (high), Tailwind (high), Radix (med), Motion (med), Lottie (high) | - | 0 | declared, anims 9->6 | no | D+M |
| Gumloop | W24 | design | light | 48/36 | Gellix 500 | GeistSans 14 | 1360 | 8/8 | Next.js (high), Tailwind (high), shadcn (med), Motion (med) | 930 | 0 | declared, anims 34->10 | no | D+M |
| Legora | W24 | design | dark | 56.2/- | Legora Sans Regular 400 | Legora Sans Regular 15 | 1392 | 24/0 | Framer (high), Motion (high), Lenis (med), Spline (med) | 2480 | 1 | declared | n/a | D frames |
| Momentic | W24 | dev | light | 56/40 | BDO Grotesk 500 | BDO Grotesk 16 | 1376 | 8/4 | Astro (high), Tailwind (high), Motion (med), GSAP (med), ScrollTrigger (med) | 930 | 0 | declared, anims 7->0 | no | D+M |
| Raindrop | W24 | evals | dark | 58/25.4 | AlphaLyrae 500 | Inter 14 | 1280 | 3/8 | Next.js (high), Tailwind (high) | 1922 | 0 | declared, anims 0->0 | no | D+M |
| Reducto | W24 | ai-infra | light | 84/48 | reductoSerif 470 | Inter 16 | 1280 | 0/0 | Next.js (high), Tailwind (high), Radix (high), Motion (med) | - | 4 | declared, anims 14->0 | no | D+M |
| Reform | W24 | design | dark | 80/34 | Instrument Sans 500 | Roboto 16 | 1280 | 8/12 | Webflow (high), GSAP (high), ScrollTrigger (high) | 992 | 4 | declared, anims 6->6 | no | D+M |
| Ubicloud | W24 | ai-infra | light | 70/40 | Bevietnampro 600 | Bevietnampro 16 | 1200 | 12/24 | Webflow (high) | - | 0 | declared, anims 0->0 | no | D+M |
| Vibrant Labs | W24 | rl-audit | dark | 64/- | Space Grotesk Bold 700 | Space Grotesk Regular 16 | 1400 | 64/0 | Framer (high), Motion (high), Lenis (med), Three.js (high), WebGL shaders (high), Lottie (high) | 620 | 0 | declared | n/a | none kept |
| Zep | W24 | design | dark | 88/44 | martinaPlantijn 400 | neueMontreal 17 | 1248 | 6/0 | Next.js (high), Tailwind (high), shadcn (low), Motion (med) | - | 1 | declared, anims 1->1 | no | D+M |
| AfterQuery | W25 | rl-audit | light | 24/24 | serif 400 | sans 18 | 688 | pill/4 | Next.js (high), Tailwind (high), Motion (med) | - | 40 | declared, anims 2->0 | no | D+M |
| Browser Use | W25 | ai-infra | dark | 88/44 | Geist 400 | Geist 16 | 1200 | pill/16 | Next.js (high), Tailwind (high), Radix (med), WebGL shaders (high) | - | 1 | declared, anims 6->0, 1 hidden text | no | D+M |
| Confident AI | W25 | evals | dark | 56/32 | Aeonik 500 | Satoshi 14 | 1267 | 0/0 | Next.js (high), Tailwind (high), WebGL shaders (high) | - | 0 | declared, anims 163->92 | no | D+M |
| HUD | W25 | rl-audit | light+dark band | 64/32 | farnham-headline 500 | Geist 14 | 1200 | 12/0 | Next.js (high), Tailwind (high), shadcn (med), Radix (high), Motion (med) | - | 0 | declared, anims 50->0 | no | D+M |
| Mastra | W25 | dev | dark | 54/30 | greed 520 | greed 17 | 1328 | 57/40 | Next.js (high), Tailwind (high), Radix (low), Motion (med), Lottie (med) | 3906 | 1 | declared, anims 3->0, 4 hidden text | no | D+M |
| Onlook | W25 | dev | dark | 60/35.1 | Inter 300 | Inter 16 | 1152 | 8/14 | Next.js (high), Tailwind (high), shadcn (med), Radix (high), Motion (med), WebGL shaders (high), Unicorn Studio (med) | - | 0 | declared, anims 5->0 | no | D+M |
| Osmosis | W25 | rl-audit | dark | 48/40 | 205 Tf Exposure 0 400 | Neuehaasgroteskdisplay 20 | 1267 | 4/- | Webflow (high), GSAP (high), ScrollTrigger (high), Lottie (high) | 1860 | 9 | declared, anims 0->0 | no | D+M |
| Roark | W25 | evals | light | 67.2/32.8 | Bricolage Grotesque 600 | Hanken Grotesk 13.5 | 1240 | pill/16 | Next.js (high), Tailwind (high) | - | 13 | declared, anims 71->0 | no | D+M |
| 21st | W26 | design | dark | 85/40 | Inter 700 | Inter 20.9 | 1104 | 10/10 | Next.js (high), Tailwind (high), shadcn (low), Radix (med), Motion (med), WebGL shaders (high) | - | 0 | declared, anims 14->2, 1 hidden text | no | D+M |
| Luel | W26 | rl-audit | light | 60/36 | Geist 300 | Geist 14 | 1056 | pill/16 | Next.js (high), Tailwind (high), Radix (med) | 396 | 0 | declared, anims 4->0 | no | D+M |
| Polymath | W26 | rl-audit | light | 22.4/22.4 | SeasonMix 600 | SeasonMix 17.3 | 720 | 5/- | Next.js (high), Tailwind (high), Lenis (high), Lottie (med) | - | 0 | declared, anims 1->1 | no | D+M |

## Per-site copy (measured)

| Site | H1 | Subhead (first 110 chars) | Words on page | Hero CTAs |
|---|---|---|---|---|
| Abundant | Abundant |  | 143 | ◐ Toggle Mode |
| Archil | The serverless runtime for intelligence. | Sandboxes and durable disks for AI. Run code on demand, keep files between calls, and share data across your s | 1617 | Start building / Copy prompt Copied / Decline |
| Cekura | Test, Monitor and Self Improve voice agents | Launch in minutes, not weeks. Test your agent before going live, monitor real production calls, and continuous | 706 | Book a Demo / Start Free Trial / Decline |
| HumanLayer | The Multiplayer Coding Agent Workspace | HumanLayer is a multiplayer coding agent IDE and cloud that works seamlessly from your workstation to anywhere | 1462 | DOWNLOAD ⌘+Enter / LINUX/WINDOWS INSTALL INSTRUCTIONS |
| Openbenchmarks | Openbenchmarks | Independent benchmarks for build-vs-buy decisions. | 978 | Backed by Y Combinator |
| Variant | Endless designs for your ideas, just scroll. | Most tools make you explain what you want. Variant just shows you. | 43 | Sign up / Sign in / Surprise me |
| hillclimb | hillclimb | Training data for recursive self-improvement | 137 | - |
| s2.dev | Just streams | S2 is the API for unlimited, durable, real-time streams. | 392 | Get started / Copy prompt |
| Sciloop | The hardest problems, built by the best minds. | IMO gold medalists, Codeforces grandmasters and top domain experts write the problems no model can solve yet. | 506 | Start earning as an expert / Get datasets |
| SF Tensor | Train what doesn't exist yet. | Novel architectures, proprietary data, frontier scale. We handle everything between your idea and the silicon  | 618 | Plan a training run / Talk to an engineer |
| Sourcebot | Code understanding for humans and agents | Sourcebot is a self-hosted tool that helps humans and agents search, navigate, and understand complex enterpri | 474 | $ npx setup-sourcebot / Book a demo |
| Boat | Most powerful & affordable cloud VMs for agents | Spawn thousands of cloud computers with a browser, persistent files, for your agents, without having to manage | 1080 | macOS |
| Epsilab | The training grounds for real-world agents. | RL environments for real-world use cases. | 74 | - |
| isoquant | Inference at the frontier of model performance. | Run open models at the lowest cost and latency, with APIs that work with your existing stack. | 683 | GET API KEY / TALK TO US |
| Papaya | Continuously improve your agents. | Papaya reads your agents' traces and code, finds the fixes you didn't know to look for, and opens the PR — eve | 1121 | Book a demo |
| Stacktrace | Run unsupervised intelligence with confidence. | Try Stacktrace → Try it in your browser | 491 | Try Stacktrace → / Try it in your browser / Reliability Dele |
| Conductor | Run a team of coding agents on your Mac. | Get Conductor “feels like going from typing with two fingers to having eight arms” Frank, Product Designer, Th | 281 | Get Conductor |
| Coval | Scale voice AI agents with confidence. | Coval gives teams the voice AI testing, evals, and QA loop to prove what works before launch, catch failures i | 1115 | Request a Demo / Start Free Trial |
| Hamming | The trust platform for voice and chat agents | Test before launch. Red-team what could go wrong. Monitor every production call. So failures become regression | 1583 | Request a demo / Sign up |
| Laminar | Ship reliable agents | Laminar is an open-source agent observability platform. It automatically catches agent failures at scale and h | 1123 | Get started – free / Setup with in minutes |
| Mem0 | AI memory that persists across sessions and agents | Drop-in memory infrastructure for AI agents and apps. Context that persists. Built for production. | 658 | Copy to Clipboard Copied! |
| Pulse | Document intelligence for trust and scale | Pulse uses OCR, layout, and vision models to produce high quality outputs from complex documents for enterpris | 1168 | Chat with Sales / Try for free / Close Cookie Popup |
| AgentMail | Email Inboxes for AI agents | We're not AI for your email, we're email for your AI Learn how it works | 506 | Learn how it works |
| Autumn | Usage-based billing for B2B companies | Billing infrastructure that grows with you: complex contract terms, any usage model, and end-to-end automation | 740 | PRICING / DISCORD / START FOR FREE |
| Dedalus Labs | The Fastest Persistent Computer for Agents | Join waitlist Docs $ curl -fsSL https://www.dedaluslabs.ai/install/dedalus   bash | 203 | Docs |
| Halluminate | Halluminate is a data research lab building benchmarks and RL environm | Our first area of focus is economically valuable workflows in financial services and consulting, but we are ra | 321 | - |
| idler | Push the frontier of your model | Reinforcement learning environments built from real production work | 22 | Contact / Browse / Careers |
| Kernel | you build agents. we give them the internet. |  | 399 | start building / book demo |
| Luminal | Inference at the speed of light. | Luminal compiles AI models to give you the fastest, highest throughput inference in the world. | 441 | GET STARTED / GITHUB |
| Caution | Secure hosting | Take entire classes of attacks off the table. Deploy sensitive software in minutes with a familiar Git workflo | 884 | Book a demo |
| Context.dev | Give your agents the internet | API for agents to scrape, search, monitor, and collect data from the web. | 1885 | Crawl the web / Explore / View all stories |
| Tokenless | Tokenless | We find flaws in RL environments and evals and help you fix them. As models become more capable, training and  | 178 | - |
| Better Auth | The most comprehensive authentication framework | Community / Changelog / Legal Toggle theme | 1581 | Get Started / DECLARATIVE CONFIG |
| Bluejay | Test, monitor, and improve voice & chat AI agents | Make every interaction better than the last one through real-world simulations and actionable observability | 347 | Request a Demo / Start for Free |
| Cua | A shared Space for every team and agent A shared Space for every team  | Your computers, shared by your team and its agents. | 849 | See pricing |
| cubic | AI code reviews for complex codebases | cubic finds hard-to-find bugs in pull requests and your entire codebase. | 1239 | Try cubic for free |
| Tinfoil | Encrypted Encrypted Cloud Compute | Tinfoil is a security research lab building an AI cloud for private, verifiable computation. | 1036 | Sign in / Get Started |
| Arga Labs | Real world sandboxes for testing and training AI agents. | Deploy simulation environments with stateful twins of the APIs, CLIs, and MCPs your agents use. Book a demo St | 510 | See more / Book a demo / Start a sandbox |
| Expanse | Expanse gets you more out of the GPUs you already have. | Expanse delivers compute certainty. We predict exactly what every job needs before it runs, so your cluster do | 866 | BOOK A DISCOVERY CALL / SEE HOW IT WORKS / Pause |
| Hub | Deployment velocity for physical AI. |  | 650 | Become an operator → / Deploy with Hub → |
| Tasklet | Run your business on agents | Automate any business task with AI agents that run 24x7. Connect your company's tools and share agents & conte | 1967 | Create your agent / Book a demo |
| Datacurve | Defining intelligence | Datacurve is pioneering the research and data collection infrastructure that will teach AI how to shoulder the | 177 | Get in touch / See our research |
| Greptile | The AI Code Reviewer | AI agents that review and test pull requests with full context of the codebase. Contact sales Start now onboar | 1208 | Contact sales / Start now |
| Gumloop | Build, share, optimize & control agents | New Chat Revenue GTM Agent Account Researcher Outbound Writer Customer Success Renewal Watch Ticket Triage GTM | 3153 | Get Started / Book a demo / New Chat |
| Legora | Legal work, without limits. | Collaborative AI for exceptional lawyers Book a demo | 769 | Book a demo |
| Momentic | Catch bugs before they ship. | Mo is an AI QA engineer that tests your app end to end. Verify critical flows and find bugs from a prompt. | 2144 | Try for free / Setup for agents / DECLINE |
| Raindrop | Detect agent issues. Prevent them from happening. | Find silent failures in production, investigate what went wrong, and simulate changes in CI. | 2546 | Start building / Book a demo |
| Reducto | Turn documents into data. | The agentic document platform for leading AI teams who demand enterprise performance at scale. One platform fo | 1407 | Try for free |
| Reform | Your operation is one of a kind. Your AI should be too. | One platform for building and managing AI agents that perform all your high-stakes operational work. Show me S | 1311 | Show me Show me |
| Ubicloud | Open source alternative to AWS | Ubicloud provides cloud services on bare metal providers, such as Hetzner, Leaseweb, or AWS Bare Metal. You ca | 462 | Try it now |
| Vibrant Labs | Autoscaled RL data for frontier agents | Post-training data that scales without armies of human annotators | 316 | Explore our research |
| Zep | Reliable agents need the right context | Zep unifies business data, documents, and conversations into shared, governed context so agents can complete t | 1398 | Request a Demo / Graphs / voyager-prod |
| AfterQuery | We teach machines how experts think. | The future of AI won’t be trained on more data, it will be trained  on better thinking. | 497 | Get data / Explore research |
| Browser Use | Agents that use the browser. And browsers for your own. | Browser Use Agents finish the task. Browser Infrastructure is the simple cloud browser for your own agents. Ru | 598 | Run an agent / Connect your agent |
| Confident AI | Ship better AI as a team. Not as individuals. | Monitor in production, review traces, and turn expert feedback into repeatable evals—all in one workspace for  | 2923 | Contact sales / Try Now For Free |
| HUD | The platform for building RL environments | Encode your expertise into environments to train and evaluate models, and create the post-training data that a | 678 | Start building / $ pip install hud |
| Mastra | Build AI agents | Read → Read → Read → Read → Read → Read → Read → Read → Read → Read → | 1115 | Get a demo / Quickstart |
| Onlook | The Developer Tool for Visual Engineers | Onlook is a free, local-first editor where designers craft exceptional experiences in code | 1172 | Download Onlook / Accept |
| Osmosis | Forward Deployed Reinforcement Learning | Osmosis helps companies create task-specific models that beat foundation models at a fraction of the cost. | 280 | BOOK A DEMO |
| Roark | Test, monitor, and improve the voice AI agents you already run. | Roark is the QA and evals platform for voice AI, not another agent builder. Simulate your agent against hundre | 1568 | Get started free → / Book a demo |
| 21st | Just copy-paste real designs. | Find components, copy prompts, and ship polished UI with your AI agent. | 402 | Get 21st free / Browse components / Home |
| Luel | The Frontier of Data | Luel is a multi-modal lab powering the foundations of machine perception. Built upon our proprietary, continuo | 92 | Contribute / Browse datasets / Accept |
| Polymath | Simulation environments for training & evaluating autonomous agents. |  | 148 | Blog / Careers |

## Per-site notes from the frames

These notes come from reading the contact sheets. Each ends with what was seen and what was inferred.

### Abundant (F24)

- hero: text only, light, monospace terminal-style page, tiny logo, "Toggle Mode" pill bottom right.
- load: text types in line by line (seen load 1.5-4.3s).
- scroll: plain scroll.
- interactive: keyboard-style option list "[x] Explore our datasets" and a form; Toggle Mode button (not clicked in frames).
- proof: none; one-line claims of backers in copy.
- mobile: single column, same content, no breakage.
- grade: B, distinctive but austere, very short
- learn: a typed, terminal-register intro can feel credible with zero imagery.
- seen-or-inferred: seen typing and form; theme toggle inferred from label.

### Archil (F24)

- hero: red gradient field with animated wave lines and node labels (Research, Analytics, Training, Agents), light text; cookie banner bottom right
- load: headline and waves appear by ~8s
- scroll: hero compresses to a band at top, then white sections; hero reappears at 55.9s (scroll back)
- interactive: code snippet tabs under "Get started"; widget frames cycle tabs/cards ("Everything agents need to work with real data") with content swapping
- proof: customer logo row under hero; quote cards; stat blocks (100x, 30x, 99.99%) on mobile
- mobile: stacks well; cookie banner covers a lot of the screen
- grade: B, strong hero, cookie banner and tabs crowd the lower page
- learn: a single data-driven animated hero beats a generic gradient
- seen-or-inferred: seen tabs swapping and the hero; waves animation inferred

### Cekura (F24)

- hero: white/lavender wave gradient, centred headline, CTA pair; cookie banner overlays.
- load: headline fades in from faint grey (2.8s).
- scroll: plain with fade-in blocks; section "Build self-improving loops" with UI diagrams revealing.
- interactive: nav dropdown opens on hover; mobile full menu list.
- proof: logo row (PwC, Deloitte, Jobber, Quo) after hero.
- mobile: stacked, cookie banner covers much of screen.
- grade: B, tidy but template-like
- learn: nothing beyond fade-in diagrams.
- seen-or-inferred: seen dropdown and menu.

### HumanLayer (F24)

- hero: dark navy, monospace, headline, video thumbnail of founder, terminal install line. Dark.
- load: text appears ~2.5s.
- scroll: UI diagrams of workspace (tasks, artifacts) animated step by step along scroll; node diagrams drawn in teal.
- interactive: video play button; mobile menu list.
- proof: logo row under hero; SOC 2 badge and testimonials late.
- mobile: stacks cleanly.
- grade: B, coherent dev look, small type
- learn: node diagrams that draw in teal on dark navy.
- seen-or-inferred: seen diagrams change; scrubbing inferred.

### Openbenchmarks (F24)

- hero: warm off-white, serif wordmark "Openbenchmarks", leaderboard tables below. Text and data, light.
- load: plain.
- scroll: stack of benchmark tables, each with small ranked rows; plain scroll.
- interactive: none.
- proof: real leaderboard data is the proof; Backed by Y Combinator tag.
- mobile: tables fit narrow screen; readable.
- grade: A, data as design, serif restraint
- learn: lead with dense ranked tables in a serif/mono pairing.
- seen-or-inferred: seen all.

### Variant (F24)

- hero: Dark near-black page with a tiled grid of empty cells, left headline "Endless designs for your ideas, just scroll" with grey/italic emphasis, two small buttons and a bottom prompt bar; dark. Tiles appear mostly empty/dark in frames.
- load: Quick fade-in of text; grid tiles faint.
- scroll: Likely infinite canvas of design tiles; in frames, text stays pinned while a few widgets appear (a dial UI at 31.7s, a small widget at 26.7s).
- interactive: Prompt bar and "Surprise me" button; no clicks seen.
- proof: None visible.
- mobile: Same layout in one column, prompt bar fixed at bottom; mostly black, nothing broken.
- grade: B, bold concept but tiles read empty in capture.
- learn: A single fixed prompt bar as the only call to action keeps a dark page focused.
- seen-or-inferred: Seen pinned text and two pop-in widgets; infinite design feed inferred from copy.

### hillclimb (F25)

- hero: Text only, a near-blank light grey page with a small serif wordmark, a mission paragraph and a hiring link; light.
- load: None; page appears by 1.5s.
- scroll: Plain scroll (page fits one screen).
- interactive: A "Our previous work" disclosure expands to a short grey paragraph.
- proof: Single line naming backers (Tier 1 VCs, Jeff Dean, Paul Graham, angels from OpenAI/Anthropic/DeepMind/xAI/Meta).
- mobile: Same single column, readable, nothing broken.
- grade: B, deliberately austere; confident but no product visual.
- learn: A short list of named backers in plain text can carry credibility without logos.
- seen-or-inferred: All seen; disclosure open at 7.8s.

### s2.dev (F25)

- hero: white, centred serif "Just streams", logo grid in boxed cells below. Light.
- load: headline types/unveils letter by letter (frame "Just").
- scroll: red-blue ribbon graphic, code snippet, "Every stream is a URL"; "One primitive, many uses" list; "Fast, and scales" benchmark.
- interactive: language tabs on code block (CURL, TypeScript...); list rows.
- proof: boxed logo grid (beam, Kernel, Trigger.dev) in hero.
- mobile: logo grid 2x3, fine.
- grade: A, restraint, serif plus code
- learn: logo grid inside hero; serif headline.
- seen-or-inferred: seen reveal; tab changes inferred.

### Sciloop (F25)

- hero: pale blue/peach gradient, serif headline "The hardest problems, built by the best minds."
- load: headline fades in ~7s.
- scroll: university logo strip, "Raw brilliance meets deep expertise" with chip cards; "How Sciloop works" with a stack of UI cards that slides.
- interactive: three-step list swaps card.
- proof: university logos (Berkeley, IITs, Stanford, Cambridge).
- mobile: stacks fine.
- grade: B, elegant, soft
- learn: institutional logos as proof.
- seen-or-inferred: seen.

### SF Tensor (F25)

- hero: white, serif headline, wide dashboard screenshot below over blue tile strip.
- load: tile pattern flashes.
- scroll: isometric cube illustrations; "Buy the training outcome" dark band at end.
- interactive: nav dropdown opens (Enterprises / AI Labs).
- proof: none clear.
- mobile: stacks, screenshot below.
- grade: B, clean, little depth
- learn: dark closing band after light page.
- seen-or-inferred: seen dropdown.

### Sourcebot (F25)

- hero: off-white, monospaced headline, dark command button, logo row. Light.
- load: slow render.
- scroll: logo row then quote cards; toast "Stop overpaying for Sourcegraph" appears bottom.
- interactive: none.
- proof: logo row, three quote cards.
- mobile: only 2 frames, grey; can't judge.
- grade: B, crisp, minimal
- learn: monospaced headline.
- seen-or-inferred: seen toast.

### Boat (F26)

- hero: deep blue, pixel-art scene of boats/forest with water reflection, headline left, install command box. Illustration, dark-ish.
- load: scene visible by 1.5s; pixel boats appear to animate.
- scroll: blue hero turns to white sections with pixel diagrams; pricing slider with pixel boat chart; blue testimonial/logo section at end.
- interactive: pricing sliders and size buttons; command tabs (macOS/Linux/Windows).
- proof: Y Combinator line, one quote card with avatar and logo grid (T3 etc.).
- mobile: stacked well; pricing tables readable.
- grade: A, strong single visual idea, consistent
- learn: one pixel/illustrated motif carried into charts and pricing.
- seen-or-inferred: seen slider UI; boat animation inferred.

### Epsilab (F26)

- hero: bold headline above a large skeuomorphic Game Boy with a green LCD screen, light grid background
- load: blank ~5s, then full hero
- scroll: nearly pinned; Game Boy stays, a sticker pack card appears to the right by ~39s
- interactive: widget frames show the screen flickering/changing and rainbow glow when clicked
- proof: "Backed by Y Combinator" chip under the subhead
- mobile: Game Boy fills the screen, sticker pack strip at the bottom; fine
- grade: A, one memorable object, committed
- learn: one tactile hero object that responds to clicks
- seen-or-inferred: seen the object and screen change; text on LCD cycling inferred

### isoquant (F26)

- hero: dark, moody mountain-lake photograph with headline left over it. Photo, dark.
- load: photo and headline appear ~4s.
- scroll: photo scrolls away; benchmark number cards ($0.07, 452) with pricing; "engineering behind" diagrams reveal one by one; code block.
- interactive: dropdown in code block widget; no tab change seen clearly.
- proof: pricing and benchmark numbers, case-study stat "91.7%".
- mobile: well stacked, bold numbers.
- grade: A, atmospheric hero plus clean data cards
- learn: a dark photographic hero then hard numbers; dark grid diagrams.
- seen-or-inferred: seen all.

### Papaya (F26)

- hero: light blue, isometric stack of orange/yellow/blue layers with data lines. Illustration.
- load: quick.
- scroll: stack slides up and out; testimonial cards; stat cards "+20%", "-30%", "$25K+"; numbered steps.
- interactive: FAQ accordion (mobile frames).
- proof: quote cards, stat tiles, SOC 2 line, YC.
- mobile: stacks well.
- grade: B, polished illustration
- learn: three outcome stats as big tiles.
- seen-or-inferred: seen all except motion in stack.

### Stacktrace (F26)

- hero: cream with serif/red italic emphasis, dark console panel below with live text. Mixed.
- load: quick.
- scroll: dark console lines change; section "For the agents your team runs" with fleet UI; phone mock.
- interactive: tabs (Reliability / Cost / Security) in hero change console content; mobile menu.
- proof: Works-with Claude/Devin/Codex row; YC.
- mobile: console below headline, cookie banner.
- grade: A, console-as-hero, serif+red accent
- learn: tabbed live console in hero.
- seen-or-inferred: seen tabs and console changes.

### Conductor (S24)

- hero: sky and clouds photo background, pixel-style wordmark, large real product UI screenshot below, light
- load: page blank for ~3s, then screenshot and sky appear; screenshot fades in
- scroll: screenshot sits near the top then scrolls away; later sections show an animated chat/avatar mock ("Ludwig has entered the chat") that appears to build in place
- interactive: hover on nav only; video play button seen in the screenshot
- proof: "Trusted by 100k+ builders" logo row after hero; X-post style quote cards on mobile
- mobile: stacks cleanly; the feature mock is blurry but intact
- grade: B, playful photo hero fights the serious product mock
- learn: a real product screenshot directly under the hero sells faster than copy
- seen-or-inferred: seen photo hero, screenshot and mock; scroll-linked build inferred

### Coval (S24)

- hero: centred headline on warm grey, dot/particle cloud illustration below, light
- load: none seen; dots visible from first frame
- scroll: hero text shrinks and slides up while the particle cloud stays, a red tag appears over it (pinned/scrubbed hero for ~30s of frames); mobile reveals "Find signal in the noise" ring of dots
- interactive: nav dropdown shown on hover (Product menu)
- proof: logo row (chime, perplexity, zoom, toast, Upstart) on mobile; banner announcing $28M Series A at top
- mobile: stacks fine; logos readable
- grade: A, one idea (noise to signal) carried by one illustration
- learn: pinned hero with a single scrubbed graphic, nothing else
- seen-or-inferred: seen the pinned hero and tag; particle motion inferred

### Hamming (S24)

- hero: centred headline with blue accent words, blue CTA, product UI cards peeking below, light
- load: none beyond fade-in; cookie banner over the product UI
- scroll: plain scroll with product screenshots, testimonial, logos, stat row (10K+, 50K+, 95-96%, 65+); sections alternate headline plus UI mock
- interactive: sections with tabs-like steps ("Test it. Red-team it. Never stop watching it"); FAQ accordion on mobile
- proof: logos and stats right after hero, testimonials with photos, SOC 2 badge
- mobile: stacks, cookie banner covers about a third of the screen
- grade: B, thorough proof but generic SaaS layout
- learn: stat row (numbers with one-line labels) below logos
- seen-or-inferred: seen all; tab behaviour inferred

### Laminar (S24)

- hero: dark, small-text headline left, node diagram of agent dots/grid right, logo row. Dark.
- load: slow, diagram nodes appear.
- scroll: hero diagram is held for very long time (30+ frames same) - essentially sticky; then trace UI panel rises; sections with trace screenshots.
- interactive: none clear.
- proof: logo row in hero; nothing else seen.
- mobile: headline large, trace UI below; fine.
- grade: B, solid dev tool look
- learn: diagram of the system's flow as hero.
- seen-or-inferred: seen static hero over many frames; pin inferred.

### Mem0 (S24)

- hero: lavender top with centred headline and code window; below a dark section with "Built for developers". Mixed.
- load: code panel in a lavender frame.
- scroll: dark section reveals chat mock in a yellow panel; counters ("200,000+"); logo strip; footer purple.
- interactive: SDK / Harness / Plugin tabs above code (mobile frames).
- proof: logo strip and 200,000+ developers counter; compliance badges in footer.
- mobile: stacks, cookie banner big.
- grade: B, mixed light/dark, a bit busy
- learn: counter plus logos together.
- seen-or-inferred: seen tabs; click effect inferred.

### Pulse (S24)

- hero: pale blue, isometric document illustration, headline left, logo row bottom. Light.
- load: quick.
- scroll: hero transitions to dark navy section "How Pulse processes unstructured data" with step list and stacked layers visual; steps highlight in sequence (pinned).
- interactive: step list highlights Step 1-5 in sequence.
- proof: logo row (UC Berkeley, Samsung, Cloudera); compliance badges; testimonial.
- mobile: stacks, cookie panel huge.
- grade: B, clear, standard
- learn: light hero to navy step pipeline.
- seen-or-inferred: seen highlights; pin inferred.

### AgentMail (S25)

- hero: dark, large orange envelope illustration with code card sliding out, wireframe globe behind. Animated mock/illustration.
- load: headline fades in orange then white; envelope rises (seen 6-19s).
- scroll: hero envelope stays pinned while a code letter slides out of it and headline lifts (pinned, scrubbed); later conventional sections.
- interactive: widget frames show a feature list with image swap on the right.
- proof: logo strip (clay, Replit, eve, Factory etc.) right under hero; "1B+ requests" stat; customer story card (Alchemy).
- mobile: envelope stays hero; sections stack; fine.
- grade: A, one strong object, orange on black
- learn: one hero object that "delivers" the product on scroll; single accent colour.
- seen-or-inferred: seen pinned slide-out across ~15 frames.

### Autumn (S25)

- hero: dark, headline left, code window in purple-magenta gradient frame right, logo strip below. Dark.
- load: code panel and headline fade in 2-7s.
- scroll: plain-ish; testimonial section scales in as a green slab with magenta/orange side tabs; later problem/solution blocks.
- interactive: mobile menu opens full-screen list; no widget clicks seen.
- proof: logo strip in hero; large green customer quote card.
- mobile: menu works, code window below headline, feature list stacked; ok.
- grade: B, bold colour slab, otherwise standard
- learn: one saturated testimonial block breaks a dark page well.
- seen-or-inferred: seen all; scale-in inferred from neighbours.

### Dedalus Labs (S25)

- hero: near-white, headline with purple highlighted words, small purple CTA, curl command.
- load: headline fades from faint; slow.
- scroll: sections swap in place (headline changes "Machines that start in <50ms", etc.) with comparison charts; pinned-like sequential panels.
- interactive: theme menu (Light/Dark/System) on mobile; no widget clicks seen.
- proof: "Backed by Y Combinator" pill.
- mobile: stacks fine, big text.
- grade: B, minimal, good type, sparse
- learn: purple accent on single phrase; sequence of one-claim panels.
- seen-or-inferred: seen panel swaps; pin inferred.

### Halluminate (S25)

- hero: a sentence of mission text on a pale blue gradient, sticky left column of links; light
- load: fade
- scroll: right column scrolls an entire benchmark write-up with a leaderboard while the left column stays sticky
- interactive: Histogram, 2D Plot and Summary Table tabs swap the benchmark chart
- proof: the benchmark itself, no logos
- mobile: single column, charts readable
- grade: A, the results are the page
- learn: publishing a result on the home page is stronger proof than any logo row
- seen-or-inferred: all seen in frames, read directly by the lead

### idler (S25)

- hero: Light grey page with a large dotted, colourful isometric cube that slices and rearranges, tiny headline "Push the frontier of your model" and small pill buttons; light.
- load: Cube fades in at about 4s, then begins shifting.
- scroll: Hero appears pinned; cube animation advanced during scroll (cube pieces separating at 9s to 10s). Only about 10s captured.
- interactive: Pill buttons hover only; none clicked.
- proof: None visible.
- mobile: Cube is scaled and centred; same elements; clean.
- grade: A, one memorable animated object, tight restraint.
- learn: One ambitious generative graphic with almost no text can set tone; we could try gold dotted mark.
- seen-or-inferred: Seen cube animation; whether it is scroll- or time-driven is inferred (unclear).

### Kernel (S25)

- hero: giant black wordmark cropped at top, lowercase headline on cream, black buttons, logo strip, light
- load: none seen
- scroll: green and black product panels slide in, a benchmark table section, quote on a green block, footer link matrix; feels like a horizontal card row (cards cut off at the right)
- interactive: nav hover; "copy prompt" button near the end
- proof: logo strip under hero ("loved by 11,000+ teams"), customer story cards, one quote with name
- mobile: single column; wordmark cropped at bottom; cards stack; fine
- grade: A, strong type and one loud green accent
- learn: one oversize wordmark as the brand mark
- seen-or-inferred: seen the panels and the table; horizontal movement inferred from cut-off cards

### Luminal (S25)

- hero: dark green-black, terminal-style headline with green accent line, green button, faint circuit lines, dark
- load: blank ~7s then hero
- scroll: sections with architecture diagrams (compiler pipeline, cluster nodes) that appear to build as you scroll; frame pairs show nodes moving
- interactive: widget frames show cluster nodes changing; mobile menu opens as a list
- proof: no logos seen; benchmark numbers (3.2x, <10ms, 0%) on mobile
- mobile: diagrams become stacked boxes; readable
- grade: B, coherent engineering look, small and low-contrast text
- learn: a diagram-driven page with benchmark numbers, no logo filler
- seen-or-inferred: seen the diagrams and menu; animation of nodes inferred

### Caution (S26)

- hero: light pale-blue with circuit-line pattern, big "Secure hosting" centred. Text over pattern.
- load: white until ~4s then headline.
- scroll: light hero then a dark band "Protect workloads. Verify what runs." appears, then white "Deploy in minutes" 3-step terminals; code panes show typed output; blur/fade transitions on nav.
- interactive: FAQ accordion (widget frame); terminal panes animate text.
- proof: small logo row under hero ("Backed by Y Combinator").
- mobile: fine; terminals stack.
- grade: B, clean light/dark rhythm
- learn: alternate dark security band against light; typed terminal steps.
- seen-or-inferred: seen terminal text change; accordion seen only as closed list.

### Context.dev (S26)

- hero: light, centred headline "Give your agents the internet", large blue-bordered search box mock, dotted background.
- load: loads immediately; blue input mock typing placeholder text.
- scroll: feature cards swap to code panel in dark terminal; "Web infrastructure" dark code block section; panels reveal on scroll.
- interactive: search mock cycles (Search, Scrape...) tabs; code tab content changes.
- proof: logo row under hero, "$8M seed" line (mobile).
- mobile: well adapted, sections stacked.
- grade: B, clear product UI, restrained
- learn: a live input box as hero object.
- seen-or-inferred: seen tabs in mock; typing inferred.

### Tokenless (S26)

- hero: text-only, serif wordmark and a paragraph in a narrow left-nav memo layout, light; thin dark navy gradient strip across the top
- load: none seen
- scroll: plain scroll
- interactive: left nav links (About, Blog, Eval leaderboard, Contact); no visible change in frames
- proof: "Backed by Y Combinator" line at the foot; blog list with dates
- mobile: same single column, nav list stacked above text; fine
- grade: B, deliberate research-memo restraint, but almost no design
- learn: a plain editorial memo tone reads as credible research
- seen-or-inferred: seen the layout and plain scroll; interactivity inferred as none

### Better Auth (Sp25)

- hero: light, monochrome, dense docs-like page with a faint cube logo; headline small bottom-left.
- load: hero text fades from white (seen 9-11s); long blank start.
- scroll: headline stays pinned as an overlay while README/feature grid and code panels scroll over it (sticky); long page.
- interactive: widget frames show feature grid and infra dashboard images; no clear click change.
- proof: logos (Vercel, Databricks) under README; announcement banner.
- mobile: single column docs-like; fine but dense and faded.
- grade: B, strong concept, low contrast in places
- learn: make the page read like the product's own README or report.
- seen-or-inferred: seen sticky headline; clicks inferred.

### Bluejay (Sp25)

- hero: light/cyan with 3D clay-style illustration (mushroom trees, teal hill), headline centred, logo row bottom. Illustration.
- load: headline and illustration appear by 3-5s.
- scroll: background changes colour cyan to white to yellow to orange to pink by section; large stat numbers (10m+, 72m+, 274); characters in each section; scrolled illustration pans.
- interactive: tab pills (Customer Support, Healthcare, ...) switch card content.
- proof: logo row in hero; "648 hours saved" case study; big stats.
- mobile: stacks cleanly, illustrations stay.
- grade: A, cohesive playful 3D world, executed well
- learn: one illustrated world with colour-shifting sections; big stat numerals.
- seen-or-inferred: seen colour shifts and tab change; scrub inferred.

### Cua (Sp25)

- hero: black, 3D floating keycaps (cream, blue, orange) with headline "A shared Space for every team/agent" - word swaps. Dark, 3D render.
- load: headline appears ~4.8s; keycaps drift in.
- scroll: headline words swap; hero scrolls to logo row then light-window mock sections (Teleport etc.) shown inside dark page; sticky-ish pill nav bottom-centre.
- interactive: download button dropdown (Mac/Windows/Linux) opens (mobile menu frames); desktop widget frames show pricing.
- proof: logos (OpenAI, Meta, Microsoft, Nvidia) below hero; "Used in projects from".
- mobile: keycaps stay, pill nav at bottom; good.
- grade: A, memorable 3D hero, crisp type
- learn: one tactile 3D object on black; word-swap headline; floating pill nav.
- seen-or-inferred: seen word swap, dropdown, pill; float motion inferred.

### cubic (Sp25)

- hero: black page with spotlight beams, grey headline, white CTA, "#1 AI code reviewer" badge, dark
- load: headline fades up from dim to bright around 7s
- scroll: multi-step feature sections, each with a small diagram or UI card; at ~28-44s small node diagrams and a gauge animate
- interactive: nav hover; no tabs seen
- proof: logo row (Linux, granola, Browserbase, n8n, Resend, Daytona, Firecrawl) after hero; testimonial with photo; SOC 2 line
- mobile: stacks cleanly; logo wall tall but fine
- grade: A, restrained dark, spotlight and small diagrams
- learn: dark page with one soft light source, logos right under the hero
- seen-or-inferred: seen all; diagram animation inferred from changing frames

### Tinfoil (Sp25)

- hero: Light page with line illustration of a GPU chip, rotating headline word (Encrypted / Confidential Cloud Compute), then a dark rounded "Our products" panel rising over it; light then dark teal.
- load: Headline word cycles with fade; nav dropdown hovered.
- scroll: Stacking sections: dark panel slides over hero; product cards, Customer Stories, Industry highlights, model-pricing table, code panels, then dark "Privacy of local. Power of cloud." and diagram; mostly plain scroll with stacking.
- interactive: Nav dropdown; mobile menu opens.
- proof: Logo row (Syncopate, Berkeley, Mozilla, Harvard, DuckDuckGo), quotes, Red Hat/Meta/Canonical cards, hardware logos (Intel, NVIDIA, AMD), compliance badges.
- mobile: Good; clear menu and stacked cards. Nothing broken.
- grade: B, rich proof, clean but conventional.
- learn: Light page with a dark panel sliding over, pairing security badges with named quotes.
- seen-or-inferred: Seen the panel overlap, dropdown and menu; stacking from adjacent frames.

### Arga Labs (Sp26)

- hero: light blue-grey, headline plus large real-looking product UI (Twin Runs table) over topographic mesh.
- load: blank to ~11s in desktop (render lag), then UI visible.
- scroll: UI panel slowly changes state across many frames while page held (pinned, scripted demo); logos then appear.
- interactive: UI appears to auto-play (cursor moving, form fills); no clicks seen.
- proof: logo strip "Trusted by engineering teams" plus "Backed by" row after demo; banner on funding.
- mobile: stacked, UI scrolls; OK.
- grade: B, clean but generic SaaS blue
- learn: auto-playing UI demo held during scroll shows product depth.
- seen-or-inferred: seen cursor and state change; pin inferred from stationary frame.

### Expanse (Sp26)

- hero: cream/white left headline, right orange gradient panel that shows a terminal/dashboard changing. Orange on cream.
- load: orange slab then terminal text appears; screen swaps between image and terminal.
- scroll: sections alternate cream/orange tables ("Every workload starts with a guess"), numbered three-step cards, then dark "Built for teams" band with orange gradient.
- interactive: widget frames show accordion on dark band (items listed left, image right).
- proof: none obvious; a metric comparison table (16-H100, 97%).
- mobile: big headline wraps heavily; sections stack, works.
- grade: A, strong accent, confident hierarchy
- learn: orange gradient plus cream; a before/after metric table.
- seen-or-inferred: seen terminal text; accordion partially seen.

### Hub (Sp26)

- hero: cream, split two halves "Hub Labs" and "Hub Deploy", line-drawn lab cage and humanoid robot with green wash. Illustration, light.
- load: split page; robot drawing appears.
- scroll: halves reveal robot with green grid overlay growing; pinned sequence, then long empty cream stretch (blank frames 62-72s) before "Deployment velocity" photo grid.
- interactive: map/industries popup list in widget frames.
- proof: photo grid of real operators; no logos.
- mobile: halves stack, floating pill nav; fine.
- grade: A, distinctive technical illustration; blank gap flaw
- learn: line-art technical drawing with one green accent.
- seen-or-inferred: seen blank stretch (could be render lag); pinned inferred.

### Tasklet (Sp26)

- hero: pale green, centred headline, large chat UI mock below. Light.
- load: quick.
- scroll: chat UI plays through steps (modal, connect Gmail); logo row; section "Get your whole team using AI".
- interactive: auto-driving UI with modals.
- proof: logo strip; SOC 2; case-study card.
- mobile: good.
- grade: B, clear product demo
- learn: auto-playing UI demo in hero.
- seen-or-inferred: seen modals.

### Datacurve (W24)

- hero: serif headline "Defining intelligence" on cream, black button, light blue announcement bar
- load: none; during scroll the headline fades as a point-cloud sculpture (grainy dots) builds behind it
- scroll: scrubbed, headline fades while a dotted statue forms over ~15s of frames; on mobile a series of dotted 3D scans with a line of text each, ends on a dark footer
- interactive: mobile menu (Products, Research, Careers, Contact)
- proof: none seen; manifesto text instead
- mobile: works well; the scan sequence is the strongest part
- grade: A, serif plus point cloud feels crafted and rare
- learn: a scrubbed monochrome texture sequence signals craft without colour
- seen-or-inferred: seen the fade and dot build; scrub inferred

### Greptile (W24)

- hero: headline "The AI Code Reviewer" with a large grey line-art lizard image, green announcement bar, light
- load: nav and green CTAs appear first, headline fades in ~10s
- scroll: logo strip rises over the hero bottom; hero text slides up and clips; later a dark section with a step diagram (index codebase, swarm of agents) animating in steps
- interactive: nav hover only seen
- proof: logo wall (NVIDIA, Vanta, Brex, etc.) under hero; large quote from Brex CTO with photo; "over 20,000 teams"
- mobile: dark diagram section reads well; hero image becomes a faded background
- grade: B, strong illustration, logo wall is crowded
- learn: one pull quote with name and role after the logos
- seen-or-inferred: seen all; diagram steps motion inferred

### Gumloop (W24)

- hero: white with small colour blob icons, headline and big agent UI screenshot below. Light.
- load: slow, page appears ~19s under load.
- scroll: UI screenshot enlarges to dashboard cards; stat counter "0+" counts up to 1B+/341K+; logo grid after.
- interactive: none clear.
- proof: customer logo grid and counter stats right after hero.
- mobile: stacked, product screens for each feature; fine.
- grade: B, polished UI, plain
- learn: count-up stats beside logo grid.
- seen-or-inferred: seen 0+ then values.

### Legora (W24)

- hero: full-bleed cinematic city photo at dusk, small centred headline low in the frame, one green CTA; dark
- load: photo appears, text follows
- scroll: hero stays pinned while a video sequence plays through it, then a stacked glass-layer diagram builds one layer per step beside a sticky label list (measured pin about 2480px)
- interactive: label list expands per layer as you scroll
- proof: logo strip after the hero, firm names
- mobile: not captured, the host reset the connection
- grade: A, cinematic hero and one scrubbed diagram
- learn: a stacked diagram that builds layer by layer as you scroll explains a system without words
- seen-or-inferred: desktop seen in frames, read directly by the lead; scrub inferred from neighbouring frames

### Momentic (W24)

- hero: white, "Catch bugs before they ship", green lime CTA, input mock. Light.
- load: quick.
- scroll: logo grid with rotating quotes; text "Coding agents have made it dramatically faster" fades in word by word (highlight scrub); dark changelog band near end.
- interactive: mobile sections with numbered steps and code panes; no widget click.
- proof: stats row (test runs executed numbers), logo grid, quote cards.
- mobile: stacks, cookie banner persists.
- grade: B, tidy, lime accent
- learn: word-by-word emphasis fade, counter row.
- seen-or-inferred: seen fade-in text; scrub inferred.

### Raindrop (W24)

- hero: left-aligned headline "Detect agent issues. Prevent them from happening." on black, logos strip, dark
- load: none seen
- scroll: sticky left sidebar steps (Trace, Detect, Investigate, Simulate, Verify) with product UI on the right changing per step; then stat block 27.8% with a quote
- interactive: widget frames show the right-hand UI changing between steps
- proof: logo strip, stats row (1.1K, Billions, Fortune 100, SOC 2) right under hero, case study with quote
- mobile: stacks; steps become a block; fine
- grade: A, the pinned step sequence with real UI is clear
- learn: a sticky step list that swaps real UI panels, like an audit walkthrough
- seen-or-inferred: seen the sticky sidebar and UI swapping; scrubbing inferred

### Reducto (W24)

- hero: centred serif headline with one purple word on warm white, purple CTA, logo strip below; light, no product in the hero
- load: logos fade in as a rotating strip
- scroll: feature list of Parse, Extract, Split, Edit beside a document diagram; plain scroll with reveals, use-case tabs near the end
- interactive: FAQ accordion opens on click; use-case tabs
- proof: rotating logo strip under the hero, one quote with role, compliance question in the FAQ
- mobile: clean stacking, video card keeps its ratio
- grade: A, restrained serif with one accent
- learn: a serif headline with a single coloured word works on a technical product
- seen-or-inferred: all seen in frames, read directly by the lead

### Reform (W24)

- hero: blurred colour gradient panel with centred headline and white "Show me" button, light page
- load: blank ~2s, then hero
- scroll: hero panel gives way to white section then dark stat section; later sections alternate dark and light; sticky hamburger button appears; a card stack on the right shows product UI changing per feature
- interactive: "Show me" buttons; carousel with arrows for testimonials; FAQ accordion
- proof: logo strip under hero; stats (20M+, $500M+, 250,000+, $1M+); testimonial with photo
- mobile: works; large hamburger sticky; layout stacks cleanly
- grade: B, many colour shifts between sections
- learn: stats row on a dark band after a light hero
- seen-or-inferred: seen the section shifts and stats; sticky card sequence inferred

### Ubicloud (W24)

- hero: cream, orange CTA, isometric cloud illustration. Light.
- load: quick.
- scroll: use-case cards, services grid, testimonial slider, orange CTA band, dark footer.
- interactive: testimonial arrows.
- proof: logo strip, quote with photo.
- mobile: stacks cleanly.
- grade: B, solid, orange
- learn: orange CTA band before footer.
- seen-or-inferred: seen.

### Vibrant Labs (W24)

- No frames kept. A failed retry overwrote the recording, so this site has measurements only.

### Zep (W24)

- hero: dark landscape painting with dashboard screenshot at bottom and purple CTA. Dark.
- load: quick.
- scroll: light sections with node graphs, stat cards, analytics; painting reappears in "Built for the enterprise" and final CTA.
- interactive: none.
- proof: logo strip right under hero; S&P quote; testimonials.
- mobile: stacks fine.
- grade: A, painted landscape plus product
- learn: classical painting plus UI is a premium look.
- seen-or-inferred: seen.

### AfterQuery (W25)

- hero: headline plus a dark grainy monochrome video/animated texture with a logo mark, light cream page
- load: video texture appears within ~3s; no other entrance seen
- scroll: plain scroll with image sections; hero image scrolls away normally
- interactive: nav hover; mobile menu opens as full-screen list
- proof: "Backed by angels from" logo row (OpenAI, Meta, Google, DeepMind) directly under hero
- mobile: clean single column, menu works, nothing broken
- grade: A, calm type, strong contrast between texture and paper
- learn: one dark textured block on a quiet page gives drama without clutter
- seen-or-inferred: seen all above; video motion inferred from changing noise between frames

### Browser Use (W25)

- hero: large two-tone headline (white/grey) on black, orange CTA, logo strip beneath, dark
- load: none beyond a quick fade-in
- scroll: plain scroll with chart and stat sections; footer is a dense link matrix
- interactive: widget frames show no obvious change; nav hover only
- proof: logo strip under hero; stats ($0.02/hour, 90.5%, 119,000 stars); benchmark chart
- mobile: single column, orange accent holds; cookie bar overlaps the bottom
- grade: A, black with one orange accent, tight type
- learn: one accent colour on black plus real benchmark numbers feels credible
- seen-or-inferred: seen all above; interactivity inferred as minimal

### Confident AI (W25)

- hero: Centred dark headline "Ship better AI as a team. Not as individuals." with CTAs, then a large product dashboard screenshot and floating coloured annotation chips, dark with purple announcement bar.
- load: Fade-in; floating chips drift around the mock.
- scroll: Sticky nav; dashboard mock scales/rises under hero; later full-section product demos with sticky text (mobile shows stacked feature cards).
- interactive: Mobile menu opens; FAQ list and "APIs for the entire pipeline" tabbed code panel seen.
- proof: Logo wall ("Trusted by 500+ leading AI companies": Panasonic, Samsung, Amdocs, BCG), customer quotes with photos, uptime and compliance lines.
- mobile: Good; menu works, logo grid and quote cards stack. Bar text tiny.
- grade: A, dense, polished, real product UI throughout.
- learn: Pair a logo wall with named quotes plus a compliance strip directly after the hero.
- seen-or-inferred: Seen hero, menu, logos, quotes, FAQ; sticky behaviour inferred.

### HUD (W25)

- hero: Centred headline over a full-bleed photo of a mossy cliff island in fog, with three live-ticking counters (task runs, environments built, inference calls) at the base; light/misty photo, black text, black CTA pill.
- load: Blank beyond 8s (load-heavy); headline and counters fade in after.
- scroll: Pinned hero; page gradually darkens as the photo recedes into a dark section (mobile: photo scrolls under dark panels). Counters keep ticking while pinned.
- interactive: Nav hover only. Mobile FAQ accordion visible. No clicks captured.
- proof: Counters in hero; product mock "Turn tasks into revenue" with earnings chart; footer only.
- mobile: Stacks cleanly; dark footer; photo hero kept. Nothing broken.
- grade: B, strong photo and live counters, thin proof.
- learn: Live ticking stat counters in the hero make claims feel measured, not asserted.
- seen-or-inferred: Seen counters changing, light-to-dark transition, FAQ. Pinning inferred from stationary hero across 30s of frames.

### Mastra (W25)

- hero: left headline on black with a soft, blurred product panel to the right that resolves; dark, one orange announcement bar
- load: panels fade from blur
- scroll: tabbed product sections (Agents, Workflow, Harness, Memory) with pinned panels (measured pin about 3906px), logo rows, customer cards
- interactive: tabs swap product panels
- proof: two logo rows directly under the hero, customer story cards with photos
- mobile: stacks, heavy use of blur during reveal
- grade: A, dense but controlled dark
- learn: blur reveals look expensive when overused; keep them short
- seen-or-inferred: all seen in frames, read directly by the lead

### Onlook (W25)

- hero: black, centred headline, small white button, large app screenshot (design editor) rising from bottom. Dark.
- load: headline fades in slowly (4-12s).
- scroll: screenshot grows/rises into view; cookie banner bottom; features in 2x2 icons; testimonial wall; FAQ.
- interactive: FAQ accordion; widget frames show screenshot detail.
- proof: "27,064 builders" and tweet-style quotes wall.
- mobile: stacks, cookie banner large.
- grade: B, strong product shot, dim
- learn: product screenshot rising from the fold under a dark headline.
- seen-or-inferred: seen rise; accordion closed only.

### Osmosis (W25)

- hero: Full-bleed dark ink-wash mountain image, blue/purple tinted, serif centred headline "Forward Deployed Reinforcement Learning", small CTA; dark with a tick-mark ruler motif at top and bottom.
- load: Fade-in of image and text by 1.5s.
- scroll: Pinned scroll-scrubbed feature section: left tab list (Hands on Deployments, Reinforcement Fine-Tuning, Continuous Improvement) cycles on right 3D glass lens, then isometric cube illustrations per use case; footer lifts in.
- interactive: Scroll-driven tabs with progress bar; no clicks.
- proof: None seen apart from footer legal links.
- mobile: Same sequence, large wordmark, works well; no breakage.
- grade: A, cohesive art direction, scrubbed 3D visuals.
- learn: Scroll-scrubbed list with a thin progress line and one 3D object per step feels like an instrument.
- seen-or-inferred: Seen the content swaps while hero fades; scrubbing inferred from the frame cadence.

### Roark (W25)

- hero: pale grey-green with dark-green headline, circular radar animation right. Light.
- load: white until ~9s then text.
- scroll: logo row; "One loop. Always improving." cards with small UI; then "Teams ship faster" quotes; green dark footer.
- interactive: radar widget cycles labels; no click.
- proof: logo row (AT&T, Google, Podium).
- mobile: stacks; large feature lists.
- grade: B, consistent green
- learn: single-colour green scheme.
- seen-or-inferred: seen radar change.

### 21st (W26)

- hero: centred headline over deep-blue fluid 3D-ish gradient, below it a real product UI mock (dark app window with chrome-like object). Dark.
- load: product mock fades up under headline; numerals 1,2,3 behind.
- scroll: headline stays pinned/fading while the big UI panel scrolls up (stacking/overlap); long scroll, ~110s.
- interactive: pointer moves over mock; copy-prompt button flips to "Copied" in mobile frames. Widget frames show a gallery of thumbnails.
- proof: none clearly seen.
- mobile: same hero stacked, UI mock below, works.
- grade: B, strong product-as-hero, loud blue gradient
- learn: let a real product panel overlap the headline as you scroll.
- seen-or-inferred: seen overlap and Copied state; scrub inferred.

### Luel (W26)

- hero: white with blue misty mountain illustration right, "The Frontier of Data" in thin type. Light.
- load: white until ~5s then headline.
- scroll: very short page; mountains shift slightly.
- interactive: mobile menu opens full-screen list.
- proof: none.
- mobile: mountains below text; cookie banner overlaps.
- grade: B, elegant but thin
- learn: nothing beyond one misty landscape.
- seen-or-inferred: seen all.

### Polymath (W26)

- hero: tiny headline, blue-line technical illustration (stacked panels with an arrow) on cream, light
- load: illustration draws in from a single panel to a full stack over ~4s
- scroll: illustration stays near the top and fades as text scrolls over it; footer has a faint globe
- interactive: none seen
- proof: one line naming backers (BaseIO, Cervin, YC) in the text
- mobile: same layout, larger logo; fine
- grade: A, restrained and distinct, the draw-in feels precise
- learn: a line-drawing that builds on load is a cheap way to look precise
- seen-or-inferred: seen the draw-in; no interactivity found
