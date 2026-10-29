---
name: Touchstone
description: Independent appraisal for AI training data, drawn as a training run in black, gold and silver.
colors:
  transfer-gold: "#e2b45a"
  gold-hover: "#eec982"
  reward-silver: "#b9bfc8"
  exploit-red: "#ff6b5b"
  pass-green: "#45d483"
  ground: "#0b0d10"
  panel: "#111418"
  panel-raised: "#161a1f"
  line: "#22272e"
  line-strong: "#2e343c"
  ink: "#eef0f3"
  ink-muted: "#a9b0b9"
  ink-faint: "#7f8792"
typography:
  display:
    fontFamily: "Bodoni Moda Variable, Bodoni 72, Didot, Georgia, serif"
    fontSize: "clamp(44px, 5.2vw, 76px)"
    fontWeight: 560
    lineHeight: 1
    letterSpacing: "-0.012em"
  headline:
    fontFamily: "Bodoni Moda Variable, Bodoni 72, Didot, Georgia, serif"
    fontSize: "clamp(34px, 4.4vw, 60px)"
    fontWeight: 560
    lineHeight: 1.02
    letterSpacing: "-0.012em"
  figure:
    fontFamily: "Bodoni Moda Variable, Bodoni 72, Didot, Georgia, serif"
    fontSize: "clamp(64px, 9vw, 136px)"
    fontWeight: 600
    lineHeight: 0.95
    letterSpacing: "-0.045em"
  title:
    fontFamily: "Geist Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Geist Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.6
    fontFeature: "\"ss01\", \"cv11\""
  lede:
    fontFamily: "Geist Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(18px, 1.5vw, 20px)"
    fontWeight: 400
    lineHeight: 1.55
  data:
    fontFamily: "Geist Mono Variable, ui-monospace, Menlo, monospace"
    fontSize: "12px"
    fontWeight: 500
    letterSpacing: "-0.01em"
    fontFeature: "\"tnum\""
rounded:
  track: "4px"
  control: "8px"
  button: "10px"
  segment: "12px"
  panel: "14px"
  tile: "18px"
spacing:
  gutter: "20px"
  stack: "12px"
  panel-pad: "20px"
  block: "28px"
  head-gap: "48px"
  section: "clamp(96px, 12vw, 160px)"
components:
  button-primary:
    backgroundColor: "{colors.transfer-gold}"
    textColor: "{colors.ground}"
    rounded: "{rounded.button}"
    padding: "0 20px"
    height: "48px"
  button-primary-hover:
    backgroundColor: "{colors.gold-hover}"
    textColor: "{colors.ground}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "0 20px"
    height: "48px"
  button-nav:
    backgroundColor: "{colors.transfer-gold}"
    textColor: "{colors.ground}"
    rounded: "{rounded.control}"
    padding: "0 14px"
    height: "38px"
  panel:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.panel}"
  panel-head:
    textColor: "{colors.ink-faint}"
    typography: "{typography.data}"
    padding: "0 16px"
    height: "44px"
  nav-link:
    textColor: "{colors.ink-muted}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  nav-link-active:
    backgroundColor: "{colors.panel-raised}"
    textColor: "{colors.ink}"
  tab:
    textColor: "{colors.ink-faint}"
    rounded: "{rounded.control}"
    padding: "0 12px"
    height: "34px"
  tab-selected:
    textColor: "{colors.ink}"
  segment-selected:
    backgroundColor: "{colors.transfer-gold}"
    textColor: "{colors.ground}"
    rounded: "{rounded.control}"
    height: "38px"
  grade-tile:
    rounded: "{rounded.tile}"
    size: "72px"
---

# Design System: Touchstone

## Overview

**Creative North Star: "The Assay Run"**

The site is a training run on a black bench. Reward climbs, transfer stays flat, and Touchstone is the eval that tells you which one you bought. The grammar is an experiment dashboard: graphite panels on a near-black ground, hairline borders, run headers carrying ids, step counts and sha prefixes, curves that draw as you watch. Over that sits the touchstone itself: the dark stone, the streak of gold drawn across it. Gold is the true number and the brand; silver is the tempting one.

Density is dashboard-calm: generous section spacing around tightly packed panels. Words are set plainly in Geist; headlines and big figures speak in Bodoni Moda, with the turn of a sentence picked out in gold italic ("Don't buy training data *blind.*"). Motion is rich but always explanatory: curves draw, numbers count up, the ranking re-sorts, the model spheres spring.

It refuses the dark-SaaS hero with a glowing product screenshot. Evidence is drawn as live charts, not mocked as screenshots.

**Key Characteristics:**
- Black ground, graphite panels, 1px hairlines; depth comes from tone, not shadow.
- Gold means transfer and Touchstone; silver means training reward; red means exploit or loss; green means pass or gain.
- Bodoni Moda for headlines and big figures, gold italic for the accent phrase; Geist for UI and body; Geist Mono for data only.
- Every chart and panel carries a run header and a "demo data" marker.
- Motion explains the number: draw, count, re-rank, spring.

## Colors

A near-monochrome graphite field where colour is reserved for meaning, led by a single warm gold.

### Primary
- **Touchstone Gold** (`transfer-gold`): transfer, the true number. Also Touchstone's own colour: the primary button, the selected segment, focus rings, text selection, the progress and timeline fills, the "us" marker on the market map, the brand mark's streak, and the italic accent words in headlines. Gold surfaces always carry ground-black text (10.1:1).
- **Lit Gold** (`gold-hover`): hover state of gold buttons only.

### Secondary
- **Reward Silver** (`reward-silver`): training reward, the tempting number. Reward curves, reward columns and reward readouts. Never used for Touchstone's own voice or actions.

### Tertiary
- **Exploit Red** (`exploit-red`): reward exploits, negative change, "don't buy" verdicts, failing grades.
- **Pass Green** (`pass-green`): positive change, passing grades, sealed and verified checks.

### Neutral
- **Bench Black** (`ground`): the page ground and the text colour on any gold surface.
- **Graphite** (`panel`): panel fill, running to #0f1215 at the bottom of each panel.
- **Raised Graphite** (`panel-raised`): active nav pill, vault rows, the glass verdict tint.
- **Hairline** (`line`): every panel border, divider, table rule and grid line.
- **Strong Hairline** (`line-strong`): secondary-button stroke, slider track, inactive timeline node.
- **Ink** (`ink`): headlines and primary text.
- **Muted Ink** (`ink-muted`): body copy under headlines, ledes, nav links, legends.
- **Faint Ink** (`ink-faint`): axes, panel meta, captions, footnotes. It measures 5.4:1 on ground, 5.1:1 on panel and 4.8:1 on raised panels, so it passes AA for small text.

Translucent tints are derived from these hexes by alpha, never new hues: gold at 12–20% for selected rows, tab pills and halos; red and green at 10–12% for grade tiles; white at 3–5% for hover rows and empty tracks.

### Named Rules
**The Two Numbers Rule.** Silver is reward, gold is transfer, in every chart, legend, readout and figure. Never swap them, and never use silver for something Touchstone recommends.

**The Verdict Colour Rule.** Red and green appear only as judgements on data: loss or exploit, gain or pass. Never as decoration or as button colours.

**The Gold Is Ours Rule.** Gold marks Touchstone's own voice: its actions, its verdict accent, its position. If gold appears, it means "the real number" or "us".

## Typography

**Display Font:** Bodoni Moda Variable (with Bodoni 72, Didot, Georgia), optical sizing on
**Body Font:** Geist Variable (with Helvetica Neue, Arial), stylistic sets ss01 and cv11
**Label/Mono Font:** Geist Mono Variable (with ui-monospace, Menlo), tabular numerals

**Character:** A high-contrast Didone for the claims and the large numbers, against a neutral grotesk for everything you operate and a monospace that only ever holds measurements. It reads as an assay certificate set over an instrument panel.

### Hierarchy
- **Display** (Bodoni Moda 560, clamp(44px, 5.2vw, 76px), line-height 1): the home hero headline. Page headers run slightly larger (clamp(44px, 5.6vw, 80px)) with a 16ch measure.
- **Headline** (Bodoni Moda 560, clamp(34px, 4.4vw, 60px), 1.02): section headlines, balanced wrap. The closing section uses clamp(44px, 6vw, 88px).
- **Figure** (Bodoni Moda 600, clamp(64px, 9vw, 136px), 0.95, -0.045em): hero statistics on the market and forecast pages. Column figures use clamp(40px, 4.4vw, 60px).
- **Title** (Geist 600, 22px, 1.25, -0.02em): step titles, card titles, environment names.
- **Body** (Geist 400, 17px, 1.6): running text. Ledes are 18–20px in muted ink, max 58ch; section-head notes 18px, max 46ch.
- **Data** (Geist Mono 500, 11–13px for labels and axes, 15–22px for readouts, tabular numerals): panel headers, axis text, run ids, step counts, legends, table headers, metric values.

Headlines are short, plain and end with a period. The four that set the voice: "Don't buy training data blind.", "Training data is expensive. Finding out it didn't work is worse.", "Small experiments, before the big spend.", "Know before you train."

### Named Rules
**The Gold Italic Rule.** A headline may pick out its turn (the final word or second sentence) in Bodoni italic at weight 500, in Touchstone Gold. One accent per headline, never in body text, never in Geist.

**The Mono Is Data Rule.** Geist Mono holds only measurements and machine identifiers: numbers, axes, ids, hashes, step counts, panel meta. Words a person reads as prose or navigation stay in Geist.

**The Bodoni Speaks Rule.** Bodoni Moda sets h1, h2 and big figures, nothing smaller. Titles, buttons, tables and UI stay in Geist.

## Layout

Content sits in a 1200px container with 20px side gutters that respect safe-area insets. Sections breathe at clamp(96px, 12vw, 160px) vertically; consecutive sections drop their top padding ("flush") so the rhythm stays even. A section opens with a two-column head (headline at 1.1fr, a short note at 0.9fr, bottom-aligned, 48px gap) and then one wide panel.

The hero is two equal columns: headline, lede, two buttons and two check-marked assurances on the left; the run panel on the right, at least min(760px, 100svh − 68px) tall. The how-it-works story is a sticky stage (1.15fr) beside scroll-driven steps (0.85fr), each step 60vh tall, with inactive steps at 28% opacity.

Panels pack tightly inside: 20px body padding, 44px headers, internal columns divided by hairlines rather than gaps. Stat rows and plan grids sit edge to edge, split by 1px rules.

Breakpoints: at 900px every two-column grid stacks, the sticky stage moves above its steps, internal column rules turn horizontal, and the nav collapses to a menu. At 560px the run chart shortens to 240px and the floating glass verdict gives way to an inline sentence.

## Elevation & Depth

The system is flat and tonal. Depth comes from the ground-to-graphite step, a top-to-bottom panel gradient (panel to #0f1215) and 1px hairlines. Shadows appear only as warm gold light or on the few objects that float: the primary button, the glass verdict, the model spheres and gold markers.

### Shadow Vocabulary
- **Gold lift** (`box-shadow: 0 1px 0 #ffffff40 inset, 0 8px 24px -8px #e2b45a80`): primary button at rest; on hover it grows to `0 14px 32px -10px #e2b45aaa`.
- **Glass float** (`box-shadow: 0 20px 40px -12px #000a`): the verdict chip over the run chart.
- **Gold halo** (`box-shadow: 0 0 0 7px #e2b45a26, 0 0 28px #e2b45aaa`): Touchstone's dot on the market map; the current timeline node uses a 6px ring of the same tint.
- **Sphere light** (`box-shadow: inset -10px -14px 26px #0b0d1066, 0 26px 44px -16px #e2b45a88`): the gold model spheres.

### Named Rules
**The Hairline First Rule.** Separate with a 1px line in `line` before reaching for a shadow. A neutral drop shadow on a resting panel is wrong; light in this world is gold.

**The Breathing Ground Rule.** The animated shader gradient (gold through black) sits only behind the hero (40% opacity) and the closing call (60%), fully masked toward the text, and never mounts with reduced motion.

## Shapes

Softly squared instrument hardware. Radii step with size: 4px for bar tracks, 8px for nav pills, tabs, chips and the compact nav button, 10px for buttons and vault rows, 12px for segmented controls and the price tag, 14px for panels and the glass verdict, 18px for grade tiles. Circles are reserved for data points, timeline nodes, slider thumbs and the model spheres. Curves are 3px round-capped strokes; chart grid lines are dashed (2 4) hairlines.

## Components

### Buttons
Gold, solid and lit from above; the one warm object on the page.
- **Shape:** gently squared (10px), 48px tall; 38px tall and 8px radius in the nav.
- **Primary:** Touchstone Gold with ground-black text, Geist 600 15px, 0 20px padding, trailing arrow icon, gold lift shadow. "Request an appraisal" is the only primary action.
- **Hover / Focus:** lightens to Lit Gold, rises 1px, the glow deepens and the arrow slides 3px right; presses to 0.98 scale. Focus is a 2px gold outline at 3px offset.
- **Secondary:** transparent with an inset strong-hairline stroke and ink text; hover adds a 3% white wash and a faint-ink stroke.
- **Text link:** ink text with a strong-hairline underline at 5px offset that turns gold on hover.

### Chips and Tags
- **Grade tile:** 72px square, 18px radius, Geist 600 40px letter; green or red at about 12% fill with a 1px inset ring of the same hue, or a 5% white neutral. In tables it shrinks to a 28px chip at 8px radius.
- **Fair-value tag:** solid gold, 12px radius, ground-black text, springs in with a slight rotation.

### Cards / Containers
- **Corner Style:** 14px.
- **Background:** graphite gradient (panel to #0f1215).
- **Shadow Strategy:** none; see Elevation & Depth.
- **Border:** 1px hairline.
- **Internal Padding:** 20px; report sides and calculators 28–32px.
- **Run header:** every panel opens with a 44px mono header: a title such as "run · env name" or "certificate · env name" in muted ink, and meta such as "demo data" or a sealed hash pushed right in faint ink.
- **Featured plan:** border tinted gold (#e2b45a55) and a warm graphite gradient (#1a170f to #0f1215).

### Inputs / Fields
- **Range slider:** 4px track filled gold up to the value over a strong-hairline remainder; 20px ink thumb with a 5px gold halo.
- **Field label:** muted ink label with the live value in mono ink, right-aligned on the same line.

### Navigation
- **Style:** sticky 68px bar, ground at 82% opacity with 16px backdrop blur; gains a hairline bottom border after 8px of scroll. Brand mark (the stone and its gold streak) and lowercase "touchstone" wordmark at left.
- **Links:** Geist 14px muted ink; the active page carries a raised-graphite pill that glides between links on a spring (stiffness 380, damping 32).
- **Mobile:** below 900px the links drop into a full-width panel under a 40px menu button and the nav button hides.

### Tabs and Segmented Control
- **Tabs:** 34px Geist 13px in faint ink; the selected tab gets a sliding pill of gold at 12% with a 1px gold-40% inset ring.
- **Segmented control:** graphite well with a hairline border (12px radius); the selected segment is a solid gold pill with black text that slides on selection.

### Run Chart (signature)
Silver reward curve and gold transfer curve drawn over 2.6s on dashed grid lines, mono axes, end labels in matching colours, a three-cell mono readout (step, reward, new problems) that counts in sync, and a legend of 14 × 2px swatches.

### Liquid-Glass Verdict (signature)
After the curves finish drawing, a refractive glass chip springs onto the gap between them: a mono caption, the verdict in Geist 17px (red when the verdict is "don't buy"), and a mono reason. On narrow screens it becomes an inline sentence under the chart.

### Dalton Spheres (signature)
Glossy gold spheres, area-proportional to model size, lit from the upper left (cream highlight through gold to bronze), with a bold size label and a mono parameter count beneath. They spring in one after another and swell on hover. Founder-kept; part of the world.

## Do's and Don'ts

### Do:
- **Do** keep silver for reward and gold for transfer in every chart, readout and legend.
- **Do** reserve the gold button for "Request an appraisal", paired with a secondary "See a sample report" where there is room.
- **Do** open every data container with a mono run header and mark demo results as "demo data".
- **Do** set h1, h2 and big figures in Bodoni Moda, with one gold italic accent per headline at most.
- **Do** separate with 1px hairlines in `line` and let tone carry depth.
- **Do** ease state changes with cubic-bezier(.16, 1, .3, 1) and give every animation a reduced-motion state that shows the final values.

### Don't:
- **Don't** put an eyebrow or kicker label above a headline; mono labels live inside panel headers and data rows only.
- **Don't** use gradient text.
- **Don't** set prose, navigation or headings in Geist Mono.
- **Don't** use red or green for anything that isn't a judgement on data.
- **Don't** set body, UI or titles in Bodoni Moda, or put a gold italic accent in Geist.
- **Don't** add a neutral drop shadow to a resting panel or card.
- **Don't** show the product as a glowing screenshot; draw the evidence as a live chart.
