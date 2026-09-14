<template>
  <div class="customer-layout">
    <CustomerNavbar @open-cart="showCart = true" />
    <div v-if="showKycBanner" class="kyc-banner">
      <i class="bi bi-exclamation-triangle-fill me-2"></i>
      Tu cuenta aun no ha sido validada. No puedes comprar ni ofrecer servicios.
      <RouterLink to="/mi-cuenta/verificacion" class="kyc-banner-link">Completar verificacion</RouterLink>
    </div>
    <main id="main-content" class="customer-main" tabindex="-1">
      <ErrorBoundary>
        <RouterView v-slot="{ Component }">
          <Suspense>
            <component :is="Component" />
            <template #fallback>
              <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
              </div>
            </template>
          </Suspense>
        </RouterView>
      </ErrorBoundary>
    </main>
    <CustomerFooter />
    <CartOffcanvas v-model="showCart" />
    <SupportChatWidget />
    <CommunicationCenter />
    <ToastManager />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import { useCartStore } from '@/store/cart';
import { useWishlistStore } from '@/store/wishlist';
import { useAppConfigStore } from '@/store/appConfig';
import CustomerNavbar from './CustomerNavbar.vue';
import CustomerFooter from './CustomerFooter.vue';
import CartOffcanvas from './CartOffcanvas.vue';
import SupportChatWidget from '@/components/customer/ui/SupportChatWidget.vue';
import CommunicationCenter from '@/components/customer/communication/CommunicationCenter.vue';
import ErrorBoundary from '@/components/ui/ErrorBoundary.vue';
import ToastManager from '@/components/layout/ToastManager.vue';

const route = useRoute();
const authStore = useAuthStore();
const cartStore = useCartStore();
const wishlistStore = useWishlistStore();
const appConfigStore = useAppConfigStore();
const showCart = ref(false);

const showKycBanner = computed(() =>
  authStore.isAuthenticated &&
  !!authStore.user?.kyc_status &&
  authStore.user.kyc_status !== 'APPROVED' &&
  route.path.startsWith('/mi-cuenta')
);

onMounted(async () => {
  // Defensa en profundidad: una sesion de staff jamas debe reflejarse en el
  // sitio publico de clientes (bug real corregido 2026-07-14: el login
  // publico podia dejar tokens de admin en este origen antes de redirigir
  // al panel). Si el localStorage de este dominio quedo con un usuario
  // is_staff por cualquier via, se purga de inmediato al montar el layout.
  if (authStore.isAdmin) {
    authStore.logout();
  }
  appConfigStore.fetchConfig();
  if (authStore.isAuthenticated) {
    await cartStore.fetchCart();
    wishlistStore.fetchWishlist().catch(() => {});
  }
});

watch(() => authStore.isAuthenticated, async (authenticated) => {
  if (authenticated) {
    await cartStore.fetchCart();
    wishlistStore.fetchWishlist().catch(() => {});
  } else {
    cartStore.reset();
    wishlistStore.reset();
  }
});
</script>

<style scoped>
.customer-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  font-family: 'Inter', sans-serif;
}
.customer-main {
  flex: 1;
  padding-top: 70px;
}

.kyc-banner {
  /* sticky (no fixed): ocupa espacio en el flujo normal, empujando <main>
     hacia abajo automaticamente -- fixed superpondria el contenido ya que
     .customer-main solo compensa la altura del navbar, no la del banner. */
  position: sticky;
  top: 70px;
  z-index: 1020;
  background: #fef2f2;
  color: #991b1b;
  border-bottom: 1px solid #fecaca;
  padding: 10px 20px;
  text-align: center;
  font-size: .875rem;
}
.kyc-banner-link {
  color: #991b1b;
  font-weight: 700;
  text-decoration: underline;
  margin-left: 8px;
}
</style>
