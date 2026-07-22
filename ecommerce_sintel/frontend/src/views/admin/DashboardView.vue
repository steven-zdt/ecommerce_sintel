<template>
  <div class="dashboard-container">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold mb-0">Panel de Control</h4>
      <div class="d-flex align-items-center gap-3">
        <router-link :to="{ name: 'shop-catalog' }" class="btn btn-sm btn-outline-primary d-flex align-items-center gap-2">
          <i class="bi bi-shop"></i>
          <span class="d-none d-sm-inline">Ver Tienda</span>
        </router-link>
        <div class="text-muted small">Actualizado: {{ lastUpdate }}</div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-3">
        <router-link :to="{ name: 'product-list' }" class="quick-action-card">
          <i class="bi bi-plus-circle-fill"></i>
          <span>Nuevo Producto</span>
        </router-link>
      </div>
      <div class="col-6 col-md-3">
        <router-link :to="{ name: 'orders' }" class="quick-action-card">
          <i class="bi bi-cart-plus-fill"></i>
          <span>Gestionar Órdenes</span>
        </router-link>
      </div>
      <div class="col-6 col-md-3">
        <router-link :to="{ name: 'users-list' }" class="quick-action-card">
          <i class="bi bi-person-plus-fill"></i>
          <span>Nuevo Usuario</span>
        </router-link>
      </div>
      <div class="col-6 col-md-3">
        <router-link :to="{ name: 'marketing' }" class="quick-action-card quick-action-card--accent">
          <i class="bi bi-megaphone-fill"></i>
          <span>Panel Marketing</span>
        </router-link>
      </div>
      <div class="col-6 col-md-3">
        <router-link :to="{ name: 'home' }" class="quick-action-card">
          <i class="bi bi-globe2"></i>
          <span>Ver Landing</span>
        </router-link>
      </div>
    </div>

    <!-- KPI Cards -->
    <div class="row g-4 mb-4">
      <div class="col-sm-6 col-xl-3" v-for="kpi in kpis" :key="kpi.label">
        <div class="kpi-card h-100">
          <div class="kpi-icon" :style="{ background: kpi.color }">
            <i :class="['bi', kpi.icon]"></i>
          </div>
          <div>
            <div class="kpi-value">
              <template v-if="loading">
                <span class="placeholder-glow"><span class="placeholder col-6"></span></span>
              </template>
              <template v-else>{{ kpi.value }}</template>
            </div>
            <div class="kpi-label">{{ kpi.label }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Marketplace de Contratistas -->
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h6 class="fw-bold mb-0 text-muted">Marketplace de Contratistas</h6>
      <router-link :to="{ name: 'service-operations' }" class="btn btn-sm btn-light-primary px-3 rounded-pill">
        Ir a Operaciones de Servicios <i class="bi bi-arrow-right ms-1"></i>
      </router-link>
    </div>
    <div class="row g-4 mb-4">
      <div class="col-sm-6 col-xl-3" v-for="kpi in marketplaceKpis" :key="kpi.label">
        <div class="kpi-card h-100">
          <div class="kpi-icon" :style="{ background: kpi.color }">
            <i :class="['bi', kpi.icon]"></i>
          </div>
          <div>
            <div class="kpi-value">
              <template v-if="loading">
                <span class="placeholder-glow"><span class="placeholder col-6"></span></span>
              </template>
              <template v-else>{{ kpi.value }}</template>
            </div>
            <div class="kpi-label">{{ kpi.label }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="row g-4 mb-4">
      <div class="col-lg-6">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-header bg-white fw-bold py-3">
            <i class="bi bi-diagram-3 me-2 text-primary"></i>Categorías top (servicios completados)
          </div>
          <div class="card-body p-0">
            <div class="top-product-list">
              <div v-for="(cat, idx) in topCategories" :key="idx" class="top-product-item">
                <div class="product-rank">{{ idx + 1 }}</div>
                <div class="product-info">
                  <div class="product-name">{{ cat.name || 'Sin categoría' }}</div>
                </div>
                <div class="product-sales">
                  <span class="badge rounded-pill bg-light text-dark">{{ cat.count }} servicios</span>
                </div>
              </div>
              <div v-if="!topCategories.length" class="p-4 text-center text-muted small">Sin servicios completados aún.</div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-lg-6">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-header bg-white fw-bold py-3">
            <i class="bi bi-award me-2 text-warning"></i>Profesionales top
          </div>
          <div class="card-body p-0">
            <div class="top-product-list">
              <div v-for="(pro, idx) in topProfessionals" :key="idx" class="top-product-item">
                <div class="product-rank">{{ idx + 1 }}</div>
                <div class="product-info">
                  <div class="product-name">{{ `${pro.first_name} ${pro.last_name}`.trim() || pro.user__email }}</div>
                  <div class="product-sku text-muted small">{{ pro.user__email }}</div>
                </div>
                <div class="product-sales">
                  <span class="badge rounded-pill bg-light text-dark">{{ pro.completed_count }} servicios</span>
                </div>
              </div>
              <div v-if="!topProfessionals.length" class="p-4 text-center text-muted small">Sin datos suficientes aún.</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Conversion Rate -->
    <div v-if="conversionRate !== null && !loading" class="card p-3 mb-4 d-flex flex-row align-items-center gap-3">
      <i class="bi bi-arrow-repeat fs-4 text-success"></i>
      <div>
        <div class="fw-bold">Tasa de Conversión: {{ conversionRate.toFixed(1) }}%</div>
        <div class="text-muted small">
          {{ marketingData?.platform_overview?.paid_orders || 0 }} pagadas /
          {{ marketingData?.platform_overview?.total_orders || 0 }} totales
        </div>
      </div>
      <div class="ms-auto" style="width:200px">
        <div class="progress" style="height:8px">
          <div class="progress-bar bg-success" :style="{ width: conversionRate + '%' }"></div>
        </div>
      </div>
    </div>

    <div class="row g-4">
      <!-- Recent Activity (Left Column) -->
      <div class="col-lg-8">
        <div class="card border-0 shadow-sm h-100">
          <div class="card-header bg-white fw-bold py-3 d-flex justify-content-between align-items-center">
            <span><i class="bi bi-clock-history me-2 text-primary"></i>Ventas Recientes</span>
            <router-link :to="{ name: 'orders' }" class="btn btn-sm btn-light-primary px-3 rounded-pill">
              Ver todas <i class="bi bi-arrow-right ms-1"></i>
            </router-link>
          </div>
          <div class="table-responsive">
            <table class="table table-hover align-middle mb-0">
              <thead class="table-light">
                <tr>
                  <th class="ps-4">UUID</th>
                  <th>Estado</th>
                  <th>Total</th>
                  <th class="pe-4">Fecha</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading">
                  <td colspan="4" class="text-center py-5">
                    <div class="spinner-border text-primary opacity-50"></div>
                  </td>
                </tr>
                <tr v-else-if="!recentOrders.length">
                  <td colspan="4" class="text-center py-5 text-muted">Sin órdenes recientes.</td>
                </tr>
                <tr v-for="order in recentOrders" :key="order.id">
                  <td class="ps-4">
                    <div class="d-flex align-items-center">
                      <span class="uuid-badge">ORD-{{ order.uuid?.substring(0, 8) || order.id }}</span>
                    </div>
                  </td>
                  <td><span :class="['badge-soft', statusClass(order.status)]">{{ order.status }}</span></td>
                  <td class="fw-semibold text-dark">${{ Number(order.total_amount).toLocaleString('es-CO') }}</td>
                  <td class="text-muted small pe-4">{{ formatDate(order.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Alerts and Insights (Right Column) -->
      <div class="col-lg-4">

        <!-- Top Selling -->
        <div class="card border-0 shadow-sm">
          <div class="card-header bg-white fw-bold py-3">
            <i class="bi bi-graph-up-arrow me-2 text-success"></i>Productos más vendidos
          </div>
          <div class="card-body p-0">
            <div class="top-product-list">
              <div v-for="(product, idx) in topProducts" :key="idx" class="top-product-item">
                <div class="product-rank">{{ idx + 1 }}</div>
                <div class="product-info">
                  <div class="product-name">{{ product.item_name }}</div>
                  <div class="product-sku text-muted small">{{ product.sku }}</div>
                </div>
                <div class="product-sales">
                  <span class="badge rounded-pill bg-light text-dark">{{ product.units_sold }} vendidos</span>
                </div>
              </div>
              <div v-if="!topProducts.length" class="p-4 text-center text-muted small">
                Sin datos de ventas.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';

const api = useApi();
const toast = useToast();
const loading = ref(true);
const metrics = ref({ total_sales: 0, orders_count: 0, customers_count: 0, products_count: 0, recent_orders: [] });
const marketingData = ref(null);
const lastUpdate = ref(new Date().toLocaleTimeString());

const recentOrders = computed(() => metrics.value.recent_orders || []);
const conversionRate = computed(() => marketingData.value?.platform_overview?.conversion_rate_pct || 0);
const topProducts = computed(() => marketingData.value?.shop?.top_selling_products || []);

const marketplace = computed(() => metrics.value.marketplace || {});
const topCategories = computed(() => marketplace.value.top_categories || []);
const topProfessionals = computed(() => marketplace.value.top_professionals || []);

const marketplaceKpis = computed(() => [
  {
    label: 'Profesionales registrados',
    value: marketplace.value.professionals_count || 0,
    icon: 'bi-people-fill',
    color: 'linear-gradient(135deg,#0ea5e9,#0369a1)',
  },
  {
    label: `Disponibles (${marketplace.value.technicians_busy || 0} ocupados)`,
    value: marketplace.value.technicians_available || 0,
    icon: 'bi-person-workspace',
    color: 'linear-gradient(135deg,#10b981,#047857)',
  },
  {
    label: 'Calificación promedio',
    value: marketplace.value.average_rating ?? '—',
    icon: 'bi-star-fill',
    color: 'linear-gradient(135deg,#f59e0b,#b45309)',
  },
  {
    label: 'Servicios en curso',
    value: (marketplace.value.service_status_counts?.assigned || 0) + (marketplace.value.service_status_counts?.in_progress || 0),
    icon: 'bi-tools',
    color: 'linear-gradient(135deg,#8b5cf6,#5b21b6)',
  },
]);

const kpis = computed(() => [
  { 
    label: 'Ventas Totales', 
    value: `$${Number(metrics.value.total_sales || 0).toLocaleString('es-CO')}`, 
    icon: 'bi-currency-dollar', 
    color: 'linear-gradient(135deg,#2563eb,#1e3a8a)' 
  },
  { 
    label: 'Órdenes', 
    value: metrics.value.orders_count || 0, 
    icon: 'bi-cart-check-fill', 
    color: 'linear-gradient(135deg,#059669,#047857)' 
  },
  { 
    label: 'Clientes', 
    value: metrics.value.customers_count || 0, 
    icon: 'bi-people-fill', 
    color: 'linear-gradient(135deg,#d97706,#b45309)' 
  },
  { 
    label: 'Productos activos', 
    value: metrics.value.products_count || 0, 
    icon: 'bi-box-seam-fill', 
    color: 'linear-gradient(135deg,#7c3aed,#5b21b6)' 
  },
]);

function statusClass(s) {
  return { 
    paid: 'bg-success-soft text-success', 
    delivered: 'bg-primary-soft text-primary', 
    pending: 'bg-warning-soft text-warning', 
    cancelled: 'bg-danger-soft text-danger' 
  }[s] || 'bg-secondary-soft text-secondary';
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' });
}

onMounted(async () => {
  try {
    const [metricsRes, marketingRes] = await Promise.all([
      api.get('dashboard/metrics/'),
      api.get('marketing/dashboard/')
    ]);
    metrics.value = metricsRes.data;
    marketingData.value = marketingRes.data;
  } catch (e) {
    console.error('Error cargando dashboard:', e);
    toast.error('Error al sincronizar datos del servidor');
  } finally {
    loading.value = false;
    lastUpdate.value = new Date().toLocaleTimeString();
  }
});
</script>

<style scoped>
.dashboard-container {
  animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Quick Actions */
.quick-action-card {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 1.25rem; background: #fff; border-radius: 1rem; border: 1px solid rgba(0,0,0,.05);
  text-decoration: none; color: #475569; transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0,0,0,.02);
}
.quick-action-card i { font-size: 1.5rem; margin-bottom: 0.5rem; color: #2563eb; }
.quick-action-card span { font-size: 0.85rem; font-weight: 500; }
.quick-action-card:hover { 
  transform: translateY(-3px); box-shadow: 0 10px 15px -3px rgba(0,0,0,.08);
  background: #f8faff; border-color: #dbeafe;
}
.quick-action-card--accent i { color: #7c3aed; }

/* KPI Cards */
.kpi-card {
  background: #fff; border-radius: 1rem; padding: 1.25rem 1.5rem;
  display: flex; align-items: center; gap: 1rem;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,.05); transition: transform .2s;
}
.kpi-card:hover { transform: translateY(-3px); }
.kpi-icon {
  width: 52px; height: 52px; border-radius: .875rem;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 1.4rem; flex-shrink: 0;
}
.kpi-value { font-size: 1.5rem; font-weight: 700; color: #1e293b; line-height: 1.2; }
.kpi-label { font-size: .8rem; color: #94a3b8; margin-top: .25rem; }

/* Table Elements */
.uuid-badge {
  background: #f1f5f9; color: #64748b; font-family: monospace;
  padding: 0.25rem 0.5rem; border-radius: 0.375rem; font-size: 0.75rem;
}

/* Soft Badges */
.badge-soft {
  padding: 0.35em 0.8em; font-weight: 600; border-radius: 2rem; font-size: 0.75rem;
}
.bg-success-soft { background: #dcfce7; color: #15803d; }
.bg-primary-soft { background: #dbeafe; color: #1d4ed8; }
.bg-warning-soft { background: #fef3c7; color: #b45309; }
.bg-danger-soft { background: #fee2e2; color: #b91c1c; }
.bg-secondary-soft { background: #f1f5f9; color: #475569; }

/* Alerts Column */
.alert-item {
  display: flex; gap: 1rem; padding: 1.25rem; border-bottom: 1px solid #f1f5f9;
}
.alert-icon {
  width: 40px; height: 40px; border-radius: 0.5rem;
  display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0;
}
.alert-title { font-weight: 600; color: #1e293b; font-size: 0.9rem; }
.alert-desc { font-size: 0.8rem; color: #64748b; }

/* Top Products */
.top-product-list {
  background: #fff;
}
.top-product-item {
  display: flex; align-items: center; gap: 1rem; padding: 1rem 1.25rem;
  border-bottom: 1px solid #f1f5f9;
}
.product-rank {
  width: 24px; height: 24px; background: #f1f5f9; color: #64748b;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 700; flex-shrink: 0;
}
.product-info { flex-grow: 1; min-width: 0; }
.product-name { font-weight: 500; color: #1e293b; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.product-sku { font-size: 0.75rem; }

.btn-light-primary { background: #f0f7ff; color: #2563eb; font-weight: 600; font-size: 0.8rem; }
.btn-light-primary:hover { background: #2563eb; color: #fff; }
</style>
