import { resolve } from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// En dev, el servicio "admin" de docker-compose pasa VITE_ENTRY=admin
// para que sirva admin.html en vez de index.html — así la URL de la
// consola es http://localhost:5174/ tal cual, sin sufijo. No basta con
// reescribir "/": una navegación directa a una ruta de React Router
// (p.ej. /login o /3/members, no un client-side navigate) es una request
// GET normal que, sin esto, cae al index.html por defecto de Vite en una
// app multi-página — sirviendo la app equivocada.
function serveAdminAtRoot(): Plugin | null {
  if (process.env.VITE_ENTRY !== 'admin') return null
  return {
    name: 'serve-admin-at-root',
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        const url = req.url?.split('?')[0] ?? ''
        const isNavigation =
          req.method === 'GET' && !!req.headers.accept?.includes('text/html')
        const isFileOrInternal = /\.[a-zA-Z0-9]+$/.test(url) || url.startsWith('/@') || url.startsWith('/src/')
        if (isNavigation && !isFileOrInternal && url !== '/admin.html') {
          req.url = '/admin.html'
        }
        next()
      })
    },
  }
}

// https://vite.dev/config/
// App multi-página: index.html es la app de oyentes, admin.html la
// consola de administración — se sirven en puertos distintos (ver
// docker-compose.yml) para que cada una tenga su propio localStorage y
// las sesiones de oyente/admin no se pisen en el mismo navegador.
export default defineConfig({
  plugins: [react(), serveAdminAtRoot()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        admin: resolve(__dirname, 'admin.html'),
      },
    },
  },
})
