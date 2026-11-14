import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development the API runs separately on port 8000 (uvicorn backend.main:app).
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
