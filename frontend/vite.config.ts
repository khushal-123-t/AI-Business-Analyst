import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // In local monorepo development, load root .env; in Vercel or standalone builds, load from ./
  envDir: fs.existsSync(path.resolve(__dirname, '../.env')) ? '../' : './',
})
