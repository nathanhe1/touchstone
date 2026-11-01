---
name: Touchstone
description: Independent audit and appraisal for AI training material, shown through recorded engine runs on a dark-to-light seam.
colors:
  gold: "#dcae4a"
  gold-2: "#e9c26c"
  gold-deep: "#80600f"
  bad: "#b4341f"
  good: "#27704a"
  bad-on-ink: "#f08370"
  good-on-ink: "#71cc97"
  ink: "#121211"
  ink-2: "#1c1c1a"
  ink-line: "#31312d"
  on-ink: "#f3f2ed"
  on-ink-2: "#aeada5"
  paper: "#f7f6f3"
  paper-2: "#efeee9"
  paper-line: "#dcdad2"
  panel-paper: "#fbfaf8"
  field: "#ffffff"
  text: "#171715"
  text-2: "#5a5952"
  text-hover: "#3a3a36"
typography:
  display:
    fontFamily: "STIX Two Text Variable, STIX Two Text, Georgia, serif"
    fontSize: "clamp(44px, 5.6vw, 80px)"
    fontWeight: 500
    lineHeight: 1.04
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "STIX Two Text Variable, STIX Two Text, Georgia, serif"
    fontSize: "clamp(32px, 3.4vw, 48px)"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-0.025em"
  figure:
    fontFamily: "STIX Two Text Variable, STIX Two Text, Georgia, serif"
    fontSize: "48px"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "-0.02em"
  title:
    fontFamily: "STIX Two Text Variable, STIX Two Text, Georgia, serif"
    fontSize: "28px"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  lede:
    fontFamily: "Geist Variable, Geist, -apple-system, Helvetica Neue, sans-serif"
    fontSize: "20px"
    fontWeight: 400
    lineHeight: 1.5
  body:
    fontFamily: "Geist Variable, Geist, -apple-system, Helvetica Neue, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Geist Variable, Geist, -apple-system, Helvetica Neue, sans-serif"
    fontSize: "14px"
    fontWeight: 500
  data:
    fontFamily: "Geist Mono Variable, Geist Mono, ui-monospace, Menlo, monospace"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  data-small:
    fontFamily: "Geist Mono Variable, Geist Mono, ui-monospace, Menlo, monospace"
    fontSize: "12px"
    fontWeight: 400
rounded:
  fine: "2px"
  base: "4px"
spacing:
  micro: "4px"
  xs: "8px"
  sm: "16px"
  md: "24px"
  lg: "32px"
  xl: "48px"
  2xl: "64px"
  3xl: "96px"
components:
  button-primary:
    backgroundColor: "{colors.text}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.base}"
    padding: "0 20px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.text-hover}"
  button-primary-on-ink:
    backgroundColor: "{colors.gold}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.base}"
    padding: "0 20px"
    height: "44px"
  button-primary-on-ink-hover:
    backgroundColor: "{colors.gold-2}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    typography: "{typography.label}"
    rounded: "{rounded.base}"
    padding: "0 20px"
    height: "44px"
  button-nav:
    backgroundColor: "{colors.gold}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.base}"
    padding: "0 14px"
    height: "36px"
  nav-link:
    textColor: "{colors.on-ink-2}"
  nav-link-active:
    textColor: "{colors.on-ink}"
  console:
    backgroundColor: "{colors.ink-2}"
    textColor: "{colors.on-ink}"
    typography: "{typography.data}"
    rounded: "{rounded.base}"
  console-tab:
    textColor: "{colors.on-ink-2}"
    typography: "{typography.label}"
    padding: "0 16px"
    height: "48px"
  console-tab-selected:
    textColor: "{colors.on-ink}"
  rating-cell:
    rounded: "{rounded.fine}"
    typography: "{typography.label}"
    width: "28px"
    height: "32px"
  rating-cell-pass:
    backgroundColor: "{colors.gold}"
    textColor: "{colors.ink}"
  panel:
    backgroundColor: "{colors.panel-paper}"
    textColor: "{colors.text}"
    rounded: "{rounded.base}"
  field:
    backgroundColor: "{colors.field}"
    textColor: "{colors.text}"
    rounded: "{rounded.base}"
    padding: "8px 12px"
---

# Design System: Touchstone

## Overview

**Creative North Star: "The Recorded Run"**

The console is the product demonstrated. Real recorded engine runs sit across the seam between one dark hero and a light body, and everything around them is plain enough to let the run be the only spectacle. The world is a ledger with an instrument laid on it: near-black at the head and foot of every page, off-white in between, hairline rules, tight corners, one gold accent.

The page tells one story in order: what it is, proof with scope, why it matters in one chart, how it works as four steps of one run, next step. Density is calm and typographic. Content sits on rules rather than in boxes, a serif states the claims and the large figures, Geist carries everything you read or operate, and Geist Mono holds what the engine actually printed. Motion is rich but tied to the run: lines resolve, a verdict lands, a curve draws, a step lights the matching console row.

Conventions were checked against the study of YC sites in [YC site analysis](reports/YC%20site%20analysis.md); go there for the counts. The report separates measured facts from judgement. Read it as evidence, not as a specification: its adoption tables describe the preview before this redesign, and the choices it does not measure (STIX Two Text, the gold, the 80px headline above the median) are judgement calls.

**Key Characteristics:**
- Near-black hero, nav, closing call and footer; off-white body; the seam between them is where the product sits.
- One gold accent; red and green carry outcomes, never decoration.
- Hairline rules, 4px corners, no shadows, no visible gradients, no card grids.
- STIX Two Text for claims and figures, Geist for reading and operating, Geist Mono for engine output.
- Motion is Motion plus short CSS state transitions, and every sequence has a finished reduced-motion state.

## Colors

Two neutral grounds, warm rather than pure, with a single gold and two outcome colours that only ever report something.

### Primary
- **Streak Gold** (`gold`): the accent on dark grounds. Primary buttons on ink, the console's selected-tab rule, the passing grade cell, text selection, the streak in the brand mark. Always carries ink text (9.1:1).
- **Lit Gold** (`gold-2`): hover state of gold buttons only.
- **Deep Gold** (`gold-deep`): the same accent where the ground is light, because Streak Gold measures 1.9:1 on paper. Links' underline and hover, focus rings, selected demo options, positive estimated values, the Cuts-the-price ledger state (5.4:1 on paper).

### Tertiary
- **Fail Red** (`bad`, `bad-on-ink`): blocked checks, failing grades, the accuracy line and its points in the chart, form validation. The lighter value is for ink grounds.
- **Pass Green** (`good`, `good-on-ink`): positive net gain, clean flags, completed stages, the engine-online dot. The lighter value is for ink grounds.

### Neutral
- **Stone Ink** (`ink`): hero, nav, page heads, closing call, footer; also the `html` ground behind overscroll.
- **Raised Ink** (`ink-2`): the console surface and the demo log, one step above Stone Ink.
- **Ink Hairline** (`ink-line`): every rule and border on dark grounds.
- **Bone** (`on-ink`): headings and primary text on dark.
- **Worn Bone** (`on-ink-2`): ledes, nav links and console keys on dark (8.3:1 on ink, 7.6:1 on the console).
- **Assay Paper** (`paper`): the body ground.
- **Shaded Paper** (`paper-2`): drop-zone hover, skeleton bars, empty tracks.
- **Paper Hairline** (`paper-line`): every rule and border on light grounds.
- **Report Paper** (`panel-paper`): the live demo's report panel. **Field White** (`field`): form inputs only.
- **Text Ink** (`text`): body text and the primary button on light grounds; **`text-hover`** is that button's hover.
- **Muted Text** (`text-2`): supporting copy on light grounds (6.5:1 on paper).

### Named Rules
**The One Accent Rule.** Gold is the only accent. Streak Gold on dark, Deep Gold on light, and no third hue enters to decorate.

**The Outcome Colour Rule.** Red and green report an outcome: a check, a result, a stage, a field that failed. They are never decoration and never a button.

**The Neutral Reward Rule.** The reward curve stays a neutral grey. It is what a seller shows you, so it never takes gold, red or green; only accuracy on new problems takes red.

**The Passing Cell Rule.** The grade scale fills A and B with gold and C, D and F with red. A grade is a Touchstone statement, so a passing cell is gold even though a passing number is green.

## Typography

**Display Font:** STIX Two Text Variable (with Georgia)
**Body Font:** Geist Variable (with -apple-system, Helvetica Neue)
**Label/Mono Font:** Geist Mono Variable (with ui-monospace, Menlo)

**Character:** A scholarly text serif at weight 500 with tight tracking, reading like a published finding, against a neutral grotesk and a monospace that is plainly machine output.

The scale is seven steps: 12, 14, 17, 20, 28, 48, 80. Headings balance their wrap.

### Hierarchy
- **Display** (`display`): every page's h1 and the closing call. Reaches 80px from about 1430px wide; holds one line on desktop and wraps on phones.
- **Headline** (`headline`): section h2s, set in sentence case and ending with a period.
- **Figure** (`figure`): proof figures on Home and market figures on Company.
- **Title** (`title`): step h3s, tier prices, verdict values, the request confirmation, legal subheads.
- **Lede** (`lede`): page ledes and closing text, muted, max 58ch; drops to 17px at 720px. Long-form prose uses the same size at 64ch.
- **Body** (`body`): running text.
- **Label** (`label`): buttons, nav, console tabs, form labels, scope lines (the last two at weight 400 where they read as text).
- **Data** (`data`, `data-small`): console logs, chart axes, step outputs at 14px; table heads and small data labels at 12px.

### Named Rules
**The Mono Is Output Rule.** Geist Mono holds what the engine prints or what a machine reads: log lines, axes, probe samples, table heads, figures in the small data labels. Console tabs and the verdict stay in Geist, because a person wrote them.

**The Serif States Rule.** STIX Two Text sets headings, large figures and prices. It never sets controls, tables' body text or running copy.

## Layout

Content sits in a 1200px container with 24px gutters (20px at 720px and below) that respect safe-area insets. Page structure is a 12-column grid with a 24px column gap. Vertical rhythm comes from the space scale: 4 as a micro step inside tight rows, then 8, 16, 24, 32, 48, 64, 96. Sections are 96px bands (64px at 720px) divided by a full-bleed hairline.

The seam is the signature layout. The hero's bottom padding runs 48px past its CTAs and then the console's negative top margin pulls it 216px up into the dark, so the console always starts 48px below the actions and straddles the dark-to-light edge; at 720px the same 48px holds with a 72px overlap. Hero headline, then a row with the lede on columns 1 to 7 and two CTAs right-aligned on columns 9 to 12. Proof follows at once in three columns.

Two recurring splits: a section head (headline on 1 to 7, note on 9 to 12, bottom-aligned) above one wide object, and a sticky left column beside a list (4 columns and 7 on subpages, 5 and 6 on Home's How section), sticky at 112px.

At 960px every split stacks and stickies release; Home's mini console disappears and each step shows its output as a mono line instead. At 720px the nav collapses, console tabs go two by two, log rows and the verdict stack, proof goes to one column and ledger tables become stacked rows. Below 380px the nav button hides and the menu button remains.

## Elevation & Depth

The system is flat with no shadow vocabulary. Depth is the step from `ink` to `ink-2`, the step from dark ground to light, and 1px hairlines. The only thing that reads as lifted is the console, and it earns that by crossing the seam rather than by casting anything.

### Named Rules
**The Seam Is The Depth Rule.** Nothing casts a shadow at rest or on hover. If an object needs presence, it crosses a ground change or takes a hairline.

## Shapes

Tight, ruled and nearly square. One radius (`base`) on buttons, the console, the panel, fields and the drop zone; `fine` only on small parts such as grade cells, skeleton bars and focus rings. Circles belong to status dots and data points. Rules are 1px and solid; the drop zone's dashed border is the one exception, because it marks an open target. Chart curves are 3px round-capped strokes, and a value measured only at two points is drawn as two points and a dotted join, never as a curve.

Drawn marks are functional only: the brand stone with its gold streak, the two-bar menu, the plus that rotates to a close on questions, and status dots.

## Components

### Buttons
Quiet, squared and flat; colour flips with the ground.
- **Shape:** gently squared (`base`), 44px tall, 36px in the nav, labels only.
- **Primary:** Text Ink on light grounds, Streak Gold on dark.
- **Hover / Focus:** background colour change over 150ms, no lift or movement. Focus is a 2px accent outline at 2px offset.
- **Ghost:** transparent with a hairline border and the ground's text colour; the border takes full text colour on hover.
- **Text link:** weight 500 with an accent underline at 4px offset; the text takes the accent on hover.

### Grade Scale
Always the full A to F row, never a lone letter: 28 by 32px cells with a hairline border and a 4px gap, the earned cell filled per the Passing Cell Rule.

### Ledger
The system's table and its main content form on subpages: a 12px mono head, then rows separated by hairlines with no fills or stripes, first column at weight 500. Prices right-align in the title style. Results lists, sources, questions and demo options share the same top-rule rhythm.

### Inputs / Fields
- **Style:** 1px border in the muted text colour on Field White, `base` radius, 16px text so phones do not zoom on focus.
- **Focus:** 2px accent outline with the border matching.
- **Error / Disabled:** red border and a 14px red message below the field; a sending submit drops to 70% opacity with an inline spinner.

### Navigation
Sticky 64px dark bar with a bottom hairline on every page: brand mark and wordmark, links right-aligned in 14px, then the gold nav button. Current page and hover move from Worn Bone to Bone over 150ms. At 720px links drop into an ink panel under a 36px bordered menu button.

### Console (signature)
A `ink-2` figure with a 1px hairline: four tabs, a log on 7 parts and a verdict on 5 parts, and a 12px caption that states the run's provenance. It plays real recorded runs, read from the file the live demo replays. Each line takes two 260ms beats: the key appears with "running" beside it, then the value resolves. After the last line the grade and finding land, a gold rule drains under the selected tab for 3.4s, and the next tab starts. Hover or focus pauses it, picking a tab holds it there, and arrow keys move between tabs. Under reduced motion it shows the finished run and never advances.

The mini console on Home's How section is the same object, one run in four rows, lit as each step reaches the middle of the viewport.

### Run Chart (signature)
One chart: solid hairline grid, mono axes, reward drawn over 1.2s and accuracy as two red points with a dotted join; the gap bracket fades in after the draw. A hover cursor reads reward alone, because that is all that was logged, and end labels sit directly on the lines with no legend.

### Demo Panel
The live demo's report: a bordered `panel` with a 13px mono head, a 2px progress line, stage dots, and an inset `ink-2` log, so the dark engine output carries onto the light page.

## Do's and Don'ts

### Do:
- **Do** put recorded engine output in the first viewport and state its provenance in a caption.
- **Do** open with a dark head and return to dark for the closing call and footer.
- **Do** place each proof figure with its scope directly beneath it.
- **Do** separate with 1px hairlines in `ink-line` or `paper-line`.
- **Do** use Deep Gold, not Streak Gold, for any accent on a light ground.
- **Do** keep state transitions at 150ms, use Motion as the only animation library, and give every sequence a finished reduced-motion state.
- **Do** say "training material" in visual examples and captions.

### Don't:
- **Don't** add shadows, including on hover.
- **Don't** use a visible gradient, gradient text or glow. A solid-colour CSS background used to draw a hairline mark is fine.
- **Don't** use card grids or box content that a rule can separate; the console and the demo panel are the only bordered surfaces.
- **Don't** add decorative icons, feature icons or arrows on buttons; functional marks are listed under Shapes.
- **Don't** put a kicker or eyebrow label above a heading or title.
- **Don't** use red or green for anything that is not an outcome.
- **Don't** lift, scale or translate controls on hover.
- **Don't** set prose or navigation in Geist Mono, or controls in STIX Two Text.
- **Don't** use a radius above `base` or a pill shape.
- **Don't** show a console or chart run that the engine did not record.
