"""The Touchstone website: company pages built here, sample-report pages from report.py, one design system."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import report
from .report import FOUNDERS, ROADMAP, esc, fmt_params, pts

FONTS = ("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,300..800"
         "&family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..600&family=IBM+Plex+Mono:wght@400;500&display=swap")
LIBRARIES = (
    "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/gsap.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.13.0/SplitText.min.js",
    "https://cdn.jsdelivr.net/npm/motion@11.18.2/dist/motion.js",
)
NAV = (("product", "Product"), ("appraisals", "Sample report"), ("market", "Market"), ("pricing", "Pricing"), ("company", "Company"))

CSS = r"""
/* Layout: one 1180px column, wide margins, sections separated by space rather than rules. */
:root{
  --bg:#0b0d10;--raise:#12151a;--raise-2:#171b21;--line:#252930;--line-2:#323741;
  --ink:#f3f0e9;--ink-2:#bdb8ad;--ink-3:#837f77;
  --gold:#e4ba62;--gold-2:#f1d08a;--gold-deep:#a37a2a;--blue:#6f9fdc;--red:#ee8669;--green:#8fd0a4;
  --display:"Bricolage Grotesque","Helvetica Neue",Arial,sans-serif;
  --text:"Newsreader",Georgia,serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
  --ease:cubic-bezier(.16,1,.3,1);--spring:cubic-bezier(.34,1.56,.64,1);
  color-scheme:dark}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:96px}
body{margin:0;background:var(--bg);color:var(--ink);font:400 19px/1.65 var(--text);-webkit-font-smoothing:antialiased}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:60;background:var(--bg)}
a{color:inherit}
img,svg{max-width:100%}
.wrap{width:min(1180px,100%);margin:0 auto;padding-left:max(24px,env(safe-area-inset-left,0px));padding-right:max(24px,env(safe-area-inset-right,0px))}
.sec{padding-block:clamp(96px,12vw,168px)}
.sec.tight{padding-top:0}

/* Type scale */
.eyebrow{display:inline-flex;align-items:center;gap:12px;margin:0 0 24px;color:var(--gold);font:500 12px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase}
.eyebrow::before{content:"";width:22px;height:1px;background:currentColor}
h1,h2,h3{margin:0;font-family:var(--display);font-weight:650;color:var(--ink);text-wrap:balance}
h1{font-size:clamp(52px,7vw,104px);line-height:.98;letter-spacing:-.03em;font-variation-settings:"opsz" 96}
h2{font-size:clamp(38px,4.6vw,68px);line-height:1.02;letter-spacing:-.025em;font-variation-settings:"opsz" 96}
h3{font-size:clamp(22px,2vw,28px);line-height:1.2;letter-spacing:-.012em}
h1 em,h2 em{font-family:var(--text);font-style:italic;font-weight:400;color:var(--gold);letter-spacing:-.02em}
.lede{max-width:620px;margin:28px 0 0;color:var(--ink-2);font-size:clamp(19px,1.6vw,22px);line-height:1.6}
.head{max-width:780px;margin-bottom:clamp(56px,6vw,88px)}
.head .lede{margin-top:22px}
.muted{color:var(--ink-3)}
.mono{font-family:var(--mono)}
.note{margin:28px 0 0;color:var(--ink-3);font:400 13px/1.6 var(--mono)}

/* Buttons */
.btn{position:relative;display:inline-flex;align-items:center;gap:14px;height:54px;padding:0 10px 0 26px;border:0;border-radius:999px;background:var(--gold);color:#16130c;font:600 16px var(--display);text-decoration:none;cursor:pointer;transition:background .25s,transform .25s var(--ease),box-shadow .25s;box-shadow:0 10px 30px -10px #e4ba6280}
.btn:hover{background:var(--gold-2);transform:translateY(-2px);box-shadow:0 18px 40px -12px #e4ba62aa}
.btn i{display:grid;width:36px;height:36px;place-items:center;border-radius:50%;background:#16130c;color:var(--gold);font-style:normal;font-size:15px;transition:transform .35s var(--spring)}
.btn:hover i{transform:rotate(-45deg)}
.btn.ghost{background:transparent;color:var(--ink);box-shadow:inset 0 0 0 1px var(--line-2)}
.btn.ghost i{background:var(--raise-2);color:var(--ink)}
.btn.ghost:hover{box-shadow:inset 0 0 0 1px var(--ink-3);background:#ffffff08}
.btn.small{height:44px;padding:0 20px;font-size:14px}
.actions{display:flex;flex-wrap:wrap;gap:14px;margin-top:40px}
.link{color:var(--ink);font:500 14px var(--mono);text-decoration:none;border-bottom:1px solid var(--line-2);padding-bottom:3px;transition:border-color .2s,color .2s}
.link:hover{color:var(--gold);border-color:var(--gold)}

/* Nav */
.nav{position:sticky;top:env(safe-area-inset-top,0px);z-index:50;border-bottom:1px solid transparent;background:#0b0d10cc;-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);transition:border-color .3s}
.nav.scrolled{border-color:var(--line)}
.nav .wrap{display:flex;align-items:center;gap:32px;height:76px}
.brand{display:flex;align-items:center;gap:10px;color:var(--ink);font:700 19px var(--display);letter-spacing:-.03em;text-decoration:none}
.brand svg{width:30px;height:30px}
.nav-links{display:flex;gap:30px;margin-left:auto}
.nav-links a{color:var(--ink-2);font:500 15px var(--display);text-decoration:none;transition:color .2s}
.nav-links a:hover,.nav-links a.on{color:var(--ink)}
.nav-links a.on{box-shadow:0 2px 0 var(--gold)}
.nav .btn{height:44px;padding:0 20px;font-size:14px}
.menu{display:none;width:44px;height:44px;margin-left:auto;border:1px solid var(--line-2);border-radius:50%;background:none;color:var(--ink);cursor:pointer}

/* Surfaces */
.surface{position:relative;padding:clamp(32px,3.5vw,48px);border:1px solid var(--line);border-radius:24px;background:linear-gradient(180deg,var(--raise),#0f1216)}
.grid-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}
.grid-4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:24px}
.grid-2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}
.split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:clamp(48px,7vw,104px);align-items:center}

/* Reveal (only hides content once JS is running) */
.js [data-reveal]{opacity:0;transform:translateY(28px);transition:opacity .9s var(--ease),transform .9s var(--ease);transition-delay:var(--d,0s)}
.js [data-reveal].in{opacity:1;transform:none}
.split-line{overflow:hidden;padding-bottom:.06em}

/* Hero */
.hero{position:relative;overflow:hidden;isolation:isolate}
.hero .wrap{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);gap:64px;align-items:center;padding-top:clamp(72px,9vw,128px);padding-bottom:clamp(96px,10vw,140px)}
.aura{position:absolute;inset:-20% -10% auto;height:120%;z-index:-1;pointer-events:none;background:radial-gradient(40% 45% at 75% 35%,#e4ba6230,transparent 70%),radial-gradient(35% 40% at 20% 75%,#3a68a338,transparent 70%);animation:aura 18s ease-in-out infinite alternate}
@keyframes aura{to{transform:translate3d(-4%,3%,0) scale(1.08)}}
.hero-meta{display:flex;flex-wrap:wrap;gap:12px 28px;margin-top:44px;color:var(--ink-3);font:500 12px var(--mono);letter-spacing:.08em;text-transform:uppercase}
.hero-meta span::before{content:"";display:inline-block;width:6px;height:6px;margin-right:10px;border-radius:50%;background:var(--gold);vertical-align:2px}

/* Console */
.console{border:1px solid var(--line-2);border-radius:20px;background:#0e1115;box-shadow:0 40px 80px -30px #000c,0 0 0 1px #ffffff06 inset;overflow:hidden}
.console-bar{display:flex;align-items:center;gap:8px;padding:14px 18px;border-bottom:1px solid var(--line);color:var(--ink-3);font:500 12px var(--mono)}
.console-bar b{width:11px;height:11px;border-radius:50%;background:#ee6a5e}.console-bar b:nth-child(2){background:#f4be4f}.console-bar b:nth-child(3){background:#61c554}
.console-bar span{margin-left:10px}.console-bar em{margin-left:auto;font-style:normal;color:var(--ink-3)}
.console-body{min-height:360px;padding:26px 26px 30px;font:400 14px/1.5 var(--mono);color:#d9dce1}
.run{display:none}.run.on{display:block}
.ln{display:flex;gap:10px;margin:0 0 14px}
.ln .p{color:var(--gold)}.ln .r{margin-left:auto;color:var(--ink-3);white-space:nowrap}
.ln .r.bad{color:var(--red)}.ln .r.good{color:var(--green)}.ln b{color:#fff;font-weight:500}
.bars{display:grid;gap:8px;margin:0 0 16px 20px}
.bars div{display:grid;grid-template-columns:24px 1fr;gap:10px;align-items:center;color:var(--ink-3);font-size:11px}
.bars i{display:block;height:6px;border-radius:3px;background:linear-gradient(90deg,var(--gold-deep),var(--gold-2));transform-origin:left}
.verdict{display:inline-block;margin-top:10px;padding:10px 18px;border:1.5px solid currentColor;border-radius:8px;font:700 16px var(--display);letter-spacing:.04em;text-transform:uppercase}
.verdict.bad{color:var(--red)}.verdict.good{color:var(--green)}

/* Marquee */
.marquee{overflow:hidden;border-block:1px solid var(--line);padding:18px 0;color:var(--ink-2)}
.marquee-track{display:flex;width:max-content;gap:40px;animation:marquee 40s linear infinite}
.marquee-track span{font:500 15px var(--display);white-space:nowrap}
.marquee-track i{color:var(--gold);font-style:normal}
.marquee:hover .marquee-track{animation-play-state:paused}
@keyframes marquee{to{transform:translateX(-50%)}}

/* Stat surfaces */
.stat{display:grid;align-content:start;gap:14px}
.stat b{font:650 clamp(56px,5.6vw,84px)/1 var(--display);letter-spacing:-.03em;color:var(--ink)}
.stat:first-child b,.stat.gold b{color:var(--gold)}
.stat p{margin:0;color:var(--ink-2);font-size:18px;line-height:1.55}
.stat small{color:var(--ink-3);font:400 12px/1.5 var(--mono)}

/* Scroll story */
.story{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:clamp(48px,6vw,96px)}
.story-steps{list-style:none;margin:0;padding:0}
.story-steps li{min-height:62vh;display:flex;align-items:center}
.story-steps li:last-child{min-height:44vh}
.story-steps article{opacity:.32;transition:opacity .5s var(--ease)}
.story-steps li.on article{opacity:1}
.story-steps .n{display:block;margin-bottom:16px;color:var(--gold);font:500 13px var(--mono);letter-spacing:.1em}
.story-steps p{margin:14px 0 0;max-width:440px;color:var(--ink-2)}
.story-stage{position:sticky;top:120px;height:min(560px,70vh);align-self:start}
.stage{position:absolute;inset:0;display:grid;place-items:center;padding:40px;border:1px solid var(--line);border-radius:28px;background:radial-gradient(70% 60% at 50% 30%,#1a1e25,#0f1216);opacity:0;visibility:hidden;transform:scale(.97);transition:opacity .6s var(--ease),transform .6s var(--ease),visibility .6s}
.stage.on{opacity:1;visibility:visible;transform:none}
.stage-label{position:absolute;top:24px;left:28px;color:var(--ink-3);font:500 12px var(--mono);letter-spacing:.1em;text-transform:uppercase}

.vault{display:grid;gap:10px;width:min(300px,100%);padding:30px 24px 24px;border:1.5px solid var(--ink-2);border-radius:16px;position:relative}
.vault::before{content:"";position:absolute;inset:-1.5px -1.5px auto;height:14px;border-radius:16px 16px 0 0;background:var(--gold)}
.vault span{padding:10px 14px;border:1px solid var(--line-2);border-radius:8px;background:var(--raise-2);font:400 13px var(--mono);color:var(--ink-2)}
.seal-hash{margin-top:22px;color:var(--gold);font:400 13px var(--mono);text-align:center}

/* Dalton spheres: area proportional to parameters */
.atoms{display:flex;align-items:flex-end;justify-content:center;gap:clamp(18px,3vw,40px);width:100%}
.atom{display:grid;justify-items:center;gap:14px}
.atom i{display:block;width:var(--d);height:var(--d);border-radius:50%;background:radial-gradient(circle at 34% 30%,#fff3cf 0,#f0cf85 18%,#d9a945 52%,#8a6120 100%);box-shadow:inset -8px -12px 24px #00000055,0 24px 40px -12px #e4ba6255}
.atom.float i{animation:bob 4.5s ease-in-out infinite;animation-delay:calc(var(--n)*-.9s)}
@keyframes bob{50%{translate:0 -10px}}
.atom b{font:600 18px var(--display)}.atom small{color:var(--ink-3);font:400 12px var(--mono)}
.measure-rows{display:grid;gap:26px;width:100%}
.measure-rows div{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:baseline}
.measure-rows span{color:var(--ink-2);font:500 16px var(--display)}
.measure-rows b{font:500 18px var(--mono)}
.track{grid-column:1/-1;height:8px;border-radius:4px;background:#ffffff10;overflow:hidden}
.track i{display:block;height:100%;width:var(--w);border-radius:4px;background:var(--c,var(--gold));transform:scaleX(0);transform-origin:left;transition:transform 1.1s var(--ease) var(--d,0s)}
.on .track i,.in .track i{transform:none}
.price-vis{width:100%}
.price-vis svg{width:100%;height:auto;overflow:visible}
.price-vis .fit{fill:none;stroke:var(--ink);stroke-width:2.5;stroke-linecap:round}
.price-vis .fc{fill:none;stroke:var(--gold);stroke-width:2.5;stroke-dasharray:6 6}
.price-vis .band{fill:#e4ba6222}
.price-vis circle{fill:var(--ink)}.price-vis .target{fill:var(--gold)}
.price-vis text{fill:var(--ink-3);font:400 12px var(--mono)}
.price-tag{display:inline-grid;margin-top:8px;padding:14px 22px;border-radius:14px;background:var(--gold);color:#16130c}
.price-tag b{font:700 34px/1 var(--display)}.price-tag span{font:500 11px var(--mono);letter-spacing:.08em;text-transform:uppercase}

/* Vertical tabs (what you get) */
.vtabs{display:grid;grid-template-columns:minmax(0,.8fr) minmax(0,1.2fr);gap:clamp(32px,5vw,72px);align-items:stretch}
.vtab-list{display:grid;align-content:start;gap:6px}
.vtab{display:grid;grid-template-columns:38px 1fr;align-items:baseline;gap:10px;width:100%;padding:20px 22px;border:0;border-radius:16px;background:transparent;color:var(--ink-3);text-align:left;cursor:pointer;transition:background .3s,color .3s}
.vtab small{font:500 12px var(--mono)}
.vtab span{font:600 22px var(--display);letter-spacing:-.01em}
.vtab:hover{color:var(--ink-2);background:#ffffff05}
.vtab[aria-selected=true]{background:var(--raise-2);color:var(--ink)}
.vtab[aria-selected=true] small{color:var(--gold)}
.vpanel{display:grid;align-content:center;gap:26px;min-height:420px}
.vpanel[hidden]{display:none}
.vpanel .big{font:650 clamp(64px,7vw,104px)/1 var(--display);letter-spacing:-.035em;color:var(--gold)}
.vpanel p{margin:0;max-width:520px;color:var(--ink-2);font-size:21px}
.vpanel small{color:var(--ink-3);font:400 12px var(--mono)}

/* Compare */
.cmp-switch{display:inline-flex;gap:4px;padding:5px;border:1px solid var(--line);border-radius:999px;background:var(--raise)}
.cmp-switch button{height:42px;padding:0 20px;border:0;border-radius:999px;background:none;color:var(--ink-2);font:500 15px var(--display);cursor:pointer;transition:color .25s}
.cmp-switch button[aria-selected=true]{color:#16130c}
.cmp-switch{position:relative}
.cmp-pill{position:absolute;top:5px;left:0;height:42px;border-radius:999px;background:var(--gold);transition:transform .5s var(--spring),width .5s var(--spring)}
.cmp-switch button{position:relative;z-index:1}
.cmp-rows{display:grid;gap:22px;margin-top:44px}
.cmp-row{display:grid;grid-template-columns:240px minmax(0,1fr) 110px;gap:24px;align-items:center}
.cmp-row span{font:500 17px var(--display)}
.cmp-row .bar{height:14px;border-radius:7px;background:#ffffff0a;overflow:hidden}
.cmp-row .bar i{display:block;height:100%;width:var(--w);border-radius:7px;background:linear-gradient(90deg,var(--gold-deep),var(--gold-2));transition:width .9s var(--ease)}
.cmp-row b{font:500 16px var(--mono);text-align:right}
.cmp-row.best span{color:var(--gold)}
.cmp-note{margin:36px 0 0;color:var(--gold);font:italic 400 24px var(--text)}

/* Audience and link cards */
.points{list-style:none;margin:28px 0 0;padding:0;display:grid;gap:16px}
.points li{position:relative;padding-left:30px;color:var(--ink-2);font-size:19px}
.points li::before{content:"";position:absolute;left:0;top:.6em;width:14px;height:2px;background:var(--gold)}
.tile{display:grid;gap:12px;align-content:start;min-height:220px;text-decoration:none;transition:border-color .3s,transform .4s var(--ease)}
.tile:hover{border-color:var(--line-2);transform:translateY(-4px)}
.tile .arrow{margin-top:auto;color:var(--gold);font:500 14px var(--mono);transition:transform .3s var(--ease)}
.tile:hover .arrow{transform:translateX(6px)}
.tile p{margin:0;color:var(--ink-2);font-size:17px}

/* CTA */
.cta{position:relative;overflow:hidden;text-align:center;padding-block:clamp(110px,13vw,180px);border-top:1px solid var(--line)}
.cta h2{font-size:clamp(48px,6.6vw,104px)}
.cta .lede{margin-inline:auto}
.cta .actions{justify-content:center}

/* Certificate (product) */
.anatomy{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:clamp(48px,6vw,96px)}
.anatomy-steps li{min-height:52vh;display:flex;align-items:center}
.anatomy-steps{list-style:none;margin:0;padding:0}
.anatomy-steps article{opacity:.3;transition:opacity .5s}
.anatomy-steps li.on article{opacity:1}
.anatomy-steps p{margin:14px 0 0;color:var(--ink-2)}
.cert-wrap{position:sticky;top:120px;align-self:start}
.cert{padding:34px;border:1px solid var(--line-2);border-radius:24px;background:linear-gradient(180deg,#151920,#0f1216);box-shadow:0 40px 90px -40px #000}
.cert-top{display:flex;justify-content:space-between;align-items:center;color:var(--ink-3);font:500 11px var(--mono);letter-spacing:.12em;text-transform:uppercase}
.cert-top em{color:var(--gold);font-style:normal}
.cert-name{display:grid;grid-template-columns:64px 1fr;gap:18px;align-items:center;margin:24px 0 10px}
.cert-name .g{display:grid;width:64px;height:64px;place-items:center;border-radius:18px;background:var(--gold);color:#16130c;font:700 34px var(--display)}
.cert-name b{display:block;font:650 24px/1.2 var(--display)}
.cert-name small{color:var(--ink-3);font:400 12px var(--mono)}
.cert-row{display:grid;grid-template-columns:1fr auto;gap:10px;padding:18px 16px;margin:0 -16px;border-radius:14px;transition:background .4s}
.cert-row span{color:var(--ink-2);font:500 16px var(--display)}
.cert-row b{font:500 17px var(--mono)}
.cert-row.hl{background:#e4ba6214}
.cert-row.hl span{color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:36px}
.chip{height:42px;padding:0 18px;border:1px solid var(--line-2);border-radius:999px;background:none;color:var(--ink-2);font:500 14px var(--display);cursor:pointer;transition:all .25s}
.chip:hover{border-color:var(--ink-3);color:var(--ink)}
.chip[aria-pressed=true]{border-color:var(--gold);background:var(--gold);color:#16130c}
.flags{margin:22px 0 0;padding:0;list-style:none;display:grid;gap:8px}
.flags li{padding:10px 14px;border-radius:10px;background:#ee866914;color:var(--red);font:400 13px var(--mono)}
.flags li.ok{background:#8fd0a414;color:var(--green)}

/* Timeline */
.timeline{position:relative;list-style:none;margin:0;padding:0 0 0 48px}
.timeline::before{content:"";position:absolute;left:11px;top:8px;bottom:8px;width:2px;background:var(--line)}
.timeline::after{content:"";position:absolute;left:11px;top:8px;width:2px;height:calc((100% - 16px)*var(--p,0));background:var(--gold)}
.timeline li{position:relative;padding-bottom:56px}
.timeline li::before{content:"";position:absolute;left:-44px;top:6px;width:18px;height:18px;border:2px solid var(--line-2);border-radius:50%;background:var(--bg);transition:border-color .4s,background .4s}
.timeline li.done::before,.timeline li.now::before{border-color:var(--gold)}
.timeline li.done::before{background:var(--gold)}
.timeline li.now::before{box-shadow:0 0 0 6px #e4ba6226}
.timeline em{color:var(--gold);font:500 12px var(--mono);font-style:normal;letter-spacing:.12em;text-transform:uppercase}
.timeline li.next em,.timeline li.later em{color:var(--ink-3)}
.timeline h3{margin:8px 0 6px}
.timeline p{margin:0;max-width:560px;color:var(--ink-2)}

/* FAQ */
.faq details{border-bottom:1px solid var(--line)}
.faq details:first-child{border-top:1px solid var(--line)}
.faq summary{display:flex;justify-content:space-between;gap:24px;padding:28px 0;font:600 22px var(--display);list-style:none;cursor:pointer;transition:color .2s}
.faq summary::-webkit-details-marker{display:none}
.faq summary:hover{color:var(--gold)}
.faq summary::after{content:"+";color:var(--gold);font:400 28px/1 var(--display);transition:transform .35s var(--spring)}
.faq details[open] summary::after{transform:rotate(45deg)}
.faq details p{margin:0;padding:0 0 30px;max-width:720px;color:var(--ink-2)}

/* Market */
.counter b{font-variant-numeric:tabular-nums}
.bigfig{font:650 clamp(72px,10vw,160px)/.95 var(--display);letter-spacing:-.04em;background:linear-gradient(90deg,var(--ink),var(--gold-2));-webkit-background-clip:text;background-clip:text;color:transparent}
.spend{margin-top:48px}
.spend-bar{position:relative;height:56px;border-radius:14px;background:#ffffff0a;overflow:hidden}
.spend-bar i{position:absolute;inset:0 auto 0 0;width:3%;background:var(--gold);transform:scaleX(0);transform-origin:left;transition:transform 1.4s var(--ease) .3s}
.in .spend-bar i{transform:none}
.spend-labels{display:flex;justify-content:space-between;margin-top:14px;color:var(--ink-3);font:400 13px var(--mono)}
.spend-labels b{color:var(--gold);font-weight:500}
.map{position:relative;aspect-ratio:1.35;border:1px solid var(--line);border-radius:24px;background:linear-gradient(var(--line) 1px,transparent 1px) 0 0/25% 25%,linear-gradient(90deg,var(--line) 1px,transparent 1px) 0 0/25% 25%,var(--raise)}
.map .ax{position:absolute;color:var(--ink-3);font:500 11px var(--mono);letter-spacing:.1em;text-transform:uppercase}
.map .ax.x{right:20px;bottom:14px}.map .ax.y{left:20px;top:16px}
.dot{position:absolute;left:var(--x);bottom:var(--y);display:flex;align-items:center;gap:10px;transform:translate(-9px,9px) scale(0);transition:transform .7s var(--spring);transition-delay:var(--d)}
.in .dot{transform:translate(-9px,9px) scale(1)}
.dot i{width:18px;height:18px;border:2px solid var(--ink-3);border-radius:50%;background:var(--bg)}
.dot span{font:600 15px var(--display);white-space:nowrap}
.dot.us i{border-color:var(--gold);background:var(--gold);box-shadow:0 0 0 8px #e4ba6222,0 0 34px #e4ba6299}
.dot.us span{color:var(--gold);font-size:17px}
.dot.left{flex-direction:row-reverse;transform:translate(calc(-100% + 9px),9px) scale(0)}
.in .dot.left{transform:translate(calc(-100% + 9px),9px) scale(1)}
.rows{border-top:1px solid var(--line)}
.rows>div{display:grid;grid-template-columns:200px minmax(0,1fr) minmax(0,1fr);gap:32px;padding:28px 0;border-bottom:1px solid var(--line)}
.rows>div.us{color:var(--gold)}
.rows b{font:600 19px var(--display)}
.rows p{margin:0;color:var(--ink-2);font-size:17px}
.rows .hdr{padding:0 0 14px;color:var(--ink-3);font:500 11px var(--mono);letter-spacing:.1em;text-transform:uppercase}

/* Pricing */
.plan{display:grid;align-content:start;gap:18px}
.plan.feature{border-color:#e4ba6255;background:linear-gradient(180deg,#1b1a15,#0f1216)}
.plan .price{font:650 44px/1 var(--display);letter-spacing:-.02em}
.plan .price small{color:var(--ink-3);font:400 15px var(--text)}
.plan .btn{justify-self:start;margin-top:12px}
.calc{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:clamp(40px,6vw,88px);align-items:center}
.field{display:grid;gap:12px;margin-bottom:34px}
.field label{display:flex;justify-content:space-between;color:var(--ink-2);font:500 16px var(--display)}
.field label output{color:var(--ink);font:500 16px var(--mono)}
input[type=range]{width:100%;height:28px;margin:0;background:none;-webkit-appearance:none;appearance:none;cursor:pointer}
input[type=range]::-webkit-slider-runnable-track{height:6px;border-radius:3px;background:linear-gradient(90deg,var(--gold) var(--fill,50%),#ffffff14 var(--fill,50%))}
input[type=range]::-webkit-slider-thumb{width:24px;height:24px;margin-top:-9px;border:0;border-radius:50%;background:var(--ink);box-shadow:0 0 0 6px #e4ba6233;-webkit-appearance:none}
input[type=range]::-moz-range-track{height:6px;border-radius:3px;background:#ffffff14}
input[type=range]::-moz-range-progress{height:6px;border-radius:3px;background:var(--gold)}
input[type=range]::-moz-range-thumb{width:24px;height:24px;border:0;border-radius:50%;background:var(--ink)}
input[type=range]:focus-visible{outline:2px solid var(--gold);outline-offset:4px;border-radius:4px}
.result{display:grid;gap:26px}
.result div{display:grid;gap:4px}
.result small{color:var(--ink-3);font:500 12px var(--mono);letter-spacing:.08em;text-transform:uppercase}
.result b{font:650 clamp(40px,4.4vw,60px)/1 var(--display);letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.result .risk b{color:var(--red)}.result .ratio b{color:var(--gold)}

/* Request */
.ask{list-style:none;margin:0;padding:0;counter-reset:ask;display:grid;gap:0}
.ask li{counter-increment:ask;display:grid;grid-template-columns:64px 1fr;gap:16px;padding:30px 0;border-bottom:1px solid var(--line)}
.ask li::before{content:"0" counter(ask);color:var(--gold);font:500 14px var(--mono);padding-top:6px}
.ask b{display:block;font:600 22px var(--display)}
.ask p{margin:6px 0 0;color:var(--ink-2)}

/* Footer */
.foot{border-top:1px solid var(--line);padding-block:64px 48px}
.foot .wrap{display:grid;grid-template-columns:1.4fr repeat(3,1fr);gap:40px}
.foot p{margin:16px 0 0;max-width:300px;color:var(--ink-3);font-size:16px}
.foot h4{margin:0 0 16px;color:var(--ink-3);font:500 11px var(--mono);letter-spacing:.12em;text-transform:uppercase}
.foot a{display:block;margin-bottom:10px;color:var(--ink-2);font:400 15px var(--display);text-decoration:none}
.foot a:hover{color:var(--gold)}

:focus-visible{outline:2px solid var(--gold);outline-offset:3px}
@media (max-width:900px){
  .hero .wrap,.split,.story,.vtabs,.anatomy,.calc,.grid-2{grid-template-columns:1fr}
  .grid-3{grid-template-columns:1fr}.grid-4{grid-template-columns:1fr 1fr}
  .story-stage{position:sticky;top:84px;height:320px;z-index:2;order:-1;background:var(--bg)}
  .cert-wrap{position:static;order:-1}
  .story-steps li,.anatomy-steps li{min-height:46vh}
  .cmp-row{grid-template-columns:1fr 90px;gap:10px 16px}.cmp-row span{grid-column:1/-1}
  .rows>div{grid-template-columns:1fr;gap:8px}.rows .hdr{display:none}
  .foot .wrap{grid-template-columns:1fr 1fr}
  .nav-links{position:absolute;top:76px;left:0;right:0;display:none;flex-direction:column;gap:0;padding:12px 24px 24px;background:var(--bg);border-bottom:1px solid var(--line)}
  .nav-links.open{display:flex}.nav-links a{padding:14px 0}
  .menu{display:grid;place-items:center}
  .nav .btn{display:none}
  .vpanel{min-height:0}
}
@media (max-width:560px){.grid-4{grid-template-columns:1fr}
  .wrap{padding-left:max(18px,env(safe-area-inset-left,0px));padding-right:max(18px,env(safe-area-inset-right,0px))}
  .console-body{min-height:330px;padding:20px;font-size:12.5px}
  .story-stage{height:290px}.stage{padding:20px}.stage-label{display:none}.vault{padding:22px 18px 16px}.vault span:nth-child(n+3){display:none}.seal-hash{margin-top:14px;font-size:11px}.atom i{width:calc(var(--d)*.7);height:calc(var(--d)*.7)}.measure-rows{gap:16px}.price-tag b{font-size:26px}
  .atom b{font-size:15px}
  .vtab{padding:14px 16px}.vtab span{font-size:19px}
  .cmp-switch{display:flex;flex-wrap:wrap;border-radius:18px}
  .foot .wrap{grid-template-columns:1fr}
}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}.js [data-reveal]{opacity:1;transform:none}.atom i,.track i{transform:none}}
"""

SCRIPT = r"""
(() => {
  const root = document.documentElement;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const gsap = window.gsap, Motion = window.Motion;
  const spring = {type: 'spring', stiffness: 220, damping: 24};
  const $ = (s, el = document) => el.querySelector(s), $$ = (s, el = document) => [...el.querySelectorAll(s)];

  // Nav
  const nav = $('.nav');
  addEventListener('scroll', () => nav.classList.toggle('scrolled', scrollY > 8), {passive: true});
  $('.menu')?.addEventListener('click', e => {
    const open = $('.nav-links').classList.toggle('open');
    e.currentTarget.setAttribute('aria-expanded', String(open));
  });

  // Count-up for [data-count]: animates the first number in the text, keeps prefix and suffix.
  const countUp = el => {
    const m = el.textContent.match(/^(\D*?)([\d,.]+)(.*)$/);
    if (!m || reduced) return;
    const [, pre, num, post] = m, target = parseFloat(num.replace(/,/g, '')), dec = (num.split('.')[1] || '').length;
    const t0 = performance.now();
    const tick = t => {
      const k = Math.min(1, (t - t0) / 1400), v = target * (1 - Math.pow(1 - k, 4));
      el.textContent = pre + v.toLocaleString('en-US', {minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: num.includes(',')}) + post;
      if (k < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  // Reveals: content is only hidden once JS runs, and is revealed the moment it reaches the screen.
  const io = new IntersectionObserver(entries => entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    io.unobserve(entry.target);
    entry.target.classList.add('in');
    $$('[data-count]', entry.target).forEach(countUp);
    if (entry.target.matches('[data-count]')) countUp(entry.target);
    if (entry.target.matches('[data-split]') && gsap && window.SplitText && !reduced) {
      const split = SplitText.create(entry.target, {type: 'lines', mask: 'lines', linesClass: 'split-line'});
      gsap.from(split.lines, {yPercent: 105, duration: 1.1, ease: 'expo.out', stagger: .09});
    }
  }), {rootMargin: '0px 0px -10% 0px'});
  $$('[data-reveal], [data-split], [data-watch]').forEach(el => io.observe(el));
  setTimeout(() => $$('[data-reveal]').forEach(el => el.classList.add('in')), 4000);

  // Sticky scroll stories: the step nearest the middle of the screen is active.
  const story = (stepsSel, onStep) => {
    const steps = $$(stepsSel);
    if (!steps.length) return;
    let current = -1, queued = false;
    const sync = () => {
      queued = false;
      const mid = innerHeight * .55;
      let best = 0;
      steps.forEach((s, i) => { if (s.getBoundingClientRect().top < mid) best = i; });
      if (best !== current) { current = best; steps.forEach((s, i) => s.classList.toggle('on', i === best)); onStep(best); }
    };
    addEventListener('scroll', () => { if (!queued) { queued = true; requestAnimationFrame(sync); } }, {passive: true});
    sync();
  };

  // Home: how it works, with a distinct animation per stage.
  const stages = $$('.stage');
  const playStage = i => {
    stages.forEach((s, j) => s.classList.toggle('on', i === j));
    const s = stages[i];
    if (!s || !gsap || reduced) return;
    if (s.dataset.kind === 'seal') {
      gsap.fromTo($$('.vault span', s), {x: -80, opacity: 0}, {x: 0, opacity: 1, duration: .6, stagger: .1, ease: 'back.out(1.7)'});
      gsap.fromTo($('.seal-hash', s), {clipPath: 'inset(0 100% 0 0)'}, {clipPath: 'inset(0 0% 0 0)', duration: 1, delay: .5, ease: 'steps(28)'});
    } else if (s.dataset.kind === 'train') {
      $$('.atom', s).forEach(a => a.classList.remove('float'));
      gsap.fromTo($$('.atom i', s), {scale: 0}, {scale: 1, duration: 1.1, stagger: .18, ease: 'elastic.out(1, .5)',
        onComplete: () => $$('.atom', s).forEach(a => a.classList.add('float'))});
    } else if (s.dataset.kind === 'price') {
      gsap.fromTo($$('.price-vis path', s), {strokeDashoffset: 400, strokeDasharray: 400}, {strokeDashoffset: 0, duration: 1.2, ease: 'power2.out'});
      gsap.fromTo($('.price-tag', s), {scale: .6, opacity: 0, rotate: -6}, {scale: 1, opacity: 1, rotate: 0, delay: .8, duration: .7, ease: 'back.out(2)'});
    }
  };
  if (stages.length) story('.story-steps li', playStage);
  $$('.story-steps li').forEach((li, i) => li.addEventListener('click', () => li.scrollIntoView({behavior: 'smooth', block: 'center'})));

  // Home: console replays two illustrative runs.
  const runs = $$('.run');
  if (runs.length && gsap && !reduced) {
    const play = i => {
      runs.forEach((r, j) => r.classList.toggle('on', i === j));
      const parts = $$('[data-l]', runs[i]);
      const tl = gsap.timeline({onComplete: () => gsap.delayedCall(2.8, () => play((i + 1) % runs.length))});
      tl.set(parts, {opacity: 0, y: 6}).set($$('.bars i', runs[i]), {scaleX: 0});
      parts.forEach((p, k) => {
        tl.to(p, {opacity: 1, y: 0, duration: .3}, k ? '+=.35' : .3);
        if (p.classList.contains('bars')) tl.to($$('i', p), {scaleX: 1, duration: .8, stagger: .12, ease: 'power2.out'});
      });
      tl.fromTo($('.verdict', runs[i]), {scale: 1.6, rotate: -10}, {scale: 1, rotate: -2, duration: .5, ease: 'back.out(2.4)'}, '-=.2');
    };
    play(0);
  }

  // Tabs: vertical list on home, any [data-tabs] group.
  $$('[data-tabs]').forEach(group => {
    const tabs = $$('[role=tab]', group);
    const select = tab => tabs.forEach(t => {
      const on = t === tab, panel = document.getElementById(t.getAttribute('aria-controls'));
      t.setAttribute('aria-selected', String(on)); t.tabIndex = on ? 0 : -1; panel.hidden = !on;
      if (on) {
        $$('[data-count]', panel).forEach(countUp);
        if (Motion && !reduced) Motion.animate(panel, {opacity: [0, 1], x: [24, 0]}, spring);
      }
    });
    tabs.forEach(t => t.addEventListener('click', () => select(t)));
    group.addEventListener('keydown', e => {
      const i = tabs.indexOf(document.activeElement);
      const n = {ArrowDown: i + 1, ArrowRight: i + 1, ArrowUp: i - 1, ArrowLeft: i - 1}[e.key];
      if (i < 0 || n === undefined) return;
      e.preventDefault(); const t = tabs[(n + tabs.length) % tabs.length]; select(t); t.focus();
    });
  });

  // Compare: switch measure, bars resize and rows re-order.
  const cmp = $('[data-compare]');
  if (cmp) {
    const btns = $$('.cmp-switch button', cmp), pill = $('.cmp-pill', cmp), box = $('.cmp-rows', cmp), rows = $$('.cmp-row', cmp);
    const notes = {reward: 'Ranked by training reward, Env A looks like the best buy.',
                   transfer: 'Ranked by real improvement, Env B wins by a mile.',
                   value: 'Per dollar, Env B delivers almost 8× what Env A does.'};
    const fmt = {reward: v => v + '%', transfer: v => '+' + v.toFixed(1) + ' pts', value: v => v.toFixed(1) + ' pts'};
    const show = btn => {
      const k = btn.dataset.k;
      btns.forEach(b => b.setAttribute('aria-selected', String(b === btn)));
      pill.style.width = btn.offsetWidth + 'px'; pill.style.transform = `translateX(${btn.offsetLeft - 5}px)`;
      const max = Math.max(...rows.map(r => +r.dataset[k]));
      const before = new Map(rows.map(r => [r, r.getBoundingClientRect().top]));
      rows.sort((a, b) => b.dataset[k] - a.dataset[k]).forEach((r, i) => {
        $('.bar i', r).style.setProperty('--w', (r.dataset[k] / max * 100) + '%');
        $('b', r).textContent = fmt[k](+r.dataset[k]);
        r.classList.toggle('best', i === 0);
        box.append(r);
      });
      if (!reduced) rows.forEach(r => {
        const dy = before.get(r) - r.getBoundingClientRect().top;
        if (dy) r.animate([{transform: `translateY(${dy}px)`}, {transform: 'none'}], {duration: 700, easing: 'cubic-bezier(.7,0,.2,1)'});
      });
      $('.cmp-note', cmp).textContent = notes[k];
    };
    btns.forEach(b => b.addEventListener('click', () => show(b)));
    show(btns[0]);
    addEventListener('resize', () => show(btns.find(b => b.getAttribute('aria-selected') === 'true')));
  }

  // Product: the certificate highlights the row each paragraph is about.
  const certRows = $$('.cert-row');
  if ($('.anatomy-steps')) story('.anatomy-steps li', i => {
    const key = $$('.anatomy-steps li')[i].dataset.key;
    certRows.forEach(r => r.classList.toggle('hl', r.dataset.key === key));
  });

  // Product: switch the sample environment; values count, flags update.
  const envData = $('#env-data');
  if (envData) {
    const envs = JSON.parse(envData.textContent);
    const chips = $$('.chip');
    const fill = (env, animate) => {
      chips.forEach(c => c.setAttribute('aria-pressed', String(c.dataset.id === env.id)));
      $('.cert-name .g').textContent = env.grade;
      $('.cert-name b').textContent = env.name;
      $('.cert-name small').textContent = env.meta;
      certRows.forEach(r => { const b = $('b', r); b.textContent = env[r.dataset.key]; if (animate) countUp(b); });
      $('.flags').innerHTML = '';
      (env.flags.length ? env.flags : ['No appraisal flags']).forEach(f => {
        const li = document.createElement('li'); li.textContent = f; if (!env.flags.length) li.className = 'ok'; $('.flags').append(li);
      });
      if (animate && Motion && !reduced) Motion.animate('.cert', {scale: [.98, 1], opacity: [.6, 1]}, spring);
    };
    chips.forEach(c => c.addEventListener('click', () => fill(envs.find(e => e.id === c.dataset.id), true)));
    fill(envs[0], false);
  }

  // Market and company: a line that fills as you scroll past it.
  const tl = $('.timeline');
  if (tl) addEventListener('scroll', () => {
    const r = tl.getBoundingClientRect();
    tl.style.setProperty('--p', Math.max(0, Math.min(1, (innerHeight * .6 - r.top) / r.height)).toFixed(3));
  }, {passive: true});

  // Pricing: what's at risk on a purchase, against the cost of one appraisal.
  const calc = $('[data-calc]');
  if (calc) {
    const money = v => '$' + Math.round(v).toLocaleString('en-US');
    const update = () => {
      const tasks = +$('#tasks').value, price = +$('#price').value, waste = +$('#waste').value;
      $$('input[type=range]', calc).forEach(i => i.style.setProperty('--fill', ((i.value - i.min) / (i.max - i.min) * 100) + '%'));
      $('#tasks-out').textContent = tasks.toLocaleString('en-US');
      $('#price-out').textContent = money(price);
      $('#waste-out').textContent = waste + '%';
      const spend = tasks * price, risk = spend * waste / 100, cost = Number(calc.dataset.cost);
      $('#spend').textContent = money(spend);
      $('#risk').textContent = money(risk);
      $('#ratio').textContent = cost ? (risk / cost).toFixed(1) + '×' : '—';
    };
    $$('input', calc).forEach(i => i.addEventListener('input', update));
    update();
  }
})();
"""

BRAND = ('<svg viewBox="0 0 42 42" aria-hidden="true"><defs><linearGradient id="ts" x1="0" y1="0" x2="1" y2="1">'
         '<stop stop-color="#8a8d92"/><stop offset=".5" stop-color="#3a3e43"/><stop offset="1" stop-color="#17191b"/></linearGradient></defs>'
         '<path d="M5 13 14 5l13 2 10 10-3 15-12 6L8 32 3 22z" fill="url(#ts)" stroke="#c9ccce" stroke-width="1.2"/>'
         '<path d="m24 8 3 10-4 5 5 3-3 9" fill="none" stroke="#e4ba62" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.4"/></svg>')


def href(prefix: str, page: str) -> str:
    return prefix + ("index.html" if page == "home" else page + "/index.html")


def request_href(prefix: str) -> tuple[str, str]:
    if report.REQUEST_FORM_URL:
        return esc(report.REQUEST_FORM_URL), ' target="_blank" rel="noopener"'
    return href(prefix, "request"), ""


def button(label: str, url: str, extra: str = "", ghost: bool = False, arrow: str = "↗") -> str:
    return f'<a class="btn{" ghost" if ghost else ""}" href="{url}"{extra}>{label}<i aria-hidden="true">{arrow}</i></a>'


def request_button(prefix: str, label: str = "Request an appraisal") -> str:
    url, extra = request_href(prefix)
    return button(label, url, extra)


def shell(page: str, title: str, description: str, body: str, prefix: str) -> str:
    links = "".join(f'<a class="{"on" if key == page else ""}" href="{href(prefix, key)}">{label}</a>' for key, label in NAV)
    url, extra = request_href(prefix)
    libs = "".join(f'<script src="{src}"></script>' for src in LIBRARIES)
    foot_cols = (
        ("Product", (("How it works", "product"), ("Sample report", "appraisals"), ("Forecast check", "forecast"))),
        ("Company", (("Market", "market"), ("Pricing", "pricing"), ("About and roadmap", "company"))),
        ("Get started", (("Request an appraisal", "request"),)),
    )
    foot = "".join(f'<div><h4>{name}</h4>' + "".join(f'<a href="{href(prefix, key)}">{label}</a>' for label, key in items) + "</div>"
                   for name, items in foot_cols)
    return f"""<!doctype html>
<html lang="en" class="js"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="claude:viewport-fit-sides" content="cover">
<title>{esc(title)}</title><meta name="description" content="{esc(description)}"><meta name="theme-color" content="#0b0d10">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}"><style>{CSS}</style></head><body>
<header class="nav"><div class="wrap"><a class="brand" href="{href(prefix, 'home')}" aria-label="Touchstone home">{BRAND}touchstone</a>
<nav class="nav-links" aria-label="Main">{links}</nav><a class="btn small" href="{url}"{extra}>Request an appraisal</a>
<button class="menu" type="button" aria-label="Open menu" aria-expanded="false">☰</button></div></header>
<main>{body}</main>
<footer class="foot"><div class="wrap"><div><a class="brand" href="{href(prefix, 'home')}">{BRAND}touchstone</a>
<p>Independent appraisal for AI training data. We test it before you buy it.</p></div>{foot}</div></footer>
{libs}<script>{SCRIPT}</script></body></html>"""


def cta(prefix: str, title: str = "Know before <em>you train.</em>", lede: str = "Send us the environment you're considering. We'll scope a pilot appraisal with you.") -> str:
    return (f'<section class="cta"><div class="aura" aria-hidden="true"></div><div class="wrap"><p class="eyebrow">Pilot appraisals</p>'
            f'<h2 data-split>{title}</h2><p class="lede">{lede}</p>'
            f'<div class="actions">{request_button(prefix)}{button("See a sample report", href(prefix, "appraisals"), ghost=True)}</div></div></section>')


def stats(items, gold_first: bool = True) -> str:
    cells = "".join(f'<div class="surface stat" data-reveal style="--d:{i * .1:.1f}s"><b data-count>{fig}</b><p>{text}</p>'
                    + (f"<small>{src}</small>" if src else "") + "</div>" for i, (fig, text, src) in enumerate(items))
    return f'<div class="grid-3">{cells}</div>'


def faq(items) -> str:
    return '<div class="faq">' + "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in items) + "</div>"


# ---------------------------------------------------------------- pages

def home(data: dict) -> str:
    p = ""
    ladder = data["ladder"]
    biggest = max(ladder.values())
    atoms = "".join(f'<div class="atom" style="--d:{(v / biggest) ** .5 * 150:.0f}px;--n:{i}"><i></i><b>{esc(k)}</b><small>{fmt_params(v)}</small></div>'
                    for i, (k, v) in enumerate(ladder.items()))
    runs = []
    for i, (name, exploit, overlap, gain, verdict, tone) in enumerate((
            ("coding-agent-v3", "2 exploits found", "31% already free", "−0.4 pts", "Not worth full price", "bad"),
            ("math-reasoning-v1", "no exploits", "6% already free", "+4.1 pts", "Worth buying", "good"))):
        bars = "".join(f'<div><span>{s}</span><i style="width:{w}%"></i></div>' for s, w in (("S", 38), ("M", 56), ("L", 74), ("XL", 92)))
        runs.append(f'<div class="run{" on" if i == 0 else ""}"><p class="ln" data-l><span class="p">›</span>seal <b>{name}</b><span class="r good">sealed</span></p>'
                    f'<p class="ln" data-l><span class="p">›</span>train 4 small models</p><div class="bars" data-l>{bars}</div>'
                    f'<p class="ln" data-l><span class="p">›</span>probe the grader<span class="r {tone}">{exploit}</span></p>'
                    f'<p class="ln" data-l><span class="p">›</span>check overlap<span class="r">{overlap}</span></p>'
                    f'<p class="ln" data-l><span class="p">›</span>forecast at your scale<span class="r {tone}">{gain}</span></p>'
                    f'<span class="verdict {tone}" data-l>{verdict}</span></div>')
    steps = (("01", "Seal", "The vendor uploads the environment to a sealed sandbox. You never see the tasks, only the results."),
             ("02", "Train small", "We train small open models on it at four sizes with one fixed recipe. Cheap, fast and repeatable."),
             ("03", "Measure", "We test the models on private problems they never trained on, and try to fool the grader."),
             ("04", "Forecast and price", "We predict the gain at your model size and put a fair price on each task."))
    step_html = "".join(f'<li class="{"on" if i == 0 else ""}"><article><span class="n">{n}</span><h3>{t}</h3><p>{x}</p></article></li>'
                        for i, (n, t, x) in enumerate(steps))
    stage_html = (
        '<div class="stage on" data-kind="seal"><span class="stage-label">01 · Seal</span><div><div class="vault">'
        + "".join(f"<span>task {n:03d}</span>" for n in range(1, 5)) + '</div><p class="seal-hash">sealed · sha256 7f3a9c04e1b2</p></div></div>'
        f'<div class="stage" data-kind="train"><span class="stage-label">02 · Four model sizes, to scale</span><div class="atoms">{atoms}</div></div>'
        '<div class="stage" data-kind="measure"><span class="stage-label">03 · Measure</span><div class="measure-rows">'
        '<div><span>Better on new problems</span><b>+4.1 pts</b><div class="track"><i style="--w:68%"></i></div></div>'
        '<div><span>Reward won by exploits</span><b>0%</b><div class="track"><i style="--w:2%;--c:var(--red);--d:.15s"></i></div></div>'
        '<div><span>Already in free data</span><b>6%</b><div class="track"><i style="--w:6%;--c:var(--blue);--d:.3s"></i></div></div></div></div>'
        '<div class="stage" data-kind="price"><span class="stage-label">04 · Forecast and price</span><div class="price-vis">'
        '<svg viewBox="0 0 400 170" aria-hidden="true"><polygon class="band" points="250,82 380,30 380,86 250,104"/>'
        '<path class="fit" d="M40 132 L130 116 L250 94"/><path class="fc" d="M250 94 L380 58"/>'
        '<circle cx="40" cy="132" r="6"/><circle cx="130" cy="116" r="6"/><circle cx="250" cy="94" r="6"/><circle class="target" cx="380" cy="58" r="9"/>'
        '<text x="40" y="160">small</text><text x="350" y="160">your size</text></svg>'
        '<span class="price-tag"><b>$640</b><span>fair value per task</span></span></div></div>')
    measures = (("Transfer", "+4.1 pts", "Does it make your model better at problems it has never seen? The number that matters."),
                ("Reward exploits", "2 found", "Can a model win reward without solving the task? If so, it learns the trick, not the skill."),
                ("Redundancy", "31%", "How much of it you could already get for free, or already own."),
                ("Forecast", "+6.0 pts", "The gain you should expect at your own model size, with an uncertainty range."),
                ("Fair value", "$640", "What each task is actually worth to you, compared with its price."))
    tablist = "".join(f'<button class="vtab" role="tab" id="m-t{i}" aria-controls="m-p{i}" aria-selected="{"true" if i == 0 else "false"}" tabindex="{0 if i == 0 else -1}">'
                      f'<small>0{i + 1}</small><span>{name}</span></button>' for i, (name, _, _) in enumerate(measures))
    panels = "".join(f'<div class="vpanel surface" role="tabpanel" id="m-p{i}" aria-labelledby="m-t{i}"{"" if i == 0 else " hidden"}>'
                     f'<span class="big" data-count>{fig}</span><p>{text}</p><small>Illustrative example</small></div>' for i, (_, fig, text) in enumerate(measures))
    envs = (("Env A · coding agent", 92, 2.0, .4), ("Env B · math reasoning", 81, 9.1, 3.1), ("Env C · web browsing", 75, 6.2, 1.8), ("Env D · tool use", 70, 4.0, 1.1))
    cmp_rows = "".join(f'<div class="cmp-row" data-reward="{r}" data-transfer="{t}" data-value="{v}"><span>{n}</span><div class="bar"><i></i></div><b></b></div>' for n, r, t, v in envs)
    marquee = "".join(f"<span>{q}</span><i>✦</i>" for q in ("Does it teach?", "Can it be gamed?", "Is it new?", "Will it scale?", "What is it worth?") * 4)
    tiles = "".join(f'<a class="surface tile" href="{href(p, key)}" data-reveal style="--d:{i * .08:.2f}s"><span class="eyebrow">{eb}</span><h3>{t}</h3><p>{x}</p><span class="arrow">Read more →</span></a>'
                    for i, (key, eb, t, x) in enumerate((
                        ("product", "Product", "Inside a report", "Every measurement, on a live sample."),
                        ("market", "Market", "Why now", "The spend, the gap and who else is here."),
                        ("pricing", "Pricing", "What it costs", "And what a bad purchase costs you."),
                        ("company", "Company", "Where we're going", "Roadmap, research and FAQ."))))
    body = f"""<section class="hero"><div class="aura" aria-hidden="true"></div><div class="wrap"><div>
<p class="eyebrow" data-reveal>Independent appraisal for AI training data</p>
<h1 data-split>Don't buy training data <em>blind.</em></h1>
<p class="lede" data-reveal style="--d:.15s">Touchstone tests an RL environment or dataset on small models before you pay, and tells you whether it will make your model better.</p>
<div class="actions" data-reveal style="--d:.25s">{request_button(p)}{button("See a sample report", href(p, "appraisals"), ghost=True)}</div>
<div class="hero-meta" data-reveal style="--d:.35s"><span>Sealed sandbox</span><span>Small-model experiments</span><span>Independent</span></div></div>
<div class="console" data-reveal style="--d:.2s" aria-label="An illustrative appraisal run"><div class="console-bar"><b></b><b></b><b></b><span>touchstone · appraisal</span><em>illustrative</em></div>
<div class="console-body">{"".join(runs)}</div></div></div></section>
<div class="marquee" aria-hidden="true"><div class="marquee-track">{marquee}</div></div>
<section class="sec"><div class="wrap"><div class="head"><p class="eyebrow">The problem</p><h2 data-split>Training data is expensive. <em>Finding out it didn't work is worse.</em></h2></div>
{stats([("$2,000", "The top price for a single RL environment task.", "Price summaries citing Epoch AI"),
        ("100%", "Reward a model won in our demo, with answers that solved nothing.", "Touchstone demo run"),
        ("Weeks", "Of GPU time before a full training run tells you the data didn't help.", "")])}</div></section>
<section class="sec tight"><div class="wrap"><div class="head"><p class="eyebrow">How it works</p><h2 data-split>Small experiments, <em>before the big spend.</em></h2></div>
<div class="story"><ol class="story-steps">{step_html}</ol><div class="story-stage">{stage_html}</div></div></div></section>
<section class="sec"><div class="wrap"><div class="head"><p class="eyebrow">What you get</p><h2 data-split>One report. <em>Five answers.</em></h2></div>
<div class="vtabs" data-tabs><div class="vtab-list" role="tablist" aria-label="Report measures" aria-orientation="vertical">{tablist}</div><div>{panels}</div></div></div></section>
<section class="sec tight"><div class="wrap"><div class="head"><p class="eyebrow">Compare environments · coming in the MVP</p><h2 data-split>The highest reward <em>isn't the best buy.</em></h2>
<p class="lede">Switch what you rank by and watch the order flip. Illustrative numbers.</p></div>
<div data-compare><div class="cmp-switch" role="tablist"><span class="cmp-pill" aria-hidden="true"></span>
<button role="tab" data-k="reward" aria-selected="true">Training reward</button><button role="tab" data-k="transfer" aria-selected="false">Real improvement</button><button role="tab" data-k="value" aria-selected="false">Value per $1k</button></div>
<div class="cmp-rows">{cmp_rows}</div><p class="cmp-note"></p></div></div></section>
<section class="sec tight"><div class="wrap"><div class="grid-2">
<div class="surface" data-reveal><p class="eyebrow">For AI teams buying data</p><h3>Check it before you sign.</h3><ul class="points"><li>Test an environment before you pay for it</li><li>Compare vendors on one private test</li><li>Stop paying for tasks your model can game</li></ul></div>
<div class="surface" data-reveal style="--d:.1s"><p class="eyebrow">For vendors selling it</p><h3>Prove it with a neutral number.</h3><ul class="points"><li>A rating buyers trust more than your own results</li><li>Find grader exploits before customers do</li><li>Back your price with measured value</li></ul></div></div></div></section>
<section class="sec tight"><div class="wrap"><div class="grid-4">{tiles}</div></div></section>
{cta(p)}"""
    return shell("home", "Touchstone", "Touchstone tests RL environments and training data on small models before you buy, so you know whether they will make your model better.", body, p)


def product(data: dict, ranked: list[dict], base: dict) -> str:
    p = "../"
    truth = data["truth_rung"]
    envs = []
    for env in ranked + [base]:
        top = env["rungs"][truth]
        envs.append({"id": env["id"], "name": env["name"], "grade": env["grade"],
                     "meta": f'{env["redundancy"]["n_tasks"]:,} tasks · sealed {env["sha256"][:10]} · demo data',
                     "learn": f'{top["env_reward_before"]:.0%} → {top["env_reward_after"]:.0%}',
                     "transfer": f'{pts(env["actual_at_truth"])} pts', "hack": f'{env["hackability"]["score"]:.0%}',
                     "overlap": f'{env["redundancy"]["public_overlap"]:.0%}', "forecast": f'{pts(env["forecast"]["forecast"])} pts',
                     "value": f'${env["fair_value_per_task"]:,.0f}', "flags": env["flags"]})
    rows = (("learn", "Learns the environment"), ("transfer", "Better on new problems"), ("hack", "Reward won by shortcuts"),
            ("overlap", "Already in free data"), ("forecast", "Forecast at the largest size"), ("value", "Fair value per task"))
    explain = (("learn", "Learnability", "First, does the model get better at the environment's own tasks? If not, nothing else matters."),
               ("transfer", "Transfer", "Then the question that decides everything: does that improvement show up on problems the model never trained on?"),
               ("hack", "Reward exploits", "We feed the grader answers that should score zero. If they score, the environment teaches tricks, not skills."),
               ("overlap", "Redundancy", "How much of it already exists in free public data. You shouldn't pay for what you have."),
               ("forecast", "Forecast", "We fit how the gain grows with model size and project it to yours, with an uncertainty range."),
               ("value", "Fair value", "Finally, a price per task based on the real gain, compared with free alternatives."))
    env_json = json.dumps(envs).replace("</", "<\\/")
    chips = "".join(f'<button class="chip" type="button" data-id="{e["id"]}" aria-pressed="{"true" if i == 0 else "false"}">{esc(e["name"])}</button>' for i, e in enumerate(envs))
    cert_rows = "".join(f'<div class="cert-row" data-key="{k}"><span>{label}</span><b></b></div>' for k, label in rows)
    steps = "".join(f'<li data-key="{k}" class="{"on" if i == 0 else ""}"><article><span class="eyebrow">{i + 1:02d}</span><h3>{t}</h3><p>{x}</p></article></li>'
                    for i, (k, t, x) in enumerate(explain))
    body = f"""<section class="hero"><div class="aura" aria-hidden="true"></div><div class="wrap" style="grid-template-columns:1fr"><div>
<p class="eyebrow" data-reveal>Product</p><h1 data-split>One sealed test. <em>Six answers.</em></h1>
<p class="lede" data-reveal>Every appraisal produces one certificate. Scroll through it below, then try it on the six sample environments from our demo run.</p></div></div></section>
<section class="sec tight"><div class="wrap"><div class="anatomy"><ol class="anatomy-steps">{steps}</ol>
<div class="cert-wrap"><div class="chips" role="group" aria-label="Sample environment">{chips}</div>
<div class="cert"><div class="cert-top"><span>Appraisal certificate</span><em>Sample · demo data</em></div>
<div class="cert-name"><span class="g"></span><div><b></b><small></small></div></div>{cert_rows}<ul class="flags"></ul></div></div></div></div></section>
<section class="sec"><div class="wrap"><div class="head"><p class="eyebrow">The process</p><h2 data-split>From upload <em>to verdict.</em></h2></div>
<div class="grid-3">{"".join(f'<div class="surface" data-reveal style="--d:{i * .1:.1f}s"><span class="eyebrow">{n}</span><h3>{t}</h3><p class="muted">{x}</p></div>' for i, (n, t, x) in enumerate((
    ("Step 1", "Sealed intake", "The seller uploads tasks, tools and grader. They are fingerprinted and never leave the sandbox."),
    ("Step 2", "Standard training", "A fixed family of small open models, one published recipe, two or three data sizes."),
    ("Step 3", "Report", "Six measurements, a forecast at your scale, a fair price and an optional public rating."))))}</div></div></section>
<section class="sec tight"><div class="wrap"><div class="head"><p class="eyebrow">Questions</p><h2 data-split>The technical <em>details.</em></h2></div>
{faq((("Which models do you train?", "A fixed family of small open models, for example 0.5B, 1.5B and 3B parameters, all with one published RL recipe."),
      ("How do you test transfer?", "On a private held-out suite that no vendor ever sees or trains on. That suite is what keeps the result honest."),
      ("How do you find reward exploits?", "Known exploit probes (empty answers, format gaming, editing tests) plus adversarial policies trained against the grader."),
      ("How good is the forecast?", "Every report shows how well small-model forecasts held up on the largest model. Our demo run is honest about where it didn't.")))}
<p class="note"><a class="link" href="{href(p, 'forecast')}">See the forecast check →</a></p></div></section>
<script type="application/json" id="env-data">{env_json}</script>
{cta(p)}"""
    return shell("product", "Product · Touchstone", "What a Touchstone appraisal measures, on six sample environments.", body, p)


def market(data: dict) -> str:
    p = "../"
    players = (("Scale AI", 30, 18, "Sells training data and infrastructure.", "Grades its own product."),
               ("Patronus AI", 20, 74, "Evaluates and tests AI models.", "Tests finished models, not the data that trains them."),
               ("In-house ML teams", 76, 44, "Run their own training experiments.", "Only after buying, at full cost."),
               ("Touchstone", 84, 86, "Independently values training resources.", "Before you buy, at small-model cost."))
    dots = "".join(f'<div class="dot{" us" if n == "Touchstone" else ""}{" left" if x > 60 else ""}" style="--x:{x}%;--y:{y}%;--d:{i * .15:.2f}s"><i></i><span>{n}</span></div>'
                   for i, (n, x, y, _, _) in enumerate(players))
    rows = "".join(f'<div class="{"us" if n == "Touchstone" else ""}" data-reveal><b>{n}</b><p>{what}</p><p>{gap}</p></div>' for n, _, _, what, gap in players)
    moat = "".join(f'<div class="surface" data-reveal style="--d:{i * .08:.2f}s"><h3>{t}</h3><p class="muted">{x}</p></div>' for i, (t, x) in enumerate((
        ("Neutral by design", "We never sell data or environments, and we publish our method."),
        ("A private test suite", "No vendor can train on it. It becomes more valuable the longer it stays clean."),
        ("Every appraisal teaches us", "Each run sharpens which environment features actually transfer."),
        ("The first standard sticks", "In ratings and audits, the first credible standard tends to win."))))
    body = f"""<section class="hero"><div class="aura" aria-hidden="true"></div><div class="wrap" style="grid-template-columns:1fr"><div>
<p class="eyebrow" data-reveal>Market</p><h1 data-split>Training data is the new <em>compute bill.</em></h1>
<p class="lede" data-reveal>AI companies are spending more on specialized data, RL and agent environments every year, with no neutral way to check what they are buying.</p></div></div></section>
<section class="sec tight"><div class="wrap"><div class="head"><p class="eyebrow">Why now</p><h2 data-split>The money is moving <em>to training data.</em></h2></div>
{stats([("$1B", "A year, reported spend on human-curated data by each leading lab.", "TechCrunch and market maps"),
        ("55%", "Share of AI cloud spend going to inference in 2026, driven by fine-tuned models in production.", "Gartner forecast"),
        ("0", "Independent auditors of training value in current market maps.", "Market maps of the data ecosystem")])}</div></section>
<section class="sec"><div class="wrap split"><div data-watch><p class="eyebrow">The opportunity</p><div class="bigfig">$30M–$100M+</div>
<p class="lede">If environment and post-training data spend reaches a few billion dollars a year by 2027–28, a verification layer taking 1–3% is a $30M–$100M+ business, before any marketplace.</p>
<div class="spend" data-reveal><div class="spend-bar"><i></i></div><div class="spend-labels"><b>Touchstone · 1–3%</b><span>Data and environment spend</span></div></div><p class="note">Our estimate.</p></div>
<div><div class="map" data-watch><span class="ax y">Independent ↑</span><span class="ax x">Measures training value →</span>{dots}</div></div></div></section>
<section class="sec tight"><div class="wrap"><div class="head"><p class="eyebrow">Competition</p><h2 data-split>Close neighbours. <em>Different job.</em></h2></div>
<div class="rows"><div class="hdr"><span>Who</span><span>What they do</span><span>Why it isn't this</span></div>{rows}</div></div></section>
<section class="sec"><div class="wrap"><div class="head"><p class="eyebrow">Why it compounds</p><h2 data-split>A moat that grows <em>with every report.</em></h2></div><div class="grid-2">{moat}</div></div></section>
<section class="sec tight"><div class="wrap"><div class="head"><p class="eyebrow">The science</p><h2 data-split>Small runs <em>predict big ones.</em></h2></div>
<div class="grid-2"><a class="surface tile" href="https://proceedings.mlr.press/v235/xia24c.html" target="_blank" rel="noopener" data-reveal><span class="stat gold"><b>5%</b></span><p>Training on a well-chosen 5% of data can beat training on all of it.</p><span class="arrow">Xia et al., LESS · ICML 2024 ↗</span></a>
<a class="surface tile" href="https://proceedings.mlr.press/v267/magnusson25a.html" target="_blank" rel="noopener" data-reveal style="--d:.1s"><span class="stat"><b>Small → large</b></span><p>Small, cheap experiments predict which data wins at larger scale.</p><span class="arrow">Magnusson et al., DataDecide · ICML 2025 ↗</span></a></div>
<p class="note">Further reading: <a class="link" href="https://scale.com/blog/rl-environments" target="_blank" rel="noopener">Scale AI on RL environments ↗</a></p></div></section>
{cta(p, "A verification layer <em>for a new market.</em>", "Talk to us about a pilot, or about the market.")}"""
    return shell("market", "Market · Touchstone", "Why now, the opportunity, and how Touchstone differs from Scale AI, Patronus AI and in-house teams.", body, p)


def pricing() -> str:
    p = "../"
    body = f"""<section class="hero"><div class="aura" aria-hidden="true"></div><div class="wrap" style="grid-template-columns:1fr"><div>
<p class="eyebrow" data-reveal>Pricing</p><h1 data-split>Costs less than <em>one bad run.</em></h1>
<p class="lede" data-reveal>Pay per appraisal when you're evaluating a purchase, or subscribe to test every environment you train on.</p></div></div></section>
<section class="sec tight"><div class="wrap"><div class="grid-2">
<div class="surface plan" data-reveal><p class="eyebrow">Per appraisal</p><h3>Check one environment</h3><div class="price">$10k–$50k <small>per appraisal</small></div>
<ul class="points"><li>Sealed test of one environment</li><li>Full six-part report</li><li>Forecast and fair value per task</li></ul>{request_button(p)}</div>
<div class="surface plan feature" data-reveal style="--d:.1s"><p class="eyebrow">Subscription</p><h3>Every environment, always</h3><div class="price">$50k–$250k <small>per year</small></div>
<ul class="points"><li>Side-by-side comparison of environments</li><li>Re-tests as environments change</li><li>Vendor ratings over time</li></ul>{request_button(p, "Talk to us")}</div></div>
<p class="note">Planned pilot pricing. Each appraisal uses roughly $1k–$5k of small-model compute.</p></div></section>
<section class="sec"><div class="wrap"><div class="head"><p class="eyebrow">Is it worth it?</p><h2 data-split>What's at stake <em>on your purchase.</em></h2>
<p class="lede">Move the sliders to match a purchase you're considering. Illustrative, using a $25k appraisal.</p></div>
<div class="calc surface" data-calc data-cost="25000"><div>
<div class="field"><label for="tasks">Tasks you're buying <output id="tasks-out"></output></label><input id="tasks" type="range" min="100" max="20000" step="100" value="5000"></div>
<div class="field"><label for="price">Price per task <output id="price-out"></output></label><input id="price" type="range" min="200" max="2000" step="50" value="800"></div>
<div class="field"><label for="waste">Share that won't help your model <output id="waste-out"></output></label><input id="waste" type="range" min="0" max="80" step="5" value="30"></div></div>
<div class="result" aria-live="polite"><div><small>Total spend</small><b id="spend"></b></div><div class="risk"><small>Money at risk</small><b id="risk"></b></div>
<div class="ratio"><small>At risk, per dollar of appraisal</small><b id="ratio"></b></div></div></div></div></section>
<section class="sec tight"><div class="wrap">{faq((("Who pays, the buyer or the vendor?", "Either. Buyers appraise before purchase; vendors commission a neutral rating to win contracts."),
      ("Why does an appraisal cost this much?", "It includes compute, the private test suite and a full report. It's still a small fraction of a single purchase."),
      ("Can we pilot first?", "Yes. Pilot appraisals are how we're starting.")))}</div></section>
{cta(p)}"""
    return shell("pricing", "Pricing · Touchstone", "Per-appraisal and subscription pricing, and a calculator for what's at risk on a purchase.", body, p)


def company() -> str:
    p = "../"
    road = "".join(f'<li class="{stage.lower()}" data-reveal><em>{esc(stage)}</em><h3>{esc(title)}</h3><p>{esc(text)}</p></li>' for stage, title, text in ROADMAP)
    team = ""
    if FOUNDERS:
        people = "".join(f'<div class="surface" data-reveal><h3>{esc(n)}</h3><p class="eyebrow">{esc(r)}</p><p class="muted">{esc(w)}</p>'
                         + (f'<a class="link" href="{esc(l)}" target="_blank" rel="noopener">Profile ↗</a>' if l else "") + "</div>"
                         for n, r, w, l in FOUNDERS)
        team = f'<section class="sec tight"><div class="wrap"><div class="head"><p class="eyebrow">Team</p><h2 data-split>Who is <em>building this.</em></h2></div><div class="grid-3">{people}</div></div></section>'
    body = f"""<section class="hero"><div class="aura" aria-hidden="true"></div><div class="wrap" style="grid-template-columns:1fr"><div>
<p class="eyebrow" data-reveal>Company</p><h1 data-split>Less wasted training. <em>More real learning.</em></h1>
<p class="lede" data-reveal>Our goal is to help AI companies spend less on ineffective training and get more useful learning from their compute. We're starting with RL environments, and will support training decisions across every type of AI model.</p></div></div></section>
{team}<section class="sec tight"><div class="wrap split" style="align-items:start"><div><p class="eyebrow">Roadmap</p><h2 data-split>Where we are, <em>where we're going.</em></h2>
<p class="lede">We'll keep this page current as pilots start.</p></div><ol class="timeline">{road}</ol></div></section>
<section class="sec"><div class="wrap"><div class="head"><p class="eyebrow">Also exploring</p><h2 data-split>Where this <em>could lead.</em></h2></div>
<div class="grid-2"><div class="surface" data-reveal><h3>Forecasting behaviour before deployment</h3><p class="muted">The same small-to-large method, applied to predicting how a model will behave before it ships.</p></div>
<div class="surface" data-reveal style="--d:.1s"><h3>Accessible ML infrastructure</h3><p class="muted">Making it possible for anyone to practice and experiment with machine learning.</p></div></div></div></section>
<section class="sec tight"><div class="wrap"><div class="head"><p class="eyebrow">Questions</p><h2 data-split>Fair questions, <em>short answers.</em></h2></div>
{faq((("Do you ever see the vendor's tasks?", "They stay in a sealed sandbox. Buyers get results, never the tasks."),
      ("Why trust small models?", "Published research shows small runs predict which data wins at scale. Every report also shows how well our forecast held up."),
      ("What can you test today?", "RL environments with automatic graders. Post-training datasets and other data types come next."),
      ("Are you independent?", "Yes. We never sell data or environments, and we publish our method.")))}</div></section>
{cta(p)}"""
    return shell("company", "Company · Touchstone", "Touchstone's mission, roadmap and FAQ.", body, p)


def request() -> str:
    p = "../"
    action = (request_button(p, "Open the request form") if report.REQUEST_FORM_URL
              else '<p class="note">The request form opens shortly. Check back here for the link.</p>')
    body = f"""<section class="hero"><div class="aura" aria-hidden="true"></div><div class="wrap" style="grid-template-columns:1fr"><div>
<p class="eyebrow" data-reveal>Request an appraisal</p><h1 data-split>Tell us what you're <em>about to buy.</em></h1>
<p class="lede" data-reveal>We're running a small number of pilot appraisals. Here's what helps us scope one.</p></div></div></section>
<section class="sec tight"><div class="wrap split" style="align-items:start"><ol class="ask">
<li data-reveal><div><b>The environment or dataset</b><p>What it trains, how big it is and who sells it.</p></div></li>
<li data-reveal><div><b>The decision</b><p>What you'd pay, and what you need to know before you do.</p></div></li>
<li data-reveal><div><b>Your model</b><p>Rough size and what you're training it to do, so we forecast at your scale.</p></div></li></ol>
<div class="surface" data-reveal><h3>Pilot appraisals</h3><p class="muted">For AI teams buying RL environments or post-training data, and for vendors who want a neutral rating.</p>{action}</div></div></section>"""
    return shell("request", "Request an appraisal · Touchstone", "Request a pilot appraisal of an RL environment or training dataset.", body, p)


def build(data: dict) -> dict[str, str]:
    pages = report.render_site(data)
    pages.pop("methodology/index.html", None)
    environments = data["environments"]
    base = next(env for env in environments if env["is_public_baseline"])
    ranked = sorted((env for env in environments if not env["is_public_baseline"]),
                    key=lambda env: ("ABCDF".index(env["grade"]), -env["lift_over_free"]))
    pages.update({
        "index.html": home(data),
        "product/index.html": product(data, ranked, base),
        "market/index.html": market(data),
        "pricing/index.html": pricing(),
        "company/index.html": company(),
        "request/index.html": request(),
    })
    return pages


def write(data_path: Path, destination: Path) -> None:
    data = json.loads(data_path.read_text())
    for relative, document in build(data).items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document)
        print(f"wrote {target}")


if __name__ == "__main__":
    write(Path(sys.argv[1]), Path(sys.argv[2]))
