<template>
  <CustomerAccountShell>
    <CustomerPageHeader title="Mis direcciones" subtitle="Direcciones de envio guardadas.">
      <template #actions>
        <CustomerButton variant="primary" @click="openCreate">
          <i class="bi bi-plus-lg me-1"></i>Agregar direccion
        </CustomerButton>
      </template>
    </CustomerPageHeader>

    <CustomerSkeleton v-if="loading" layout="grid" :count="2" height="180px" />
    <CustomerErrorState v-else-if="loadError" @retry="fetchAddresses" />

    <CustomerEmptyState
      v-else-if="addresses.length === 0"
      icon="bi-geo-alt"
      title="No tienes direcciones guardadas"
      description="Agrega una direccion de envio para agilizar tus compras."
    >
      <template #action>
        <CustomerButton variant="primary" @click="openCreate">Agregar direccion</CustomerButton>
      </template>
    </CustomerEmptyState>

    <div v-else class="addresses-grid">
      <CustomerCard v-for="addr in addresses" :key="addr.uuid" :highlighted="addr.is_default">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <p class="addr-title"><i class="bi bi-geo-alt-fill me-1"></i>{{ addr.label || 'Direccion' }}</p>
          <span v-if="addr.is_default" class="badge bg-primary-subtle text-primary border border-primary-subtle small">Direccion Principal</span>
        </div>
        <p class="addr-name">{{ addr.full_name }}</p>
        <p class="addr-detail">{{ addr.address_line_1 }}</p>
        <p v-if="addr.address_line_2" class="addr-detail">{{ addr.address_line_2 }}</p>
        <p class="addr-detail">{{ addr.city }}, {{ addr.state }} {{ addr.postal_code }}</p>
        <p class="addr-detail">{{ addr.country }}</p>
        <p class="addr-detail"><i class="bi bi-telephone me-1"></i>{{ addr.phone_number }}</p>

        <CustomerConfirmInline
          v-if="pendingDelete?.uuid === addr.uuid"
          message="Eliminar esta direccion?"
          :loading="deleting"
          @confirm="executeDelete(addr)"
          @cancel="pendingDelete = null"
        />
        <div v-else class="addr-actions">
          <CustomerButton v-if="!addr.is_default" variant="secondary" @click="setDefault(addr)">
            Seleccionar como direccion de envio
          </CustomerButton>
          <CustomerButton variant="secondary" @click="openEdit(addr)">
            <i class="bi bi-pencil me-1"></i>Editar
          </CustomerButton>
          <CustomerButton variant="icon" aria-label="Eliminar direccion" @click="pendingDelete = addr">
            <i class="bi bi-trash"></i>
          </CustomerButton>
        </div>
      </CustomerCard>
    </div>

    <CustomerOverlayPanel v-model="showForm" :title="editing ? 'Editar direccion' : 'Nueva direccion'">
      <form @submit.prevent="saveAddress">
        <div class="row g-3">
          <div class="col-12">
            <label class="form-label small fw-semibold">Nombre de la direccion (Casa, Oficina, etc.)</label>
            <input v-model="form.label" type="text" class="form-control" placeholder="Casa" />
          </div>
          <div class="col-12">
            <label class="form-label small fw-semibold">Nombre completo</label>
            <input v-model="form.full_name" type="text" class="form-control" required />
          </div>
          <div class="col-12">
            <label class="form-label small fw-semibold">Direccion</label>
            <input v-model="form.address_line_1" type="text" class="form-control" required />
          </div>
          <div class="col-12">
            <label class="form-label small fw-semibold">Apartamento, apto, etc. (opcional)</label>
            <input v-model="form.address_line_2" type="text" class="form-control" />
          </div>
          <div class="col-6">
            <label class="form-label small fw-semibold">Ciudad</label>
            <input v-model="form.city" type="text" class="form-control" required />
          </div>
          <div class="col-6">
            <label class="form-label small fw-semibold">Departamento</label>
            <input v-model="form.state" type="text" class="form-control" />
          </div>
          <div class="col-6">
            <label class="form-label small fw-semibold">Codigo postal</label>
            <input v-model="form.postal_code" type="text" class="form-control" />
          </div>
          <div class="col-6">
            <label class="form-label small fw-semibold">Telefono</label>
            <input v-model="form.phone_number" type="tel" class="form-control" required />
          </div>
          <div class="col-12">
            <div class="form-check">
              <input v-model="form.is_default" type="checkbox" class="form-check-input" id="isDefaultCheck" />
              <label class="form-check-label small" for="isDefaultCheck">Usar como predeterminada</label>
            </div>
          </div>
        </div>
        <div class="d-flex gap-2 justify-content-end mt-4">
          <CustomerButton variant="secondary" @click="closeForm">Cancelar</CustomerButton>
          <CustomerButton variant="primary" :loading="saving">
            {{ editing ? 'Guardar cambios' : 'Agregar direccion' }}
          </CustomerButton>
        </div>
      </form>
    </CustomerOverlayPanel>
  </CustomerAccountShell>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import CustomerAccountShell from '@/components/customer/account/CustomerAccountShell.vue';
import CustomerPageHeader from '@/components/customer/account/CustomerPageHeader.vue';
import CustomerCard from '@/components/customer/account/CustomerCard.vue';
import CustomerButton from '@/components/customer/account/CustomerButton.vue';
import CustomerConfirmInline from '@/components/customer/account/CustomerConfirmInline.vue';
import CustomerOverlayPanel from '@/components/customer/account/CustomerOverlayPanel.vue';
import CustomerEmptyState from '@/components/customer/account/CustomerEmptyState.vue';
import CustomerErrorState from '@/components/customer/account/CustomerErrorState.vue';
import CustomerSkeleton from '@/components/customer/account/CustomerSkeleton.vue';

const api = useApi();
const toast = useToast();

const loading = ref(true);
const loadError = ref(false);
const saving = ref(false);
const deleting = ref(false);
const addresses = ref([]);
const showForm = ref(false);
const editing = ref(null);
const pendingDelete = ref(null);

const defaultForm = () => ({
  label: '', full_name: '', address_line_1: '', address_line_2: '',
  city: '', state: '', postal_code: '', country: 'Colombia',
  phone_number: '', is_default: false,
});
const form = ref(defaultForm());

async function fetchAddresses() {
  loading.value = true;
  loadError.value = false;
  try {
    const res = await api.get('orders/addresses/');
    addresses.value = res.data.results ?? res.data ?? [];
  } catch {
    loadError.value = true;
    toast.error('Error al cargar direcciones');
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  form.value = defaultForm();
  showForm.value = true;
}

function openEdit(addr) {
  editing.value = addr;
  form.value = {
    label: addr.label || '',
    full_name: addr.full_name || '',
    address_line_1: addr.address_line_1 || '',
    address_line_2: addr.address_line_2 || '',
    city: addr.city || '',
    state: addr.state || '',
    postal_code: addr.postal_code || '',
    country: addr.country || 'Colombia',
    phone_number: addr.phone_number || '',
    is_default: addr.is_default || false,
  };
  showForm.value = true;
}

function closeForm() {
  showForm.value = false;
  editing.value = null;
}

async function saveAddress() {
  saving.value = true;
  try {
    if (editing.value) {
      const res = await api.patch(`orders/addresses/${editing.value.uuid}/`, form.value);
      const idx = addresses.value.findIndex(a => a.uuid === editing.value.uuid);
      if (idx !== -1) addresses.value[idx] = res.data;
      if (res.data.is_default) addresses.value.forEach(a => { a.is_default = a.uuid === res.data.uuid; });
      toast.success('Direccion actualizada');
    } else {
      const res = await api.post('orders/addresses/', form.value);
      if (res.data.is_default) addresses.value.forEach(a => { a.is_default = false; });
      addresses.value.unshift(res.data);
      toast.success('Direccion agregada');
    }
    closeForm();
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al guardar la direccion');
  } finally {
    saving.value = false;
  }
}

async function setDefault(addr) {
  try {
    await api.post(`orders/addresses/${addr.uuid}/set-default/`);
    addresses.value = addresses.value.map(a => ({ ...a, is_default: a.uuid === addr.uuid }));
    toast.success('Direccion de envio actualizada');
  } catch {
    toast.error('Error al actualizar');
  }
}

async function executeDelete(addr) {
  deleting.value = true;
  try {
    await api.delete(`orders/addresses/${addr.uuid}/`);
    addresses.value = addresses.value.filter(a => a.uuid !== addr.uuid);
    toast.success('Direccion eliminada');
  } catch {
    toast.error('Error al eliminar');
  } finally {
    deleting.value = false;
    pendingDelete.value = null;
  }
}

onMounted(fetchAddresses);
</script>

<style scoped>
.addresses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.addr-title { font-weight: 700; font-size: 0.95rem; color: #1e3a8a; margin: 0; }
.addr-name { font-weight: 600; font-size: 0.85rem; color: var(--acc-text, #111827); margin: 0 0 4px; }
.addr-detail { font-size: 0.85rem; color: #374151; margin: 0; }

.addr-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}
</style>
