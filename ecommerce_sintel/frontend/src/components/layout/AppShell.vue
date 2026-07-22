<template>
  <!-- Offcanvas Sidebar (mobile) -->
  <div
    class="offcanvas offcanvas-start bg-black"
    tabindex="-1"
    :class="{ show: sidebarOpen }"
    :style="sidebarOpen ? 'visibility:visible' : ''"
    id="sidebarOffcanvas"
  >
    <Sidebar @close="sidebarOpen = false" />
  </div>
  <div v-if="sidebarOpen" class="offcanvas-backdrop fade show" @click="sidebarOpen = false"></div>

  <div class="shell-wrapper">
    <!-- Desktop Sidebar -->
    <div class="d-none d-lg-flex sidebar-column">
      <Sidebar />
    </div>

    <!-- Content area -->
    <div class="content-area">
      <Navbar @toggle-sidebar="sidebarOpen = !sidebarOpen" />

      <main class="main-content container-fluid p-4">
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
    </div>
  </div>

  <!-- Toast notifications -->
  <ToastManager />

</template>

<script setup>
import { ref, onMounted } from 'vue';
import Sidebar from './Sidebar.vue';
import Navbar from './Navbar.vue';
import ToastManager from './ToastManager.vue';
import ErrorBoundary from '@/components/ui/ErrorBoundary.vue';
import { useAppConfigStore } from '@/store/appConfig';
import { useTheme } from '@/composables/useTheme';

const sidebarOpen = ref(false);
const appConfigStore = useAppConfigStore();
const { init: initTheme } = useTheme();

onMounted(() => {
  appConfigStore.fetchConfig();
  initTheme();
});
</script>

<style scoped>
.shell-wrapper {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.sidebar-column {
  flex-shrink: 0;
}
.content-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.main-content {
  flex: 1;
  overflow-y: auto;
  background: #f8fafc;
  transition: all .3s ease;
}
:global([data-bs-theme="dark"]) .main-content {
  background: #0f172a;
}
</style>
