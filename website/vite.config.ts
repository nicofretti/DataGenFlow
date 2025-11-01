import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: process.env.BASE_URL || '/',
  build: {
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks: {
          // split react and react-dom into separate chunk
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          // split primer ui library into separate chunk
          'primer-vendor': ['@primer/react'],
          // split markdown rendering into separate chunk
          'markdown-vendor': ['react-markdown', 'remark-gfm', 'react-syntax-highlighter'],
        },
      },
    },
  },
})
