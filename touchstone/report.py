"""Render appraisal results into a small, self-contained static website."""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

# Paste the request form link (Google Forms, Tally, Typeform) here; the site's buttons use it once set.
REQUEST_FORM_URL = ""

# Where Touchstone is and where it is going. Stage is "Done", "Now", "Next" or "Later"; edit as things happen.
ROADMAP = [
    ("Done", "Prototype pipeline", "Seal, train four model sizes, test transfer, probe the grader, forecast and price. Runs end to end."),
    ("Now", "Customer conversations", "Reaching out to RL environment vendors and AI teams about pilot appraisals."),
    ("Next", "A real open-source environment", "Run a public RL environment through the full pipeline."),
    ("Next", "Compare environments", "Rank several environments side by side by value per dollar."),
    ("Later", "Beyond RL", "Training decisions across model types, and forecasting behaviour before a model ships."),
]

# The team, shown on the home page once filled in: (name, role, one line on why you, link or "").
FOUNDERS = []

GRADE_CLASS = {"A": "g-a", "B": "g-b", "C": "g-c", "D": "g-d", "F": "g-f", "—": "g-base"}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def fmt_params(value: int) -> str:
    return f"{value / 1e6:.2f}M" if value >= 1e6 else f"{value / 1e3:.0f}K"


def pts(value: float) -> str:
    return f"{value:+.1f}".replace("-", "−")


def chip(value: float, unit: str = "pts", after: str = "") -> str:
    """A signed number set inside prose as a small data chip, kept on one line with trailing punctuation."""
    return (f'<span class="chip-wrap"><b class="chip {"gain" if value >= 0 else "loss"}">'
            f'{pts(value)}{(" " + unit) if unit else ""}</b>{after}</span>')


def spec_list(items: list[tuple[str, str]]) -> str:
    return '<dl class="spec-list">' + "".join(f"<div><dt>{esc(label)}</dt><dd>{value}</dd></div>" for label, value in items) + "</dl>"


ICONS = {
    "search": '<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/>',
    "theme": '<circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor"/>',
    "print": '<path d="M7 9V4h10v5M7 17H5a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-2"/><path d="M7 14h10v6H7z"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
}


def icon(name: str) -> str:
    """Line icons drawn in SVG so they never fall back to a platform emoji."""
    return (f'<svg class="icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" '
            f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def brand_mark() -> str:
    return """<svg class="brand-mark" viewBox="0 0 42 42" aria-hidden="true">
<defs><linearGradient id="stone-face" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#777b80"/><stop offset=".48" stop-color="#35393d"/><stop offset="1" stop-color="#17191b"/></linearGradient></defs>
<path d="M5 13 14 5l13 2 10 10-3 15-12 6L8 32 3 22z" fill="url(#stone-face)" stroke="#bfc2c3" stroke-width="1.2"/>
<path d="m9 13 8-5 8 2 7 8-3 5-11-3-7 6-7-5z" fill="#ffffff" opacity=".14"/>
<path d="m24 8 3 10-4 5 5 3-3 9" fill="none" stroke="#d4aa57" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2"/>
<path d="m10 28 8-5 8 3" fill="none" stroke="#d7d9d9" stroke-linecap="round" stroke-width="1"/>
</svg>"""


def spark(curve: list[float], width: int = 110, height: int = 30) -> str:
    if len(curve) < 2:
        return ""
    high = max(1e-6, max(curve))
    points = [(i * width / (len(curve) - 1), height - 2 - value / high * (height - 4))
              for i, value in enumerate(curve)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area = f"0,{height} " + line + f" {width},{height}"
    x, y = points[-1]
    return (f'<svg class="spark" viewBox="0 0 {width} {height}" aria-hidden="true">'
            f'<polygon points="{area}"/><polyline points="{line}"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5"/></svg>')


def scatter(envs: list[dict], mean_miss: float) -> str:
    """Forecast against measured change, with each set's miss drawn to the diagonal."""
    width, height, pad = 560, 380, 58
    predicted = [env["forecast"]["forecast"] for env in envs]
    actual = [env["actual_at_truth"] for env in envs]
    lows = [env["forecast"]["lo"] for env in envs]
    highs = [env["forecast"]["hi"] for env in envs]
    low = float(int(min(predicted + actual + lows)) - 1)
    high = float(int(max(predicted + actual + highs)) + 1)
    if high <= low:
        high = low + 1

    def sx(value):
        return pad + (value - low) / (high - low) * (width - pad - 18)

    def sy(value):
        return height - pad + 8 - (value - low) / (high - low) * (height - pad - 18)

    tick = 2 if high - low <= 16 else 5 if high - low <= 40 else 10
    x0, x1, y0, y1 = sx(low), sx(high), sy(low), sy(high)
    parts = [f'<clipPath id="sc-clip"><rect x="{x0:.1f}" y="{y1:.1f}" width="{x1 - x0:.1f}" height="{y0 - y1:.1f}"/></clipPath>']
    for value in range(int(low), int(high) + 1):
        major = value % tick == 0
        size = 6 if major else 3
        parts.append(f'<line class="sc-tick{"" if major else " minor"}" x1="{sx(value):.1f}" x2="{sx(value):.1f}" y1="{y0:.1f}" y2="{y0 + size:.1f}"/>'
                     f'<line class="sc-tick{"" if major else " minor"}" y1="{sy(value):.1f}" y2="{sy(value):.1f}" x1="{x0 - size:.1f}" x2="{x0:.1f}"/>')
        if major:
            parts.append(f'<line class="sc-grid" x1="{sx(value):.1f}" x2="{sx(value):.1f}" y1="{y1:.1f}" y2="{y0:.1f}"/>'
                         f'<line class="sc-grid" y1="{sy(value):.1f}" y2="{sy(value):.1f}" x1="{x0:.1f}" x2="{x1:.1f}"/>'
                         f'<text class="sc-tick-label" x="{sx(value):.1f}" y="{y0 + 18:.1f}" text-anchor="middle">{value:+d}</text>'
                         f'<text class="sc-tick-label" x="{x0 - 10:.1f}" y="{sy(value) + 3:.1f}" text-anchor="end">{value:+d}</text>')
    band = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in (
        (low, low - mean_miss), (high, high - mean_miss), (high, high + mean_miss), (low, low + mean_miss)))
    parts.append(f'<g clip-path="url(#sc-clip)"><polygon class="sc-band" points="{band}"/>'
                 f'<line class="sc-band-edge" x1="{x0:.1f}" y1="{sy(low + mean_miss):.1f}" x2="{x1:.1f}" y2="{sy(high + mean_miss):.1f}"/>'
                 f'<line class="sc-band-edge" x1="{x0:.1f}" y1="{sy(low - mean_miss):.1f}" x2="{x1:.1f}" y2="{sy(high - mean_miss):.1f}"/></g>'
                 f'<line class="sc-diag" pathLength="1" x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}"/>'
                 f'<rect class="sc-plot" x="{x0:.1f}" y="{y1:.1f}" width="{x1 - x0:.1f}" height="{y0 - y1:.1f}"/>')
    angle = -45 * (y0 - y1) / (x1 - x0)
    note_x = sx(low + (high - low) * .78)
    parts.append(f'<text class="sc-note" x="{note_x:.1f}" y="{sy(low + (high - low) * .78) - 7:.1f}" text-anchor="middle" '
                 f'transform="rotate({angle:.1f} {note_x:.1f} {sy(low + (high - low) * .78):.1f})">perfect forecast</text>'
                 f'<text class="sc-band-label" x="{x1 - 6:.1f}" y="{y0 - 8:.1f}" text-anchor="end">shaded: ±{mean_miss:.1f} pts average miss</text>')
    for index, (env, forecast, observed) in enumerate(zip(envs, predicted, actual)):
        interval = env["forecast"]
        px, py = sx(forecast), sy(observed)
        parts.append(
            f'<g class="sc-range"><line class="sc-whisker" x1="{sx(interval["lo"]):.1f}" x2="{sx(interval["hi"]):.1f}" y1="{py:.1f}" y2="{py:.1f}"/>'
            f'<line class="sc-whisker" x1="{sx(interval["lo"]):.1f}" x2="{sx(interval["lo"]):.1f}" y1="{py - 4:.1f}" y2="{py + 4:.1f}"/>'
            f'<line class="sc-whisker" x1="{sx(interval["hi"]):.1f}" x2="{sx(interval["hi"]):.1f}" y1="{py - 4:.1f}" y2="{py + 4:.1f}"/></g>')
        parts.append(
            f'<a class="chart-point-link" href="../appraisals/{esc(env["id"])}/index.html" data-chart-point data-pop-open="peek-{esc(env["id"])}" tabindex="0" '
            f'data-name="{esc(env["name"])}" data-forecast="{forecast:+.1f}" data-actual="{observed:+.1f}" data-px="{px:.1f}" data-py="{py:.1f}" '
            f'data-low="{interval["lo"]:+.1f}" data-high="{interval["hi"]:+.1f}" data-grade="{esc(env["grade"])}" '
            f'aria-label="Open {esc(env["name"])} quick look: forecast {forecast:+.1f}, actual {observed:+.1f}">'
            f'<line class="sc-resid" x1="{px:.1f}" x2="{px:.1f}" y1="{py:.1f}" y2="{sy(forecast):.1f}"/>'
            f'<text class="sc-miss" x="{px + 9:.1f}" y="{(py + sy(forecast)) / 2 + 3:.1f}">miss {observed - forecast:+.1f}</text>'
            f'<rect class="sc-point {GRADE_CLASS[env["grade"]]}" x="{px - 5:.1f}" y="{py - 5:.1f}" width="10" height="10" style="--n:{index}">'
            f'<title>{esc(env["name"])}: forecast {forecast:+.1f}, actual {observed:+.1f}</title></rect></a>')
    parts.append(f'<g class="sc-xhair" aria-hidden="true"><line/><line/>'
                 f'<g><rect x="-26" y="0" width="52" height="15"/><text y="11" text-anchor="middle"></text></g>'
                 f'<g><rect x="-54" y="-7.5" width="52" height="15"/><text x="-28" y="3.5" text-anchor="middle"></text></g></g>')
    parts.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{height - 5}" class="sc-axis" text-anchor="middle">Predicted change, pts →</text>')
    parts.append(f'<text x="13" y="{(y0 + y1) / 2:.1f}" class="sc-axis" text-anchor="middle" transform="rotate(-90 13 {(y0 + y1) / 2:.1f})">Measured change, pts →</text>')
    return (f'<svg viewBox="0 0 {width} {height}" role="group" data-plot data-low="{low}" data-high="{high}" '
            f'data-x0="{x0:.1f}" data-x1="{x1:.1f}" data-y0="{y0:.1f}" data-y1="{y1:.1f}" '
            f'aria-label="Interactive forecast versus actual transfer chart">{"".join(parts)}</svg>')


def chart_legend(envs: list[dict]) -> str:
    items = []
    for env in envs:
        items.append(
            f'<a href="../appraisals/{esc(env["id"])}/index.html" class="legend-item">'
            f'<i class="{GRADE_CLASS[env["grade"]]}"></i><span>{esc(env["name"])}</span>'
            f'<b aria-label="Grade {esc(env["grade"])}">{esc(env["grade"])}</b></a>'
        )
    return f'<div class="chart-legend" aria-label="Chart environment links">{"".join(items)}</div>'


def axis_limit(values, step: float = 2.0) -> float:
    """Round the largest magnitude up to a tidy step so bars share one axis."""
    high = max([abs(value) for value in values] + [step])
    return step * -(-high // step)


def signed_bar(value: float, limit: float) -> str:
    side = "gain" if value >= 0 else "loss"
    share = min(abs(value) / limit, 1) * 50
    return f'<span class="dbar" aria-hidden="true"><i class="{side}" style="--share:{share:.1f}%"></i></span>'


def meter(share: float, risk: bool = False, delay: int = 0) -> str:
    """Twenty-cell meter, lit left to right like a level gauge."""
    return (f'<span class="meter{" is-risk" if risk else ""}" aria-hidden="true">'
            f'<i style="--share:{min(share, 1) * 100:.1f}%;--delay:{delay}ms"></i></span>')


def ruler(low: float, high: float, step: float, minor: float, labels: bool = True) -> str:
    """Tick marks positioned along a horizontal axis, as percentages."""
    ticks = []
    for index in range(int(round((high - low) / minor)) + 1):
        value = round(low + index * minor, 6)
        at = (value - low) / (high - low) * 100
        major = abs(value / step - round(value / step)) < 1e-6
        label = f'<em>{"0" if value == 0 else f"{value:+g}".replace("-", "−")}</em>' if labels and major else ""
        ticks.append(f'<span class="{"major" if major else "minor"}{" is-zero" if value == 0 else ""}" style="left:{at:.2f}%">{label}</span>')
    return f'<span class="ruler" aria-hidden="true">{"".join(ticks)}</span>'


def mini_bars(values: list[float], tips: list[str], label: str) -> str:
    """Tiny column chart; diverges around a zero line when any value is negative."""
    diverging = any(value < 0 for value in values)
    high = max([abs(value) for value in values] + [1e-9])
    bars = "".join(
        f'<i class="{"gain" if value >= 0 else "loss"}" data-tip="{esc(tip)}" '
        f'style="--h:{abs(value) / high * (50 if diverging else 100):.1f}%;--n:{index}"></i>'
        for index, (value, tip) in enumerate(zip(values, tips)))
    return f'<span class="mini-bars{"" if diverging else " is-up"}" role="img" aria-label="{esc(label)}">{bars}</span>'


def ladder_chart(environment: dict) -> str:
    """Before → after at each model size: a tick where practice started, an arrow where it ended."""
    rungs = list(environment["rungs"].items())
    width, left, right, row = 440, 74, 70, 36
    axis = 14 + row * len(rungs)
    height = axis + 44
    top = max(max(r["heldout_before"], r["heldout_after"]) for _, r in rungs)
    domain = max(10.0, 10 * -(-top * 1.08 // 10))

    def sx(value):
        return left + value / domain * (width - left - right)

    parts = [f'<line class="db-axis" x1="{sx(0):.1f}" x2="{sx(domain):.1f}" y1="{axis}" y2="{axis}"/>']
    for index in range(len(rungs)):
        if index % 2 == 0:
            parts.append(f'<rect class="db-band" x="0" y="{14 + index * row - row / 2:.1f}" width="{width}" height="{row}"/>')
    for tick in range(0, int(domain) + 1, 5):
        major = tick % 10 == 0
        parts.append(f'<line class="db-tick{"" if major else " minor"}" x1="{sx(tick):.1f}" x2="{sx(tick):.1f}" y1="{axis}" y2="{axis + (6 if major else 3)}"/>')
        if major:
            parts.append(f'<text class="db-tick-label" x="{sx(tick):.1f}" y="{axis + 17}" text-anchor="middle">{tick}</text>')
    for index, (size, rung) in enumerate(rungs):
        y = 14 + index * row
        before, after = rung["heldout_before"], rung["heldout_after"]
        side = "gain" if after >= before else "loss"
        bx, ax = sx(before), sx(after)
        direction = 1 if after >= before else -1
        tip_x = ax - direction * 7
        tip = f"{size} · {fmt_params(rung['params'])} params: {before:.1f} → {after:.1f} ({pts(after - before)} pts)"
        parts.append(
            f'<g class="db-row" data-tip="{esc(tip)}" style="--n:{index}">'
            f'<rect class="db-hit" x="0" y="{y - row / 2:.1f}" width="{width}" height="{row}"/>'
            f'<line class="db-proj" x1="{bx:.1f}" x2="{bx:.1f}" y1="{y:.1f}" y2="{axis}"/><line class="db-proj" x1="{ax:.1f}" x2="{ax:.1f}" y1="{y:.1f}" y2="{axis}"/>'
            f'<text class="db-label" x="8" y="{y + 3.5:.1f}"><tspan class="db-size">{esc(size)}</tspan> {fmt_params(rung["params"])}</text>'
            f'<line class="db-before" x1="{bx:.1f}" x2="{bx:.1f}" y1="{y - 7:.1f}" y2="{y + 7:.1f}"/>'
            f'<line class="db-line {side}" pathLength="1" x1="{bx:.1f}" x2="{tip_x:.1f}" y1="{y:.1f}" y2="{y:.1f}"/>'
            f'<polygon class="db-arrow {side}" points="{ax:.1f},{y:.1f} {tip_x:.1f},{y - 5:.1f} {tip_x:.1f},{y + 5:.1f}"/>'
            f'<text class="db-value" x="{width - 6}" y="{y + 4:.1f}" text-anchor="end">{pts(after - before)}</text>'
            f'<g class="db-tag" transform="translate({bx:.1f} {axis + 24})"><rect x="-22" y="0" width="44" height="14"/><text y="10" text-anchor="middle">{before:.1f}</text></g>'
            f'<g class="db-tag is-after {side}" transform="translate({ax:.1f} {axis + 4})"><rect x="-22" y="0" width="44" height="14"/><text y="10" text-anchor="middle">{after:.1f}</text></g></g>')
    return (f'<figure class="db-chart viz"><svg viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="Held-out score before and after practice at each model size">{"".join(parts)}</svg>'
            f'<figcaption><span><i class="key-before"></i>Before practice</span><span><i class="key-after"></i>After practice</span>'
            f'<span>Score on new questions, 0–{domain:.0f} · hover a row to project it</span></figcaption></figure>')


def probe_bars(environment: dict) -> str:
    rows = ['<li class="probe-head" aria-hidden="true"><span>Non-answer</span><span class="probe-scale"><em>0</em><em class="is-flag">20% flag</em><em>100%</em></span><span></span><span></span></li>']
    for index, (name, value) in enumerate(environment["hackability"]["per_exploit"].items()):
        flagged = value >= .2
        rows.append(f'<li class="probe-row{" is-flagged" if flagged else ""}" data-tip="{esc(name)}: non-answers earned {value:.0%} of the reward">'
                    f'<span>{esc(name)}</span><span class="meter-wrap">{meter(value, flagged, index * 90)}</span>'
                    f'<b>{value:.0%}</b><em>{"Flagged" if flagged else "Held"}</em></li>')
    return f'<ul class="probe-bars viz">{"".join(rows)}</ul>'


def range_strip(environment: dict) -> str:
    """The forecast's 90% range with the forecast and the measured result on one ruled axis."""
    forecast = environment["forecast"]
    actual = environment["actual_at_truth"]
    values = [forecast["lo"], forecast["hi"], actual, forecast["forecast"], 0.0]
    low, high = float(int(min(values)) - 2), float(int(max(values)) + 2)
    step = 5 if high - low > 16 else 2

    def at(value):
        return (value - low) / (high - low) * 100

    stacked = abs(at(forecast["forecast"]) - at(actual)) < 24
    zones = json.dumps([[round(forecast["lo"], 2), "below the 90% range"], [round(forecast["hi"], 2), "inside the 90% range"],
                        [high + 1, "above the 90% range"]])
    return (f'<div class="range-strip viz{" is-stacked" if stacked else ""}" role="img" aria-label="Forecast {pts(forecast["forecast"])} points, '
            f'90% range {pts(forecast["lo"])} to {pts(forecast["hi"])}, measured {pts(actual)} points">'
            f'<div class="range-track" data-scrub data-min="{low}" data-max="{high}" data-digits="1" data-unit=" pts" data-zones="{esc(zones)}">'
            f'<span class="range-band" style="left:{at(forecast["lo"]):.1f}%;width:{at(forecast["hi"]) - at(forecast["lo"]):.1f}%"></span>'
            f'<span class="range-zero" style="left:{at(0):.1f}%"></span>'
            f'<span class="range-forecast" style="left:{at(forecast["forecast"]):.1f}%"><b class="range-tag">forecast {pts(forecast["forecast"])}</b></span>'
            f'<span class="range-actual" style="left:{at(actual):.1f}%"><b class="range-tag">measured {pts(actual)}</b></span>'
            f'{ruler(low, high, step, 1)}</div>'
            f'<div class="range-key"><span><i class="key-band"></i>90% range {pts(forecast["lo"])} to {pts(forecast["hi"])}</span>'
            f'<span><i class="key-forecast"></i>Forecast</span><span><i class="key-actual"></i>Measured</span><span>hover the strip to read it</span></div></div>')


def pop_window(pop_id: str, title: str, panels: list[tuple[str, str]], wide: bool = False) -> str:
    """A floating, draggable window; more than one panel renders as tabs."""
    tabs = ""
    if len(panels) > 1:
        tabs = '<div class="pop-tabs" role="tablist">' + "".join(
            f'<button class="pop-tab" type="button" role="tab" id="{pop_id}-tab-{index}" aria-controls="{pop_id}-panel-{index}" '
            f'aria-selected="{"true" if index == 0 else "false"}" tabindex="{0 if index == 0 else -1}">{esc(label)}</button>'
            for index, (label, _) in enumerate(panels)) + '<span class="pop-tab-ink" aria-hidden="true"></span></div>'
    body = "".join(
        f'<div class="pop-panel{" is-active" if index == 0 else ""}" id="{pop_id}-panel-{index}"'
        + (f' role="tabpanel" aria-labelledby="{pop_id}-tab-{index}"' if tabs else "")
        + f'{"" if index == 0 else " hidden"}>{content}</div>'
        for index, (_, content) in enumerate(panels))
    return (f'<section class="pop-window{" is-wide" if wide else ""}" id="{pop_id}" role="dialog" aria-labelledby="{pop_id}-title" hidden>'
            f'<div class="pop-bar" data-drag-handle><span class="lights">'
            f'<button class="light is-close" type="button" data-pop-close aria-label="Close window"></button>'
            f'<button class="light is-min" type="button" data-pop-minimize aria-label="Minimize window to the tab bar"></button>'
            f'<button class="light is-zoom" type="button" data-pop-zoom aria-label="Zoom window"></button></span>'
            f'<span class="pop-title" id="{pop_id}-title">{esc(title)}</span></div>'
            f'{tabs}<div class="pop-body">{body}</div></section>')


def peek_window(environment: dict, href: str) -> str:
    forecast = environment["forecast"]
    overview = (
        f'<div class="pop-lead"><span class="pop-grade">{esc(environment["grade"])}</span><div>'
        f'<strong class="pop-heading">{esc(environment["name"])}</strong>'
        f'<span class="pop-kicker">{environment["redundancy"]["n_tasks"]:,} tasks · {environment["redundancy"]["unique_tasks"]:,} unique</span></div></div>'
        f'<div class="pop-stats"><div class="pop-stat"><small>Measured on new questions</small><b data-count>{pts(environment["actual_at_truth"])}</b></div>'
        f'<div class="pop-stat"><small>Forecast vs free</small><b data-count>{pts(environment["lift_over_free"])}</b></div>'
        f'<div class="pop-stat"><small>Value per task</small><b data-count>${environment["fair_value_per_task"]:,.0f}</b></div></div>'
        f'<p class="pop-label">Forecast at the largest model, against what happened</p>{range_strip(environment)}')
    flags = environment["flags"]
    flag_list = ("<ul class=\"pop-flags\">" + "".join(f"<li>{esc(flag)}</li>" for flag in flags) + "</ul>"
                 if flags else '<p class="pop-note">No appraisal flags.</p>')
    shortcuts = (f'<p class="pop-label">Reward earned by non-answers · lower is better</p>{probe_bars(environment)}{flag_list}')
    transfer = (f'<p class="pop-label">Held-out score before → after practice</p>{ladder_chart(environment)}'
                f'<p class="pop-note">Forecast at the largest model: {pts(forecast["forecast"])} pts '
                f'(90% range {pts(forecast["lo"])} to {pts(forecast["hi"])}).</p>')
    certificate = (f'<a class="button button-ink" href="{href}">Open certificate <span class="button-orb" aria-hidden="true">↗</span></a>'
                   if href else '<span class="pop-note">The free yardstick has no certificate.</span>')
    actions = (f'<div class="pop-actions">{certificate}'
               f'<button class="button button-outline" type="button" data-copy="{esc(environment["sha256"])}">Copy fingerprint</button></div>')
    return pop_window(f'peek-{environment["id"]}', f'Quick look · {environment["name"]}',
                      [("Overview", overview + actions), ("Transfer", transfer + actions), ("Shortcuts", shortcuts + actions)])


def peek_button(environment: dict, label: str = "Quick look") -> str:
    return (f'<button class="peek-button" type="button" data-pop-open="peek-{esc(environment["id"])}" aria-haspopup="dialog">'
            f'<span class="peek-eye" aria-hidden="true"></span>{esc(label)}</button>')


def info_chip(pop_id: str, label: str) -> str:
    return (f'<button class="info-chip" type="button" data-pop-open="{pop_id}" aria-haspopup="dialog" aria-expanded="false" '
            f'aria-label="{esc(label)}"></button>')


def scoreboard(environments: list[dict], base: dict) -> str:
    """One row per practice set: measured change, shortcut reward and public overlap. Sortable and scrubbable."""
    everyone = environments + [base]
    limit = axis_limit([env["actual_at_truth"] for env in everyone])
    rows = []
    for index, env in enumerate(everyone):
        change = env["actual_at_truth"]
        hack = env["hackability"]["score"]
        overlap = env["redundancy"]["public_overlap"]
        tip = (f"{env['name']}: {pts(change)} pts on new questions · shortcut reward {hack:.0%} · "
               f"public overlap {overlap:.0%}")
        rows.append(
            f'<button class="board-row{" is-baseline" if env["is_public_baseline"] else ""}" type="button" '
            f'data-pop-open="peek-{esc(env["id"])}" aria-haspopup="dialog" data-tip="{esc(tip)}" '
            f'data-name="{esc(env["name"])}" data-change="{change:.3f}" data-hack="{hack:.4f}" data-overlap="{overlap:.4f}" style="--n:{index}">'
            f'<span class="board-name"><i class="board-grade">{esc(env["grade"])}</i>{esc(env["name"])}</span>'
            f'<span class="board-cell board-change">{signed_bar(change, limit)}<b>{pts(change)}</b></span>'
            f'<span class="board-cell">{meter(hack, hack >= .2, index * 70)}<b>{hack:.0%}</b></span>'
            f'<span class="board-cell">{meter(overlap, overlap >= .5, index * 70)}<b>{overlap:.0%}</b></span>'
            f'<span class="board-open" aria-hidden="true">↗</span></button>')
    step = 2 if limit <= 10 else 5
    return (f'<div class="scoreboard viz crop" role="group" aria-label="Every practice set at a glance" data-limit="{limit}">'
            f'<div class="board-head"><button class="board-sort" type="button" data-sort="name">Practice set</button>'
            f'<span class="board-axis"><button class="board-sort" type="button" data-sort="change">Change on new questions, pts</button>'
            f'{ruler(-limit, limit, step, 1)}</span>'
            f'<button class="board-sort" type="button" data-sort="hack">Shortcut reward</button>'
            f'<button class="board-sort" type="button" data-sort="overlap">Copied from free</button><span></span></div>'
            f'<div class="board-rows">{"".join(rows)}<span class="board-scrub" aria-hidden="true"><b></b><span></span></span></div></div>')


def rank_slope(environments: list[dict]) -> str:
    """Bump chart from forecast rank to measured rank; flat lines mean the order held."""
    by_forecast = sorted(environments, key=lambda env: (-env["forecast"]["forecast"], env["name"]))
    by_actual = sorted(environments, key=lambda env: (-env["actual_at_truth"], env["name"]))
    count = len(environments)
    lines, left, right = [], [], []
    for env in environments:
        start, end = by_forecast.index(env), by_actual.index(env)
        kept = abs(start - end) <= 1
        y1, y2 = (start + .5) / count * 100, (end + .5) / count * 100
        tip = f"{env['name']}: forecast rank {start + 1}, measured rank {end + 1}"
        lines.append(f'<polyline class="{"is-kept" if kept else ""}" data-slope="{esc(env["id"])}" data-tip="{esc(tip)}" '
                     f'points="0,{y1:.2f} 16,{y1:.2f} 84,{y2:.2f} 100,{y2:.2f}"/>')
    for rank, env in enumerate(by_forecast, 1):
        left.append(f'<li data-slope="{esc(env["id"])}"><b>{pts(env["forecast"]["forecast"])}</b><span>{esc(env["name"])}</span><i>{rank:02d}</i></li>')
    for rank, env in enumerate(by_actual, 1):
        moved = by_forecast.index(env) + 1 - rank
        badge = (f'<em class="up">▲{moved}</em>' if moved > 0 else f'<em class="down">▼{-moved}</em>' if moved < 0 else '<em class="same">=</em>')
        right.append(f'<li data-slope="{esc(env["id"])}"><i>{rank:02d}</i><span>{esc(env["name"])}</span>{badge}<b>{pts(env["actual_at_truth"])}</b></li>')
    return (f'<figure class="slope viz" style="--rows:{count}"><div class="slope-head"><span>Forecast order</span><span></span><span>Measured order</span></div>'
            f'<div class="slope-body"><ol class="slope-left">{"".join(left)}</ol>'
            f'<svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Lines connect each set\'s forecast rank to its measured rank">{"".join(lines)}</svg>'
            f'<ol class="slope-right">{"".join(right)}</ol></div>'
            f'<figcaption><span><i class="key-kept"></i>Rank held within one place</span><span><i class="key-moved"></i>Rank moved two or more places</span></figcaption></figure>')


def model_ladder(ladder: dict) -> str:
    """Circles whose area is proportional to parameter count; they can be nested to compare."""
    biggest, smallest = max(ladder.values()), min(ladder.values())
    rungs = "".join(
        f'<figure class="ladder-rung" style="--d:{(params / biggest) ** .5 * 140:.1f}px;--n:{index}">'
        f'<span class="ladder-dot" data-tip="{esc(size)}: {params:,} parameters · {params / smallest:,.1f}× the smallest"></span>'
        f'<figcaption><b>{esc(size)}</b>{fmt_params(params)}</figcaption></figure>'
        for index, (size, params) in enumerate(ladder.items()))
    wider = (7e9 / biggest) ** .5
    return (f'<div class="ladder-wrap"><button class="ladder-toggle" type="button" data-ladder-toggle aria-pressed="false">Nest the circles</button>'
            f'<div class="model-ladder viz">{rungs}</div></div>'
            f'<p class="pop-note">Circle area is proportional to parameters. A 7B model drawn to the same scale would be about '
            f'{wider:.0f}× wider than XL, roughly {wider * 140:,.0f} px across.</p>')


def rho_scale(rho: float) -> str:
    """An instrument dial for rank match, with the keep-or-kill threshold marked."""
    def at(value):
        return (value + 1) / 2 * 100

    zones = json.dumps([[-.3, "mostly reversed"], [.3, "no consistent match"], [.6, "weak: below the 0.6 keep threshold"],
                        [1.01, "usable: at or above the keep threshold"]])
    bands = "".join(f'<span class="rho-zone {name}" style="left:{at(lo):.1f}%;width:{at(hi) - at(lo):.1f}%"></span>'
                    for name, lo, hi in (("z-rev", -1, -.3), ("z-none", -.3, .3), ("z-weak", .3, .6), ("z-keep", .6, 1)))
    return (f'<div class="rho-scale viz" role="img" aria-label="Rank match {rho:.2f} on a scale from −1 to 1; the keep threshold is 0.6">'
            f'<div class="rho-track" data-scrub data-min="-1" data-max="1" data-digits="2" data-zones="{esc(zones)}">{bands}'
            f'<span class="rho-keep" style="left:{at(.6):.1f}%"><em>keep ≥ 0.6</em></span>'
            f'{ruler(-1, 1, .5, .1)}<span class="rho-needle" style="--at:{at(rho):.1f}%"><b>{rho:.2f}</b></span></div>'
            f'<div class="rho-labels"><span>reversed</span><span>no match</span><span>same order</span></div></div>')


CSS = r"""
:root{color-scheme:light;--paper:#f7f5ef;--surface:#fffefa;--ink:#172b3b;--muted:#6b7981;--line:#deded7;--navy:#123446;--navy-2:#1c4d5e;--mint:#b9f1ce;--lime:#d8fa70;--blue:#2768f5;--blue-soft:#e8efff;--good:#24764b;--good-soft:#e1f3e7;--warn:#94600d;--warn-soft:#fff0d4;--bad:#a33732;--bad-soft:#fbe7e3;--base:#75828a;--base-soft:#e9eceb;--mono:"IBM Plex Mono",monospace;--sans:"Inter",Arial,sans-serif;--display:"Space Grotesk",sans-serif}
:root[data-theme=dark]{color-scheme:dark;--paper:#111d25;--surface:#192832;--ink:#f3f5ef;--muted:#a3b3b9;--line:#30434d;--navy:#0a1a22;--navy-2:#193b49;--mint:#a9eec1;--lime:#dbf686;--blue:#91adff;--blue-soft:#27354d;--good:#83d8a1;--good-soft:#20392b;--warn:#f0c16d;--warn-soft:#3d311c;--bad:#f08d82;--bad-soft:#422724;--base:#a4b2b5;--base-soft:#29363c}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:95px}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 var(--sans);-webkit-font-smoothing:antialiased}button,input{font:inherit}a{color:inherit}button{color:inherit}.site-nav{position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:22px;min-height:76px;padding:0 clamp(22px,6vw,92px);border-bottom:1px solid color-mix(in srgb,var(--line),transparent 14%);background:color-mix(in srgb,var(--paper),transparent 7%);backdrop-filter:blur(16px)}.wordmark{display:flex;align-items:center;gap:10px;text-decoration:none;font:700 17px var(--display);letter-spacing:-.07em}.brand-icon{display:grid;place-items:center;width:29px;height:29px;border-radius:9px;background:var(--lime);color:var(--navy);font-size:17px}.nav-links,.nav-actions{display:flex;align-items:center;gap:clamp(12px,2.4vw,30px)}.nav-links a{position:relative;padding:10px 0;color:var(--muted);text-decoration:none;font-size:12px;font-weight:600;transition:color .2s}.nav-links a:after{position:absolute;right:0;bottom:3px;left:0;height:2px;background:var(--blue);content:"";transform:scaleX(0);transform-origin:left;transition:transform .22s}.nav-links a:hover,.nav-links a.active{color:var(--ink)}.nav-links a:hover:after,.nav-links a.active:after{transform:scaleX(1)}.nav-actions{gap:8px}.nav-action{display:grid;place-items:center;width:38px;height:38px;border:1px solid var(--line);border-radius:50%;background:var(--surface);cursor:pointer;transition:transform .2s,border-color .2s}.nav-action:hover{transform:translateY(-2px);border-color:var(--blue)}.menu-toggle{display:none}.nav-cta{padding:10px 15px;border-radius:999px;background:var(--ink);color:var(--paper);font-size:11px;font-weight:650;text-decoration:none;transition:transform .2s,background .2s}.nav-cta:hover{transform:translateY(-2px);background:var(--blue)}
.container{width:min(1240px,100%);margin:0 auto;padding:0 clamp(22px,6vw,92px)}.eyebrow{display:flex;align-items:center;gap:9px;margin:0 0 17px;color:var(--muted);font:500 10px var(--mono);letter-spacing:.13em;text-transform:uppercase}.eyebrow:before{width:7px;height:7px;border-radius:50%;background:var(--blue);box-shadow:0 0 0 4px color-mix(in srgb,var(--blue),transparent 88%);content:""}.hero{position:relative;overflow:hidden;background:var(--navy);color:#f6f7ed}.hero:before{position:absolute;inset:0;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.16'/%3E%3C/svg%3E");opacity:.2;pointer-events:none;content:""}.hero-inner{position:relative;display:grid;grid-template-columns:1fr .95fr;align-items:center;gap:5vw;min-height:670px;padding-top:68px;padding-bottom:72px}.hero .eyebrow{color:#b7c8c9}.hero h1{max-width:680px;margin:0;font:700 clamp(58px,8.4vw,112px)/.93 var(--display);letter-spacing:-.085em}.hero h1 span{display:block;color:var(--lime)}.hero-lede{max-width:480px;margin:25px 0 0;color:#c5d0cf;font-size:16px;line-height:1.75}.hero-buttons{display:flex;align-items:center;gap:13px;flex-wrap:wrap;margin-top:27px}.button{display:inline-flex;align-items:center;justify-content:center;gap:22px;min-height:48px;padding:0 19px;border:1px solid transparent;border-radius:999px;text-decoration:none;font-size:12px;font-weight:650;cursor:pointer;transition:transform .22s,background .22s,border-color .22s,box-shadow .22s}.button:hover{transform:translateY(-3px)}.button-lime{background:var(--lime);color:var(--navy);box-shadow:0 4px 0 #91b144}.button-lime:hover{box-shadow:0 7px 0 #91b144}.button-ghost{border-color:#ffffff42;color:#f6f7ed;background:#ffffff0b}.button-ghost:hover{background:#ffffff18}.button-arrow{font-size:17px;transition:transform .2s}.button:hover .button-arrow{transform:translate(3px,2px)}.hero-meta{display:flex;align-items:center;gap:9px;margin-top:26px;color:#b9c9c7;font-size:11px}.hero-meta b{color:var(--lime);font:500 11px var(--mono)}
.hero-scene{position:relative;min-height:425px;perspective:1000px}.scene-glow{position:absolute;top:6%;right:5%;width:310px;aspect-ratio:1;border:1px solid #d5f7e52c;border-radius:50%;box-shadow:0 0 0 38px #d5f7e510,0 0 0 82px #d5f7e509;animation:slow-spin 32s linear infinite}.scene-glow:after{position:absolute;inset:38px;border:1px dashed #d5f7e52c;border-radius:50%;content:""}.window{position:absolute;width:min(330px,83%);overflow:hidden;border:1px solid #203746;border-radius:15px;background:#f8f7f1;color:#172b3b;box-shadow:0 25px 70px #07141b70;transition:transform .45s cubic-bezier(.2,.8,.2,1),opacity .35s,filter .35s}.window:hover{transform:translateY(-7px) rotate(0)!important}.window-one{top:26px;left:2%;transform:rotate(-5deg);animation:window-one .9s .12s both}.window-two{top:163px;right:0;z-index:2;transform:rotate(4deg);animation:window-two .9s .28s both}.window-three{bottom:4px;left:8%;transform:rotate(2deg);animation:window-three .9s .42s both}.window-bar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 13px;border-bottom:1px solid #d9ddd9;background:repeating-linear-gradient(0deg,#e8e9e5,#e8e9e5 1px,#f3f3ef 1px,#f3f3ef 3px);color:#65717a;font-size:10px}.window-dots{display:flex;gap:5px}.window-dots i{width:9px;height:9px;border-radius:50%;background:#ed7264}.window-dots i:nth-child(2){background:#efbb4f}.window-dots i:nth-child(3){background:#71c58b}.window-controls{display:flex;gap:4px}.window-controls button{width:22px;height:22px;border:0;border-radius:50%;background:transparent;color:#5e6c72;cursor:pointer}.window-controls button:hover{background:#dce1dc}.window-body{padding:19px 21px 21px;background-image:radial-gradient(#172b3b12 .8px,transparent .8px);background-size:15px 15px}.window-body small{color:#6e7c7f;font:10px var(--mono);letter-spacing:.08em;text-transform:uppercase}.window-body h2{margin:10px 0 7px;font:700 24px/1.1 var(--display);letter-spacing:-.055em}.window-body p{margin:0;color:#56656b;font-size:12px;line-height:1.65}.window-tag{display:inline-flex;margin-top:14px;padding:5px 8px;border-radius:999px;background:#e6f4e9;color:#256041;font:10px var(--mono)}.window.is-minimized .window-body{display:none}.window.is-closed{opacity:0;pointer-events:none;transform:scale(.8) translateY(28px)!important}.restore-window{position:absolute;right:4px;bottom:0;display:none;padding:9px 13px;border:1px solid #ffffff50;border-radius:999px;background:#ffffff12;color:white;font-size:11px;cursor:pointer}.restore-window.visible{display:block;animation:pop-in .3s both}
.stat-rail{display:grid;grid-template-columns:repeat(4,1fr);margin:0 auto;border-bottom:1px solid var(--line)}.stat-rail>div{padding:24px 23px;border-right:1px solid var(--line)}.stat-rail>div:first-child{padding-left:0}.stat-rail>div:last-child{border:0}.stat-rail small{display:block;color:var(--muted);font-size:10px}.stat-rail b{display:block;margin-top:6px;font:600 clamp(20px,2.4vw,29px) var(--display);letter-spacing:-.05em}.stat-rail em{color:var(--muted);font:400 10px var(--mono);font-style:normal}.section{padding-top:96px;padding-bottom:96px}.section-heading{display:flex;justify-content:space-between;align-items:end;gap:32px;margin-bottom:32px}.section-heading h2,.page-title{margin:0;font:650 clamp(38px,5vw,63px)/1.02 var(--display);letter-spacing:-.075em}.section-heading h2 span,.page-title span{color:var(--blue)}.section-heading>p{max-width:400px;margin:0;color:var(--muted);font-size:13px;line-height:1.75}.section-link{display:inline-flex;align-items:center;gap:8px;color:var(--blue);font-size:12px;font-weight:650;text-decoration:none;white-space:nowrap}.section-link:hover{gap:13px}.feature-card{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(240px,.85fr);overflow:hidden;border:1px solid var(--line);border-radius:20px;background:var(--surface);box-shadow:0 14px 40px #1a30450b;transition:transform .3s,box-shadow .3s}.feature-card:hover{transform:translateY(-5px);box-shadow:0 24px 55px #1a304515}.feature-main{padding:clamp(24px,4vw,46px)}.feature-top{display:flex;align-items:center;justify-content:space-between;gap:15px;color:var(--muted);font:10px var(--mono);text-transform:uppercase;letter-spacing:.08em}.grade{display:inline-grid;place-items:center;width:40px;height:40px;border-radius:12px;font:650 20px var(--display)}.g-a,.g-b{background:var(--good-soft);color:var(--good)}.g-c{background:var(--warn-soft);color:var(--warn)}.g-d,.g-f{background:var(--bad-soft);color:var(--bad)}.g-base{background:var(--base-soft);color:var(--base)}.feature-main h3{margin:24px 0 7px;font:650 clamp(25px,3vw,37px)/1.1 var(--display);letter-spacing:-.06em}.feature-main>p{max-width:520px;color:var(--muted);font-size:13px}.feature-stats{display:flex;gap:30px;flex-wrap:wrap;margin-top:23px}.feature-stats div{display:grid;gap:3px}.feature-stats small{color:var(--muted);font-size:10px}.feature-stats b{font:550 19px var(--mono);letter-spacing:-.05em}.feature-aside{display:flex;flex-direction:column;justify-content:space-between;min-height:260px;padding:28px;background:var(--navy);color:#f2f5e9}.feature-aside .grade{background:var(--lime);color:var(--navy)}.feature-aside p{max-width:250px;color:#c1ceca;font-size:12px}.feature-aside strong{color:var(--lime);font:600 clamp(30px,4vw,48px) var(--display);letter-spacing:-.07em}.feature-aside .section-link{color:var(--lime)}
.quick-links{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:18px}.quick-card{display:flex;min-height:154px;flex-direction:column;justify-content:space-between;padding:20px;border:1px solid var(--line);border-radius:14px;background:var(--surface);text-decoration:none;transition:transform .25s,border-color .25s,background .25s}.quick-card:hover{transform:translateY(-4px);border-color:var(--blue);background:var(--blue-soft)}.quick-card span:first-child{color:var(--muted);font:10px var(--mono)}.quick-card b{font:600 19px var(--display);letter-spacing:-.04em}.quick-card>span:nth-last-child(2){align-self:flex-end;color:var(--blue);font-size:18px}
.ticker{overflow:hidden;padding:18px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);background:var(--lime);color:var(--navy)}.ticker-track{display:flex;width:max-content;align-items:center;gap:27px;animation:marquee 35s linear infinite}.ticker-track span{font:600 11px var(--mono);letter-spacing:.1em}.ticker-track i{font-style:normal;font-size:18px}.ticker:hover .ticker-track{animation-play-state:paused}
.page-head{padding:78px 0 42px}.page-head .eyebrow{margin-bottom:20px}.page-head .page-title{max-width:820px}.page-intro{max-width:650px;margin:19px 0 0;color:var(--muted);font-size:14px}.toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:20px 0 17px;flex-wrap:wrap}.filters{display:flex;gap:6px;flex-wrap:wrap}.filter{padding:8px 12px;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--muted);font-size:11px;cursor:pointer;transition:background .2s,color .2s,border-color .2s}.filter span{margin-left:5px;font:10px var(--mono)}.filter.active,.filter:hover{border-color:var(--ink);background:var(--ink);color:var(--paper)}.search{display:flex;align-items:center;gap:8px;width:min(280px,100%);height:40px;padding:0 13px;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--muted)}.search input{width:100%;border:0;outline:0;background:transparent;color:var(--ink);font-size:11px}.result-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.result-card{position:relative;display:grid;grid-template-columns:auto 1fr auto;align-items:start;gap:15px;min-height:170px;padding:21px;border:1px solid var(--line);border-radius:15px;background:var(--surface);text-decoration:none;transition:transform .25s,border-color .25s,box-shadow .25s;animation:card-in .5s both}.result-card:hover{transform:translateY(-4px);border-color:var(--blue);box-shadow:0 15px 35px #1a304510}.result-card h3{margin:2px 0 6px;font:600 18px/1.2 var(--display);letter-spacing:-.045em}.result-card p{margin:0;color:var(--muted);font-size:11px}.result-card .result-grade{width:37px;height:37px;border-radius:11px;font-size:18px}.result-arrow{color:var(--blue);font-size:20px;transition:transform .2s}.result-card:hover .result-arrow{transform:translate(3px,-3px)}.result-values{display:flex;gap:18px;flex-wrap:wrap;margin-top:16px}.result-values span{display:grid;gap:2px;color:var(--muted);font-size:9px}.result-values b{color:var(--ink);font:500 12px var(--mono)}.empty-state{grid-column:1/-1;padding:35px;text-align:center;color:var(--muted)}.baseline-card{margin-top:20px;padding:18px 20px;border:1px dashed var(--line);border-radius:13px;color:var(--muted);font-size:11px}.baseline-card b{color:var(--ink)}
.detail-hero{position:relative;overflow:hidden;margin-top:40px;padding:clamp(25px,5vw,55px);border-radius:22px;background:var(--navy);color:#f6f7ed}.detail-hero:after{position:absolute;right:-65px;bottom:-165px;width:340px;height:340px;border:1px solid #ffffff24;border-radius:50%;box-shadow:0 0 0 38px #ffffff0b,0 0 0 78px #ffffff08;content:""}.detail-hero .eyebrow{color:#c0cfcb}.detail-hero h1{position:relative;z-index:1;max-width:740px;margin:0;font:650 clamp(38px,6vw,72px)/1 var(--display);letter-spacing:-.075em}.detail-hero .detail-meta{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:22px;color:#c4d0cd;font-size:11px}.detail-hero .grade{width:48px;height:48px;background:var(--lime);color:var(--navy)}.detail-hero .detail-meta b{color:var(--lime);font:500 13px var(--mono)}.detail-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:25px}.detail-actions .button{min-height:42px;font-size:11px}.detail-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0 30px}.metric-card{padding:18px;border:1px solid var(--line);border-radius:14px;background:var(--surface)}.metric-card small{display:block;color:var(--muted);font-size:10px}.metric-card b{display:block;margin-top:9px;font:550 clamp(18px,2.5vw,26px) var(--mono);letter-spacing:-.05em}.metric-card p{margin:5px 0 0;color:var(--muted);font-size:9px}.panel{padding:clamp(20px,3vw,30px);border:1px solid var(--line);border-radius:17px;background:var(--surface)}.panel h2{margin:0 0 7px;font:600 23px var(--display);letter-spacing:-.05em}.panel-intro{margin:0 0 19px;color:var(--muted);font-size:11px}.hash-box{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:15px 0;padding:13px;border:1px solid var(--line);border-radius:11px;background:var(--paper)}.hash-box small{color:var(--muted);font:9px var(--mono);letter-spacing:.08em}.hash-box code{flex:1;min-width:180px;overflow-wrap:anywhere;font:10px var(--mono)}.copy-button{padding:7px 11px;border:1px solid var(--line);border-radius:999px;background:var(--surface);font-size:10px;cursor:pointer}.copy-button:hover{border-color:var(--blue)}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:12px}table{width:100%;border-collapse:collapse;font-size:11px}th,td{padding:12px 13px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}th{background:var(--paper);color:var(--muted);font:500 9px var(--mono);letter-spacing:.06em;text-transform:uppercase;white-space:nowrap}tr:last-child td{border-bottom:0}.num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}.spark{display:block;width:100px;height:27px}.spark polygon{fill:var(--blue-soft)}.spark polyline{fill:none;stroke:var(--blue);stroke-width:1.6}.spark circle{fill:var(--blue)}.checks{display:flex;flex-wrap:wrap;gap:8px}.check{padding:7px 10px;border-radius:999px;background:var(--base-soft);color:var(--muted);font:10px var(--mono)}.check.hit{background:var(--bad-soft);color:var(--bad)}.integrity-note{margin-top:17px;padding:14px;border-radius:11px;background:var(--bad-soft);color:var(--bad);font-size:11px}.integrity-note.clean{background:var(--good-soft);color:var(--good)}
.chart-panel{display:grid;grid-template-columns:minmax(0,.8fr) minmax(0,1.2fr);gap:25px;align-items:center}.chart-copy h2{font:600 27px/1.08 var(--display);letter-spacing:-.055em}.chart-copy>p:not(.eyebrow):not(.fine-print){color:var(--muted);font-size:12px}.chart-stat{display:flex;gap:12px;align-items:center;margin-top:21px}.chart-stat>b{font:600 42px var(--display);letter-spacing:-.07em}.chart-stat span{color:var(--muted);font-size:10px}.chart-stat small{display:block}.verdict{margin-top:18px;padding:13px;border-left:3px solid var(--blue);background:var(--blue-soft);font-size:11px}.chart svg{width:100%;height:auto}.grid{stroke:var(--line);stroke-width:1}.diag{stroke:var(--blue);stroke-dasharray:5 5;stroke-width:1.3}.whisker{stroke:var(--muted);stroke-width:1.3;opacity:.65}.point{stroke:var(--surface);stroke-width:2}.point.g-a,.point.g-b{fill:var(--good)}.point.g-c{fill:var(--warn)}.point.g-d,.point.g-f{fill:var(--bad)}.point-label,.tick{fill:var(--muted);font:10px var(--mono)}.point-label{fill:var(--ink)}.axis{fill:var(--muted);font:11px var(--sans)}
.process-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}.process-card{position:relative;min-height:205px;padding:19px;border:1px solid var(--line);border-radius:14px;background:var(--surface);transition:transform .25s,border-color .25s}.process-card:hover{transform:translateY(-5px);border-color:var(--blue)}.process-card>span{display:grid;place-items:center;width:29px;height:29px;border-radius:50%;background:var(--blue-soft);color:var(--blue);font:10px var(--mono)}.process-card h3{margin:28px 0 7px;font:600 18px var(--display)}.process-card p{margin:0;color:var(--muted);font-size:10px;line-height:1.7}.note-panel{display:flex;gap:14px;align-items:flex-start;margin-top:25px;padding:20px;border:1px solid var(--line);border-radius:14px;background:var(--surface)}.note-icon{display:grid;place-items:center;flex:none;width:27px;height:27px;border-radius:50%;background:var(--blue-soft);color:var(--blue);font:600 12px var(--mono)}.note-panel p{margin:0;color:var(--muted);font-size:11px}.note-panel b{color:var(--ink)}
.footer{display:flex;justify-content:space-between;gap:15px;align-items:center;margin-top:35px;padding:25px 0 30px;border-top:1px solid var(--line);color:var(--muted);font-size:10px}.footer .wordmark{color:var(--ink)}.footer-links{display:flex;gap:18px}.footer-links a{color:var(--muted);text-decoration:none}.footer-links a:hover{color:var(--blue)}.toast{position:fixed;right:24px;bottom:24px;z-index:50;padding:12px 17px;border-radius:999px;background:var(--ink);color:var(--paper);font-size:11px;opacity:0;transform:translateY(12px);pointer-events:none;transition:opacity .2s,transform .2s}.toast.show{opacity:1;transform:translateY(0)}dialog{width:min(500px,calc(100% - 32px));padding:0;border:1px solid var(--line);border-radius:20px;background:var(--surface);color:var(--ink);box-shadow:0 30px 100px #0819235c}dialog::backdrop{background:#0b1c28a8;backdrop-filter:blur(5px)}.dialog-inner{padding:30px}.dialog-top{display:flex;align-items:center;justify-content:space-between}.dialog-close{width:34px;height:34px;border:1px solid var(--line);border-radius:50%;background:transparent;cursor:pointer}.dialog-inner h2{margin:22px 0 8px;font:650 34px var(--display);letter-spacing:-.07em}.dialog-inner p{color:var(--muted);font-size:13px}.dialog-actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:22px}.dialog-actions .button{min-height:42px;font-size:11px}.reveal{opacity:0;transform:translateY(22px);transition:opacity .7s ease,transform .7s cubic-bezier(.2,.8,.2,1)}.reveal.visible{opacity:1;transform:none}.result-card[hidden]{display:none}
@keyframes hero-up{from{opacity:0;transform:translateY(25px)}to{opacity:1;transform:none}}@keyframes window-one{from{opacity:0;transform:translate(-25px,24px) rotate(-12deg)}to{opacity:1;transform:rotate(-5deg)}}@keyframes window-two{from{opacity:0;transform:translate(30px,30px) rotate(12deg)}to{opacity:1;transform:rotate(4deg)}}@keyframes window-three{from{opacity:0;transform:translate(-20px,25px) rotate(9deg)}to{opacity:1;transform:rotate(2deg)}}@keyframes slow-spin{to{transform:rotate(360deg)}}@keyframes marquee{to{transform:translateX(-50%)}}@keyframes card-in{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}@keyframes pop-in{from{opacity:0;transform:scale(.9)}to{opacity:1;transform:scale(1)}}@media(prefers-reduced-motion:reduce){*,*:before,*:after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}.reveal{opacity:1;transform:none}}
@media(max-width:850px){.hero-inner{grid-template-columns:1fr;gap:20px;padding-top:58px}.hero-scene{min-height:390px;max-width:590px;width:100%;margin:0 auto}.stat-rail>div{padding-inline:13px}.chart-panel{grid-template-columns:1fr}.chart{max-width:680px;margin:auto}.process-grid{grid-template-columns:repeat(3,1fr)}}
@media(max-width:620px){.site-nav{min-height:66px;padding-inline:18px}.menu-toggle{display:grid}.nav-links{position:absolute;top:65px;right:0;left:0;display:none;align-items:stretch;gap:0;padding:8px 20px 15px;border-bottom:1px solid var(--line);background:var(--paper)}.nav-links.open{display:grid}.nav-links a{padding:12px 4px}.nav-cta{padding:9px 12px}.container{padding-inline:20px}.hero-inner{min-height:auto;padding-top:52px;padding-bottom:45px}.hero h1{font-size:clamp(54px,13vw,78px)}.hero-lede{font-size:14px}.hero-scene{min-height:335px;margin-top:7px}.window{width:min(300px,85%)}.window-one{top:12px}.window-two{top:125px}.window-three{bottom:0}.stat-rail{grid-template-columns:repeat(2,1fr)}.stat-rail>div{padding:16px 10px;border-bottom:1px solid var(--line)}.stat-rail>div:first-child{padding-left:10px}.stat-rail>div:nth-child(2){border-right:0}.stat-rail>div:nth-child(3),.stat-rail>div:nth-child(4){border-bottom:0}.section{padding-top:67px;padding-bottom:67px}.section-heading{display:grid;align-items:start;gap:13px}.section-heading h2,.page-title{font-size:clamp(37px,10vw,53px)}.feature-card{grid-template-columns:1fr}.feature-aside{min-height:190px}.quick-links{grid-template-columns:1fr}.quick-card{min-height:120px}.page-head{padding:56px 0 30px}.result-grid{grid-template-columns:1fr}.toolbar{align-items:stretch}.search{width:100%}.filters{width:100%}.result-card{min-height:154px;padding:17px;gap:11px}.detail-hero{margin-top:22px}.detail-stats{grid-template-columns:repeat(2,1fr)}.process-grid{grid-template-columns:repeat(2,1fr)}.process-card{min-height:180px}.footer{align-items:flex-start;flex-wrap:wrap}.footer-links{width:100%}}
@media(max-width:390px){.nav-cta{font-size:10px}.hero h1{font-size:51px}.hero-buttons .button{min-height:43px;padding-inline:14px}.hero-scene{min-height:300px}.window{width:88%}.window-two{top:111px}.window-body{padding:15px 17px}.window-body h2{font-size:21px}.process-grid{grid-template-columns:1fr 1fr}.process-card{padding:14px}}
"""

CSS += r"""
:root{--paper:#f5f4f0;--surface:#fff;--ink:#171819;--muted:#6d7072;--line:#d8d8d4;--navy:#171819;--navy-2:#252627;--mint:#d2c19a;--lime:#d8bd7c;--blue:#a3803e;--blue-soft:#f1eadb;--good:#416952;--good-soft:#e8efe9;--warn:#927039;--warn-soft:#f4eddc;--bad:#9c4a43;--bad-soft:#f3e7e5;--base:#777b7d;--base-soft:#e9e9e6;--display:"Instrument Serif",Georgia,serif;--sans:"Manrope",Arial,sans-serif}
:root[data-theme=dark]{--paper:#151617;--surface:#202122;--ink:#f4f3ef;--muted:#a9aaab;--line:#3a3b3b;--navy:#101112;--navy-2:#242526;--mint:#d7c49b;--lime:#d8bd7c;--blue:#d2b16d;--blue-soft:#332d20;--good:#9ab7a2;--good-soft:#26352b;--warn:#d0b576;--warn-soft:#393222;--bad:#d99a91;--bad-soft:#382725;--base:#b0b1b1;--base-soft:#303132}
body{font-size:16px;letter-spacing:-.018em}.wordmark{font-family:var(--sans);font-weight:750;letter-spacing:-.065em}.brand-mark{display:block;width:37px;height:37px;flex:none;filter:drop-shadow(0 2px 3px #0002)}.wordmark:hover .brand-mark{animation:stone-turn .7s cubic-bezier(.2,.8,.2,1)}.nav-links a:after{background:var(--lime)}.nav-links a.active{color:var(--blue)}.nav-cta{border:1px solid var(--ink);background:var(--ink);color:var(--paper)}.nav-cta:hover{background:var(--blue);border-color:var(--blue)}.hero{background:#171819}.hero:before{opacity:.15}.hero h1{color:#f6f7ed;font-family:var(--display);font-size:clamp(72px,9vw,124px);font-weight:400;letter-spacing:-.045em;line-height:.84}.hero h1>span:not(.kinetic-char){color:var(--lime);font-style:italic}.hero h1 span.kinetic-char{color:inherit;font-style:inherit}.hero .eyebrow:before{background:var(--lime);box-shadow:0 0 0 4px #d8bd7c24}.hero-lede{font-size:17px}.button-lime{background:var(--lime);color:#171819;box-shadow:0 4px 0 #9c824d}.button-lime:hover{background:#e2ca91;box-shadow:0 7px 0 #9c824d}.button-ghost{border-color:#d7d7d355}.feature-aside{background:#222324}.feature-aside .grade{background:var(--lime);color:#171819}.feature-aside .section-link{color:var(--lime)}
.section-heading h2,.page-title,.chart-copy h2,.feature-main h3,.quick-card b,.process-card h3,.dialog-inner h2{font-family:var(--display);font-weight:400;letter-spacing:-.025em}.section-heading h2 span,.page-title span{color:var(--blue);font-style:italic}.page-title{font-size:clamp(52px,7vw,82px);line-height:.93}.eyebrow{letter-spacing:.16em}.eyebrow:before{background:var(--blue);box-shadow:0 0 0 4px color-mix(in srgb,var(--blue),transparent 82%)}.grade{display:inline-flex;align-items:center;justify-content:center;width:auto;height:auto;min-height:30px;padding:6px 12px;border:1px solid color-mix(in srgb,currentColor,transparent 68%);border-radius:999px;font:600 10px var(--mono);letter-spacing:.07em;text-transform:uppercase}.result-grade{font-size:9px}.feature-top>.grade{flex:none}.feature-aside .grade{border-color:#d8bd7c80}.process-card{padding-top:25px}.process-card>span{display:inline-flex;align-items:center;justify-content:center;width:auto;height:auto;min-height:26px;padding:5px 11px;border:1px solid var(--line);border-radius:999px;background:var(--paper);color:var(--blue);font:500 9px var(--mono);letter-spacing:.08em;text-transform:uppercase}.process-card h3{margin-top:31px;font-size:26px}.window-tag,.check,.filter,.quick-card>span:first-child{border-radius:999px}.window-tag{background:#eee5d3;color:#66532e}.quick-card{position:relative;min-height:172px;overflow:hidden}.quick-card:after{position:absolute;right:-26px;bottom:-50px;width:110px;height:110px;border:1px solid var(--line);border-radius:50%;box-shadow:0 0 0 13px color-mix(in srgb,var(--line),transparent 80%),0 0 0 28px color-mix(in srgb,var(--line),transparent 87%);content:"";transition:transform .4s}.quick-card:hover:after{transform:scale(1.18)}.quick-card small{max-width:85%;color:var(--muted);font-size:11px;line-height:1.6}.quick-card>span:first-child{position:relative;z-index:1;align-self:flex-start;padding:5px 9px;border:1px solid var(--line);font-size:9px}.quick-card>span:nth-last-child(2){position:relative;z-index:1;align-self:flex-end;color:var(--blue);font-size:18px}.feature-stats>div{position:relative;padding-left:13px}.feature-stats>div:before{position:absolute;top:4px;bottom:4px;left:0;width:2px;border-radius:2px;background:var(--lime);content:""}.feature-main h3{font-size:clamp(31px,4vw,47px)}.stat-rail b{display:flex;align-items:baseline;gap:0 7px;flex-wrap:wrap;font-family:var(--display);font-size:clamp(27px,3vw,38px);font-weight:400;line-height:1.05}.stat-rail em{font-family:var(--sans);font-size:11px;letter-spacing:0}.ticker{background:var(--lime);color:#171819}.ticker-track{animation-duration:48s}.ticker-track span{font-size:10px}.result-card{border-radius:4px 20px 4px 20px}.result-card:nth-child(3n+2){border-radius:20px 4px 20px 4px}.result-card:hover{border-color:var(--blue)}.metric-card{border-radius:4px 15px 4px 15px}.panel{border-radius:4px 20px 4px 20px}.detail-hero{border-radius:4px 26px 4px 26px;background:#1a1b1c}.detail-hero h1{font-family:var(--display);font-weight:400;letter-spacing:-.025em}.detail-hero .grade{background:var(--lime);color:#171819}.detail-hero .detail-meta b{color:var(--lime)}.hash-box code{color:var(--blue)}.check{border:1px solid var(--line);background:var(--surface)}.check.hit{border-color:#9c4a4360}.chart-frame{position:relative;padding:13px;border:1px solid var(--line);border-radius:3px 17px 3px 17px;background:linear-gradient(145deg,var(--surface),var(--paper));box-shadow:inset 0 1px #fff8,0 16px 38px #0000000a}.chart-frame svg{overflow:visible}.chart-frame .grid{stroke:var(--line);stroke-dasharray:2 6;opacity:.8}.chart-frame .diag{stroke:var(--blue);stroke-dasharray:4 6;stroke-width:1.8}.chart-frame .whisker{stroke:var(--blue);stroke-width:2;opacity:.5}.chart-point-link{cursor:pointer;outline:none}.point{transform-box:fill-box;transform-origin:center;transition:r .2s,filter .2s,stroke-width .2s;animation:point-arrive .6s cubic-bezier(.2,.8,.2,1) both;filter:drop-shadow(0 2px 3px #0002)}.point:hover,.chart-point-link:focus .point{r:10;stroke:var(--lime);stroke-width:4;filter:drop-shadow(0 0 6px #b7985e99)}.point-label{font-family:var(--sans);font-size:9px;font-weight:650;paint-order:stroke;stroke:var(--surface);stroke-width:3px;stroke-linejoin:round}.chart-tooltip{position:absolute;right:20px;bottom:20px;left:20px;z-index:2;display:grid;gap:4px;padding:12px 15px;border:1px solid var(--line);border-radius:3px 14px 3px 14px;background:color-mix(in srgb,var(--surface),transparent 5%);box-shadow:0 10px 24px #0002;opacity:0;transform:translateY(7px);pointer-events:none;transition:opacity .2s,transform .2s}.chart-tooltip.visible{opacity:1;transform:none}.chart-tooltip b{font:500 12px var(--sans)}.chart-tooltip span{color:var(--muted);font:10px var(--mono)}.chart-hint{margin:8px 4px 0;color:var(--muted);font-size:10px}.chart-frame .point{stroke:var(--surface)}
.kinetic-word{display:inline-block;transition:opacity .55s cubic-bezier(.2,.8,.2,1),transform .55s cubic-bezier(.2,.8,.2,1),color .2s;transition-delay:calc(var(--word-index,0)*36ms);opacity:0;transform:translateY(.42em) rotateX(-24deg);transform-origin:50% 100%}.text-entered .kinetic-word{opacity:1;transform:none}.kinetic-char{display:inline-block;transition:opacity .65s cubic-bezier(.2,.8,.2,1),transform .65s cubic-bezier(.2,.8,.2,1),color .2s;transition-delay:calc(var(--word-index,0)*16ms);opacity:0;transform:translateY(.36em) rotateX(-45deg);transform-origin:50% 100%}.text-entered .kinetic-char{opacity:1;transform:none}.hero h1 span.kinetic-char{display:inline-block}.hero h1 .kinetic-char:hover,.section-heading h2 .kinetic-char:hover,.page-title .kinetic-char:hover{color:var(--lime);transform:translateY(-.1em) rotate(-5deg)}.reveal{transition-duration:.85s}.reveal.visible{transition-timing-function:cubic-bezier(.16,1,.3,1)}.window{box-shadow:0 25px 70px #0008,0 0 0 1px #ffffff12}.window:hover{box-shadow:0 34px 90px #0009,0 0 0 1px #d8bd7c55}.window-one{animation:window-one .9s .12s both,float-note 7s 1.1s ease-in-out infinite}.window-two{animation:window-two .9s .28s both,float-note 8s 1.2s ease-in-out infinite reverse}.window-three{animation:window-three .9s .42s both,float-note 7.5s 1.4s ease-in-out infinite}.feature-card{border-radius:4px 22px 4px 22px}.feature-card:hover{box-shadow:0 24px 55px #00000014}.dialog-inner h2{font-size:42px}.footer .brand-mark{width:33px;height:33px}
@keyframes stone-turn{0%{transform:rotate(0) scale(1)}45%{transform:rotate(-13deg) scale(1.12)}100%{transform:rotate(0) scale(1)}}@keyframes float-note{0%,100%{translate:0 0}50%{translate:0 -8px}}@keyframes point-arrive{from{opacity:0;transform:scale(.3)}to{opacity:1;transform:scale(1)}}
@media(max-width:850px){.hero h1{font-size:clamp(68px,11vw,100px)}}@media(max-width:620px){.site-nav{gap:9px}.wordmark{font-size:15px}.brand-mark{width:33px;height:33px}.nav-links{z-index:2}.hero h1{font-size:clamp(62px,14vw,88px)}.hero-lede{font-size:15px}.process-card h3{font-size:22px}.chart-tooltip{right:12px;bottom:12px;left:12px}.quick-card{min-height:150px}}@media(prefers-reduced-motion:reduce){.window-one,.window-two,.window-three,.scene-glow,.ticker-track{animation:none}.kinetic-char,.kinetic-word{opacity:1;transform:none;transition:none}}
"""

CSS += r"""
.page-title span.kinetic-char,.section-heading h2 span.kinetic-char{color:inherit;font-style:inherit}
.chart-legend{display:flex;gap:8px;flex-wrap:wrap;margin:12px 3px 2px}
.legend-item{display:flex;align-items:center;gap:7px;padding:7px 10px;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--ink);font-size:9px;text-decoration:none;transition:transform .2s,border-color .2s,box-shadow .2s}
.legend-item:hover{transform:translateY(-2px);border-color:var(--blue);box-shadow:0 6px 14px #00000012}
.legend-item i{width:8px;height:8px;border-radius:50%;background:var(--good)}
.legend-item i.g-c{background:var(--warn)}.legend-item i.g-d,.legend-item i.g-f{background:var(--bad)}
.legend-item b{color:var(--muted);font:500 8px var(--mono)}
.stat-rail>div{min-width:0}.stat-rail em{display:inline-block}
"""

CSS += r"""
:root{--display:"Manrope",Arial,sans-serif;--sans:"Manrope",Arial,sans-serif}
body{font-family:var(--sans);font-size:15px;letter-spacing:-.012em}
h1,h2,h3,.page-title,.section-heading h2,.feature-main h3,.chart-copy h2,.quick-card b,.process-card h3,.dialog-inner h2,.window-body h2{font-family:var(--display);font-weight:700;letter-spacing:-.055em}
.hero h1{font-family:var(--display);font-size:clamp(62px,8vw,104px);font-weight:750;line-height:.98;letter-spacing:-.075em}
.hero h1>span:not(.kinetic-word){color:var(--lime);font-style:normal}
.hero h1 .kinetic-word{color:inherit;font-style:inherit}
.page-title{font-size:clamp(48px,6.6vw,76px);line-height:1.02}
.section-heading h2{font-size:clamp(40px,5vw,58px);line-height:1.04}
.section-heading h2 span,.page-title>span:not(.kinetic-word){color:var(--blue);font-style:normal}
.section-heading h2 .kinetic-word,.page-title .kinetic-word{color:inherit;font-style:inherit}
.hero-lede,.page-intro{font-size:15px;line-height:1.72}
.window-body p,.result-card p,.quick-card small,.process-card p,.feature-main>p,.metric-card p,.chart-copy>p:not(.eyebrow):not(.fine-print),.note-panel p,.panel-intro,.baseline-card{font-size:12px;line-height:1.65}
.eyebrow{font-family:var(--sans);font-size:10px;font-weight:650;letter-spacing:.13em}
.window-body small,.feature-top,.window-tag,.hero-meta,.result-values span,.metric-card small,.chart-hint{font-family:var(--sans);font-size:10px;letter-spacing:.015em}
.stat-rail{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px;margin:0 auto;padding:24px 0 3px}
.stat-pod{position:relative;display:grid;align-content:space-between;min-height:145px;overflow:hidden;padding:18px 19px;border:1px solid #ffffff;border-radius:4px 21px 4px 21px;background:linear-gradient(145deg,var(--surface),color-mix(in srgb,var(--surface),var(--paper) 48%));color:var(--ink);text-decoration:none;box-shadow:0 3px 0 #c9c7c0,0 12px 25px #17181912,inset 0 1px #fff;transition:transform .28s cubic-bezier(.2,.8,.2,1),box-shadow .28s,border-color .2s}
.stat-pod:nth-child(even){transform:translateY(8px);border-radius:21px 4px 21px 4px}
.stat-pod:before{position:absolute;inset:0;background:radial-gradient(circle at var(--shine-x,90%) var(--shine-y,8%),#d8bd7c35,transparent 42%);opacity:.7;content:"";pointer-events:none}
.stat-pod:after{position:absolute;right:-20px;bottom:-50px;width:100px;height:100px;border:1px solid #a3803e30;border-radius:50%;box-shadow:0 0 0 12px #a3803e0a,0 0 0 26px #a3803e08;content:"";transition:transform .4s}
.stat-pod:hover{z-index:2;transform:translateY(-5px) rotate(-1deg);border-color:#d4bd87;box-shadow:0 6px 0 #b8a779,0 22px 34px #17181920,inset 0 1px #fff}
.stat-pod:nth-child(even):hover{transform:translateY(1px) rotate(1deg)}
.stat-pod:hover:after{transform:scale(1.18)}
.stat-pod small,.stat-pod span,.stat-pod b{position:relative;z-index:1}
.stat-pod small{color:var(--muted);font-size:10px;font-weight:600}
.stat-pod b{display:block;margin:7px 0;font:750 clamp(32px,3.8vw,46px)/1 var(--sans);letter-spacing:-.075em;font-variant-numeric:tabular-nums}
.stat-pod b sup{color:var(--muted);font:500 12px var(--sans);letter-spacing:0}
.stat-pod>span{display:flex;align-items:center;justify-content:space-between;gap:8px;color:var(--muted);font-size:10px}
.stat-pod>span i{color:var(--blue);font-size:15px;font-style:normal;transition:transform .2s}
.stat-pod:hover>span i{transform:translate(3px,-3px)}
.stat-rail.reveal{transition-delay:.08s}
.feature-card,.quick-card,.result-card,.process-card,.window{transform-style:preserve-3d;will-change:transform;transition:transform .32s cubic-bezier(.2,.8,.2,1),box-shadow .32s,border-color .22s}
.feature-card{box-shadow:0 4px 0 #c9c7c0,0 18px 35px #17181910}
.feature-card:hover{box-shadow:0 7px 0 #b7a577,0 27px 48px #1718191e}
.quick-card,.process-card{box-shadow:0 3px 0 #c9c7c0,0 10px 19px #1718190d}
.quick-card:hover,.process-card:hover{box-shadow:0 6px 0 #b7a577,0 20px 34px #17181918}
.result-card{box-shadow:0 3px 0 #c9c7c0,0 11px 22px #1718190d}
.result-card:hover{box-shadow:0 6px 0 #b7a577,0 22px 36px #1718191b}
.stat-pod.is-tilting,.feature-card.is-tilting,.quick-card.is-tilting,.result-card.is-tilting,.process-card.is-tilting{transform:perspective(900px) rotateX(var(--tilt-x,0deg)) rotateY(var(--tilt-y,0deg)) translateY(-4px) translateZ(8px)}
.window.is-tilting{transform:perspective(900px) rotateX(var(--tilt-x,0deg)) rotateY(var(--tilt-y,0deg)) translateZ(12px)!important}
.feature-card:before,.quick-card:before,.result-card:before,.process-card:before{position:absolute;inset:0;border-radius:inherit;background:radial-gradient(circle at var(--shine-x,90%) var(--shine-y,5%),#d8bd7c24,transparent 42%);content:"";opacity:0;pointer-events:none;transition:opacity .25s}
.feature-card,.quick-card,.result-card,.process-card{isolation:isolate}
.feature-card.is-tilting:before,.quick-card.is-tilting:before,.result-card.is-tilting:before,.process-card.is-tilting:before{opacity:1}
.hero-scene{filter:drop-shadow(0 28px 25px #0005)}
.window{box-shadow:0 16px 0 #0003,0 30px 60px #0007,0 0 0 1px #ffffff42}
.window-one{animation:window-one .9s .12s both,float-note 7s 1.1s ease-in-out infinite}
.window-two{animation:window-two .9s .28s both,float-note 8s 1.2s ease-in-out infinite reverse}
.window-three{animation:window-three .9s .42s both,float-note 7.5s 1.4s ease-in-out infinite}
.window.is-tilting{box-shadow:0 24px 15px #0005,0 38px 70px #0008,0 0 0 1px #d8bd7c70}
.chart-frame{box-shadow:0 4px 0 #c9c7c0,0 20px 42px #17181918,inset 0 1px #fff}
.chart-frame svg{filter:drop-shadow(0 5px 8px #0000000a)}
.point{animation-delay:calc(var(--point-order,0)*90ms)}
.kinetic-word{display:inline-block;opacity:0;transform:translateY(.35em) rotateX(-15deg);transform-origin:50% 100%;transition:opacity .48s cubic-bezier(.2,.8,.2,1),transform .55s cubic-bezier(.2,.8,.2,1),color .2s;transition-delay:calc(var(--word-index,0)*26ms);white-space:pre}
.text-entered .kinetic-word{opacity:1;transform:none}
.hero h1 .kinetic-word:hover,.page-title .kinetic-word:hover,.section-heading h2 .kinetic-word:hover{color:var(--lime);transform:translateY(-.06em)}
.hero h1>span .kinetic-word{color:var(--lime)}
.page-title>span .kinetic-word,.section-heading h2>span .kinetic-word{color:var(--blue)}
.reveal{opacity:0;transform:translateY(18px) scale(.99);transition:opacity .75s ease,transform .75s cubic-bezier(.16,1,.3,1)}
.reveal.visible{opacity:1;transform:none}
.grade{font-family:var(--sans);font-size:10px;letter-spacing:.035em;text-transform:none}.g-a,.g-b{background:#d8bd7c24;color:#947642}.g-c{background:#c9c9c324;color:#858787}.g-d,.g-f{background:#8e929324;color:#777b7d}
.result-card .result-grade{width:auto;height:auto;min-height:29px;border-radius:999px}
.metric-card b,.chart-stat>b,.feature-stats b,.result-values b{font-family:var(--sans);font-weight:700;letter-spacing:-.045em}
.feature-stats b{font-size:18px}.result-values b{font-size:12px}
.feature-stats small{font-family:var(--sans);font-size:10px}
.panel h2,.dialog-inner h2{font-family:var(--sans);font-weight:700;letter-spacing:-.05em}
.quick-card b,.process-card h3,.feature-main h3{font-family:var(--sans);font-weight:700;letter-spacing:-.045em}
.chart-point-link{outline:none}.chart-point-link:focus-visible .point{r:11;stroke:var(--lime);stroke-width:4}
.chart-legend{gap:7px}.legend-item{padding:7px 9px;font-size:10px}.legend-item b{font-size:9px}
.detail-stats{gap:14px}.metric-card{box-shadow:0 3px 0 #c9c7c0,0 10px 18px #1718190b}
.feature-aside{box-shadow:inset 1px 0 #fff2}
.button:focus-visible,.nav-links a:focus-visible,.nav-action:focus-visible,.nav-cta:focus-visible{outline:2px solid var(--blue);outline-offset:3px}
@media(max-width:850px){.stat-rail{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.stat-pod:nth-child(even){transform:none}.stat-pod:nth-child(even):hover{transform:translateY(-5px) rotate(1deg)}}
@media(max-width:620px){.stat-rail{gap:10px;padding-top:16px}.stat-pod{min-height:127px;padding:14px;border-radius:4px 16px 4px 16px}.stat-pod b{font-size:35px}.stat-pod>span{font-size:9px}.hero h1{font-size:clamp(53px,12vw,76px)}.page-title{font-size:clamp(42px,10vw,61px)}.section-heading h2{font-size:clamp(36px,9vw,49px)}.window-body h2{font-size:22px}.chart-frame{padding:8px}.legend-item{font-size:9px}.result-card{transform:none!important}}
@media(prefers-reduced-motion:reduce){.stat-pod,.feature-card,.quick-card,.result-card,.process-card,.window{will-change:auto}.stat-pod:hover,.feature-card:hover,.quick-card:hover,.result-card:hover,.process-card:hover{transform:none}.stat-pod.is-tilting,.feature-card.is-tilting,.quick-card.is-tilting,.result-card.is-tilting,.process-card.is-tilting,.window.is-tilting{transform:none!important}.window-one,.window-two,.window-three{animation:none}.kinetic-word{opacity:1;transform:none;transition:none}}
"""

CSS += r"""
.hero h1>span.kinetic-word{display:inline-block;color:#f6f7ed;font-style:normal}
.hero h1>span:not(.kinetic-word){display:block;color:var(--lime);font-style:normal}
.hero h1>span:not(.kinetic-word)>.kinetic-word{display:inline-block;color:var(--lime)}
.section-heading h2>span:not(.kinetic-word),.page-title>span:not(.kinetic-word){color:var(--blue);font-style:normal}
.section-heading h2>span:not(.kinetic-word)>.kinetic-word,.page-title>span:not(.kinetic-word)>.kinetic-word{color:var(--blue)}
.section-heading h2>.kinetic-word,.page-title>.kinetic-word{display:inline-block}
.stat-pod b{font-variant-numeric:tabular-nums}
"""

CSS += r"""
:root{color-scheme:light;--paper:#f5f2e9;--surface:#fffdf8;--ink:#191a1b;--muted:#70716e;--line:#d8d5cc;--navy:#171819;--navy-2:#383b3c;--mint:#c4c6c6;--lime:#d8bd7c;--blue:#a9874f;--blue-soft:#f0e8d7;--display:"Instrument Serif",Georgia,serif;--sans:"Bricolage Grotesque",Arial,sans-serif;--text:"Newsreader",Georgia,serif}
:root[data-theme=dark]{color-scheme:dark;--paper:#151616;--surface:#202222;--ink:#f4f1e9;--muted:#b4b1a8;--line:#414242;--navy:#101111;--navy-2:#292c2d;--mint:#bfc2c2;--lime:#d8bd7c;--blue:#dfc27e;--blue-soft:#343027}
body{font-family:var(--sans);font-size:16px;letter-spacing:-.012em}
h1,h2,.page-title,.section-heading h2,.feature-main h3,.chart-copy h2,.dialog-inner h2,.window-body h2{font-family:var(--display);font-weight:400;letter-spacing:-.035em}
h3,.quick-card b,.process-card h3{font-family:var(--display);font-weight:400;letter-spacing:-.025em}
.hero h1{font-size:clamp(68px,8.2vw,110px);font-weight:400;line-height:.88;letter-spacing:-.045em}
.hero h1>span:not(.kinetic-word),.section-heading h2>span:not(.kinetic-word),.page-title>span:not(.kinetic-word){font-style:italic}
.page-title{font-size:clamp(52px,7vw,86px);line-height:.94}
.section-heading h2{font-size:clamp(48px,6.1vw,76px);line-height:.96}
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.025em;text-transform:none}
.run-ledger{position:relative;display:grid;grid-template-columns:1.05fr .85fr 1.05fr .85fr 1.15fr;align-items:center;gap:0;margin:34px 0 15px;padding:22px 0 25px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);isolation:isolate}
.ledger-intro{align-self:start;padding:9px 22px 0 0}
.ledger-intro p{max-width:145px;margin:9px 0;color:var(--muted);font:italic 20px/1.1 var(--display)}
.ledger-stat{position:relative;display:flex;min-height:84px;align-items:center;gap:10px;padding:6px 15px;border-left:1px solid var(--line);color:var(--ink);text-decoration:none;transition:transform .35s cubic-bezier(.2,.8,.2,1),color .2s}
.ledger-stat:hover{z-index:2;color:var(--blue);transform:translateY(-5px) rotate(-1deg)}
.ledger-stat b{position:relative;z-index:1;font:400 clamp(36px,4vw,58px)/.9 var(--display);letter-spacing:-.035em}
.ledger-stat span,.ledger-stat small{font-size:11px;line-height:1.4;color:var(--muted)}
.ledger-scale{align-items:flex-start;justify-content:center;flex-direction:column;transform:translateY(8px)}
.ledger-scale b{font-size:25px}
.ledger-signal{gap:7px;isolation:isolate}
.ledger-signal b{font-size:46px}
.signal-orbit{position:absolute;inset:50% auto auto 50%;z-index:0;width:68px;height:68px;border:1px solid color-mix(in srgb,var(--blue),transparent 40%);border-radius:50%;transform:translate(-50%,-50%);animation:orbit-turn 11s linear infinite}
.signal-orbit:after{position:absolute;top:3px;left:8px;width:7px;height:7px;border-radius:50%;background:var(--lime);content:""}
.ledger-suite{align-items:flex-end;flex-direction:column;justify-content:center;text-align:right}
.ledger-suite b{font-size:40px}
.feature-card{overflow:hidden;border:1px solid var(--line);border-radius:4px 44px 4px 44px;background:var(--surface)}
.feature-main{position:relative;padding:clamp(24px,4vw,52px)}
.feature-top{display:flex;align-items:center;gap:16px;color:var(--muted);font-size:12px}
.feature-grade{margin-left:auto;color:var(--blue);font:italic 54px/.75 var(--display);transform:rotate(8deg)}
.feature-main h3{max-width:620px;margin:24px 0 10px;font-size:clamp(38px,5.3vw,68px);line-height:.95}
.feature-main>p{max-width:520px;font-size:14px;line-height:1.7}
.feature-stats{margin-top:32px}
.feature-stats>div{border-left:1px solid var(--line)}
.feature-stats small{font-size:11px}
.feature-stats b{font:400 25px/1 var(--display);letter-spacing:-.02em}
.feature-aside{justify-content:space-between;padding:clamp(22px,3vw,42px);border-left:1px solid var(--line);background:linear-gradient(155deg,var(--surface),color-mix(in srgb,var(--surface),var(--blue-soft) 26%))}
.feature-note{max-width:200px;font:italic 22px/1.2 var(--display)}
.feature-note p{margin:0}
.feature-estimate strong{display:block;color:var(--blue);font:italic clamp(55px,7vw,82px)/.9 var(--display);letter-spacing:-.045em}
.feature-estimate p{margin:9px 0 16px;color:var(--muted);font-size:13px}
.quick-links{grid-template-columns:1.15fr .9fr 1fr;align-items:stretch;gap:16px;margin-top:30px}
.quick-card{position:relative;min-height:190px;padding:23px;border:1px solid var(--line);border-radius:3px 30px 3px 3px;background:var(--surface)}
.quick-card--1{min-height:224px;border-radius:38px 3px 3px 3px;background:linear-gradient(140deg,var(--surface),var(--blue-soft))}
.quick-card--2{margin-top:24px;border-radius:3px 3px 38px 3px}
.quick-card--3{transform:translateY(-8px) rotate(.6deg)}
.quick-kicker{max-width:130px;color:var(--muted);font:italic 18px/1.1 var(--display)}
.quick-card b{display:block;max-width:230px;margin-top:24px;font-size:29px;line-height:.98}
.quick-card small{max-width:230px;margin-top:14px;font-size:12px}
.quick-arrow{position:absolute;top:20px;right:20px;color:var(--blue);font-size:20px;transition:transform .3s}
.quick-card:hover .quick-arrow{transform:translate(5px,-5px) rotate(45deg)}
.process-grid{grid-template-columns:repeat(5,minmax(0,1fr));gap:15px}
.process-card{position:relative;display:flex;min-height:190px;flex-direction:column;justify-content:space-between;overflow:visible;padding:18px 14px 18px 0;border:0;border-top:1px solid var(--line);border-radius:0;background:transparent;box-shadow:none}
.process-card:nth-child(even){transform:translateY(22px)}
.process-card:hover,.process-card:nth-child(even):hover{transform:translateY(-5px) rotate(-1deg);box-shadow:none}
.process-mark{display:grid;width:44px!important;height:44px!important;min-height:0!important;place-items:center;padding:0!important;border:0!important;border-radius:0!important;background:transparent!important;box-shadow:none!important;color:var(--blue);font:italic 35px/.8 var(--display);transform:rotate(-9deg);transition:transform .45s cubic-bezier(.2,.8,.2,1),color .2s}
.process-card:nth-child(2) .process-mark{font-size:42px;transform:rotate(12deg)}
.process-card:nth-child(3) .process-mark{font-size:31px;transform:rotate(-20deg)}
.process-card:nth-child(4) .process-mark{font-size:35px}
.process-card:nth-child(5) .process-mark{font-size:38px;transform:rotate(7deg)}
.process-card:hover .process-mark{color:var(--lime);transform:rotate(22deg) scale(1.16)}
.process-card h3{margin:20px 0 7px;font-size:30px}
.process-card p{max-width:190px;font-size:12px;line-height:1.6}
.process-grid:not(.process-journey) .process-card{min-height:150px}
.result-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.result-card{display:grid;grid-template-columns:64px minmax(0,1fr);align-items:start;gap:13px;min-height:212px;padding:24px;border:1px solid var(--line);border-radius:3px 28px 3px 3px;background:var(--surface);text-decoration:none}
.result-card:nth-child(3n+2){grid-template-columns:minmax(0,1fr) 64px;border-radius:28px 3px 3px 3px;background:linear-gradient(135deg,var(--surface),var(--blue-soft))}
.result-card:nth-child(3n+2) .result-content{order:1}
.result-card:nth-child(3n+2) .result-grade{order:2}
.result-card:nth-child(3n){border-radius:3px 3px 28px 3px}
.result-grade{display:grid;width:auto;height:auto;min-height:0;place-items:center;border:0;border-radius:0;background:none!important;color:var(--blue)!important;font:italic 58px/.8 var(--display);transition:transform .4s}
.result-card:hover .result-grade{transform:rotate(-11deg) scale(1.14)}
.result-content{min-width:0}
.result-topline{display:flex;align-items:center;justify-content:space-between;min-height:24px;color:var(--muted);font-size:11px}
.result-arrow{color:var(--blue);font-size:19px;transition:transform .25s}
.result-card:hover .result-arrow{transform:translate(4px,-4px)}
.result-card h3{max-width:400px;margin:12px 0 7px;font:italic 31px/.98 var(--display);letter-spacing:-.02em}
.result-card p{min-height:32px;margin:0;color:var(--muted);font-size:12px}
.result-lead{display:flex;align-items:baseline;gap:9px;margin:15px 0 7px}
.result-lead b{color:var(--ink);font:400 27px/.9 var(--display)}
.result-lead span{color:var(--muted);font-size:10px}
.result-footnote{color:var(--muted);font-size:10px}
.result-footnote i{padding:0 4px;color:var(--blue);font-style:normal}
.filter[data-filter="A"],.filter[data-filter="B"],.filter[data-filter="C"],.filter[data-filter="D"],.filter[data-filter="F"]{min-width:43px;font:italic 19px var(--display)}
.filter span{font:500 10px var(--sans)}
.detail-hero{position:relative;padding:clamp(26px,5vw,62px);border-radius:3px 56px 3px 3px;background:var(--navy);color:var(--paper)}
.detail-hero:after{position:absolute;right:6%;bottom:-80px;width:250px;height:250px;border:1px solid #d8bd7c55;border-radius:50%;box-shadow:0 0 0 18px #d8bd7c0a,0 0 0 42px #d8bd7c07;content:"";pointer-events:none}
.detail-hero h1{max-width:790px;font-size:clamp(47px,7vw,88px);line-height:.92}
.detail-grade{display:inline-block;margin-right:4px;color:var(--lime);font:italic 24px/.8 var(--display)}
.detail-meta{position:relative;z-index:1}
.detail-signals{display:grid;grid-template-columns:.85fr 1.7fr;align-items:center;gap:40px;margin:24px 0 48px;padding:26px 0;border-bottom:1px solid var(--line)}
.detail-forecast{display:flex;flex-direction:column;align-items:flex-start;gap:5px}
.detail-forecast span,.detail-forecast small{color:var(--muted);font-size:11px}
.detail-forecast strong{color:var(--blue);font:italic clamp(62px,8vw,95px)/.8 var(--display);letter-spacing:-.04em}
.detail-ledger{display:flex;justify-content:space-between;gap:16px}
.detail-ledger p{display:flex;flex-direction:column;gap:5px;margin:0;padding-left:17px;border-left:1px solid var(--line)}
.detail-ledger b{font:italic 30px/.9 var(--display);font-weight:400}
.detail-ledger span{max-width:130px;color:var(--muted);font-size:10px}
.chart-legend{align-items:flex-start;gap:4px}
.legend-item{align-items:center;min-height:35px;padding:5px 8px;border:0;border-bottom:1px solid var(--line);border-radius:0;background:transparent}
.legend-item span{font-size:10px}
.legend-item b{display:grid;width:20px;height:22px;place-items:center;border:0;border-radius:50%;background:transparent;color:var(--blue);font:italic 18px var(--display)}
.chart-note-rail{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:25px;margin-top:28px}
.chart-note-rail p{display:flex;align-items:center;gap:13px;margin:0;padding:13px 0;border-top:1px solid var(--line)}
.chart-note-rail p>b{color:var(--blue);font:italic 31px/.8 var(--display)}
.chart-note-rail p>span{display:flex;flex-direction:column;font-size:12px}
.chart-note-rail small{color:var(--muted);font-size:10px}
.chart-note-rail i{width:26px;border-top:1px dashed var(--blue)}
.pilot-notes{display:grid;grid-template-columns:1.2fr 1fr .9fr;align-items:center;gap:22px;margin-top:34px;padding:20px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.pilot-notes p{display:flex;flex-direction:column;align-items:flex-start;margin:0}
.pilot-notes p+ p{padding-left:22px;border-left:1px solid var(--line)}
.pilot-notes strong{color:var(--blue);font:italic clamp(32px,4vw,50px)/.95 var(--display);font-weight:400}
.pilot-notes span{margin:4px 0;font-size:13px}
.pilot-notes small{max-width:235px;color:var(--muted);font-size:11px;line-height:1.5}
.chart-frame{border-radius:38px 4px 4px 4px;background:var(--surface)}
.chart-frame .diag{stroke-dasharray:900;stroke-dashoffset:900;animation:draw-chart 1.5s .25s ease-out forwards}
.chart-frame .point{transform-box:fill-box;transform-origin:center;animation:point-arrive .55s both;animation-delay:calc(var(--point-order,0)*90ms)}
.hero-scene .window{width:min(310px,78%);border-radius:8px 26px 8px 8px}
.hero-scene .window-one{top:12px;left:1%;z-index:4}
.hero-scene .window-two{top:148px;right:0;z-index:3}
.hero-scene .window-three{bottom:0;left:5%;z-index:2}
.hero-scene .window:hover{z-index:5;animation-play-state:paused!important}
.window-body{padding:16px 18px 18px}
.window-body small{font-family:var(--sans);font-size:11px;letter-spacing:.02em;text-transform:none}
.window-body h2{margin-top:8px;font-size:27px;font-style:italic}
.window-two .window-bar{justify-content:space-between;border:0;background:#e4e0d6;color:#343536;font-size:11px}
.window-two .window-dots{display:none}
.window-two .window-body{background-color:#f8f6ee;background-image:linear-gradient(#172b3b0c 1px,transparent 1px);background-size:100% 23px}
.window-three{border-color:#d8bd7c;background:#202222;color:#f4f1e9}
.window-three .window-bar{border:0;background:#d8bd7c;color:#171819}
.window-three .window-dots{display:none}
.window-three .window-controls button{color:#171819}
.window-three .window-body{background:linear-gradient(145deg,#303233,#171819)}
.window-three .window-body small{color:#e0c782}
.window-three .window-body h2{color:#f5f2e9}
.window-three .window-body p{color:#c6c6c1}
.process-card:nth-child(odd) .process-mark{animation:mark-breathe 4.8s ease-in-out infinite}
.process-card:nth-child(even) .process-mark{animation:mark-tilt 5.4s ease-in-out infinite}
.process-card:nth-child(3n) .process-mark{animation-delay:.7s}
.process-card:nth-child(4n) .process-mark{animation-delay:1.2s}
.check{padding:5px 0!important;border:0!important;border-bottom:1px solid var(--line)!important;border-radius:0!important;background:transparent!important}
.check.hit{color:var(--blue)}
.legend-item i{background:var(--lime)!important}
.legend-item i.g-c{background:#aaa9a1!important}
.legend-item i.g-d,.legend-item i.g-f{background:#777976!important}
.chart-frame .point.g-a,.chart-frame .point.g-b{fill:var(--blue)}
.chart-frame .point.g-c{fill:#aaa9a1}
.chart-frame .point.g-d,.chart-frame .point.g-f{fill:#777976}
.nav-links a,.nav-cta,.button{font-family:var(--sans)}

@keyframes orbit-turn{to{transform:translate(-50%,-50%) rotate(360deg)}}
@keyframes draw-chart{to{stroke-dashoffset:0}}
@keyframes point-arrive{0%{opacity:0;transform:scale(.3)}70%{transform:scale(1.25)}100%{opacity:1;transform:scale(1)}}
@keyframes mark-breathe{0%,100%{transform:translateY(0) rotate(-8deg)}50%{transform:translateY(-5px) rotate(5deg)}}
@keyframes mark-tilt{0%,100%{transform:translateX(0) rotate(10deg)}50%{transform:translateX(4px) rotate(-9deg)}}
@media(max-width:900px){.run-ledger{grid-template-columns:1fr 1fr 1fr;row-gap:12px}.ledger-intro{grid-column:span 3}.ledger-stat:nth-of-type(4){border-left:0}.process-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.process-grid:not(.process-journey){grid-template-columns:repeat(3,minmax(0,1fr))}.process-card:nth-child(even){transform:none}.feature-card{grid-template-columns:1fr 220px}}
@media(max-width:680px){.hero h1{font-size:clamp(60px,13vw,84px)}.page-title{font-size:clamp(47px,11vw,66px)}.run-ledger{grid-template-columns:1fr 1fr;gap:0;padding:18px 0}.ledger-intro{grid-column:span 2}.ledger-stat{min-height:76px;padding:8px 10px;border-left:0;border-top:1px solid var(--line)}.ledger-stat:nth-of-type(even){border-left:1px solid var(--line)}.ledger-scale{transform:none}.ledger-signal{min-height:92px}.feature-card{grid-template-columns:1fr}.feature-aside{min-height:200px;flex-direction:row;border-top:1px solid var(--line);border-left:0}.feature-note{max-width:135px}.quick-links{grid-template-columns:1fr 1fr;gap:11px}.quick-card,.quick-card--1{min-height:175px}.quick-card--2,.quick-card--3{margin:0;transform:none}.quick-card--3{grid-column:span 2;min-height:150px}.quick-card b{font-size:26px}.process-grid,.process-grid:not(.process-journey){grid-template-columns:1fr 1fr;gap:12px}.process-card{min-height:158px}.result-grid{grid-template-columns:1fr}.result-card{min-height:190px}.detail-signals{grid-template-columns:1fr;gap:22px}.detail-ledger{gap:8px}.detail-ledger p{padding-left:10px}.detail-ledger b{font-size:25px}.chart-note-rail{grid-template-columns:1fr;gap:0}.pilot-notes{grid-template-columns:1fr 1fr;gap:15px}.pilot-suite{grid-column:span 2}.pilot-notes p+ p{padding-left:15px}.pilot-suite{padding:10px 0 0;border-top:1px solid var(--line)}}
@media(max-width:420px){.run-ledger{margin-top:18px}.ledger-stat span,.ledger-stat small{font-size:10px}.feature-stats{grid-template-columns:1fr 1fr;gap:15px}.feature-stats>div{padding-left:9px}.quick-links{grid-template-columns:1fr}.quick-card--3{grid-column:auto}.process-grid,.process-grid:not(.process-journey){grid-template-columns:1fr}.process-card{min-height:130px}.process-mark{width:35px;height:35px}.result-card{grid-template-columns:45px minmax(0,1fr);gap:8px;padding:17px}.result-card:nth-child(3n+2){grid-template-columns:minmax(0,1fr) 45px}.result-grade{font-size:46px}.result-card h3{font-size:27px}.detail-ledger{flex-wrap:wrap}.detail-ledger p{min-width:28%}}
@media(prefers-reduced-motion:reduce){.ledger-stat,.signal-orbit,.process-mark,.result-grade,.quick-arrow,.chart-frame .diag,.chart-frame .point{animation:none!important;transition:none!important}.chart-frame .diag{stroke-dashoffset:0}.chart-frame .point{opacity:1;transform:none}}
"""

CSS += r"""
.plain-brief{display:grid;grid-template-columns:.8fr 1.5fr;gap:clamp(28px,6vw,82px);align-items:start;margin:35px 0 12px;padding:clamp(24px,4vw,48px);border:1px solid var(--line);border-radius:4px 38px 4px 4px;background:linear-gradient(125deg,var(--surface),var(--blue-soft))}
.plain-brief-intro{position:sticky;top:110px}
.plain-brief-intro .eyebrow{margin-bottom:20px}
.plain-brief-intro h2{max-width:330px;margin:0;font:italic 400 clamp(38px,5vw,58px)/.93 var(--display);letter-spacing:-.03em}
.plain-brief-intro>p:last-child{max-width:310px;margin:19px 0 0;color:var(--muted);font-size:14px;line-height:1.75}
.plain-brief-copy{max-width:690px}
.plain-brief-copy>p{margin:0 0 20px;font-size:clamp(17px,2vw,21px);line-height:1.6}
.plain-brief-copy>p strong{font-weight:700}
.plain-steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;margin-top:27px}
.plain-step{position:relative;min-height:158px;padding:16px 14px 14px 0;border-top:1px solid color-mix(in srgb,var(--blue),transparent 40%);transition:transform .28s}
.plain-step:hover{transform:translateY(-5px)}
.plain-step-mark{display:block;margin-bottom:16px;color:var(--blue);font:italic 26px/.8 var(--display)}
.plain-step h3{margin:0 0 7px;font:italic 400 24px/1 var(--display)}
.plain-step p{margin:0;color:var(--muted);font-size:12px;line-height:1.6}
.why-buy{display:grid;grid-template-columns:1.1fr 1fr 1fr 1fr;gap:20px;align-items:start;margin:35px 0 5px;padding:25px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.why-buy h3{max-width:190px;margin:0;font:italic 400 30px/.98 var(--display)}
.why-buy p{margin:0;color:var(--muted);font-size:13px;line-height:1.65}
.why-buy p strong{display:block;margin-bottom:5px;color:var(--ink);font-weight:650}
.run-ledger .eyebrow{margin:0}
.run-ledger .ledger-intro p{max-width:190px}
.plain-brief .eyebrow{font-size:10px}
.sample-caveat{margin:-1px 0 0;padding:0 10px 20px;color:var(--muted);font-size:11px;line-height:1.55}
.run-ledger .ledger-signal>span:last-child{max-width:125px}
.feature-main>p{max-width:600px;font-size:14px;line-height:1.7}
.feature-stats small{max-width:130px;line-height:1.45}
.grade-explainer{margin:18px 0 0!important;color:var(--muted);font-size:11px!important;line-height:1.6!important}
.feature-estimate>small{display:block;max-width:200px;margin-top:5px;color:var(--muted);font-size:10px;line-height:1.4}
.home-method-link{display:inline-flex;align-items:center;gap:8px;margin-top:24px;color:var(--blue);font-size:12px;font-weight:650;text-decoration:none}
.home-method-link:hover{text-decoration:underline;text-underline-offset:4px}
.scale-caveat{margin:18px 0;color:var(--muted);font-size:12px;line-height:1.7}
.scale-caveat strong{color:var(--ink)}
@media(max-width:850px){.plain-brief{grid-template-columns:1fr;gap:20px}.plain-brief-intro{position:static}.plain-brief-intro h2{max-width:520px}.plain-brief-intro>p:last-child{max-width:600px}.why-buy{grid-template-columns:1fr 1fr}.why-buy h3{max-width:260px}}
@media(max-width:560px){.plain-brief{padding:22px;border-radius:4px 28px 4px 4px}.plain-steps{grid-template-columns:1fr;gap:5px}.plain-step{min-height:0;padding:13px 0}.plain-step-mark{float:right;margin:4px 4px 0 14px}.why-buy{grid-template-columns:1fr;gap:16px}.why-buy h3{max-width:none}.why-buy p{max-width:360px}.run-ledger .ledger-intro p{max-width:220px}}

.feature-aside{position:relative;display:flex;flex-direction:column;align-items:stretch;gap:30px;overflow:hidden;background:#222324;color:#f4f3ef}
.feature-aside:before{position:absolute;top:-105px;right:-110px;width:250px;height:250px;border:1px solid #d8bd7c45;border-radius:50%;box-shadow:0 0 0 20px #d8bd7c0a,0 0 0 48px #d8bd7c08;content:"";animation:aside-orbit 22s linear infinite;pointer-events:none}
.feature-note{position:relative;z-index:1;max-width:none;font:normal 16px/1.5 var(--sans)}
.feature-note-head{display:flex;align-items:center;gap:12px}
.feature-note-orbit{display:grid;width:36px;height:36px;flex:none;place-items:center;border:1px solid #d8bd7c80;border-radius:50%;color:var(--lime);font-size:17px;animation:proof-orbit 5s ease-in-out infinite}
.proof-label{color:#d2c19a;font:600 10px/1.3 var(--mono);letter-spacing:.1em;text-transform:uppercase}
.feature-proof-number{display:block;margin:22px 0 4px;color:#f5f2e9;font:italic 400 clamp(66px,8vw,100px)/.8 var(--display);letter-spacing:-.06em;animation:proof-rise .9s .18s both}
.feature-proof-number span{margin-left:7px;color:var(--lime);font:500 17px var(--sans);letter-spacing:0}
.feature-note>p{max-width:265px;margin:12px 0 0;color:#e3e1da;font:500 16px/1.5 var(--sans)}
.forecast-caveat{display:grid;grid-template-columns:28px 1fr;align-items:start;gap:10px;margin-top:24px;padding:15px 15px 15px 12px;border:1px solid #d8bd7c54;border-radius:3px 16px 3px 16px;background:linear-gradient(115deg,#d8bd7c20,#ffffff06);box-shadow:0 8px 20px #0002;animation:caveat-arrive .8s .45s both}
.caveat-spark{display:grid;width:25px;height:25px;place-items:center;border-radius:50%;background:var(--lime);color:#171819;font-size:13px;animation:spark-turn 8s linear infinite}
.forecast-caveat b{display:block;margin:0 0 4px;color:#f4e4b7;font:600 13px/1.35 var(--sans)}
.forecast-caveat small{display:block;max-width:340px;color:#d0cfca;font:400 12px/1.55 var(--sans)}
.feature-estimate{position:relative;z-index:1;padding-top:22px;border-top:1px solid #ffffff24}
.feature-estimate strong{font-size:clamp(48px,6vw,68px)}
.result-card p{min-height:42px;color:var(--ink);font-size:13px;line-height:1.55}
.result-topline>span:first-child{font-weight:600;letter-spacing:.015em}
.result-lead{padding-top:11px;border-top:1px solid var(--line)}
.plain-step:nth-child(2),.why-buy>*:nth-child(2),.process-card:nth-child(2){transition-delay:.12s}
.plain-step:nth-child(3),.why-buy>*:nth-child(3),.process-card:nth-child(3){transition-delay:.24s}
.why-buy>*:nth-child(4),.process-card:nth-child(4){transition-delay:.36s}
.process-card:nth-child(5){transition-delay:.48s}
.kinetic-word{filter:blur(3px);transition-duration:.6s;transition-delay:calc(var(--word-index,0)*14ms)}
.text-entered .kinetic-word{filter:blur(0)}
.kinetic-word:hover{animation:word-pop .38s cubic-bezier(.2,.8,.2,1)}
@keyframes aside-orbit{to{transform:rotate(360deg)}}
@keyframes proof-orbit{0%,100%{transform:translateY(0) rotate(-8deg)}50%{transform:translateY(-5px) rotate(12deg)}}
@keyframes proof-rise{from{opacity:0;filter:blur(8px);transform:translateY(24px) scale(.92)}to{opacity:1;filter:blur(0);transform:none}}
@keyframes caveat-arrive{from{opacity:0;transform:translateX(18px)}to{opacity:1;transform:none}}
@keyframes spark-turn{to{transform:rotate(360deg)}}
@keyframes word-pop{50%{transform:translateY(-.1em) rotate(-3deg)}}
@media(max-width:900px){.feature-aside{gap:22px}.feature-note>p{max-width:520px}}
@media(max-width:560px){.feature-aside{padding:24px 22px}.feature-proof-number{font-size:76px}.forecast-caveat{margin-top:20px}.feature-estimate{padding-top:18px}}
@media(prefers-reduced-motion:reduce){.feature-aside:before,.feature-note-orbit,.feature-proof-number,.forecast-caveat,.caveat-spark,.plain-step,.why-buy>*,.process-card{animation:none!important}.feature-proof-number{opacity:1;filter:none;transform:none}.kinetic-word{filter:none}}
"""

CSS += r"""
:root{--gain:#b07f22;--loss:#3f78ad;--risk:#a2502f;--spring:cubic-bezier(.34,1.56,.64,1);--out:cubic-bezier(.16,1,.3,1)}
:root[data-theme=dark]{--gain:#b88a2c;--loss:#5a92d6;--risk:#d9825f}
body{animation:page-in .5s ease-out both}main{animation:main-in .7s var(--out) both}
body.is-leaving{opacity:0;transition:opacity .18s ease-in}
.scroll-progress{position:absolute;right:0;bottom:-1px;left:0;height:2px;background:linear-gradient(90deg,var(--lime),var(--blue));transform:scaleX(var(--progress,0));transform-origin:left;pointer-events:none}
::view-transition-old(root),::view-transition-new(root){animation:none;mix-blend-mode:normal}
::view-transition-new(root){animation:theme-reveal .7s var(--out)}
.nav-action[data-theme-toggle]{transition:transform .5s var(--spring),border-color .2s}.nav-action[data-theme-toggle].is-turning{transform:rotate(180deg)}
.nav-search{display:flex;align-items:center;gap:9px;height:38px;padding:0 6px 0 13px;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--muted);font-size:11px;cursor:pointer;transition:border-color .2s,color .2s,transform .2s}
.nav-search:hover{border-color:var(--blue);color:var(--ink);transform:translateY(-2px)}
kbd{display:inline-grid;min-width:22px;height:22px;place-items:center;padding:0 6px;border:1px solid var(--line);border-bottom-width:2px;border-radius:6px;background:var(--paper);color:var(--muted);font:500 10px var(--mono)}

/* buttons: one family, several temperaments */
.button{position:relative;overflow:hidden;isolation:isolate;translate:var(--mx,0) var(--my,0);transition:transform .22s,background .22s,border-color .22s,box-shadow .22s,color .22s,translate .25s var(--out)}
.button:active{transform:translateY(1px) scale(.98)}
.button-lime:before{position:absolute;inset:0;z-index:-1;background:linear-gradient(110deg,transparent 30%,#ffffffa0 48%,transparent 66%);content:"";transform:translateX(-120%);transition:transform .75s var(--out)}
.button-lime:hover:before{transform:translateX(120%)}
.button-ink{gap:14px;padding:0 5px 0 20px;background:var(--ink);color:var(--paper)}
.button-ink:hover{background:color-mix(in srgb,var(--ink),var(--blue) 25%)}
.button-orb{display:grid;width:36px;height:36px;place-items:center;border-radius:50%;background:var(--lime);color:#171819;font-size:15px;transition:transform .45s var(--spring)}
.button-ink:hover .button-orb{transform:rotate(45deg) scale(1.08)}
.button-outline{border-color:currentColor;background:transparent;color:var(--ink)}
.button-outline:after{position:absolute;inset:0;z-index:-1;background:var(--ink);content:"";transform:scaleX(0);transform-origin:right;transition:transform .4s var(--out)}
.button-outline:hover{color:var(--paper)}.button-outline:hover:after{transform:scaleX(1);transform-origin:left}
.button-ring{gap:12px;border-color:#ffffff40;background:transparent;color:#f6f7ed}
.button-ring .button-arrow{display:grid;width:28px;height:28px;place-items:center;border:1px solid currentColor;border-radius:50%;font-size:13px;transition:transform .5s var(--spring)}
.button-ring:hover{border-color:var(--lime);color:var(--lime)}.button-ring:hover .button-arrow{transform:translateY(3px) rotate(360deg)}
.button-kbd{gap:10px;border-color:#ffffff2e;background:#ffffff0d;color:#c5d0cf}.button-kbd:hover{background:#ffffff1a;color:#fff}
.button-kbd kbd{border-color:#ffffff30;background:#ffffff12;color:#e8e6dc}
.ripple{position:absolute;z-index:0;width:var(--size);height:var(--size);border-radius:50%;background:currentColor;opacity:.22;pointer-events:none;transform:translate(-50%,-50%) scale(0);animation:ripple .6s ease-out forwards}
.section-link{background:linear-gradient(currentColor,currentColor) left bottom/0 1px no-repeat;padding-bottom:2px;transition:gap .25s,background-size .35s var(--out)}
.section-link:hover{background-size:100% 1px}
.peek-button{position:relative;z-index:2;display:inline-flex;align-items:center;gap:8px;padding:7px 12px 7px 9px;border:1px solid var(--ink);border-radius:8px;background:var(--surface);color:var(--ink);font-size:11px;font-weight:650;cursor:pointer;box-shadow:3px 3px 0 var(--ink);transition:transform .18s,box-shadow .18s,background .2s}
.peek-button:hover{background:var(--lime);color:#171819;transform:translate(-1px,-1px);box-shadow:4px 4px 0 var(--ink)}
.peek-button:active{transform:translate(2px,2px);box-shadow:1px 1px 0 var(--ink)}
.peek-eye{position:relative;width:16px;height:10px;border:1.5px solid currentColor;border-radius:50%/60%}
.peek-eye:after{position:absolute;top:50%;left:50%;width:4px;height:4px;border-radius:50%;background:currentColor;content:"";transform:translate(-50%,-50%);transition:transform .3s var(--spring)}
.peek-button:hover .peek-eye:after{transform:translate(-10%,-50%) scale(1.3)}
.info-chip{position:relative;z-index:3;display:grid;width:26px;height:26px;flex:none;place-items:center;padding:0;border:1px solid color-mix(in srgb,var(--blue),transparent 45%);border-radius:50%;background:var(--surface);color:var(--blue);font-size:15px;line-height:1;cursor:pointer;transition:transform .4s var(--spring),background .2s,color .2s}
.info-chip:before{position:absolute;inset:-5px;border:1px solid var(--blue);border-radius:50%;content:"";opacity:0;animation:chip-ping 2.8s 1.5s ease-out 2}
.info-chip:hover{background:var(--blue);color:var(--surface);transform:scale(1.12)}
.info-chip[aria-expanded=true]{background:var(--ink);color:var(--paper);transform:rotate(45deg)}
.button:focus-visible,.peek-button:focus-visible,.info-chip:focus-visible,.pop-tab:focus-visible,.board-row:focus-visible,.nav-search:focus-visible{outline:2px solid var(--blue);outline-offset:3px}

/* floating windows */
.pop-window{position:fixed;top:90px;left:calc(50% - 220px);z-index:60;display:flex;width:min(450px,calc(100vw - 24px));max-height:min(80vh,660px);flex-direction:column;overflow:hidden;border:1px solid var(--line);border-radius:10px 26px 10px 10px;background:var(--surface);color:var(--ink);box-shadow:0 3px 0 #0000000d,0 30px 80px #0b0c0d45;transform-origin:var(--origin-x,50%) var(--origin-y,0%)}
.pop-window.is-wide{width:min(560px,calc(100vw - 24px))}
.pop-window[hidden]{display:none}
.pop-window.is-front{z-index:61;box-shadow:0 3px 0 #0000000d,0 34px 90px #0b0c0d55,0 0 0 1px color-mix(in srgb,var(--blue),transparent 55%)}
.pop-window.is-opening{animation:pop-open .55s var(--spring) both}
.pop-window.is-closing{animation:pop-close .22s ease-in both}
.pop-window.is-dragging{cursor:grabbing;user-select:none}
.pop-bar{display:flex;align-items:center;gap:11px;padding:9px 10px 9px 13px;border-bottom:1px solid var(--line);background:repeating-linear-gradient(0deg,color-mix(in srgb,var(--paper),var(--line) 25%) 0 1px,var(--paper) 1px 3px);cursor:grab;touch-action:none;user-select:none}
.pop-title{flex:1;min-width:0;overflow:hidden;color:var(--muted);font-size:11px;font-weight:600;text-overflow:ellipsis;white-space:nowrap}
.lights{display:flex;flex:none;gap:7px}
.light{position:relative;display:grid;width:12px;height:12px;place-items:center;padding:0;border:0;border-radius:50%;background:#ed6a5e;box-shadow:inset 0 0 0 .5px #0000002e;cursor:pointer}
.light.is-min{background:#f5bf4f}.light.is-zoom{background:#61c554}
.light:after{color:#4d0000a8;font:700 9px/1 var(--sans);content:"";opacity:0}
.light.is-close:after{content:"×";font-size:11px}.light.is-min:after{content:"−";color:#5a3a00b3}.light.is-zoom:after{content:"+";color:#003d00a8}
.lights:hover .light:after,.light:focus-visible:after{opacity:1}
.light:active{filter:brightness(.82)}
.light:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.window-bar .lights{gap:6px}.window-bar .light{width:10px;height:10px}.window-bar .light:after{font-size:8px}.window-bar .light.is-close:after{font-size:9px}
.window-spacer{width:46px}
.pop-window.is-zoomed{top:72px!important;left:calc(50% - min(450px,50vw - 24px))!important;width:min(900px,calc(100vw - 48px));max-height:calc(100vh - 96px)}
.pop-window.is-zoomed .pop-body{padding:24px 28px 28px}
.pop-dock{position:fixed;bottom:0;left:20px;z-index:58;display:flex;align-items:flex-end;gap:3px;max-width:calc(100vw - 400px);overflow-x:auto;pointer-events:none;scrollbar-width:none}
.dock-tab{position:relative;display:flex;align-items:center;gap:8px;min-width:0;max-width:220px;height:34px;padding:0 6px 0 12px;border:1px solid var(--line);border-bottom:0;border-radius:9px 9px 0 0;background:var(--surface);color:var(--ink);box-shadow:0 -6px 18px #0b0c0d14;cursor:pointer;pointer-events:auto;transform-origin:50% 100%;transition:transform .15s,background .15s}
.dock-tab:hover{transform:translateY(-3px);background:color-mix(in srgb,var(--surface),var(--blue-soft) 60%)}
.dock-tab:before{flex:none;width:7px;height:7px;border-radius:50%;background:#f5bf4f;content:""}
.dock-tab span{overflow:hidden;font-size:11px;font-weight:600;text-overflow:ellipsis;white-space:nowrap}
.dock-tab button{display:grid;flex:none;width:20px;height:20px;place-items:center;padding:0;border:0;border-radius:5px;background:transparent;color:var(--muted);font-size:13px;cursor:pointer}
.dock-tab button:hover{background:var(--ink);color:var(--paper)}
.dock-tab:focus-visible{outline:2px solid var(--blue);outline-offset:-2px}
@media(max-width:680px){.pop-dock{right:8px;left:8px;max-width:none}.dock-tab{max-width:160px}}
.pop-tabs{position:relative;display:flex;gap:2px;padding:7px 10px 0;border-bottom:1px solid var(--line);background:var(--surface)}
.pop-tab{position:relative;z-index:1;padding:8px 13px 11px;border:0;border-radius:10px 10px 0 0;background:transparent;color:var(--muted);font-size:12px;font-weight:650;cursor:pointer;transition:color .2s,background .2s}
.pop-tab:hover{background:var(--blue-soft);color:var(--ink)}.pop-tab[aria-selected=true]{color:var(--ink)}
.pop-tab-ink{position:absolute;bottom:-1px;left:0;width:var(--ink-w,0);height:3px;border-radius:3px 3px 0 0;background:var(--blue);transform:translateX(var(--ink-x,0));transition:transform .5s var(--spring),width .5s var(--spring)}
.pop-body{overflow:auto;padding:18px 18px 20px;overscroll-behavior:contain}
.pop-panel.is-active{animation:panel-in .42s var(--out) both}
.pop-lead{display:flex;align-items:center;gap:14px}
.pop-grade{display:grid;width:56px;height:56px;flex:none;place-items:center;border-radius:50%;background:var(--ink);color:var(--lime);font:italic 34px/1 var(--display);animation:grade-stamp .7s .1s var(--spring) both}
.pop-heading{display:block;font:italic 400 29px/1 var(--display);letter-spacing:-.02em}
.pop-kicker{display:block;margin-top:5px;color:var(--muted);font-size:11px}
.pop-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:16px 0}
.pop-stat{padding:10px 11px;border:1px solid var(--line);border-radius:3px 13px 3px 3px;background:var(--paper);animation:stat-rise .5s var(--out) both;animation-delay:calc(var(--n,0)*70ms + 120ms)}
.pop-stat:nth-child(2){--n:1}.pop-stat:nth-child(3){--n:2}
.pop-stat small{display:block;color:var(--muted);font-size:10px;line-height:1.3}
.pop-stat b{display:block;margin-top:6px;font:400 25px/1 var(--display);font-variant-numeric:tabular-nums}
.pop-label{margin:4px 0 10px;color:var(--muted);font-size:11px;font-weight:600}
.pop-note{margin:12px 0 0;color:var(--muted);font-size:11px;line-height:1.55}
.pop-flags{display:grid;gap:6px;margin:14px 0 0;padding:0;list-style:none}
.pop-flags li{position:relative;padding:8px 10px 8px 28px;border-radius:3px 10px 3px 3px;background:color-mix(in srgb,var(--risk),transparent 90%);font-size:11px;animation:stat-rise .45s var(--out) both}
.pop-flags li:before{position:absolute;top:8px;left:10px;color:var(--risk);content:"!";font-weight:800}
.pop-flags li:nth-child(2){animation-delay:.08s}.pop-flags li:nth-child(3){animation-delay:.16s}
.pop-actions{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-top:18px;padding-top:15px;border-top:1px solid var(--line)}
.pop-actions .button{min-height:44px;font-size:11px}
.pop-copy p{margin:0 0 10px;font-size:13px;line-height:1.65}.pop-copy p:last-child{margin:0}
.pop-copy strong{font-weight:700}
.pop-env-list{display:grid;gap:6px;margin:12px 0 0;padding:0;list-style:none}
.pop-env-list li{display:flex;align-items:center;gap:10px;font-size:12px;animation:stat-rise .4s var(--out) both;animation-delay:calc(var(--n,0)*50ms)}
.pop-env-list i{display:grid;width:26px;height:26px;place-items:center;border-radius:50%;background:var(--blue-soft);color:var(--blue);font:italic 17px var(--display)}
.suite-split{display:flex;gap:3px;height:30px;margin:6px 0 10px}
.suite-split span{display:flex;flex:1;align-items:center;justify-content:center;border:1px solid var(--ink);background:repeating-linear-gradient(45deg,color-mix(in srgb,var(--gain),transparent calc(100% - var(--a))) 0 1px,transparent 1px 4px) var(--surface);color:var(--ink);font:500 9.5px var(--mono);clip-path:inset(0 100% 0 0);transition:clip-path .3s linear;transition-delay:calc(var(--n)*.3s)}
.viz-on .suite-split span,.suite-split.viz-on span{clip-path:inset(0)}

/* charts: an assay-plate language. Hairlines, ruler ticks, crop marks, hatching, stepped motion. */
:root{--hatch-loss:repeating-linear-gradient(-45deg,var(--loss) 0 1.5px,transparent 1.5px 4px);--hatch-gain:repeating-linear-gradient(45deg,var(--gain) 0 1px,transparent 1px 4px);--plot-ink:color-mix(in srgb,var(--ink),transparent 12%);--crisp:cubic-bezier(.7,0,.2,1)}
.crop{position:relative}
.crop:before{position:absolute;inset:-7px;z-index:0;background:linear-gradient(var(--ink),var(--ink)) 0 0/10px 1px,linear-gradient(var(--ink),var(--ink)) 0 0/1px 10px,linear-gradient(var(--ink),var(--ink)) 100% 0/10px 1px,linear-gradient(var(--ink),var(--ink)) 100% 0/1px 10px,linear-gradient(var(--ink),var(--ink)) 0 100%/10px 1px,linear-gradient(var(--ink),var(--ink)) 0 100%/1px 10px,linear-gradient(var(--ink),var(--ink)) 100% 100%/10px 1px,linear-gradient(var(--ink),var(--ink)) 100% 100%/1px 10px;background-repeat:no-repeat;content:"";pointer-events:none}
.viz-tip{position:fixed;top:0;left:0;z-index:90;max-width:250px;padding:6px 9px;border:1px solid var(--ink);background:var(--surface);color:var(--ink);font:500 10.5px/1.45 var(--mono);box-shadow:3px 3px 0 var(--ink);opacity:0;pointer-events:none;transform:translate(14px,16px);transition:opacity .06s linear}
.viz-tip.is-left{transform:translate(calc(-100% - 14px),16px)}
.viz-tip.show{opacity:1}
.ruler{position:absolute;right:0;bottom:0;left:0;height:0;pointer-events:none}
.ruler span{position:absolute;bottom:0;height:4px;border-left:1px solid var(--muted)}
.ruler span.major{height:7px;border-color:var(--ink)}
.ruler span.is-zero{height:10px;border-left-width:2px;margin-left:-.5px}
.ruler em{position:absolute;top:-15px;left:0;color:var(--muted);font:500 9px var(--mono);font-style:normal;transform:translateX(-50%);white-space:nowrap}
.dbar{position:relative;display:block;height:14px}
.dbar:before{position:absolute;top:-9px;bottom:-9px;left:50%;width:1px;background:var(--ink);content:""}
.dbar i{position:absolute;top:0;bottom:0;width:var(--share)}
.dbar .gain{left:calc(50% + 1px);background:var(--gain)}
.dbar .loss{right:50%;background:var(--hatch-loss);box-shadow:inset 0 0 0 1px var(--loss)}
.meter{position:relative;display:block;height:10px;background:color-mix(in srgb,var(--line),transparent 15%);-webkit-mask:repeating-linear-gradient(90deg,#000 0 calc(5% - 2px),transparent calc(5% - 2px) 5%);mask:repeating-linear-gradient(90deg,#000 0 calc(5% - 2px),transparent calc(5% - 2px) 5%)}
.meter i{position:absolute;inset:0 auto 0 0;width:var(--share);background:var(--plot-ink);clip-path:inset(0 100% 0 0);transition:clip-path .7s steps(14,end) var(--delay,0s)}
.meter.is-risk i{background:var(--risk)}
.viz-on .meter i{clip-path:inset(0)}
.meter-wrap{position:relative;display:block}
.meter-wrap:after{position:absolute;top:-5px;bottom:-5px;left:20%;border-left:1px dashed var(--risk);content:""}
.mini-bars{position:relative;display:flex;align-items:stretch;gap:2px;width:100%;height:38px;clip-path:inset(-4px 100% -4px -4px);transition:clip-path .6s linear}
.viz-on .mini-bars,.mini-bars.viz-on{clip-path:inset(-4px)}
.mini-bars:before{position:absolute;top:50%;right:0;left:0;height:1px;background:currentColor;content:""}
.mini-bars.is-up:before{top:auto;bottom:0}
.mini-bars i{position:relative;flex:1;min-width:4px;cursor:crosshair}
.mini-bars i:after{position:absolute;right:0;left:0;height:var(--h);min-height:1px;content:""}
.mini-bars i.gain:after{bottom:50%;background:var(--gain)}
.mini-bars i.loss:after{top:50%;background:var(--hatch-loss);box-shadow:inset 0 0 0 1px var(--loss)}
.mini-bars.is-up i.gain:after{bottom:0}
.mini-bars i:hover{background:color-mix(in srgb,currentColor,transparent 86%)}
.db-chart{margin:0}.db-chart svg{display:block;width:100%;height:auto;overflow:visible}
.db-band{fill:color-mix(in srgb,var(--line),transparent 72%)}
.db-axis,.db-tick{stroke:var(--ink)}.db-tick.minor{stroke:var(--muted)}
.db-tick-label,.db-label{fill:var(--muted);font:9px var(--mono);letter-spacing:.04em}.db-size{fill:var(--ink);font-weight:600}
.db-value{fill:var(--ink);font:500 11px var(--mono)}
.db-hit{fill:transparent}
.db-row{cursor:crosshair;transition:opacity .1s linear}
.db-chart svg:hover .db-row{opacity:.3}.db-chart svg:hover .db-row:hover{opacity:1}
.db-before{stroke:var(--ink);stroke-width:2}
.db-line{stroke-width:2;stroke-dasharray:1;stroke-dashoffset:1;transition:stroke-dashoffset .3s linear;transition-delay:calc(var(--n)*.3s + .1s)}
.db-line.gain{stroke:var(--gain)}.db-line.loss{stroke:var(--loss)}
.db-arrow{opacity:0;transition:opacity 0s linear;transition-delay:calc(var(--n)*.3s + .4s)}
.db-arrow.gain{fill:var(--gain)}.db-arrow.loss{fill:var(--loss)}
.viz-on .db-line{stroke-dashoffset:0}.viz-on .db-arrow{opacity:1}
.db-proj{stroke:var(--ink);stroke-width:1;stroke-dasharray:2 3;opacity:0}
.db-tag{opacity:0}.db-tag rect{fill:var(--surface);stroke:var(--ink)}.db-tag text{fill:var(--ink);font:500 9.5px var(--mono)}
.db-tag.is-after rect{fill:var(--ink)}.db-tag.is-after text{fill:var(--paper)}
.db-row:hover .db-proj,.db-row:hover .db-tag{opacity:1}
.db-chart figcaption,.range-key,.slope figcaption{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;color:var(--muted);font:500 9px var(--mono);letter-spacing:.06em;text-transform:uppercase}
.db-chart figcaption span,.range-key span,.slope figcaption span{display:inline-flex;align-items:center;gap:6px}
.key-before,.key-after,.key-band,.key-forecast,.key-actual,.key-kept,.key-moved{display:inline-block}
.key-before{width:2px;height:12px;background:var(--ink)}
.key-after{width:0;height:0;border-top:5px solid transparent;border-bottom:5px solid transparent;border-left:8px solid var(--gain)}
.key-band{width:18px;height:10px;background:var(--hatch-gain);box-shadow:inset 0 0 0 1px var(--gain)}
.key-forecast{width:2px;height:13px;background:var(--gain)}
.key-actual{width:8px;height:8px;background:var(--ink);transform:rotate(45deg)}
.key-kept{width:18px;height:2px;background:var(--gain)}.key-moved{width:18px;border-top:1px dashed var(--muted)}
.scrub-hair{position:absolute;top:-6px;bottom:-6px;z-index:4;width:0;border-left:1px solid var(--ink);opacity:0;pointer-events:none}
.is-scrubbing>.scrub-hair{opacity:1}
.scrub-hair b{position:absolute;bottom:100%;left:0;padding:2px 5px;background:var(--ink);color:var(--paper);font:500 9.5px var(--mono);transform:translateX(-50%);white-space:nowrap}
.scrub-hair em{position:absolute;top:100%;left:6px;margin-top:3px;padding:1px 5px;border:1px solid var(--ink);background:var(--surface);color:var(--ink);font:500 9.5px var(--mono);font-style:normal;white-space:nowrap}
.scrub-hair.is-flip em{right:6px;left:auto}
[data-scrub]{cursor:crosshair}
.range-strip{margin-top:4px;padding-top:22px}.range-strip.is-stacked{padding-top:40px}
.range-track{position:relative;height:28px;margin-bottom:20px;border-top:1px solid var(--ink);border-bottom:1px solid var(--ink)}
.range-track .ruler{bottom:-1px}.range-track .ruler span{top:100%;bottom:auto}.range-track .ruler em{top:9px}
.range-band{position:absolute;top:5px;bottom:5px;background:var(--hatch-gain);box-shadow:inset 0 0 0 1px var(--gain);clip-path:inset(0 100% 0 0);transition:clip-path .6s linear}
.range-zero{position:absolute;top:0;bottom:0;border-left:1px solid var(--ink)}
.range-forecast{position:absolute;top:-6px;bottom:-6px;width:0;border-left:2px solid var(--gain);margin-left:-1px;opacity:0;transition:opacity 0s linear .6s}
.range-actual{position:absolute;top:0;bottom:0;width:0;opacity:0;transition:opacity 0s linear .8s}
.range-actual:before{position:absolute;top:50%;left:-4.5px;width:9px;height:9px;margin-top:-4.5px;background:var(--ink);box-shadow:0 0 0 2px var(--surface);content:"";transform:rotate(45deg)}
.range-tag{position:absolute;bottom:calc(100% + 7px);left:-1px;color:var(--ink);font:500 9.5px var(--mono);white-space:nowrap}
.range-tag:before{position:absolute;top:100%;left:0;height:7px;border-left:1px solid currentColor;content:""}
.range-forecast .range-tag{bottom:calc(100% + 1px);color:var(--gain)}
.range-strip.is-stacked .range-forecast .range-tag{bottom:calc(100% + 19px)}
.range-strip.is-stacked .range-forecast .range-tag:before{height:19px}
.viz-on .range-band{clip-path:inset(0)}.viz-on .range-forecast,.viz-on .range-actual{opacity:1}
.is-scrubbing .range-tag{opacity:.2}
.probe-bars{display:grid;gap:0;margin:0;padding:0;border-top:1px solid var(--ink);list-style:none}
.probe-row,.probe-head{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(90px,1fr) 38px 56px;align-items:center;gap:10px;padding:7px 4px;border-bottom:1px solid color-mix(in srgb,var(--line),transparent 30%);font:11px var(--mono)}
.probe-head{padding:5px 4px;color:var(--muted);font:500 9px var(--mono);letter-spacing:.06em;text-transform:uppercase}
.probe-scale{position:relative;display:block;height:12px}.probe-scale em{position:absolute;top:0;font-style:normal}.probe-scale em:first-child{left:0}.probe-scale em:last-child{right:0}
.probe-scale em.is-flag{left:20%;color:var(--risk);transform:translateX(-50%)}
.probe-row{cursor:crosshair;transition:box-shadow .08s linear}
.probe-row:hover{box-shadow:inset 3px 0 0 var(--ink)}
.probe-row b{font:500 11px var(--mono);text-align:right}.probe-row em{color:var(--muted);font:500 9px var(--mono);font-style:normal;letter-spacing:.06em;text-transform:uppercase}
.probe-row.is-flagged em{color:var(--risk)}
.probe-row.is-flagged>span:first-child{text-decoration:underline;text-decoration-color:var(--risk);text-underline-offset:3px}
/* home: hero additions */
.hero:after{position:absolute;inset:0;background:radial-gradient(520px circle at var(--spot-x,72%) var(--spot-y,32%),#d8bd7c1c,transparent 62%);content:"";pointer-events:none;transition:background .15s}
.hero-inner{z-index:1}
.window-bar{cursor:grab;touch-action:none}.window.is-dragging{cursor:grabbing;transition:none;animation-play-state:paused!important;user-select:none}
.window-viz{display:grid;gap:6px;margin-top:13px;padding-top:12px;border-top:1px dashed #172b3b2a;color:#56656b;font-size:10px}
.window-viz .meter{background:#172b3b14}
.window-three .window-viz{border-color:#ffffff26;color:#c6c6c1}
.window-three .mini-bars{color:#e0c782}
.window-viz-row{display:flex;align-items:baseline;justify-content:space-between;gap:10px}
.window-viz-row b{font:500 11px var(--mono)}
.window-two .mini-bars{color:#172b3b}
.hero-buttons{gap:10px}.hero-buttons .button{min-height:50px;padding:0 16px;gap:14px}
.button-small{min-height:30px;gap:9px;padding:0 5px 0 12px;font-size:10px}.button-small kbd{height:20px;min-width:20px}.hero-meta{flex-wrap:wrap}.hero-meta .button-small{margin-left:6px}
@media(min-width:851px){.hero-scene{min-height:500px}.hero-scene .window-one{top:0}.hero-scene .window-two{top:150px}.hero-scene .window-three{bottom:-6px}}
@media(max-width:850px){.hero-scene{min-height:470px}}
@media(max-width:680px){.ledger-stat .info-chip{top:6px;right:4px}.run-ledger{padding-top:18px}.hero-scene{min-height:430px}}
.hero-scene .window-body p{font-size:11px}
.hero-scene .window-viz .mini-bars{height:28px}

/* home: scoreboard */
.board-section{padding-top:20px}
.scoreboard{margin-top:10px;border-top:2px solid var(--ink);border-bottom:1px solid var(--ink)}
.board-head,.board-row{display:grid;grid-template-columns:minmax(170px,1.3fr) minmax(200px,1.6fr) minmax(110px,.8fr) minmax(110px,.8fr) 30px;align-items:center;gap:22px}
.board-head{align-items:end;padding:12px 6px 9px;border-bottom:1px solid var(--ink)}
.board-sort{display:inline-flex;align-items:center;gap:6px;padding:0;border:0;background:none;color:var(--muted);font:500 9px var(--mono);letter-spacing:.08em;text-align:left;text-transform:uppercase;cursor:pointer}
.board-sort:after{content:"↕";opacity:.45}
.board-sort[data-dir=descending]:after{content:"↓";opacity:1}.board-sort[data-dir=ascending]:after{content:"↑";opacity:1}
.board-sort:hover,.board-sort[data-dir]{color:var(--ink)}
.board-sort[data-dir]{text-decoration:underline;text-underline-offset:4px}
.board-axis{position:relative;display:grid;grid-template-columns:minmax(0,1fr) 48px;gap:6px 10px}
.board-axis .board-sort{grid-column:1/-1}
.board-axis .ruler{position:relative;grid-column:1;height:22px}
.board-axis .ruler span{bottom:0}.board-axis .ruler em{top:-14px}
.board-rows{position:relative;clip-path:inset(0 100% 0 0)}
.viz-on .board-rows{clip-path:inset(-60px -60px -60px -60px);transition:clip-path 1.1s linear}
.scoreboard:after{position:absolute;top:0;bottom:0;left:0;z-index:5;width:2px;background:var(--gain);content:"";opacity:0;pointer-events:none}
.scoreboard.viz-on:after{animation:board-scan 1.1s linear}
.board-row{position:relative;width:100%;padding:13px 6px;border:0;border-bottom:1px solid var(--line);background:transparent;color:var(--ink);text-align:left;cursor:pointer;transition:opacity .1s linear,background .1s linear}
.board-row:last-of-type{border-bottom:0}
.board-row:before{position:absolute;top:-1px;bottom:-1px;left:0;width:3px;background:var(--ink);content:"";opacity:0}
.board-row:hover{background:color-mix(in srgb,var(--blue-soft),transparent 35%)}.board-row:hover:before{opacity:1}
.board-row.is-baseline{color:var(--muted);background:repeating-linear-gradient(135deg,transparent 0 7px,color-mix(in srgb,var(--line),transparent 50%) 7px 8px)}
.board-name{display:flex;align-items:center;gap:12px;font:italic 400 21px/1.05 var(--display)}
.board-grade{display:grid;width:28px;height:28px;flex:none;place-items:center;border:1px solid var(--ink);color:var(--ink);font:italic 17px/1 var(--display)}
.board-row:hover .board-grade{background:var(--ink);color:var(--lime)}
.board-cell{display:grid;grid-template-columns:minmax(0,1fr) 48px;align-items:center;gap:10px}
.board-cell b{font:500 12px var(--mono);text-align:right;font-variant-numeric:tabular-nums}
.board-open{color:var(--ink);font:13px var(--mono)}.board-row:hover .board-open{color:var(--blue)}
.board-scrub{position:absolute;top:0;bottom:0;z-index:3;width:0;border-left:1px solid var(--ink);opacity:0;pointer-events:none}
.scoreboard.is-scrubbing .board-scrub{opacity:1}
.board-scrub b{position:absolute;top:0;left:0;padding:3px 6px;background:var(--ink);color:var(--paper);font:500 10px var(--mono);transform:translate(-50%,-100%);white-space:nowrap}
.board-scrub span{position:absolute;bottom:6px;left:8px;padding:2px 6px;border:1px solid var(--ink);background:var(--surface);color:var(--ink);font:500 10px var(--mono);white-space:nowrap}
.board-scrub.is-flip span{right:8px;left:auto}
.scoreboard.is-scrubbing .board-row.is-out{opacity:.22}
.board-legend{display:flex;gap:18px;flex-wrap:wrap;margin-top:14px;color:var(--muted);font:500 9px var(--mono);letter-spacing:.06em;text-transform:uppercase}
.board-legend span{display:inline-flex;align-items:center;gap:7px}
.board-legend i{display:inline-block;width:16px;height:9px}
.board-legend .k-gain{background:var(--gain)}.board-legend .k-loss{background:var(--hatch-loss);box-shadow:inset 0 0 0 1px var(--loss)}.board-legend .k-risk{background:var(--risk)}
.board-legend .k-base{background:repeating-linear-gradient(135deg,transparent 0 3px,var(--muted) 3px 4px);box-shadow:inset 0 0 0 1px var(--line)}
.board-hint{margin:10px 0 0;color:var(--muted);font:500 9px var(--mono);letter-spacing:.06em;text-transform:uppercase}

/* ledger chips and stretched links */
.ledger-stat{cursor:pointer}
.ledger-link{position:absolute;inset:0;z-index:1}
.ledger-link:focus-visible{outline:2px solid var(--blue);outline-offset:-2px}
.ledger-stat .info-chip{position:absolute;top:-33px;right:10px;width:22px;height:22px;font-size:13px}
.run-ledger{padding-top:34px}
.result-link{position:absolute;inset:0;z-index:1;border-radius:inherit}
.result-link:focus-visible{outline:2px solid var(--blue);outline-offset:3px}
.result-viz{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-top:14px}
.result-viz figure{display:grid;gap:5px;width:min(130px,45%);margin:0;color:var(--muted);font-size:9px}
.result-viz figcaption{display:flex;justify-content:space-between}
.result-card .result-viz .mini-bars{color:var(--ink);height:32px}
.result-card .mini-bars i{z-index:2}

/* notices */
.notice-stack{position:fixed;right:20px;bottom:20px;z-index:55;display:grid;gap:10px;width:min(350px,calc(100vw - 32px));pointer-events:none}
.notice{position:relative;display:grid;grid-template-columns:34px minmax(0,1fr) 24px;align-items:start;gap:11px;overflow:hidden;padding:13px 12px 16px 13px;border:1px solid var(--line);border-radius:4px 18px 4px 18px;background:color-mix(in srgb,var(--surface),transparent 6%);color:var(--ink);box-shadow:0 18px 42px #0b0c0d2a;backdrop-filter:blur(14px);pointer-events:auto;animation:notice-in .6s var(--spring) both}
.notice[hidden]{display:none}.notice.is-leaving{animation:notice-out .32s ease-in forwards}
.notice-icon{display:grid;width:34px;height:34px;place-items:center;border-radius:50%;background:#171819;color:var(--lime);font-size:15px;animation:notice-icon .8s .2s var(--spring) both}
.notice b{display:block;font-size:12px;line-height:1.3}.notice p{margin:3px 0 0;color:var(--muted);font-size:11px;line-height:1.45}
.notice-open{margin-top:7px;padding:0;border:0;background:none;color:var(--blue);font-size:11px;font-weight:700;cursor:pointer}
.notice-open:hover{text-decoration:underline;text-underline-offset:3px}
.notice-close{display:grid;width:24px;height:24px;place-items:center;border:0;border-radius:50%;background:transparent;color:var(--muted);cursor:pointer;transition:background .2s,transform .3s var(--spring)}
.notice-close:hover{background:var(--blue-soft);transform:rotate(90deg)}
.notice-timer{position:absolute;bottom:0;left:0;width:100%;height:2px;background:linear-gradient(90deg,var(--lime),var(--blue));transform-origin:left;animation:notice-timer 8s linear forwards}
.notice:hover .notice-timer,.notice:focus-within .notice-timer{animation-play-state:paused}

/* command palette */
dialog.palette{width:min(580px,calc(100% - 24px));margin:12vh auto auto;border-radius:6px 26px 6px 6px;overflow:hidden}
dialog.palette[open]{animation:pop-open .45s var(--spring) both}
dialog.palette::backdrop{animation:backdrop-in .3s both}
.palette-input{display:flex;align-items:center;gap:12px;padding:16px 18px;border-bottom:1px solid var(--line)}
.palette-input span{color:var(--blue);font-size:19px}
.palette-input input{flex:1;min-width:0;border:0;outline:0;background:transparent;color:var(--ink);font:italic 400 24px var(--display)}
.palette-list{max-height:min(55vh,420px);margin:0;padding:8px;overflow:auto;list-style:none}
.palette-group{padding:10px 10px 5px;color:var(--muted);font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.palette-item a{position:relative;display:grid;grid-template-columns:30px minmax(0,1fr) auto;align-items:center;gap:12px;padding:10px 12px;border-radius:10px;color:var(--ink);text-decoration:none;animation:item-in .35s var(--out) both;animation-delay:calc(var(--i,0)*28ms)}
.palette-item i{display:grid;width:30px;height:30px;place-items:center;border-radius:50%;background:var(--blue-soft);color:var(--blue);font:italic 17px var(--display)}
.palette-item small{color:var(--muted);font-size:10px}
.palette-item.is-active a{background:var(--blue-soft)}
.palette-item.is-active a:before{position:absolute;top:10px;bottom:10px;left:0;width:3px;border-radius:3px;background:var(--blue);content:""}
.palette-item.is-active small{color:var(--ink)}
.palette-empty{padding:26px;color:var(--muted);text-align:center;font-size:12px}
.palette-foot{display:flex;gap:16px;padding:10px 18px;border-top:1px solid var(--line);color:var(--muted);font-size:10px}
.palette-foot span{display:inline-flex;align-items:center;gap:6px}

/* detail and forecast additions */
.detail-forecast .range-strip{width:100%;max-width:360px;margin-top:12px}
.detail-ledger p{position:relative;padding-right:30px}
.detail-ledger .info-chip{position:absolute;top:-4px;right:0}
.evidence-grid{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);gap:16px;margin-bottom:16px}
.evidence-grid .panel h2{font-size:21px}
.rho-scale{margin:10px 0 4px}
.rho-track{position:relative;height:22px;margin:34px 4px 26px;border-top:1px solid var(--ink);border-bottom:1px solid var(--ink)}
.rho-track .ruler{bottom:-1px}.rho-track .ruler span{top:100%;bottom:auto}.rho-track .ruler em{top:9px}
.rho-zone{position:absolute;top:0;bottom:0}
.rho-zone.z-rev{background:repeating-linear-gradient(-45deg,color-mix(in srgb,var(--loss),transparent 55%) 0 1px,transparent 1px 5px)}
.rho-zone.z-weak{background:repeating-linear-gradient(45deg,color-mix(in srgb,var(--gain),transparent 60%) 0 1px,transparent 1px 6px)}
.rho-zone.z-keep{background:var(--hatch-gain)}
.rho-keep{position:absolute;top:-8px;bottom:-8px;border-left:1px dashed var(--ink)}
.rho-keep em{position:absolute;top:-14px;left:4px;color:var(--ink);font:500 9px var(--mono);font-style:normal;white-space:nowrap}
.rho-needle{position:absolute;top:-10px;bottom:-4px;left:0;z-index:2;width:0;border-left:2px solid var(--ink);margin-left:-1px;transition:left .9s steps(18,end) .2s}
.rho-needle:before{position:absolute;top:-1px;left:-6px;border-top:7px solid var(--ink);border-right:5px solid transparent;border-left:5px solid transparent;content:""}
.viz-on .rho-needle{left:var(--at)}
.rho-needle b{position:absolute;bottom:calc(100% + 8px);left:0;padding:2px 6px;background:var(--ink);color:var(--paper);font:500 10px var(--mono);transform:translateX(-50%);white-space:nowrap}
.rho-track.is-scrubbing .rho-needle b{opacity:.2}
.rho-labels{display:flex;justify-content:space-between;color:var(--muted);font:500 9px var(--mono);letter-spacing:.06em;text-transform:uppercase}
.slope-panel{display:grid;grid-template-columns:minmax(0,.75fr) minmax(0,1.25fr);gap:30px;align-items:center;margin-top:16px}
.slope-panel h2{font-size:27px}.slope-panel>div>p:not(.eyebrow):not(.fine-print){color:var(--muted);font-size:12px}
.slope{margin:0}
.slope-head,.slope-body{display:grid;grid-template-columns:minmax(0,1fr) minmax(60px,.6fr) minmax(0,1fr);gap:0}
.slope-head{margin-bottom:6px;padding-bottom:6px;border-bottom:1px solid var(--ink);color:var(--muted);font:500 9px var(--mono);letter-spacing:.08em;text-transform:uppercase}.slope-head span:first-child{text-align:right}.slope-head span:last-child{padding-left:8px}
.slope ol{display:grid;grid-template-rows:repeat(var(--rows),40px);margin:0;padding:0;list-style:none}
.slope li{position:relative;display:flex;align-items:center;gap:8px;min-width:0;padding:0 8px;border-bottom:1px solid color-mix(in srgb,var(--line),transparent 40%);font-size:11.5px;cursor:crosshair;transition:opacity .1s linear,background .1s linear}
.slope li span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.slope li b{flex:none;color:var(--muted);font:500 10px var(--mono)}
.slope li i{flex:none;color:var(--ink);font:600 9px var(--mono);font-style:normal}
.slope-left li{justify-content:flex-end;text-align:right}
.slope-left li:after,.slope-right li:before{position:absolute;top:50%;width:7px;height:7px;margin-top:-3.5px;background:var(--ink);content:""}
.slope-left li:after{right:-4px}.slope-right li:before{left:-4px}
.slope li em{flex:none;padding:0 4px;border:1px solid currentColor;font:600 9px/1.5 var(--mono);font-style:normal}
.slope li em.up{color:var(--gain)}.slope li em.down{color:var(--loss)}.slope li em.same{color:var(--muted)}
.slope svg{width:100%;height:calc(var(--rows)*40px);overflow:visible;clip-path:inset(-10px 100% -10px -10px);transition:clip-path .9s linear .15s}
.viz-on svg{clip-path:inset(-10px)}
.slope polyline{fill:none;stroke:var(--muted);stroke-width:1.25;stroke-dasharray:3 3;vector-effect:non-scaling-stroke;cursor:crosshair;transition:opacity .1s linear}
.slope polyline.is-kept{stroke:var(--gain);stroke-width:2.5;stroke-dasharray:none}
.slope.has-hot polyline:not(.is-hot),.slope.has-hot li:not(.is-hot){opacity:.15}
.slope polyline.is-hot{stroke:var(--ink);stroke-width:3;stroke-dasharray:none;opacity:1}.slope li.is-hot{background:var(--blue-soft)}

/* methodology additions */
.process-journey{position:relative}
.process-journey:before{position:absolute;top:-4px;left:0;z-index:1;width:8px;height:8px;border-radius:50%;background:var(--lime);box-shadow:0 0 0 4px #d8bd7c33,0 0 14px #d8bd7c;content:"";animation:journey 7s ease-in-out infinite}
.process-card{cursor:pointer}
.process-card .info-chip{position:absolute;top:14px;right:6px}
.ladder-panel{display:grid;grid-template-columns:minmax(0,.8fr) minmax(0,1.2fr);gap:30px;align-items:center;margin-top:30px}
.ladder-panel h3{margin:0 0 8px;font-size:30px}.ladder-panel p:not(.eyebrow):not(.fine-print){color:var(--muted);font-size:12px}
.ladder-wrap{display:grid;gap:8px}
.ladder-toggle{justify-self:start;padding:6px 10px;border:1px solid var(--ink);background:transparent;color:var(--ink);font:500 9px var(--mono);letter-spacing:.08em;text-transform:uppercase;cursor:pointer;box-shadow:2px 2px 0 var(--ink);transition:transform .08s linear,box-shadow .08s linear}
.ladder-toggle:hover{background:var(--lime);color:#171819}.ladder-toggle:active{transform:translate(2px,2px);box-shadow:none}
.ladder-toggle[aria-pressed=true]{background:var(--ink);color:var(--paper)}
.model-ladder{display:flex;align-items:flex-end;gap:clamp(14px,4vw,40px);min-height:200px;padding:16px 0 0}
.ladder-rung{position:relative;z-index:calc(10 - var(--n));display:grid;justify-items:center;gap:9px;margin:0}
.ladder-dot{display:block;width:var(--d);height:var(--d);border-radius:50%;background:radial-gradient(circle at 32% 30%,#f1dfb2,var(--lime) 45%,var(--blue));box-shadow:0 8px 20px #a3803e40;cursor:crosshair;transform:scale(0);transition:transform .9s var(--spring),filter .15s;transition-delay:calc(var(--n)*140ms),0s}
.viz-on .ladder-dot{transform:none}
.ladder-dot:hover{filter:brightness(1.08)}
.ladder-rung figcaption{display:grid;justify-items:center;color:var(--muted);font:10px var(--mono)}.ladder-rung figcaption b{color:var(--ink);font:italic 400 20px/1 var(--display)}
.model-ladder.is-nested{display:grid;justify-content:center}
.is-nested .ladder-rung{grid-area:1/1;align-self:end}
.is-nested .ladder-dot{box-shadow:0 6px 16px #a3803e55,inset 0 0 0 1px #ffffff40}
.is-nested .ladder-rung figcaption{position:absolute;bottom:calc(var(--d) + 1px);left:50%;display:flex;align-items:baseline;gap:5px;padding:0 4px;background:var(--surface);white-space:nowrap;transform:translateX(-50%)}
.is-nested .ladder-rung figcaption b{font-size:14px}
.pop-window .model-ladder{min-height:180px;justify-content:center}

.pop-tab,.filter,.nav-search{position:relative;overflow:hidden}
.nav-cta{translate:var(--mx,0) var(--my,0);transition:transform .2s,background .2s,translate .25s var(--out)}
.filters{position:relative}
.filter-ink{position:absolute;top:0;left:0;z-index:0;border-radius:999px;background:var(--ink);box-shadow:0 6px 16px #0000001f;transition:transform .5s var(--spring),width .5s var(--spring),height .3s}
.has-ink .filter{position:relative;z-index:1}
.has-ink .filter.active{border-color:transparent;background:transparent;color:var(--paper)}
.has-ink .filter:not(.active):hover{border-color:var(--ink);background:var(--surface);color:var(--ink)}
.pop-formula{margin:12px 0;padding:12px 13px;border:1px dashed color-mix(in srgb,var(--blue),transparent 40%);border-radius:3px 12px 3px 3px;background:var(--paper);font:11px/1.6 var(--mono);overflow-wrap:anywhere}
.feature-actions{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.feature-aside .peek-button{border-color:var(--lime);background:transparent;color:var(--lime);box-shadow:3px 3px 0 var(--lime)}
.feature-aside .peek-button:hover{background:var(--lime);color:#171819;box-shadow:4px 4px 0 #f4f3ef}
.detail-hero .button-kbd,.detail-hero .button-ring{min-height:42px;font-size:11px}
.detail-hero .button-ring .button-arrow{width:24px;height:24px;font-size:12px}
@media(max-width:680px){.nav-print{display:none}.notice-stack .notice:has(~ .notice:not([hidden])){display:none}}
@media(max-width:480px){.nav-cta{display:none}}
@media(hover:none){.pop-tab:hover{background:transparent}}

.chart-frame{border:1px solid var(--line)!important;border-radius:0!important;background:var(--surface)!important;box-shadow:none!important}
.chart-frame svg{filter:none!important;cursor:crosshair}
.chart-frame .chart-legend{position:relative;z-index:1}
.chart-tooltip{border:1px solid var(--ink);border-radius:0;background:var(--surface);box-shadow:3px 3px 0 var(--ink);transition:opacity .06s linear}
.chart-tooltip b{font:500 12px var(--sans)}.chart-tooltip span{font:500 10px var(--mono)}
.sc-plot{fill:none;stroke:var(--ink);stroke-width:1}
.sc-grid{stroke:var(--line);stroke-dasharray:1 4}
.sc-tick{stroke:var(--ink)}.sc-tick.minor{stroke:var(--muted)}
.sc-tick-label{fill:var(--muted);font:9px var(--mono)}
.sc-axis{fill:var(--muted);font:500 9px var(--mono);letter-spacing:.08em;text-transform:uppercase}
.sc-band{fill:color-mix(in srgb,var(--gain),transparent 88%)}
.sc-band-edge{stroke:var(--gain);stroke-dasharray:2 3;opacity:.7}
.sc-band-label{fill:var(--muted);font:500 9px var(--mono)}
.sc-diag{stroke:var(--ink);stroke-width:1;stroke-dasharray:1;stroke-dashoffset:1;transition:stroke-dashoffset .6s linear}
.sc-note{fill:var(--ink);font:italic 13px var(--display)}
.sc-whisker{stroke:var(--muted);stroke-width:1}
.sc-resid{stroke:var(--ink);stroke-width:1;stroke-dasharray:2 2;opacity:.45}
.sc-point{fill:var(--surface);stroke:var(--ink);stroke-width:1.25;opacity:0;transition:opacity 0s linear,stroke-width .08s linear;transition-delay:calc(var(--n)*.12s + .6s),0s}
.sc-point.g-a,.sc-point.g-b{fill:var(--gain)}
.sc-point.g-d,.sc-point.g-f{fill:color-mix(in srgb,var(--loss),transparent 65%)}
.sc-miss{opacity:0;fill:var(--ink);font:600 10px var(--mono);paint-order:stroke;stroke:var(--surface);stroke-width:4px;stroke-linejoin:round}
.viz-on .sc-diag{stroke-dashoffset:0}.viz-on .sc-point{opacity:1}
.chart-point-link:hover .sc-miss,.chart-point-link:focus .sc-miss,.chart-point-link.is-snapped .sc-miss{opacity:1}
.chart-point-link:hover .sc-resid,.chart-point-link:focus .sc-resid,.chart-point-link.is-snapped .sc-resid{stroke-width:1.75;opacity:1}
.chart-point-link:hover .sc-point,.chart-point-link:focus .sc-point,.chart-point-link.is-snapped .sc-point{stroke-width:3}
.sc-xhair{opacity:0;pointer-events:none}
svg.is-scrubbing .sc-xhair{opacity:1}
.sc-xhair line{stroke:var(--ink);stroke-width:.75;stroke-dasharray:3 2}
.sc-xhair rect{fill:var(--ink)}.sc-xhair text{fill:var(--paper);font:600 9px var(--mono)}
@keyframes board-scan{0%{left:0;opacity:1}98%{left:100%;opacity:1}100%{left:100%;opacity:0}}
body{font-optical-sizing:auto;letter-spacing:-.008em}
.eyebrow{font:500 10px/1.2 var(--mono);letter-spacing:.12em;text-transform:uppercase}
.plain-brief-copy>p{max-width:640px;font:400 clamp(19px,1.9vw,23px)/1.55 var(--text);letter-spacing:-.005em}
.plain-brief-copy>p strong{font-weight:600;background:linear-gradient(transparent 66%,color-mix(in srgb,var(--lime),transparent 45%) 66%)}
.hero-lede,.page-intro,.section-heading>p,.plain-brief-intro>p:last-child,.plain-step p,.process-card p,.why-buy p,.quick-card small,.result-card p,.feature-main>p,.feature-note>p,.chart-copy>p:not(.eyebrow):not(.fine-print),.pilot-notes small,.panel-intro,.verdict,.scale-caveat,.grade-explainer,.pop-copy p,.slope-panel>div>p:not(.eyebrow):not(.fine-print),.ladder-panel p:not(.eyebrow):not(.fine-print),.hero-scene .window-body p,.forecast-caveat small,.feature-estimate p,.feature-estimate>small,.chart-note-rail small,.sample-caveat,.dialog-inner p{font-family:var(--text);letter-spacing:0}
.page-intro,.section-heading>p,.plain-brief-intro>p:last-child,.plain-step p,.process-card p,.why-buy p,.quick-card small,.chart-copy>p:not(.eyebrow):not(.fine-print),.pilot-notes small,.panel-intro,.scale-caveat,.grade-explainer,.pop-copy p,.slope-panel>div>p:not(.eyebrow):not(.fine-print),.ladder-panel p:not(.eyebrow):not(.fine-print),.sample-caveat{color:color-mix(in srgb,var(--ink),var(--muted) 50%)}
.hero-lede{font-size:clamp(18px,1.6vw,20px);line-height:1.55}
.page-intro,.section-heading>p,.plain-brief-intro>p:last-child{font-size:17px;line-height:1.55}
.plain-step p,.process-card p,.why-buy p,.quick-card small,.result-card p,.pilot-notes small,.pop-copy p,.slope-panel>div>p:not(.eyebrow):not(.fine-print),.ladder-panel p:not(.eyebrow):not(.fine-print),.chart-copy>p:not(.eyebrow):not(.fine-print),.scale-caveat,.verdict{font-size:15px;line-height:1.5}
.feature-main>p,.feature-note>p{font-size:17px;line-height:1.5}
.panel-intro,.grade-explainer,.sample-caveat,.forecast-caveat small,.feature-estimate>small,.chart-note-rail small{font-size:13.5px!important;line-height:1.45!important}
.hero-scene .window-body p{font-size:13px;line-height:1.45}
.why-buy p strong{font-family:var(--sans)}
.ledger-stat>span:not(.signal-orbit),.ledger-stat>small,.detail-ledger p>span,.detail-forecast>span,.feature-stats small,.pilot-notes span,.result-lead span{color:var(--muted);font:italic 400 16px/1.1 var(--display);letter-spacing:-.005em}
.ledger-signal>span:last-of-type{max-width:150px}
.ledger-signal .signal-orbit{left:62px}
.why-buy p strong,.plain-step h3{font-variation-settings:"wdth" 88}
.button,.nav-cta,.nav-links a{font-variation-settings:"wdth" 90}
.chip-wrap{white-space:nowrap}.chip{display:inline-block;padding:0 .38em;border:1px solid;color:var(--ink);font:600 .74em/1.55 var(--mono);letter-spacing:0;vertical-align:.12em;white-space:nowrap}
.chip.gain{border-color:var(--gain);background:color-mix(in srgb,var(--gain),transparent 84%)}
.chip.loss{border-color:var(--loss);background:repeating-linear-gradient(-45deg,color-mix(in srgb,var(--loss),transparent 80%) 0 1.5px,transparent 1.5px 4px)}
.feature-main>p em{font-style:italic}
.fine-print{display:flex;align-items:baseline;gap:8px;margin:12px 0 0;color:var(--muted);font:500 9.5px/1.6 var(--mono)!important;letter-spacing:.09em;text-transform:uppercase}
.fine-print:before{flex:none;color:var(--blue);font-size:11px;content:"✳"}
.fine-print.is-alert{color:var(--risk)}.fine-print.is-alert:before{color:var(--risk);content:"!"}
.feature-aside .fine-print{color:#a9a69d}.feature-aside .fine-print:before{color:var(--lime)}
.sample-caveat{padding:0 0 22px}
.factor-list{margin-top:26px}
.factor-title{display:block;margin-bottom:9px;color:var(--muted);font:500 9.5px var(--mono);letter-spacing:.1em;text-transform:uppercase}
.factor-list ol{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));margin:0;padding:0;border-top:1px solid var(--ink);list-style:none}
.factor-list li{display:flex;align-items:baseline;gap:10px;padding:10px 14px 10px 0;border-bottom:1px solid var(--line);font:550 13.5px/1.3 var(--sans);font-variation-settings:"wdth" 92}
.factor-list li:nth-child(even){padding-left:14px;border-left:1px solid var(--line)}
.factor-list i{flex:none;color:var(--blue);font:italic 400 19px/1 var(--display)}
.versus{display:grid;gap:9px;margin-top:18px}
.versus>div{display:grid;grid-template-columns:64px minmax(0,1fr) 46px;align-items:center;gap:10px}
.versus span{color:#bdbab1;font:500 9.5px var(--mono);letter-spacing:.08em;text-transform:uppercase}
.versus b{color:#f5f2e9;font:600 12px var(--mono);text-align:right}
.versus .dbar:before{background:#f4f3ef80}
.versus small{color:#8f8c84;font:500 9px var(--mono);letter-spacing:.08em;text-transform:uppercase}
.spec-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));margin:16px 0 0;border-top:1px solid var(--ink)}
.spec-list>div{padding:9px 14px 10px 0;border-bottom:1px solid var(--line)}
.spec-list>div+div{padding-left:14px;border-left:1px solid var(--line)}
.spec-list dt{color:var(--muted);font:500 9px/1.3 var(--mono);letter-spacing:.08em;text-transform:uppercase}
.spec-list dd{margin:5px 0 0;font:400 21px/1.1 var(--display)}
.result-card .spec-list{margin-top:10px}.result-card .spec-list dd{font-size:17px}
.chart-copy .spec-list{grid-template-columns:repeat(4,minmax(0,1fr))}.chart-copy .spec-list dd{font-size:17px}
.chart-stat span{max-width:220px;color:var(--ink);font:italic 400 19px/1.15 var(--display)}
.baseline-aside{margin-top:26px}
.verdict{padding:14px 16px;border:0;border-left:2px solid var(--ink);background:color-mix(in srgb,var(--blue-soft),transparent 30%);font:400 15px/1.5 var(--text)}
.verdict-lead{display:block;margin-bottom:5px;font:italic 400 24px/1.05 var(--display)}
.panel .pop-flags{margin-top:8px}
@media(max-width:560px){.factor-list ol{grid-template-columns:1fr}.factor-list li:nth-child(even){padding-left:0;border-left:0}.spec-list>div+div{padding-left:0;border-left:0}}
@keyframes page-in{from{opacity:0}}
@keyframes main-in{from{opacity:0;transform:translateY(14px)}}
@keyframes theme-reveal{from{clip-path:circle(0 at var(--vt-x,100%) var(--vt-y,0))}to{clip-path:circle(150vmax at var(--vt-x,100%) var(--vt-y,0))}}
@keyframes ripple{to{opacity:0;transform:translate(-50%,-50%) scale(1)}}
@keyframes chip-ping{0%{opacity:.8;transform:scale(.8)}100%{opacity:0;transform:scale(1.5)}}
@keyframes pop-open{from{opacity:0;transform:scale(.55) translateY(14px);filter:blur(8px)}to{opacity:1;transform:none;filter:none}}
@keyframes pop-close{to{opacity:0;transform:scale(.86) translateY(10px);filter:blur(4px)}}
@keyframes sheet-open{from{transform:translateY(105%)}to{transform:none}}
@keyframes sheet-close{to{transform:translateY(105%)}}
@keyframes panel-in{from{opacity:0;transform:translateX(var(--panel-from,16px))}to{opacity:1;transform:none}}
@keyframes grade-stamp{0%{opacity:0;transform:scale(2.2) rotate(-25deg)}100%{opacity:1;transform:none}}
@keyframes stat-rise{from{opacity:0;transform:translateY(10px)}}
@keyframes notice-in{from{opacity:0;transform:translateX(50px) scale(.92)}}
@keyframes notice-out{to{opacity:0;transform:translateX(70px) scale(.96)}}
@keyframes notice-icon{from{transform:scale(0) rotate(-90deg)}}
@keyframes notice-timer{to{transform:scaleX(0)}}
@keyframes item-in{from{opacity:0;transform:translateY(6px)}}
@keyframes backdrop-in{from{opacity:0}}
@keyframes journey{0%{left:0}50%{left:calc(100% - 8px)}100%{left:0}}
@media(max-width:900px){.board-head,.board-row{grid-template-columns:minmax(150px,1.2fr) minmax(170px,1.5fr) minmax(90px,.8fr) 26px}.board-head>span:nth-child(4),.board-row>.board-cell:nth-of-type(4){display:none}.evidence-grid,.slope-panel,.ladder-panel{grid-template-columns:1fr}}
@media(max-width:680px){.nav-search span{display:none}.nav-search{padding:0 8px}.board-head{display:none}.board-row{grid-template-columns:minmax(0,1fr) 22px;gap:9px 12px;padding:14px 4px}.board-name{grid-column:1/-1;font-size:19px}.board-row>.board-cell{grid-column:1}.board-row>.board-cell:nth-of-type(3):before{content:"Shortcut reward";grid-column:1/-1;color:var(--muted);font-size:10px}.board-row>.board-cell:nth-of-type(2):before{content:"Change on new questions";grid-column:1/-1;color:var(--muted);font-size:10px}.board-cell{row-gap:4px}.board-open{grid-column:2;grid-row:1}.pop-window,.pop-window.is-wide{top:auto!important;right:8px;bottom:8px;left:8px!important;width:auto;max-height:84vh;border-radius:24px 24px 10px 10px;transform-origin:50% 100%}.pop-window.is-opening{animation:sheet-open .5s var(--out) both}.pop-window.is-closing{animation:sheet-close .25s ease-in both}.pop-stats{grid-template-columns:1fr 1fr 1fr;gap:6px}.pop-stat b{font-size:20px}.probe-row{grid-template-columns:minmax(0,1fr) 60px 34px;gap:8px}.probe-row em{display:none}.notice-stack{right:12px;bottom:12px;left:12px;width:auto}.result-viz{flex-wrap:wrap}.slope-head,.slope-body{grid-template-columns:minmax(0,1fr) 44px minmax(0,1fr);gap:6px}.slope li{font-size:10px}.slope li b{display:none}.detail-ledger p{padding-right:26px}}
@media(prefers-reduced-motion:reduce){body,main,.board-row,.pop-window,.pop-panel,.notice,.notice-icon,.pop-grade,.pop-stat,.palette-item a,.process-journey:before,.info-chip:before{animation:none!important}.board-row{opacity:1;transform:none}.notice-timer{animation-duration:8s!important}.button{translate:none}}
"""


# Product-site layer: plain grotesque headings, a cooler neutral and the touchstone's gold streak as the one accent.
CSS += r"""
:root{--paper:#f3f3ef;--surface:#fbfbf8;--ink:#141618;--muted:#5f6367;--line:#d8d9d3;--blue:#86621b;--blue-soft:#ece5d3;--lime:#d6b25c;--band:#141618;--band-ink:#ecebe6;--band-muted:#a7a9a6}
:root[data-theme=dark]{--paper:#0f1113;--surface:#17191c;--ink:#ecebe6;--muted:#9b9fa3;--line:#2b2e32;--blue:#d6b25c;--blue-soft:#25211a;--lime:#d6b25c;--band:#191b1e;--band-ink:#ecebe6;--band-muted:#a7a9a6}
.reveal{opacity:1!important;transform:none!important}
.eyebrow:before,.hero:after{display:none}
.hero h1,.page-title,.section-heading h2,.cta-band h2{font-family:var(--sans);font-style:normal;font-weight:680;font-variation-settings:"opsz" 96,"wdth" 90;letter-spacing:-.022em;line-height:1;text-wrap:balance}
.section{padding-top:72px;padding-bottom:72px}.problem{padding-bottom:24px}
.hero h1>span:not(.kinetic-word),.page-title>span:not(.kinetic-word),.section-heading h2>span:not(.kinetic-word),.cta-band h2>span{font-style:normal}
.hero h1{max-width:620px;font-size:clamp(46px,5.4vw,78px);color:#f4f3ef}
.hero h1>span:not(.kinetic-word){display:block;color:var(--lime)}
.page-title{font-size:clamp(44px,5.6vw,76px)}
.section-heading h2{font-size:clamp(34px,4.2vw,58px)}
.section-heading h2>span:not(.kinetic-word),.page-title>span:not(.kinetic-word){color:var(--blue)}
.hero{background:var(--band)}
.hero-inner{grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);gap:56px;min-height:0;padding-top:84px;padding-bottom:88px}
.hero-lede{max-width:540px;color:#c9c8c2}
.hero-meta{display:block;margin-top:22px;color:var(--band-muted);font:500 10px/1.6 var(--mono);letter-spacing:.08em;text-transform:uppercase}
.cert{display:grid;gap:14px;padding:22px 24px 20px;border:1px solid #ffffff2b;background:#1f2225;color:var(--band-ink);box-shadow:0 30px 70px #0007}
.cert-head{display:flex;align-items:center;justify-content:space-between;gap:12px;color:var(--band-muted);font:500 9.5px var(--mono);letter-spacing:.1em;text-transform:uppercase}
.cert-stamp{padding:3px 7px;border:1px solid var(--lime);color:var(--lime)}
.cert-title{display:grid;grid-template-columns:54px minmax(0,1fr);align-items:center;gap:14px;padding-bottom:14px;border-bottom:1px solid #ffffff24}
.cert-grade{display:grid;width:54px;height:54px;place-items:center;border:1px solid var(--lime);color:var(--lime);font:italic 400 36px/1 var(--display)}
.cert-title strong{display:block;font:650 21px/1.15 var(--sans);font-variation-settings:"wdth" 90;letter-spacing:-.02em}
.cert-title small{display:block;margin-top:4px;color:var(--band-muted);font:500 9.5px var(--mono);letter-spacing:.06em}
.cert-row{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:baseline;gap:6px 16px;padding:10px 0;border-bottom:1px solid #ffffff14}
.cert-row>span:first-child{font:500 13.5px var(--sans)}
.cert-row b{font:600 13px var(--mono);font-variant-numeric:tabular-nums}
.cert-viz{grid-column:1/-1;color:var(--band-muted);font:500 9.5px var(--mono);letter-spacing:.06em;text-transform:uppercase}
.cert .dbar:before{background:#ecebe680}.cert .meter{background:#ffffff26}.cert .meter i{background:#ecebe6}.cert .meter.is-risk i{background:var(--risk)}
.cert-foot{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.cert-foot small{display:block;color:var(--band-muted);font:500 9px/1.4 var(--mono);letter-spacing:.08em;text-transform:uppercase}
.cert-foot b{display:block;margin-top:4px;font:700 26px/1 var(--sans);font-variation-settings:"wdth" 88;letter-spacing:-.03em}
.cert-foot em{color:var(--band-muted);font:500 11px var(--mono);font-style:normal;letter-spacing:0}
.cert-link{justify-self:start;color:var(--lime);font:600 10px var(--mono);letter-spacing:.08em;text-decoration:none;text-transform:uppercase}
.cert-link:hover{text-decoration:underline;text-underline-offset:4px}
.fact-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:28px}
.fact-row article{display:grid;align-content:start;gap:10px;padding-top:16px;border-top:2px solid var(--ink)}
.fact-row b{font:680 clamp(30px,3.2vw,44px)/1 var(--sans);font-variation-settings:"opsz" 96,"wdth" 90;letter-spacing:-.02em}
.fact-row p{margin:0;font:400 16px/1.5 var(--text)}
.fact-row small,.research-card small{color:var(--muted);font:500 9.5px/1.5 var(--mono);letter-spacing:.06em;text-transform:uppercase}
.steps{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:24px;margin:0;padding:0;list-style:none}
.steps li{display:grid;align-content:start;gap:8px;padding-top:14px;border-top:1px solid var(--ink)}
.steps i{color:var(--blue);font:600 10px var(--mono);font-style:normal;letter-spacing:.1em}
.steps i:before{content:"Step "}
.steps h3{margin:0;font:650 21px/1.15 var(--sans);font-variation-settings:"wdth" 90;letter-spacing:-.02em}
.steps p{margin:0;color:color-mix(in srgb,var(--ink),var(--muted) 45%);font:400 15px/1.5 var(--text)}
.measures{margin-top:56px}
.measures dl{margin:14px 0 0;border-top:2px solid var(--ink)}
.measures dl>div{display:grid;grid-template-columns:minmax(160px,.35fr) minmax(0,1fr);gap:24px;padding:14px 0;border-bottom:1px solid var(--line)}
.measures dt{font:650 18px/1.3 var(--sans);font-variation-settings:"wdth" 90}
.measures dd{margin:0;font:400 17px/1.5 var(--text)}
.audience{padding-top:0}
.audience-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.audience-grid article{padding:28px;border:1px solid var(--line);background:var(--surface)}
.audience-grid h3{margin:0 0 16px;font:680 30px/1.05 var(--sans);font-variation-settings:"opsz" 96,"wdth" 90;letter-spacing:-.018em}
.audience-grid ul{display:grid;gap:10px;margin:0;padding:0;list-style:none}
.audience-grid li{position:relative;padding-left:20px;font:400 16px/1.45 var(--text)}
.audience-grid li:before{position:absolute;top:.62em;left:0;width:8px;height:8px;background:var(--lime);content:""}
.compare{border-radius:0}
.compare table{font-size:13px}
.compare th[scope=row]{font:600 13px var(--sans);text-transform:none;letter-spacing:0;color:var(--ink);background:transparent;white-space:normal}
.compare tr.is-us th,.compare tr.is-us td{background:var(--blue-soft);font-weight:700}
.research-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.research-card{display:grid;gap:14px;padding:24px;border:1px solid var(--line);background:var(--surface);color:var(--ink);text-decoration:none;transition:border-color .15s}
.research-card:hover{border-color:var(--ink)}
.research-card p{margin:0;font:400 22px/1.35 var(--text)}
.status-list{margin:0;padding:0;border-top:2px solid var(--ink);list-style:none}
.status-list li{display:grid;grid-template-columns:minmax(160px,.35fr) minmax(0,1fr);gap:24px;padding:16px 0;border-bottom:1px solid var(--line)}
.status-list b{font:650 18px var(--sans);font-variation-settings:"wdth" 90}
.status-list p{margin:0;font:400 17px/1.5 var(--text)}
.cta-band{margin-top:40px;padding:80px 0;background:var(--band);color:var(--band-ink)}
.cta-inner{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,.7fr);align-items:end;gap:40px}
.cta-band .eyebrow{color:var(--band-muted)}
.cta-band h2{margin:0;font-size:clamp(36px,4.4vw,60px);color:#f4f3ef}
.cta-band h2>span{color:var(--lime)}
.process-card,.process-card:nth-child(even),.process-card:hover,.process-card:nth-child(even):hover{transform:none}
.process-mark,.process-card:nth-child(n) .process-mark{animation:none!important;transform:none!important;font-size:26px!important}
.process-journey:before{display:none}
.process-card h3{font:650 22px/1.1 var(--sans);font-variation-settings:"wdth" 90;letter-spacing:-.02em}
.cta-band p:not(.eyebrow){max-width:560px;margin:18px 0 0;color:#c9c8c2;font:400 18px/1.5 var(--text)}
.cta-band .cta-note{color:var(--lime);font:600 10px var(--mono);letter-spacing:.08em;text-transform:uppercase}
.cta-actions{display:flex;justify-content:flex-end;gap:12px;flex-wrap:wrap}
main+.footer,.cta-band+.footer{margin-top:0}
@media(max-width:680px){.hero-inner{grid-template-columns:1fr;gap:36px;padding-top:52px;padding-bottom:56px}.fact-row,.steps,.audience-grid,.research-grid,.cta-inner{grid-template-columns:1fr}.measures dl>div,.status-list li{grid-template-columns:1fr;gap:4px}.cta-actions{justify-content:flex-start}.cert{padding:18px}.research-card p{font-size:19px}}
"""

# Motion layer: shader gradient, liquid glass, scroll-driven steps, tabs, flow diagram, marquee.
CSS += r"""
.hero{position:relative;isolation:isolate}
.shader{position:absolute;inset:0;z-index:-1;width:100%;height:100%;display:block}
.hero:before{z-index:0;opacity:.08}
.hero-inner{position:relative;z-index:1}
.hero-copy{position:relative}
.hero h1 .split-line,.section-heading h2 .split-line,.h2 .split-line,.cta-band h2 .split-line{padding-bottom:.06em}
.hero-visual{perspective:1200px}
.glass{background:linear-gradient(135deg,#ffffff24,#ffffff08 60%);-webkit-backdrop-filter:blur(20px) saturate(1.6);backdrop-filter:blur(20px) saturate(1.6);border:1px solid #ffffff33;box-shadow:inset 0 1px 0 #ffffff55,inset 0 -1px 0 #ffffff12,0 30px 70px #0000004d}
.glass-light{position:relative;overflow:hidden;background:linear-gradient(135deg,color-mix(in srgb,var(--surface),transparent 15%),color-mix(in srgb,var(--surface),transparent 45%));-webkit-backdrop-filter:blur(18px) saturate(1.4);backdrop-filter:blur(18px) saturate(1.4);border:1px solid color-mix(in srgb,var(--line),transparent 20%);box-shadow:inset 0 1px 0 #ffffff80,0 20px 50px #0000001a}
.glass-light:after,.cert:after{position:absolute;inset:0;background:radial-gradient(360px circle at var(--gx,20%) var(--gy,0%),#ffffff40,transparent 50%);content:"";opacity:.7;pointer-events:none;mix-blend-mode:soft-light}
.cert{position:relative;overflow:hidden;background:linear-gradient(140deg,#ffffff1c,#ffffff06 55%,#00000030);-webkit-backdrop-filter:blur(22px) saturate(1.7);backdrop-filter:blur(22px) saturate(1.7);border:1px solid #ffffff38;box-shadow:inset 0 1px 0 #ffffff59,inset 0 -1px 0 #ffffff14,0 40px 90px #0009;transform-style:preserve-3d;will-change:transform}
.cert-title,.cert-rows,.cert-foot,.cert-head,.cert-link{position:relative;z-index:1}
.tilt{transform-style:preserve-3d;will-change:transform}
.marquee{overflow:hidden;padding:16px 0;background:var(--lime);color:#141618}
.marquee-track{display:flex;width:max-content;align-items:center;gap:28px;will-change:transform}
.marquee-track span{font:700 22px/1 var(--sans);font-variation-settings:"wdth" 88;letter-spacing:-.01em;white-space:nowrap}
.marquee-track i{font-style:normal;font-size:14px}
.fact{display:grid;align-content:start;gap:10px;min-height:170px;padding:24px;border-top:0}
.fact .info-chip{position:absolute;top:16px;right:16px}
.fact p{font:400 17px/1.4 var(--text)}
.scrolly{padding:40px 0 80px}
.scrolly-inner{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:56px;align-items:start}
.scrolly-copy h2{margin:0 0 28px;font-size:clamp(34px,4.2vw,58px)}
.scrolly-steps{margin:0;padding:0;list-style:none}
.scrolly-step{min-height:44vh;display:flex;align-items:flex-start}
.scrolly-step:last-child{min-height:30vh}
.scrolly-step button{display:grid;grid-template-columns:44px minmax(0,1fr);gap:4px 14px;width:100%;padding:18px 0;border:0;border-top:1px solid var(--line);background:none;color:var(--muted);text-align:left;cursor:pointer;transition:color .3s}
.scrolly-step .step-no{grid-row:span 2;color:inherit;font:600 11px var(--mono);letter-spacing:.1em;padding-top:6px}
.scrolly-step b{font:680 28px/1.1 var(--sans);font-variation-settings:"wdth" 90;letter-spacing:-.02em}
.scrolly-step p{margin:0;font:400 17px/1.45 var(--text);opacity:.55;transition:opacity .3s}
.scrolly-step.is-active button{border-top-color:var(--ink);color:var(--ink)}
.scrolly-step.is-active .step-no{color:var(--blue)}
.scrolly-step.is-active p{opacity:1}
.scrolly-stage-wrap{position:sticky;top:calc(110px + env(safe-area-inset-top,0px))}
.scrolly-stage{min-height:380px;padding:32px}
.stage-panel{position:absolute;inset:32px 32px 44px;display:grid;place-items:center;opacity:0;visibility:hidden;transition:opacity .35s,visibility .35s}
.stage-panel.is-active{position:relative;inset:auto;min-height:300px;opacity:1;visibility:visible}
.stage-progress{position:absolute;right:32px;bottom:20px;left:32px;height:2px;background:var(--line)}
.stage-progress i{display:block;height:100%;background:var(--blue);transform:scaleX(var(--p,.25));transform-origin:left;transition:transform .4s var(--out)}
.vis-seal{display:grid;justify-items:center;gap:18px;width:100%}
.vault{position:relative;display:grid;gap:6px;width:min(260px,100%);padding:22px 18px 18px;border:2px solid var(--ink);border-radius:6px}
.vault-lid{position:absolute;top:-2px;right:-2px;left:-2px;height:10px;border:2px solid var(--ink);border-bottom:0;border-radius:6px 6px 0 0;background:var(--blue);transform-origin:left bottom}
.task-chip{display:block;padding:6px 10px;border:1px solid var(--line);background:var(--surface);font:500 11px var(--mono);font-style:normal}
.hash{color:var(--blue);font:500 11px var(--mono)}
.vis-train{position:relative;display:flex;align-items:flex-end;justify-content:center;gap:22px;width:100%;padding-bottom:10px}
.vis-train .ladder-dot{transform:none}
.train-curve{position:absolute;right:0;bottom:-6px;left:0;width:100%;height:60px;overflow:visible;pointer-events:none}
.train-curve path{fill:none;stroke:var(--blue);stroke-width:2;stroke-dasharray:1;stroke-dashoffset:0;vector-effect:non-scaling-stroke}
.vis-measure{display:grid;gap:18px;width:100%}
.vis-measure>div{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px 16px;align-items:baseline}
.vis-measure span{font:500 14px var(--sans)}
.vis-measure b{font:600 15px var(--mono)}
.vis-measure .dbar,.vis-measure .meter{grid-column:1/-1}
.vis-price{position:relative;width:100%}
.vis-price svg{width:100%;height:auto;overflow:visible}
.pr-axis{stroke:var(--ink)}.pr-band{fill:color-mix(in srgb,var(--gain),transparent 78%)}
.pr-fit{fill:none;stroke:var(--ink);stroke-width:2}.pr-forecast{fill:none;stroke:var(--gain);stroke-width:2;stroke-dasharray:5 4}
.pr-dot{fill:var(--ink)}.pr-target{fill:var(--gain);stroke:var(--surface);stroke-width:3}
.vis-price text{fill:var(--muted);font:500 10px var(--mono)}
.price-tag{position:absolute;top:0;right:0;padding:10px 14px;border:1px solid var(--ink);background:var(--surface);box-shadow:4px 4px 0 var(--ink)}
.price-tag b{display:block;font:700 28px/1 var(--sans);font-variation-settings:"wdth" 88}
.price-tag span{color:var(--muted);font:500 9.5px var(--mono);letter-spacing:.06em;text-transform:uppercase}
.split-section{padding-top:40px}
.split-grid{display:grid;grid-template-columns:1.25fr 1fr;gap:56px;align-items:start}
.h2{margin:0 0 22px;font:680 clamp(30px,3.4vw,46px)/1.02 var(--sans);font-variation-settings:"opsz" 96,"wdth" 90;letter-spacing:-.022em}
.h2>span{color:var(--blue)}
.seg-list{position:relative;display:inline-flex;flex-wrap:wrap;gap:2px;padding:4px;border-radius:999px}
.seg-list.glass{background:color-mix(in srgb,var(--surface),transparent 30%);border-color:var(--line);box-shadow:inset 0 1px 0 #ffffff70,0 8px 24px #0000000f}
.seg-tab{position:relative;z-index:1;padding:9px 16px;border:0;border-radius:999px;background:none;color:var(--muted);font:600 13px var(--sans);cursor:pointer;transition:color .25s}
.seg-tab[aria-selected=true]{color:var(--paper)}
.seg-ink{position:absolute;top:4px;left:0;z-index:0;width:var(--w,0);height:calc(100% - 8px);border-radius:999px;background:var(--ink);transform:translateX(var(--x,0))}
.seg-panels{margin-top:22px}
.metric{display:grid;gap:10px;padding:26px;border:1px solid var(--line);background:var(--surface)}
.metric-value{font:700 clamp(46px,5vw,72px)/1 var(--sans);font-variation-settings:"opsz" 96,"wdth" 86;letter-spacing:-.03em;color:var(--blue)}
.metric p{margin:0;font:400 19px/1.4 var(--text)}
.metric small{color:var(--muted);font:500 9.5px var(--mono);letter-spacing:.08em;text-transform:uppercase}
.ticks{display:grid;gap:14px;margin:0;padding:26px;border:1px solid var(--line);background:var(--surface);list-style:none}
.ticks li{position:relative;padding-left:30px;font:400 20px/1.35 var(--text)}
.ticks li:before{position:absolute;top:.25em;left:0;width:18px;height:18px;border-radius:50%;background:var(--lime) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23141618' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 12.5 10 16.5 18 8'/%3E%3C/svg%3E") center/12px no-repeat;content:""}
.flow{display:grid;grid-template-columns:1fr 1.2fr 1.1fr 1.2fr 1fr;align-items:center;gap:0;margin:10px 0 40px}
.flow-node{position:relative;display:grid;justify-items:center;gap:4px;padding:22px 12px;border:1px solid var(--line);background:var(--surface);text-align:center}
.flow-node b{font:650 17px var(--sans)}.flow-node small{color:var(--muted);font:500 9.5px var(--mono);letter-spacing:.06em;text-transform:uppercase}
.vault-node{aspect-ratio:1;align-content:center;border-radius:50%;border-color:var(--ink);background:var(--band);color:var(--band-ink)}
.vault-node small{color:var(--lime)}
.orbit{position:absolute;inset:-14px;border:1px dashed color-mix(in srgb,var(--blue),transparent 30%);border-radius:50%;animation:orbit-spin 18s linear infinite}
.orbit:after{position:absolute;top:8%;left:12%;width:8px;height:8px;border-radius:50%;background:var(--lime);content:""}
.orbit.is-outer{inset:-30px;border-style:solid;border-color:color-mix(in srgb,var(--line),transparent 10%);animation-duration:30s;animation-direction:reverse}
.flow-pipe{position:relative;height:2px;margin:0 6px;background:repeating-linear-gradient(90deg,var(--ink) 0 6px,transparent 6px 11px)}
.flow-pipe i{position:absolute;top:50%;left:0;padding:2px 6px;border:1px solid var(--ink);background:var(--surface);font:600 9.5px var(--mono);font-style:normal;transform:translate(-50%,-50%);animation:flow-move 3.6s linear infinite;animation-delay:calc(var(--n,0)*-1.2s)}
.flow-pipe i:nth-child(2){--n:1}.flow-pipe i:nth-child(3){--n:2}
.flow-pipe.is-out i{border-color:var(--blue);color:var(--blue)}
.cmp{border-top:2px solid var(--ink)}
.cmp-row{display:grid;grid-template-columns:minmax(0,1.3fr) repeat(3,minmax(0,1fr));align-items:center;gap:12px;padding:14px 6px;border-bottom:1px solid var(--line)}
.cmp-row>*:not(b){justify-self:center}
.cmp-head{color:var(--muted);font:500 9.5px var(--mono);letter-spacing:.08em;text-transform:uppercase}
.cmp-row b{font:600 15px var(--sans)}
.cmp-row.is-us{background:var(--blue-soft)}
.mark.is-yes{color:var(--gain)}.mark.is-no{color:color-mix(in srgb,var(--muted),transparent 40%)}
.research-card{display:grid;gap:12px;padding:28px}
.research-card>b{font:700 44px/1 var(--sans);font-variation-settings:"opsz" 96,"wdth" 86;letter-spacing:-.03em;color:var(--blue)}
.research-card p{position:relative;z-index:1;margin:0;font:400 20px/1.35 var(--text)}
.timeline{position:relative;margin:0;padding:0 0 0 28px;list-style:none}
.timeline:before{position:absolute;top:6px;bottom:6px;left:6px;width:2px;background:var(--line);content:""}
.timeline:after{position:absolute;top:6px;left:6px;width:2px;height:calc(var(--line-p,1)*(100% - 12px));background:var(--blue);content:""}
.timeline li{position:relative;display:grid;gap:4px;padding:0 0 26px}
.timeline li:before{position:absolute;top:6px;left:-27px;width:12px;height:12px;border:2px solid var(--blue);border-radius:50%;background:var(--paper);content:""}
.timeline b{font:650 20px var(--sans)}.timeline p{margin:0;max-width:640px;color:color-mix(in srgb,var(--ink),var(--muted) 45%);font:400 17px/1.5 var(--text)}
.cta-band{position:relative;isolation:isolate;overflow:hidden;padding:110px 0}
.cta-inner{position:relative;z-index:1}
.hero h1{max-width:none;font-size:clamp(44px,4.7vw,70px)}
.hero-copy{max-width:600px}
.h2{font-size:clamp(28px,2.9vw,40px)}.h2.is-large{font-size:clamp(34px,4vw,56px)}
.scrolly-copy h2{font-family:var(--sans)}
.detail-hero h1{font:680 clamp(44px,5.4vw,76px)/1 var(--sans);font-variation-settings:"opsz" 96,"wdth" 90;letter-spacing:-.022em}
.fact{min-height:0;padding:26px 26px 30px}
.cta-band .cta-note{margin-top:20px;color:var(--lime);font:600 10px var(--mono)!important;letter-spacing:.1em;text-transform:uppercase}
.button{min-height:54px;padding:0 8px 0 24px;gap:16px;border-radius:999px;font:650 14.5px var(--sans);letter-spacing:-.005em}
.button-lime{border:0;background:linear-gradient(180deg,#ebca78,#cfa646);color:#141618;box-shadow:inset 0 1px 0 #ffffff80,inset 0 -2px 0 #00000014,0 1px 0 #8a6a23,0 12px 28px #c9a24a4d}
.button-lime:hover{background:linear-gradient(180deg,#f1d388,#d6ae50);box-shadow:inset 0 1px 0 #ffffff80,0 1px 0 #8a6a23,0 18px 36px #c9a24a73}
.button-lime .button-arrow,.button-ring .button-arrow{display:grid;width:38px;height:38px;place-items:center;border-radius:50%;font-size:15px;transition:transform .35s var(--spring)}
.button-lime .button-arrow{background:#141618;color:#ebca78}
.button-lime:hover .button-arrow{transform:rotate(-45deg)}
.button-ring{border:1px solid #ffffff47;background:#ffffff12;-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);color:#f6f7ed}
.button-ring .button-arrow{border:1px solid currentColor}
.button-ring:hover{border-color:var(--lime);background:#ffffff1f;color:#fff}
.button-outline{border:1.5px solid var(--ink)}
.nav-cta{padding:12px 20px;border:0;background:linear-gradient(180deg,#ebca78,#cfa646);color:#141618;font-size:12.5px;font-weight:700;box-shadow:inset 0 1px 0 #ffffff80,0 1px 0 #8a6a23,0 8px 18px #c9a24a40}
.nav-cta:hover{background:linear-gradient(180deg,#f1d388,#d6ae50);color:#141618}
@keyframes orbit-spin{to{transform:rotate(360deg)}}
@keyframes flow-move{from{left:0}to{left:100%}}
@media(max-width:680px){.scrolly-inner,.split-grid{grid-template-columns:1fr;gap:28px}.scrolly-stage-wrap{position:sticky;top:calc(70px + env(safe-area-inset-top,0px));z-index:2;order:-1}.scrolly-step{min-height:32vh}.scrolly-stage{min-height:0;padding:14px 16px 24px;background:var(--surface)}.stage-panel.is-active{min-height:190px}.stage-panel{inset:14px 16px 24px}.vis-train .ladder-rung{transform:scale(.8)}.price-tag b{font-size:20px}.flow{grid-template-columns:1fr;gap:26px;justify-items:center}.flow-node{width:100%}.vault-node{width:160px}.flow-pipe{width:2px;height:40px;margin:0;background:repeating-linear-gradient(180deg,var(--ink) 0 6px,transparent 6px 11px)}.flow-pipe i{display:none}.cmp-row{grid-template-columns:minmax(0,1.2fr) repeat(3,minmax(0,1fr));gap:6px;font-size:13px}.cmp-head{font-size:8px}.marquee-track span{font-size:18px}.fact{min-height:0}}
@media(prefers-reduced-motion:reduce){.orbit,.flow-pipe i{animation:none}}
"""

# Type system and the dark, immersive home page.
CSS += r"""
:root{--sans:"Mona Sans","Helvetica Neue",Arial,sans-serif;--text:"Mona Sans","Helvetica Neue",Arial,sans-serif;--mono:"Geist Mono",ui-monospace,Menlo,monospace;--display:"Instrument Serif",Georgia,serif}
body{font-family:var(--sans);letter-spacing:-.005em}
h1 em,h2 em,.h2 em{font-family:var(--display);font-style:italic;font-weight:400;letter-spacing:-.01em}
.is-home{--paper:#0a0c0f;--surface:#12151a;--ink:#eef0f3;--muted:#8d949e;--line:#242a33;--blue:#e3bf68;--blue-soft:#221d12;--lime:#e3bf68;--band:#0a0c0f;--band-ink:#eef0f3;--band-muted:#9aa1aa;--gain:#d9b45a;--loss:#5a92d6;--risk:#ef8466;background:var(--paper);color:var(--ink)}
.is-home .site-nav{border-bottom-color:#ffffff12;background:color-mix(in srgb,var(--paper),transparent 20%)}
.is-home .wordmark{color:var(--ink)}
.is-home .nav-search{background:#ffffff0a;border-color:#ffffff1f}
.is-home .footer{border-top-color:var(--line)}
.is-home h1,.is-home h2,.is-home h3{font-family:var(--sans);font-style:normal;text-wrap:balance}
.is-home h1 em,.is-home h2 em{color:var(--lime)}
.t-hero{position:relative;isolation:isolate;overflow:hidden;background:var(--paper)}
.t-hero:after{position:absolute;inset:auto 0 0;height:160px;background:linear-gradient(transparent,var(--paper));content:"";pointer-events:none}
.t-hero-inner{position:relative;z-index:1;display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr);align-items:center;gap:56px;min-height:min(820px,calc(100vh - 76px));padding-top:80px;padding-bottom:120px}
.t-pill{display:inline-flex;align-items:center;gap:10px;margin:0 0 26px;padding:7px 14px 7px 10px;border:1px solid #ffffff24;border-radius:999px;background:#ffffff0d;color:#d6dbe1;font:500 11px var(--mono);letter-spacing:.12em;text-transform:uppercase;-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.t-pill i{position:relative;width:8px;height:8px;border-radius:50%;background:var(--lime)}
.t-pill i:after{position:absolute;inset:-4px;border:1px solid var(--lime);border-radius:50%;content:"";animation:pill-ping 2s ease-out infinite}
.t-hero h1{margin:0;color:#fff;font:780 clamp(46px,4.9vw,76px)/1 var(--sans);font-variation-settings:"wdth" 104;letter-spacing:-.035em}
.t-hero h1 em{font-size:1.06em}
.t-lede{max-width:520px;margin:26px 0 0;color:#b9c0c9;font:400 19px/1.55 var(--sans)}
.t-actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:34px}
.t-console{position:relative;border-radius:16px;background:linear-gradient(160deg,#ffffff14,#ffffff05 60%);overflow:hidden}
.t-console-bar{display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid #ffffff14;color:#9aa1aa;font:500 11px var(--mono)}
.t-console-bar .lights{gap:7px}.t-console-bar .light{cursor:default}
.t-console-bar em{margin-left:auto;padding:2px 8px;border:1px solid #ffffff24;border-radius:999px;font-style:normal;font-size:10px;letter-spacing:.08em;text-transform:uppercase}
.t-console-body{position:relative;min-height:340px;padding:22px 24px 26px;color:#d9dee4;font:400 13px/1.5 var(--mono)}
.c-run{display:none}.c-run.is-active{display:block}
.c-line{display:flex;align-items:baseline;gap:8px;margin:0 0 12px}
.c-line b{color:#fff;font-weight:600}
.c-prompt{color:var(--lime)}
.c-ok,.c-flag{margin-left:auto;color:#9aa1aa;white-space:nowrap}
.c-ok{color:var(--lime)}
.c-flag.is-bad{color:var(--risk)}.c-flag.is-good{color:var(--lime)}
.c-bars{display:grid;gap:7px;margin:-2px 0 14px 18px}
.c-bar{display:grid;grid-template-columns:22px minmax(0,1fr);align-items:center;gap:8px;color:#7d8590;font-size:11px}
.c-bar em{font-style:normal}
.c-bar i{display:block;width:var(--w);height:6px;border-radius:3px;background:linear-gradient(90deg,#a78232,#ebca78);transform-origin:left}
.c-verdict{display:inline-block;margin:8px 0 0;padding:9px 16px;border:2px solid currentColor;border-radius:6px;font:800 15px var(--sans);font-variation-settings:"wdth" 110;letter-spacing:.06em;text-transform:uppercase;transform:rotate(-2deg)}
.c-verdict.is-bad{color:var(--risk)}.c-verdict.is-good{color:var(--lime)}
.is-home .marquee{background:var(--lime)}
.t-kicker{display:inline-flex;align-items:center;gap:10px;margin:0 0 18px;color:var(--lime);font:500 11px var(--mono);letter-spacing:.14em;text-transform:uppercase}
.t-kicker:before{width:18px;height:1px;background:currentColor;content:""}
.t-statement{padding-top:150px;padding-bottom:40px}
.t-scrub{max-width:1040px;margin:0;font:680 clamp(30px,3.6vw,54px)/1.18 var(--sans);font-variation-settings:"wdth" 104;letter-spacing:-.028em}
.t-section{padding-top:110px;padding-bottom:20px}
.t-head{margin-bottom:44px}
.t-head-split{display:flex;align-items:flex-end;justify-content:space-between;gap:32px}
.t-head-split>p{max-width:360px;margin:0;color:var(--muted);font:400 16px/1.5 var(--sans)}
.is-home h2{margin:0;font:760 clamp(36px,4.3vw,64px)/1.02 var(--sans);font-variation-settings:"wdth" 106;letter-spacing:-.032em}
.is-home .h2{font-size:clamp(30px,3vw,44px)}.is-home .h2.is-large{font-size:clamp(36px,4.3vw,64px)}
.t-card,.bento-tile,.t-plan,.glass-panel{position:relative;overflow:hidden;border:1px solid #ffffff17;border-radius:18px;background:linear-gradient(170deg,#ffffff0e,#ffffff03 70%);box-shadow:inset 0 1px 0 #ffffff14}
.t-card:after,.bento-tile:after,.t-plan:after{position:absolute;inset:0;background:radial-gradient(420px circle at var(--gx,50%) var(--gy,0%),#e3bf6824,transparent 55%);content:"";opacity:0;pointer-events:none;transition:opacity .3s}
.t-card:hover:after,.bento-tile:hover:after,.t-plan:hover:after{opacity:1}
.t-card:hover,.bento-tile:hover,.t-plan:hover{border-color:#e3bf6852}
.t-problems{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}
.t-card{display:grid;align-content:start;gap:12px;padding:30px;color:var(--ink);text-decoration:none}
.t-icon{display:grid;width:46px;height:46px;place-items:center;margin-bottom:10px;border-radius:12px;background:var(--blue-soft);color:var(--lime);font:600 20px var(--mono)}
.t-card b{font:780 34px/1.05 var(--sans);font-variation-settings:"wdth" 104;letter-spacing:-.025em}
.t-card p{margin:0;color:var(--muted);font:400 16px/1.45 var(--sans)}
.t-card small{color:var(--lime);font:500 11px var(--mono);letter-spacing:.06em}
.t-card .info-chip{position:absolute;top:22px;right:22px;background:transparent;border-color:#ffffff30;color:var(--ink)}
.is-home .scrolly{padding:120px 0 60px}
.is-home .scrolly-step button{border-top-color:var(--line)}
.is-home .scrolly-step b{font-family:var(--sans);font-variation-settings:"wdth" 104}
.is-home .scrolly-step p{font-family:var(--sans);font-size:16px}
.glass-panel{-webkit-backdrop-filter:blur(18px);backdrop-filter:blur(18px)}
.is-home .vault,.is-home .vault-lid{border-color:#eef0f3}
.is-home .price-tag{border-color:#eef0f3;box-shadow:4px 4px 0 var(--lime)}
.bento{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));grid-auto-rows:250px;gap:18px}
.bento-tile{display:grid;grid-template-rows:auto 1fr;gap:16px;padding:28px}
.bento-tile.is-wide{grid-column:span 2}
.bento-tile h3{margin:0 0 6px;font:740 23px/1.1 var(--sans);font-variation-settings:"wdth" 104;letter-spacing:-.02em}
.bento-tile p{margin:0;max-width:360px;color:var(--muted);font:400 15px/1.45 var(--sans)}
.b-art{position:relative;align-self:end}
.b-rise{width:100%;height:90px;overflow:visible}
.b-rise path{fill:none;stroke:var(--lime);stroke-width:3;stroke-linecap:round;stroke-dasharray:1;animation:draw-loop 4s ease-in-out infinite}
.b-rise circle{fill:var(--lime);animation:dot-pop 4s ease-in-out infinite}
.b-exploit{display:flex;align-items:center;gap:10px}
.b-exploit i{width:14px;height:14px;border-radius:4px;background:#ffffff1a;animation:bug-blink 2.4s infinite}
.b-exploit i:nth-child(2){animation-delay:.4s}.b-exploit i:nth-child(3){animation-delay:.8s}
.b-exploit b{margin-left:6px;padding:4px 10px;border:1px solid var(--risk);border-radius:999px;color:var(--risk);font:600 12px var(--mono)}
.b-venn{height:80px}
.b-venn i{position:absolute;top:6px;width:68px;height:68px;border-radius:50%;border:2px solid var(--lime);background:#e3bf6814}
.b-venn i:first-child{left:0;animation:venn-l 3.5s ease-in-out infinite}.b-venn i:nth-child(2){left:44px;border-color:#5a92d6;background:#5a92d614;animation:venn-r 3.5s ease-in-out infinite}
.b-venn b{position:absolute;top:28px;left:130px;font:700 22px var(--mono);color:var(--ink)}
.b-scale{display:flex;align-items:flex-end;gap:10px;height:90px}
.b-scale i{width:26px;border-radius:6px 6px 2px 2px;background:linear-gradient(180deg,#ebca78,#a78232);animation:bar-grow 3s ease-in-out infinite;transform-origin:bottom}
.b-scale i:nth-child(1){height:25%}.b-scale i:nth-child(2){height:45%;animation-delay:.15s}.b-scale i:nth-child(3){height:68%;animation-delay:.3s}.b-scale i:nth-child(4){height:95%;animation-delay:.45s}
.b-price{display:flex;align-items:baseline;gap:14px}
.b-price b{color:var(--lime);font:800 44px/1 var(--sans);font-variation-settings:"wdth" 104}
.b-price s{position:relative;color:var(--muted);font:500 18px var(--mono);text-decoration:none}
.b-price s:after{position:absolute;top:50%;left:-4px;right:-4px;height:2px;background:var(--risk);content:"";transform:scaleX(0);transform-origin:left;animation:strike 3s ease-in-out infinite}
.compare{padding:32px}
.cmp-bars{display:grid;gap:16px;margin-top:28px}
.cmp-bar{display:grid;grid-template-columns:220px minmax(0,1fr) 90px;align-items:center;gap:18px}
.cmp-bar span{font:600 15px var(--sans)}
.cmp-bar i{display:block;width:var(--w);height:16px;border-radius:8px;background:linear-gradient(90deg,#a78232,#ebca78);box-shadow:0 0 24px #e3bf6833;transition:width .8s var(--out)}
.cmp-bar b{font:600 14px var(--mono);text-align:right}
.cmp-note{margin:24px 0 0;color:var(--lime);font:500 13px var(--mono)}
.is-home .seg-list.glass{background:#ffffff0a;border-color:#ffffff1f;box-shadow:none}
.is-home .seg-tab{color:var(--muted)}
.is-home .seg-tab[aria-selected=true]{color:#0a0c0f}
.is-home .seg-ink{background:var(--lime)}
.t-two{display:grid;grid-template-columns:1fr 1fr;gap:64px;align-items:start}
.is-home .ticks{border-radius:18px;border-color:#ffffff17;background:linear-gradient(170deg,#ffffff0e,#ffffff03 70%)}
.is-home .ticks li{font:500 18px/1.4 var(--sans)}
.quad{position:relative;aspect-ratio:1.25;margin-top:6px;border-left:1px solid var(--line);border-bottom:1px solid var(--line);background:linear-gradient(var(--line) 1px,transparent 1px) 0 0/25% 25%,linear-gradient(90deg,var(--line) 1px,transparent 1px) 0 0/25% 25%;background-color:#ffffff03}
.q-axis{position:absolute;color:var(--muted);font:500 10px var(--mono);letter-spacing:.1em;text-transform:uppercase}
.q-x{right:0;bottom:-24px}.q-y{top:0;left:-8px;transform:rotate(-90deg) translateX(-100%);transform-origin:top left}
.q-point span{white-space:nowrap}.q-point.is-left{flex-direction:row-reverse;transform:translate(calc(-100% + 7px),7px)}.q-point.is-us.is-left{transform:translate(calc(-100% + 9px),9px)}.q-point{position:absolute;left:var(--x);bottom:var(--y);display:flex;align-items:center;gap:8px;padding:0;border:0;background:none;color:var(--ink);font:600 13px var(--sans);transform:translate(-7px,7px);cursor:help}
.q-point i{width:14px;height:14px;border:2px solid var(--muted);border-radius:50%;background:var(--paper)}
.q-point.is-us{color:var(--lime);font-size:15px}
.q-point.is-us i{width:18px;height:18px;border-color:var(--lime);background:var(--lime);box-shadow:0 0 0 6px #e3bf6826,0 0 30px #e3bf6880;animation:us-pulse 2.4s ease-in-out infinite}
.q-hint{margin:34px 0 0;color:var(--muted);font:500 11px var(--mono)}
.t-research,.t-plans{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.t-card.research b{color:var(--lime);font-size:58px}
.t-card.research p{color:var(--ink);font-size:20px}
.t-plan{display:grid;align-content:start;gap:14px;padding:34px}
.t-plan h3{margin:0;font:760 30px/1.1 var(--sans);font-variation-settings:"wdth" 104;letter-spacing:-.025em}
.t-plan>p:not(.t-kicker){margin:0;color:var(--muted);font:400 16px var(--sans)}
.t-plan .ticks{padding:0;border:0;background:none}
.t-plan .ticks li{font-size:16px}
.t-plan .button{justify-self:start;margin-top:8px}
.t-plan.is-featured{border-color:#e3bf6866;background:linear-gradient(170deg,#e3bf681f,#ffffff03 70%)}
.roadmap{position:relative;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:18px;margin:0;padding:34px 0 0;list-style:none}
.roadmap:before{position:absolute;top:8px;right:0;left:0;height:2px;background:linear-gradient(90deg,var(--lime) 30%,var(--line) 30%);content:""}
.roadmap li{position:relative;display:grid;align-content:start;gap:8px}
.roadmap li:before{position:absolute;top:-32px;left:0;width:14px;height:14px;border:2px solid var(--line);border-radius:50%;background:var(--paper);content:""}
.roadmap .rm-done:before{border-color:var(--lime);background:var(--lime)}
.roadmap .rm-now:before{border-color:var(--lime);box-shadow:0 0 0 6px #e3bf6826;animation:us-pulse 2.4s infinite}
.roadmap em{justify-self:start;padding:3px 10px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font:500 10px var(--mono);font-style:normal;letter-spacing:.1em;text-transform:uppercase}
.roadmap .rm-done em,.roadmap .rm-now em{border-color:var(--lime);color:var(--lime)}
.roadmap b{font:700 17px/1.25 var(--sans)}
.roadmap p{margin:0;color:var(--muted);font:400 14px/1.45 var(--sans)}
.is-home .cta-band{margin-top:120px;padding:140px 0;text-align:left}
.is-home .cta-band h2{font-size:clamp(46px,6vw,96px);color:#fff}
.is-home .cta-band .cta-note{margin-top:22px}
.is-home .cta-band p.t-kicker{max-width:none;margin:0 0 18px;color:var(--lime);font:500 11px var(--mono);letter-spacing:.14em}
.t-hero{background:radial-gradient(60% 70% at 78% 30%,#e3bf6822,transparent 70%),radial-gradient(50% 60% at 15% 80%,#2a4a6e33,transparent 70%),var(--paper)}
.is-home .marquee{padding:12px 0}
.is-home .marquee-track{gap:22px}
.is-home .marquee-track span{font:650 15px/1 var(--sans);font-variation-settings:"wdth" 100;letter-spacing:.01em}
.is-home .marquee-track i{font-size:10px}
.t-statement{padding-top:110px;padding-bottom:10px}
.t-section{padding-top:90px}
.is-home .scrolly{padding:90px 0 30px}
.is-home .scrolly-step{min-height:30vh}
.is-home .scrolly-step:last-child{min-height:22vh}
.bento{grid-auto-rows:minmax(210px,auto)}
.bento-tile.is-wide .b-rise{height:110px}
.is-home .cta-band{margin-top:90px;padding:110px 0}
.why-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}
.why-card{position:relative;display:grid;align-content:start;gap:6px;padding:30px;border-top:2px solid var(--lime);background:linear-gradient(180deg,#e3bf6812,transparent 70%)}
.why-card b{color:#fff;font:800 clamp(52px,5vw,76px)/1 var(--sans);font-variation-settings:"wdth" 100;letter-spacing:-.04em}
.why-card span{color:var(--lime);font:500 11px var(--mono);letter-spacing:.1em;text-transform:uppercase}
.why-card p{margin:10px 0 0;color:var(--muted);font:400 15px/1.45 var(--sans)}
.market{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr);gap:40px;align-items:start}
.market-figure{display:grid;gap:14px;padding:34px}
.market-figure small{color:var(--lime);font:500 11px var(--mono);letter-spacing:.1em;text-transform:uppercase}
.market-figure b{font:800 clamp(52px,6vw,92px)/1 var(--sans);font-variation-settings:"wdth" 96;letter-spacing:-.045em;background:linear-gradient(90deg,#fff,#ebca78);-webkit-background-clip:text;background-clip:text;color:transparent}
.market-figure p{margin:0;max-width:560px;color:var(--muted);font:400 16px/1.5 var(--sans)}
.market-bar{display:grid;gap:10px;margin-top:10px}
.market-bar i{position:relative;display:block;width:var(--w);min-width:8px;height:30px;border-radius:6px;background:#ffffff14}
.market-bar i.is-us{background:var(--lime);box-shadow:0 0 20px #e3bf6888}
.market-bar span{position:absolute;top:50%;left:12px;color:var(--ink);font:500 11px var(--mono);white-space:nowrap;transform:translateY(-50%)}
.market-bar i.is-us span{left:calc(100% + 12px);color:var(--lime)}
.moat{display:grid;gap:12px}
.moat-card{padding:18px 20px;border:1px solid #ffffff17;border-left:3px solid var(--lime);border-radius:10px;background:#ffffff06;transition:transform .25s var(--out),background .25s}
.moat-card:hover{transform:translateX(6px);background:#e3bf6810}
.moat-card b{display:block;font:700 17px var(--sans)}
.moat-card p{margin:4px 0 0;color:var(--muted);font:400 14px/1.45 var(--sans)}
.faq details{border-top:1px solid var(--line)}
.faq details:last-child{border-bottom:1px solid var(--line)}
.faq summary{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:22px 4px;font:650 clamp(18px,1.8vw,22px)/1.3 var(--sans);cursor:pointer;list-style:none}
.faq summary::-webkit-details-marker{display:none}
.faq summary i{position:relative;flex:none;width:28px;height:28px;border:1px solid var(--line);border-radius:50%;transition:transform .35s var(--spring),background .2s}
.faq summary i:before,.faq summary i:after{position:absolute;top:50%;left:50%;width:11px;height:1.5px;margin:-.75px 0 0 -5.5px;background:var(--ink);content:""}
.faq summary i:after{transform:rotate(90deg)}
.faq details[open] summary i{background:var(--lime);border-color:var(--lime);transform:rotate(45deg)}
.faq details[open] summary i:before,.faq details[open] summary i:after{background:#0a0c0f}
.faq summary:hover{color:var(--lime)}
.faq-a{overflow:hidden}
.faq-a p{margin:0;max-width:720px;padding:0 4px 24px;color:var(--muted);font:400 17px/1.55 var(--sans)}
.person small{color:var(--lime);font:500 11px var(--mono);letter-spacing:.08em;text-transform:uppercase}
.person a{color:var(--lime);font:500 12px var(--mono);text-decoration:none}
@media(max-width:680px){.why-grid,.market{grid-template-columns:1fr}.is-home .scrolly-step{min-height:26vh}}
@keyframes pill-ping{0%{opacity:.9;transform:scale(.6)}100%{opacity:0;transform:scale(1.8)}}
@keyframes draw-loop{0%{stroke-dashoffset:1}45%,80%{stroke-dashoffset:0}100%{stroke-dashoffset:-1}}
@keyframes dot-pop{0%,40%{opacity:0;transform:scale(0)}50%,85%{opacity:1;transform:scale(1)}100%{opacity:0}}
@keyframes bug-blink{0%,60%,100%{background:#ffffff1a}70%,90%{background:var(--risk);box-shadow:0 0 14px var(--risk)}}
@keyframes venn-l{50%{transform:translateX(10px)}}@keyframes venn-r{50%{transform:translateX(-10px)}}
@keyframes bar-grow{0%,100%{transform:scaleY(.35)}50%{transform:scaleY(1)}}
@keyframes strike{0%,30%{transform:scaleX(0)}50%,90%{transform:scaleX(1)}100%{transform:scaleX(0)}}
@keyframes us-pulse{50%{box-shadow:0 0 0 10px #e3bf6814,0 0 40px #e3bf6899}}
@media(max-width:680px){.t-hero-inner,.t-two{grid-template-columns:1fr;gap:40px;min-height:0;padding-top:48px;padding-bottom:80px}.t-problems,.bento,.t-research,.t-plans,.roadmap{grid-template-columns:1fr}.bento{grid-auto-rows:auto}.bento-tile{min-height:210px}.bento-tile.is-wide{grid-column:auto}.t-head-split{display:block}.t-head-split>p{margin-top:16px}.cmp-bar{grid-template-columns:1fr 64px;gap:6px 12px}.cmp-bar span{grid-column:1/-1}.roadmap{padding:0 0 0 30px}.roadmap:before{top:0;bottom:0;left:6px;right:auto;width:2px;height:auto;background:linear-gradient(var(--lime) 30%,var(--line) 30%)}.roadmap li:before{top:2px;left:-30px}.t-statement{padding-top:90px}.t-section{padding-top:80px}.t-console-body{min-height:320px;font-size:12px}.quad{margin-left:14px}}
@media(prefers-reduced-motion:reduce){.t-pill i:after,.b-rise path,.b-rise circle,.b-exploit i,.b-venn i,.b-scale i,.b-price s:after,.q-point.is-us i,.roadmap .rm-now:before{animation:none}.b-rise path{stroke-dashoffset:0}}
"""

# Wider than a phone means the desktop layout, scaled to fit; only phones reflow.
CSS = CSS.replace("@media(max-width:900px)", "@media(max-width:680px)").replace("@media(max-width:850px)", "@media(max-width:680px)")
CSS = CSS.replace("@media(min-width:851px)", "@media(min-width:681px)")

# One committed light look: drop every dark token block so no host or system setting can flip it.
CSS = re.sub(r":root\[data-theme=dark\]\{[^}]*\}", "", CSS) + ":root{color-scheme:light}\n"
CSS += r"""
.site-nav{top:env(safe-area-inset-top,0px)}
body{font-variant-emoji:text}
html.is-scaled .scale-frame{overflow:clip}
html.is-scaled .scale-page{width:var(--design-width);transform:scale(var(--page-scale));transform-origin:0 0}
.icon{display:block;flex:none}
.detail-hero{color:#f4f1e9}
.nav-action{color:var(--ink)}
.nav-search .icon{display:none}
@media(max-width:680px){.nav-search{width:38px;justify-content:center;padding:0}.nav-search kbd,.nav-search span{display:none}.nav-search .icon{display:block}}
.info-chip{font-size:0}
.info-chip:before,.info-chip:after{position:absolute;inset:auto;top:50%;left:50%;width:10px;height:1.5px;margin:-.75px 0 0 -5px;border:0;border-radius:1px;background:currentColor;content:"";opacity:1;animation:none}
.info-chip:after{transform:rotate(90deg)}
.ledger-stat{align-self:stretch}
.ledger-scale{transform:none}
.ledger-stat .info-chip{top:-27px;right:12px;width:24px;height:24px}
@media(max-width:680px){.ledger-stat{padding-top:38px!important}.ledger-stat .info-chip{top:8px;right:6px}.button-kbd kbd{display:none}.eyebrow{letter-spacing:.06em}.chart-legend{display:grid;grid-template-columns:1fr 1fr}.legend-item span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}

.notice-stack{bottom:calc(20px + env(safe-area-inset-bottom,0px))}
.pop-dock{padding-bottom:env(safe-area-inset-bottom,0px)}
.toast{bottom:calc(24px + env(safe-area-inset-bottom,0px))}
@media(max-width:680px){.notice-stack{bottom:calc(12px + env(safe-area-inset-bottom,0px))}.pop-window,.pop-window.is-wide{bottom:calc(8px + env(safe-area-inset-bottom,0px))}}
"""

LIBRARIES = "".join(f'<script src="{url}"></script>' for url in (
    "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/gsap.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/ScrollTrigger.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/SplitText.min.js",
    "https://cdn.jsdelivr.net/npm/motion@11.18.2/dist/motion.js",
))

DESIGN_WIDTH = 1280
SCALE_BOOT = f"""(function(){{var r=document.documentElement,w=r.clientWidth||innerWidth;if(w>680&&w<{DESIGN_WIDTH}){{r.classList.add('is-scaled');r.style.setProperty('--design-width','{DESIGN_WIDTH}px');r.style.setProperty('--page-scale',w/{DESIGN_WIDTH});r.dataset.scale=w/{DESIGN_WIDTH}}}}})()"""

SCRIPT = r"""
(() => {
  const root = document.documentElement;
  const toast = document.querySelector('.toast');
  const themeToggle = document.querySelector('[data-theme-toggle]');
  let toastTimer;
  const notify = message => {
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2300);
  };
  try {
    const saved = localStorage.getItem('touchstone-theme');
    if (saved === 'dark' || saved === 'light') root.dataset.theme = saved;
  } catch (error) { console.error('Unable to read the saved theme preference.', error); }
  const currentTheme = () => root.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  const updateThemeLabel = () => {
    themeToggle?.setAttribute('aria-label', `Switch to ${currentTheme() === 'dark' ? 'light' : 'dark'} theme`);
  };
  updateThemeLabel();
  themeToggle?.addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    const apply = () => {
      root.dataset.theme = next;
      try { localStorage.setItem('touchstone-theme', next); }
      catch (error) { console.error('Unable to save the theme preference.', error); }
      updateThemeLabel();
    };
    const bounds = themeToggle.getBoundingClientRect();
    root.style.setProperty('--vt-x', `${bounds.left + bounds.width / 2}px`);
    root.style.setProperty('--vt-y', `${bounds.top + bounds.height / 2}px`);
    themeToggle.classList.toggle('is-turning');
    if (document.startViewTransition && !matchMedia('(prefers-reduced-motion: reduce)').matches) document.startViewTransition(apply);
    else apply();
  });
  // Embedded frames (such as a shared artifact) block printing, so the print buttons only show on a standalone page.
  document.querySelectorAll('[data-print]').forEach(button => {
    if (window.self !== window.top) button.hidden = true;
    else button.addEventListener('click', () => window.print());
  });
  document.querySelector('[data-menu]')?.addEventListener('click', event => {
    const nav = document.querySelector('.nav-links');
    const open = nav.classList.toggle('open');
    event.currentTarget.setAttribute('aria-expanded', String(open));
  });
  document.querySelectorAll('.window').forEach(windowCard => {
    windowCard.querySelectorAll('[data-minimize]').forEach(button => button.addEventListener('click', () => windowCard.classList.toggle('is-minimized')));
    windowCard.querySelector('[data-zoom]')?.addEventListener('click', () => {
      windowCard.classList.remove('is-minimized');
      windowCard.style.zIndex = '20';
    });
    windowCard.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => {
      windowCard.classList.add('is-closed');
      document.querySelector(`[data-restore="${windowCard.dataset.window}"]`)?.classList.add('visible');
    }));
    document.querySelector(`[data-restore="${windowCard.dataset.window}"]`)?.addEventListener('click', event => {
      windowCard.classList.remove('is-closed', 'is-minimized');
      event.currentTarget.classList.remove('visible');
    });
  });
  const dialog = document.querySelector('#about-dialog');
  document.querySelectorAll('[data-open-dialog]').forEach(button => button.addEventListener('click', () => dialog?.showModal()));
  document.querySelectorAll('[data-close-dialog]').forEach(button => button.addEventListener('click', () => dialog?.close()));
  dialog?.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  document.querySelectorAll('[data-copy]').forEach(button => button.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(button.dataset.copy); notify('Fingerprint copied to clipboard'); }
    catch (error) { console.error('Unable to copy the environment fingerprint.', error); notify('Copy unavailable in this browser'); }
  }));
  const cards = [...document.querySelectorAll('.result-card')];
  const search = document.querySelector('#appraisal-search');
  const filters = [...document.querySelectorAll('[data-filter]')];
  let grade = 'all';
  const applyFilters = () => {
    const query = search?.value.trim().toLocaleLowerCase() || '';
    cards.forEach(card => {
      card.hidden = !card.dataset.search.includes(query) || (grade !== 'all' && card.dataset.grade !== grade);
    });
    const empty = document.querySelector('.empty-state');
    if (empty) empty.hidden = cards.some(card => !card.hidden);
  };
  search?.addEventListener('input', applyFilters);
  filters.forEach(button => button.addEventListener('click', () => {
    grade = button.dataset.filter;
    filters.forEach(filter => {
      const active = filter === button;
      filter.classList.toggle('active', active);
      filter.setAttribute('aria-pressed', String(active));
    });
    applyFilters();
  }));
  const tooltip = document.querySelector('.chart-tooltip');
  const showChartPoint = point => {
    if (!tooltip) return;
    tooltip.replaceChildren();
    const title = document.createElement('b');
    title.textContent = `${point.dataset.name} · Grade ${point.dataset.grade}`;
    const values = document.createElement('span');
    values.textContent = `Forecast ${point.dataset.forecast} pts · Actual ${point.dataset.actual} pts`;
    const interval = document.createElement('span');
    interval.textContent = `90% forecast range ${point.dataset.low} to ${point.dataset.high} pts`;
    tooltip.append(title, values, interval);
    tooltip.classList.add('visible');
  };
  document.querySelectorAll('[data-chart-point]').forEach(point => {
    point.addEventListener('pointerenter', () => showChartPoint(point));
    point.addEventListener('focusin', () => showChartPoint(point));
    point.addEventListener('pointerleave', () => {
      if (!point.matches(':focus')) tooltip?.classList.remove('visible');
    });
    point.addEventListener('focusout', () => tooltip?.classList.remove('visible'));
  });
})();
"""

SCRIPT += r"""
(() => {
  // Floating layers live outside the scaled page so they keep their natural size and fixed positioning.
  document.querySelectorAll('.pop-window,.notice-stack').forEach(layer => document.body.append(layer));
  const root = document.documentElement;
  const frame = document.querySelector('.scale-frame'), page = document.querySelector('.scale-page');
  const designWidth = parseFloat(getComputedStyle(root).getPropertyValue('--design-width')) || 1280;
  const fitPage = () => {
    const width = root.clientWidth;
    const scaled = width > 680 && width < designWidth;
    const scale = scaled ? width / designWidth : 1;
    root.classList.toggle('is-scaled', scaled);
    root.style.setProperty('--design-width', `${designWidth}px`);
    root.style.setProperty('--page-scale', String(scale));
    root.dataset.scale = String(scale);
    frame.style.height = scaled ? `${page.offsetHeight * scale}px` : '';
  };
  fitPage();
  addEventListener('resize', fitPage);
  if ('ResizeObserver' in window) new ResizeObserver(fitPage).observe(page);
})();

(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Pointer distances measured on screen shrink with the page; divide them back into page pixels.
  const pageScale = element => (element.closest('.scale-page') ? Number(document.documentElement.dataset.scale || 1) : 1);
  const finePointer = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const clamp = (value, low, high) => Math.min(Math.max(value, low), high);

  const replay = element => { element.classList.remove('viz-on'); void element.offsetWidth; element.classList.add('viz-on'); };
  const countUp = element => {
    const node = [...element.childNodes].find(child => child.nodeType === 3 && /\d/.test(child.textContent));
    const match = node?.textContent.match(/^(.*?)([+\-−]?)([\d,]*\.?\d+)(.*)$/s);
    if (!match || reduced) return;
    const original = node.textContent;
    const [, before, sign, digits, after] = match;
    const target = parseFloat(digits.replace(/,/g, ''));
    const decimals = (digits.split('.')[1] || '').length;
    const format = value => before + sign + value.toLocaleString('en-US', {
      minimumFractionDigits: decimals, maximumFractionDigits: decimals, useGrouping: digits.includes(',')
    }) + after;
    const start = performance.now();
    const step = now => {
      const progress = Math.min(1, (now - start) / 1100);
      node.textContent = progress < 1 ? format(target * (1 - Math.pow(1 - progress, 4))) : original;
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  const outsidePops = selector => [...document.querySelectorAll(selector)].filter(element => !element.closest('.pop-window'));
  if ('IntersectionObserver' in window && !reduced) {
    const watcher = new IntersectionObserver(entries => entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      if (entry.target.matches('[data-count]')) countUp(entry.target);
      else entry.target.classList.add('viz-on');
      watcher.unobserve(entry.target);
    }), {threshold: .3});
    outsidePops('.viz,[data-count]').forEach(element => watcher.observe(element));
  } else outsidePops('.viz').forEach(element => element.classList.add('viz-on'));

  // Hover detail for any mark that carries data-tip.
  const tip = document.createElement('div');
  tip.className = 'viz-tip';
  tip.setAttribute('aria-hidden', 'true');
  document.body.append(tip);
  let tipTarget = null;
  const placeTip = (x, y) => {
    tip.style.left = `${x}px`;
    tip.style.top = `${Math.min(y, innerHeight - 70)}px`;
    tip.classList.toggle('is-left', x > innerWidth - 280);
  };
  const showTip = (target, x, y) => {
    if (target.closest('.is-scrubbing')) return;
    tipTarget = target;
    tip.textContent = target.dataset.tip;
    tip.classList.add('show');
    placeTip(x, y);
  };
  const hideTip = () => { tipTarget = null; tip.classList.remove('show'); };
  document.addEventListener('pointerover', event => {
    const target = event.target.closest('[data-tip]');
    if (target && event.pointerType !== 'touch') showTip(target, event.clientX, event.clientY);
  });
  document.addEventListener('pointermove', event => { if (tipTarget) placeTip(event.clientX, event.clientY); });
  document.addEventListener('pointerout', event => { if (tipTarget && !tipTarget.contains(event.relatedTarget)) hideTip(); });
  document.addEventListener('focusin', event => {
    const target = event.target.closest('[data-tip]');
    if (!target) return hideTip();
    const bounds = target.getBoundingClientRect();
    showTip(target, bounds.left + Math.min(bounds.width / 2, 200), bounds.top);
  });
  addEventListener('scroll', hideTip, {passive: true});


  const progress = document.querySelector('.scroll-progress');
  let progressQueued = false;
  const updateProgress = () => {
    if (progressQueued) return;
    progressQueued = true;
    requestAnimationFrame(() => {
      const range = document.documentElement.scrollHeight - innerHeight;
      progress?.style.setProperty('--progress', range > 0 ? String(scrollY / range) : '0');
      progressQueued = false;
    });
  };
  addEventListener('scroll', updateProgress, {passive: true});
  updateProgress();

  // Drag a window by its title bar. Hero windows move inside the scene; pop windows inside the viewport.
  let heroLayer = 10;
  const makeDraggable = (box, handle, floating) => {
    handle.addEventListener('pointerdown', event => {
      if (event.button !== 0 || event.target.closest('button')) return;
      if (floating && matchMedia('(max-width: 680px)').matches) return;
      const left = floating ? box.getBoundingClientRect().left : box.offsetLeft;
      const top = floating ? box.getBoundingClientRect().top : box.offsetTop;
      const startX = event.clientX, startY = event.clientY;
      Object.assign(box.style, {left: `${left}px`, top: `${top}px`, right: 'auto', bottom: 'auto'});
      if (!floating) box.style.zIndex = String(++heroLayer);
      box.classList.add('is-dragging');
      box.classList.remove('is-tilting');
      handle.setPointerCapture(event.pointerId);
      const move = moveEvent => {
        const scale = floating ? 1 : pageScale(box);
        let x = left + (moveEvent.clientX - startX) / scale, y = top + (moveEvent.clientY - startY) / scale;
        if (floating) { x = clamp(x, 80 - box.offsetWidth, innerWidth - 80); y = clamp(y, 8, innerHeight - 48); }
        box.style.left = `${x}px`;
        box.style.top = `${y}px`;
      };
      const release = () => {
        box.classList.remove('is-dragging');
        handle.removeEventListener('pointermove', move);
        handle.removeEventListener('pointerup', release);
        handle.removeEventListener('pointercancel', release);
      };
      handle.addEventListener('pointermove', move);
      handle.addEventListener('pointerup', release);
      handle.addEventListener('pointercancel', release);
    });
  };
  document.querySelectorAll('.hero-scene .window').forEach(windowCard => makeDraggable(windowCard, windowCard.querySelector('.window-bar'), false));

  // Floating windows with tabs.
  const pops = [...document.querySelectorAll('.pop-window')];
  const triggers = new Map();
  let popLayer = 61;
  const front = pop => { pops.forEach(other => other.classList.toggle('is-front', other === pop)); pop.style.zIndex = String(++popLayer); };
  const animatePanel = panel => {
    panel?.querySelectorAll('.viz').forEach(replay);
    panel?.querySelectorAll('[data-count]').forEach(countUp);
  };
  const moveInk = pop => {
    const ink = pop.querySelector('.pop-tab-ink');
    const tab = pop.querySelector('.pop-tab[aria-selected="true"]');
    if (!ink || !tab) return;
    ink.style.setProperty('--ink-x', `${tab.offsetLeft}px`);
    ink.style.setProperty('--ink-w', `${tab.offsetWidth}px`);
  };
  const placePop = (pop, trigger) => {
    const width = pop.offsetWidth, height = pop.offsetHeight;
    let x = (innerWidth - width) / 2, y = (innerHeight - height) / 2;
    if (trigger) {
      const bounds = trigger.getBoundingClientRect();
      x = bounds.left + bounds.width / 2 - width / 2;
      y = bounds.bottom + 12;
      if (y + height > innerHeight - 12) y = bounds.top - height - 12;
      if (y < 12) y = (innerHeight - height) / 2;
    }
    x = clamp(x, 12, Math.max(12, innerWidth - width - 12));
    y = clamp(y, 12, Math.max(12, innerHeight - height - 12));
    Object.assign(pop.style, {left: `${x}px`, top: `${y}px`});
    if (trigger) {
      const bounds = trigger.getBoundingClientRect();
      pop.style.setProperty('--origin-x', `${bounds.left + bounds.width / 2 - x}px`);
      pop.style.setProperty('--origin-y', `${bounds.top + bounds.height / 2 - y}px`);
    }
  };
  // Minimized windows become tabs along the bottom edge; the window shrinks into its tab.
  const dock = document.createElement('div');
  dock.className = 'pop-dock';
  dock.setAttribute('role', 'toolbar');
  dock.setAttribute('aria-label', 'Minimized windows');
  document.body.append(dock);
  const docked = new Map();
  const morph = (element, from, to, options) => element.animate([
    {transform: `translate(${from.left - to.left}px,${from.top - to.top}px) scale(${from.width / to.width},${from.height / to.height})`, opacity: from.opacity ?? 1},
    {transform: 'none', opacity: 1}], {duration: 380, easing: 'cubic-bezier(.2,.8,.2,1)', ...options});
  const restorePop = pop => {
    const tab = docked.get(pop);
    if (!tab) return;
    const from = tab.getBoundingClientRect();
    docked.delete(pop);
    tab.remove();
    pop.hidden = false;
    pop.style.transformOrigin = '0 0';
    front(pop);
    if (!reduced) morph(pop, {left: from.left, top: from.top, width: from.width, height: from.height, opacity: .3}, pop.getBoundingClientRect())
      .finished.then(() => { pop.style.transformOrigin = ''; });
    else pop.style.transformOrigin = '';
    moveInk(pop);
    pop.querySelector('.pop-tab[aria-selected="true"], [data-pop-close]').focus({preventScroll: true});
  };
  const minimizePop = pop => {
    if (pop.hidden || docked.has(pop)) return;
    const tab = document.createElement('div');
    tab.className = 'dock-tab';
    tab.tabIndex = 0;
    tab.setAttribute('role', 'button');
    tab.setAttribute('aria-label', `Restore ${pop.querySelector('.pop-title').textContent}`);
    const title = document.createElement('span');
    title.textContent = pop.querySelector('.pop-title').textContent.replace(/^Quick look · /, '');
    const close = document.createElement('button');
    close.type = 'button';
    close.textContent = '×';
    close.setAttribute('aria-label', 'Close window');
    tab.append(title, close);
    dock.append(tab);
    docked.set(pop, tab);
    tab.addEventListener('click', event => { if (!event.target.closest('button')) restorePop(pop); });
    tab.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); restorePop(pop); } });
    close.addEventListener('click', () => { docked.delete(pop); tab.remove(); pop.classList.remove('is-zoomed'); triggers.get(pop)?.setAttribute('aria-expanded', 'false'); });
    pop.classList.remove('is-opening');
    tab.focus({preventScroll: true});
    if (reduced) { pop.hidden = true; return; }
    const from = pop.getBoundingClientRect(), to = tab.getBoundingClientRect();
    pop.style.transformOrigin = '0 0';
    pop.animate([{transform: 'none', opacity: 1},
      {transform: `translate(${to.left - from.left}px,${to.top - from.top}px) scale(${to.width / from.width},${to.height / from.height})`, opacity: .2}],
      {duration: 340, easing: 'cubic-bezier(.5,0,.75,0)'}).finished.then(() => { pop.hidden = true; pop.style.transformOrigin = ''; });
    tab.animate([{transform: 'translateY(100%)'}, {transform: 'none'}], {duration: 260, delay: 200, easing: 'cubic-bezier(.2,.8,.2,1)', fill: 'backwards'});
  };
  const zoomPop = pop => {
    if (matchMedia('(max-width: 680px)').matches) return;
    const from = pop.getBoundingClientRect();
    pop.classList.toggle('is-zoomed');
    pop.querySelector('[data-pop-zoom]').setAttribute('aria-label', pop.classList.contains('is-zoomed') ? 'Restore window size' : 'Zoom window');
    moveInk(pop);
    if (reduced) return;
    pop.style.transformOrigin = '0 0';
    morph(pop, from, pop.getBoundingClientRect(), {duration: 420}).finished.then(() => { pop.style.transformOrigin = ''; });
  };
  const openPop = (pop, trigger) => {
    if (docked.has(pop)) { restorePop(pop); return; }
    if (!pop.hidden && !pop.classList.contains('is-closing')) { front(pop); return; }
    pop.classList.remove('is-closing', 'is-opening');
    pop.hidden = false;
    placePop(pop, trigger);
    void pop.offsetWidth;
    pop.classList.add('is-opening');
    front(pop);
    triggers.get(pop)?.setAttribute('aria-expanded', 'false');
    triggers.set(pop, trigger);
    trigger?.setAttribute('aria-expanded', 'true');
    moveInk(pop);
    animatePanel(pop.querySelector('.pop-panel.is-active'));
    (pop.querySelector('.pop-tab[aria-selected="true"]') || pop.querySelector('[data-pop-close]')).focus({preventScroll: true});
  };
  const closePop = pop => {
    if (pop.hidden || pop.classList.contains('is-closing')) return;
    const trigger = triggers.get(pop);
    trigger?.setAttribute('aria-expanded', 'false');
    if (trigger && document.contains(trigger) && pop.contains(document.activeElement)) trigger.focus({preventScroll: true});
    const finish = () => { pop.hidden = true; pop.classList.remove('is-closing', 'is-opening'); };
    if (reduced) return finish();
    pop.classList.remove('is-opening');
    pop.classList.add('is-closing');
    const done = event => { if (event.target === pop) { pop.removeEventListener('animationend', done); finish(); } };
    pop.addEventListener('animationend', done);
  };
  const selectTab = (pop, tab) => {
    const tabs = [...pop.querySelectorAll('.pop-tab')];
    const from = tabs.findIndex(other => other.getAttribute('aria-selected') === 'true');
    const to = tabs.indexOf(tab);
    tabs.forEach(other => {
      const selected = other === tab;
      const panel = document.getElementById(other.getAttribute('aria-controls'));
      other.setAttribute('aria-selected', String(selected));
      other.tabIndex = selected ? 0 : -1;
      panel.hidden = !selected;
      panel.classList.toggle('is-active', selected);
      if (selected) { panel.style.setProperty('--panel-from', `${to >= from ? 18 : -18}px`); animatePanel(panel); }
    });
    moveInk(pop);
  };
  pops.forEach(pop => {
    const tabs = [...pop.querySelectorAll('.pop-tab')];
    tabs.forEach(tab => tab.addEventListener('click', () => selectTab(pop, tab)));
    pop.querySelector('.pop-tabs')?.addEventListener('keydown', event => {
      const current = tabs.indexOf(document.activeElement);
      const next = {ArrowRight: current + 1, ArrowLeft: current - 1, Home: 0, End: tabs.length - 1}[event.key];
      if (next === undefined || current < 0) return;
      event.preventDefault();
      const tab = tabs[(next + tabs.length) % tabs.length];
      selectTab(pop, tab);
      tab.focus();
    });
    pop.querySelector('[data-pop-close]').addEventListener('click', () => closePop(pop));
    pop.querySelector('[data-pop-minimize]').addEventListener('click', () => minimizePop(pop));
    pop.querySelector('[data-pop-zoom]').addEventListener('click', () => zoomPop(pop));
    pop.querySelector('.pop-bar').addEventListener('dblclick', event => { if (!event.target.closest('button')) zoomPop(pop); });
    pop.addEventListener('pointerdown', () => front(pop));
    makeDraggable(pop, pop.querySelector('[data-drag-handle]'), true);
  });
  document.addEventListener('click', event => {
    const trigger = event.target.closest('[data-pop-open]');
    const pop = trigger && document.getElementById(trigger.dataset.popOpen);
    if (!pop) return;
    event.preventDefault();
    if (!pop.hidden && triggers.get(pop) === trigger && trigger.classList.contains('info-chip')) closePop(pop);
    else openPop(pop, trigger);
  });
  document.querySelectorAll('.process-card').forEach(card => card.addEventListener('click', event => {
    if (!event.target.closest('button')) card.querySelector('.info-chip')?.click();
  }));
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || document.querySelector('dialog[open]')) return;
    const top = pops.filter(pop => !pop.hidden).sort((a, b) => Number(b.style.zIndex) - Number(a.style.zIndex))[0];
    if (top) closePop(top);
  });
  addEventListener('resize', () => pops.forEach(moveInk));

  // Move elements to new positions, then animate each from where it was.
  const flip = (elements, mutate) => {
    const before = new Map(elements.map(element => [element, element.getBoundingClientRect()]));
    mutate();
    if (reduced) return;
    elements.forEach(element => {
      const from = before.get(element), to = element.getBoundingClientRect();
      const dx = from.left - to.left, dy = from.top - to.top;
      const scale = pageScale(element);
      if (dx || dy) element.animate([{transform: `translate(${dx / scale}px,${dy / scale}px)`}, {transform: 'none'}],
                                    {duration: 480, easing: 'cubic-bezier(.7,0,.2,1)'});
    });
  };
  const signed = (value, digits) => `${value >= 0 ? '+' : '−'}${Math.abs(value).toFixed(digits)}`;

  // Scoreboard: sortable columns and a threshold scrubber over the change column.
  document.querySelectorAll('.scoreboard').forEach(board => {
    const rowsBox = board.querySelector('.board-rows');
    const rows = () => [...rowsBox.querySelectorAll('.board-row')];
    const scrub = board.querySelector('.board-scrub');
    const sorts = [...board.querySelectorAll('[data-sort]')];
    const limit = Number(board.dataset.limit);
    sorts.forEach(button => button.addEventListener('click', () => {
      const key = button.dataset.sort;
      const dir = button.dataset.dir === 'descending' ? 'ascending' : button.dataset.dir === 'ascending' ? 'descending'
        : key === 'name' ? 'ascending' : 'descending';
      sorts.forEach(other => { if (other !== button) delete other.dataset.dir; });
      button.dataset.dir = dir;
      const sorted = rows().sort((a, b) => key === 'name' ? a.dataset.name.localeCompare(b.dataset.name)
        : Number(a.dataset[key]) - Number(b.dataset[key]));
      if (dir === 'descending') sorted.reverse();
      flip(rows(), () => sorted.forEach(row => rowsBox.insertBefore(row, scrub)));
    }));
    const clear = () => { board.classList.remove('is-scrubbing'); rows().forEach(row => row.classList.remove('is-out')); };
    board.addEventListener('pointermove', event => {
      if (event.pointerType === 'touch') return;
      const bar = rowsBox.querySelector('.dbar');
      const bounds = bar.getBoundingClientRect(), box = rowsBox.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right) return clear();
      const value = ((event.clientX - bounds.left) / bounds.width * 2 - 1) * limit;
      const passing = rows().filter(row => value >= 0 ? Number(row.dataset.change) >= value : Number(row.dataset.change) <= value);
      rows().forEach(row => row.classList.toggle('is-out', !passing.includes(row)));
      scrub.style.left = `${(event.clientX - box.left) / pageScale(board)}px`;
      scrub.classList.toggle('is-flip', event.clientX > box.right - 200);
      scrub.querySelector('b').textContent = `${value >= 0 ? '≥' : '≤'} ${signed(value, 1)} pts`;
      scrub.querySelector('span').textContent = `${passing.length} of ${rows().length} sets ${value >= 0 ? 'gain at least this' : 'lose at least this'}`;
      board.classList.add('is-scrubbing');
      hideTip();
    });
    board.addEventListener('pointerleave', clear);
  });

  // Any ruled track with data-scrub reads out the value under the pointer.
  document.querySelectorAll('[data-scrub]').forEach(track => {
    const min = Number(track.dataset.min), max = Number(track.dataset.max), digits = Number(track.dataset.digits || 1);
    const zones = JSON.parse(track.dataset.zones || '[]');
    const hair = document.createElement('span');
    hair.className = 'scrub-hair';
    hair.setAttribute('aria-hidden', 'true');
    const value = document.createElement('b'), zone = document.createElement('em');
    hair.append(value, zone);
    track.append(hair);
    track.addEventListener('pointermove', event => {
      const bounds = track.getBoundingClientRect();
      const share = clamp((event.clientX - bounds.left) / bounds.width, 0, 1);
      const reading = min + share * (max - min);
      hair.style.left = `${share * 100}%`;
      hair.classList.toggle('is-flip', share > .55);
      value.textContent = signed(reading, digits) + (track.dataset.unit || '');
      zone.textContent = (zones.find(([upTo]) => reading <= upTo) || [0, ''])[1];
      track.classList.add('is-scrubbing');
    });
    track.addEventListener('pointerleave', () => track.classList.remove('is-scrubbing'));
  });

  // Scatter: a crosshair that reads both axes and snaps to the nearest set.
  document.querySelectorAll('svg[data-plot]').forEach(svg => {
    const d = svg.dataset;
    const low = Number(d.low), high = Number(d.high), x0 = Number(d.x0), x1 = Number(d.x1), y0 = Number(d.y0), y1 = Number(d.y1);
    const hair = svg.querySelector('.sc-xhair');
    const [vertical, horizontal] = hair.querySelectorAll(':scope > line');
    const [xTag, yTag] = hair.querySelectorAll(':scope > g');
    const points = [...svg.querySelectorAll('[data-chart-point]')].map(link => ({link, x: Number(link.dataset.px), y: Number(link.dataset.py)}));
    let snapped = null;
    const hide = () => {
      svg.classList.remove('is-scrubbing');
      points.forEach(point => point.link.classList.remove('is-snapped'));
      snapped?.link.dispatchEvent(new Event('pointerleave'));
      snapped = null;
    };
    svg.addEventListener('pointermove', event => {
      const at = new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse());
      if (at.x < x0 || at.x > x1 || at.y < y1 || at.y > y0) return hide();
      const nearest = points.map(point => [Math.hypot(point.x - at.x, point.y - at.y), point]).sort((a, b) => a[0] - b[0])[0];
      const next = nearest && nearest[0] < 26 ? nearest[1] : null;
      if (next !== snapped) {
        snapped?.link.dispatchEvent(new Event('pointerleave'));
        next?.link.dispatchEvent(new Event('pointerenter'));
      }
      snapped = next;
      const x = snapped ? snapped.x : at.x, y = snapped ? snapped.y : at.y;
      points.forEach(point => point.link.classList.toggle('is-snapped', point === snapped));
      [['x1', x], ['x2', x], ['y1', y1], ['y2', y0]].forEach(([name, v]) => vertical.setAttribute(name, v));
      [['x1', x0], ['x2', x1], ['y1', y], ['y2', y]].forEach(([name, v]) => horizontal.setAttribute(name, v));
      xTag.setAttribute('transform', `translate(${x} ${y0 + 4})`);
      yTag.setAttribute('transform', `translate(${x0} ${y})`);
      xTag.querySelector('text').textContent = signed(low + (x - x0) / (x1 - x0) * (high - low), 1);
      yTag.querySelector('text').textContent = signed(low + (y0 - y) / (y0 - y1) * (high - low), 1);
      svg.classList.add('is-scrubbing');
    });
    svg.addEventListener('pointerleave', hide);
    svg.addEventListener('click', event => {
      if (snapped && !event.target.closest('[data-chart-point]')) snapped.link.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
    });
  });

  // Model ladder: nest the circles on a shared baseline, or set them side by side.
  document.querySelectorAll('[data-ladder-toggle]').forEach(button => button.addEventListener('click', () => {
    const ladder = button.parentElement.querySelector('.model-ladder');
    flip([...ladder.children], () => ladder.classList.toggle('is-nested'));
    const nested = ladder.classList.contains('is-nested');
    button.setAttribute('aria-pressed', String(nested));
    button.textContent = nested ? 'Set side by side' : 'Nest the circles';
  }));

  // Trace one practice set across the slope chart.
  document.querySelectorAll('.slope').forEach(slope => {
    const marks = [...slope.querySelectorAll('[data-slope]')];
    marks.forEach(mark => {
      mark.addEventListener('pointerenter', () => {
        slope.classList.add('has-hot');
        marks.forEach(other => other.classList.toggle('is-hot', other.dataset.slope === mark.dataset.slope));
      });
      mark.addEventListener('pointerleave', () => { slope.classList.remove('has-hot'); marks.forEach(other => other.classList.remove('is-hot')); });
    });
  });

  // A sliding highlight behind the active grade filter.
  const filterBox = document.querySelector('.filters');
  if (filterBox) {
    const ink = document.createElement('span');
    ink.className = 'filter-ink';
    ink.setAttribute('aria-hidden', 'true');
    filterBox.prepend(ink);
    filterBox.classList.add('has-ink');
    const placeInk = () => {
      const active = filterBox.querySelector('.filter.active');
      if (!active) return;
      Object.assign(ink.style, {width: `${active.offsetWidth}px`, height: `${active.offsetHeight}px`,
                                transform: `translate(${active.offsetLeft}px,${active.offsetTop}px)`});
    };
    placeInk();
    filterBox.addEventListener('click', () => requestAnimationFrame(placeInk));
    addEventListener('resize', placeInk);
  }

  // Command palette: ⌘K, Ctrl+K or / from anywhere.
  const palette = document.querySelector('#palette');
  const input = palette?.querySelector('input');
  const list = palette?.querySelector('.palette-list');
  const siteRoot = document.body.dataset.root || '';
  const entries = window.TOUCHSTONE_INDEX || [];
  let activeIndex = 0;
  const paletteItems = () => [...list.querySelectorAll('.palette-item')];
  const setActive = index => {
    const items = paletteItems();
    if (!items.length) return;
    activeIndex = (index + items.length) % items.length;
    items.forEach((item, position) => item.classList.toggle('is-active', position === activeIndex));
    items[activeIndex].scrollIntoView({block: 'nearest'});
  };
  const renderPalette = () => {
    const query = input.value.trim().toLocaleLowerCase();
    const matches = entries.filter(entry => `${entry.title} ${entry.meta}`.toLocaleLowerCase().includes(query));
    list.replaceChildren();
    let shown = 0;
    [...new Set(matches.map(entry => entry.group))].forEach(group => {
      const heading = document.createElement('li');
      heading.className = 'palette-group';
      heading.textContent = group;
      list.append(heading);
      matches.filter(entry => entry.group === group).forEach(entry => {
        const item = document.createElement('li');
        item.className = 'palette-item';
        const link = document.createElement('a');
        link.href = siteRoot + entry.href;
        link.style.setProperty('--i', String(shown++));
        const mark = document.createElement('i');
        mark.textContent = entry.mark;
        const title = document.createElement('span');
        title.textContent = entry.title;
        const meta = document.createElement('small');
        meta.textContent = entry.meta;
        link.append(mark, title, meta);
        link.addEventListener('pointerenter', () => setActive(paletteItems().indexOf(item)));
        item.append(link);
        list.append(item);
      });
    });
    if (!shown) {
      const empty = document.createElement('li');
      empty.className = 'palette-empty';
      empty.textContent = 'Nothing matches. Try a set name or a page.';
      list.append(empty);
    }
    setActive(0);
  };
  const openPalette = () => {
    if (!palette || palette.open) return;
    input.value = '';
    renderPalette();
    palette.showModal();
    input.focus();
  };
  input?.addEventListener('input', renderPalette);
  input?.addEventListener('keydown', event => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); setActive(activeIndex + (event.key === 'ArrowDown' ? 1 : -1)); }
    if (event.key === 'Enter') { event.preventDefault(); paletteItems()[activeIndex]?.querySelector('a').click(); }
  });
  palette?.addEventListener('click', event => { if (event.target === palette) palette.close(); });
  document.querySelectorAll('[data-palette-open]').forEach(button => button.addEventListener('click', openPalette));
  document.addEventListener('keydown', event => {
    const typing = event.target.closest?.('input,textarea,[contenteditable]');
    if (((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') || (event.key === '/' && !typing)) {
      event.preventDefault();
      openPalette();
    }
  });

})();
"""


SCRIPT += r"""
(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const gsap = window.gsap, Motion = window.Motion;
  const spring = {type: 'spring', stiffness: 260, damping: 22, mass: .6};

  // Shader gradient: flowing ink, gold and blue; the light leans toward the pointer.
  const shaders = [];
  document.querySelectorAll('[data-shader]').forEach(canvas => {
    const gl = canvas.getContext('webgl', {antialias: false, premultipliedAlpha: false});
    if (!gl) return;
    canvas.addEventListener('webglcontextlost', event => { event.preventDefault(); canvas.style.display = 'none'; });
    const compile = (type, source) => { const shader = gl.createShader(type); gl.shaderSource(shader, source); gl.compileShader(shader); return shader; };
    const program = gl.createProgram();
    gl.attachShader(program, compile(gl.VERTEX_SHADER, 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}'));
    gl.attachShader(program, compile(gl.FRAGMENT_SHADER, `precision mediump float;uniform vec2 r;uniform float t;uniform vec2 m;
      float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
      float n(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y);}
      float fbm(vec2 p){float v=0.,a=.5;for(int k=0;k<5;k++){v+=a*n(p);p=p*2.03+vec2(1.7,9.2);a*=.5;}return v;}
      void main(){vec2 uv=gl_FragCoord.xy/r;vec2 q=uv*vec2(r.x/r.y,1.);
        float a=fbm(q*1.1+vec2(t*.03,-t*.018));float b=fbm(q*1.6+a*1.4+vec2(-t*.02,t*.025));
        float glow=smoothstep(.75,0.,distance(uv,m));
        vec3 col=vec3(.075,.082,.09);
        col=mix(col,vec3(.12,.2,.3),smoothstep(.4,.95,b)*.7);
        col=mix(col,vec3(.84,.69,.35),smoothstep(.66,1.05,a+glow*.2)*.45);
        col+=vec3(.84,.69,.35)*glow*.12;
        col+=(h(gl_FragCoord.xy+t)-.5)*.03;
        gl_FragColor=vec4(col,1.);}`));
    gl.linkProgram(program);
    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(program, 'p');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const uR = gl.getUniformLocation(program, 'r'), uT = gl.getUniformLocation(program, 't'), uM = gl.getUniformLocation(program, 'm');
    const state = {canvas, gl, visible: true, mouse: [.7, .6], target: [.7, .6]};
    const size = () => {
      const ratio = Math.min(devicePixelRatio || 1, 1.5);
      canvas.width = Math.max(1, canvas.clientWidth * ratio * .6);
      canvas.height = Math.max(1, canvas.clientHeight * ratio * .6);
      gl.viewport(0, 0, canvas.width, canvas.height);
    };
    size();
    if ('ResizeObserver' in window) new ResizeObserver(size).observe(canvas);
    const host = canvas.parentElement;
    host.addEventListener('pointermove', event => {
      const bounds = canvas.getBoundingClientRect();
      state.target = [(event.clientX - bounds.left) / bounds.width, 1 - (event.clientY - bounds.top) / bounds.height];
    });
    state.draw = time => {
      state.mouse = state.mouse.map((v, i) => v + (state.target[i] - v) * .06);
      gl.uniform2f(uR, canvas.width, canvas.height);
      gl.uniform1f(uT, time / 1000);
      gl.uniform2f(uM, state.mouse[0], state.mouse[1]);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };
    if ('IntersectionObserver' in window) new IntersectionObserver(([entry]) => { state.visible = entry.isIntersecting; }).observe(canvas);
    shaders.push(state);
  });
  if (shaders.length) {
    // Hidden tabs pause the loop; redraw at once on return so the gradient never shows a stale or blank frame.
    document.addEventListener('visibilitychange', () => { if (!document.hidden) shaders.forEach(state => state.draw(performance.now())); });
    if (reduced) shaders.forEach(state => state.draw(8000));
    else { const loop = time => { shaders.forEach(state => state.visible && state.draw(time)); requestAnimationFrame(loop); }; requestAnimationFrame(loop); }
  }

  // Tabs: a sliding pill under the active tab; the new panel springs in.
  document.querySelectorAll('[data-tabs]').forEach(group => {
    const list = group.querySelector('[role=tablist]'), ink = group.querySelector('.seg-ink');
    const buttons = [...list.querySelectorAll('[role=tab]')];
    const place = button => { ink.style.setProperty('--x', `${button.offsetLeft}px`); ink.style.setProperty('--w', `${button.offsetWidth}px`); };
    const select = (button, focus) => {
      buttons.forEach(other => {
        const on = other === button;
        other.setAttribute('aria-selected', String(on));
        other.tabIndex = on ? 0 : -1;
        const panel = document.getElementById(other.getAttribute('aria-controls'));
        panel.hidden = !on;
        panel.classList.toggle('is-active', on);
        if (on && Motion && !reduced) {
          Motion.animate(panel, {opacity: [0, 1], y: [14, 0]}, spring);
          const value = panel.querySelector('.metric-value, .ticks');
          if (value) Motion.animate(value, {scale: [.9, 1]}, {...spring, stiffness: 320});
          panel.querySelectorAll('.viz').forEach(viz => { viz.classList.remove('viz-on'); void viz.offsetWidth; viz.classList.add('viz-on'); });
        }
      });
      if (ink.dataset.ready && Motion && !reduced) {
        Motion.animate(ink, {'--x': `${button.offsetLeft}px`, '--w': `${button.offsetWidth}px`}, spring);
      } else place(button);
      ink.dataset.ready = '1';
      if (focus) button.focus();
    };
    buttons.forEach(button => button.addEventListener('click', () => select(button)));
    list.addEventListener('keydown', event => {
      const index = buttons.indexOf(document.activeElement);
      const next = {ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: buttons.length - 1}[event.key];
      if (next === undefined || index < 0) return;
      event.preventDefault();
      select(buttons[(next + buttons.length) % buttons.length], true);
    });
    select(buttons.find(button => button.getAttribute('aria-selected') === 'true') || buttons[0]);
    addEventListener('resize', () => place(buttons.find(button => button.getAttribute('aria-selected') === 'true')));
  });

  // Spring tilt with a glass highlight that tracks the pointer; magnetic primary buttons; ripples.
  if (fine && !reduced && Motion) {
    document.querySelectorAll('.cert, .tilt').forEach(card => {
      card.addEventListener('pointermove', event => {
        const bounds = card.getBoundingClientRect();
        const x = (event.clientX - bounds.left) / bounds.width, y = (event.clientY - bounds.top) / bounds.height;
        card.style.setProperty('--gx', `${x * 100}%`);
        card.style.setProperty('--gy', `${y * 100}%`);
        Motion.animate(card, {rotateX: (.5 - y) * 7, rotateY: (x - .5) * 9, scale: 1.015}, spring);
      });
      card.addEventListener('pointerleave', () => Motion.animate(card, {rotateX: 0, rotateY: 0, scale: 1}, spring));
    });
    document.querySelectorAll('.button-lime, .nav-cta').forEach(button => {
      button.addEventListener('pointermove', event => {
        const bounds = button.getBoundingClientRect();
        Motion.animate(button, {x: (event.clientX - bounds.left - bounds.width / 2) * .22, y: (event.clientY - bounds.top - bounds.height / 2) * .35}, spring);
      });
      button.addEventListener('pointerleave', () => Motion.animate(button, {x: 0, y: 0}, spring));
    });
  }
  document.addEventListener('pointerdown', event => {
    const host = event.target.closest('.button,.seg-tab,.pop-tab,.filter,.nav-search,.nav-cta');
    if (!host || reduced) return;
    const bounds = host.getBoundingClientRect();
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.cssText = `left:${event.clientX - bounds.left}px;top:${event.clientY - bounds.top}px;--size:${Math.max(bounds.width, bounds.height) * 2.2}px`;
    host.append(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
  });

  // Scroll-driven steps: the active step lights up and its illustration plays.
  const steps = [...document.querySelectorAll('.scrolly-step')];
  const panels = [...document.querySelectorAll('.stage-panel')];
  const progress = document.querySelector('.stage-progress');
  const playStage = index => {
    const panel = panels[index];
    if (!panel || !gsap || reduced) return;
    gsap.killTweensOf(panel.querySelectorAll('*'));
    if (index === 0) {
      gsap.timeline()
        .fromTo(panel.querySelectorAll('.task-chip'), {x: -60, opacity: 0}, {x: 0, opacity: 1, stagger: .12, duration: .5, ease: 'back.out(1.6)'})
        .fromTo(panel.querySelector('.vault-lid'), {rotate: -28}, {rotate: 0, duration: .45, ease: 'bounce.out'}, '-=.1')
        .fromTo(panel.querySelector('.hash'), {clipPath: 'inset(0 100% 0 0)'}, {clipPath: 'inset(0 0% 0 0)', duration: .9, ease: 'steps(24)'});
    } else if (index === 1) {
      gsap.timeline()
        .fromTo(panel.querySelectorAll('.ladder-dot'), {scale: 0}, {scale: 1, stagger: .14, duration: .7, ease: 'elastic.out(1, .55)'})
        .fromTo(panel.querySelector('.train-curve path'), {strokeDashoffset: 1}, {strokeDashoffset: 0, duration: 1, ease: 'power2.out'}, '-=.4');
    } else if (index === 2) {
      panel.querySelectorAll('.viz').forEach(viz => { viz.classList.remove('viz-on'); void viz.offsetWidth; viz.classList.add('viz-on'); });
      gsap.fromTo(panel.querySelectorAll('.vis-measure > div'), {y: 18, opacity: 0}, {y: 0, opacity: 1, stagger: .12, duration: .5, ease: 'power3.out'});
    } else {
      gsap.timeline()
        .fromTo(panel.querySelectorAll('.pr-dot'), {scale: 0, transformOrigin: 'center'}, {scale: 1, stagger: .12, duration: .4, ease: 'back.out(2)'})
        .fromTo(panel.querySelector('.pr-fit'), {strokeDasharray: 1, strokeDashoffset: 1}, {strokeDashoffset: 0, duration: .6}, '-=.2')
        .fromTo(panel.querySelector('.pr-band'), {opacity: 0}, {opacity: 1, duration: .4})
        .fromTo(panel.querySelector('.pr-target'), {scale: 0, transformOrigin: 'center'}, {scale: 1, duration: .5, ease: 'elastic.out(1, .5)'})
        .fromTo(panel.querySelector('.price-tag'), {y: -20, opacity: 0, rotate: -6}, {y: 0, opacity: 1, rotate: 0, duration: .6, ease: 'back.out(2)'}, '-=.2');
    }
  };
  let activeStep = -1;
  const setStep = index => {
    if (index === activeStep) return;
    activeStep = index;
    steps.forEach((step, i) => step.classList.toggle('is-active', i === index));
    panels.forEach((panel, i) => panel.classList.toggle('is-active', i === index));
    progress?.style.setProperty('--p', String((index + 1) / panels.length));
    playStage(index);
  };
  steps.forEach((step, index) => step.querySelector('button').addEventListener('click', () => {
    setStep(index);
    step.scrollIntoView({behavior: reduced ? 'auto' : 'smooth', block: 'center'});
  }));

  if (!gsap || !window.ScrollTrigger) { if (steps.length) setStep(0); return; }
  gsap.registerPlugin(ScrollTrigger);
  if (window.SplitText) gsap.registerPlugin(SplitText);
  // The active step is the last one whose top has passed 60% of the viewport, however fast the page moved.
  const syncStep = () => {
    const line = innerHeight * .6;
    const passed = steps.filter(step => step.getBoundingClientRect().top < line);
    setStep(Math.max(0, passed.length - 1));
  };
  if (steps.length) {
    setStep(0);
    ScrollTrigger.create({trigger: steps[0].parentElement, start: 'top bottom', end: 'bottom top', onUpdate: syncStep, onRefresh: syncStep});
  }
  if (reduced) return;

  // Reveals run when an element reaches the screen. Nothing is hidden beforehand, so a missed trigger
  // can never leave a gap; elements already on screen at load simply animate in place.
  const reveal = (elements, animate) => {
    if (!('IntersectionObserver' in window)) return;
    const watcher = new IntersectionObserver(entries => entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      watcher.unobserve(entry.target);
      animate(entry.target);
    }), {rootMargin: '0px 0px -8% 0px'});
    elements.forEach(element => watcher.observe(element));
  };
  reveal(document.querySelectorAll('[data-split]'), heading => {
    if (!window.SplitText) return;
    const split = SplitText.create(heading, {type: 'lines', mask: 'lines', linesClass: 'split-line'});
    gsap.fromTo(split.lines, {yPercent: 105}, {yPercent: 0, duration: .9, ease: 'expo.out', stagger: .08});
  });
  reveal(document.querySelectorAll('[data-rise], .t-card, .bento-tile, .t-plan, .faq details, .why-card, .moat-card'), element =>
    gsap.fromTo(element, {y: 26, opacity: 0}, {y: 0, opacity: 1, duration: .7, ease: 'power3.out', clearProps: 'transform,opacity'}));
  gsap.from('.cert', {y: 60, rotateX: 18, opacity: 0, duration: 1.2, ease: 'expo.out', delay: .2});
  gsap.from('.cert-row', {x: 24, opacity: 0, stagger: .08, duration: .6, ease: 'power3.out', delay: .6});

  // Marquee that speeds up and leans with scroll velocity.
  const track = document.querySelector('.marquee-track');
  if (track) {
    const loop = gsap.to(track, {xPercent: -50, ease: 'none', duration: 38, repeat: -1});
    const lean = gsap.quickTo(track, 'skewX', {duration: .5, ease: 'power3'});
    ScrollTrigger.create({onUpdate: self => {
      const velocity = self.getVelocity();
      loop.timeScale(self.direction * (1 + Math.min(Math.abs(velocity) / 250, 5)));
      gsap.to(loop, {timeScale: self.direction, duration: 1.4, ease: 'power2.out', overwrite: true});
      lean(gsap.utils.clamp(-8, 8, velocity / -220));
      gsap.delayedCall(.15, () => lean(0));
    }});
  }

  // The timeline line fills as you scroll past it.
  const timeline = document.querySelector('.timeline');
  if (timeline) ScrollTrigger.create({trigger: timeline, start: 'top 80%', end: 'bottom 60%', scrub: true,
    onUpdate: self => timeline.style.setProperty('--line-p', self.progress.toFixed(3))});

  // Findings pop in once the sample report is on screen.
  const notices = [...document.querySelectorAll('[data-notice]')];
  const dismiss = notice => {
    if (!notice.isConnected) return;
    if (Motion) Motion.animate(notice, {x: 80, opacity: 0}, {duration: .3}).finished.then(() => notice.remove());
    else notice.remove();
  };
  notices.forEach(notice => {
    notice.querySelector('.notice-close').addEventListener('click', () => dismiss(notice));
    notice.querySelector('.notice-timer').addEventListener('animationend', () => dismiss(notice));
    notice.querySelector('.notice-open')?.addEventListener('click', () => dismiss(notice));
  });
  const sample = document.querySelector('#sample');
  if (sample && notices.length) ScrollTrigger.create({trigger: sample, start: 'top 55%', once: true, onEnter: () => {
    notices.forEach((notice, index) => gsap.delayedCall(.5 + index * 1.2, () => {
      notice.hidden = false;
      if (Motion) Motion.animate(notice, {x: [120, 0], opacity: [0, 1], scale: [.92, 1]}, spring);
    }));
  }});
})();
"""


SCRIPT += r"""
(() => {
  const gsap = window.gsap, Motion = window.Motion;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const spring = {type: 'spring', stiffness: 260, damping: 24};

  // Re-measure scroll positions whenever the scaled page changes height.
  const frame = document.querySelector('.scale-frame');
  if (frame && window.ScrollTrigger && 'ResizeObserver' in window) {
    let last = 0, pending;
    new ResizeObserver(() => {
      const height = frame.getBoundingClientRect().height;
      if (Math.abs(height - last) < 2) return;
      last = height;
      clearTimeout(pending);
      pending = setTimeout(() => ScrollTrigger.refresh(), 150);
    }).observe(frame);
  }

  // Hero: copy and console arrive in sequence.
  if (gsap && !reduced) gsap.from('[data-intro]', {y: 34, opacity: 0, duration: 1, ease: 'expo.out', stagger: .12, delay: .25});

  // Console: two illustrative appraisal runs, typed out line by line, forever.
  const runs = [...document.querySelectorAll('.c-run')];
  if (runs.length && gsap && !reduced) {
    const play = index => {
      runs.forEach((run, i) => run.classList.toggle('is-active', i === index));
      const run = runs[index];
      const parts = [...run.querySelectorAll('[data-l]')];
      const timeline = gsap.timeline({delay: index === 0 ? 1 : .2, onComplete: () => gsap.delayedCall(2.6, () => play((index + 1) % runs.length))});
      timeline.set(parts, {opacity: 0, y: 8}).set(run.querySelectorAll('.c-bar i'), {scaleX: 0});
      parts.forEach((part, i) => {
        timeline.to(part, {opacity: 1, y: 0, duration: .3, ease: 'power2.out'}, i ? '+=.3' : 0);
        if (part.classList.contains('c-bars')) timeline.to(part.querySelectorAll('.c-bar i'), {scaleX: 1, duration: .8, stagger: .14, ease: 'power2.out'});
      });
      timeline.fromTo(run.querySelector('.c-verdict'), {scale: 1.7, rotate: -14}, {scale: 1, rotate: -2, duration: .55, ease: 'back.out(2.2)'}, '-=.3');
    };
    play(0);
  }

  // The mission statement lights up word by word as it scrolls through the screen.
  const statement = document.querySelector('[data-scrub-text]');
  if (statement && gsap && window.SplitText && window.ScrollTrigger && !reduced) {
    const words = SplitText.create(statement, {type: 'words'}).words;
    gsap.fromTo(words, {opacity: .14}, {opacity: 1, stagger: .1, ease: 'none',
      scrollTrigger: {trigger: statement, start: 'top 80%', end: 'bottom 45%', scrub: true}});
  }

  // Compare environments: switch the measure, bars resize and the order reshuffles.
  document.querySelectorAll('[data-compare]').forEach(box => {
    const rows = [...box.querySelectorAll('.cmp-bar')], wrap = box.querySelector('.cmp-bars'), note = box.querySelector('[data-note]');
    const tabs = [...box.querySelectorAll('[data-metric]')], ink = box.querySelector('.seg-ink');
    const notes = {reward: 'Ranked by training reward, Env A looks best.',
                   transfer: 'Ranked by real improvement on new problems, Env B wins.',
                   value: 'Per dollar spent, Env B delivers almost 8× what Env A does.'};
    const format = {reward: v => `${v}%`, transfer: v => `+${v.toFixed(1)} pts`, value: v => `${v.toFixed(1)} pts`};
    const placeInk = (tab, animate) => {
      if (animate && Motion && !reduced) Motion.animate(ink, {'--x': `${tab.offsetLeft}px`, '--w': `${tab.offsetWidth}px`}, spring);
      else { ink.style.setProperty('--x', `${tab.offsetLeft}px`); ink.style.setProperty('--w', `${tab.offsetWidth}px`); }
    };
    const show = (tab, animate) => {
      const metric = tab.dataset.metric;
      tabs.forEach(other => other.setAttribute('aria-selected', String(other === tab)));
      placeInk(tab, animate);
      const max = Math.max(...rows.map(row => Number(row.dataset[metric])));
      rows.forEach(row => {
        const value = Number(row.dataset[metric]);
        row.querySelector('i').style.setProperty('--w', `${value / max * 100}%`);
        row.querySelector('b').textContent = format[metric](value);
      });
      const before = new Map(rows.map(row => [row, row.getBoundingClientRect().top]));
      [...rows].sort((a, b) => Number(b.dataset[metric]) - Number(a.dataset[metric])).forEach(row => wrap.append(row));
      if (animate && !reduced) rows.forEach(row => {
        const dy = before.get(row) - row.getBoundingClientRect().top;
        const scale = Number(document.documentElement.dataset.scale || 1);
        if (dy) row.animate([{transform: `translateY(${dy / scale}px)`}, {transform: 'none'}], {duration: 650, easing: 'cubic-bezier(.7,0,.2,1)'});
      });
      note.textContent = notes[metric];
      if (animate && Motion && !reduced) Motion.animate(note, {opacity: [0, 1], y: [8, 0]}, spring);
    };
    tabs.forEach(tab => tab.addEventListener('click', () => show(tab, true)));
    show(tabs[0], false);
    addEventListener('resize', () => placeInk(tabs.find(tab => tab.getAttribute('aria-selected') === 'true'), false));
  });

  // Positioning chart: the points drop in, Touchstone last.
  if (gsap && !reduced && 'IntersectionObserver' in window) {
    const once = (selector, animate) => {
      const target = document.querySelector(selector);
      if (!target) return;
      const watcher = new IntersectionObserver(([entry]) => { if (entry.isIntersecting) { watcher.disconnect(); animate(); } });
      watcher.observe(target);
    };
    once('.quad', () => gsap.fromTo('.q-point', {scale: 0, opacity: 0}, {scale: 1, opacity: 1, duration: .7, ease: 'back.out(2)', stagger: .18, clearProps: 'transform,opacity'}));
    once('.roadmap', () => gsap.fromTo('.roadmap li', {y: 30, opacity: 0}, {y: 0, opacity: 1, duration: .7, ease: 'power3.out', stagger: .12, clearProps: 'transform,opacity'}));
  }

  // FAQ: answers spring open and closed.
  document.querySelectorAll('.faq details').forEach(item => {
    const summary = item.querySelector('summary'), answer = item.querySelector('.faq-a');
    summary.addEventListener('click', event => {
      if (!Motion || reduced) return;
      event.preventDefault();
      if (item.open) Motion.animate(answer, {height: [answer.offsetHeight + 'px', '0px'], opacity: [1, 0]}, {duration: .3}).finished.then(() => { item.open = false; answer.style.height = ''; });
      else { item.open = true; Motion.animate(answer, {height: ['0px', answer.scrollHeight + 'px'], opacity: [0, 1]}, spring).finished.then(() => { answer.style.height = ''; }); }
    });
  });
})();
"""

def app_shell(content: str, title: str, description: str, prefix: str, active: str, body_class: str = "") -> str:
    links = {"home": prefix + "index.html", "appraisals": prefix + "appraisals/index.html",
             "forecast": prefix + "forecast/index.html", "methodology": prefix + "methodology/index.html"}
    nav = "".join(
        f'<a class="{"active" if key == active else ""}" href="{url}">{label}</a>'
        for key, label in (("home", "Home"), ("methodology", "How it works"), ("appraisals", "Sample report"), ("forecast", "Forecast check"))
        for url in (links[key],)
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#171819"><meta name="description" content="{esc(description)}">
<title>{'Touchstone' if active == 'home' else esc(title) + ' · Touchstone'}</title><script>{SCALE_BOOT}</script><link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Mona+Sans:wdth,wght@75..125,200..900&family=Geist+Mono:wght@400..600&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<style>{CSS}</style><noscript><style>.reveal{{opacity:1;transform:none}}.dbar i,.meter i,.mini-bars i:after,.db-after,.range-band,.range-actual,.ladder-dot,.suite-split span{{transform:none}}.db-line{{stroke-dashoffset:0}}.board-row{{opacity:1;transform:none}}.range-forecast{{opacity:1}}.slope svg{{clip-path:none}}.rho-marker{{left:var(--at)}}.nav-search,.info-chip,.peek-button{{display:none}}</style></noscript></head><body class="{body_class}" data-root="{prefix}">
<div class="scale-frame"><div class="scale-page">
<nav class="site-nav"><a class="wordmark" href="{links['home']}" aria-label="Touchstone home">{brand_mark()}<span>touchstone</span></a>
<div class="nav-links">{nav}</div><div class="nav-actions"><button class="nav-search" type="button" data-palette-open aria-label="Search pages and appraisals">{icon('search')}<span>Search</span><kbd>⌘K</kbd></button>
<a class="nav-cta" href="{esc(REQUEST_FORM_URL) if REQUEST_FORM_URL else links['home'] + '#request'}"{' target="_blank" rel="noopener"' if REQUEST_FORM_URL else ''}>Request an appraisal</a>
<button class="nav-action menu-toggle" type="button" data-menu aria-label="Open navigation" aria-expanded="false">{icon('menu')}</button></div>
<span class="scroll-progress" aria-hidden="true"></span></nav>
{content}
<footer class="container footer"><a class="wordmark" href="{links['home']}">{brand_mark()}<span>touchstone</span></a>
<span>Independent appraisal for AI training data</span><div class="footer-links"><a href="{links['methodology']}">How it works</a><a href="{links['appraisals']}">Sample report</a><a href="{links['forecast']}">Forecast check</a></div></footer>
</div></div>
<dialog class="palette" id="palette" aria-label="Search Touchstone"><label class="palette-input"><span aria-hidden="true">⌕</span>
<input type="search" placeholder="Jump to a practice set or page…" aria-label="Search pages and appraisals" autocomplete="off"></label>
<ul class="palette-list" role="list"></ul><div class="palette-foot"><span><kbd>↑</kbd><kbd>↓</kbd> move</span><span><kbd>↵</kbd> open</span><span><kbd>esc</kbd> close</span></div></dialog>
<div class="toast" role="status" aria-live="polite"></div><script src="{prefix}search-index.js"></script>{LIBRARIES}<script>{SCRIPT}</script></body></html>"""


def result_card(environment: dict, prefix: str, delay: int = 0) -> str:
    grade = environment["grade"]
    if environment["hackability"]["score"] >= .2:
        signal_label = "Shortcut reward"
        signal_value = f'{environment["hackability"]["score"]:.0%}'
        summary = "Wrong or shortcut answers earned points in our grader test."
    elif environment["redundancy"]["public_overlap"] >= .2:
        signal_label = "Public-set overlap"
        signal_value = f'{environment["redundancy"]["public_overlap"]:.0%}'
        summary = "Many of its tasks also appear in free practice."
    else:
        signal_label = "Forecast vs free practice"
        signal_value = f'{pts(environment["lift_over_free"])} pts'
        change = environment["actual_at_truth"]
        summary = f"After practice, new-question score moved {chip(change)}"
    sizes = list(environment["rungs"])
    transfers = [rung["heldout_after"] - rung["heldout_before"] for rung in environment["rungs"].values()]
    by_size = mini_bars(transfers, [f"{size}: {pts(value)} pts on new questions" for size, value in zip(sizes, transfers)],
                        f"Change on new questions by model size: " + ", ".join(f"{size} {pts(value)}" for size, value in zip(sizes, transfers)))
    return f"""<article class="result-card reveal" style="animation-delay:{min(delay, 500)}ms"
data-grade="{esc(grade)}" data-search="{esc(environment['name'].lower())}">
<a class="result-link" href="{prefix}{esc(environment['id'])}/index.html" aria-label="Open the grade {esc(grade)} certificate for {esc(environment['name'])}"></a>
<span class="result-grade" aria-label="Grade {esc(grade)}">{esc(grade)}</span><div class="result-content">
<div class="result-topline"><span>{esc(signal_label)}</span><span class="result-arrow" aria-hidden="true">↗</span></div>
<h3>{esc(environment['name'])}</h3><p>{summary}</p>
<div class="result-lead"><b data-count>{esc(signal_value)}</b><span>{esc(signal_label.lower())}</span></div>
{spec_list([("Forecast at largest model", pts(environment['forecast']['forecast']) + " pts"), ("Value per task", f"${environment['fair_value_per_task']:,.0f}")])}
<div class="result-viz"><figure class="viz">{by_size}<figcaption><span>{esc(sizes[0])}</span><span>by model size</span><span>{esc(sizes[-1])}</span></figcaption></figure>
{peek_button(environment)}</div></div></article>"""


def request_action(label: str = "Request an appraisal", prefix: str = "") -> str:
    """The main call to action: the external request form when one is set, else the request section."""
    if REQUEST_FORM_URL:
        return (f'<a class="button button-lime" href="{esc(REQUEST_FORM_URL)}" target="_blank" rel="noopener">'
                f'{esc(label)} <span class="button-arrow" aria-hidden="true">↗</span></a>')
    return f'<a class="button button-lime" href="{prefix}index.html#request">{esc(label)} <span class="button-arrow" aria-hidden="true">↓</span></a>'


def sample_certificate(environment: dict, truth: str) -> str:
    """The hero's product shot: one real certificate from the demo run, marked as a sample."""
    top = environment["rungs"][truth]
    hack = environment["hackability"]["score"]
    overlap = environment["redundancy"]["public_overlap"]
    change = environment["actual_at_truth"]
    rows = [
        ("Learns the environment", f'{top["env_reward_before"]:.0%} → {top["env_reward_after"]:.0%}', "reward on its own tasks"),
        ("Transfers to new questions", f"{pts(change)} pts", signed_bar(change, axis_limit([change], 4))),
        ("Reward won by shortcuts", f"{hack:.0%}", meter(hack, hack >= .2)),
        ("Copied from free data", f"{overlap:.0%}", meter(overlap, overlap >= .5)),
    ]
    body = "".join(f'<div class="cert-row"><span>{label}</span><b>{value}</b><span class="cert-viz">{viz}</span></div>'
                   for label, value, viz in rows)
    return f"""<article class="cert viz" aria-label="Sample appraisal certificate">
<div class="cert-head"><span>Appraisal certificate</span><span class="cert-stamp">Sample · demo data</span></div>
<div class="cert-title"><span class="cert-grade">{esc(environment['grade'])}</span><div><strong>{esc(environment['name'])}</strong>
<small>RL environment · {environment['redundancy']['n_tasks']:,} tasks · sealed {esc(environment['sha256'][:10])}</small></div></div>
<div class="cert-rows">{body}</div>
<div class="cert-foot"><div><small>Forecast gain vs free data, at {esc(truth)}</small><b>{pts(environment['lift_over_free'])} pts</b></div>
<div><small>Fair value</small><b>${environment['fair_value_per_task']:,.0f}<em> / task</em></b></div></div>
<a class="cert-link" href="appraisals/{esc(environment['id'])}/index.html">Open the full sample certificate <span aria-hidden="true">↗</span></a></article>"""


def check_icon(yes: bool) -> str:
    path = '<path d="M5 12.5 10 17 19 7"/>' if yes else '<path d="M7 7l10 10M17 7 7 17"/>'
    return (f'<svg class="mark {"is-yes" if yes else "is-no"}" viewBox="0 0 24 24" width="18" height="18" fill="none" '
            f'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" '
            f'role="img" aria-label="{"Yes" if yes else "No"}">{path}</svg>')


def tabs(group: str, items: list[tuple[str, str]], label: str) -> str:
    """An in-page tab set: a sliding indicator over the active tab, one panel at a time."""
    buttons = "".join(
        f'<button class="seg-tab" type="button" role="tab" id="{group}-tab-{index}" aria-controls="{group}-panel-{index}" '
        f'aria-selected="{"true" if index == 0 else "false"}" tabindex="{0 if index == 0 else -1}">{esc(name)}</button>'
        for index, (name, _) in enumerate(items))
    panels = "".join(
        f'<div class="seg-panel{" is-active" if index == 0 else ""}" role="tabpanel" id="{group}-panel-{index}" '
        f'aria-labelledby="{group}-tab-{index}"{"" if index == 0 else " hidden"}>{body}</div>'
        for index, (_, body) in enumerate(items))
    return (f'<div class="seg" data-tabs><div class="seg-list glass" role="tablist" aria-label="{esc(label)}">{buttons}'
            f'<span class="seg-ink" aria-hidden="true"></span></div><div class="seg-panels">{panels}</div></div>')


def step_visuals(environment: dict, ladder: dict, truth: str) -> list[str]:
    """One small animated illustration per appraisal step."""
    biggest = max(ladder.values())
    seal = ('<div class="vis-seal"><div class="vault"><span class="vault-lid"></span>'
            + "".join(f'<i class="task-chip" style="--n:{index}">task {index + 1:03d}</i>' for index in range(4))
            + f'</div><code class="hash" data-hash="sha256 {esc(environment["sha256"][:24])}">sha256 {esc(environment["sha256"][:24])}</code></div>')
    train = ('<div class="vis-train">' + "".join(
        f'<figure class="ladder-rung" style="--d:{(params / biggest) ** .5 * 120:.1f}px;--n:{index}"><span class="ladder-dot"></span>'
        f'<figcaption><b>{esc(size)}</b>{fmt_params(params)}</figcaption></figure>'
        for index, (size, params) in enumerate(ladder.items()))
        + '<svg class="train-curve" viewBox="0 0 300 60" preserveAspectRatio="none" aria-hidden="true"><path pathLength="1" d="M0 55 C 60 50, 90 30, 150 22 S 250 8, 300 6"/></svg></div>')
    change = environment["actual_at_truth"]
    hack = environment["hackability"]["score"]
    overlap = environment["redundancy"]["public_overlap"]
    measure = ('<div class="vis-measure viz">'
               f'<div><span>Transfer to new questions</span><b>{pts(change)}</b>{signed_bar(change, axis_limit([change], 4))}</div>'
               f'<div><span>Reward won by shortcuts</span><b>{hack:.0%}</b>{meter(hack, hack >= .2)}</div>'
               f'<div><span>Copied from free data</span><b>{overlap:.0%}</b>{meter(overlap, overlap >= .5)}</div></div>')
    gains = environment["forecast"]["gains_by_rung"]
    xs = [40, 110, 180]
    ys = [70 - g * 3 for g in gains]
    price = ('<div class="vis-price"><svg viewBox="0 0 320 120" aria-hidden="true">'
             '<line class="pr-axis" x1="20" y1="100" x2="310" y2="100"/>'
             '<polygon class="pr-band" points="180,72 290,30 290,74 180,86"/>'
             f'<path class="pr-fit" pathLength="1" d="M{xs[0]} {ys[0]:.1f} L{xs[1]} {ys[1]:.1f} L{xs[2]} {ys[2]:.1f}"/>'
             f'<path class="pr-forecast" pathLength="1" d="M{xs[2]} {ys[2]:.1f} L290 52"/>'
             + "".join(f'<circle class="pr-dot" cx="{x}" cy="{y:.1f}" r="4" style="--n:{index}"/>' for index, (x, y) in enumerate(zip(xs, ys)))
             + f'<circle class="pr-target" cx="290" cy="52" r="6"/><text x="290" y="116" text-anchor="middle">{esc(truth)}</text></svg>'
             f'<div class="price-tag"><b>${environment["fair_value_per_task"]:,.0f}</b><span>fair value per task</span></div></div>')
    return [seal, train, measure, price]


def console_runs() -> str:
    """Two illustrative appraisal runs the hero console plays in a loop."""
    runs = (
        ("coding-agent-v3", "2 reward exploits found", "31% of tasks already free", "−0.4 pts", "Not worth full price", "is-bad"),
        ("math-reasoning-v1", "No exploits found", "6% of tasks already free", "+4.1 pts", "Worth buying", "is-good"),
    )
    blocks = []
    for index, (name, exploits, overlap, gain, verdict, tone) in enumerate(runs):
        bars = "".join(f'<span class="c-bar"><em>{size}</em><i style="--w:{width}%"></i></span>'
                       for size, width in (("S", 38), ("M", 57), ("L", 74), ("XL", 92)))
        blocks.append(f"""<div class="c-run{" is-active" if index == 0 else ""}" data-run="{index}">
<p class="c-line" data-l="0"><span class="c-prompt">›</span> seal <b>{name}</b><span class="c-ok">sealed ✓</span></p>
<p class="c-line" data-l="1"><span class="c-prompt">›</span> train 4 small models</p><div class="c-bars" data-l="2">{bars}</div>
<p class="c-line" data-l="3"><span class="c-prompt">›</span> probe the grader<span class="c-flag {tone}">{exploits}</span></p>
<p class="c-line" data-l="4"><span class="c-prompt">›</span> check overlap<span class="c-flag">{overlap}</span></p>
<p class="c-line" data-l="5"><span class="c-prompt">›</span> forecast at your scale<span class="c-flag {tone}">{gain}</span></p>
<p class="c-verdict {tone}" data-l="6">{verdict}</p></div>""")
    return "".join(blocks)


def home_page(data: dict, ranked: list[dict], base: dict, best: dict) -> str:
    ladder = data["ladder"]
    biggest = max(ladder.values())
    spheres = "".join(f'<figure class="ladder-rung" style="--d:{(params / biggest) ** .5 * 110:.1f}px;--n:{index}"><span class="ladder-dot"></span>'
                      f'<figcaption><b>{esc(size)}</b>{fmt_params(params)}</figcaption></figure>' for index, (size, params) in enumerate(ladder.items()))
    visuals = [
        '<div class="vis-seal"><div class="vault"><span class="vault-lid"></span>' + "".join(f'<i class="task-chip">task {n:03d}</i>' for n in range(1, 5))
        + '</div><code class="hash">sealed · sha256 7f3a9c04e1b2…</code></div>',
        f'<div class="vis-train">{spheres}<svg class="train-curve" viewBox="0 0 300 60" preserveAspectRatio="none" aria-hidden="true"><path pathLength="1" d="M0 55 C 60 50, 90 30, 150 22 S 250 8, 300 6"/></svg></div>',
        '<div class="vis-measure viz"><div><span>Better on new problems</span><b>+4.1</b>' + signed_bar(4.1, 6)
        + '</div><div><span>Reward won by exploits</span><b>0%</b>' + meter(0) + '</div><div><span>Already free</span><b>6%</b>' + meter(.06) + '</div></div>',
        '<div class="vis-price"><svg viewBox="0 0 320 120" aria-hidden="true"><line class="pr-axis" x1="20" y1="100" x2="310" y2="100"/>'
        '<polygon class="pr-band" points="180,58 290,22 290,62 180,74"/><path class="pr-fit" pathLength="1" d="M40 88 L110 76 L180 66"/>'
        '<path class="pr-forecast" pathLength="1" d="M180 66 L290 42"/><circle class="pr-dot" cx="40" cy="88" r="4"/><circle class="pr-dot" cx="110" cy="76" r="4"/>'
        '<circle class="pr-dot" cx="180" cy="66" r="4"/><circle class="pr-target" cx="290" cy="42" r="6"/><text x="290" y="116" text-anchor="middle">your scale</text></svg>'
        '<div class="price-tag"><b>$640</b><span>fair value per task</span></div></div>',
    ]
    steps = (("Seal", "The vendor's tasks go into a sealed sandbox. You only ever see results."),
             ("Train small", "Small open models train on it with one fixed recipe, at four sizes."),
             ("Measure", "We test on private problems and try to fool the grader."),
             ("Forecast and price", "We predict the gain at your model size and price each task."))
    step_list = "".join(f'<li class="scrolly-step{" is-active" if i == 0 else ""}" data-step="{i}"><button type="button"><span class="step-no">0{i + 1}</span>'
                        f'<b>{t}</b><p>{x}</p></button></li>' for i, (t, x) in enumerate(steps))
    stage = "".join(f'<div class="stage-panel{" is-active" if i == 0 else ""}" data-stage="{i}">{v}</div>' for i, v in enumerate(visuals))
    bento = (
        ("is-wide", "Transfer", "Does it make your model better at problems it never saw?", '<svg class="b-art b-rise" viewBox="0 0 200 80" aria-hidden="true"><path pathLength="1" d="M0 70 C40 66 60 50 90 44 S150 18 200 10"/><circle cx="200" cy="10" r="5"/></svg>'),
        ("", "Reward exploits", "Can a model score without solving the task?", '<div class="b-art b-exploit" aria-hidden="true"><i></i><i></i><i></i><b>2 found</b></div>'),
        ("", "Redundant tasks", "How much of it is already free?", '<div class="b-art b-venn" aria-hidden="true"><i></i><i></i><b>31%</b></div>'),
        ("", "Forecast", "What gain should you expect at your model size?", '<div class="b-art b-scale" aria-hidden="true"><i></i><i></i><i></i><i></i></div>'),
        ("", "Fair value", "What is each task actually worth?", '<div class="b-art b-price" aria-hidden="true"><b>$640</b><s>$2,000</s></div>'),
    )
    bento_html = "".join(f'<article class="bento-tile tilt {cls}" data-rise><div class="b-copy"><h3>{title}</h3><p>{text}</p></div>{art}</article>'
                         for cls, title, text, art in bento)
    compare_envs = (("Env A · coding agent", 92, 2.0, .4), ("Env B · math reasoning", 81, 9.1, 3.1),
                    ("Env C · web browsing", 75, 6.2, 1.8), ("Env D · tool use", 70, 4.0, 1.1))
    compare_rows = "".join(
        f'<div class="cmp-bar" data-reward="{reward}" data-transfer="{transfer}" data-value="{value}">'
        f'<span>{esc(name)}</span><i style="--w:{reward}%"></i><b>{reward}%</b></div>'
        for name, reward, transfer, value in compare_envs)
    compare = (f'<div class="compare glass-panel" data-compare><div class="seg-list glass" role="tablist" aria-label="Rank environments by">'
               f'<button class="seg-tab" type="button" role="tab" aria-selected="true" data-metric="reward">Training reward</button>'
               f'<button class="seg-tab" type="button" role="tab" aria-selected="false" data-metric="transfer">Real improvement</button>'
               f'<button class="seg-tab" type="button" role="tab" aria-selected="false" data-metric="value">Value per $1k</button>'
               f'<span class="seg-ink" aria-hidden="true"></span></div><div class="cmp-bars" role="img" aria-label="Four illustrative environments ranked by the selected measure">{compare_rows}</div>'
               f'<p class="cmp-note" data-note>Ranked by training reward, Env A looks best.</p></div>')
    audience = tabs("audience", [
        ("AI teams buying data", '<ul class="ticks"><li>Test an environment before you sign</li><li>Compare vendors on one private test</li><li>Stop paying for tasks your model can game</li></ul>'),
        ("Vendors selling it", '<ul class="ticks"><li>A neutral rating buyers trust</li><li>Find grader exploits before customers do</li><li>Back your price with measured value</li></ul>'),
    ], "Who it's for")
    # (name, measures training value 0-100, independent of the seller 0-100, note)
    players = (("Scale AI", 30, 16, "Sells training data and infrastructure, and grades its own product."),
               ("Patronus AI", 20, 74, "Independent, but tests finished models, not the data that trains them."),
               ("In-house teams", 76, 44, "Measure real value, but only after buying, with full-size training runs."),
               ("Touchstone", 84, 86, "Independent, and measures training value before you buy, with small runs."))
    quad = "".join(f'<button class="q-point{" is-us" if name == "Touchstone" else ""}{" is-left" if x > 60 else ""}" type="button" style="--x:{x}%;--y:{y}%" data-tip="{esc(note)}">'
                   f'<i></i><span>{esc(name)}</span></button>' for name, x, y, note in players)
    roadmap = "".join(f'<li class="rm-{stage.lower()}"><em>{esc(stage)}</em><b>{esc(title)}</b><p>{esc(text)}</p></li>' for stage, title, text in ROADMAP)
    request_note = "" if REQUEST_FORM_URL else '<p class="cta-note">Request form opens shortly</p>'
    faq = "".join(f'<details><summary>{q}<i aria-hidden="true"></i></summary><div class="faq-a"><p>{a}</p></div></details>' for q, a in (
        ("Do you see the vendor's tasks?", "They stay in a sealed sandbox. Buyers get results, never the tasks."),
        ("Why trust small models?", "Published work shows small runs predict which data wins at scale. Every report also shows how well our forecast held up."),
        ("Which models do you train?", "A fixed family of small open models, for example 0.5B, 1.5B and 3B, with one published recipe."),
        ("What can you test today?", "RL environments with automatic graders. Post-training datasets and other data types come next."),
        ("What does it cost?", "Pilot appraisals are priced per environment. Subscriptions cover continuous testing and comparison."),
    ))
    team = ""
    if FOUNDERS:
        people = "".join(f'<article class="t-card tilt person"><b>{esc(name)}</b><small>{esc(role)}</small><p>{esc(why)}</p>'
                         + (f'<a href="{esc(link)}" target="_blank" rel="noopener">Profile ↗</a>' if link else "") + "</article>"
                         for name, role, why, link in FOUNDERS)
        team = f'<section class="container t-section"><div class="t-head"><p class="t-kicker">Team</p><h2 data-split>Who is <em>building this.</em></h2></div><div class="t-problems">{people}</div></section>'
    statement = ("Touchstone helps AI companies decide which training data and RL environments are worth paying for, "
                 "before they commit to full-scale training.")
    content = f"""<header class="t-hero"><canvas class="shader" data-shader aria-hidden="true"></canvas><div class="container t-hero-inner">
<div class="t-hero-copy"><p class="t-pill" data-intro><i></i>Pilot appraisals opening</p>
<h1 data-split>Will this training data make your model <em>better?</em></h1>
<p class="t-lede" data-intro>Touchstone answers before you pay. We run small, cheap experiments on RL environments and training data, then tell you what they are worth.</p>
<div class="t-actions" data-intro>{request_action()}<a class="button button-ring" href="#how">See how it works <span class="button-arrow">↓</span></a></div></div>
<div class="t-console glass" data-intro aria-label="An illustrative appraisal run"><div class="t-console-bar"><span class="lights"><i class="light is-close"></i><i class="light is-min"></i><i class="light is-zoom"></i></span><span>touchstone · appraisal</span><em>illustrative</em></div>
<div class="t-console-body">{console_runs()}</div></div></div></header>
<div class="marquee" aria-hidden="true"><div class="marquee-track">{"".join(f"<span>{q}</span><i>✦</i>" for q in ("Does it teach?", "Can it be gamed?", "Is it new?", "Will it scale?", "What is it worth?") * 4)}</div></div>
<main class="t-main">
<section class="container t-statement"><p class="t-kicker">What we do</p><p class="t-scrub" data-scrub-text>{statement}</p></section>
<section class="container t-section"><div class="t-head"><p class="t-kicker">The problem</p><h2 data-split>Training is expensive. <em>Guessing is worse.</em></h2></div>
<div class="t-problems">
<article class="t-card tilt" data-rise><span class="t-icon">$</span><b data-count>$2,000</b><p>Top price of one RL environment task</p>{info_chip("pop-price", "What RL tasks cost")}</article>
<article class="t-card tilt" data-rise><span class="t-icon">≠</span><b>Rewards mislead</b><p>High reward does not mean the model learned a real skill</p>{info_chip("pop-hack", "Reward hacking")}</article>
<article class="t-card tilt" data-rise><span class="t-icon">⧗</span><b>Weeks of GPU</b><p>Full training runs are how most teams find out today</p>{info_chip("pop-self", "How teams check today")}</article></div></section>
<section class="container t-section"><div class="t-head t-head-split"><div><p class="t-kicker">Why now</p><h2 data-split>The money is moving <em>to training data.</em></h2></div>
<p data-rise>Reported figures from public sources. Spend is rising faster than anyone's ability to check it.</p></div>
<div class="why-grid">
<article class="why-card tilt"><b data-count>$1B</b><span>a year</span><p>Reported spend on human-curated data by each leading lab</p></article>
<article class="why-card tilt"><b data-count>55%</b><span>of AI cloud spend</span><p>Inference share Gartner expects in 2026, driven by fine-tuned models in production</p></article>
<article class="why-card tilt"><b>0</b><span>neutral auditors</span><p>Independent checks of training value in current market maps</p></article></div></section>
<section class="scrolly" id="how"><div class="container scrolly-inner"><div class="scrolly-copy"><p class="t-kicker">How it works</p>
<h2 data-split class="h2 is-large">Small experiments, <em>before the big spend.</em></h2><ol class="scrolly-steps">{step_list}</ol></div>
<div class="scrolly-stage-wrap"><div class="scrolly-stage glass-panel">{stage}<div class="stage-progress" aria-hidden="true"><i></i></div></div></div></div></section>
<section class="container t-section"><div class="t-head"><p class="t-kicker">What you get</p><h2 data-split>One report. <em>Five answers.</em></h2></div><div class="bento">{bento_html}</div></section>
<section class="container t-section"><div class="t-head t-head-split"><div><p class="t-kicker">Compare environments · coming in the MVP</p><h2 data-split>The highest reward <em>isn't the best buy.</em></h2></div>
<p data-rise>Switch the ranking and watch the order change. Illustrative numbers.</p></div>{compare}</section>
<section class="container t-section t-two"><div><p class="t-kicker">Who it's for</p><h2 data-split class="h2">Both sides <em>of the deal.</em></h2>{audience}</div>
<div><p class="t-kicker">Where we fit</p><h2 data-split class="h2">Independent, <em>and cheap to run.</em></h2>
<div class="quad" data-rise><span class="q-axis q-x">Measures training value →</span><span class="q-axis q-y">Independent →</span>{quad}</div><p class="q-hint">Hover a name for detail</p></div></section>
<section class="container t-section"><div class="t-head"><p class="t-kicker">The opportunity</p><h2 data-split>A verification layer <em>for a new market.</em></h2></div>
<div class="market"><div class="market-figure glass-panel" data-rise><small>Revenue opportunity · our estimate</small><b>$30M–$100M+</b>
<p>If environment and post-training data spend reaches a few billion dollars a year by 2027–28, a verification layer taking 1–3% is a $30M–$100M+ business, before any marketplace.</p>
<div class="market-bar" aria-hidden="true"><i style="--w:100%"><span>Data and environment spend · $ billions</span></i><i class="is-us" style="--w:3%"><span>Touchstone · 1–3%</span></i></div></div>
<div class="moat"><p class="t-kicker">Why it compounds</p>
<article class="moat-card"><b>Neutral by design</b><p>We never sell data or environments.</p></article>
<article class="moat-card"><b>A private test suite</b><p>No vendor can train on it. Its value grows the longer it stays clean.</p></article>
<article class="moat-card"><b>Every appraisal teaches us</b><p>Each run sharpens which environment features actually transfer.</p></article>
<article class="moat-card"><b>The first standard sticks</b><p>In ratings and audits, the first credible standard tends to win.</p></article></div></div></section>
<section class="container t-section"><div class="t-head"><p class="t-kicker">The science</p><h2 data-split>Small runs <em>predict big ones.</em></h2></div><div class="t-research">
<a class="t-card tilt research" href="https://proceedings.mlr.press/v235/xia24c.html" target="_blank" rel="noopener" data-rise><b>5%</b><p>of well-chosen data can beat training on all of it</p><small>Xia et al. · LESS · ICML 2024 ↗</small></a>
<a class="t-card tilt research" href="https://proceedings.mlr.press/v267/magnusson25a.html" target="_blank" rel="noopener" data-rise><b>Small → large</b><p>Small experiments predict which data wins at scale</p><small>Magnusson et al. · DataDecide · ICML 2025 ↗</small></a></div></section>
<section class="container t-section"><div class="t-head"><p class="t-kicker">Pricing</p><h2 data-split>Pay per appraisal, <em>or subscribe.</em></h2></div><div class="t-plans">
<article class="t-plan tilt" data-rise><p class="t-kicker">Per appraisal</p><h3>Check one environment</h3><p>Before you buy or train on it.</p><ul class="ticks"><li>Sealed test</li><li>Full report</li><li>Fair-value estimate</li></ul>{request_action("Request an appraisal")}</article>
<article class="t-plan tilt is-featured" data-rise><p class="t-kicker">Subscription</p><h3>Every environment, always</h3><p>For teams training continuously.</p><ul class="ticks"><li>Side-by-side comparison</li><li>Re-tests as environments change</li><li>Vendor ratings over time</li></ul>{request_action("Talk to us")}</article></div></section>
{team}<section class="container t-section"><div class="t-head"><p class="t-kicker">Roadmap</p><h2 data-split>Where we are, <em>where we're going.</em></h2></div><ol class="roadmap" data-rise>{roadmap}</ol></section>
<section class="container t-section faq"><div class="t-head"><p class="t-kicker">Questions</p><h2 data-split>Fair questions, <em>short answers.</em></h2></div>{faq}</section>
<section class="cta-band" id="request"><canvas class="shader" data-shader aria-hidden="true"></canvas><div class="container cta-inner"><div>
<p class="t-kicker">Pilot appraisals</p><h2 data-split>Know before <em>you train.</em></h2>{request_note}</div>
<div class="cta-actions">{request_action() if REQUEST_FORM_URL else ""}<a class="button button-ring" href="appraisals/index.html">See a sample report <span class="button-arrow">↗</span></a></div></div></section>
</main>{"".join([
        pop_window("pop-price", "What RL tasks cost", [("", '<div class="pop-copy"><p>Single RL environment tasks typically sell for <strong>$200 to $2,000</strong>, sometimes $20k. Exclusive deals cost 4 to 5 times more.</p></div><p class="fine-print">Price summary citing Epoch AI</p>')]),
        pop_window("pop-hack", "Why rewards mislead", [("", '<div class="pop-copy"><p>Weak graders, leaked answers and tasks passed without being solved are the most reported failure. A model can score high and learn nothing it can use elsewhere.</p></div>')]),
        pop_window("pop-self", "How teams check today", [("", '<div class="pop-copy"><p>Buyers test a small sample, trust results the vendor ran on its own setup, or run full-size training and find out weeks later.</p></div>')]),
    ])}"""
    return app_shell(content, "Touchstone", "Touchstone runs small, cheap experiments so AI companies know which training data and RL environments are worth paying for.", "", "home", "is-home")


def process_cards(variant: str = "journey") -> str:
    items = [
        ("◆", "Seal", "Fingerprint the environment and keep vendor tasks private."),
        ("⌁", "Probe", "Try non-solutions against the grader. Catch reward hacks early."),
        ("↗", "Train", "Run one repeatable GRPO recipe at every model size."),
        ("◉", "Measure", "Test private-suite transfer, contamination, and free-set overlap."),
        ("≈", "Value", "Forecast at buyer scale. Price only what is novel and useful."),
    ]
    return "".join(
        f'<article class="process-card process-card--{variant} reveal">'
        f'<span class="process-mark" aria-hidden="true">{mark}</span>'
        f'{info_chip("step-" + title.lower(), "More about the " + title + " step")}'
        f'<div><h3>{title}</h3><p>{description}</p></div></article>'
        for mark, title, description in items
    )


def process_windows(data: dict) -> str:
    environments = data["environments"]
    sample = environments[0]
    exploits = list(sample["hackability"]["per_exploit"])
    third = data["heldout_items"] // 3
    steps = [
        ("seal", "Seal", (
            '<div class="pop-copy"><p>Each vendor environment is copied into a content-addressed vault and fingerprinted. '
            'Any later change to a task or the grader changes the fingerprint.</p></div>'
            f'<p class="pop-label">Fingerprint · {esc(sample["name"])}</p><p class="pop-formula">{esc(sample["sha256"])}</p>'
            '<p class="pop-note">In production the vault also runs in an isolated container with no network.</p>')),
        ("probe", "Probe", (
            '<div class="pop-copy"><p>Before any training, we hand the grader answers that should earn nothing. '
            'If any of them collects 20% or more of the reward, the grader is flagged and the set is not priced.</p></div>'
            '<ul class="pop-env-list">' + "".join(f'<li style="--n:{index}"><i>{index + 1}</i>{esc(name)}</li>' for index, name in enumerate(exploits)) + '</ul>')),
        ("train", "Train", (
            '<div class="pop-copy"><p>One group-relative policy-gradient recipe with a KL penalty to the base model, '
            'and learning rates scaled by width. The same recipe runs at every rung.</p></div>' + model_ladder(data["ladder"]))),
        ("measure", "Measure", (
            f'<div class="pop-copy"><p>Every trained model answers {data["heldout_items"]} private questions it never practiced. '
            'We also check overlap with free public sets and with the private suite itself.</p></div>'
            f'<div class="suite-split viz"><span style="--a:55%;--n:0">2-digit + · {third}</span><span style="--a:35%;--n:1">3-digit + · {third}</span><span style="--a:20%;--n:2">Reversal · {third}</span></div>')),
        ("value", "Value", (
            '<div class="pop-copy"><p>We fit score gain against log(parameters), bootstrap the held-out items for a 90% range, '
            'and forecast at the largest rung. Only lift beyond free practice is priced.</p></div>'
            f'<p class="pop-formula">value per task = max(0, lift over free) × ${data["dollars_per_point"]:,} per point ÷ unique tasks × share not in free sets</p>'
            '<p class="pop-note">Sets with a gameable grader get no price until the vendor fixes it.</p>')),
    ]
    return "".join(pop_window(f"step-{key}", f"Step · {title}", [("", body)], wide=key == "seal")
                   for key, title, body in steps)


def appraisals_page(ranked: list[dict], base: dict) -> str:
    counts = {grade: sum(env["grade"] == grade for env in ranked) for grade in "ABCDF"}
    filters = '<button class="filter active" data-filter="all" aria-pressed="true">All results <span>' + str(len(ranked)) + '</span></button>'
    filters += "".join(f'<button class="filter" data-filter="{grade}" aria-label="Filter by grade {grade}" aria-pressed="false">{grade} <span>{count}</span></button>'
                       for grade, count in counts.items() if count)
    cards = "".join(result_card(env, "", index * 60) for index, env in enumerate(ranked))
    body = f"""<main class="container"><header class="page-head"><p class="eyebrow">Sample report · demo data</p>
<h1 class="page-title">Six environments.<br><span>One test.</span></h1><p class="page-intro">A demo appraisal of six fictional RL environments, each built to show a common failure, trained on tiny models. The pipeline is real; the vendors and numbers are examples.</p>
<div class="toolbar"><div class="filters" role="group" aria-label="Filter appraisals by grade">{filters}</div>
<label class="search"><span aria-hidden="true">⌕</span><input id="appraisal-search" type="search" placeholder="Search environments" aria-label="Search environments"></label></div>
<div class="result-grid">{cards}<p class="empty-state" hidden>No matches. Try a different search or grade.</p></div>
<aside class="baseline-aside"><p class="fine-print">The yardstick every grade is measured against</p>{spec_list([("Free comparison set", esc(base['name'])), ("Tasks", f"{base['redundancy']['n_tasks']:,}"), ("Its change on new questions", pts(base['actual_at_truth']))])}</aside></header></main>
{''.join(peek_window(env, env['id'] + '/index.html') for env in ranked)}"""
    return app_shell(body, "Appraisals", "Browse independent environment appraisals and open each evidence certificate.", "../", "appraisals")


def detail_page(data: dict, environment: dict, base: dict) -> str:
    truth = data["truth_rung"]
    rows = []
    for size, rung in environment["rungs"].items():
        check = '<span class="check">BUYER SCALE</span>' if size == truth else ""
        transfer = rung["heldout_after"] - rung["heldout_before"]
        rows.append(f"""<tr><td><b>{esc(size)}</b> {check}</td><td class="num">{fmt_params(rung['params'])}</td>
<td class="num">{rung['env_reward_before']:.0%} → {rung['env_reward_after']:.0%}</td>
<td class="num">{rung['heldout_before']:.1f} → {rung['heldout_after']:.1f}</td>
<td class="num">{pts(transfer)}</td><td>{spark(rung['curve'])}</td></tr>""")
    lift, hack = environment["lift_over_free"], environment["hackability"]["score"]
    novel = 1 - environment["redundancy"]["public_overlap"]
    unique = environment["redundancy"]["unique_tasks"]
    value_math = (f'max(0, {lift:+.2f}) pts × ${data["dollars_per_point"]:,} per pt ÷ {unique:,} unique tasks × {novel:.0%} not free'
                  if hack < .2 else f'Not priced: shortcut answers earned {hack:.0%} of the reward, above the 20% limit.')
    explainers = "".join([
        pop_window("pop-lift", "Forecast vs free practice", [("", (
            f'<div class="pop-copy"><p>The forecast for this set at {esc(truth)} minus the forecast for <strong>{esc(base["name"])}</strong>.</p></div>'
            f'<div class="pop-stats"><div class="pop-stat"><small>This set</small><b data-count>{pts(environment["forecast"]["forecast"])}</b></div>'
            f'<div class="pop-stat"><small>Free set</small><b data-count>{pts(base["forecast"]["forecast"])}</b></div>'
            f'<div class="pop-stat"><small>Difference</small><b data-count>{pts(lift)}</b></div></div>'
            '<p class="pop-note">Grades: A at +5 or more, B at +2, C at +0.5. Shortcuts or a training-vs-test gap cap the grade at D.</p>'))]),
        pop_window("pop-hack", "Shortcut probes", [("", (
            '<p class="pop-label">Reward earned by each non-answer</p>' + probe_bars(environment)))], wide=True),
        pop_window("pop-value", "How value per task is estimated", [("", (
            f'<div class="pop-copy"><p>Buyers only pay for improvement beyond free practice, and only for tasks they cannot already get for free.</p></div>'
            f'<p class="pop-formula">{esc(value_math)}</p>'
            f'<div class="pop-stats"><div class="pop-stat"><small>Lift</small><b data-count>{pts(lift)}</b></div>'
            f'<div class="pop-stat"><small>Not free</small><b data-count>{novel:.0%}</b></div>'
            f'<div class="pop-stat"><small>Per task</small><b data-count>${environment["fair_value_per_task"]:,.0f}</b></div></div>'))]),
    ])
    flags = environment["flags"]
    integrity = (f'<p class="fine-print is-alert">{len(flags)} appraisal flag{"s" if len(flags) != 1 else ""}</p><ul class="pop-flags">'
                 + "".join(f"<li>{esc(flag)}</li>" for flag in flags) + "</ul>"
                 if flags else '<div class="integrity-note clean">No appraisal flags found for this environment.</div>')
    grader = "Passed" if environment["grader"]["ok"] else "Needs review"
    content = f"""<main class="container"><header class="page-head"><p class="eyebrow"><a href="../index.html">← Sample report</a> · Sample certificate · demo data</p>
<section class="detail-hero"><p class="eyebrow">Touchstone appraisal · Run {esc(data['generated'].split()[0])}</p>
<h1>{esc(environment['name'])}</h1><div class="detail-meta"><span class="detail-grade" aria-label="Grade {esc(environment['grade'])}">{esc(environment['grade'])}</span><span>Forecast at {esc(truth)}: <b>{pts(environment['forecast']['forecast'])} pts</b></span><span>·</span><span>{environment['redundancy']['n_tasks']:,} tasks · {environment['redundancy']['unique_tasks']:,} unique</span></div>
<div class="detail-actions"><a class="button button-lime" href="#evidence">Explore evidence <span class="button-arrow">↓</span></a><button type="button" class="button button-ring" data-print>Print certificate <span class="button-arrow">⎙</span></button>
<button type="button" class="button button-kbd" data-copy="{esc(environment['sha256'])}">Copy fingerprint <kbd>#</kbd></button></div></section>
<div class="detail-signals"><div class="detail-forecast"><span>Forecast at {esc(truth)} scale</span><strong data-count>{pts(environment['forecast']['forecast'])}</strong><small>90% range {environment['forecast']['lo']:+.1f} to {environment['forecast']['hi']:+.1f} pts</small>{range_strip(environment)}</div>
<div class="detail-ledger"><p><b data-count>{pts(environment['lift_over_free'])} pts</b><span>forecast vs {esc(base['name'])}</span>{info_chip("pop-lift", "How forecast vs free is computed")}</p>
<p><b data-count>{environment['hackability']['score']:.0%}</b><span>reward earned by shortcut probes</span>{info_chip("pop-hack", "Show every shortcut probe")}</p>
<p><b data-count>${environment['fair_value_per_task']:,.0f}</b><span>estimated value per task</span>{info_chip("pop-value", "How value per task is estimated")}</p></div></div></header>
<section class="evidence-grid" id="evidence"><div class="panel reveal"><h2>Before and after, by size.</h2><p class="panel-intro">Each row starts at the score before practice (tick) and points to the score after (arrow). Hover a row to drop it onto the axis.</p>{ladder_chart(environment)}</div>
<div class="panel reveal"><h2>Would the grader reward a shortcut?</h2><p class="panel-intro">Reward received by non-solutions. Lower is better; 20% or more is flagged.</p>{probe_bars(environment)}
{spec_list([("Grader reliability", grader), ("Copied from free", f"{environment['redundancy']['public_overlap']:.0%}"), ("Overlap with private suite", f"{environment['contamination']:.1%}")])}</div></section>
<section class="panel"><h2>Transfer, at every scale.</h2><p class="panel-intro">Held-out score before and after training. The buyer-scale rung anchors the forecast.</p>
<div class="table-wrap"><table><thead><tr><th>Model</th><th class="num">Parameters</th><th class="num">Vendor reward</th><th class="num">Held-out score</th><th class="num">Transfer</th><th>Training reward</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<div class="hash-box"><small>Sealed environment · SHA-256</small><code>{esc(environment['sha256'])}</code><button class="copy-button" type="button" data-copy="{esc(environment['sha256'])}">Copy fingerprint</button></div>
{integrity}</section>
</main>{explainers}"""
    return app_shell(content, environment["name"], "Evidence certificate with transfer, integrity, grader-probe, and fair-value results.", "../../", "appraisals")


def forecast_page(data: dict) -> str:
    validation = data["validation"]
    rho = validation["spearman_forecast_vs_actual"]
    verdict_lead, verdict = (("Promising, not proven.", "Small-model results tracked the larger model in this sample. Test again on much larger, representative models before relying on it.") if rho >= .6 else
                             ("No useful match.", "The small-model forecasts did not predict which sets helped more. With six sets and tiny models, read this as a warning, not proof that scaling helps or hurts."))
    envs = [env for env in data["environments"] if not env["is_public_baseline"]]
    content = f"""<main class="container"><header class="page-head"><p class="eyebrow">Small → large model validation</p>
<h1 class="page-title">Do small tests predict<br><span>what larger AI learns?</span></h1><p class="page-intro">We use results from smaller AI models to predict which practice sets will help larger ones. Then we check those predictions against what happened in this test.</p></header>
<section class="panel chart-panel"><div class="chart-copy"><p class="eyebrow">A test of the forecast · {len(envs)} practice sets</p><h2>Did the prediction hold up?</h2>
<p>Each square is a practice set, placed by its forecast and by what was measured. The closer to the diagonal, the better the forecast.</p>
<div class="chart-stat"><b data-count>{rho:.2f}</b><span>Rank match: did the sets stay in the same order?</span></div>
{spec_list([("1", "same order"), ("0", "no match"), ("below 0", "reversed"), ("Average miss", pts(validation['mean_abs_error_pts']).lstrip("+") + " pts")])}
<p class="fine-print">A rank correlation, not a percent or accuracy score</p>
<div class="verdict"><b class="verdict-lead">{esc(verdict_lead)}</b>{esc(verdict)}</div><p class="scale-caveat"><strong>Scaling can go either way.</strong> A larger model may learn a useful skill more strongly, or a harmful shortcut more strongly.</p>
{spec_list([("Models in this run", f"{fmt_params(min(data['ladder'].values()))}–{fmt_params(max(data['ladder'].values()))}"), ("Commercial models", "billions")])}
<p class="fine-print">Commercial scale needs its own test on much larger models</p>
<a class="section-link" href="../appraisals/index.html">Compare the practice sets ↗</a></div>
<div class="chart-frame viz crop"><div class="chart-tooltip" role="status" aria-live="polite"></div>{scatter(envs, validation['mean_abs_error_pts'])}{chart_legend(envs)}<p class="chart-hint">Move across the plot: the crosshair reads both axes and snaps to the nearest set. Dashed drops show each miss. Click for a quick look.</p></div></section>
<section class="panel slope-panel reveal"><div><p class="eyebrow">Same data, ranked</p><h2>Did the order survive?</h2>
<p>Left is the order the forecast predicted; right is the order measured on the largest model. A forecast that ranks well draws flat lines. Hover a set to trace it.</p>{rho_scale(rho)}</div>
{rank_slope(envs)}</section>
<section class="section"><div class="section-heading"><div><p class="eyebrow">Reading the chart</p><h2>Honest about<br><span>uncertainty.</span></h2></div><p>The forecast is an experiment, not a buying promise. For now, use the individual test results, and wait for tests on larger AI models before trusting predictions about scale.</p></div>
<div class="chart-note-rail"><p><b>x</b><span>Predicted score change<small>What the small-model results suggested.</small></span></p>
<p><b>y</b><span>Measured score change<small>What happened on the largest test model.</small></span></p>
<p><i aria-hidden="true"></i><span>Perfect prediction<small>Dots near the line match the forecast.</small></span></p></div></section></main>
{''.join(peek_window(env, '../appraisals/' + env['id'] + '/index.html') for env in envs)}"""
    return app_shell(content, "Forecast validation", "Compare small-model transfer forecasts against observed buyer-scale outcomes.", "../", "forecast")


def methodology_page(data: dict) -> str:
    content = f"""<main class="container"><header class="page-head"><p class="eyebrow">How it works</p>
<h1 class="page-title">How an appraisal<br><span>works.</span></h1><p class="page-intro">The environment goes into a sealed sandbox. We train small models on it, measure what carries over to new questions, try to game its grader and forecast the gain at your scale. Select a step for detail.</p></header>
<section class="process-grid process-journey">{process_cards("journey")}</section>
<section class="section"><div class="section-heading"><div><p class="eyebrow">The prototype</p><h2>Real pipeline.<br><span>Prototype scale.</span></h2></div><p>Every step runs end to end today. The sample vendors and tiny CPU models are demonstration data, chosen so the run finishes on a laptop.</p></div>
<div class="pilot-notes"><p class="pilot-vendors"><strong>Six</strong><span>fictional environments</span><small>Designed to expose grading shortcuts, contamination, and answer leakage.</small></p>
<p class="pilot-models"><strong>29K–1.3M</strong><span>parameters, trained on CPU</span><small>One fixed character-level GRPO recipe across model sizes.</small></p>
<p class="pilot-suite"><strong data-count>{data['heldout_items']}</strong><span>held-out items</span><small>Arithmetic and string reversal; production domains need their own private suites.</small></p></div>
<div class="ladder-panel panel reveal"><div><p class="eyebrow">Drawn to scale</p><h3>The model ladder.</h3><p>Each circle's area is its parameter count. Hover a circle for the exact number.</p></div><div>{model_ladder(data['ladder'])}</div></div></section>
<div class="hero-buttons" style="padding-bottom:35px">{request_action(prefix="../")}<a class="button button-outline" href="../appraisals/index.html">See the sample report <span class="button-arrow">↗</span></a></div></main>
{process_windows(data)}"""
    return app_shell(content, "Methodology", "How Touchstone seals, probes, trains, measures, and values learning environments.", "../", "methodology")


def render_site(data: dict) -> dict[str, str]:
    environments = data["environments"]
    vendors = [env for env in environments if not env["is_public_baseline"]]
    baseline = next(env for env in environments if env["is_public_baseline"])
    grade_order = "ABCDF"
    ranked = sorted(vendors, key=lambda env: (grade_order.index(env["grade"]), -env["lift_over_free"]))
    best = ranked[0] if ranked else baseline
    pages = {
        "index.html": home_page(data, ranked, baseline, best),
        "appraisals/index.html": appraisals_page(ranked, baseline),
        "forecast/index.html": forecast_page(data),
        "methodology/index.html": methodology_page(data),
    }
    for env in ranked:
        pages[f"appraisals/{env['id']}/index.html"] = detail_page(data, env, baseline)
    entries = [{"group": "Pages", "title": title, "meta": meta, "href": href, "mark": mark} for title, meta, href, mark in (
        ("Home", "What Touchstone does", "index.html", "⌂"),
        ("How it works", "Seal, train, measure, forecast and price", "methodology/index.html", "◆"),
        ("Sample report", f"{len(ranked)} demo certificates", "appraisals/index.html", "≡"),
        ("Forecast check", "Do small runs predict larger models?", "forecast/index.html", "↗"))]
    entries += [{"group": "Sample environments", "title": env["name"], "href": f"appraisals/{env['id']}/index.html", "mark": env["grade"],
                 "meta": f"Grade {env['grade']} · {pts(env['actual_at_truth'])} pts on new questions"} for env in ranked]
    pages = {path: document.replace("↗", "↗\ufe0e").replace("✳", "✳\ufe0e").replace("↕", "↕\ufe0e") for path, document in pages.items()}
    index = '<script>window.TOUCHSTONE_INDEX = ' + json.dumps(entries, ensure_ascii=False).replace("</", "<\\/") + ';</script>'
    return {path: re.sub(r'<script src="(?:\.\./)*search-index\.js"></script>', lambda _: index, document) for path, document in pages.items()}


def render(data: dict) -> str:
    """Render the home page for callers that need a single HTML document."""
    return render_site(data)["index.html"]


def write_site(data_path: Path, destination: Path) -> None:
    data = json.loads(data_path.read_text())
    for relative_path, document in render_site(data).items():
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document)
        print(f"wrote {target}")


if __name__ == "__main__":
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    write_site(source, target.parent)
