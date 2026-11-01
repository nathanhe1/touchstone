/* The name made literal, in three dimensions. A black stone sits off the right edge of the first screen. A silver ball rubs a
   broken streak across it, then a gold ball rubs one that holds. Both streaks are painted into the stone's own textures,
   so they catch light as metal. Loaded on demand so three.js never delays the first paint. */
import { useEffect, useMemo, useRef } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'

const W = 2048, H = 1024
const SCALE = new THREE.Vector3(.56, 1, 1.26)
const BALL = .085

type Rub = { from: number; to: number; u0: number; u1: number; v0: number; v1: number; ink: string; broken: boolean; strokes: { off: number; w: number; a: number; seed: number }[] }

function makeRub(seed: number, from: number, to: number, u0: number, u1: number, v0: number, v1: number, ink: string, broken: boolean, count: number): Rub {
  let n = seed
  const r = () => (n = (n * 16807) % 2147483647) / 2147483647
  const strokes = Array.from({ length: count }, (_, i) => {
    const t = i / (count - 1) - .5
    return { off: t * 24 + (r() - .5) * 3, w: .4 + r() * 1.3, a: .45 + r() * .55 * (1 - Math.abs(t)), seed: Math.floor(r() * 1e6) }
  })
  return { from, to, u0, u1, v0, v1, ink, broken, strokes }
}
const SILVER = makeRub(77, .3, 1.9, .345, .475, .625, .61, '#c4c9d1', true, 34)
const GOLD = makeRub(4041, 2.2, 3.9, .335, .485, .5, .475, '#e8bd66', false, 34)
const NARROW = (r: Rub): Rub => ({ ...r, u0: .5 + (r.u0 - .41) * .62, u1: .5 + (r.u1 - .41) * .62 })
const ease = (t: number) => t * t * (3 - 2 * t)
const clamp = (t: number) => Math.min(1, Math.max(0, t))

// A point on the stone's surface for a texture coordinate, in the stone group's space.
function surface(u: number, v: number, out: THREE.Vector3) {
  const phi = u * Math.PI * 2, theta = (1 - v) * Math.PI
  const p = new THREE.Vector3(-Math.cos(phi) * Math.sin(theta), Math.cos(theta), Math.sin(phi) * Math.sin(theta))
  const n = new THREE.Vector3(p.x / SCALE.x, p.y / SCALE.y, p.z / SCALE.z).normalize()
  return out.copy(p).multiply(SCALE).addScaledVector(n, BALL + .012)
}

function useTextures() {
  return useMemo(() => {
    const map = document.createElement('canvas'), pbr = document.createElement('canvas'), bump = document.createElement('canvas')
    map.width = pbr.width = W; map.height = pbr.height = H
    bump.width = 1024; bump.height = 512
    const c = map.getContext('2d')!, m = pbr.getContext('2d')!, b = bump.getContext('2d')!
    c.fillStyle = '#17191d'; c.fillRect(0, 0, W, H)
    m.fillStyle = 'rgb(0,128,0)'; m.fillRect(0, 0, W, H)
    b.fillStyle = '#808080'; b.fillRect(0, 0, 1024, 512)
    let n = 91
    const r = () => (n = (n * 16807) % 2147483647) / 2147483647
    for (let i = 0; i < 26000; i++) {
      c.fillStyle = `rgba(${r() > .5 ? '255,255,255' : '0,0,0'},${.012 + r() * .03})`
      c.fillRect(r() * W, r() * H, 1 + r() * 3, 1 + r() * 3)
      b.fillStyle = `rgba(${r() > .5 ? '255,255,255' : '0,0,0'},${.06 + r() * .1})`
      b.fillRect(r() * 1024, r() * 512, 1 + r() * 2, 1 + r() * 2)
    }
    const mapT = new THREE.CanvasTexture(map), pbrT = new THREE.CanvasTexture(pbr), bumpT = new THREE.CanvasTexture(bump)
    mapT.colorSpace = THREE.SRGBColorSpace
    mapT.anisotropy = pbrT.anisotropy = 8
    return { c, m, mapT, pbrT, bumpT }
  }, [])
}

// Paints the part of a rub between two progress values, on both the colour and the metal maps.
function paint(rub: Rub, a: number, b: number, c: CanvasRenderingContext2D, m: CanvasRenderingContext2D) {
  const x = (t: number) => (rub.u0 + (rub.u1 - rub.u0) * t) * W
  const y = (t: number) => (1 - (rub.v0 + (rub.v1 - rub.v0) * t + Math.sin(t * Math.PI) * .014)) * H
  c.lineCap = m.lineCap = 'round'
  c.strokeStyle = rub.ink; m.strokeStyle = 'rgb(0,84,255)'
  for (const s of rub.strokes) {
    if (rub.broken) { const k = s.seed % 7 + 5, gap = Math.sin(a * k * 6.1 + s.seed) + Math.sin(a * (k + 9) * 2.3 + s.seed * .3) + a * .9; if (gap > .3) continue }
    c.globalAlpha = s.a; c.lineWidth = s.w; m.lineWidth = s.w
    for (const t of [c, m]) { t.beginPath(); t.moveTo(x(a), y(a) + s.off); t.lineTo(x(b), y(b) + s.off); t.stroke() }
  }
  c.globalAlpha = 1
}

function Lighting() {
  const { gl, scene } = useThree()
  useEffect(() => {
    const pmrem = new THREE.PMREMGenerator(gl), room = new RoomEnvironment()
    const env = pmrem.fromScene(room, .04)
    scene.environment = env.texture; scene.environmentIntensity = .26
    return () => { env.dispose(); pmrem.dispose(); scene.environment = null }
  }, [gl, scene])
  return <>
    <directionalLight position={[-4, 5, 5]} intensity={1.5} color="#fff1d6" />
    <directionalLight position={[5, -1, 2]} intensity={.8} color="#aeb9cc" />
  </>
}

function Scene({ still }: { still: boolean }) {
  const viewport = useThree(s => s.viewport)
  const group = useRef<THREE.Group>(null!), silver = useRef<THREE.Mesh>(null!), gold = useRef<THREE.Mesh>(null!)
  const { c, m, mapT, pbrT, bumpT } = useTextures()
  const done = useRef({ silver: 0, gold: 0 }), clock = useRef(0), tmp = useMemo(() => new THREE.Vector3(), [])
  const geometry = useMemo(() => {
    const g = new THREE.SphereGeometry(1, 180, 120), p = g.attributes.position, v = new THREE.Vector3()
    for (let i = 0; i < p.count; i++) {
      v.fromBufferAttribute(p, i)
      const d = Math.sin(v.x * 2.1 + 1) * Math.cos(v.y * 2.7) * .018 + Math.sin(v.y * 5.3 + v.z * 3) * .006
      v.multiplyScalar(1 + d); p.setXYZ(i, v.x, v.y, v.z)
    }
    g.computeVertexNormals()
    return g
  }, [])
  const narrow = viewport.aspect < .9
  const size = narrow ? viewport.width * .78 : Math.min(viewport.height * .46, viewport.width * .3)
  const silverRub = useMemo(() => narrow ? NARROW(SILVER) : SILVER, [narrow]), goldRub = useMemo(() => narrow ? NARROW(GOLD) : GOLD, [narrow])
  useFrame((state, delta) => {
    clock.current = still ? 10 : clock.current + Math.min(delta, .05)
    const t = clock.current
    let dirty = false
    const step = (rub: Rub, key: 'silver' | 'gold') => {
      const to = ease(clamp((t - rub.from) / (rub.to - rub.from)))
      for (let at = done.current[key]; at < to; at += .004) { paint(rub, at, Math.min(to, at + .004), c, m); dirty = true }
      if (to > done.current[key]) done.current[key] = to
      return to
    }
    const a = step(silverRub, 'silver'), b = step(goldRub, 'gold')
    if (dirty) { mapT.needsUpdate = true; pbrT.needsUpdate = true }
    surface(silverRub.u0 + (silverRub.u1 - silverRub.u0) * a, silverRub.v0 + (silverRub.v1 - silverRub.v0) * a, tmp); silver.current.position.copy(tmp)
    silver.current.visible = t > SILVER.from - .25
    surface(goldRub.u0 + (goldRub.u1 - goldRub.u0) * b, goldRub.v0 + (goldRub.v1 - goldRub.v0) * b, tmp); gold.current.position.copy(tmp)
    gold.current.visible = t > GOLD.from - .25
    const k = 1 - Math.pow(.02, delta)
    group.current.rotation.y += (state.pointer.x * .1 - .1 + Math.sin(state.clock.elapsedTime * .2) * .03 - group.current.rotation.y) * k
    group.current.rotation.x += (-state.pointer.y * .06 + .04 - group.current.rotation.x) * k
  })
  return (
    <group ref={group} position={narrow ? [0, -viewport.height * .34, 0] : [viewport.width * .02 + size * 1.26, -viewport.height * .05, 0]} scale={size}>
      <group rotation={[0, -Math.PI / 2, 0]}>
        <mesh geometry={geometry} scale={SCALE}>
          <meshPhysicalMaterial map={mapT} metalnessMap={pbrT} roughnessMap={pbrT} bumpMap={bumpT} bumpScale={.5} metalness={1} roughness={1} clearcoat={.3} clearcoatRoughness={.3} />
        </mesh>
        <mesh ref={silver} visible={false}><sphereGeometry args={[BALL, 48, 32]} /><meshStandardMaterial color="#cfd4dc" metalness={1} roughness={.22} /></mesh>
        <mesh ref={gold} visible={false}><sphereGeometry args={[BALL, 48, 32]} /><meshStandardMaterial color="#e6b95e" metalness={1} roughness={.18} /></mesh>
      </group>
    </group>
  )
}

function Loop({ active }: { active: boolean }) {
  const set = useThree(s => s.setFrameloop)
  useEffect(() => { set(active ? 'always' : 'never') }, [active, set])
  return null
}

export default function Stone({ active, still, onReady }: { active: boolean; still: boolean; onReady: () => void }) {
  return (
    <Canvas className="stone-canvas" camera={{ fov: 26, position: [0, 0, 7] }} dpr={[1, 1.75]} gl={{ antialias: true, alpha: true }} onCreated={onReady} aria-hidden="true">
      <Lighting /><Scene still={still} /><Loop active={active} />
    </Canvas>
  )
}
