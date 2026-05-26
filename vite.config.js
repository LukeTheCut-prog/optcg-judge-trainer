import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub repo: LukeTheCut-prog/optcg-judge-trainer
export default defineConfig({
  plugins: [react()],
  base: process.env.GITHUB_ACTIONS ? '/optcg-judge-trainer/' : '/',
})
