<template>
  <nav id="sintel-sidebar" class="sidebar d-flex flex-column h-100">
    <!-- Mobile header -->
    <div class="offcanvas-header d-lg-none border-bottom border-dark border-opacity-50 py-3">
      <h5 class="offcanvas-title text-gradient fw-bold mb-0">{{ brandName }} Panel</h5>
      <button type="button" class="btn-close btn-close-white" @click="$emit('close')"></button>
    </div>

    <!-- Desktop header -->
    <div class="sidebar-brand p-4 border-bottom border-dark border-opacity-50 d-none d-lg-block">
      <h4 class="mb-0 fw-bold text-gradient">{{ brandName }} <span class="fw-light opacity-50">Admin</span></h4>
    </div>

    <!-- Navigation -->
    <ul class="list-unstyled mt-3 px-3 flex-grow-1 overflow-auto">

      <!-- Panel -->
      <li class="sidebar-label px-1 pt-2 pb-2">Panel</li>
      <li v-for="item in mainLinks" :key="item.to">
        <RouterLink :to="item.to" class="sidebar-link" :class="{ active: isActive(item.to) }">
          <i :class="['bi', item.icon, 'me-3 fs-5']"></i>
          {{ item.label }}
        </RouterLink>
      </li>

      <!-- Modulos por app -->
      <li class="sidebar-label px-1 pt-4 pb-2">Modulos</li>

      <li v-for="group in moduleGroups" :key="group.key" class="grp-wrap">
        <button
          class="sidebar-group-btn"
          :class="{ 'grp-active': isGroupActive(group) }"
          :style="`--c: ${group.color}`"
          @click="toggleGroup(group.key)"
        >
          <span class="grp-dot"></span>
          <i :class="['bi', group.icon, 'grp-icon']"></i>
          <span class="grp-text">
            <span class="grp-name">{{ group.label }}</span>
            <span class="grp-src">{{ group.src }}</span>
          </span>
          <i :class="['bi chevron', openGroups[group.key] ? 'bi-chevron-up' : 'bi-chevron-down']"></i>
        </button>

        <ul v-show="openGroups[group.key]" class="list-unstyled submenu" :style="`--c: ${group.color}`">
          <li v-for="item in group.children" :key="item.to">
            <RouterLink :to="item.to" class="sub-link" :class="{ active: isActive(item.to) }">
              <i :class="['bi', item.icon, 'sub-icon']"></i>
              {{ item.label }}
            </RouterLink>
          </li>
        </ul>
      </li>

      <!-- Configuracion (antes "Sistema", CORE v4 Fase 6) -->
      <li class="sidebar-label px-1 pt-4 pb-2">Configuracion</li>
      <li v-for="item in systemLinks" :key="item.to">
        <RouterLink :to="item.to" class="sidebar-link" :class="{ active: isActive(item.to) }">
          <i :class="['bi', item.icon, 'me-3 fs-5']"></i>
          {{ item.label }}
        </RouterLink>
      </li>

    </ul>
  </nav>
</template>

<script setup>
import { reactive, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useAppConfigStore } from '@/store/appConfig';

// White-label F7 (2026-08-14): antes "Sintel Panel"/"Sintel UI" hardcodeado --
// ver AUDITORIA/WHITE_LABEL/WHITE_LABEL_FRONTEND_AUDIT.md.
const appConfigStore = useAppConfigStore();
const brandName = computed(() => appConfigStore.brand.site_name || 'Panel');

const route = useRoute();

const isActive   = (path) => route.path.startsWith(path.replace(/\/$/, ''));
const isGroupActive = (g) => g.children.some(item => isActive(item.to));

// Asistente IA (/panel/asistente) -- descongelado a peticion explicita del
// usuario (2026-09-23, ver settings.ADMIN_AI_ASSISTANT_ENABLED). El propio
// comentario original de este archivo (congelamiento 2026-09-16) decia
// "descomentar esta entrada" pero la entrada del link nunca se llego a
// escribir aqui -- solo la nota. Se agrega ahora por primera vez.
const mainLinks = [
  { to: '/panel/dashboard',  icon: 'bi-speedometer2',  label: 'Dashboard' },
  { to: '/panel/perfil',     icon: 'bi-person-circle', label: 'Mi Perfil' },
  { to: '/panel/asistente',  icon: 'bi-robot',         label: 'Asistente IA' },
];

// [2026-07-12] Reorganizado por dominios de negocio (CORE v4, Fase 6), no por app tecnica.
// Ningun 'to' cambio de ruta -- ver Documentacion/Arquitectura_general/
// MIGRACION_CORE_V4_DOMINIOS_FASE2_NAVEGACION.md para el mapeo completo aprobado.
// Dominios sin ninguna vista todavia (Organization, CRM, Compras, Inventario, RRHH) no
// aparecen en el menu -- una seccion vacia es peor UX que no mostrarla (recomendacion
// explicita de la Fase 2).
const moduleGroups = [
  {
    key:   'organization',
    label: 'Organizacion',
    src:   'organization/',
    icon:  'bi-building-gear',
    color: '#64748b',
    children: [
      { to: '/panel/organizacion', icon: 'bi-building', label: 'Empresa e Institucional' },
    ],
  },
  {
    key:   'sitio-web',
    label: 'Sitio Web',
    src:   'core/',
    icon:  'bi-window-stack',
    color: '#14b8a6',
    children: [
      { to: '/panel/home-config',    icon: 'bi-house-gear', label: 'Home Publica' },
      { to: '/panel/nosotros',       icon: 'bi-people',      label: 'Nosotros' },
      { to: '/panel/seo/meta-tags',  icon: 'bi-tags',        label: 'Meta Tags SEO' },
    ],
  },
  {
    key:   'catalogo',
    label: 'Catalogo',
    src:   'shop/',
    icon:  'bi-shop',
    color: '#3b82f6',
    children: [
      { to: '/panel/productos',  icon: 'bi-box-seam',      label: 'Productos' },
      { to: '/panel/categorias', icon: 'bi-tag',           label: 'Categorias' },
      { to: '/panel/marcas',     icon: 'bi-bookmark-star', label: 'Marcas' },
      { to: '/panel/impuestos',  icon: 'bi-percent',       label: 'Impuestos' },
    ],
  },
  {
    key:   'cotizaciones',
    label: 'Cotizaciones',
    src:   'quotes/',
    icon:  'bi-file-earmark-text',
    color: '#f97316',
    children: [
      { to: '/panel/cotizaciones', icon: 'bi-file-earmark-text', label: 'Cotizaciones' },
    ],
  },
  {
    key:   'servicios',
    label: 'Servicios',
    src:   'technical_services/',
    icon:  'bi-tools',
    color: '#f59e0b',
    children: [
      { to: '/panel/servicios',    icon: 'bi-wrench-adjustable', label: 'Servicios' },
      { to: '/panel/servicios/solicitudes', icon: 'bi-inbox',    label: 'Solicitudes' },
      { to: '/panel/s-categorias', icon: 'bi-diagram-3',         label: 'Categorias' },
      { to: '/panel/s-niveles',    icon: 'bi-bar-chart-steps',   label: 'Niveles' },
    ],
  },
  {
    key:   'renting',
    label: 'Renting',
    src:   'renting/',
    icon:  'bi-truck',
    color: '#8b5cf6',
    children: [
      { to: '/panel/renta',        icon: 'bi-truck',          label: 'Equipos' },
      { to: '/panel/renta/solicitudes', icon: 'bi-clipboard-check', label: 'Solicitudes' },
      { to: '/panel/r-categorias', icon: 'bi-tags',           label: 'Categorias' },
      { to: '/panel/r-marcas',     icon: 'bi-bookmark-star',  label: 'Marcas' },
      { to: '/panel/r-labor',      icon: 'bi-person-gear',    label: 'Mano de Obra' },
    ],
  },
  {
    key:   'mkt',
    label: 'Marketing',
    src:   'marketing/',
    icon:  'bi-graph-up-arrow',
    color: '#ec4899',
    children: [
      { to: '/panel/marketing',   icon: 'bi-megaphone',  label: 'Campanias' },
    ],
  },
  {
    key:   'ventas',
    label: 'Ventas',
    src:   'orders/ · payment/',
    icon:  'bi-cart-check',
    color: '#f97316',
    children: [
      { to: '/panel/ordenes',      icon: 'bi-bag-check',         label: 'Ordenes' },
      { to: '/panel/pagos',        icon: 'bi-credit-card',       label: 'Pagos' },
    ],
  },
  {
    key:   'operaciones',
    label: 'Operaciones',
    src:   'operations/ · orders/ · technical_services/ · renting/',
    icon:  'bi-geo-alt',
    color: '#0ea5e9',
    children: [
      { to: '/panel/operaciones',  icon: 'bi-clipboard-check', label: 'Operaciones' },
      { to: '/panel/despachadores',icon: 'bi-person-badge',    label: 'Despachadores' },
      { to: '/panel/productos/operaciones', icon: 'bi-truck', label: 'Operaciones de Tienda' },
      { to: '/panel/servicios/operaciones', icon: 'bi-clipboard-check', label: 'Operaciones de Servicios' },
      { to: '/panel/servicios/asignacion-tecnicos', icon: 'bi-person-check', label: 'Asignacion de Tecnicos' },
      { to: '/panel/servicios/agenda', icon: 'bi-calendar3', label: 'Agenda de Tecnicos' },
      { to: '/panel/servicios/horarios', icon: 'bi-clock-history', label: 'Horarios y Ausencias' },
      { to: '/panel/ordenes/renting', icon: 'bi-truck-flatbed', label: 'Operaciones Renting' },
    ],
  },
  {
    key:   'proveedores',
    label: 'Proveedores/Contratistas',
    src:   'accounts/',
    icon:  'bi-person-badge',
    color: '#a855f7',
    children: [
      { to: '/panel/profesionales', icon: 'bi-person-badge', label: 'Profesionales' },
    ],
  },
  {
    key:   'soporte',
    label: 'Soporte',
    src:   'support/',
    icon:  'bi-headset',
    color: '#10b981',
    children: [
      { to: '/panel/soporte', icon: 'bi-chat-dots', label: 'Chat de Soporte' },
      { to: '/panel/soporte/tickets', icon: 'bi-ticket-detailed', label: 'Tickets' },
      { to: '/panel/soporte/ia-config', icon: 'bi-robot', label: 'Proveedores de IA' },
      { to: '/panel/soporte/whatsapp', icon: 'bi-whatsapp', label: 'Conexion WhatsApp' },
    ],
  },
];

// Abrir el grupo activo al cargar
const openGroups = reactive(
  Object.fromEntries(moduleGroups.map(g => [g.key, isGroupActive(g)]))
);

function toggleGroup(key) {
  openGroups[key] = !openGroups[key];
}

// [2026-07-12] Renombrado "Sistema" -> "Configuracion" (CORE v4, Fase 6). "Pagos" se movio
// al grupo Ventas (ver moduleGroups) -- Configuracion ya no lo incluye.
const systemLinks = [
  { to: '/panel/usuarios', icon: 'bi-people', label: 'Usuarios' },
  { to: '/panel/validaciones', icon: 'bi-patch-check', label: 'Validaciones KYC' },
  { to: '/panel/seguridad', icon: 'bi-shield-lock', label: 'Seguridad' },
  { to: '/panel/mcp-tokens', icon: 'bi-key', label: 'Tokens MCP' },
  { to: '/panel/notificaciones', icon: 'bi-bell', label: 'Notificaciones' },
];

defineEmits(['close']);
</script>

<style scoped>
/* ── Shell ───────────────────────────────────────────────────────── */
.sidebar {
  min-width: 270px; max-width: 270px;
  background: #0a0a0a; color: #fff;
  border-right: 1px solid rgba(255,255,255,0.05);
}
.text-gradient {
  background: linear-gradient(135deg, #fff 0%, #38bdf8 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* ── Labels ──────────────────────────────────────────────────────── */
.sidebar-label {
  font-size: .63rem; letter-spacing: 2.5px; text-transform: uppercase;
  font-weight: 700; color: rgba(255,255,255,.3);
}

/* ── Flat links (Panel / Sistema) ────────────────────────────────── */
.sidebar-link {
  display: flex; align-items: center;
  padding: .45rem 1rem; border-radius: 50px;
  color: rgba(255,255,255,.55); text-decoration: none;
  font-size: .92rem; font-weight: 500;
  transition: all .18s ease;
  margin-bottom: .2rem;
}
.sidebar-link:hover  { color: #fff; background: rgba(255,255,255,.07); transform: translateX(4px); }
.sidebar-link.active { color: #fff; background: #1e3a8a; box-shadow: 0 3px 12px rgba(30,58,138,.45); }

/* ── Group wrapper ───────────────────────────────────────────────── */
.grp-wrap { margin-bottom: .2rem; }

/* ── Group toggle button ─────────────────────────────────────────── */
.sidebar-group-btn {
  display: flex; align-items: center; width: 100%;
  padding: .45rem 1rem; border-radius: 50px; border: none; background: none;
  color: rgba(255,255,255,.55); font-size: .92rem; font-weight: 500;
  transition: all .18s ease; cursor: pointer;
}
.sidebar-group-btn:hover  { color: #fff; background: rgba(255,255,255,.07); }
.sidebar-group-btn.grp-active { color: #fff; }

/* colored dot */
.grp-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--c, #fff); flex-shrink: 0;
  margin-right: .65rem; opacity: .55;
  transition: opacity .18s, box-shadow .18s;
}
.sidebar-group-btn:hover .grp-dot,
.sidebar-group-btn.grp-active .grp-dot {
  opacity: 1;
  box-shadow: 0 0 7px var(--c, #fff);
}

/* icon next to dot */
.grp-icon { font-size: 1rem; margin-right: .6rem; flex-shrink: 0; }

/* label + source path */
.grp-text   { display: flex; flex-direction: column; flex-grow: 1; text-align: left; }
.grp-name   { font-size: .92rem; font-weight: 500; line-height: 1.2; }
.grp-src    { font-size: .6rem; font-family: monospace; opacity: .35; margin-top: .1rem; letter-spacing: .3px; }

/* chevron */
.chevron { font-size: .65rem; opacity: .5; flex-shrink: 0; }

/* ── Submenu ─────────────────────────────────────────────────────── */
.submenu {
  margin-left: 1.8rem;
  padding-left: .75rem;
  border-left: 2px solid var(--c, rgba(255,255,255,.12));
  margin-bottom: .35rem;
}
.sub-link {
  display: flex; align-items: center;
  padding: .3rem .65rem; border-radius: 40px;
  color: rgba(255,255,255,.5); text-decoration: none;
  font-size: .86rem; font-weight: 400;
  transition: all .15s ease;
  margin-bottom: .1rem;
}
.sub-link:hover  { color: #fff; background: rgba(255,255,255,.07); transform: translateX(3px); }
.sub-link.active { color: #fff; background: rgba(255,255,255,.12); font-weight: 600; }
.sub-icon { font-size: .85rem; margin-right: .5rem; flex-shrink: 0; }
</style>
