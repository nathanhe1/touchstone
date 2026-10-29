import { useEffect } from 'react'
import { useThree } from '@react-three/fiber'
import { ShaderGradientCanvas, ShaderGradient } from '@shadergradient/react'

/** Stops the render loop while the gradient is off screen, without destroying the WebGL context. */
function Loop({ active }: { active: boolean }) {
  const setFrameloop = useThree(s => s.setFrameloop)
  useEffect(() => { setFrameloop(active ? 'always' : 'never') }, [active, setFrameloop])
  return null
}

// Loaded on demand so three.js never delays the first paint.
export default function Shader({ colors, active }: { colors: [string, string, string]; active: boolean }) {
  return (
    <ShaderGradientCanvas style={{ position: 'absolute', inset: 0 }} pixelDensity={0.6} fov={45} lazyLoad={false}>
      <ShaderGradient type="waterPlane" animate="on" uSpeed={0.12} uStrength={1.6} uDensity={1.1} uFrequency={3.2} uAmplitude={0}
        color1={colors[0]} color2={colors[1]} color3={colors[2]} brightness={0.9} lightType="3d" grain="off"
        cAzimuthAngle={170} cPolarAngle={70} cDistance={4.2} cameraZoom={1} positionX={0} positionY={0.9} positionZ={-0.3}
        rotationX={45} rotationY={0} rotationZ={0} reflection={0.1} />
      <Loop active={active} />
    </ShaderGradientCanvas>
  )
}
