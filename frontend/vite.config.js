import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy /api calls to the PrepPilot backend (running on port 8001).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: { '/api': 'http://localhost:8001' },
  },
})
