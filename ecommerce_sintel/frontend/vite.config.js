import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [vue()],
  // base: DIFERENTE segun comando -- vite.config.js es el mismo archivo para
  // "npm run dev" (command==='serve') y "npm run build" (command==='build'),
  // pero cada uno necesita un base distinto:
  //   - dev: '/' -- el servidor Vite en localhost:5173 sirve TODO desde la
  //     raiz (HTML, HMR, fallback SPA para rutas como /panel/dashboard).
  //     Poner aqui el prefijo de produccion rompe el servidor de desarrollo
  //     completo (bug real: /panel/dashboard devolvia 404 en localhost:5173
  //     tras fijar base al prefijo de produccion sin condicionar por comando).
  //   - build: '/static/panel/js/bundle/' -- DEBE coincidir con
  //     static_url_prefix en DJANGO_VITE (settings/base.py) y con donde
  //     collectstatic realmente deja los archivos
  //     (staticfiles/panel/js/bundle/...). Vite usa "base" para construir en
  //     tiempo de ejecucion las URLs de imports/CSS de rutas cargadas
  //     dinamicamente (code-splitting) -- con base:'/' en el build de
  //     produccion esas URLs salian como /assets/Chunk.js en vez de
  //     /static/panel/js/bundle/assets/Chunk.js, Nginx devolvia el shell
  //     HTML (catch-all) para esa ruta inexistente, y el navegador
  //     rechazaba el modulo por MIME type incorrecto ("Failed to load
  //     module script... text/html"), dejando la SPA en pantalla en blanco.
  //   Bugs reales encontrados probando en desarrollo y produccion reales (2026-07-10).
  base: command === 'build' ? '/static/panel/js/bundle/' : '/',
  server: {
    // DOCKER FIX: usar 0.0.0.0 para que el contenedor 'frontend' sea accesible
    // desde el contenedor 'django' a traves de la red Docker.
    // Con 'localhost' solo seria accesible dentro del mismo contenedor.
    host: '0.0.0.0',
    port: 5173,
    // HMR: el navegador necesita saber la URL publica del servidor Vite.
    // En desarrollo con Docker, el navegador llega por localhost:5173.
    hmr: {
      host: 'localhost',
      port: 5173,
    },
    // WINDOWS/DOCKER FIX: inotify no propaga eventos del filesystem NTFS al
    // contenedor Linux. Sin polling, Vite nunca detecta cambios del host
    // y el HMR queda silenciosamente inactivo.
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
  build: {
    // outDir: directorio de salida del bundle, relativo a /frontend.
    // 'dist' es la ruta estandar de Vite y es la que el Dockerfile copia al stage runtime.
    // En desarrollo se usa 'npm run dev' (Vite dev server), no los archivos buildados.
    outDir: 'dist',
    emptyOutDir: true,
    // manifest:true genera el archivo .vite/manifest.json que django-vite necesita
    // para resolver los nombres de archivos con hash en produccion.
    manifest: true,
    rollupOptions: {
      input: {
        // admin: unico SPA real -- sirve tanto /panel/* como el portal de cliente
        // (mismo router.js, ver frontend/CLAUDE.md). Monta en #shop-spa-root.
        admin: resolve(__dirname, 'src/apps/admin/main.js'),
      },
    },
  },
  resolve: {
    alias: {
      // '@' permite imports limpios sin rutas relativas largas:
      // import useApi from '@/composables/useApi' en lugar de '../../composables/useApi'
      '@': resolve(__dirname, 'src'),
    },
  },
  // Vitest lee este mismo archivo — "npm run test" ejecuta con command==='serve'
  // (Vitest resuelve la config como el dev server), asi que 'base' arriba se
  // resuelve a '/' durante los tests, sin impacto (no se usa en tests).
  test: {
    environment: 'jsdom',
    globals: true,
    // .AGENT/load-tests/*.spec.ts y e2e/*.spec.js son specs de Playwright
    // (npx playwright test), no de Vitest -- excluir para que Vitest no
    // intente transformarlos (comparten el sufijo *.spec.js/.ts).
    exclude: ['**/node_modules/**', '**/.AGENT/**', '**/e2e/**'],
  },
}));
