import { resolve } from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// En dev, el servicio "admin" de docker-compose pasa VITE_ENTRY=admin
// para que la raíz "/" sirva admin.html en vez de index.html — así la
// URL de la consola es http://localhost:5174/ tal cual, sin sufijo.
function serveAdminAtRoot(): Plugin | null {
  if (process.env.VITE_ENTRY !== 'admin') return null
  return {
    name: 'serve-admin-at-root',
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        if (req.url === '/') req.url = '/admin.html'
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
