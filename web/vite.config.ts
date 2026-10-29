import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

// Some dependencies ship a literal U+FFFD inside string literals; write it as the equivalent escape
// so the bundle is plain text that any uploader accepts.
const escapeReplacementChar = (): Plugin => ({
  name: 'escape-replacement-char',
  generateBundle(_, bundle) {
    for (const file of Object.values(bundle)) {
      if (file.type === 'chunk') file.code = file.code.replaceAll('�', '\\ufffd')
    }
  },
})

// Relative asset paths so the build works from any folder, including the published artifact.
export default defineConfig({
  base: './',
  plugins: [react(), escapeReplacementChar()],
  build: { chunkSizeWarningLimit: 1600 },
})
