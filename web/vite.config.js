import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// `npm run dev`      -> committed mocks, backend can be switched off entirely
// `npm run dev:live` -> http://localhost:8000
//
// One flag, one client module. Components never call fetch directly, so
// swapping between the two is a mode change and nothing else.
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  define: {
    __USE_LIVE_API__: JSON.stringify(mode === 'live'),
    __API_BASE__: JSON.stringify('http://localhost:8000'),
  },
  server: { port: 5173 },
}))
