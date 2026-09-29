import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// Every build gets an id, compiled into the app and written to /version.json. An open tab
// compares the two (lib/version.ts) and offers a reload after a new build is deployed.
const buildId = Date.now().toString(36)
const versionFile: Plugin = {
  name: 'geo-draw-version',
  apply: 'build',
  generateBundle() {
    this.emitFile({ type: 'asset', fileName: 'version.json', source: JSON.stringify({ build: buildId }) })
  },
}

// Dev: `npm run dev` on :5173 forwards /api to the FastAPI server on :8000
// (`uvicorn api.main:app --reload` from the repo root). Same origin, so cookies just work.
export default defineConfig({
  plugins: [react(), tailwindcss(), versionFile],
  define: { __BUILD_ID__: JSON.stringify(buildId) },
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  // The chat page chunk (KaTeX, Markdown, drawing tools) is ~250 kB gzipped and loaded once.
  build: { chunkSizeWarningLimit: 1000 },
  server: {
    // start.sh passes GEO_DRAW_API_PORT when the API runs on another port.
    proxy: { '/api': `http://localhost:${process.env.GEO_DRAW_API_PORT ?? 8000}` },
  },
})
