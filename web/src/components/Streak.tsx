/* The name made literal. A touchstone is the dark stone merchants rubbed metal on before they paid: the streak shows what
   the metal is worth. Scrolling rubs two streaks across the stone, in the site's own colours: silver is the reward a seller
   shows you and it breaks up, gold is what carries over to new problems and it holds. Drawn in SVG, driven by scroll. */
import { useRef } from 'react'
import { motion, useScroll, useTransform, type MotionValue } from 'motion/react'
import { reduced } from '../ui'

const LINES = [
  'A touchstone is the dark stone merchants used to test gold before they bought it.',
  'Rub the metal across the stone, read the streak, and you know what it\'s worth.',
  'We do the same for training material.',
]

/* A rubbed mark as fine parallel strokes along a shallow curve. Fixed geometry keeps scrubbing cheap, since only a clip
   rectangle moves. The silver strokes are broken up with long gaps; the gold ones run nearly the full length. */
type Stroke = { d: string; w: number; o: number; dash?: string }
function rubbed(seed: number, y0: number, y1: number, count: number, spread: number, broken: boolean) {
  let n = seed
  const r = () => (n = (n * 16807) % 2147483647) / 2147483647
  return Array.from({ length: count }, (_, i): Stroke => {
    const off = (i / (count - 1) - .5) * spread + (r() - .5) * 2.4
    const edge = Math.abs(i / (count - 1) - .5) * 2
    const a = 96 + r() * (10 + edge * 34), b = 564 - r() * (10 + edge * 40)
    return {
      d: `M${a.toFixed(1)} ${(y0 + off).toFixed(1)} Q${(a + b) / 2} ${(Math.min(y0, y1) - 22 + off * 1.1).toFixed(1)} ${b.toFixed(1)} ${(y1 + off).toFixed(1)}`,
      w: 1 + r() * 2.6,
      o: .55 + r() * .45 * (1 - edge * .5),
      dash: broken ? `${Math.round(18 + r() * 46)} ${Math.round(16 + r() * 40)} ${Math.round(8 + r() * 26)} ${Math.round(22 + r() * 34)}` : undefined,
    }
  })
}
const SILVER = rubbed(77, 176, 168, 16, 22, true)
const GOLD = rubbed(4041, 268, 260, 26, 32, false)

function Line({ text, i, progress }: { text: string; i: number; progress: MotionValue<number> }) {
  const a = i * .32
  const opacity = useTransform(progress, i === 0 ? [0, .24, .3] : i === 1 ? [.26, .34, .56, .62] : [.58, .68], i === 0 ? [1, 1, 0] : i === 1 ? [0, 1, 1, 0] : [0, 1])
  const y = useTransform(progress, [a - .06, a + .04], [i === 0 ? 0 : 18, 0])
  return <motion.p className={i === 2 ? 'streak-last' : ''} style={reduced ? undefined : { opacity, y }}>{text}</motion.p>
}

export function Streak() {
  const ref = useRef<HTMLElement>(null)
  const { scrollYProgress: p } = useScroll({ target: ref, offset: ['start start', 'end end'] })
  const silverW = useTransform(p, [.04, .34], [0, 480])
  const goldW = useTransform(p, [.34, .68], [0, 480])
  const fade = useTransform(p, [.42, .74], [.95, .3])
  const stone = useTransform(p, [0, 1], [1.03, 1])
  return (
    <section className="streak" ref={ref} aria-label="Why the name Touchstone">
      <div className="streak-pin">
        <div className="wrap streak-grid">
          <div className="streak-copy">{LINES.map((t, i) => <Line key={t} text={t} i={i} progress={p} />)}</div>
          <motion.svg className="streak-stone" viewBox="0 0 640 420" role="img" aria-label="Two streaks on a dark stone: silver breaks up, gold holds" style={reduced ? undefined : { scale: stone }}>
            <defs>
              <linearGradient id="st-face" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#3b4047" /><stop offset=".45" stopColor="#1d2025" /><stop offset="1" stopColor="#0f1114" /></linearGradient>
              <linearGradient id="st-gold" gradientUnits="userSpaceOnUse" x1="96" y1="0" x2="564" y2="0"><stop stopColor="#c9963c" /><stop offset=".5" stopColor="#f2d088" /><stop offset="1" stopColor="#e2b45a" /></linearGradient>
            </defs>
            <path d="M58 92 214 26l232 18 158 118-36 170-204 66-254-22L28 246z" fill="url(#st-face)" stroke="#6b7078" strokeWidth="1.2" />
            <path d="M214 26 262 150 58 92M262 150l248 44 94-32M262 150l-46 196M510 194l-52 204" fill="none" stroke="#ffffff0d" strokeWidth="1" />
            <clipPath id="st-rub-s"><motion.rect x="90" y="130" height="90" width={reduced ? 480 : silverW} /></clipPath>
            <clipPath id="st-rub-g"><motion.rect x="90" y="218" height="90" width={reduced ? 480 : goldW} /></clipPath>
            <g clipPath="url(#st-rub-s)" fill="none" strokeLinecap="round"><motion.g stroke="#b9bfc8" style={reduced ? { opacity: .3 } : { opacity: fade }}>{SILVER.map((l, i) => <path key={i} d={l.d} strokeWidth={l.w} strokeOpacity={l.o} strokeDasharray={l.dash} />)}</motion.g></g>
            <g clipPath="url(#st-rub-g)" fill="none" strokeLinecap="round" stroke="url(#st-gold)">{GOLD.map((l, i) => <path key={i} d={l.d} strokeWidth={l.w} strokeOpacity={l.o} />)}</g>
            <text className="streak-tag" x="112" y="134">reward</text>
            <text className="streak-tag gold" x="104" y="316">new problems</text>
          </motion.svg>
        </div>
      </div>
    </section>
  )
}
