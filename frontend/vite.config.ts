import { resolve } from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

function blockAdminPath(): Plugin | null {
  if (process.env.VITE_ENTRY === 'admin') return null
  return {
    name: 'block-admin-path',
    configurePreviewServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url?.split('?')[0] === '/admin.html') {
          res.statusCode = 404
          res.end('Not Found')
          return
        }
        next()
      })
    },
  }
}

function adminEntry(): Plugin | null {
  if (process.env.VITE_ENTRY !== 'admin') return null
  return {
    name: 'admin-entry',
    transformIndexHtml(html) {
      return html
        .replace('/favicon.svg', '/favicon-admin.svg')
        .replace(
          '<title>Chomelo — jukebox clandestina</title>',
          '<title>Chomelo Admin — consola</title>',
        )
    },
  }
}

export default defineConfig({
  server: {
    allowedHosts: ["jukebox.chomelo.org", "jukebox-admin.chomelo.org", "localhost"],
    proxy: {
      "/api": "http://backend:8000",
    },
  },
  preview: {
    allowedHosts: ["jukebox.chomelo.org", "jukebox-admin.chomelo.org", "localhost"],
  },
  plugins: [react(), adminEntry(), blockAdminPath()],
  build: {
    rollupOptions: {
      input: { main: resolve(__dirname, 'index.html') },
    },
  },
})
