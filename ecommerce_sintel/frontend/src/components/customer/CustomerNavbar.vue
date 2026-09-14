<template>
  <nav :class="['customer-navbar navbar navbar-expand-lg', standalone ? 'position-relative' : 'fixed-top', { 'customer-navbar--scrolled': isScrolled }]" aria-label="Navegacion principal">
    <a class="skip-link" href="#main-content">Saltar al contenido principal</a>
    <div class="container-fluid px-3 px-lg-4">

      <!-- Logo / Nombre de empresa -->
      <RouterLink class="navbar-brand d-flex align-items-center gap-2" to="/">
        <img v-if="brand.logo" :src="brand.logo" :alt="`Logo de ${brand.site_name}`" class="brand-img" />
        <span class="brand-logo">{{ brand.site_name }}</span>
      </RouterLink>

      <!-- Nav links — desktop -->
      <div class="collapse navbar-collapse" id="customerNav">
        <ul class="navbar-nav mx-auto gap-1">
          <!-- Links dinamicos desde la BD, con fallback a links estaticos -->
          <template v-if="navLinks.length">
            <li v-for="link in navLinks" :key="link.uuid" class="nav-item">
              <a
                v-if="link.open_in_new_tab || isExternalUrl(link.url)"
                class="nav-link nav-pill"
                :href="link.url"
                target="_blank"
                rel="noopener noreferrer"
              >
                <i v-if="link.icon_class" :class="`bi ${link.icon_class} me-1`"></i>{{ link.label }}
              </a>
              <RouterLink
                v-else
                class="nav-link nav-pill"
                :class="{ active: route.path.startsWith(link.url) }"
                :to="link.url"
              >
                <i v-if="link.icon_class" :class="`bi ${link.icon_class} me-1`"></i>{{ link.label }}
              </RouterLink>
            </li>
          </template>
          <template v-else>
            <li class="nav-item">
              <RouterLink class="nav-link nav-pill" :class="{ active: route.path.startsWith('/tienda') }" to="/tienda">
                <i class="bi bi-shop me-1"></i>Tienda
              </RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink class="nav-link nav-pill" :class="{ active: route.path.startsWith('/alquiler') }" to="/alquiler">
                <i class="bi bi-truck me-1"></i>Alquiler
              </RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink class="nav-link nav-pill" :class="{ active: route.path.startsWith('/servicios') }" to="/servicios">
                <i class="bi bi-tools me-1"></i>Servicios
              </RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink class="nav-link nav-pill" :class="{ active: route.path.startsWith('/cotizar') }" to="/cotizar">
                <i class="bi bi-file-earmark-text me-1"></i>Cotizar
              </RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink class="nav-link nav-pill" :class="{ active: route.path.startsWith('/contratistas') }" to="/contratistas">
                <i class="bi bi-people me-1"></i>Contratistas
              </RouterLink>
            </li>
          </template>
        </ul>

        <!-- Search -->
        <div class="search-wrap me-3 d-none d-lg-block">
          <div class="input-group input-group-sm">
            <span class="input-group-text bg-white border-end-0 text-muted">
              <i class="bi bi-search"></i>
            </span>
            <input
              v-model="searchQuery"
              type="text"
              class="form-control border-start-0 ps-0"
              placeholder="Buscar productos..."
              @keyup.enter="doSearch"
              @input="onSearchInput"
            >
          </div>
        </div>

        <!-- Cart button -->
        <button class="btn btn-light btn-sm position-relative me-2 cart-btn" aria-label="Abrir carrito" @click="$emit('open-cart')">
          <i class="bi bi-bag fs-5"></i>
          <span v-if="cartStore.itemCount > 0" class="cart-badge">{{ cartStore.itemCount }}</span>
        </button>

        <!-- User menu -->
        <div v-if="authStore.isAuthenticated && !authStore.isAdmin" class="dropdown">
          <button class="btn btn-sm user-btn dropdown-toggle" data-bs-toggle="dropdown">
            <span class="user-avatar">{{ authStore.initials }}</span>
            <span class="d-none d-xl-inline ms-2">{{ authStore.user?.first_name || 'Mi cuenta' }}</span>
          </button>
          <ul class="dropdown-menu dropdown-menu-end shadow border-0">
            <li>
              <RouterLink class="dropdown-item" to="/mi-cuenta">
                <i class="bi bi-person me-2 text-muted"></i>Mi perfil
              </RouterLink>
            </li>
            <li>
              <RouterLink class="dropdown-item" to="/mi-cuenta/pedidos">
                <i class="bi bi-bag-check me-2 text-muted"></i>Mis pedidos
              </RouterLink>
            </li>
            <li>
              <RouterLink class="dropdown-item" to="/mi-cuenta/cotizaciones">
                <i class="bi bi-file-earmark-text me-2 text-muted"></i>Mis cotizaciones
              </RouterLink>
            </li>
            <li>
              <RouterLink class="dropdown-item" to="/mi-cuenta/perfil-profesional">
                <i class="bi bi-person-badge me-2 text-muted"></i>Asociado de Negocio
              </RouterLink>
            </li>
            <li><hr class="dropdown-divider"></li>
            <li>
              <button class="dropdown-item text-danger" @click="handleLogout" :disabled="logoutLoading">
                <span v-if="logoutLoading" class="spinner-border spinner-border-sm me-2"></span>
                <i v-else class="bi bi-box-arrow-right me-2"></i>Cerrar sesión
              </button>
            </li>
          </ul>
        </div>

        <div v-else class="d-flex gap-2">
          <RouterLink to="/login" class="btn btn-sm btn-outline-secondary px-3">Entrar</RouterLink>
          <RouterLink to="/register" class="btn btn-sm btn-outline-secondary px-3">Registrarse</RouterLink>
          <RouterLink to="/registro-profesional" class="btn btn-sm btn-warning fw-semibold px-3">
            <i class="bi bi-person-badge me-1"></i>Se Asociado de Negocio
          </RouterLink>
        </div>
      </div>

      <!-- Mobile: cart + hamburger -->
      <div class="d-flex align-items-center gap-2 d-lg-none">
        <button class="btn btn-light btn-sm position-relative cart-btn" aria-label="Abrir carrito" @click="$emit('open-cart')">
          <i class="bi bi-bag fs-5"></i>
          <span v-if="cartStore.itemCount > 0" class="cart-badge">{{ cartStore.itemCount }}</span>
        </button>
        <button class="navbar-toggler border-0" type="button" data-bs-toggle="collapse" data-bs-target="#customerNav" aria-controls="customerNav" aria-label="Abrir menu de navegacion">
          <i class="bi bi-list fs-4"></i>
        </button>
      </div>

    </div>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import { useCartStore } from '@/store/cart';
import { useAppConfigStore } from '@/store/appConfig';
import { useAuth } from '@/composables/useAuth';

/**
 * brandOverride / navLinksOverride: cuando se pasan (no null), reemplazan el
 * estado de appConfigStore -- usado por la Vista Previa de /panel/home-config
 * para reflejar los cambios EN MEMORIA del formulario (aun sin guardar), sin
 * afectar el uso real en CustomerLayout (que no pasa estas props y sigue
 * leyendo del store como siempre). Ver
 * ai_skills/frontend/editor/home_render_audit_2026_07_11.md (Fase 3).
 */
const props = defineProps({
  brandOverride:    { type: Object, default: null },
  navLinksOverride: { type: Array,  default: null },
  // standalone: usa position:relative en vez de fixed-top -- necesario para
  // embeber el navbar real dentro de un contenedor acotado (la Vista Previa
  // del panel admin), donde "fixed" se saldria del frame y taparia la
  // pantalla completa. El uso real en CustomerLayout no pasa esta prop.
  standalone: { type: Boolean, default: false },
});

defineEmits(['open-cart']);

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const cartStore = useCartStore();
const appConfigStore = useAppConfigStore();
const { logout } = useAuth();

const brand    = computed(() => props.brandOverride    || appConfigStore.brand);
const navLinks = computed(() => props.navLinksOverride || appConfigStore.navbarLinks);

// Un enlace externo debe abrirse como <a>, nunca como RouterLink (Vue Router
// trata cualquier "to" que no empiece con "/" como una ruta interna rota) --
// no depender solo del checkbox manual "abrir en nueva pestaña".
function isExternalUrl(url) {
  return /^https?:\/\//.test(url || '');
}

const searchQuery = ref('');
const logoutLoading = ref(false);
const isScrolled = ref(false);
let searchTimer = null;

function updateScrolledState() {
  isScrolled.value = !props.standalone && window.scrollY > 12;
}

onMounted(() => {
  updateScrolledState();
  window.addEventListener('scroll', updateScrolledState, { passive: true });
});

onUnmounted(() => window.removeEventListener('scroll', updateScrolledState));

function doSearch() {
  if (!searchQuery.value.trim()) return;
  router.push({ name: 'shop-catalog', query: { q: searchQuery.value.trim() } });
}

function onSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(doSearch, 400);
}

async function handleLogout() {
  logoutLoading.value = true;
  try {
    await logout();
  } finally {
    logoutLoading.value = false;
  }
}
</script>

<style scoped>
.customer-navbar {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.07);
  height: 70px;
  z-index: 1030;
  transition: box-shadow var(--landing-transition), background var(--landing-transition);
}
.customer-navbar--scrolled {
  background: rgba(255, 255, 255, .98);
  box-shadow: var(--landing-shadow-sm);
}
.skip-link {
  position: fixed;
  top: .75rem;
  left: .75rem;
  z-index: 1040;
  padding: .65rem 1rem;
  border-radius: var(--landing-radius-sm);
  background: var(--landing-ink-950);
  color: #fff;
  transform: translateY(-160%);
  transition: transform var(--landing-transition);
}
.skip-link:focus { transform: translateY(0); color: #fff; }

/* Menu movil (hamburguesa, < 992px / navbar-expand-lg): el menu expandido es
   hijo de .customer-navbar, que tiene height:70px fijo -- sin esto, el
   contenido del menu (links + buscador + carrito + sesion) se desborda por
   fuera de esos 70px SIN fondo propio, quedando dibujado directo encima del
   primer banner de la Home (bug real, corregido 2026-07-20). Se desacopla el
   panel del alto fijo del padre con su propio position:fixed + fondo solido,
   en vez de depender de que .customer-navbar crezca. */
@media (max-width: 991.98px) {
  .customer-navbar .navbar-collapse {
    position: fixed;
    top: 70px;
    left: 0;
    right: 0;
    max-height: calc(100vh - 70px);
    overflow-y: auto;
    background: #ffffff;
    box-shadow: 0 16px 32px rgba(0, 0, 0, 0.12);
    border-top: 1px solid rgba(0, 0, 0, 0.06);
    padding: 1rem 1.25rem 1.5rem;
  }
  .customer-navbar .navbar-nav {
    margin-bottom: 1rem;
  }
  .customer-navbar .search-wrap {
    margin-bottom: 1rem;
  }
}

.brand-img {
  height: 36px;
  width: auto;
  object-fit: contain;
}
.brand-logo {
  font-size: 1.4rem;
  font-weight: 800;
  background: linear-gradient(135deg, #2563eb 0%, #1e3a8a 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.nav-pill {
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 0.88rem;
  font-weight: 500;
  color: #374151;
  transition: all .15s ease;
}
.nav-pill:hover, .nav-pill.active {
  background: #eff6ff;
  color: #2563eb;
}

.search-wrap input, .search-wrap .input-group-text {
  border-radius: 0;
  border-color: #e5e7eb;
  font-size: .85rem;
}
.search-wrap .input-group {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  width: 240px;
  transition: width .2s ease;
}
.search-wrap .input-group:focus-within {
  width: 300px;
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px rgba(37,99,235,.1);
}

.cart-btn {
  border-radius: 10px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  transition: all .15s ease;
}
.cart-btn:hover {
  background: #dbeafe;
  border-color: #93c5fd;
}
.cart-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  background: #ef4444;
  color: white;
  font-size: 0.65rem;
  font-weight: 700;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  border: 2px solid white;
}

.user-btn {
  background: #eff6ff;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  padding: 6px 12px;
  font-weight: 500;
  font-size: .85rem;
  color: #1e40af;
  transition: all .15s ease;
}
.user-btn:hover { background: #dbeafe; }

.user-avatar {
  display: inline-flex;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #1e3a8a;
  color: white;
  font-size: .7rem;
  font-weight: 700;
  align-items: center;
  justify-content: center;
}

.dropdown-menu { border-radius: 12px; min-width: 200px; font-size: .88rem; }
.dropdown-item { border-radius: 6px; padding: 8px 12px; }
.dropdown-item:hover { background: #f3f4f6; }
</style>
