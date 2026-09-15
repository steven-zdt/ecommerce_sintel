<template>
  <aside class="account-sidebar">
    <div class="sidebar-header">
      <CustomerAvatar :src="avatarUrl" :initials="initials" :size="72" editable @click="$emit('go-profile')" />
      <div class="sidebar-user-info">
        <p class="sidebar-name">{{ displayName }}</p>
        <p class="sidebar-email">{{ userEmail }}</p>
      </div>
    </div>

    <nav class="sidebar-nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="sidebar-nav-item"
        active-class="sidebar-nav-item--active"
      >
        <i :class="['bi', item.icon, 'nav-icon']"></i>
        <span>{{ item.label }}</span>
        <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>

<script setup>
import { computed } from 'vue';
import { useAuthStore } from '@/store/auth';
import CustomerAvatar from '@/components/customer/account/CustomerAvatar.vue';

const emit = defineEmits(['go-profile']);
const authStore = useAuthStore();

const displayName = computed(() => {
  const u = authStore.user;
  if (!u) return 'Mi cuenta';
  return [u.first_name, u.last_name].filter(Boolean).join(' ') || u.email?.split('@')[0] || 'Mi cuenta';
});

const userEmail = computed(() => authStore.user?.email || '');

const initials = computed(() => {
  const parts = displayName.value.split(' ').filter(Boolean);
  return parts.slice(0, 2).map(p => p[0]?.toUpperCase()).join('');
});

const avatarUrl = computed(() => {
  const pic = authStore.user?.profile_picture;
  if (!pic) return null;
  return pic.startsWith('http') ? pic : `/media/${pic}`;
});

// Notificaciones (preferencias de canal) se retiro del alcance de Mi Cuenta
// (unificacion del design system, 2026-07-17) -- ver MEMORY.md.
const baseNavItems = [
  { to: '/mi-cuenta/perfil',      icon: 'bi-person',         label: 'Mi perfil' },
  { to: '/mi-cuenta/pedidos',     icon: 'bi-bag',            label: 'Mis pedidos' },
  { to: '/mi-cuenta/operaciones', icon: 'bi-truck',          label: 'Mis operaciones' },
  { to: '/mi-cuenta/wishlist',    icon: 'bi-heart',          label: 'Lista de deseos' },
  { to: '/mi-cuenta/direcciones', icon: 'bi-geo-alt',        label: 'Mis direcciones' },
  { to: '/mi-cuenta/tarjetas',    icon: 'bi-credit-card',    label: 'Metodos de pago' },
  { to: '/mi-cuenta/cotizaciones',icon: 'bi-clipboard-check',label: 'Cotizaciones' },
  { to: '/mi-cuenta/soporte',     icon: 'bi-headset',        label: 'Soporte' },
];

const navItems = computed(() => {
  const operationalTypes = ['TECHNICIAN', 'PROFESSIONAL', 'SPECIALIST', 'TRANSPORTER', 'CONTRACTOR'];
  const userType = authStore.user?.profile?.user_type;
  if (!operationalTypes.includes(userType)) {
    // SSoT de identidad: todo usuario nace CUSTOMER -- ofrecerle el upgrade
    // a Asociado de Negocio aqui es el UNICO lugar donde nace un profesional
    // (ver accounts/CLAUDE.md), nunca en el registro.
    if (userType === 'CUSTOMER') {
      return [
        ...baseNavItems,
        { to: '/mi-cuenta/perfil-profesional', icon: 'bi-briefcase', label: 'Solicitar cuenta como Asociado de Negocio' },
      ];
    }
    return baseNavItems;
  }
  return [
    ...baseNavItems,
    { to: '/mis-tareas', icon: 'bi-clipboard2-check', label: 'Mis tareas' },
  ];
});
</script>

<style scoped>
.account-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 24px 0 16px;
  height: fit-content;
  position: sticky;
  top: 90px;
}

.sidebar-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 0 20px 20px;
  border-bottom: 1px solid #f3f4f6;
  margin-bottom: 8px;
  text-align: center;
}

.sidebar-name {
  font-weight: 600;
  font-size: 0.95rem;
  color: #111827;
  margin: 0;
}

.sidebar-email {
  font-size: 0.75rem;
  color: #6b7280;
  margin: 0;
  word-break: break-all;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 8px;
}

.sidebar-nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  color: #374151;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background .15s, color .15s;
  position: relative;
}

.sidebar-nav-item:hover {
  background: #f3f4f6;
  color: #111827;
}

.sidebar-nav-item--active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}

.nav-icon { font-size: 1rem; }

.nav-badge {
  margin-left: auto;
  background: #ef4444;
  color: #fff;
  border-radius: 99px;
  padding: 1px 7px;
  font-size: 0.7rem;
  font-weight: 700;
}
</style>
