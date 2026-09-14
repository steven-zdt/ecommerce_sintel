# sintel-e2e-ui

Tests e2e con Playwright.

## Antes de correr `npm install` en este host

`@playwright/test` descarga navegadores (Chromium/Firefox/WebKit) como paso
`postinstall`. En Windows, instalar/actualizar WebKit dispara además la
instalación silenciosa de WSL (`node_modules/playwright-core/bin/install_webkit_wsl.ps1`),
que el 2026-07-21 llevó a un ciclo de reinicios del servidor y tumbó producción.

Por eso este equipo tiene seteada la variable de usuario
`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` (persistente, `setx`). Con eso,
`npm install` **no** descarga ni toca navegadores/WSL automáticamente.

Si necesitás instalar/actualizar los navegadores de verdad, hacelo a mano y
de forma consciente:

```powershell
$env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = "0"
npx playwright install
```

Y volvé a dejar la variable de usuario en `1` después (`setx PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD 1`).

Este es un host de **producción** (corre `sintel_prod_db`, `nginx`,
`cloudflared` vía `docker-compose.prod.yml`). No corras nada que instale o
actualice software del sistema (WSL, Docker, features de Windows) sin
confirmación explícita de un humano.
