import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

// Only the Vite server reads API_TARGET. No credentials belong in frontend config.
const proxy = { '/api': { target: process.env.API_TARGET || 'http://127.0.0.1:8000', changeOrigin: true } }
export default defineConfig({ plugins: [tailwindcss()], server: { proxy }, preview: { proxy } })
