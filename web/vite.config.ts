import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages serves from `<user>.github.io/<repo>/` — set base path to
// the repo name so asset URLs resolve. Local dev (`npm run dev`) uses "/"
// because VITE_BASE is unset.
const base = process.env.VITE_BASE ?? '/'

export default defineConfig({
  base,
  plugins: [react()],
})
