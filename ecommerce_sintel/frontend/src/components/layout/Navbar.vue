<template>
  <nav class="sintel-navbar sticky-top">
    <div class="navbar-inner">
      <!-- Left: Sidebar toggle + Breadcrumb -->
      <div class="d-flex align-items-center gap-3">
        <button class="icon-btn d-lg-none" aria-label="Abrir menu" @click="$emit('toggle-sidebar')">
          <i class="bi bi-list fs-4"></i>
        </button>
        <div class="breadcrumb-area d-none d-lg-block">
          <span class="breadcrumb-root">{{ appConfigStore.brand.site_name }}</span>
          <i class="bi bi-chevron-right mx-2 text-muted small"></i>
          <span class="breadcrumb-current">{{ currentSection }}</span>
        </div>
      </div>

      <!-- Center: Search -->
      <div class="search-wrap d-none d-md-flex">
        <i class="bi bi-search search-icon"></i>
        <input type="text" class="search-input" placeholder="Buscar en el ecosistema... (Alt+S)" />
      </div>

      <!-- Right: Actions + User menu -->
      <div class="d-flex align-items-center gap-2">
        <!-- Dark mode toggle -->
        <button
          class="icon-btn"
          type="button"
          @click="toggleTheme"
          :title="theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
          :aria-label="theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
        >
          <i :class="['bi', theme === 'dark' ? 'bi-sun fs-5' : 'bi-moon-stars fs-5']" aria-hidden="true"></i>
        </button>

        <!-- Notifications -->
        <div class="dropdown">
          <button class="icon-btn position-relative" type="button" data-bs-toggle="dropdown" aria-label="Notificaciones" @click="onOpenNotifications">
            <i class="bi bi-bell fs-5" aria-hidden="true"></i>
            <span v-if="notificationsStore.unseenCount > 0" class="notif-badge">{{ notificationsStore.unseenCount }}</span>
          </button>
          <div class="dropdown-menu dropdown-menu-end notif-dropdown">
            <div class="notif-header">
              <h6 class="mb-0 fw-bold">Notificaciones</h6>
            </div>
            <div v-if="notificationsStore.loading" class="notif-empty">
              <span class="spinner-border spinner-border-sm text-primary"></span>
            </div>
            <div v-else-if="notificationsStore.recent.length === 0" class="notif-empty">
              <i class="bi bi-chat-dots-fill fs-1 opacity-25 d-block mb-2"></i>
              <p class="small text-muted mb-0">Sin novedades</p>
            </div>
            <ul v-else class="notif-list">
              <li v-for="log in notificationsStore.recent" :key="log.uuid" class="notif-item">
                <i :class="['bi', log.status === 'FAILED' ? 'bi-exclamation-triangle-fill text-danger' : 'bi-check-circle-fill text-success']"></i>
                <div class="notif-item-body">
                  <p class="notif-item-title mb-0">{{ log.template_slug || 'Notificacion' }}</p>
                  <p class="notif-item-meta mb-0">{{ log.channel }} · {{ formatDate(log.created_at) }}</p>
                </div>
              </li>
            </ul>
          </div>
        </div>

        <div class="vr mx-1 opacity-25"></div>

        <!-- User dropdown -->
        <div class="dropdown">
          <button class="user-btn" type="button" data-bs-toggle="dropdown">
            <div class="user-text d-none d-md-block text-end">
              <div class="user-email">{{ user?.email || '...' }}</div>
              <div class="user-role">{{ roleLabel }}</div>
            </div>
            <div class="user-avatar">{{ initials }}</div>
          </button>
          <ul class="dropdown-menu dropdown-menu-end dropdown-menu-modern">
            <li>
              <RouterLink class="dropdown-item dropdown-item-modern" to="/panel/perfil">
                <i class="bi bi-person me-2"></i> Mi Perfil
              </RouterLink>
            </li>
            <li><hr class="dropdown-divider mx-2"></li>
            <li>
              <button 
                class="dropdown-item dropdown-item-modern text-danger w-100 text-start d-flex align-items-center" 
                @click="handleLogout"
                :disabled="logoutLoading"
              >
                <span v-if="logoutLoading" class="spinner-border spinner-border-sm me-2"></span>
                <i v-else class="bi bi-box-arrow-right me-2"></i> 
                {{ logoutLoading ? 'Cerrando...' : 'Finalizar Sesión' }}
              </button>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import { useAppConfigStore } from '@/store/appConfig';
import { useNotificationsStore } from '@/store/notifications';
import { useAuth } from '@/composables/useAuth';
import { useTheme } from '@/composables/useTheme';

const route = useRoute();
const authStore = useAuthStore();
const appConfigStore = useAppConfigStore();
const notificationsStore = useNotificationsStore();
const { logout } = useAuth();
const { theme, toggle: toggleTheme } = useTheme();

function formatDate(value) {
  return new Date(value).toLocaleString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function onOpenNotifications() {
  notificationsStore.fetchRecent().then(() => notificationsStore.markOpened());
}

onMounted(() => {
  notificationsStore.fetchRecent();
});

const user = computed(() => authStore.user);
const initials = computed(() => authStore.initials);

const roleLabel = computed(() => user.value?.is_staff ? 'Administrador' : 'Usuario');

const sectionMap = {
  '/panel/dashboard': 'Dashboard',
  '/panel/productos': 'Productos',
  '/panel/categorias': 'Categorías',
  '/panel/ordenes': 'Órdenes',
  '/panel/servicios': 'Servicios Técnicos',
  '/panel/cotizaciones': 'Cotizaciones',
  '/panel/renta': 'Renta de Equipos',
  '/panel/marketing': 'Marketing',
  '/panel/usuarios': 'Gestión de Usuarios',
  '/panel/perfil': 'Mi Perfil',
};
const currentSection = computed(() => {
  for (const [prefix, label] of Object.entries(sectionMap)) {
    if (route.path.startsWith(prefix)) return label;
  }
  return 'Panel';
});

const logoutLoading = ref(false);

async function handleLogout() {
  logoutLoading.value = true;
  try {
    await logout();
  } finally {
    logoutLoading.value = false;
  }
}

defineEmits(['toggle-sidebar']);
</script>

<style scoped>
.sintel-navbar {
  height: 70px;
  background: rgba(255,255,255,.88);
  backdrop-filter: blur(12px) saturate(180%);
  border-bottom: 1px solid rgba(0,0,0,.07);
  z-index: 1030;
}
.navbar-inner {
  height: 100%; padding: 0 1.5rem;
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
}
.icon-btn {
  width: 40px; height: 40px; border-radius: 50%; border: 1px solid rgba(0,0,0,.06);
  background: transparent; color: #475569; display: flex; align-items: center; justify-content: center;
  transition: all .2s;
}
.icon-btn:hover { background: rgba(0,0,0,.05); color: #1e3a8a; }

.breadcrumb-root { color: #94a3b8; font-size: .875rem; }
.breadcrumb-current { color: #1e293b; font-weight: 600; font-size: .875rem; }

.search-wrap { position: relative; }
.search-icon { position: absolute; left: .875rem; top: 50%; transform: translateY(-50%); color: #94a3b8; font-size: .875rem; }
.search-input {
  padding: .5rem 1rem .5rem 2.5rem; border-radius: 50px;
  border: 1px solid transparent; background: rgba(0,0,0,.04);
  width: 320px; font-size: .875rem; transition: all .3s;
}
.search-input:focus {
  outline: none; background: #fff; border-color: #1e3a8a;
  box-shadow: 0 0 0 4px rgba(30,58,138,.1); width: 400px;
}

.user-btn {
  display: flex; align-items: center; gap: .625rem;
  background: none; border: none; padding: .375rem .5rem; border-radius: .75rem;
  cursor: pointer; transition: background .2s;
}
.user-btn:hover { background: rgba(0,0,0,.04); }
.user-email { font-size: .8rem; font-weight: 600; line-height: 1.2; color: #1e293b; }
.user-role { font-size: .68rem; color: #94a3b8; }
.user-avatar {
  width: 36px; height: 36px; background: #1e3a8a; color: #fff;
  border-radius: 10px; display: flex; align-items: center; justify-content: center;
  font-weight: 600; font-size: .875rem;
  box-shadow: 0 4px 10px rgba(30,58,138,.2);
}

.notif-badge {
  position: absolute; top: -2px; right: -2px;
  background: #ef4444; color: #fff; border-radius: 99px;
  min-width: 18px; height: 18px; padding: 0 4px;
  font-size: .65rem; font-weight: 700; line-height: 18px; text-align: center;
}
.notif-dropdown { width: 320px; border-radius: 16px; border: 1px solid rgba(0,0,0,.08); padding: 0; overflow: hidden; }
.notif-header { padding: .875rem 1rem; border-bottom: 1px solid rgba(0,0,0,.06); }
.notif-empty { padding: 2rem; text-align: center; }
.notif-list { list-style: none; margin: 0; padding: .25rem; max-height: 320px; overflow-y: auto; }
.notif-item { display: flex; gap: .625rem; align-items: flex-start; padding: .625rem .75rem; border-radius: 10px; }
.notif-item:hover { background: rgba(0,0,0,.03); }
.notif-item-title { font-size: .8rem; font-weight: 600; color: #1e293b; }
.notif-item-meta { font-size: .7rem; color: #94a3b8; }

.dropdown-menu-modern { border: 1px solid rgba(0,0,0,.08); border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,.1); padding: .5rem; margin-top: .75rem; }
.dropdown-item-modern { border-radius: 8px; padding: .5rem .75rem; font-size: .875rem; transition: background .2s; }
.dropdown-item-modern:hover { background: rgba(0,0,0,.04); }

/* --- Dark mode (2026-07-11) — este navbar es 100% CSS custom, no clases
   Bootstrap, asi que data-bs-theme="dark" no lo re-tema automaticamente. --- */
:global([data-bs-theme="dark"]) .sintel-navbar {
  background: rgba(15,23,42,.88);
  border-bottom-color: rgba(255,255,255,.08);
}
:global([data-bs-theme="dark"]) .icon-btn {
  color: #cbd5e1;
  border-color: rgba(255,255,255,.1);
}
:global([data-bs-theme="dark"]) .icon-btn:hover {
  background: rgba(255,255,255,.06);
  color: #93c5fd;
}
:global([data-bs-theme="dark"]) .breadcrumb-current { color: #e2e8f0; }
:global([data-bs-theme="dark"]) .search-input {
  background: rgba(255,255,255,.06);
  color: #e2e8f0;
}
:global([data-bs-theme="dark"]) .search-input:focus { background: rgba(15,23,42,.9); }
:global([data-bs-theme="dark"]) .user-email { color: #e2e8f0; }
:global([data-bs-theme="dark"]) .user-btn:hover { background: rgba(255,255,255,.06); }
</style>
