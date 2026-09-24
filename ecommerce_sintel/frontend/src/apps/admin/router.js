import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import { useAppConfigStore } from '@/store/appConfig';
import useApi from '@/composables/useApi';

// Rutas divididas por dominio bajo ./routes/ (P2-3, auditoria 2026-07-23) --
// cada archivo preserva el orden interno original de sus rutas, que es lo
// unico relevante para evitar shadowing (dos rutas del MISMO nivel donde una
// estatica debe preceder a una dinamica, ver comentarios en
// adminOrders.routes.js/adminUsers.routes.js/adminRenting.routes.js). El
// orden ENTRE dominios distintos no importa: tienen prefijos de path
// distintos y no pueden ensombrecerse entre si.
import { authRoutes } from './routes/auth.routes';
import { customerRoutes } from './routes/customer.routes';
import { adminAuthRoutes } from './routes/adminAuth.routes';
import { adminShopRoutes } from './routes/adminShop.routes';
import { adminOrdersRoutes } from './routes/adminOrders.routes';
import { adminUsersRoutes } from './routes/adminUsers.routes';
import { adminServicesRoutes } from './routes/adminServices.routes';
import { adminQuotesRoutes } from './routes/adminQuotes.routes';
import { adminRentingRoutes } from './routes/adminRenting.routes';
import { adminCoreRoutes } from './routes/adminCore.routes';
import { adminOpsRoutes } from './routes/adminOps.routes';
import { adminSeoRoutes } from './routes/adminSeo.routes';
// adminAiRoutes (/panel/asistente) -- descongelado a peticion explicita del
// usuario (2026-09-23, ver settings.ADMIN_AI_ASSISTANT_ENABLED).
import { adminAiRoutes } from './routes/adminAi.routes';
// adminMarketingRoutes (/panel/marketing) -- el Sidebar (Sidebar.vue linea 180)
// ya enlazaba aqui desde antes, pero el router nunca lo registraba: la unica
// causa real de "`/panel/marketing` no permite crear campanias" (la API
// POST /api/v1/marketing/campaigns/ funciona bien, verificado; el usuario
// nunca podia LLEGAR al formulario). PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_
// CATALOG_MEDIA_CANALES_LOOP.md, Fase 1, 2026-09-23.
import { adminMarketingRoutes } from './routes/adminMarketing.routes';

// Lazy-load de vistas para mejor rendimiento
const AppShell      = () => import('@/components/layout/AppShell.vue');
const DashboardView = () => import('@/views/admin/DashboardView.vue');
const ProfileView   = () => import('@/views/admin/ProfileView.vue');

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    // ── AUTH ──────────────────────────────────────────────────────────────────
    ...authRoutes,

    // ── CUSTOMER PORTAL ───────────────────────────────────────────────────────
    customerRoutes,

    // ── PANEL ADMIN — login exclusivo (aislado de /login de clientes) ──────────
    ...adminAuthRoutes,

    // ── PANEL ADMIN (protegido — requiere admin) ───────────────────────────────
    {
      path: '/panel',
      component: AppShell,
      meta: { requiresAuth: true, requiresAdmin: true },
      redirect: '/panel/dashboard',
      children: [
        { path: 'dashboard',    name: 'dashboard',    component: DashboardView },
        { path: 'perfil',       name: 'profile',      component: ProfileView },
        ...adminShopRoutes,
        ...adminOrdersRoutes,
        ...adminUsersRoutes,
        ...adminServicesRoutes,
        ...adminQuotesRoutes,
        ...adminRentingRoutes,
        ...adminCoreRoutes,
        ...adminOpsRoutes,
        ...adminSeoRoutes,
        ...adminAiRoutes,
        ...adminMarketingRoutes,
      ],
    },

    // ── REDIRECT LEGACY ───────────────────────────────────────────────────────
    // ── CATCH-ALL ─────────────────────────────────────────────────────────────
    // Funcion en vez de `redirect: { name: 'home' }`: la forma objeto reutiliza
    // los params de la ruta no encontrada (incluye `pathMatch`), y como 'home'
    // no los declara, Vue Router los descarta con un warning en consola. Ver
    // https://github.com/vuejs/router/blob/main/packages/router/CHANGELOG.md#414-2022-08-22
    //
    // DT-L10 (auditoria, doc 02): version anterior redirigia SIEMPRE a '/'
    // (home publica), incluso para un typo dentro de /panel/* -- un admin
    // quedaba tirado en el catalogo de cliente en vez del dashboard. El guard
    // de host (mas abajo) solo cubre panel.sintel.net.co; en localhost/dev o
    // un solo dominio compartido, este catch-all es la unica red de
    // seguridad para /panel/algo-que-no-existe.
    { path: '/:pathMatch(.*)*', redirect: (to) => ({ path: to.path.startsWith('/panel') ? '/panel/dashboard' : '/' }) },
  ],
});

// ── Guard de host (Fase 3, ADR-001: aislamiento de dominio del panel) ──────────
// panel.sintel.net.co debe servir EXCLUSIVAMENTE /panel/*; los demas dominios
// (sintel.net.co, www) ya no deben poder navegar a /panel/*. No se activa un
// bundle/build separado (ver ADR-001 §2) -- es el mismo router de siempre,
// solo con esta restriccion adicional evaluada antes que cualquier guard de
// auth. localhost/127.0.0.1 (dev) quedan exentos para no requerir dos
// dominios en desarrollo local.
const ADMIN_HOSTNAME = 'panel.sintel.net.co';
const LOCAL_HOSTNAMES = ['localhost', '127.0.0.1'];

function isPanelPath(path) {
  return path === '/panel' || path.startsWith('/panel/');
}

// White-label F3 (2026-08-14): las 4 verticales "core" del sitio publico se pueden
// ocultar desde el panel (core.HomeModuleConfig.is_visible, ya existia -- ver
// AUDITORIA/WHITE_LABEL/WHITE_LABEL_MIGRATION_ROADMAP.md F3). Antes de esta fase el
// router no consultaba ese flag para nada -- una vertical desactivada seguia
// navegable directamente por URL aunque no apareciera en la home/navbar. Se mapean
// a mano (no generico) porque el mismo module_url puede ser compartido por modulos
// "custom" adicionales que no representan una vertical distinta (ver hallazgo en el
// roadmap); solo estas 4 claves nucleo controlan navegacion.
const CORE_MODULE_PATH_PREFIXES = {
  shop: '/tienda',
  renting: '/alquiler',
  services: '/servicios',
  quotes: '/cotizar',
};

function findDisabledCoreModuleFor(path, modules) {
  for (const [moduleKey, prefix] of Object.entries(CORE_MODULE_PATH_PREFIXES)) {
    if (path === prefix || path.startsWith(`${prefix}/`)) {
      const entry = modules.find((m) => m.module_key === moduleKey);
      if (entry && entry.is_visible === false) return moduleKey;
    }
  }
  return null;
}

// ── Navigation Guards ─────────────────────────────────────────────────────────
router.beforeEach(async (to) => {
  const hostname = window.location.hostname;
  if (!LOCAL_HOSTNAMES.includes(hostname)) {
    const isAdminHost = hostname === ADMIN_HOSTNAME;
    const targetIsPanel = isPanelPath(to.path);

    if (isAdminHost && !targetIsPanel) {
      // panel.sintel.net.co no sirve nada fuera de /panel/*.
      return { path: '/panel/dashboard' };
    }

    if (!isAdminHost && targetIsPanel) {
      // Purga cualquier sesion (de cliente o de staff) que hubiera quedado
      // en este origen antes de saltar al panel -- nunca debe quedar residuo
      // de una sesion de admin reflejado en sintel.net.co (bug real: el login
      // publico dejaba tokens de staff en este origen antes de este guard
      // redirigir). A-05 (auditoria enterprise): antes limpiaba ambos
      // storages a mano (localStorage/sessionStorage.removeItem por clave),
      // un tercer camino de limpieza de sesion fuera del store de auth --
      // usar authStore.logout() unifica con useApi.js (que ya lo usa en sus
      // 2 puntos de fallo de refresh/401) y ademas limpia el estado en
      // memoria de Pinia (accessToken/user), no solo el storage.
      useAuthStore().logout();
      // El dominio publico ya no sirve el panel. Redirige preservando el
      // path completo (incluye query/hash via fullPath) para no romper
      // bookmarks/enlaces antiguos a sintel.net.co/panel/* (ADR-001 D2).
      window.location.replace(`https://${ADMIN_HOSTNAME}${to.fullPath}`);
      return false;
    }
  }

  // White-label F3: si la ruta destino pertenece a una de las 4 verticales core y
  // esta desactivada desde el panel, redirige a home en vez de renderizarla. Fetch
  // cacheado (fetchConfig() no repite la llamada si ya cargo) -- no agrega una
  // llamada extra en la practica, CustomerLayout/AppShell ya lo iban a pedir.
  if (!isPanelPath(to.path)) {
    const appConfigStore = useAppConfigStore();
    await appConfigStore.fetchConfig();
    if (findDisabledCoreModuleFor(to.path, appConfigStore.modules)) {
      return { name: 'home' };
    }
  }

  // Recuperacion PSE: cuando el navegador regresa despues de la redireccion bancaria,
  // sessionStorage conserva el UUID de la transaccion pendiente.
  // Lo interceptamos aqui y mandamos al usuario directamente a /payment/result.
  const pendingTx = sessionStorage.getItem('wompi_pending_tx');
  if (pendingTx && to.path !== '/payment/result') {
    sessionStorage.removeItem('wompi_pending_tx');
    return { path: '/payment/result', query: { tx: pendingTx } };
  }

  const authStore = useAuthStore();

  // Sincronizar perfil si los datos de sesion no tienen is_staff (localStorage viejo)
  if (authStore.isAuthenticated && authStore.user?.is_staff === undefined) {
    try {
      const api = useApi();
      const { data } = await api.get('auth/profile/');
      authStore.setUser(data);
    } catch (_) {
      authStore.logout();
      return { name: 'admin-login' };
    }
  }

  // Refrescar perfil al entrar al dashboard del cliente -- asi un upgrade
  // aprobado (user_type/kyc_status) se refleja en el menu/sidebar sin
  // necesidad de relogin (no existe infraestructura WebSocket para esto).
  if (authStore.isAuthenticated && to.path.startsWith('/mi-cuenta')) {
    try {
      const api = useApi();
      const { data } = await api.get('auth/profile/');
      authStore.setUser(data);
    } catch (_) {
      // Silencioso -- si falla, el usuario sigue con los datos que ya tenia
    }
  }

  // 1. Ruta del panel admin requiere auth -> admin-login (ruta aislada)
  if (to.meta.requiresAuth && to.meta.requiresAdmin && !authStore.isAuthenticated) {
    return { name: 'admin-login' };
  }

  // 2. Ruta requiere auth genérica (clientes) y no autenticado -> login cliente
  if (to.meta.requiresAuth && !to.meta.requiresAdmin && !authStore.isAuthenticated) {
    return { name: 'login' };
  }

  // 3. Ruta requiere admin y esta autenticado pero no es admin -> tienda
  if (to.meta.requiresAdmin && authStore.isAuthenticated && !authStore.isAdmin) {
    return { name: 'shop-catalog' };
  }

  // 4. /panel/login con admin ya autenticado -> dashboard directo
  if (to.meta.requiresAdminGuest && authStore.isAuthenticated && authStore.isAdmin) {
    return { name: 'dashboard' };
  }

  // 5. Ruta de guest (login/register) con usuario autenticado -> su area
  if (to.meta.requiresGuest && authStore.isAuthenticated) {
    return authStore.isAdmin ? { name: 'dashboard' } : { name: 'shop-catalog' };
  }
});

export default router;
